from flask import Flask, render_template, jsonify, send_from_directory
import feedparser
import html
from html.parser import HTMLParser
from io import StringIO
import requests
import re
import os
# service-to-service auth
import google.auth.transport.requests
import google.oauth2.id_token


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

    # Fetch the RSS feed using the proxy server
    if not ( (feed_number >= 1) and ( feed_number <= len(rss_feed_urls) ) ):
        return jsonify({'success': False, 'error': 'feed index out of range: {}'.format(feed_number)})
    rss_feed_url = rss_feed_urls[feed_number - 1]
    if not rss_feed_url.startswith('http'):
        return jsonify({'success': False, 'error': 'Bad url: {}'.format(rss_feed_url)})
    headers={'user-agent': 'Mozilla/5.0 (X11; Linux i686; rv:109.0) Gecko/20100101 Firefox/120.0','accept': '*/*'}

    # if the url contains cloudfunctions.net then get an auth token
    # and add it to the header when requesting
    if 'cloudfunctions.net' in rss_feed_url:
        print('Debug: calling auth')
        auth_req = google.auth.transport.requests.Request()
        id_token = google.oauth2.id_token.fetch_id_token(auth_req, rss_feed_url)
        headers["Authorization"]= f"Bearer {id_token}"
        print('Debug: auth {}'.format(f"Bearer {id_token}")) # dont do this


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
        if not 'title' in entry.keys():
            return jsonify({'success': False, 'error': 'Feed missing title key'})
        if not 'link' in entry.keys():
            return jsonify({'success': False, 'error': 'Feed missing url key'})
        if 'summary' in entry.keys():
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


