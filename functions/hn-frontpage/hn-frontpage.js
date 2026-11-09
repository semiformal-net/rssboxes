// Hacker News front page, in HN's ranked order, as RSS.
// Gets the ranked story ids from the official HN API (Firebase), then the
// story details from Algolia in one request, and puts them back in HN order.
// The result is cached in memory for 30 minutes. If a refresh fails, the
// last good copy is served instead.

const TOP_STORIES = 'https://hacker-news.firebaseio.com/v0/topstories.json';
const ALGOLIA = 'https://hn.algolia.com/api/v1/search';
const HN_ITEM = 'https://news.ycombinator.com/item?id=';
const COUNT = 30;
const CACHE_MS = 30 * 60 * 1000;
const TIMEOUT_MS = 10 * 1000;

let cache = { at: 0, xml: '' };

const esc = (s) => String(s ?? '')
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

const getJSON = async (url) => {
  const res = await fetch(url, { signal: AbortSignal.timeout(TIMEOUT_MS) });
  if (!res.ok) throw new Error(`${new URL(url).hostname} returned ${res.status}`);
  return res.json();
};

const buildFeed = async () => {
  const ids = (await getJSON(TOP_STORIES)).slice(0, COUNT);
  const tags = `(story,poll,job),(${ids.map((id) => `story_${id}`).join(',')})`;
  const { hits } = await getJSON(`${ALGOLIA}?tags=${encodeURIComponent(tags)}&hitsPerPage=${COUNT}`);

  const byId = new Map(hits.map((h) => [Number(h.objectID), h]));
  const items = ids.map((id) => byId.get(id)).filter(Boolean).map((h) => {
    const permalink = HN_ITEM + h.objectID;
    return `    <item>
      <title>${esc(h.title)}</title>
      <link>${esc(h.url || permalink)}</link>
      <comments>${esc(permalink)}</comments>
      <guid isPermaLink="false">${esc(h.objectID)}</guid>
      <pubDate>${new Date(h.created_at).toUTCString()}</pubDate>
    </item>`;
  });
  if (!items.length) throw new Error('no stories found');

  return `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Hacker News: Front Page</title>
    <link>https://news.ycombinator.com/</link>
    <description>Hacker News front page, in ranked order</description>
${items.join('\n')}
  </channel>
</rss>
`;
};

export default {
  async fetch() {
    if (Date.now() - cache.at > CACHE_MS) {
      try {
        cache = { at: Date.now(), xml: await buildFeed() };
      } catch (err) {
        if (!cache.xml) return new Response(`upstream error: ${err.message}`, { status: 502 });
        // keep serving the stale copy
      }
    }
    return new Response(cache.xml, {
      headers: {
        'content-type': 'application/rss+xml; charset=utf-8',
        'cache-control': 'public, max-age=300',
      },
    });
  },
};
