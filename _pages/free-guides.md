---
title: "Free Guides to Legal Streaming in Ireland"
permalink: /free-guides/
layout: single
description: "Get three free PDF guides from On Air Ireland by email: getting started with legal streaming, watching GAA legally, and choosing a streaming device."
excerpt: "Three free PDF guides, sent straight to your inbox."
seo:
  type: WebPage
header:
  overlay_image: /assets/images/teasers/streaming-8.jpg
  overlay_filter: 0.5
  teaser: /assets/images/teasers/streaming-8.jpg
  og_image: /assets/images/social-home.jpg
  image_description: "A living room TV showing a streaming app home screen"
---

{% if site.newsletter_enabled %}
Three free guides from On Air Ireland, written in plain English and covering licensed, legal services only. Enter your email and we'll send you all three.

<div class="newsletter-signup">
  <h2 class="newsletter-signup__title">Send me the free guides</h2>
  <p class="newsletter-signup__desc">You'll get a confirmation email first. Click the link in it and your guides arrive straight after, followed by one newsletter a month with price changes and new guides. Unsubscribe any time. See our <a href="/privacy-policy/">privacy policy</a>.</p>
  <form class="newsletter-signup__form js-newsletter-form" action="{{ site.newsletter_form_action }}" method="POST">
    <input type="email" name="EMAIL" placeholder="you@example.com" required aria-label="Email address" autocomplete="email">
    <input type="text" name="email_address_check" value="" tabindex="-1" autocomplete="off" aria-hidden="true" style="display:none">
    <input type="hidden" name="locale" value="en">
    <button type="submit">Send me the guides</button>
  </form>
  <p class="newsletter-signup__message" hidden></p>
</div>

## What's in the guides

**The Irish Streaming Starter Guide.** Every legal streaming service in Ireland and what it costs, where to watch live sport, three example monthly budgets, and which device to buy. 8 pages, prices checked October 2026.

**Watching GAA Legally in Ireland.** Who shows which games on RTÉ, TG4 and GAA+, what GAA+ costs, and how to get it on your TV. 8 pages.

**Choosing the Right Streaming Device.** Fire TV, Google TV, Apple TV or your smart TV: which one suits your home, how to set it up, and how to stop buffering. 8 pages.
{% else %}
Three free guides from On Air Ireland, written in plain English and covering licensed, legal services only.

- **[The Irish Streaming Starter Guide (PDF)](/assets/downloads/irish-streaming-starter-guide.pdf)**: every legal service and its price, live sport, budgets and devices
- **[Watching GAA Legally in Ireland (PDF)](/assets/downloads/gaa-legal-streaming-guide.pdf)**: RTÉ, TG4 and GAA+ coverage and costs
- **[Choosing the Right Streaming Device (PDF)](/assets/downloads/legal-streaming-device-guide.pdf)**: which device suits your home and how to set it up
{% endif %}

## More from On Air Ireland

- [Sport on TV this week](/sport-on-tv/): updated every Thursday
- [Streaming prices in Ireland](/streaming-prices/): every service in one table
- [What will my streaming cost?](/streaming-cost-calculator/): pick your services, see the total
- [Start here](/start-here/): three steps to a legal streaming setup
- [Watch on YouTube](https://www.youtube.com/@onairireland)
- [Follow us on X @onairireland](https://x.com/onairireland){% if site.whatsapp_channel_url and site.whatsapp_channel_url != "" %}
- [Follow us on WhatsApp]({{ site.whatsapp_channel_url }}){% endif %}
