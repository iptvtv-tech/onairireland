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
                    message.innerHTML = "Thanks for subscribing! Download your free guides: " +
            "<a href=\"/assets/downloads/gaa-legal-streaming-guide.pdf\" target=\"_blank\" style=\"color:#38bdf8;font-weight:700;\">GAA Coverage Guide →</a> " +
            "&nbsp;|&nbsp; " +
            "<a href=\"/assets/downloads/legal-streaming-device-guide.pdf\" target=\"_blank\" style=\"color:#38bdf8;font-weight:700;\">Device Buying Guide →</a>";
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
