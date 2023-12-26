from flask import Flask, redirect, url_for, render_template # requires flask>=2.1
from flask_caching import Cache
import functions_framework
import requests
import html
import random
import os

#cache = Cache(config={'DEBUG':True, 'CACHE_TYPE': 'SimpleCache')
app = Flask(__name__)
#cache.init_app(app)

RSS_SRC=os.environ['RSS_SRC']           # eg, 'https://favorite.site/ajax.php'
RED_API_KEY=os.environ['RED_API_KEY']   # eg, '1ec19bb7.e4f451de62439521ec19bb73046281'
baseurl=os.environ['baseurl']           # eg, 'https://spam.com/'

if not baseurl.endswith('/'):
    baseurl=baseurl+'/'

RELEASE_TYPES={'1':'Album','3':'Soundtrack','5':'EP','6':'Anthology','7':'Compilation','9':'Single','11':'Live album','13':'Remix','14':'Bootleg','15':'Interview','16':'Mixtape','17':'Demo','18':'Concert Recording','19':'DJ Mix','21':'Unknown'}

def cleanuphtml(records):
    for r,q in enumerate(records):
        for i in ['groupName','artist']:
            if records[r][i]:
                records[r][i] = html.unescape( records[r][i] )
        if records[r]['tags']:
            records[r]['tags'] = [ html.unescape( t ) for t in records[r]['tags'] ]
    return records

#@app.route("/")
#@cache.cached(timeout=21600) # 24hr cache
@functions_framework.http
def main(request):

    response=requests.post(RSS_SRC + '?action=top10',
                        data={'type': 'torrents', 'limit': 10},
                        headers={'Content-Type':'application/json','Authorization': RED_API_KEY})
    j=response.json()
    colnames=['Cover','Album','Artist','Year','Tags','releaseType']
    records=j['response'][0]['results']
    records=cleanuphtml(records)
    return render_template("rss.xml", records=records, releasetypes=RELEASE_TYPES, baseurl=baseurl,
                           guid='%030x' % random.randrange(16**30) )

if __name__ == "__main__":
    app.run(debug=True)
