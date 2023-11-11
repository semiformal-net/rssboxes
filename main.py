from flask import Flask, render_template, jsonify, send_from_directory
import feedparser
import html
from html.parser import HTMLParser
from io import StringIO
import requests
import re

app = Flask(__name__)

def clean_summary(summary):
    cln=html.unescape(summary)
    cln=strip_tags(cln)
    cln=cln.strip()
    # look for the first sentence or the first line and grab that,
    #  then trim the result to 200char
    rcln=re.split(r'\n|(?<!\.[A-Z])[\.\!\?]\s',cln)[0][0:200]
    return(rcln)

class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.text = StringIO()
    def handle_data(self, d):
        self.text.write(d)
    def get_data(self):
        return self.text.getvalue()

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

app.config.from_object('rss_config')
rss_feed_urls=app.config['RSS_FEEDS']

# Route to render the main page
@app.route('/')
def index():
    return render_template('home.html', rss_feed_urls=rss_feed_urls)

# Route to fetch and return the RSS feed as JSON
@app.route('/fetch_feed/<int:feed_number>')
def fetch_feed(feed_number):
    try:
        # Fetch the RSS feed using the proxy server
        rss_feed_url = rss_feed_urls[feed_number - 1]
        response = requests.get(rss_feed_url)
        xml_string = response.text
        feed_parsed = feedparser.parse(xml_string)

        # Extract relevant information from the parsed feed
        feed_items = []
        for entry in feed_parsed.entries[:5]:  # Get the top 5 entries
            if 'summary' in entry.keys():
                s=clean_summary(entry.summary)
            else:
                s=""
            feed_items.append({
                'title': html.unescape(entry.title),
                'summary': s,
                'url': entry.link
            })

        return jsonify({'success': True, 'title': html.unescape(feed_parsed['feed']['title']), 'feed_items': feed_items})
    except Exception as e:
       return jsonify({'success': False, 'error': str(e)})

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


