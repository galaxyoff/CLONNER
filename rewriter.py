import os
from urllib.parse import urlparse, urlunparse


def _make_local_path(output_dir, parsed_url):
    """
    Converte path+query para um nome seguro para o sistema de arquivos.
    """
    path = parsed_url.path
    
    # Adicionar index.html para diretórios
    if path.endswith("/") or path == "":
        path += "index.html"
    
    # Incluir query string se presente
    if parsed_url.query:
        # Substituir caracteres especiais para evitar nomes de arquivo inválidos
        query = parsed_url.query.replace('&', '_').replace('=', '-').replace('/', '_')
        path = path.rstrip('/') + '_' + query
    
    return os.path.normpath(os.path.join(output_dir, path.lstrip('/')))


def rewrite_links(soup, output_dir, domain):
    """
    Reescreve URLs que apontam para o mesmo domínio em caminhos locais relativos.
    
    Inclui:
    - Links em tags <a>
    - Scripts <script src>
    - Estilos <link href>
    - Imagens <img src> e <img srcset>
    - Vídeos <video>, <source>
    - Áudio <audio>, <source>
    - Objetos <object>, <embed>
    - Fonts em CSS inline e <style>
    """
    # 1. Reescrever href/src em tags comuns
    for tag in soup.find_all(["a", "img", "link", "script", "source", "video", "audio", "object", "embed", "iframe"]):
        attr = "href" if tag.name in ["a", "link"] else "src"
        url = tag.get(attr)

        if url:
            parsed_url = urlparse(url)
            # Apenas reescrever URLs do mesmo domínio ou URLs relativas
            if parsed_url.netloc == domain or parsed_url.netloc == '':
                local_path = _make_local_path(output_dir, parsed_url)
                # Criar link relativo a partir do output_dir
                rel = os.path.relpath(local_path, output_dir)
                # Converter barras invertidas para frente para HTML
                tag[attr] = rel.replace(os.path.sep, '/')

    # 2. Reescrever srcset em imagens
    for tag in soup.find_all("img", srcset=True):
        srcset = tag.get("srcset", "")
        new_srcset_parts = []
        
        for part in srcset.split(','):
            part = part.strip()
            if not part:
                continue
                
            # Separar URL de descriptors (width, pixel density)
            parts = part.split()
            if not parts:
                continue
                
            url = parts[0]
            descriptor = ' '.join(parts[1:]) if len(parts) > 1 else ''
            
            parsed_url = urlparse(url)
            if parsed_url.netloc == domain or parsed_url.netloc == '':
                local_path = _make_local_path(output_dir, parsed_url)
                rel = os.path.relpath(local_path, output_dir).replace(os.path.sep, '/')
                
                if descriptor:
                    new_srcset_parts.append(f"{rel} {descriptor}")
                else:
                    new_srcset_parts.append(rel)
        
        if new_srcset_parts:
            tag['srcset'] = ', '.join(new_srcset_parts)

    # 3. Reescrever urls() dentro de atributos style
    for element in soup.find_all(style=True):
        original_style = element.get('style', '')
        rewritten_style = _rewrite_css_urls(original_style, output_dir, domain)
        element['style'] = rewritten_style

    # 4. Reescrever urls() dentro de tags <style>
    for style_tag in soup.find_all('style'):
        if style_tag.string:
            style_tag.string = _rewrite_css_urls(style_tag.string, output_dir, domain)

    # 5. Reescrever data attributes comuns
    data_attrs = [
        'data-src', 'data-background', 'data-image', 'data-icon',
        'data-src-large', 'data-src-small', 'data.original', 'data.lazy'
    ]
    for attr in data_attrs:
        for tag in soup.find_all(attrs={attr: True}):
            url = tag.get(attr)
            if url:
                parsed_url = urlparse(url)
                if parsed_url.netloc == domain or parsed_url.netloc == '':
                    local_path = _make_local_path(output_dir, parsed_url)
                    rel = os.path.relpath(local_path, output_dir).replace(os.path.sep, '/')
                    tag[attr] = rel

    # 6. Reescrever URLs em meta tags (og:image, twitter:image, etc.)
    for tag in soup.find_all("meta", content=True):
        content = tag.get("content", "")
        prop_or_name = tag.get("property", "") or tag.get("name", "")
        
        if any(x in prop_or_name for x in ["image", "video", "audio"]):
            parsed_url = urlparse(content)
            if parsed_url.netloc == domain or parsed_url.netloc == '':
                local_path = _make_local_path(output_dir, parsed_url)
                rel = os.path.relpath(local_path, output_dir).replace(os.path.sep, '/')
                tag['content'] = rel

    # 7. Reescrever <use href/xlink:href>
    for tag in soup.find_all("use"):
        for attr in ["href", "xlink:href"]:
            url = tag.get(attr)
            if url:
                parsed_url = urlparse(url)
                if parsed_url.netloc == domain or parsed_url.netloc == '':
                    local_path = _make_local_path(output_dir, parsed_url)
                    rel = os.path.relpath(local_path, output_dir).replace(os.path.sep, '/')
                    tag[attr] = rel

    return soup


def _rewrite_css_urls(css_text, output_dir, domain):
    """Rewrites URLs inside CSS text (inline styles or <style> tags)."""
    import re
    
    def repl(match):
        url = match.group(1).strip('"\'')
        
        # Skip data URIs
        if url.startswith('data:'):
            return match.group(0)
        
        parsed = urlparse(url)
        
        # Only rewrite same-domain URLs
        if parsed.netloc == domain or parsed.netloc == '':
            local_path = _make_local_path(output_dir, parsed)
            rel = os.path.relpath(local_path, output_dir).replace(os.path.sep, '/')
            return f'url("{rel}")'
        else:
            return match.group(0)
    
    # Match url() patterns, including escaped quotes
    return re.sub(r'url\(\s*["\']?([^"\'()]+)["\']?\s*\)', repl, css_text)


def get_content_type_for_extension(file_path):
    """
    Retorna o Content-Type baseado na extensão do arquivo.
    Útil para servir arquivos estáticos corretamente.
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    content_types = {
        '.html': 'text/html',
        '.htm': 'text/html',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.mjs': 'application/javascript',
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.txt': 'text/plain',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.webp': 'image/webp',
        '.ico': 'image/x-icon',
        '.bmp': 'image/bmp',
        '.woff': 'font/woff',
        '.woff2': 'font/woff2',
        '.ttf': 'font/ttf',
        '.otf': 'font/otf',
        '.eot': 'application/vnd.ms-fontobject',
        '.mp4': 'video/mp4',
        '.webm': 'video/webm',
        '.ogg': 'video/ogg',
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.ogg': 'audio/ogg',
        '.pdf': 'application/pdf',
        '.zip': 'application/zip',
    }
    
    return content_types.get(ext, 'application/octet-stream')

