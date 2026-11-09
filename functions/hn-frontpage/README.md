# Hacker News front page, in ranked order

A Cloudflare Worker (also deployable to GCP) that serves the current Hacker News front page as RSS, in the same order as https://news.ycombinator.com/.

> **Not in use.** https://hackernews.betacat.io/feed.xml ([code](https://github.com/polyrabbit/hacker-news-digest)) does the same job, and adds a one-paragraph summary of each article. rssboxes uses it instead. This function is kept in case betacat goes away. See "Hacker News feeds" in the main README.

It replaces `https://hnrss.org/frontpage`, which often returns 502s, sorts by age rather than rank, and returns only 20 of the 30 stories by default.

## How it works

1. Gets the ranked story ids from the official HN API, `https://hacker-news.firebaseio.com/v0/topstories.json`, and keeps the first 30.
2. Gets the details for those stories from Algolia in one request, `https://hn.algolia.com/api/v1/search?tags=(story,poll,job),(story_<id>,...)`.
3. Puts the stories back in HN's order.

Each item links to the article (or to the HN page for Ask HN and other text posts), with the HN discussion in `<comments>`. There is no description.

## Why not Algolia's `front_page` tag?

`https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=30` returns the stories on the front page in one request, without `topstories.json`. It returns the right stories, but not in HN's order.

Checked on 2026-11-09:

- Both lists had the same 30 stories. (A third-party guide found 29 of 30 in one check, so the lists can briefly differ.)
- No story had the same rank in both. Ranks differed by up to 25 places.
- Algolia's `/search` sorts by relevance, then points, then comments. With no query, that means points, highest first (859 down to 12 in that check). `/search_by_date` sorts newest first. Neither one sorts the way HN does.
- HN also takes age into account. Stories an hour old with 19 to 42 points were at HN #3, #4 and #20, but near the bottom of Algolia's list. The story with the most points (859, 18 hours old) was HN #26 and Algolia #1.

So `topstories.json` is still needed for the order. Algolia only fills in the details.

To compare the two lists yourself (needs jq 1.6 or newer),

```
jq -rn \
 --argjson top "$(curl -s https://hacker-news.firebaseio.com/v0/topstories.json)" \
 --argjson fp "$(curl -s 'https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=30')" \
 '($fp.hits|map(.objectID|tonumber)) as $ids
  | ($fp.hits|INDEX(.objectID)) as $by
  | (["HN","ALG","Δ","PTS","AGE","TITLE"]|@tsv),
    ($top[:30]|to_entries[]
     | .key as $i | .value as $id | $by[$id|tostring] as $h
     | if $h then ($ids|index($id)) as $a | ($a-$i) as $d
         | [$i+1, $a+1, (if $d>0 then "+" else "" end)+($d|tostring),
            $h.points, "\(((now-$h.created_at_i)/3600)|floor)h", $h.title[:40]]
       else [$i+1,"-","-","-","-","(not in front_page)"] end
     | @tsv)' \
| column -t -s$'\t'
```

## Cache

The feed is kept in memory for 30 minutes. If a refresh fails, the last good copy is served. The cache is per instance, so a cold start fetches again, and returns a 502 if the APIs are down at that moment.

## Files

- `hn-frontpage.js`, the feed, written as a Cloudflare Worker
- `index.js`, a small GCP adapter that calls the Worker code
- `wrangler.toml`, Cloudflare config
- `package.json`, GCP config (Node, ES modules, no dependencies)

## Deploy to GCP

From this directory,

```
gcloud functions deploy hn-frontpage \
--no-allow-unauthenticated \
--no-gen2 --region=northamerica-northeast1 \
--runtime=nodejs22 --entry-point=main \
--trigger-http --project=rssboxes-382506
```

## Deploy to Cloudflare

From this directory,

```
npx wrangler deploy
```

## Run locally

At http://localhost:8787,

```
npx wrangler dev
```

## Add to main rssboxes site

Once deployed, replace `https://hnrss.org/frontpage?description=0` in `rss_config.py` in the parent directory with the function url (eg, https://northamerica-northeast1-rssboxes-382506.cloudfunctions.net/hn-frontpage), then redeploy rssboxes.
