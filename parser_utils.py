from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
import re


def _normalize(url):
    """Remove fragment e trailing slash para normalizar URL."""
    url, _ = urldefrag(url)
    if url.endswith('/'):
        url = url[:-1]
    return url


def extract_links(html, base_url, domain):
    """
    Extrai todos os links de uma página HTML.
    
    Inclui:
    - Links de tags <a>
    - Scripts <script src>
    - Estilos <link href>
    - Imagens <img src> e <img srcset>
    - Vídeos <video>, <source>, <track>
    - Áudio <audio>, <source>
    - Fonts <link rel="stylesheet"> para fontes
    - Objetos <object>, <embed>
    - SVG <use>
    - Background images em inline styles
    - Data attributes comuns
    """
    soup = BeautifulSoup(html, "html.parser")
    links = set()

    def add_url(raw):
        """Adiciona URL normalizada se for do mesmo domínio."""
        if not raw:
            return
        full = urljoin(base_url, raw)
        parsed = urlparse(full)
        if parsed.netloc == domain:
            links.add(_normalize(full))

    # 1. Links em tags <a>
    for tag in soup.find_all("a"):
        add_url(tag.get("href"))

    # 2. Scripts JavaScript - <script src>
    for tag in soup.find_all("script", src=True):
        add_url(tag.get("src"))

    # 3. CSS externo - <link rel="stylesheet"> e <link href>
    for tag in soup.find_all("link", href=True):
        add_url(tag.get("href"))

    # 4. Imagens - <img src> e <img srcset>
    for tag in soup.find_all("img", src=True):
        add_url(tag.get("src"))
    
    # 5. Imagens em srcset (múltiplas resoluções)
    for tag in soup.find_all("img", srcset=True):
        for part in tag['srcset'].split(','):
            src = part.strip().split(' ')[0]
            add_url(src)

    # 6. Vídeos - <video>, <source>, <track>
    for tag in soup.find_all("video"):
        add_url(tag.get("src"))
        for source in tag.find_all("source", src=True):
            add_url(source.get("src"))
        for track in tag.find_all("track", src=True):
            add_url(track.get("src"))
    
    for tag in soup.find_all("source", src=True):
        add_url(tag.get("src"))

    # 7. Áudio - <audio>, <source>
    for tag in soup.find_all("audio"):
        add_url(tag.get("src"))
        for source in tag.find_all("source", src=True):
            add_url(source.get("src"))

    # 8. Objetos e embeds - <object>, <embed>
    for tag in soup.find_all("object", data=True):
        add_url(tag.get("data"))
    for tag in soup.find_all("embed", src=True):
        add_url(tag.get("src"))

    # 9. SVG - <use href/xlink:href>
    for tag in soup.find_all("use"):
        add_url(tag.get("href"))
        add_url(tag.get("xlink:href"))

    # 10. Iframes
    for tag in soup.find_all("iframe", src=True):
        add_url(tag.get("src"))

    # 11. Background images em inline styles
    for element in soup.find_all(style=True):
        style_text = element.get("style", "")
        for url in re.findall(r'url\(["\']?([^"\'()]+)["\']?\)', style_text):
            add_url(url.strip('"\''))

    # 12. URLs em style tags
    for style_tag in soup.find_all("style"):
        style_text = style_tag.string or ""
        for url in re.findall(r'url\(["\']?([^"\'()]+)["\']?\)', style_text):
            add_url(url.strip('"\''))

    # 13. Data attributes comuns
    data_attrs = [
        'data-src', 'data-background', 'data-image', 'data-icon',
        'data-src-large', 'data-src-small', 'data.original', 'data.lazy'
    ]
    for attr in data_attrs:
        for tag in soup.find_all(attrs={attr: True}):
            add_url(tag.get(attr))

    # 14. Meta tags (og:image, twitter:image, etc.)
    for tag in soup.find_all("meta", content=True):
        content = tag.get("content", "")
        if any(x in tag.get("property", "") or tag.get("name", "") for x in ["image", "video", "audio"]):
            add_url(content)

    return links, soup


def get_resource_type(url):
    """
    Determina o tipo de recurso baseado na URL.
    
    Retorna:
    - 'html': Página HTML
    - 'css': Arquivo CSS
    - 'js': Arquivo JavaScript
    - 'image': Imagem (jpg, png, gif, svg, webp, etc.)
    - 'font': Fonte (woff, woff2, ttf, otf, etc.)
    - 'video': Vídeo (mp4, webm, ogg, etc.)
    - 'audio': Áudio (mp3, wav, ogg, etc.)
    - 'other': Outro tipo
    """
    parsed = urlparse(url)
    path = parsed.path.lower()
    ext = path.split('.')[-1] if '.' in path else ''
    
    # Mapeamento de extensões para tipos
    image_exts = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'ico', 'bmp', 'tiff', 'avif']
    css_exts = ['css']
    js_exts = ['js', 'mjs']
    font_exts = ['woff', 'woff2', 'ttf', 'otf', 'eot', 'svg']
    video_exts = ['mp4', 'webm', 'ogg', 'avi', 'mov', 'wmv', 'flv']
    audio_exts = ['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a']
    document_exts = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx']
    
    if ext in image_exts or 'image' in path:
        return 'image'
    elif ext in css_exts or path.endswith('.css'):
        return 'css'
    elif ext in js_exts or 'javascript' in path or '.js' in path:
        return 'js'
    elif ext in font_exts or 'font' in path or 'fonts' in path:
        return 'font'
    elif ext in video_exts or 'video' in path:
        return 'video'
    elif ext in audio_exts or 'audio' in path or 'sound' in path:
        return 'audio'
    elif ext in document_exts:
        return 'document'
    elif 'html' in path or path == '' or path.endswith('/'):
        return 'html'
    else:
        return 'other'

