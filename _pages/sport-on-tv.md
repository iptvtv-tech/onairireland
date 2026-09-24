---
title: "Sport on TV This Week in Ireland"
permalink: /sport-on-tv/
layout: single
description: "This week's big live sport in Ireland and where to watch it legally: GAA, rugby, football, golf and racing, with free-to-air games marked."
excerpt: "The week's big games, and the legal place to watch each one."
seo:
  type: WebPage
header:
  overlay_image: /assets/images/teasers/streaming-8.jpg
  overlay_filter: 0.5
  teaser: /assets/images/teasers/streaming-8.jpg
  og_image: /assets/images/social-home.jpg
  image_description: "A living room TV showing a streaming app home screen"
---

{% assign wk = site.data.sport_week %}
{% if wk.events and wk.events.size > 0 %}
<p class="sport-week__range">{{ wk.week_start | date: "%A %-d %B" }} to {{ wk.week_end | date: "%A %-d %B %Y" }} · Updated every Thursday · Times are Irish time</p>

<p class="sport-week__legend"><span class="sport-week__free">FREE</span> = on a free-to-air channel or free app (RTÉ, Virgin Media, TG4)</p>

{% assign days = wk.events | group_by_exp: "e", "e.date | date: '%Y-%m-%d'" %}
{% for day in days %}
<h2 class="sport-week__day">{{ day.items[0].date | date: "%A %-d %B" }}</h2>
<ul class="sport-week__list">
{% for e in day.items %}
  <li class="sport-week__item">
    <span class="sport-week__time">{{ e.time }}</span>
    <span class="sport-week__main"><strong>{{ e.event }}</strong> <span class="sport-week__comp">{{ e.sport }} · {{ e.competition }}</span></span>
    <span class="sport-week__watch">{% if e.free %}<span class="sport-week__free">FREE</span> {% endif %}{{ e.watch }} <a href="{{ e.source }}" rel="noopener" target="_blank" class="sport-week__src" aria-label="Source for {{ e.event }}">source</a></span>
  </li>
{% endfor %}
</ul>
{% endfor %}

Schedules change, especially for GAA and when broadcasters swap games at short notice. Check the broadcaster's own listing on the day.
{% else %}
<div class="notice--info">
<p><strong>This week's listings are on the way.</strong> We publish the week's big live sport, and the legal place to watch each game, every Thursday.</p>
<p>In the meantime, our guides cover where to watch each sport all season:</p>
</div>
{% endif %}

## Where to watch each sport, all season

- [GAA: every championship game and where it's shown](/gaa/)
- [Premier League football in Ireland]({% post_url 2026-09-13-where-to-watch-premier-league-football-legally-in-ireland %})
- [Champions League]({% post_url 2026-09-15-where-to-watch-the-uefa-champions-league-legally-in-ireland %})
- [United Rugby Championship]({% post_url 2026-09-16-where-to-watch-the-united-rugby-championship-legally-in-ireland %}) and [Six Nations]({% post_url 2026-09-11-how-to-watch-six-nations-rugby-legally-in-ireland %})
- [All sports streaming guides](/sports-streaming/)

{% if site.whatsapp_channel_url and site.whatsapp_channel_url != "" %}
<p class="sport-week__whatsapp"><a class="btn btn--success" href="{{ site.whatsapp_channel_url }}" target="_blank" rel="noopener">Get match-day alerts on our WhatsApp Channel</a></p>
{% endif %}
