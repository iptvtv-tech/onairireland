---
title: "Irish Streaming Prices Tracker"
permalink: /streaming-prices/
layout: single
description: "What Netflix, Disney+, NOW, HBO Max, Prime Video, Apple TV and GAA+ cost in Ireland today, with the date each price was last checked."
excerpt: "Every major streaming price in Ireland, in one table, with the date we last checked it."
seo:
  type: WebPage
last_updated: 2026-09-24
header:
  overlay_image: /assets/images/teasers/streaming-8.jpg
  overlay_filter: 0.5
  teaser: /assets/images/teasers/streaming-8.jpg
  og_image: /assets/images/social-home.jpg
  image_description: "A living room TV showing a streaming app home screen"
---

{% assign all_prices = site.data.prices %}
{% assign latest_check = all_prices | map: "checked" | sort | last %}

Standard prices for the main legal streaming services in Ireland, in euro, including VAT. Each row shows when the price last changed (where we know it) and the date we last confirmed it, with a link to the source.

<p class="price-tracker__stamp">Prices last checked: <strong>{{ latest_check | date: "%-d %B %Y" }}</strong></p>

Prices here are the standard rates. Many services run introductory offers for new customers, so you may pay less for the first few months. Always confirm on the provider's own site before you subscribe.

Want to add up your own bill? Try the [streaming cost calculator](/streaming-cost-calculator/).

{% assign changed = all_prices | where_exp: "p", "p.changed" | sort: "changed" | reverse %}
{% if changed.size > 0 %}
## Recent price changes

<ul class="price-tracker__changes">
{% for p in changed limit: 6 %}
  <li><strong>{{ p.service }} {{ p.plan }}</strong> is now {% if p.monthly %}{% include euro.html amount=p.monthly %} a month{% else %}{% include euro.html amount=p.yearly %} a year{% endif %} (changed {{ p.changed | date: "%-d %B %Y" }}). <a href="{{ p.url }}" rel="noopener" target="_blank">Source: {{ p.source }}</a></li>
{% endfor %}
</ul>
{% endif %}

{% assign groups = "general|Netflix, Disney+ and Prime Video;film-tv|Film, TV and entertainment;sport|Sport;free|Free services and the TV licence" | split: ";" %}
{% for g in groups %}
{% assign gparts = g | split: "|" %}
{% assign rows = all_prices | where: "group", gparts[0] %}
## {{ gparts[1] }}

<div class="price-tracker__wrap">
<table class="price-tracker">
  <thead>
    <tr><th scope="col">Service</th><th scope="col">Plan</th><th scope="col">Monthly</th><th scope="col">Yearly</th><th scope="col">Checked</th></tr>
  </thead>
  <tbody>
  {% for p in rows %}
    <tr>
      <td data-label="Service"><strong>{{ p.service }}</strong></td>
      <td data-label="Plan">{{ p.plan }}{% if p.note %}<br><small>{{ p.note }}</small>{% endif %}</td>
      <td data-label="Monthly">{% if p.monthly == 0 %}Free{% elsif p.monthly %}{% include euro.html amount=p.monthly %}{% else %}–{% endif %}</td>
      <td data-label="Yearly">{% if p.yearly %}{% include euro.html amount=p.yearly %}{% else %}–{% endif %}</td>
      <td data-label="Checked"><a href="{{ p.url }}" rel="noopener" target="_blank" title="Source: {{ p.source }}">{{ p.checked | date: "%-d %b %Y" }}</a></td>
    </tr>
  {% endfor %}
  </tbody>
</table>
</div>
{% endfor %}

## How we keep this up to date

We check every price on this page at least once a quarter, and straight away when a provider announces a change. Spotted a price that's out of date? [Tell us](/ask/) and we'll fix it.

Want to know when prices change? Join the newsletter at the bottom of this page — price rises go in the next email.
