import re
import os
import html
import socket
import ipaddress
from urllib.parse import urlparse
from html.parser import HTMLParser

from flask import Flask, render_template, jsonify, send_from_directory, request
import feedparser
import requests
from blingfire import text_to_sentences

# service-to-service auth
import google.auth.transport.requests
import google.oauth2.id_token

app = Flask(__name__)
app.config.from_object('rss_config')
rss_feed_urls = app.config['RSS_FEEDS']

URL_REGEX = re.compile(r'^https?://[^\s/$.?#].[^\s]*$', re.IGNORECASE)
METADATA_HOSTS = {"metadata.google.internal", "metadata", "169.254.169.254"}
REQUEST_HEADERS = {
    'user-agent': 'Mozilla/5.0 (X11; Linux i686; rv:109.0) Gecko/20100101 Firefox/120.0',
    'accept': '*/*'
}
MAX_FEED_ITEMS = 5
MAX_FEED_BYTES = 3 * 1024 * 1024  # 3MB response cap
ALLOWED_FEED_PORTS = {80, 443}
HTTP_SESSION = requests.Session()
HTTP_SESSION.headers.update(REQUEST_HEADERS)

class StrippingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def get_text(self):
        return "".join(self.parts)

def html_to_text(s: str) -> str:
    parser = StrippingParser()
    parser.feed(s)
    return html.unescape(parser.get_text()).strip()

def first_sentence(text: str) -> str:
    if not text:
        return ""

    try:
        # blingfire returns newline-separated sentences
        sentences = text_to_sentences(text).split("\n")

        for s in sentences:
            s = s.strip()
            if s:
                return s

        # if blingfire returns only empty lines, fall back
        return text

    except Exception:
        # any failure → safe fallback
        return text

def clean_summary(summary: str, max_length: int = 200) -> str:
    """
    Cleans and truncates an RSS summary:
    - Strips HTML
    - Unescapes HTML entities
    - Extracts the first sentence or line
    - Truncates cleanly at word boundaries up to `max_length`
    """
    if not summary:
        return ""

    # Remove HTML tags and unescape entities
    text = html_to_text(summary)

    first = first_sentence(text)

    # Fallback if no clean sentence found
    return truncate_at_word_boundary(first, max_length)

def truncate_at_word_boundary(text: str, max_length: int) -> str:
    """
    Truncates the text at the last word boundary before max_length.
    Appends ellipsis if truncation occurs.
    """
    if len(text) <= max_length:
        return text

    # Prefer the last whitespace boundary, but fall back to a hard cut for long words.
    cut = None
    for match in re.finditer(r'\s+', text[:max_length + 1]):
        cut = match.start()
    if cut is None or cut < max_length * 0.5:
        cut = max_length

    truncated = text[:cut].rstrip()
    if not truncated:
        truncated = text[:max_length].rstrip()
    if not truncated:
        return "..." if max_length > 0 else ""

    if truncated[-1] in ".!?":
        truncated = truncated[:-1]
    return truncated + "..."

def is_blocked_ip(ip_str: str) -> bool:
    ip = ipaddress.ip_address(ip_str)
    return any([
        ip.is_loopback,
        ip.is_private,
        ip.is_link_local,
        ip.is_multicast,
        ip.is_reserved,
        ip.is_unspecified,
    ])

def validate_feed_url(rss_feed_url: str, strict_ssrf: bool = False):
    if not rss_feed_url or not URL_REGEX.match(rss_feed_url):
        return False, "Malformed URL"

    parsed = urlparse(rss_feed_url)
    if parsed.scheme not in ("http", "https"):
        return False, "Only http/https URLs are allowed"

    hostname = (parsed.hostname or "").lower().strip()
    if not hostname:
        return False, "URL must include a hostname"

    if parsed.port and parsed.port not in ALLOWED_FEED_PORTS:
        return False, "Blocked port"

    if hostname in METADATA_HOSTS:
        return False, "Blocked host"

    if hostname == "localhost" or hostname.endswith(".localhost"):
        return False, "Blocked host"

    if strict_ssrf:
        try:
            for info in socket.getaddrinfo(hostname, None):
                ip_str = info[4][0]
                if is_blocked_ip(ip_str):
                    return False, "Blocked host"
        except Exception:
            return False, "Unable to resolve host"

    return True, None

def sanitize_outbound_link(link: str) -> str:
    if not link:
        return None
    link = html.unescape(str(link)).strip()
    if not link:
        return None
    parsed = urlparse(link)
    if parsed.scheme not in ("http", "https"):
        return None
    return link

def read_limited_response_text(response, max_bytes: int):
    chunks = []
    total = 0
    for chunk in response.iter_content(chunk_size=65536, decode_unicode=False):
        if not chunk:
            continue
        total += len(chunk)
        if total > max_bytes:
            return None
        chunks.append(chunk)

    body = b"".join(chunks)
    encoding = response.encoding or "utf-8"
    return body.decode(encoding, errors="replace")

def parse_feed_items(xml_string: str):
    if len(xml_string) < 100:
        return {'success': False, 'error': 'Bad feed data (response too short)'}

    try:
        feed_parsed = feedparser.parse(xml_string)
    except Exception:
        return {'success': False, 'error': 'unable to parse'}

    feed_items = []
    for entry in feed_parsed.entries:
        title = entry.get('title')
        link = sanitize_outbound_link(entry.get('link'))

        if not title or not link:
            continue

        summary = clean_summary(entry.get('summary', ""))
        feed_items.append({
            'title': html.unescape(title),
            'summary': summary,
            'url': html.unescape(link),
        })

        if len(feed_items) == MAX_FEED_ITEMS:
            break

    feed_title = ""
    try:
        feed_title = html.unescape(feed_parsed['feed'].get('title', 'Untitled Feed'))
    except Exception:
        feed_title = "Untitled Feed"

    return {'success': True, 'title': feed_title, 'feed_items': feed_items}

def fetch_feed_payload(rss_feed_url: str, strict_ssrf: bool = False):
    valid, error = validate_feed_url(rss_feed_url, strict_ssrf=strict_ssrf)
    if not valid:
        return {'success': False, 'error': error, 'errorType': 'validation'}

    headers = {}

    # If the URL contains cloudfunctions.net then get an auth token.
    if 'cloudfunctions.net' in rss_feed_url:
        auth_req = google.auth.transport.requests.Request()
        id_token = google.oauth2.id_token.fetch_id_token(auth_req, rss_feed_url)
        headers["Authorization"] = f"Bearer {id_token}"

    try:
        response = HTTP_SESSION.get(
            rss_feed_url,
            headers=headers,
            timeout=20,
            allow_redirects=not strict_ssrf,
            stream=True,
        )
    except Exception:
        return {'success': False, 'error': 'Unable to fetch feed URL', 'errorType': 'upstream'}

    if strict_ssrf and response.is_redirect:
        response.close()
        return {'success': False, 'error': 'Redirects are not allowed', 'errorType': 'validation'}

    if not response.ok:
        response.close()
        return {'success': False, 'error': f'Server returned: {response.status_code}', 'errorType': 'upstream'}

    xml_text = read_limited_response_text(response, MAX_FEED_BYTES)
    response.close()
    if xml_text is None:
        return {'success': False, 'error': 'Feed response too large', 'errorType': 'validation'}

    return parse_feed_items(xml_text)


# Route to render the main page
@app.route('/')
def index():
    return render_template('home.html')

@app.route('/api/v1/config')
def api_config():
    return jsonify({
        'appTitle': 'BOXED NEWS NOW',
        'maxItemsPerFeed': MAX_FEED_ITEMS,
    })

@app.route('/api/v1/feeds/default')
def api_default_feeds():
    feeds = []
    for idx, source_url in enumerate(rss_feed_urls, start=1):
        feeds.append({
            'id': f'default:{idx}',
            'index': idx,
            'sourceUrl': source_url,
            'displayName': None,
        })
    return jsonify(feeds)

@app.route('/api/v1/feeds/fetch', methods=['POST'])
def api_fetch_feed():
    payload = request.get_json(silent=True) or {}
    feed_ref = payload.get('feedRef') or {}
    ref_type = feed_ref.get('type')

    if ref_type == 'default':
        index = feed_ref.get('index')
        if not isinstance(index, int) or index < 1 or index > len(rss_feed_urls):
            return jsonify({'success': False, 'error': 'feed index out of range'}), 400
        result = fetch_feed_payload(rss_feed_urls[index - 1], strict_ssrf=False)
        status_code = 200 if result.get('success') else 502
        return jsonify(result), status_code

    if ref_type == 'url':
        rss_feed_url = feed_ref.get('url')
        result = fetch_feed_payload(rss_feed_url, strict_ssrf=True)
        if result.get('success'):
            status_code = 200
        elif result.get('errorType') == 'validation':
            status_code = 400
        else:
            status_code = 502
        return jsonify(result), status_code

    return jsonify({'success': False, 'error': 'Unsupported feedRef.type'}), 400

# Route to fetch and return the RSS feed as JSON
@app.route('/fetch_feed/<int:feed_number>')
def fetch_feed(feed_number):
    if feed_number < 1 or feed_number > len(rss_feed_urls):
        return jsonify({'success': False, 'error': f'feed index out of range: {feed_number}'})
    return jsonify(fetch_feed_payload(rss_feed_urls[feed_number - 1], strict_ssrf=False))

@app.route('/static/<path:filename>')
def serve_static(filename):
    root_dir = os.path.dirname(os.getcwd())
    return send_from_directory(os.path.join(root_dir, 'static'), filename)

@app.route('/favicon.ico')
def serve_favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/favicon.svg')
def serve_favicon_svg():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.svg', mimetype='image/svg+xml')

if __name__ == '__main__':
    app.run(port=8080)
