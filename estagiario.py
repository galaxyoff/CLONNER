import os
import argparse
import logging
import requests
import sys
import getpass
from urllib.parse import urlparse, urljoin
from urllib import robotparser
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
import ctypes
import subprocess

# Enable ANSI colors on Windows and set UTF-8 encoding
subprocess.run(['chcp', '65001'], shell=True, capture_output=True)
kernel32 = ctypes.windll.kernel32
kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

from downloader import download_file, download_file_safe, get_all_resources_from_html
from parser_utils import extract_links, get_resource_type
from rewriter import rewrite_links


# Configuracao do servidor (pode ser via variavel de ambiente ou perguntar ao usuario)
SERVER_URL = os.environ.get('ESTAGIARIO_SERVER', '').rstrip('/')


# ANSI color codes
AZUL = '\033[94m'
VERDE = '\033[92m'
VERMELHO = '\033[91m'
AMARELO = '\033[93m'
RESET = '\033[0m'

def print_welcome():
    """Imprime a tela de boas-vindas"""
    print("\n" + "="*60)
    print("  ██████╗ ███████╗████████╗██████╗  ██████╗  █████╗ ██████╗ ██████╗ ")
    print("  ██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔═══██╗██╔══██╗██╔══██╗██╔══██╗")
    print("  ██████╔╝█████╗     ██║   ██████╔╝██║   ██║███████║██████╔╝██║  ██║")
    print("  ██╔══██╗██╔══╝     ██║   ██╔══██╗██║   ██║██╔══██║██╔══██╗██║  ██║")
    print("  ██║  ██║███████╗   ██║   ██║  ██║╚██████╔╝██║  ██║██║  ██║██████╔╝")
    print("  ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ")
    print("="*60)
    print(AZUL + "        FERRAMENTA PROFISSIONAL DE CLONAGEM DE SITES" + RESET)
    print(AMARELO + "                    Versão 2.0" + RESET)
    print("="*60 + "\n")


def login():
    """Funcao de login para verificar acesso via API"""
    global SERVER_URL
    
    print("\n" + "="*40)
    print("         🔐 TELA DE LOGIN")
    print("="*40)
    
    # Se nao tem servidor configurado, pergunta
    if not SERVER_URL:
        print("\n🌐 Configure o servidor de autenticacao:")
        SERVER_URL = input("Digite a URL do servidor: ").strip().rstrip('/')
        if not SERVER_URL:
            print(VERMELHO + "✗ Servidor nao informado!" + RESET)
            return False
    
    usuario = input("Usuario: ").strip()
    senha = getpass.getpass("Senha: ")
    
    try:
        response = requests.post(
            f"{SERVER_URL}/api/login",
            data={'username': usuario, 'password': senha},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(VERDE + "✓ Acesso permitido!" + RESET)
                print(f"  Bem-vindo, {data['user']['username']}!")
                
                # Verificar se acesso expirou
                if data['user'].get('access_expires'):
                    print(f"  ⚠️  Acesso expira em: {data['user']['access_expires']}")
                return True
            else:
                print(VERMELHO + "✗ " + data.get('message', 'Login falhou') + RESET)
                return False
        else:
            print(VERMELHO + "✗ Erro ao conectar com o servidor!" + RESET)
            print(f"   Codigo: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(VERMELHO + "✗ Nao foi possivel conectar ao servidor!" + RESET)
        print(f"   Verifique se {SERVER_URL} esta acessivel")
        return False
    except Exception as e:
        print(VERMELHO + "✗ Erro: " + str(e) + RESET)
        return False


def iniciar_painel_admin():
    """Inicia o painel admin web"""
    print(VERDE + "\n🌐 Iniciando painel admin..." + RESET)
    print("   Acesse: http://localhost:5000/admin")
    print("   Para sair, pressione Ctrl+C\n")
    import admin_panel
    admin_panel.main()


class SiteCloner:
    def __init__(self, start_url, output_dir="output", max_pages=None, workers=4):
        self.start_url = start_url
        self.output_dir = output_dir
        self.max_pages = max_pages
        self.workers = workers

        parsed = urlparse(start_url)
        self.domain = parsed.netloc
        os.makedirs(output_dir, exist_ok=True)

        self.visited = set()
        self.to_visit = deque([self._normalize(start_url)])
        
        # Recursos baixados
        self.downloaded_resources = set()
        self.failed_downloads = []

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "EstagiarioBot/2.0 (+https://estagiario.com.br)"
        })

        self._setup_robots(start_url)

        logging.basicConfig(
            level=logging.INFO,
            format="[%(levelname)s] %(message)s"
        )

    def _setup_robots(self, url):
        rp = robotparser.RobotFileParser()
        rp.set_url(urljoin(url, "/robots.txt"))
        try:
            rp.read()
        except Exception:
            logging.debug("robots.txt nao pode ser lido; ignorando")
        self.robots = rp

    def _normalize(self, url):
        parsed = urlparse(url)
        clean = parsed._replace(fragment="").geturl()
        if clean.endswith("/") and not clean == urljoin(clean, "/"):
            clean = clean.rstrip("/")
        return clean

    def _allowed(self, url):
        try:
            return self.robots.can_fetch("*", url)
        except Exception:
            return True

    def _download_resource(self, url):
        """Baixa um recurso (imagem, CSS, JS, fonte, etc.)"""
        if url in self.downloaded_resources:
            return True
            
        try:
            download_file(self.session, url, self.output_dir)
            self.downloaded_resources.add(url)
            return True
        except Exception as e:
            logging.warning(f"Erro ao baixar recurso {url}: {e}")
            self.failed_downloads.append(url)
            return False

    def _process(self, url):
        """Processa uma URL - baixa a página e extrai links"""
        logging.info(f"Clonando {url}")
        self.visited.add(url)

        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        
        # Se for HTML, processa normally
        if "text/html" in content_type:
            links, soup = extract_links(resp.text, url, self.domain)
            soup = rewrite_links(soup, self.output_dir, self.domain)
            
            # Salvar HTML modificado
            file_path = self._get_file_path(url)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(str(soup))
            
            # Baixar recursos encontrados na página
            self._download_page_resources(resp.text, url)
            
            return links
        else:
            # Não é HTML, apenas baixar o arquivo
            try:
                download_file(self.session, url, self.output_dir)
                self.downloaded_resources.add(url)
            except Exception as e:
                logging.warning(f"Erro ao baixar {url}: {e}")
            
            return []

    def _download_page_resources(self, html, base_url):
        """Baixa todos os recursos de uma página HTML"""
        resources = get_all_resources_from_html(html, base_url, self.domain)
        
        logging.info(f"Baixando {len(resources)} recursos da página...")
        
        # Usar thread pool para baixar recursos em paralelo
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {executor.submit(self._download_resource, url): url for url in resources}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    url = futures[future]
                    logging.warning(f"Erro ao baixar {url}: {e}")

    def _get_file_path(self, url):
        """Retorna o caminho do arquivo local para uma URL"""
        from urllib.parse import urlparse, quote_plus
        parsed_url = urlparse(url)
        path = parsed_url.path
        if path.endswith("/") or path == "":
            path += "index.html"
        if parsed_url.query:
            qs = quote_plus(parsed_url.query, safe='')
            path = path.rstrip('/') + '_' + qs
        file_path = os.path.normpath(os.path.join(self.output_dir, path.lstrip("/")))
        return file_path

    def run(self):
        limit_msg = "sem limite" if self.max_pages is None else str(self.max_pages)
        logging.info(f"Iniciando clonagem de {self.start_url}")
        logging.info(f"Limite: {limit_msg} paginas | Workers: {self.workers}")
        
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            while self.to_visit:
                if self.max_pages is not None and len(self.visited) >= self.max_pages:
                    break
                    
                # Coletar URLs para processar nesta tanda
                urls_to_process = []
                while self.to_visit and len(urls_to_process) < self.workers:
                    url = self.to_visit.popleft()
                    if url not in self.visited and self._allowed(url):
                        urls_to_process.append(url)
                
                if not urls_to_process:
                    break
                    
                # Processar URLs em paralelo
                futures = {executor.submit(self._process, url): url for url in urls_to_process}
                
                # Processar resultados e adicionar novos links
                for future in as_completed(futures):
                    try:
                        links = future.result()
                        if links:
                            for link in links:
                                if link not in self.visited and self._allowed(link):
                                    self.to_visit.append(link)
                    except Exception as e:
                        logging.warning(f"Erro ao processar: {e}")

        # Resumo final
        print("\n" + "="*50)
        print("  📊 RESUMO DA CLONAGEM")
        print("="*50)
        print(f"  ✓ Paginas clonadas: {len(self.visited)}")
        print(f"  ✓ Recursos baixados: {len(self.downloaded_resources)}")
        if self.failed_downloads:
            print(f"  ⚠️  Falhas: {len(self.failed_downloads)}")
        print(f"  📁 Salvo em: {os.path.abspath(self.output_dir)}")
        print("="*50 + "\n")


def main():
    # Verifica se quer iniciar o painel admin
    if len(sys.argv) > 1 and sys.argv[1] == '--admin':
        iniciar_painel_admin()
        return
    
    # Chamar login antes de qualquer coisa
    if not login():
        print("Voce precisa fazer login para usar a ferramenta.")
        sys.exit(1)
    
    parser = argparse.ArgumentParser(
        prog="Estagiario",
        description="Ferramenta profissional de clonagem de sites",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  estagiario https://exemplo.com
  estagiario https://exemplo.com -o minha_pasta
  estagiario https://exemplo.com -m 50 -w 8
        """
    )

    parser.add_argument("url", nargs="?", default=None, help="URL inicial a ser clonada")
    parser.add_argument("-o", "--output", default=None,
                        help="Pasta de saida (padrao: output)")
    parser.add_argument("-m", "--max", type=int, default=None,
                        help="Maximo de paginas (padrao: sem limite)")
    parser.add_argument("-w", "--workers", type=int, default=4,
                        help="Numero de threads simultaneas (padrao: 4)")
    parser.add_argument("--admin", action="store_true",
                        help="Abrir painel admin web")

    args = parser.parse_args()
    
    # Se quiser abrir painel admin
    if args.admin:
        iniciar_painel_admin()
        return
    
    # Se nao passou URL como argumento, perguntar interativamente
    if args.url is None:
        print_welcome()
        print("\n=== URL do Site ===")
        args.url = input("Digite a URL do site que deseja clonar: ").strip()
        if not args.url:
            print("Erro: URL e obrigatoria!")
            sys.exit(1)
        
        # Adicionar http se nao tiver
        if not args.url.startswith("http"):
            args.url = "https://" + args.url
    
    print_welcome()
    
    if args.output is None:
        print("\n=== Configuracao de Saida ===")
        print(f"Padrao: output (na pasta atual)")
        args.output = input("Digite o caminho onde deseja salvar o site: ").strip()
        if not args.output:
            args.output = "output"
    
    if args.max is None:
        print("\n=== Configuracao de Paginas ===")
        print("Padrao: Clonar site inteiro (sem limite)")
        limit_input = input("Digite o numero maximo de paginas (deixe vazio para clonar tudo): ").strip()
        if limit_input:
            try:
                args.max = int(limit_input)
            except ValueError:
                args.max = None
    
    print(f"\n{AMARELO}🚀 Preparando para clonar:{RESET} {args.url}")
    print(f"{VERDE}📁 Salvando em:{RESET} {args.output}")
    if args.max:
        print(f"{AZUL}📄 Limite de paginas:{RESET} {args.max}")
    else:
        print(f"{AZUL}📄 Limite:{RESET} Site inteiro")
    print(f"{AZUL}⚡ Workers:{RESET} {args.workers}")
    print("\n")
    
    cloner = SiteCloner(args.url, args.output, args.max, args.workers)
    cloner.run()


if __name__ == "__main__":
    main()

