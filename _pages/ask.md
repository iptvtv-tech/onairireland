---
title: "Ask Us a Streaming Question"
permalink: /ask/
layout: single
description: "Stuck with a streaming app, device or bill? Ask On Air Ireland. We answer by email, and common questions become new guides."
excerpt: "Stuck with an app, a device or a bill? Ask us."
seo:
  type: WebPage
header:
  overlay_image: /assets/images/teasers/streaming-8.jpg
  overlay_filter: 0.5
  teaser: /assets/images/teasers/streaming-8.jpg
  og_image: /assets/images/social-home.jpg
  image_description: "A living room TV showing a streaming app home screen"
---

Can't find the answer in our guides? Ask us. We read every question, reply by email when we can, and turn the most common ones into new guides (without your name).

We only help with legal services. We can't help with unofficial IPTV boxes, "loaded" sticks or VPNs.

<form id="ask-form" class="ask-form" novalidate>
  <label for="ask-topic">What's it about?</label>
  <select id="ask-topic" name="topic">
    <option>A streaming app (RTÉ Player, NOW, Netflix, GAA+...)</option>
    <option>A device (Fire TV, smart TV, Apple TV...)</option>
    <option>Where to watch a game, show or film</option>
    <option>Prices and saving money</option>
    <option>Something on this site is wrong or out of date</option>
    <option>Something else</option>
  </select>
  <label for="ask-device">What do you watch on? (optional)</label>
  <input id="ask-device" name="device" type="text" placeholder="e.g. Samsung TV from 2019, Fire TV Stick 4K">
  <label for="ask-question">Your question</label>
  <textarea id="ask-question" name="question" rows="6" required placeholder="Tell us what you're trying to do and what happens"></textarea>
  <button type="submit" class="btn btn--primary">Open in my email app</button>
  <p class="ask-form__note">This opens your own email app with the question filled in, addressed to <strong>hello@iptvirelandtv.com</strong>. Nothing is sent or stored until you press send there. If nothing opens, email us directly at that address.</p>
</form>

<script>
document.addEventListener("DOMContentLoaded", function () {
  var form = document.getElementById("ask-form");
  if (!form) return;
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var q = form.question.value.trim();
    if (!q) { form.question.focus(); return; }
    var body = q + "\n\n" + (form.device.value.trim() ? "Watching on: " + form.device.value.trim() + "\n" : "") + "Sent from " + location.href;
    window.location.href = "mailto:hello@iptvirelandtv.com?subject=" +
      encodeURIComponent("Question: " + form.topic.value) + "&body=" + encodeURIComponent(body);
  });
});
</script>

## Before you ask

- [Why is my streaming app buffering?]({% post_url 2026-09-11-why-is-my-streaming-app-buffering-common-fixes %})
- [All troubleshooting guides](/troubleshooting/)
- [Search the site](/search/)
