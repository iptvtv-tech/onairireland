// Event tracking for GoatCounter and Google Analytics 4. Both tools are loaded
// only after a visitor accepts analytics in cookie-consent.js, so before
// consent (or after a decline) track() does nothing.
//
// Events (GoatCounter path -> GA4 event name):
//   amazon/<page>          -> affiliate_click     someone clicked an Amazon link
//                                                 (link code and text in the title)
//   whatsapp/<page>        -> whatsapp_follow     clicked "Follow on WhatsApp"
//   download/<file>        -> guide_download      downloaded a free PDF guide
//   signup/<form>/<page>   -> newsletter_signup   Brevo accepted a signup (newsletter.js)
//   calculator/<page>      -> calculator_use      first change in the cost calculator
//   quiz/<result>          -> quiz_complete       reached the quiz result (stream-quiz.js)
// GoatCounter: tick "Show events" in the dashboard. GA4: Reports > Engagement > Events.
(function () {
  var GA4_EVENTS = {
    amazon: "affiliate_click", whatsapp: "whatsapp_follow", download: "guide_download",
    signup: "newsletter_signup", calculator: "calculator_use", quiz: "quiz_complete"
  };

  // Returns true if the event was sent to at least one tool.
  function track(path, title, params) {
    var sent = false;
    var gc = window.goatcounter;
    if (gc && typeof gc.count === "function") {
      gc.count({ path: path, title: title || path, event: true });
      sent = true;
    }
    // window.gtag only exists once the visitor has accepted analytics.
    var name = GA4_EVENTS[path.split("/")[0]];
    if (name && typeof window.gtag === "function") {
      var data = { event_label: title || path, page_path: location.pathname };
      if (params) for (var k in params) if (Object.prototype.hasOwnProperty.call(params, k)) data[k] = params[k];
      window.gtag("event", name, data);
      sent = true;
    }
    return sent;
  }
  window.oaiTrack = track;

  var page = location.pathname.replace(/\/$/, "") || "/home";

  function onClick(e) {
    var a = e.target.closest && e.target.closest("a[href]");
    if (!a) return;
    var href = a.href;
    var text = (a.textContent || "").trim().replace(/\s+/g, " ").slice(0, 80);

    if (/^https?:\/\/(amzn\.to|amzn\.eu|link\.amazon|(www\.)?amazon\.(co\.uk|ie|com|de))\//i.test(href)) {
      var code = href.replace(/^https?:\/\/[^/]+\//, "").split(/[?#]/)[0];
      track("amazon" + page, code + " | " + (text || "image"));
    } else if (/whatsapp\.com\/channel\//i.test(href)) {
      track("whatsapp" + page, "Follow on WhatsApp");
    } else if (/\.pdf($|[?#])/i.test(href)) {
      var file = href.split(/[?#]/)[0].split("/").pop();
      track("download/" + file, file);
    }
  }

  // "click" covers normal clicks and keyboard Enter; "auxclick" covers
  // middle-click "open in new tab".
  document.addEventListener("click", onClick, true);
  document.addEventListener("auxclick", function (e) {
    if (e.button === 1) onClick(e);
  }, true);
})();
