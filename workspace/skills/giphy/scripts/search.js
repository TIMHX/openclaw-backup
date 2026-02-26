const giphy = require('giphy-api')({
  apiKey: process.env.GIPHY_API_KEY
});
const query = process.argv[2];
const limit = parseInt(process.argv[3]) || 5;

if (!query) {
  console.error('Usage: giphy-search "query" [limit]');
  process.exit(1);
}

giphy.search({
  q: query,
  limit: limit
}, function (err, res) {
  if (err) {
    console.error('Error:', err.message);
    process.exit(1);
  }
  if (!res.data || res.data.length === 0) {
    console.log('No results found');
    return;
  }
  res.data.forEach(gif => {
    console.log(gif.images.original.url);
  });
});
