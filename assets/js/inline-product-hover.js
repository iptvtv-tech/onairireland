document.addEventListener("DOMContentLoaded", function () {
  var links = document.querySelectorAll(
    '.initial-content a[href*="amzn.to"], .initial-content a[href*="sovrn.co"], .initial-content a[href*="AFFILIATE_LINK"]'
  );
  if (!links.length) return;

  fetch("/products.json")
    .then(function (r) { return r.json(); })
    .then(function (products) {
      var tooltip = document.createElement("div");
      tooltip.className = "inline-product-hover";
      tooltip.hidden = true;
      document.body.appendChild(tooltip);

      links.forEach(function (link) {
        var match = products.find(function (p) {
          return p.affiliate_link && link.href.indexOf(p.affiliate_link) !== -1;
        });
        if (!match) return;

        link.addEventListener("mouseenter", function () {
          tooltip.innerHTML =
            '<img src="' + match.image + '" alt="' + match.name + '" onerror="this.style.display=\'none\'">' +
            '<div class="inline-product-hover__body"><strong>' + match.name + '</strong><span>' + match.price + '</span></div>';
          var rect = link.getBoundingClientRect();
          var left = Math.max(8, Math.min(rect.left, window.innerWidth - 280));
          tooltip.style.left = left + "px";
          tooltip.style.top = (rect.bottom + window.scrollY + 8) + "px";
          tooltip.hidden = false;
        });

        link.addEventListener("mouseleave", function () {
          tooltip.hidden = true;
        });
      });
    })
    .catch(function () { /* silently skip if products.json fails to load */ });
});
