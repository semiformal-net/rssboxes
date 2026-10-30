// GCP Cloud Functions entry point. Wraps the Cloudflare Worker so the same
// filter code runs on both platforms.
import worker from './cbc-worldnews-filter.js';

export const main = async (req, res) => {
  const r = await worker.fetch(new Request(`http://local${req.url}`));
  res
    .status(r.status)
    .set('content-type', r.headers.get('content-type') || 'text/plain')
    .send(await r.text());
};
