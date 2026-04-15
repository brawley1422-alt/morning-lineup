(function () {
  "use strict";

  // Landing page install chip + analytics.
  //
  // The landing page itself is the CTA — masthead + trust dek, greet bar, and
  // the team-picker grid. We don't need a competing headline stripe. This
  // file wires a discreet "Add to Home Screen" chip in the footer that only
  // appears when install is actually possible, and fires a landing_view event
  // tagged with first/return variant so we can measure launch-week conversion
  // against visit count.

  var VISIT_KEY = "ml_visits";

  var deferredPrompt = null;
  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferredPrompt = e;
    var chip = document.getElementById("foot-install");
    if (chip && chip.hasAttribute("hidden")) {
      chip.textContent = "Install Morning Lineup";
      chip.hidden = false;
    }
  });

  function track(type, extra) {
    try {
      if (typeof window.mlTrack === "function") {
        window.mlTrack(type, extra || {});
      }
    } catch (e) {}
  }

  function isStandalone() {
    try {
      if (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) return true;
      if ("standalone" in navigator && navigator.standalone) return true;
    } catch (e) {}
    return false;
  }

  function isIOSSafari() {
    var ua = navigator.userAgent || "";
    var isIOS = /iPad|iPhone|iPod/.test(ua) && !window.MSStream;
    var isSafari = /Safari/.test(ua) && !/CriOS|FxiOS|EdgiOS/.test(ua);
    return isIOS && isSafari;
  }

  function readVisits() {
    try {
      var v = parseInt(localStorage.getItem(VISIT_KEY) || "0", 10);
      return isNaN(v) ? 0 : v;
    } catch (e) { return 0; }
  }

  function init() {
    if (isStandalone()) {
      track("landing_view", { variant: "standalone" });
      return;
    }

    var visits = readVisits();
    var variant = visits >= 2 ? "return" : "first";
    track("landing_view", { variant: variant });

    // First-time visitors see the greet rewritten as a welcome CTA.
    // We check that the reader name is still the default "Reader." — if
    // landing-hydrate.js has already filled in a real name, leave it alone.
    if (variant === "first") {
      var head = document.getElementById("greet-head");
      var sub = document.getElementById("greet-sub");
      var pick = document.getElementById("greet-pick");
      var reader = document.getElementById("greet-reader");
      var readerText = reader ? (reader.textContent || "").trim() : "";
      if (head && sub && (readerText === "Reader." || readerText === "")) {
        window.__mlFirstVisitGreet = true;
        head.innerHTML = 'Welcome to <span class="welcome-em">the Press Box.</span>';
        sub.innerHTML = 'A daily briefing for every MLB team <span class="g">·</span> rebuilt every morning at 6 a.m. Central';
        if (pick) pick.hidden = false;
        track("landing_cta_shown", { variant: "first" });
      }
    }

    var chip = document.getElementById("foot-install");
    if (!chip) return;

    if (deferredPrompt) {
      chip.textContent = "Install Morning Lineup";
      chip.hidden = false;
    } else if (isIOSSafari()) {
      chip.textContent = "Share → Add to Home";
      chip.hidden = false;
    } else {
      return; // no install path, leave hidden
    }

    chip.addEventListener("click", function () {
      track("landing_install_clicked", { variant: variant });
      if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(function (choice) {
          track("install_" + (choice.outcome === "accepted" ? "accepted" : "ignored"), { source: "footer_chip" });
          deferredPrompt = null;
          chip.hidden = true;
        });
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
