import os
import requests
from urllib.parse import urlparse, quote_plus
import logging

logger = logging.getLogger(__name__)


def get_content_type(response):
    """Extrai o content-type da resposta HTTP."""
    return response.headers.get('content-type', '').split(';')[0].strip().lower()


def get_file_extension(content_type, url):
    """
    Determina a extensão do arquivo baseado no content-type ou URL.
    """
    # Mapeamento de content-type para extensão
    content_type_map = {
        'text/html': '.html',
        'text/css': '.css',
        'application/javascript': '.js',
        'application/x-javascript': '.js',
        'text/javascript': '.js',
        'application/json': '.json',
        'application/xml': '.xml',
        'text/plain': '.txt',
        'image/png': '.png',
        'image/jpeg': '.jpg',
        'image/gif': '.gif',
        'image/svg+xml': '.svg',
        'image/webp': '.webp',
        'image/x-icon': '.ico',
        'font/woff': '.woff',
        'font/woff2': '.woff2',
        'font/ttf': '.ttf',
        'font/otf': '.otf',
        'video/mp4': '.mp4',
        'video/webm': '.webm',
        'video/ogg': '.ogg',
        'audio/mpeg': '.mp3',
        'audio/wav': '.wav',
        'audio/ogg': '.ogg',
        'application/pdf': '.pdf',
        'application/zip': '.zip',
    }
    
    # Primeiro tenta pelo content-type
    if content_type in content_type_map:
        return content_type_map[content_type]
    
    # Se não encontrar, tenta pela extensão na URL
    parsed_url = urlparse(url)
    path = parsed_url.path.lower()
    
    # Extensões comuns
    if path.endswith('.js'):
        return '.js'
    elif path.endswith('.css'):
        return '.css'
    elif path.endswith('.png'):
        return '.png'
    elif path.endswith('.jpg') or path.endswith('.jpeg'):
        return '.jpg'
    elif path.endswith('.gif'):
        return '.gif'
    elif path.endswith('.svg'):
        return '.svg'
    elif path.endswith('.webp'):
        return '.webp'
    elif path.endswith('.ico'):
        return '.ico'
    elif path.endswith('.woff'):
        return '.woff'
    elif path.endswith('.woff2'):
        return '.woff2'
    elif path.endswith('.ttf'):
        return '.ttf'
    elif path.endswith('.otf'):
        return '.otf'
    elif path.endswith('.mp4'):
        return '.mp4'
    elif path.endswith('.webm'):
        return '.webm'
    elif path.endswith('.mp3'):
        return '.mp3'
    elif path.endswith('.wav'):
        return '.wav'
    elif path.endswith('.pdf'):
        return '.pdf'
    
    # Padrão para HTML
    return '.html'


def download_file(session, url, output_dir, verify_ssl=True):
    """
    Baixa uma URL usando requests.Session e salva em output_dir.
    
    Args:
        session: requests.Session configurado
        url: URL para baixar
        output_dir: Diretório de saída
        verify_ssl: Se deve verificar certificados SSL
    
    Returns:
        O caminho local onde o arquivo foi salvo.
    
    Raises:
        Exception: Se o download falhar.
    """
    try:
        response = session.get(url, timeout=30, verify=verify_ssl)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.warning(f"Erro ao baixar {url}: {e}")
        raise
    
    content_type = get_content_type(response)
    
    # Parse da URL para determinar o caminho do arquivo
    parsed_url = urlparse(url)
    path = parsed_url.path
    
    # Tratar diretórios
    if path.endswith("/") or path == "":
        path += "index.html"
    
    # Incluir query string para evitar colisões
    if parsed_url.query:
        qs = quote_plus(parsed_url.query, safe='')
        path = path.rstrip('/') + '_' + qs
    
    # Se não tiver extensão, verificar pelo content-type
    if not os.path.splitext(path)[1]:
        ext = get_file_extension(content_type, url)
        if ext and ext != '.html':
            path = path.rstrip('/') + ext
    
    file_path = os.path.normpath(os.path.join(output_dir, path.lstrip("/")))
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Determinar modo de escrita
    is_binary = (
        'image' in content_type or
        'video' in content_type or
        'audio' in content_type or
        'font' in content_type or
        'pdf' in content_type or
        'zip' in content_type or
        'application/octet-stream' in content_type
    )
    
    if is_binary or 'b' in content_type:
        with open(file_path, "wb") as f:
            f.write(response.content)
    else:
        # Tentar detectar encoding
        encoding = response.encoding or 'utf-8'
        try:
            with open(file_path, "w", encoding=encoding) as f:
                f.write(response.text)
        except UnicodeEncodeError:
            # Se falhar, salvar como binary
            with open(file_path, "wb") as f:
                f.write(response.content)
    
    logger.info(f"✓ Baixado: {url} -> {file_path}")
    return file_path


def download_file_safe(session, url, output_dir, verify_ssl=True):
    """
    Versão segura do download que não lança exceção em caso de erro.
    
    Returns:
        Caminho do arquivo se bem-sucedido, None caso contrário.
    """
    try:
        return download_file(session, url, output_dir, verify_ssl)
    except Exception as e:
        logger.warning(f"Falha ao baixar {url}: {e}")
        return None


def get_all_resources_from_html(html, base_url, domain):
    """
    Extrai todos os recursos de uma página HTML.
    
    Args:
        html: Conteúdo HTML
        base_url: URL base da página
        domain: Domínio do site
    
    Returns:
        Lista de URLs de recursos a baixar.
    """
    from bs4 import BeautifulSoup
    import re
    
    soup = BeautifulSoup(html, "html.parser")
    resources = set()
    
    # URLs em atributos src e href
    for tag in soup.find_all(["script", "link", "img", "source", "video", "audio", "object", "embed", "iframe"]):
        for attr in ["src", "href", "data"]:
            url = tag.get(attr)
            if url and not url.startswith(('data:', 'mailto:', 'tel:', 'javascript:')):
                from urllib.parse import urljoin
                full_url = urljoin(base_url, url)
                parsed = urlparse(full_url)
                if parsed.netloc == domain or parsed.netloc == '':
                    resources.add(full_url)
    
    # URLs em srcset
    for tag in soup.find_all(attrs={"srcset": True}):
        for part in tag.get("srcset", "").split(","):
            url = part.strip().split()[0]
            if url and not url.startswith('data:'):
                from urllib.parse import urljoin
                full_url = urljoin(base_url, url)
                parsed = urlparse(full_url)
                if parsed.netloc == domain or parsed.netloc == '':
                    resources.add(full_url)
    
    # URLs em inline styles
    for tag in soup.find_all(style=True):
        for url in re.findall(r'url\(["\']?([^"\'()]+)["\']?\)', tag.get("style", "")):
            if url and not url.startswith('data:'):
                from urllib.parse import urljoin
                full_url = urljoin(base_url, url)
                parsed = urlparse(full_url)
                if parsed.netloc == domain or parsed.netloc == '':
                    resources.add(full_url)
    
    return list(resources)

