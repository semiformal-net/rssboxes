const express = require('express');
const Parser = require('rss-parser');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.static('public'));
app.use('/favicon.ico', express.static('public/favicon.ico'));
app.set('views', __dirname + '/views');
app.set('view engine', 'ejs');

const RSS_FEEDS = [
  'https://www.yahoo.com/news/rss',
  'https://feeds.a.dj.com/rss/RSSWorldNews.xml',
  'http://feeds.bbci.co.uk/news/video_and_audio/world/rss.xml',
  'http://rss.cbc.ca/lineup/canada.xml',
  'https://cdn.feedcontrol.net/8/1114-wioSIX3uu8MEj.xml',
  'http://news.ycombinator.com/rss',
  'http://feed.torrentfreak.com/Torrentfreak/',
  'https://motherboard.vice.com/en_us/rss',
  'http://feeds.feedburner.com/Mobilesyrup',
  'https://www.producthunt.com/feed?category=undefined',
  'http://feeds.wired.com/wired/index',
  'http://krebsonsecurity.com/feed/',
  'https://mshibanami.github.io/GitHubTrendingRSS/daily/all.xml',
  'https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml',
  'https://noted.lol/rss/'
];

app.get('/', async (req, res) => {
  try {
    const parser = new Parser();
    const promises = RSS_FEEDS.map((url) => parser.parseURL(url));
    const feeds = await Promise.all(promises);
    const news = feeds.map((feed) => ({
      title: feed.title,
      items: feed.items.slice(0, 5).map((item) => ({
        title: item.title,
        link: item.link,
      })),
    }));
    res.render('index', { news });
  } catch (err) {
    console.error(err);
    res.status(500).send(err.message);
  }
});

app.listen(PORT, () => console.log(`Server listening on port ${PORT}...`));
