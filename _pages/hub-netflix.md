---
title: "Netflix in Ireland: Prices, Plans and Guides"
permalink: /netflix/
layout: single
description: "Everything about Netflix in Ireland: current prices, which plan to pick, fixes when it freezes, and where to watch the biggest Netflix shows."
excerpt: "Prices, plans, fixes and what's worth watching on Netflix in Ireland."
last_updated: 2026-09-24
seo:
  type: WebPage
header:
  overlay_image: /assets/images/teasers/streaming-8.jpg
  overlay_filter: 0.5
  teaser: /assets/images/teasers/streaming-8.jpg
  og_image: /assets/images/social-home.jpg
  image_description: "A living room TV showing a streaming app home screen"
---

Netflix is one of the most popular paid streaming services in Irish homes. It has three plans, and prices went up in September 2026.

{% assign nf = site.data.prices | where: "service", "Netflix" %}
| Plan | Monthly |
|---|---|
{% for p in nf %}| {{ p.plan }} | {% include euro.html amount=p.monthly %} |
{% endfor %}

*Prices checked {{ nf[0].checked | date: "%-d %B %Y" }}. See the [streaming prices tracker](/streaming-prices/) for every service.*

New to it? Read [Netflix Ireland price changes for 2026]({% post_url 2026-09-13-netflix-ireland-price-changes-for-2026-what-you-need-to-know %}) and [Netflix keeps freezing? Try these fixes]({% post_url 2026-09-20-netflix-keeps-freezing-try-these-fixes %}).

## All our Netflix guides

{% include hub-posts.html keywords="Netflix|Squid Game|Wednesday|Stranger Things|Bridgerton" %}
