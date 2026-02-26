---
name: giphy
description: Search and share GIFs using Giphy API. Use for finding viral memes, reactions, and trending GIFs.
metadata:
  openclaw:
    emoji: 🎬
    requires:
      bins: []
    install:
      - id: npm
        kind: npm
        package: giphy-api
        label: Install giphy-api (npm)
    env:
      - GIPHY_API_KEY=your_api_key_here
---

# Giphy GIF Search

Search Giphy for GIFs and memes.

## Setup

1. Get a free Giphy API key at: https://developers.giphy.com/dashboard/
2. Set the environment variable:
   ```bash
   export GIPHY_API_KEY=your_api_key_here
   ```

## Usage

### CLI script (easiest)
```bash
./skills/giphy/scripts/giphy-search "penguin meme"
./skills/giphy/scripts/giphy-search "viral meme" 10
```

### With npm package
```javascript
const giphy = require('giphy-api')('YOUR_API_KEY');

// Search
giphy.search('penguin meme', function(err, res) {
  console.log(res.data[0].images.original.url);
});

// Trending
giphy.trending(function(err, res) {
  console.log(res.data);
});
```

## Available GIFs

Search using the CLI script:
```bash
./skills/giphy/scripts/giphy-search "penguin meme"
./skills/giphy/scripts/giphy-search "depressed penguin"
./skills/giphy/scripts/giphy-search "viral meme"
```
