document.addEventListener("DOMContentLoaded", function () {
  var form = document.getElementById("newsletter-form");
  if (!form) return;
  var message = document.getElementById("newsletter-message");

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var data = new FormData(form);

    fetch(form.action, {
      method: "POST",
      body: data,
      headers: { "Accept": "application/json" }
    })
      .then(function (response) {
        if (response.ok) {
          form.reset();
          message.textContent = "Thanks for subscribing! Check your inbox to confirm.";
          message.className = "newsletter-signup__message newsletter-signup__message--success";
        } else {
          message.textContent = "Something went wrong — please try again.";
          message.className = "newsletter-signup__message newsletter-signup__message--error";
        }
        message.hidden = false;
      })
      .catch(function () {
        message.textContent = "Something went wrong — please try again.";
        message.className = "newsletter-signup__message newsletter-signup__message--error";
        message.hidden = false;
      });
  });
});
