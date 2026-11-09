# rssboxes

A simple app to pull various rss feeds and display them in boxes

Demo site: [rssboxes.semiformal.net](https://rssboxes.semiformal.net/)

## configuration

Edit the feeds in `rss_config.py`. It is just a python file.

## Hacker News feeds

Most Hacker News feeds aren't the front page, even when they say so:

- **Front page vs best.** The front page (https://news.ycombinator.com/) ranks stories by points and age, so new stories rise fast. "Best" is the top-voted stories of the past few days, which lags well behind the front page. When I checked, feeds built on "best" covered only 6 to 8 of the 30 front-page stories.
- **The official feed** (https://news.ycombinator.com/rss) is blocked for rssboxes.
- **hnrss.org** is unmaintained (last commit Oct 2023) and often returns 502s. Its `/frontpage` feed is newest first rather than in rank order, and has only 20 stories by default. None of its forks fix this.
- **Algolia's `front_page` tag** gets the right stories, but sorted by points or by date, never by HN rank. The HN API's `topstories.json` is the only source of the order.

For now rssboxes uses https://hackernews.betacat.io/feed.xml ([code](https://github.com/polyrabbit/hacker-news-digest)). It scrapes the front page in rank order and adds an AI summary of each article. It rebuilds every 20 minutes. Caveats:

- New stories can take up to about 20 minutes to appear.
- Text posts (Ask HN and similar) get a useless summary, often just "Sorry".
- It's one person's project.

If it goes away, [functions/hn-frontpage](functions/hn-frontpage/) serves the front page in rank order, without summaries.

## hosting

This is set up to run on GCP per [these instructions](https://cloud.google.com/appengine/docs/standard/python3/runtime).

run `gcloud app deploy`

This can be made to proxy behind cloudflare, or just as a simple CNAME pointer from a domain. See [here](https://gist.github.com/patmigliaccio/d559035e1aa7808705f689b20d7b3fd3)

## Dependencies

Direct dependencies are listed in `requirements.in`. `requirements.txt` is generated from it and pins every package, including indirect ones. To add or upgrade a package, edit `requirements.in`, then regenerate the lock file with [uv](https://docs.astral.sh/uv/):

```
uv pip compile requirements.in --python-version 3.14 -o requirements.txt
```

Don't edit `requirements.txt` by hand. To bump indirect packages without changing `requirements.in`, add `--upgrade` to the command. Deploys install from `requirements.txt` only.

## Docker

You can run this as a docker container if you'd like. Using the included `Dockerfile`,

```
docker build -t rssboxes .
docker run -it -p 8080:8080 rssboxes
```

## Why?

I did this for fun, and maybe because I wanted a lightweight, ad-free, self-hosted [alternative to iGoogle](https://www.theguardian.com/technology/askjack/2013/nov/07/igoogle-alternatives).
