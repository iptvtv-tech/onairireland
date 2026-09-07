// Shuffles the order of product cards within each showcase on every page
// load, so returning visitors (and different visitors) don't always see
// the same product first. Purely presentational — the underlying data
// still comes from one place (_data/products.yml).
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll('.product-showcase[data-shuffle="true"] .product-showcase__grid').forEach(function (grid) {
    var cards = Array.prototype.slice.call(grid.children);
    for (var i = cards.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      grid.appendChild(cards[j]);
      cards.splice(j, 1);
    }
    // re-append remaining in shuffled order
    cards.forEach(function (c) { grid.appendChild(c); });
  });

  // Gentle fade-in for product cards and post tiles as they scroll into view
  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });

  document.querySelectorAll(".product-card, .archive__item").forEach(function (el) {
    observer.observe(el);
  });
});
