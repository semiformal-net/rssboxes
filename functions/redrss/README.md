# Top music rss

Pulls top ten music and offers spotify links to each. The code attempts to pull an album link from spotify.

## spotify integration

The code uses the search api to look for an album matching the results. If it can find one, it will link to it directly, like `https://open.spotify.com/album/4EshWy8AMZAg6U0FDkDbu2`. If it doesn't get a clear result it will just link to a search url that will take the user to the results so they can (hopefully) find the album, like `https://open.spotify.com/search/artist:Neil%20Young%20album:Before%20and%20After%20year:2023`. Authorizing to the spotify api is a pain. I followed [this tutorial](I followed this tutorial: https://www.youtube.com/watch?v=ZvGnvOShStI) to get the `refresh_token`.

## Secrets

This expects these secrets in the secret manager:

- RSS_SRC, the site to pull top music from eg, 'https://favorite.site/ajax.php'
- RED_API_KEY, the api key for the site eg, '1ec19bb7.e4f451de62439521ec19bb73046281'
- baseurl, the site hosting this feed (this is not used for anything important; eg, 'https://spam.com/')
- b64client, b64-encoded `client_id` and `client_secret` from a spotify app eg, 'c3BhbWFmYXNmc2FnZGdsa2Rqc2xna2pkc2xna2pkc2xrZ2pzZGdzZXJnZWVlZWVlCg='
- refresh_token, a token to use to replace an expired api token eg, 'AQABQAiHoPL-xKUX3mmM7BK6Zf5iuV3o_R4fzFSBTMl_1Bh8tmS82HDIZrzMtYscSqfObmB_NKrKJGpQbIWW7pSZb6lYo'

## Deploy

Deploy with,

```
gcloud functions deploy redrss \
--no-allow-unauthenticated \
--no-gen2 --region=northamerica-northeast1 \
--runtime=python311 --entry-point=main \
--set-secrets=RSS_SRC=RSS_SRC:1,baseurl=baseurl:1,RED_API_KEY=RED_API_KEY:1,b64client=b64client:1,refresh_token=refresh_token:1 \
--trigger-http
```

## Add to main rssboxes site

Once deployed, get the url (eg, https://northamerica-northeast1-rssboxes-382506.cloudfunctions.net/redrss) and add to `rss_config.py` in the parent directory, then redeploy rssboxes.

## Security

The cloud function is deployed privately, and cannot be invoked without authentication (`--no-allow-unauthenticated`). The main rssboxes app is configured to generate an auth token and pass it in the header when calling any `*cloudfunctions.net*` APIs.
