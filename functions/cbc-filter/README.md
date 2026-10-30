# CBC world news, wire stories only

A Cloudflare Worker that serves CBC's official World feed (`https://www.cbc.ca/webfeed/rss/rss-world`) with everything except straight wire copy removed.

## Filter

An item is kept when both are true:

- it has no `<dc:creator>` (byline)
- its `<category>` is exactly `News/World`

In CBC's World feed, items with no byline are AP or Reuters wire stories. Items with a byline are CBC reporting and analysis. The World feed also carries other sections (Politics, Canada, Sports, Entertainment), which the category check drops.

Kept items and the channel info are passed through unchanged.

Known gaps:

- Wire stories that name the reporter (eg, an AP obituary) are dropped.
- This relies on CBC's feed metadata, which can change without notice. The same article has been seen with different bylines and categories in different CBC feeds.
- On busy days, wire stories can be pushed out of CBC's 20-item feed, so the box may show fewer than 5 items.

## Debug

`/?debug=1` returns a plain-text list of every item in CBC's feed, marked KEEP or drop, with its byline and category. Check this first if the box fills with analysis pieces or goes empty.

## Files

- `cbc-worldnews-filter.js`, the filter, written as a Cloudflare Worker
- `index.js`, a small GCP adapter that calls the Worker code
- `wrangler.toml`, Cloudflare config
- `package.json`, GCP config (Node, ES modules, no dependencies)

The same code deploys to either platform.

## Deploy to GCP

From this directory,

```
gcloud functions deploy cbc-filter \
--no-allow-unauthenticated \
--no-gen2 --region=northamerica-northeast1 \
--runtime=nodejs22 --entry-point=main \
--trigger-http --project=rssboxes-382506
```

`nodejs22` is the newest Node runtime on 1st gen. It is deprecated 2027-04-30 and decommissioned 2027-10-31. 2nd gen urls end in `run.app`, which rssboxes does not currently send auth tokens to.

## Deploy to Cloudflare

From this directory,

```
npx wrangler deploy
```

This deploys to `https://cbc-filter.<your-subdomain>.workers.dev/`. CBC's response is cached for 5 minutes (Cloudflare only).

## Run locally

At http://localhost:8787,

```
npx wrangler dev
```

## Add to main rssboxes site

Once deployed, get the url (eg, https://northamerica-northeast1-rssboxes-382506.cloudfunctions.net/cbc-filter) and add to `rss_config.py` in the parent directory, then redeploy rssboxes.

## Security

On GCP, the function is deployed privately (`--no-allow-unauthenticated`). rssboxes sends an auth token when calling any `*cloudfunctions.net*` url. Its service account has `roles/cloudfunctions.invoker` at the project level, so no extra permissions are needed after deploy.

On Cloudflare, the worker is public and needs no auth. It only serves a filtered copy of a public feed, and holds no secrets.
