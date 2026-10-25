# Top music rss

Pulls top ten music and offers spotify links to each. The code attempts to pull an album link from spotify.

## spotify integration

The code uses the search api to look for an album matching the results. If it can find one, it will link to it directly, like `https://open.spotify.com/album/4EshWy8AMZAg6U0FDkDbu2`. If it doesn't get a clear result it will just link to a search url that will take the user to the results so they can (hopefully) find the album, like `https://open.spotify.com/search/artist:Neil%20Young%20album:Before%20and%20After%20year:2023`. Authorizing to the spotify api is a pain. I followed [this tutorial](I followed this tutorial: https://www.youtube.com/watch?v=ZvGnvOShStI) to get the `refresh_token`.

## Secrets

This expects two secrets in the secret manager.

`REDRSS_CONFIG`, a JSON object with these keys:

- `rss_src`, the site to pull top music from eg, 'https://favorite.site/ajax.php'
- `red_api_key`, the api key for the site eg, '1ec19bb7.e4f451de62439521ec19bb73046281'
- `b64client`, b64-encoded `client_id` and `client_secret` from a spotify app eg, 'c3BhbWFmYXNmc2FnZGdsa2Rqc2xna2pkc2xna2pkc2xrZ2pzZGdzZXJnZWVlZWVlCg='
- `refresh_token`, a token to use to replace an expired api token eg, 'AQABQAiHoPL-xKUX3mmM7BK6Zf5iuV3o_R4fzFSBTMl_1Bh8tmS82HDIZrzMtYscSqfObmB_NKrKJGpQbIWW7pSZb6lYo'

For example:

```
{"rss_src": "https://favorite.site/ajax.php", "red_api_key": "...", "b64client": "...", "refresh_token": "..."}
```

`baseurl`, the site hosting this feed (this is not used for anything important; eg, 'https://spam.com/')

## Dependencies

Direct dependencies are listed in `requirements.in`. `requirements.txt` is generated from it and pins every package, including indirect ones. To add or upgrade a package, edit `requirements.in`, then regenerate the lock file with [uv](https://docs.astral.sh/uv/):

```
uv pip compile requirements.in --python-version 3.12 -o requirements.txt
```

Don't edit `requirements.txt` by hand. To bump indirect packages without changing `requirements.in`, add `--upgrade` to the command. Deploys install from `requirements.txt` only.

## Deploy

Deploy with,

```
gcloud functions deploy redrss \
--no-allow-unauthenticated \
--no-gen2 --region=northamerica-northeast1 \
--runtime=python312 --entry-point=main \
--set-secrets=REDRSS_CONFIG=REDRSS_CONFIG:latest,baseurl=baseurl:1 \
--trigger-http --project=rssboxes-382506
```

## Add to main rssboxes site

Once deployed, get the url (eg, https://northamerica-northeast1-rssboxes-382506.cloudfunctions.net/redrss) and add to `rss_config.py` in the parent directory, then redeploy rssboxes.

## Security

The cloud function is deployed privately, and cannot be invoked without authentication (`--no-allow-unauthenticated`). The main rssboxes app is configured to generate an auth token and pass it in the header when calling any `*cloudfunctions.net*` APIs.
