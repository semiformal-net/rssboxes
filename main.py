from flask import Flask, render_template, request, session, redirect, url_for, send_from_directory
import asyncio
import aiohttp
import feedparser
import os
import html
from io import StringIO
from html.parser import HTMLParser
import re

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

app = Flask(__name__)

async def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

async def clean_summary(summary):
    cln=html.unescape(summary)
    cln=await strip_tags(cln)
    cln=cln.strip()
    # look for the first sentence or the first line and grab that,
    #  then trim the result to 200char
    rcln=re.split(r'\n|(?<!\.[A-Z])[\.\!\?]\s',cln)[0][0:200]
    return(rcln)

async def get_connection_pool(num_connections=10):
    connector=aiohttp.TCPConnector(ssl=False, limit=num_connections)
    session = aiohttp.ClientSession(connector=connector)
    return session

async def fetch_feed(feed_url, session):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:58.0) Gecko/20100101 Firefox/58.0"}
    #async with aiohttp.ClientSession(headers=headers) as session:
    async with session.get(feed_url) as response:
        if response.status != 200:
            raise Exception(f"Error fetching feed from {feed_url}. Server responded with status {response.status}.")
        return await response.text()

async def get_articles_and_title(feed_url,session):
    try:
        feed_data = await asyncio.wait_for(fetch_feed(feed_url,session), timeout=5)
    except asyncio.TimeoutError:
        return [{'title': 'Timed out!', 'link': feed_url}], feed_url
    feed_parsed = feedparser.parse(feed_data)
    if 'summary' in feed_parsed['entries'][0].keys():
        articles_dict=[{'title': html.unescape(entry.title), 'link': entry.link, 'summary': await clean_summary(entry.summary) } for entry in feed_parsed.entries[:5]]
    else:
        articles_dict=[{'title': html.unescape(entry.title), 'link': entry.link, 'summary': None } for entry in feed_parsed.entries[:5]]

    return articles_dict , html.unescape(feed_parsed['feed']['title'])

async def get_feed_articles(feed,session):
    try:
        articles, title = await get_articles_and_title(feed,session)
        return {
            'title': title,
            'articles': articles
        }
    except Exception as e:
        return {'title': f"Error fetching feed: {str(e)}", 'articles': [], 'summaries': []}

async def get_all_feed_articles(RSS_FEEDS, num_connections=10):
    session = await get_connection_pool(num_connections)
    tasks = [asyncio.create_task(get_feed_articles(feed, session)) for feed in RSS_FEEDS]
    results = await asyncio.gather(*tasks)
    await session.close()
    return results

app.config.from_object('rss_config')
RSS_FEEDS=app.config['RSS_FEEDS']

@app.route('/')
def get_news():
    print(RSS_FEEDS)
    feed_list = asyncio.run(get_all_feed_articles(RSS_FEEDS))
    return render_template('home.html', feeds=feed_list)

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
