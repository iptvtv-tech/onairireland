---
title: "All Guides"
permalink: /guides/
layout: single
description: "Every On Air Ireland guide in one place: topic hubs, set-up guides, fixes, reviews, news, plus the price tracker, calculator and quiz."
excerpt: "Every topic, tool and guide on the site."
seo:
  type: WebPage
header:
  overlay_image: /assets/images/teasers/streaming-8.jpg
  overlay_filter: 0.5
  teaser: /assets/images/teasers/streaming-8.jpg
  og_image: /assets/images/social-home.jpg
  image_description: "A living room TV showing a streaming app home screen"
---

## Popular topics

- [GAA on TV and streaming](/gaa/)
- [Netflix in Ireland](/netflix/)
- [NOW and Sky](/now-and-sky/)
- [Virgin Media TV and Virgin Media Play](/virgin-media/)
- [Amazon Fire TV](/fire-tv/)

## Tools

- [Sport on TV this week](/sport-on-tv/)
- [Streaming prices tracker](/streaming-prices/)
- [What will my streaming cost? calculator](/streaming-cost-calculator/)
- [Which streaming setup is right for you? quiz](/quiz/)
- [Best prices on streaming devices](/best-prices/)

## Browse by type

{% assign sections = "Streaming Services|/streaming-services/|Which services exist, what they cost and what's on them;Devices|/devices/|Streaming sticks, boxes and smart TVs;Installation Guides|/installation-guides/|Step-by-step set-up for each app and device;Troubleshooting|/troubleshooting/|Fixes for buffering, crashes and login problems;Sports Streaming|/sports-streaming/|Where to watch each sport legally;Watch Guides|/watch-guides/|Where to watch specific shows and films;Reviews|/reviews/|Our verdict on services and devices;News|/news/|Price changes, launches and new apps" | split: ";" %}
<ul class="guides-sections">
{% for s in sections %}{% assign sp = s | split: "|" %}
  <li><a href="{{ sp[1] }}"><strong>{{ sp[0] }}</strong></a> — {{ sp[2] }}</li>
{% endfor %}
</ul>

## Latest guides

<div class="hub-posts">
{% for post in site.posts limit: 10 %}
  {% include archive-single.html %}
{% endfor %}
</div>

Looking for something specific? [Search the site](/search/) or [ask us](/ask/).
