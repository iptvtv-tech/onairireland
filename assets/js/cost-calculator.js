// Streaming cost calculator. Prices come from _data/prices.yml (rendered into
// data-prices on the page), so updating that file updates the calculator too.
document.addEventListener("DOMContentLoaded", function () {
  var root = document.getElementById("cost-calc");
  if (!root) return;

  var prices;
  try {
    prices = JSON.parse(root.getAttribute("data-prices"));
  } catch (e) {
    return;
  }

  var list = document.getElementById("cost-calc-services");
  var outMonth = document.getElementById("cost-calc-month");
  var outYear = document.getElementById("cost-calc-year");
  var tipsEl = document.getElementById("cost-calc-tips");
  var resetBtn = document.getElementById("cost-calc-reset");

  function euro(n) {
    return "€" + n.toFixed(2);
  }

  // Group plans by service, keeping the order in the data file.
  // Free apps are left out (they cost nothing); the TV licence stays in.
  var services = [];
  var byName = {};
  prices.forEach(function (p, i) {
    p.id = "plan-" + i;
    if (p.group === "free" && !p.yearly) return;
    if (!byName[p.service]) {
      byName[p.service] = { name: p.service, combinable: !!p.combinable, plans: [] };
      services.push(byName[p.service]);
    }
    byName[p.service].plans.push(p);
  });

  function planLabel(p) {
    var bits = [];
    if (typeof p.monthly === "number") bits.push(euro(p.monthly) + "/month");
    if (typeof p.yearly === "number") bits.push(euro(p.yearly) + "/year");
    return p.plan + " <span class=\"cost-calc__price\">" + bits.join(" or ") + "</span>";
  }

  services.forEach(function (s) {
    var box = document.createElement("fieldset");
    box.className = "cost-calc__service";
    var html = "<legend>" + s.name + "</legend>";
    var groupName = "svc-" + s.name.replace(/[^a-z0-9]/gi, "");
    var single = s.plans.length === 1;

    s.plans.forEach(function (p) {
      var type = s.combinable || single ? "checkbox" : "radio";
      var yearlyOpt = typeof p.monthly === "number" && typeof p.yearly === "number";
      html += "<label class=\"cost-calc__plan\"><input type=\"" + type + "\" name=\"" + groupName +
        "\" value=\"" + p.id + "\"> " + planLabel(p) + "</label>";
      if (yearlyOpt) {
        html += "<label class=\"cost-calc__yearly\" hidden><input type=\"checkbox\" data-yearly-for=\"" + p.id +
          "\"> Pay yearly (" + euro(p.yearly) + ")</label>";
      }
    });
    if (!s.combinable && !single) {
      html += "<label class=\"cost-calc__plan cost-calc__plan--none\"><input type=\"radio\" name=\"" + groupName +
        "\" value=\"\" checked> Don't have it</label>";
    }
    box.innerHTML = html;
    list.appendChild(box);
  });

  var planById = {};
  prices.forEach(function (p) { planById[p.id] = p; });

  function selected() {
    var out = [];
    root.querySelectorAll("input[name^='svc-']:checked").forEach(function (input) {
      if (!input.value) return;
      var p = planById[input.value];
      var yearlyBox = root.querySelector("input[data-yearly-for='" + p.id + "']");
      out.push({ plan: p, payYearly: yearlyBox ? yearlyBox.checked : typeof p.monthly !== "number" });
    });
    return out;
  }

  function has(sel, service, plan) {
    return sel.some(function (s) {
      return s.plan.service === service && (!plan || s.plan.plan === plan);
    });
  }

  function update() {
    // Show "Pay yearly" only under a ticked plan.
    root.querySelectorAll(".cost-calc__yearly").forEach(function (label) {
      var id = label.querySelector("input").getAttribute("data-yearly-for");
      var planInput = root.querySelector("input[value='" + id + "']");
      label.hidden = !planInput.checked;
      if (label.hidden) label.querySelector("input").checked = false;
    });

    var sel = selected();
    var year = 0;
    var yearlySaving = 0;
    sel.forEach(function (s) {
      var p = s.plan;
      if (s.payYearly) {
        year += p.yearly;
      } else {
        year += p.monthly * 12;
        if (typeof p.yearly === "number") yearlySaving += p.monthly * 12 - p.yearly;
      }
    });
    outYear.textContent = euro(year);
    outMonth.textContent = euro(year / 12);

    var tips = [];
    if (yearlySaving > 0.5) {
      tips.push("Paying yearly for the plans that offer it would save you about " + euro(yearlySaving) + " a year.");
    }
    if (has(sel, "Netflix", "Premium")) {
      tips.push("Netflix Standard costs €7 a month less than Premium. You only need Premium for 4K or four screens at once.");
    }
    if (has(sel, "HBO Max") && has(sel, "NOW", "Entertainment & HBO Max")) {
      tips.push("NOW Entertainment & HBO Max already includes HBO Max Basic with Ads, so you may be paying for HBO Max twice.");
    }
    if (has(sel, "NOW", "Sports")) {
      tips.push("NOW Sports is much cheaper on a 12-month offer than month to month. Check the NOW site for the current deal.");
    }
    if (sel.length >= 4) {
      tips.push("You have " + sel.length + " paid plans. Most people save by keeping two or three and rotating the rest.");
    }
    tipsEl.innerHTML = tips.map(function (t) { return "<li>" + t + "</li>"; }).join("");
    tipsEl.hidden = tips.length === 0;
  }

  root.addEventListener("change", update);
  resetBtn.addEventListener("click", function () {
    root.querySelectorAll("input").forEach(function (input) {
      input.checked = input.type === "radio" && input.value === "";
    });
    update();
  });
  update();
});
