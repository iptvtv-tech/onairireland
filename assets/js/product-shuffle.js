// Product showcase rotation. Each showcase contains every product whose
// show_on list matches the post type; on each page load this picks a random
// set of `data-show` cards (default 3) to display and hides the rest, so all
// matching products rotate across visits. Purely presentational -- the
// underlying data still comes from one place (_data/products.yml).
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll('.product-showcase[data-shuffle="true"]').forEach(function (showcase) {
    var grid = showcase.querySelector(".product-showcase__grid");
    if (!grid) return;
    var show = parseInt(showcase.getAttribute("data-show"), 10);
    if (!(show > 0)) show = 3;
    var cards = Array.prototype.slice.call(grid.querySelectorAll(".product-card"));
    // Fisher-Yates shuffle, then re-append in the new order.
    for (var i = cards.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = cards[i]; cards[i] = cards[j]; cards[j] = tmp;
    }
    cards.forEach(function (card, index) {
      grid.appendChild(card);
      card.hidden = index >= show;
    });
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
