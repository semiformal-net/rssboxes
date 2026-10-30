# Cecily, with one-line summaries

A Cloud Function (Node) that serves the [Cecily](https://cecily-feed.nfshost.com/cecily.xml) feed with each item's description replaced by a one-sentence summary.

Cecily's `<description>` holds the whole article, starting with a byline (`Author | Publication | Date | U`). rssboxes shows the first sentence of that, which is usually the byline or site boilerplate.

## TODO

- Disable Claude Haiku 5.5 in Model Garden (Google Cloud console), unless retrying the quota request. It was enabled for testing, but this project's quota request was denied, so it's unused.

## How it works

- Fetches the Cecily feed (5 items a day).
- For each item, sends the title, byline and first 1500 words to a model on Vertex AI (Gemini 3.1 Flash-Lite by default), asking for one sentence.
- If an item has under 40 words of text, it also fetches the article page and uses its `og:description`.
- If the model can't tell what the piece is about (it answers `NONE`), the original description is kept.
- Everything else in the feed is passed through unchanged.

## Cache

Each item is summarized once. Results are kept in two places:

- In memory, for as long as the function instance lives.
- In the Cloud Storage bucket `rssboxes-382506-cecily-summary`, one small JSON file per item under `summaries/`, so a cold start reads them back instead of calling the model.

"No summary" results are cached too, so an item the model can't summarize isn't sent again. Failed model calls aren't cached, and are retried on the next request.

The bucket's lifecycle rule (`lifecycle.json`) deletes files 3 days after they're written. Cloud Storage applies lifecycle rules once a day or so, so files can last up to a day longer. If an item is still in the feed after its file is deleted, it's summarized again.

If the bucket can't be read or written, the function logs a warning and carries on with the in-memory cache only.

## Cost limit

The function makes at most `MAX_CALLS_PER_DAY` model calls per UTC day (default 30), across all instances. The count is kept in the bucket as `counters/YYYY-MM-DD.json`, and the lifecycle rule deletes old counters too. Items over the limit keep their original description, and show `skipped, daily limit reached` in debug output.

Each call sends at most about 3,000 tokens and gets at most 400 back, so costs at most about $0.0014 on Gemini 3.1 Flash-Lite ($0.0005 on Claude Haiku 5.5). At 30 a day, model spend can't go much over $1.25 a month. A normal day uses 5 calls.

Failed calls count toward the limit, so a broken model (eg, quota errors) stops being retried after 30 attempts until the next UTC day. To reset today's count, delete the counter:

```
gcloud storage rm gs://rssboxes-382506-cecily-summary/counters/$(date -u +%F).json
```

If the bucket is unavailable, each instance keeps its own count, so the limit is per instance.

Google Cloud has no hard spending cap for Vertex AI. Two other guards:

- **Quota.** Vertex AI's per-minute request quota limits how fast a model can be called. Gemini models have a default quota. Partner models like Claude Haiku may start at 0, which fails every call with `429 RESOURCE_EXHAUSTED`.
- **Budget alert.** A billing budget emails you as spend passes thresholds. It doesn't stop spending.

## Model and cost

The model is set by the `MODEL` env var:

- `gemini-3.1-flash-lite` (default), with thinking set to minimal. $0.25 / $1.50 per million tokens in / out. Listed for retirement no earlier than May 2027; check the [model lifecycle page](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions) before then. (`gemini-2.5-flash-lite` is cheaper, but was retired on Vertex AI in October 2026.)
- Any `claude-` model, eg `claude-haiku-5-5`, with thinking off. $0.10 / $0.50 per million tokens. Needs the model enabled in Model Garden and a Vertex AI quota for it. This project's quota request for Claude Haiku was denied in October 2026, so it can't be used yet.

Each summary sends about 2,200 tokens and gets about 40 back: roughly $0.0006 on Gemini 3.1 Flash-Lite, $0.00024 on Claude Haiku 5.5. With the bucket cache, that's about 5 summaries a day, or roughly $0.10 a month on Gemini. Bucket storage and reads cost well under a cent a month.

Other settings: `GOOGLE_CLOUD_LOCATION` (default `global`), `CACHE_BUCKET`, and `MAX_CALLS_PER_DAY`.

The function authenticates to Vertex AI and Cloud Storage as its runtime service account. There is no API key.

## Debug

`/?debug=1` returns a plain-text list of items, where each summary came from (`memory`, `stored` in the bucket, or `new` with the number of words sent), and the summary.

## Files

- `index.js`, the function (Node, ES modules)
- `package.json` and `package-lock.json`, with three dependencies: `@google/genai` (Gemini), `@anthropic-ai/vertex-sdk` (Claude) and `@google-cloud/storage`
- `lifecycle.json`, the bucket's delete-after-3-days rule
- `.gcloudignore`, keeps `node_modules` and docs out of the upload

To upgrade a dependency, change its version in `package.json` and run `npm install` to update the lock file.

## Run locally

To test without Google Cloud, call `setClient(client, bucket)` with stand-ins: `client.models.generateContent` (Gemini) or `client.messages.create` (Claude) returns a response, and `bucket.file(name)` has `download()` and `save()`. Pass `null` as the bucket to turn off the bucket cache.

To call Vertex AI and the bucket for real, `gcloud auth application-default login` first, then run it with [functions-framework](https://www.npmjs.com/package/@google-cloud/functions-framework):

```
npx @google-cloud/functions-framework --target=main
```

## One-time setup

Enable Vertex AI:

```
gcloud services enable aiplatform.googleapis.com --project=rssboxes-382506
```

To use Claude instead of Gemini (optional):

- Enable the model: in the Google Cloud console, open Model Garden, find Claude Haiku 5.5, and click Enable. This accepts Anthropic's terms for the project.
- Request a per-minute quota for it, eg 10 requests a minute, in the console under IAM & Admin > Quotas, filtering for `base_model:anthropic-claude-haiku`. Or:

```
gcloud beta quotas preferences create \
--service=aiplatform.googleapis.com --project=rssboxes-382506 \
--quota-id=GlobalOnlinePredictionRequestsPerMinutePerProjectPerBaseModel \
--dimensions=base_model=anthropic-claude-haiku \
--preferred-value=10 --preference-id=cecily-haiku-rpm \
--email=YOUR_EMAIL
```

- Once granted, add `MODEL=claude-haiku-5-5` to `--set-env-vars` and redeploy.

Optionally, set a budget alert for the project. Find the billing account, then create the budget:

```
gcloud billing projects describe rssboxes-382506 \
--format='value(billingAccountName)'

gcloud billing budgets create --billing-account=ACCOUNT_ID \
--display-name=rssboxes --budget-amount=5USD \
--filter-projects=projects/rssboxes-382506 \
--threshold-rule=percent=0.5 --threshold-rule=percent=1.0
```

Gen1 functions run as the App Engine default service account unless set otherwise. Check with:

```
gcloud functions describe cecily-summary --region=northamerica-northeast1 \
--project=rssboxes-382506 --format='value(serviceAccountEmail)'
```

Give that account access to Vertex AI:

```
gcloud projects add-iam-policy-binding rssboxes-382506 \
--member=serviceAccount:rssboxes-382506@appspot.gserviceaccount.com \
--role=roles/aiplatform.user
```

Create the cache bucket, private, in the same region as the function, then add the lifecycle rule (from this directory):

```
gcloud storage buckets create gs://rssboxes-382506-cecily-summary \
--project=rssboxes-382506 --location=northamerica-northeast1 \
--uniform-bucket-level-access --public-access-prevention

gcloud storage buckets update gs://rssboxes-382506-cecily-summary \
--lifecycle-file=lifecycle.json
```

Let the service account read and write files in that bucket only:

```
gcloud storage buckets add-iam-policy-binding gs://rssboxes-382506-cecily-summary \
--member=serviceAccount:rssboxes-382506@appspot.gserviceaccount.com \
--role=roles/storage.objectUser
```

## Deploy

From this directory,

```
gcloud functions deploy cecily-summary \
--no-allow-unauthenticated \
--no-gen2 --region=northamerica-northeast1 \
--runtime=nodejs22 --entry-point=main --timeout=60s \
--set-env-vars=GOOGLE_CLOUD_PROJECT=rssboxes-382506,GOOGLE_CLOUD_LOCATION=global \
--trigger-http --project=rssboxes-382506
```

`nodejs22` is the newest Node runtime on 1st gen. It is deprecated 2027-04-30 and decommissioned 2027-10-31. 2nd gen urls end in `run.app`, which rssboxes does not currently send auth tokens to.

To test, pass your own identity token:

```
curl -s -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
'https://northamerica-northeast1-rssboxes-382506.cloudfunctions.net/cecily-summary?debug=1'
```

## Add to main rssboxes site

Replace the Cecily url in `rss_config.py` in the parent directory with https://northamerica-northeast1-rssboxes-382506.cloudfunctions.net/cecily-summary, then redeploy rssboxes.

## Security

The function is deployed privately (`--no-allow-unauthenticated`). rssboxes sends an auth token when calling any `*cloudfunctions.net*` url, and its service account has `roles/cloudfunctions.invoker` at the project level.

The cache bucket is private (public access prevention on) and holds only summaries of public articles. The storage role is granted on that bucket only, though the App Engine default account often also has the project-wide Editor role, which covers all buckets.

Article pages are only fetched over http(s) by hostname; IP-literal and internal hostnames are refused. Article text is passed to the model as data, and the output is capped at one line of 300 characters.
