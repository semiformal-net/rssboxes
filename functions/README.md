# functions

These private functions serve rss to the rssboxes site. They are not public (ie, they access private sources, using api keys), but can serve data to rssboxes.

Each function has a readme with deployment details.

## security

In general these functions need not be exposed to the outside word. rssboxes is configured to authenticate to them. See details in the README.md files.

## Add to main rssboxes site

Once deployed, get the url (eg, https://northamerica-northeast1-rssboxes-382506.cloudfunctions.net/redrss) and add to `rss_config.py` in the parent directory, then redeploy rssboxes.
