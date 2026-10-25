# rssboxes

A simple app to pull various rss feeds and display them in boxes

Demo site: [rssboxes.semiformal.net](https://rssboxes.semiformal.net/)

## configuration

Edit the feeds in `rss_config.py`. It is just a python file.

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
