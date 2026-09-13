// Shuffles the order of product cards within each showcase on every page
// load, so returning visitors (and different visitors) don't always see
// the same product first. Purely presentational — the underlying data
// still comes from one place (_data/products.yml).
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".product-card, .archive__item").forEach(function (el) {
    observer.observe(el);
  });

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
});