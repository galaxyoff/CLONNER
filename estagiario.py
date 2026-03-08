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

from downloader import download_file
from parser_utils import extract_links
from rewriter import rewrite_links
import database


# ANSI color codes
AZUL = '\033[94m'
VERDE = '\033[92m'
VERMELHO = '\033[91m'
RESET = '\033[0m'

def print_welcome():
    """Imprime a tela de boas-vindas"""
    print("\n" + "="*50)
    print("  ESTAGIARIO - FERRAMENTA DE CLONAGEM DE SITES")
    print("="*50)
    print(AZUL + "                    ESTAGIARIOX00" + RESET)


def login():
    """Função de login para verificar acesso usando banco de dados"""
    print("\n" + "="*40)
    print("         TELA DE LOGIN")
    print("="*40)
    
    usuario = input("Usuário: ").strip()
    # getpass esconde os caracteres digitados no terminal
    senha = getpass.getpass("Senha: ")
    
    # Verifica no banco de dados
    resultado = database.verificar_login(usuario, senha)
    
    if resultado['success']:
        print(VERDE + "✓ Acesso permitido!" + RESET)
        print(f"  Bem-vindo, {resultado['user']['username']}!")
        return True
    else:
        print(VERMELHO + "✗ " + resultado['message'] + RESET)
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
        
        # Track downloaded resources
        self.downloaded_resources = set()

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "EstagiarioBot/1.0 (+https://example.com)"
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
            logging.debug("robots.txt não pôde ser lido; ignorando")
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

    def _process(self, url):
        logging.info(f"Clonando {url}")
        self.visited.add(url)

        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()

        links, soup = extract_links(resp.text, url, self.domain)
        soup = rewrite_links(soup, self.output_dir, self.domain)

        # Save the downloaded file
        content_type = resp.headers.get("content-type", "")
        
        # Get the file path using the same logic as download_file
        from urllib.parse import urlparse, quote_plus
        parsed_url = urlparse(url)
        path = parsed_url.path
        if path.endswith("/") or path == "":
            path += "index.html"
        if parsed_url.query:
            qs = quote_plus(parsed_url.query, safe='')
            path = path.rstrip('/') + '_' + qs
        file_path = os.path.normpath(os.path.join(self.output_dir, path.lstrip("/")))
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        if "text/html" in content_type:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(str(soup))
        elif "text/css" in content_type:
            from rewriter import _rewrite_css_urls
            css_content = resp.text
            rewritten_css = _rewrite_css_urls(css_content, self.output_dir, self.domain)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(rewritten_css)

        return links

    def run(self):
        limit_msg = "sem limite" if self.max_pages is None else str(self.max_pages)
        logging.info(f"Iniciando clonagem de {self.start_url} (limite: {limit_msg} páginas)")
        
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            while self.to_visit:
                if self.max_pages is not None and len(self.visited) >= self.max_pages:
                    break
                    
                # Collect URLs to process in this batch
                urls_to_process = []
                while self.to_visit and len(urls_to_process) < self.workers:
                    url = self.to_visit.popleft()
                    if url not in self.visited and self._allowed(url):
                        urls_to_process.append(url)
                
                if not urls_to_process:
                    break
                    
                # Submit all URLs in parallel
                futures = {executor.submit(self._process, url): url for url in urls_to_process}
                
                # Process results and add new links to the queue
                for future in as_completed(futures):
                    try:
                        links = future.result()
                        # Add new links to the queue
                        if links:
                            for link in links:
                                if link not in self.visited and self._allowed(link):
                                    self.to_visit.append(link)
                    except Exception as e:
                        logging.warning(f"Erro ao processar: {e}")

        logging.info(f"Clonagem finalizada! Total de páginas clonadas: {len(self.visited)}")


def main():
    # Verifica se quer iniciar o painel admin
    if len(sys.argv) > 1 and sys.argv[1] == '--admin':
        iniciar_painel_admin()
        return
    
    # Chamar login antes de qualquer coisa
    if not login():
        print("Você precisa fazer login para usar a ferramenta.")
        sys.exit(1)
    
    parser = argparse.ArgumentParser(
        prog="Estagiario",
        description="Ferramenta de clonagem de sites"
    )

    parser.add_argument("url", nargs="?", default=None, help="URL inicial a ser clonada")
    parser.add_argument("-o", "--output", default=None,
                        help="Pasta de saída (padrão: output)")
    parser.add_argument("-m", "--max", type=int, default=None,
                        help="Máximo de páginas (padrão: sem limite)")
    parser.add_argument("-w", "--workers", type=int, default=4,
                        help="Número de threads simultâneas")
    parser.add_argument("--admin", action="store_true",
                        help="Abrir painel admin web")

    args = parser.parse_args()
    
    # Se quiser abrir painel admin
    if args.admin:
        iniciar_painel_admin()
        return
    
    # Se não passou URL como argumento, perguntar interativamente
    if args.url is None:
        print_welcome()
        print("\n=== URL do Site ===")
        args.url = input("Digite a URL do site que deseja clonar: ").strip()
        if not args.url:
            print("Erro: URL é obrigatória!")
            sys.exit(1)
        
        # Adicionar http se não tiver
        if not args.url.startswith("http"):
            args.url = "https://" + args.url
    
    print_welcome()
    
    if args.output is None:
        print("\n=== Configuração de Saída ===")
        print(f"Padrão: output (na pasta atual)")
        args.output = input("Digite o caminho onde deseja salvar o site: ").strip()
        if not args.output:
            args.output = "output"
    
    if args.max is None:
        print("\n=== Configuração de Páginas ===")
        print("Padrão: Clonar site inteiro (sem limite)")
        limit_input = input("Digite o número máximo de páginas (deixe vazio para clonar tudo): ").strip()
        if limit_input:
            try:
                args.max = int(limit_input)
            except ValueError:
                args.max = None
    
    print(f"\n🚀 Preparando para clonar: {args.url}")
    print(f"📁 Salvando em: {args.output}")
    if args.max:
        print(f"📄 Limite de páginas: {args.max}")
    else:
        print(f"📄 Limite: Site inteiro")
    print("\n")
    
    cloner = SiteCloner(args.url, args.output, args.max, args.workers)
    cloner.run()


if __name__ == "__main__":
    main()
