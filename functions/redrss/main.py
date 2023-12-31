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

RSS_SRC=os.environ['RSS_SRC']               # eg, 'https://favorite.site/ajax.php'
RED_API_KEY=os.environ['RED_API_KEY']       # eg, '1ec19bb7.e4f451de62439521ec19bb73046281'
baseurl=os.environ['baseurl']               # eg, 'https://spam.com/'
# these are for spotify api access. I followed this tutorial: https://www.youtube.com/watch?v=ZvGnvOShStI
b64client=os.environ['b64client']           # eg, 'c3BhbWFmYXNmc2FnZGdsa2Rqc2xna2pkc2xna2pkc2xrZ2pzZGdzZXJnZWVlZWVlCg='
refresh_token=os.environ['refresh_token']   # eg, 'AQABQAiHoPL-xKUX3mmM7BK6Zf5iuV3o_R4fzFSBTMl_1Bh8tmS82HDIZrzMtYscSqfObmB_NKrKJGpQbIWW7pSZb6lYo'

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

def get_spotify_token(b64client,refresh_token):
    if not b64client or not refresh_token:
        return None
    token_response=requests.post('https://accounts.spotify.com/api/token',
                        data={'refresh_token': refresh_token, 'grant_type': 'refresh_token'},
                        headers={'content-type': 'application/x-www-form-urlencoded','Authorization': 'Basic {}'.format(b64client)})
    if not token_response.ok:
        return None
    token_response_json=token_response.json()
    if not 'access_token' in token_response_json:
        return None
    token=token_response_json['access_token']
    return token

def get_spotify_result_url(query,token):
    q_response=requests.get('https://api.spotify.com/v1/search?q={}&type=album&limit=1'.format(query),
                        headers={'Authorization': 'Bearer {}'.format(token)})
    if not q_response.ok:
        return None
    q_response_json=q_response.json()
    try:
        album_url=q_response_json['albums']['items'][0]['external_urls']['spotify']
    except:
        return None
    if not album_url.startswith('https://open.spotify.com'):
        return None
    return album_url

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

    token=get_spotify_token(b64client,refresh_token)

    for i,r in enumerate(records):
        records[i]['link']='https://open.spotify.com/search/artist:{}%20album:{}%20year:{}'.format(r['artist'],r['groupName'],r['year'])
        if token:
            query='artist:{}%20album:{}%20year:{}'.format(r['artist'],r['groupName'],r['year'])
            url=get_spotify_result_url(query,token)
            if url:
                records[i]['link']=url

    return render_template("rss.xml", records=records, releasetypes=RELEASE_TYPES, baseurl=baseurl,
                           guid='%030x' % random.randrange(16**30) )

if __name__ == "__main__":
    app.run(debug=True)
