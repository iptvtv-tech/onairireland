document.addEventListener("DOMContentLoaded", function () {
  // Lazy-load images that don't set loading themselves, EXCEPT the page hero
  // and header logo: lazy-loading those delays Largest Contentful Paint.
  document.querySelectorAll("img:not([loading])").forEach(function (img) {
    if (img.closest(".page__hero, .page__hero--overlay, .masthead, .oai-hero")) return;
    img.setAttribute("loading", "lazy");
  });
});
