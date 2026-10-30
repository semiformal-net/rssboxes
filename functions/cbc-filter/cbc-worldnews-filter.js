// CBC world news, wire stories only.
// Fetches CBC's official World feed and drops items that have a byline
// (<dc:creator>) or whose <category> is not exactly "News/World".
// In CBC's feed, items with no byline are AP/Reuters wire copy.
// Everything else in the feed is passed through unchanged.
//
//   /          filtered RSS
//   /?debug=1  plain-text list of kept and dropped items

const SOURCE = 'https://www.cbc.ca/webfeed/rss/rss-world';
const CATEGORY = 'News/World';

const tag = (xml, name) => {
  const m = xml.match(new RegExp(`<${name}[^>]*>([\\s\\S]*?)</${name}>`));
  return m ? m[1].replace(/^<!\[CDATA\[|\]\]>$/g, '').trim() : '';
};

export default {
  async fetch(request) {
    const debug = new URL(request.url).searchParams.has('debug');

    const res = await fetch(SOURCE, { cf: { cacheTtl: 300 } });
    if (!res.ok) return new Response(`CBC returned ${res.status}`, { status: 502 });
    const xml = await res.text();

    const log = [];
    const out = xml.replace(/[ \t]*<item>[\s\S]*?<\/item>\s*/g, (item) => {
      const byline = tag(item, 'dc:creator');
      const category = tag(item, 'category');
      const keep = !byline && category === CATEGORY;
      log.push(`${keep ? 'KEEP' : 'drop'} | ${(byline || '-').padEnd(20).slice(0, 20)} | ${category.padEnd(18).slice(0, 18)} | ${tag(item, 'title')}`);
      return keep ? item : '';
    });

    if (debug) {
      const kept = log.filter((l) => l.startsWith('KEEP')).length;
      return new Response(`kept ${kept} of ${log.length}\n\n${log.join('\n')}\n`, {
        headers: { 'content-type': 'text/plain; charset=utf-8' },
      });
    }

    return new Response(out, {
      headers: {
        'content-type': 'application/rss+xml; charset=utf-8',
        'cache-control': 'public, max-age=300',
      },
    });
  },
};
