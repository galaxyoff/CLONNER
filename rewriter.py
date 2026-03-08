import os
from urllib.parse import urlparse, urlunparse


def _make_local_path(output_dir, parsed_url):
    # convert path+query to a filesystem-safe name
    path = parsed_url.path
    if path.endswith("/") or path == "":
        path += "index.html"
    # include query string if present
    if parsed_url.query:
        # replace & and = to avoid invalid filenames
        query = parsed_url.query.replace('&', '_').replace('=', '-')
        path = path.rstrip('/') + '_' + query
    return os.path.normpath(os.path.join(output_dir, path.lstrip('/')))


def rewrite_links(soup, output_dir, domain):
    """Change URLs that point to the same domain into local relative paths.

    Also rewrites URLs inside inline CSS and style tags.
    """
    for tag in soup.find_all(["a", "img", "link", "script", "source"]):
        attr = "href" if tag.name in ["a", "link"] else "src"
        url = tag.get(attr)

        if url:
            parsed_url = urlparse(url)
            if parsed_url.netloc == domain or parsed_url.netloc == '':
                local_path = _make_local_path(output_dir, parsed_url)
                # make relative link from output_dir
                rel = os.path.relpath(local_path, output_dir)
                # convert backslashes to forward for HTML
                tag[attr] = rel.replace(os.path.sep, '/')

    # rewrite urls() inside style attributes and <style> tags
    for element in soup.find_all(style=True):
        element['style'] = _rewrite_css_urls(element['style'], output_dir, domain)
    for style_tag in soup.find_all('style'):
        style_tag.string = _rewrite_css_urls(style_tag.string or '', output_dir, domain)

    return soup


def _rewrite_css_urls(css_text, output_dir, domain):
    import re
    def repl(match):
        url = match.group(1).strip('"\'')
        parsed = urlparse(url)
        if parsed.netloc == domain or parsed.netloc == '':
            local_path = _make_local_path(output_dir, parsed)
            rel = os.path.relpath(local_path, output_dir).replace(os.path.sep, '/')
            return f'url("{rel}")'
        else:
            return match.group(0)
    return re.sub(r'url\(([^)]+)\)', repl, css_text)
