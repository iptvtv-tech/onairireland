---
title: "Search"
permalink: /search/
layout: single
description: "Search On Air Ireland's guides on legal streaming services, devices, and installation."
excerpt: "Search all our guides."
seo:
  type: WebPage
header:
  overlay_image: /assets/images/teasers/streaming-8.jpg
  overlay_filter: 0.5
  teaser: /assets/images/teasers/streaming-8.jpg
  og_image: /assets/images/social-home.jpg
  image_description: "A living room TV showing a streaming app home screen"
---

<div class="site-search">
  <input type="search" aria-label="Search guides" id="search-input" class="site-search__input" placeholder="Search guides (e.g. 'Fire TV Stick', 'GAA', 'TV licence')...">
  <ul id="search-results" class="site-search__results"></ul>
</div>

<script src="https://cdn.jsdelivr.net/npm/simple-jekyll-search@1.10.0/dest/simple-jekyll-search.min.js"></script>
<script>
  SimpleJekyllSearch({
    searchInput: document.getElementById('search-input'),
    resultsContainer: document.getElementById('search-results'),
    json: '{{ "/search.json" | relative_url }}',
    searchResultTemplate: '<li class="site-search__result"><a href="{url}"><strong>{title}</strong><br><span>{excerpt}</span></a></li>',
    noResultsText: '<li class="site-search__no-results">No results found — try a different term.</li>',
    limit: 15,
    fuzzy: false
  });
</script>
