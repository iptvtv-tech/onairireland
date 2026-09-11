---
title: "Search"
permalink: /search/
layout: single
description: "Search On Air Ireland's guides on legal streaming services, devices, and installation."
excerpt: "Search all our guides."
seo:
  type: WebPage
---

<div class="site-search">
  <input type="text" id="search-input" class="site-search__input" placeholder="Search guides (e.g. 'Fire TV Stick', 'GAA', 'TV licence')...">
  <ul id="search-results" class="site-search__results"></ul>
</div>

<script src="https://cdn.jsdelivr.net/npm/simple-jekyll-search@latest/dest/simple-jekyll-search.min.js"></script>
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
