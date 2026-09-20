document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("img:not([loading])").forEach(function (img) {
    img.setAttribute("loading", "lazy");
  });
});
