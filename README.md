# rssboxes

A simple nodejs app (my first!) to pull various rss feeds and display them in boxes

Edit the feeds in `index.js`

Demo site: [rssboxes.semiformal.net](https://rssboxes.semiformal.net/)

## hosting

This is set up to run on GCP per [these instructions](https://cloud.google.com/appengine/docs/standard/nodejs/building-app).

run `gcloud app deploy`

This can be made to proxy behind cloudflare, or just as a simple CNAME pointer from a domain. See [here](https://gist.github.com/patmigliaccio/d559035e1aa7808705f689b20d7b3fd3)
