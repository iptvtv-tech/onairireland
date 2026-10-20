---
title: "Search"
permalink: /search/
layout: single
description: "Search On Air Ireland's guides on legal streaming services, devices, and installation."
excerpt: "Search all our guides."
seo:
  type: WebPage
header:
  overlay_image: /assets/images/pages/site-hero-hero.webp
  overlay_image_small: /assets/images/pages/site-hero-hero-800.webp
  teaser: /assets/images/pages/site-hero-teaser.webp
  image_description: Minimalist living room with a wall-mounted flat-screen TV and wooden console
  overlay_filter: 0.5
  og_image: /assets/images/social-home.jpg
---

<div class="site-search">
  <input type="search" aria-label="Search guides" id="search-input" class="site-search__input" placeholder="Search guides (e.g. 'Fire TV Stick', 'GAA', 'TV licence')...">
  <ul id="search-results" class="site-search__results"></ul>
</div>

<script src="https://cdn.jsdelivr.net/npm/simple-jekyll-search@1.10.0/dest/simple-jekyll-search.min.js" integrity="sha384-UN+lyciv8Ta643YxZ9sY2tdTSmk3KE61Qq84ZIXG9NRTbD9+NFXy38m9h6Exxx3n" crossorigin="anonymous"></script>
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
