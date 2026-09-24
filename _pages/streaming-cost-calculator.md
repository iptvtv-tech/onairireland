---
title: "What Will My Streaming Cost? Irish Calculator"
permalink: /streaming-cost-calculator/
layout: single
description: "Tick the streaming services you pay for and see your monthly and yearly total in euro, plus simple ways Irish households can pay less."
excerpt: "Tick what you pay for. See the monthly and yearly total, and where you could save."
seo:
  type: WebPage
header:
  overlay_image: /assets/images/teasers/streaming-8.jpg
  overlay_filter: 0.5
  teaser: /assets/images/teasers/streaming-8.jpg
  og_image: /assets/images/social-home.jpg
  image_description: "A living room TV showing a streaming app home screen"
---

Pick the plan you have (or are thinking about) for each service. The total updates as you go. Prices are the standard Irish rates from our [streaming prices tracker](/streaming-prices/) and don't include introductory offers.

<div id="cost-calc" class="cost-calc" data-prices='{{ site.data.prices | jsonify | escape }}'>
  <noscript><p>The calculator needs JavaScript. You can see every price on the <a href="/streaming-prices/">streaming prices tracker</a>.</p></noscript>
  <div class="cost-calc__services" id="cost-calc-services"></div>
  <div class="cost-calc__total" aria-live="polite">
    <div><span class="cost-calc__label">Per month</span><span class="cost-calc__amount" id="cost-calc-month">€0.00</span></div>
    <div><span class="cost-calc__label">Per year</span><span class="cost-calc__amount" id="cost-calc-year">€0.00</span></div>
  </div>
  <ul class="cost-calc__tips" id="cost-calc-tips"></ul>
  <button type="button" class="cost-calc__reset" id="cost-calc-reset">Clear all</button>
</div>

<script src="{{ '/assets/js/cost-calculator.js' | relative_url }}" defer></script>

## Free services to add at no cost

RTÉ Player, Virgin Media Play and TG4 Player are free. You need a TV licence (€160 a year) if you have a TV that can pick up broadcast channels, whatever apps you use. See [do you need a TV licence to stream?]({% post_url 2026-09-07-tv-licence-streaming-ireland %})

## Ways to pay less

- **Rotate, don't stack.** Keep one or two services at a time and switch when you've finished what you wanted to watch. You can cancel most monthly plans any time.
- **Pay yearly for the ones you keep.** Disney+, Prime and Hayu cost less over a year on an annual plan.
- **Check what your TV or broadband package already includes.** Some Sky and Virgin Media packages include Netflix, and many Sky packages include HBO Max.
- **Take the ads plan.** Where there is one, it's usually the cheapest way in.

Not sure which services you need? Take the [three-question quiz](/quiz/).
