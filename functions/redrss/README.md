# Top music rss

Pulls top ten music and offers spotify links to each.

## Secrets

This expects three secrets in the secret manager:

- RSS_SRC, the site to pull top music from eg, 'https://favorite.site/ajax.php'
- RED_API_KEY, the api key for the site eg, '1ec19bb7.e4f451de62439521ec19bb73046281'
- baseurl the site hosting this feed (this is not used for anything important; eg, 'https://spam.com/')

## Deploy

Deploy with,

```
gcloud functions deploy redrss \ 
--no-allow-unauthenticated \
--no-gen2 --region=northamerica-northeast1 \
--runtime=python311 --entry-point=main \
--set-secrets=RSS_SRC=RSS_SRC:1,baseurl=baseurl:1,RED_API_KEY=RED_API_KEY:1 \
--trigger-http
```

## Add to main rssboxes site

Once deployed, get the url (eg, https://northamerica-northeast1-rssboxes-382506.cloudfunctions.net/redrss) and add to `rss_config.py` in the parent directory, then redeploy rssboxes.

## Security

The cloud function is deployed privately, and cannot be invoked without authentication (`--no-allow-unauthenticated`). The main rssboxes app is configured to generate an auth token and pass it in the header when calling any `*cloudfunctions.net*` APIs.
