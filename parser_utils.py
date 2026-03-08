from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
import re


def _normalize(url):
    # remove fragment and trailing slash consistency
    url, _ = urldefrag(url)
    if url.endswith('/'):
        url = url[:-1]
    return url


def extract_links(html, base_url, domain):
    soup = BeautifulSoup(html, "html.parser")
    links = set()

    # helper to add normalized same-domain url
    def add_url(raw):
        if not raw:
            return
        full = urljoin(base_url, raw)
        parsed = urlparse(full)
        if parsed.netloc == domain:
            links.add(_normalize(full))

    for tag in soup.find_all(["a", "img", "link", "script", "source"]):
        attr = "href" if tag.name in ["a", "link"] else "src"
        add_url(tag.get(attr))

        # handle srcset (image sets)
        if tag.has_attr('srcset'):
            for part in tag['srcset'].split(','):
                src = part.strip().split(' ')[0]
                add_url(src)

    # extract urls from inline style or <style> content
    style_text = ''
    for element in soup.find_all(style=True):
        style_text += element['style'] + '\n'
    for style_tag in soup.find_all('style'):
        style_text += style_tag.string or ''

    for url in re.findall(r'url\(([^)]+)\)', style_text):
        add_url(url.strip('"\''))

    return links, soup