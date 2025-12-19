import re
import os
import html
from io import StringIO
from html.parser import HTMLParser

from flask import Flask, render_template, jsonify, send_from_directory
import feedparser
import requests

# service-to-service auth
import google.auth.transport.requests
import google.oauth2.id_token

app = Flask(__name__)

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

    # Mask common abbreviations so sentence splitting doesn't treat them as boundaries.
    abbrev_token = "<DOT>"
    abbreviations = (
        "Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "Sr.", "Jr.",
        "St.", "vs.", "etc.", "e.g.", "i.e.", "U.S.", "U.K.",
    )
    for abbr in abbreviations:
        pattern = re.compile(re.escape(abbr), re.IGNORECASE)
        text = pattern.sub(lambda m: m.group(0).replace(".", abbrev_token), text)

    # Use regex to split into sentences or lines
    parts = re.split(r'(?<=[.!?])\s+|\n', text)

    for part in parts:
        clean_part = part.replace(abbrev_token, ".").strip()
        if clean_part:
            return truncate_at_word_boundary(clean_part, max_length)

    # Fallback if no clean sentence found
    return truncate_at_word_boundary(text.replace(abbrev_token, "."), max_length)

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

app.config.from_object('rss_config')
rss_feed_urls=app.config['RSS_FEEDS']

# Route to render the main page
@app.route('/')
def index():
    return render_template('home.html', rss_feed_urls=rss_feed_urls)

# Route to fetch and return the RSS feed as JSON
@app.route('/fetch_feed/<int:feed_number>')
def fetch_feed(feed_number):

    # Fetch the RSS feed using the proxy server
    if not ( (feed_number >= 1) and ( feed_number <= len(rss_feed_urls) ) ):
        return jsonify({'success': False, 'error': 'feed index out of range: {}'.format(feed_number)})
    rss_feed_url = rss_feed_urls[feed_number - 1]
    URL_REGEX = re.compile(r'^https?://[^\s/$.?#].[^\s]*$', re.IGNORECASE)
    if not URL_REGEX.match(rss_feed_url):
        return jsonify({'success': False, 'error': 'Malformed URL'})
    headers={'user-agent': 'Mozilla/5.0 (X11; Linux i686; rv:109.0) Gecko/20100101 Firefox/120.0','accept': '*/*'}

    # if the url contains cloudfunctions.net then get an auth token
    # and add it to the header when requesting
    if 'cloudfunctions.net' in rss_feed_url:
        print('Debug: calling auth')
        auth_req = google.auth.transport.requests.Request()
        id_token = google.oauth2.id_token.fetch_id_token(auth_req, rss_feed_url)
        headers["Authorization"]= f"Bearer {id_token}"

    response = requests.get(rss_feed_url,headers=headers)
    if not response.ok:
        return jsonify({'success': False, 'error': 'Server returned: {}'.format(response.status_code)})
    xml_string = response.text
    if len(xml_string)<100:
        return jsonify({'success': False, 'error': 'Bad feed data (response 2short)'})
    try:
        feed_parsed = feedparser.parse(xml_string)
    except:
        return jsonify({'success': False, 'error': 'unable to parse'})

    # Extract relevant information from the parsed feed
    feed_items = []
    for entry in feed_parsed.entries[:5]:  # Get the top 5 entries
        if not 'title' in entry:
            return jsonify({'success': False, 'error': 'Feed missing title key'})
        if not 'link' in entry:
            return jsonify({'success': False, 'error': 'Feed missing url key'})
        required_keys = ['title', 'link']
        for key in required_keys:
            if key not in entry:
                return jsonify({'success': False, 'error': f'Missing expected field: {key}'})
        if 'summary' in entry:
            s=clean_summary(entry.summary)
        else:
            s=""
        feed_items.append({
            'title': html.unescape(entry.title),
            'summary': s,
            'url': html.unescape(entry.link),
        })

    return jsonify({'success': True, 'title': html.unescape(feed_parsed['feed']['title']), 'feed_items': feed_items})

@app.route('/static/<path:filename>')
def serve_static(filename):
    root_dir = os.path.dirname(os.getcwd())
    return send_from_directory(os.path.join(root_dir, 'static'), filename)

@app.route('/favicon.ico')
def serve_favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    app.run(port=8080)

