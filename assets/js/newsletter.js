document.addEventListener("DOMContentLoaded", function () {
  // 1. On articles, copy the signup box from the footer template into the
  //    middle of the article (before a heading about halfway down).
  var tpl = document.getElementById("newsletter-inline-template");
  var content = document.querySelector(".page__content");
  if (tpl && content && "content" in tpl) {
    var headings = Array.prototype.filter.call(content.querySelectorAll("h2"), function (h) {
      // skip headings inside FAQ/related/product blocks
      return h.parentElement === content;
    });
    if (headings.length >= 3) {
      var target = headings[Math.floor(headings.length / 2)];
      target.parentNode.insertBefore(tpl.content.cloneNode(true), target);
    }
  }

  // 2. Wire up every signup form on the page (footer + in-article).
  var forms = document.querySelectorAll(".js-newsletter-form");
  Array.prototype.forEach.call(forms, function (form) {
    var box = form.parentElement;
    var message = box.querySelector(".newsletter-signup__message");
    var button = form.querySelector("button");

    function show(text, ok) {
      if (!message) return;
      message.textContent = text;
      message.className = "newsletter-signup__message newsletter-signup__message--" + (ok ? "success" : "error");
      message.hidden = false;
    }

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (button) button.disabled = true;

      // Sends the signup to MailerLite (Newsletter group, double opt-in).
      fetch(form.action, { method: "POST", body: new FormData(form) })
        .then(function (response) {
          return response.json().catch(function () { return {}; }).then(function (data) {
            return { ok: response.ok, data: data };
          });
        })
        .then(function (res) {
          if (res.ok && res.data && res.data.success !== false) {
            form.reset();
            show("Almost done! Check your inbox and click the link to confirm your subscription. Your free guides arrive straight after.", true);
          } else {
            show("That didn't work. Please check your email address and try again.", false);
          }
        })
        .catch(function () {
          show("Something went wrong. Please try again in a moment.", false);
        })
        .then(function () {
          if (button) button.disabled = false;
        });
    });
  });
});
