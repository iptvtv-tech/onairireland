document.addEventListener("DOMContentLoaded", function () {
  var banner = document.getElementById("cookie-consent");
  if (!banner) return;

  var acceptButton = document.getElementById("cookie-accept");
  var declineButton = document.getElementById("cookie-decline");
  var settingsButton = document.getElementById("cookie-settings");

  function readChoice() {
    try {
      return window.localStorage.getItem("oai-cookie-consent");
    } catch (error) {
      return null;
    }
  }

  function saveChoice(value) {
    try {
      window.localStorage.setItem("oai-cookie-consent", value);
    } catch (error) {
      // Keep the consent banner usable when storage is unavailable.
    }
  }

  function loadGoatCounter() {
    if (document.querySelector("script[data-oai-goatcounter]")) return;

    var script = document.createElement("script");
    script.async = true;
    script.src = "https://gc.zgo.at/count.js";
    script.setAttribute("data-goatcounter", "https://onairireland.goatcounter.com/count");
    script.setAttribute("data-oai-goatcounter", "true");
    document.head.appendChild(script);
  }

  function loadGoogleAnalytics() {
    var gaId = banner.getAttribute("data-ga-id");
    if (!gaId || document.querySelector("script[data-oai-google-analytics]")) return;

    var script = document.createElement("script");
    script.async = true;
    script.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(gaId);
    script.setAttribute("data-oai-google-analytics", "true");
    document.head.appendChild(script);

    window.dataLayer = window.dataLayer || [];
    window.gtag = function () {
      window.dataLayer.push(arguments);
    };
    // The site runs no ads, so Google's advertising storage stays off: accepting
    // analytics sets only the _ga cookies, not the _gcl_au ad cookie.
    window.gtag("consent", "default", {
      ad_storage: "denied",
      ad_user_data: "denied",
      ad_personalization: "denied",
      analytics_storage: "granted"
    });
    window.gtag("js", new Date());
    window.gtag("config", gaId, {
      anonymize_ip: true,
      allow_google_signals: false,
      allow_ad_personalization_signals: false
    });
  }

  function loadAnalytics() {
    loadGoatCounter();
    loadGoogleAnalytics();
  }

  var choice = readChoice();
  if (choice === "accepted") {
    banner.hidden = true;
    loadAnalytics();
  } else if (choice === "declined") {
    banner.hidden = true;
  } else {
    banner.hidden = false;
  }

  if (acceptButton) {
    acceptButton.addEventListener("click", function () {
      saveChoice("accepted");
      banner.hidden = true;
      loadAnalytics();
    });
  }

  // Remove Google cookies (_ga, _ga_<id>, and any _gcl_ ad cookie set before
  // ad storage was turned off) when consent is withdrawn.
  function clearAnalyticsCookies() {
    var host = window.location.hostname;
    var domains = ["", host, "." + host.replace(/^www\./, "")];
    document.cookie.split(";").forEach(function (cookie) {
      var name = cookie.split("=")[0].trim();
      if (!/^(_ga(_|$)|_gcl_)/.test(name)) return;
      domains.forEach(function (domain) {
        document.cookie = name + "=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/" +
          (domain ? "; domain=" + domain : "");
      });
    });
  }

  if (declineButton) {
    declineButton.addEventListener("click", function () {
      var hadAccepted = readChoice() === "accepted";
      saveChoice("declined");
      clearAnalyticsCookies();
      banner.hidden = true;
      // Reload after revocation so newly loaded analytics scripts are removed.
      if (hadAccepted) window.location.reload();
    });
  }

  // The footer's cookie-settings link lets visitors change their choice.
  if (settingsButton) {
    settingsButton.addEventListener("click", function (event) {
      if (event && event.preventDefault) event.preventDefault();
      banner.hidden = false;
    });
  }
});
