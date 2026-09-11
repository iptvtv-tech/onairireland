---
title: "This Week's Best Prices"
permalink: /best-prices/
layout: single
description: "Current pricing on the streaming devices and services we recommend, in one place."
excerpt: "All our recommended devices and services, in one browsable page."
seo:
  type: WebPage
last_updated: "September 2026"
---

{% include last-updated.html %}

{% include affiliate-disclosure.html %}

A single page pulling together every device and service we currently recommend, grouped by category — useful if you just want to browse and shop rather than read a full guide.

{% assign product_categories = site.data.products | map: "category" | uniq %}
{% for cat in product_categories %}
## {{ cat }}

{% include product-showcase.html category=cat title=cat limit=20 %}
{% endfor %}
