document.addEventListener("DOMContentLoaded", function () {
  // 1. On articles, copy the signup box from the footer template into the
  //    middle of the article (before a heading about halfway down).
  var tpl = document.getElementById("newsletter-inline-template");
  var content = document.querySelector(".page__content");
  if (tpl && content && "content" in tpl) {
    // Only look at the article itself: stop at the FAQ / related-posts blocks.
    var body = [];
    for (var el = content.firstElementChild; el; el = el.nextElementSibling) {
      if (el.matches(".faq-section, .related-posts")) break;
      if (el.matches(".share-buttons, .sidebar__right, aside")) continue;
      body.push(el);
    }
    var isHeading = function (el) {
      return /^H[23]$/.test(el.tagName) && !/^related/i.test(el.textContent.trim());
    };
    var headings = body.filter(isHeading);
    var paragraphs = body.filter(function (el) { return el.tagName === "P"; });
    var box = tpl.content.cloneNode(true);

    if (headings.length >= 2) {
      // before the heading about halfway down
      var h = headings[Math.floor(headings.length / 2)];
      h.parentNode.insertBefore(box, h);
    } else if (paragraphs.length >= 2) {
      // after the paragraph about halfway down
      var p = paragraphs[Math.floor(paragraphs.length / 2)];
      p.parentNode.insertBefore(box, p.nextSibling);
    } else if (body.length) {
      // very short post: after the last bit of the article
      var last = body[body.length - 1];
      last.parentNode.insertBefore(box, last.nextSibling);
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

      // Sends the signup to Brevo (double opt-in). isAjax=1 makes Brevo reply with JSON.
      var url = form.action + (form.action.indexOf("?") === -1 ? "?" : "&") + "isAjax=1";
      fetch(url, { method: "POST", body: new FormData(form) })
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
