document.addEventListener("DOMContentLoaded", function () {
  var quiz = document.getElementById("stream-quiz");
  if (!quiz) return;

  var answers = {};
  var steps = quiz.querySelectorAll(".stream-quiz__step");
  var resultStep = quiz.querySelector('[data-step="result"]');
  var resultText = document.getElementById("stream-quiz-result-text");
  var restartBtn = document.getElementById("stream-quiz-restart");

  function showStep(n) {
    steps.forEach(function (step) {
      step.hidden = step.getAttribute("data-step") != n;
    });
    resultStep.hidden = true;
  }

     function recommend() {
    var text = "";

    if (answers.priority === "sports") {
      text = "Since live sport is your priority, look at a licensed sports package (Sky Sports, Premier Sports, or GAA+ depending on what you follow) on top of RTÉ/TG4's free coverage. ";
    } else if (answers.priority === "movies") {
      text = "For movies and shows, a general streaming subscription (Netflix, Disney+, or Prime Video) covers most of what you're after. ";
    } else {
      text = "If you want to stay fully free, RTÉ Player, Virgin Media Player, and TG4 Player between them cover a surprising amount, with zero subscription cost. ";
    }

    if (answers.budget === "low") {
      text += "Given your budget, stick to one paid service at most and lean on the free options to fill the rest. ";
    } else if (answers.budget === "mid") {
      text += "Your budget comfortably covers one or two subscriptions together. ";
    } else {
      text += "With a flexible budget, you could reasonably run a full stack — a general service, a sports package, and Sky Stream — without much compromise. ";
    }

    var productCategory = "Streaming Services";
    if (answers.device === "need") {
      productCategory = "Devices";
      text += "Since you'll need a device too, a Fire TV Stick 4K is the easiest all-round starting point — check our device buying guide for other options.";
    } else if (answers.device === "unsure") {
      text += "If you're not sure what your current TV supports, check our smart TV guide before buying anything extra — you might not need a separate device at all.";
    } else if (answers.priority === "sports") {
      productCategory = "Sports Streaming";
      text += "Since you're already set up on a device, you're ready to just pick a service from above and sign up directly.";
    } else {
      text += "Since you're already set up on a device, you're ready to just pick the services from above and sign up directly.";
    }

    resultText.textContent = text;
    steps.forEach(function (step) { step.hidden = true; });
    resultStep.hidden = false;

    var productContainer = document.getElementById("stream-quiz-product");
    productContainer.innerHTML = "";
    fetch("/products.json")
      .then(function (r) { return r.json(); })
      .then(function (products) {
        var matches = products.filter(function (p) { return p.category === productCategory; });
        if (matches.length === 0) matches = products.filter(function (p) { return p.category === "Streaming Services"; });
        if (matches.length === 0) return;
        var pick = matches[Math.floor(Math.random() * matches.length)];
        productContainer.innerHTML =
          '<div class="stream-quiz__pick">' +
          '<img src="' + pick.image + '" alt="' + pick.name + '" loading="lazy" onerror="this.style.display=\'none\'">' +
          '<div><strong>' + pick.name + '</strong><br><span>' + pick.price + '</span><br>' +
          '<a href="' + pick.affiliate_link + '" rel="nofollow sponsored noopener" target="_blank">Check Price →</a></div>' +
          '</div>';
      })
      .catch(function () { /* silently skip the product card if this fails */ });
  }
  quiz.addEventListener("click", function (e) {
    if (!e.target.classList.contains("stream-quiz__option")) return;
    var q = e.target.getAttribute("data-q");
    var a = e.target.getAttribute("data-a");
    answers[q] = a;

    if (q === "priority") showStep(2);
    else if (q === "budget") showStep(3);
    else if (q === "device") recommend();
  });

  restartBtn.addEventListener("click", function () {
    answers = {};
    showStep(1);
  });
});
