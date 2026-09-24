document.addEventListener("DOMContentLoaded", function () {
  var banner = document.getElementById("cookie-consent");
  if (!banner) return;

  var choice = null;
  try { choice = localStorage.getItem("oai-cookie-consent"); } catch (e) {}

  function loadAnalytics() {
    var gaId = banner.getAttribute("data-ga-id");
    if (!gaId || gaId === "") return;
    var script = document.createElement("script");
    script.async = true;
    script.src = "https://www.googletagmanager.com/gtag/js?id=" + gaId;
    document.head.appendChild(script);
    window.dataLayer = window.dataLayer || [];
    function gtag() { dataLayer.push(arguments); }
    window.gtag = gtag;
    gtag("js", new Date());
    gtag("config", gaId, { anonymize_ip: true });
  }

    if (choice === "accepted") {
    banner.hidden = true;
    loadAnalytics();
  } else if (choice !== "declined") {
    banner.hidden = false;
  }

  document.getElementById("cookie-accept").addEventListener("click", function () {
    localStorage.setItem("oai-cookie-consent", "accepted");
    banner.hidden = true;
    loadAnalytics();
  });

  document.getElementById("cookie-decline").addEventListener("click", function () {
    var hadAccepted = localStorage.getItem("oai-cookie-consent") === "accepted";
    localStorage.setItem("oai-cookie-consent", "declined");
    banner.hidden = true;
    // If analytics was running, reload so it stops for the rest of the visit.
    if (hadAccepted) window.location.reload();
  });

  // "Cookie settings" link in the footer lets visitors change their mind.
  var settings = document.getElementById("cookie-settings");
  if (settings) {
    settings.addEventListener("click", function () {
      banner.hidden = false;
    });
  }
});
