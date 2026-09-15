// Shuffles the order of product cards within each showcase on every page
// load, so returning visitors (and different visitors) don't always see
// the same product first. Purely presentational -- the underlying data
// still comes from one place (_data/products.yml).
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll('.product-showcase[data-shuffle="true"] .product-showcase__grid').forEach(function (grid) {
    var cards = Array.prototype.slice.call(grid.children);
    for (var i = cards.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      grid.appendChild(cards[j]);
      cards.splice(j, 1);
    }
    cards.forEach(function (c) { grid.appendChild(c); });
  });

  // Sitewide image fallback: if ANY image on the site fails to load
  // (missing file, broken path, not-yet-uploaded photo), swap it for the
  // placeholder graphic instead of showing a broken-image icon.
  var FALLBACK_IMAGE = "/assets/images/social-default.svg";
    document.querySelectorAll("img").forEach(function (img) {
    img.addEventListener(
      "error",
      function () {
        if (img.src.indexOf("social-default.svg") === -1) {
          img.src = FALLBACK_IMAGE;
        }
      },
      { once: true }
    );
  });

  // Accessibility safety net: fill in alt text for any image missing it
  // entirely, using the page title as a reasonable fallback description.
  // Note: this only helps real visitors/screen readers via JS -- it does
  // NOT reliably fix search-engine crawler warnings (e.g. Bing), since
  // not all crawlers execute JavaScript before evaluating the page.
  document.querySelectorAll("img:not([alt])").forEach(function (img) {
    img.setAttribute("alt", document.title || "Image");
  });
});
