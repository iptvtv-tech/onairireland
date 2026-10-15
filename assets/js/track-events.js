// Click tracking with GoatCounter. Cookieless and no personal data, so it
// counts every visitor without needing cookie consent.
//
// Events show in the GoatCounter dashboard (tick "Show events" if hidden):
//   amazon/<page>    someone clicked an Amazon link on <page>
//                    (the link's code and text are in the title)
//   whatsapp/<page>  someone clicked "Follow on WhatsApp" on <page>
//   download/<file>  someone downloaded a free PDF guide
//   signup/<form>/<page>  Brevo accepted a newsletter or price-alert signup
//                    (sent from newsletter.js)
(function () {
  function track(path, title) {
    var gc = window.goatcounter;
    if (!gc || typeof gc.count !== "function") return; // blocked or not loaded
    gc.count({ path: path, title: title || path, event: true });
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
