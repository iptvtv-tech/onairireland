document.addEventListener("DOMContentLoaded", function () {
  var form = document.getElementById("newsletter-form");
  if (!form) return;
  var message = document.getElementById("newsletter-message");
  var button = form.querySelector("button");

  function show(text, ok) {
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
