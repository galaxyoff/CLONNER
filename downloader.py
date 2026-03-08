import os
from urllib.parse import urlparse, quote_plus


def download_file(session, url, output_dir):
    """Fetch URL using a requests.Session and save it under output_dir.

    Returns the local filesystem path where it was stored. Raises on failure.
    """
    response = session.get(url, timeout=10)
    response.raise_for_status()

    parsed_url = urlparse(url)
    path = parsed_url.path
    if path.endswith("/") or path == "":
        path += "index.html"

    # include query if present to avoid collisions
    if parsed_url.query:
        qs = quote_plus(parsed_url.query, safe='')
        path = path.rstrip('/') + '_' + qs

    file_path = os.path.normpath(os.path.join(output_dir, path.lstrip("/")))
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    mode = "wb" if 'b' in response.headers.get('content-type', '') or not response.text else "w"
    encoding = None if mode == "wb" else "utf-8"
    with open(file_path, mode, encoding=encoding) as f:
        f.write(response.content if mode == "wb" else response.text)

    return file_path
    print(f"Downloaded {url} to {file_path}")