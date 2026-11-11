---
noindex: true # thin or title no longer matches the facts; kept for readers and links (11 Nov 2026)
sitemap: false
title: "NOW Ireland Prices 2026: What Changed and What Didn't"
excerpt: "We found no 2026 price rise announced by NOW Ireland. The 2026 change was HBO Max joining NOW Entertainment. Current prices and what it means for your bill."
description: "We found no 2026 price rise announced by NOW Ireland. The 2026 change was HBO Max joining NOW Entertainment. Current prices and what it means for your bill."
last_updated: 2026-11-10
last_checked: 2026-11-10
categories:
  - News
tags:
  - news
header:
  overlay_image: /assets/images/posts/now-ireland-raises-prices-for-2026-hero.webp
  overlay_image_small: /assets/images/posts/now-ireland-raises-prices-for-2026-hero-800.webp
  teaser: /assets/images/posts/now-ireland-raises-prices-for-2026-teaser.webp
  og_image: /assets/images/posts/now-ireland-raises-prices-for-2026-og.jpg
  caption: 'Photo: [RDNE Stock project](https://www.pexels.com/photo/emotional-man-sitting-on-couch-watching-a-video-on-tablet-6414642/) on [Pexels](https://www.pexels.com)'
seo:
  type: Article
toc: true
draft_generated: true
affiliate_links: false
faqs:
  - question: "Did NOW raise its prices in Ireland in 2026?"
    answer: "We couldn't find a 2026 price rise on NOW Ireland's own website, help pages or terms. NOW's 2026 change was adding HBO Max Basic with Ads to the Entertainment membership from 26 March 2026."
  - question: "Did existing NOW Entertainment members pay more for HBO Max?"
    answer: "No, not straight away. NOW says members with Entertainment on 26 March 2026 were moved to Entertainment & HBO Max at no extra cost. Members on a Monthly Saver keep their price until the minimum term ends, then pay the regular Entertainment & HBO Max price unless they cancel."
  - question: "How much notice does NOW give before a price rise?"
    answer: "NOW's Irish terms say it aims to give at least 30 days' notice of a change that materially disadvantages you, and you can cancel within that notice period."
---

{% include last-updated.html %}

{% include share-buttons.html %}

We couldn't find a 2026 price rise from NOW in Ireland. NOW's own Irish pages show no announced increase, and its standard monthly prices on 10 November 2026 were the same as when we checked them on 7 October 2026. The real 2026 change was HBO Max joining the Entertainment membership in March.

*Correction (10 November 2026): an earlier version of this article said NOW had confirmed price rises in Ireland for 2026. We couldn't confirm that on NOW's Irish website, help pages or terms, so we've rewritten it to cover what NOW actually changed.*

## At a glance

- **Price rise in 2026:** none found on NOW Ireland's own pages at the time of writing (November 2026).
- **What changed:** from 26 March 2026, NOW Entertainment includes HBO Max Basic with Ads, and NOW sells a new **Entertainment & HBO Max** membership.
- **Existing members:** moved over at no extra cost, according to [NOW's help page](https://www.nowtv.com/ie/help/article/levelling-up-entertainment-membership).
- **Monthly Saver members:** your price stays the same until your minimum term ends, then rises to the regular Entertainment & HBO Max price unless you cancel.

## NOW's prices in Ireland now

{% assign now_plans = site.data.prices | where: "service", "NOW" %}
These are NOW's standard monthly prices on [NOW's Irish membership page](https://www.nowtv.com/ie/membership) at the time of writing (November 2026):

| Membership | Standard price a month |
|---|---|
{% for p in now_plans %}| {{ p.plan }} | {% include euro.html amount=p.monthly %} |
{% endfor %}

New customers usually get an introductory price on a minimum term, for example on Entertainment for six months or on the Sports Saver bundle for 12 months. After that, the standard price applies unless you cancel. Our [streaming prices tracker](/streaming-prices/) has every current Irish price, and the [streaming cost calculator](/streaming-cost-calculator/) adds up a bill.

## What happened with HBO Max

On 11 February 2026 Sky [announced](https://www.skygroup.sky/en-gb/article/sky-brings-together-netflix-disney-hbo-max-and-hayu-into-one-single-subscription-exclusively-on-sky) that HBO Max Basic with Ads would be packaged with NOW Entertainment from 26 March 2026, "at no extra cost for existing customers". The announcement gave UK prices only.

NOW's Irish help page explains what happened to Irish members:

- If you had an active Entertainment membership on 26 March 2026, NOW moved you to **Entertainment & HBO Max** automatically, and your monthly payments stayed the same.
- If you were on the Entertainment **Monthly Saver**, your payments stay the same until the end of your minimum term. After that, {% assign now_hbo = site.data.prices | where: "plan", "Entertainment & HBO Max" | first %}NOW says you'll pay the regular price of {% include euro.html amount=now_hbo.monthly %} a month unless you cancel.
- On bundles such as Entertainment and Cinema, only the Entertainment part changed.

{% assign now_ent = site.data.prices | where: "plan", "Entertainment" | where: "service", "NOW" | first %}
So if your Monthly Saver ends and you see {% include euro.html amount=now_hbo.monthly %} rather than {% include euro.html amount=now_ent.monthly %}, that's the move to Entertainment & HBO Max, not a general price rise. Plain Entertainment without HBO Max is still on NOW's membership page at {% include euro.html amount=now_ent.monthly %} a month. For more on HBO Max in Ireland, see [our HBO Max guide](/news/is-hbo-max-coming-to-ireland/).

## If NOW does raise prices

NOW's [Irish terms](https://www.nowtv.com/ie/terms) say it may increase prices at any time, but it aims to tell you at least 30 days before a change that materially disadvantages you. If you object, you can cancel within that notice period, and a monthly membership can be cancelled at any time before your next month starts. If you get a notice, read it for the date and your options. We'll update our [price tracker](/streaming-prices/) when NOW's Irish prices change.

**Related guides:** [Sky Stream vs NOW](/streaming-services/sky-stream-vs-now-ireland/) · [Sky and NOW hub](/now-and-sky/) · [Sky Ireland's 2026 changes](/news/sky-ireland-unveils-new-streaming-price-plan-for-2026/)

Sources: [NOW Ireland memberships](https://www.nowtv.com/ie/membership) (checked 10 November 2026) · [NOW help: Entertainment Membership & HBO Max](https://www.nowtv.com/ie/help/article/levelling-up-entertainment-membership) (checked 10 November 2026) · [NOW help: Sports Membership](https://help.nowtv.com/ie/article/sports-membership) (checked 10 November 2026) · [NOW Ireland terms of use](https://www.nowtv.com/ie/terms) (checked 10 November 2026) · [Sky Group press release](https://www.skygroup.sky/en-gb/article/sky-brings-together-netflix-disney-hbo-max-and-hayu-into-one-single-subscription-exclusively-on-sky) (11 February 2026)

{% include faq-section.html %}

{% include related-posts.html %}

{% include whatsapp-cta.html %}
