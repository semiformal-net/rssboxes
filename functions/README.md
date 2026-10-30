# functions

These functions serve rss to the rssboxes site, for feeds that need some processing before rssboxes can use them.

| Function | Platform | Access | What it does |
|---|---|---|---|
| [redrss](redrss/) | GCP Cloud Functions | private | Top music from a private source, with spotify links |
| [cbc-filter](cbc-filter/) | GCP Cloud Functions or Cloudflare Workers | private on GCP, public on Cloudflare | CBC world news, filtered to wire stories |
| [cecily-summary](cecily-summary/) | GCP Cloud Functions | private | Cecily longreads, with a one-sentence summary per item (Gemini or Claude on Vertex AI) |

Each function has a readme with deployment details.

## security

GCP functions are deployed privately (`--no-allow-unauthenticated`), and rssboxes is configured to authenticate to them. rssboxes's service account has `roles/cloudfunctions.invoker` at the project level, so a new function needs no extra permissions to be called. Functions that only reshape a public feed (eg, `cbc-filter`) can also run publicly on Cloudflare.

Making a function public (`--allow-unauthenticated`) failed with a warning in this project, most likely because of an organization policy that blocks `allUsers`. To test a private function, pass your own identity token:

```
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" <function url>
```

Check that a function is private with `gcloud functions get-iam-policy <name> --region=northamerica-northeast1 --project=rssboxes-382506`. A policy with no `allUsers` binding (eg, only an `etag`) is private.

`cecily-summary` calls a model on Vertex AI as the functions' runtime service account (the App Engine default account, `rssboxes-382506@appspot.gserviceaccount.com`, unless changed), which needs `roles/aiplatform.user` on the project. Once granted, any function running as that account can call Vertex AI. It also caches summaries in its own private bucket, with the storage role granted on that bucket only.

See details in each README.md.

## Costs

All functions are 1st gen with 256MB memory, and fit in the Cloud Functions free tier at rssboxes's traffic. The only paid usage is model calls from `cecily-summary`, estimated at about $0.10 a month, with a daily call limit that caps it near $1.25; see its README.

## Add to main rssboxes site

Once deployed, get the url (eg, https://northamerica-northeast1-rssboxes-382506.cloudfunctions.net/redrss) and add to `rss_config.py` in the parent directory, then redeploy rssboxes.
