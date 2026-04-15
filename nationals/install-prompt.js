(function () {
  "use strict";

  // Smart install prompt — shows an installable banner to users who have
  // visited 3+ times, are on mobile, haven't already installed the PWA,
  // and haven't dismissed the banner before.
  //
  // Analytics: install_shown, install_accepted, install_dismissed, install_ignored.
  //
  // Platform handling:
  //   - Chrome / Edge / Samsung Internet: use the native beforeinstallprompt
  //     event. Button triggers the platform's install dialog.
  //   - iOS Safari: no install API. Banner shows "Tap Share → Add to Home
  //     Screen" with an illustration.
  //   - Already installed (display-mode: standalone): no banner.
  //
  // Graceful degrade: if anything fails, the banner silently does not appear.

  var MIN_VISITS = 3;
  var VISIT_KEY = "ml_visits";
  var DISMISS_KEY = "ml_install_dismissed";

  var deferredPrompt = null;

  // Capture the install event early. The browser only fires this once per
  // page load, and only if the PWA is installable. Stashing it lets us
  // trigger the install dialog later when the user clicks our button.
  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferredPrompt = e;
  });

  function track(evType, extra) {
    try {
      if (typeof window.mlTrack === "function") {
        window.mlTrack(evType, extra || {});
      }
    } catch (e) { /* noop */ }
  }

  function isStandalone() {
    try {
      if (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) return true;
      // iOS Safari legacy
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

  function bumpVisits() {
    try {
      var v = parseInt(localStorage.getItem(VISIT_KEY) || "0", 10);
      v = isNaN(v) ? 1 : v + 1;
      localStorage.setItem(VISIT_KEY, String(v));
      return v;
    } catch (e) {
      return 0;
    }
  }

  function isDismissed() {
    try { return localStorage.getItem(DISMISS_KEY) === "1"; }
    catch (e) { return false; }
  }

  function markDismissed() {
    try { localStorage.setItem(DISMISS_KEY, "1"); }
    catch (e) {}
  }

  function buildBanner(mode) {
    var banner = document.createElement("div");
    banner.className = "ml-install-banner";
    banner.setAttribute("role", "dialog");
    banner.setAttribute("aria-label", "Install Morning Lineup");

    var copy = document.createElement("div");
    copy.className = "ml-install-copy";

    var title = document.createElement("div");
    title.className = "ml-install-title";
    title.textContent = "Read every morning.";

    var detail = document.createElement("div");
    detail.className = "ml-install-detail";
    if (mode === "ios") {
      detail.textContent = "Tap the Share button below, then Add to Home Screen.";
    } else {
      detail.textContent = "Install Morning Lineup to your home screen for one-tap access.";
    }

    copy.appendChild(title);
    copy.appendChild(detail);

    var actions = document.createElement("div");
    actions.className = "ml-install-actions";

    if (mode === "native") {
      var installBtn = document.createElement("button");
      installBtn.type = "button";
      installBtn.className = "ml-install-accept";
      installBtn.textContent = "Install";
      installBtn.addEventListener("click", function () {
        if (!deferredPrompt) return;
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(function (choice) {
          if (choice.outcome === "accepted") {
            track("install_accepted", {});
          } else {
            track("install_ignored", {});
          }
          deferredPrompt = null;
          hide(banner);
        });
      });
      actions.appendChild(installBtn);
    }

    var dismissBtn = document.createElement("button");
    dismissBtn.type = "button";
    dismissBtn.className = "ml-install-dismiss";
    dismissBtn.textContent = "Not now";
    dismissBtn.setAttribute("aria-label", "Dismiss install prompt");
    dismissBtn.addEventListener("click", function () {
      markDismissed();
      track("install_dismissed", {});
      hide(banner);
    });
    actions.appendChild(dismissBtn);

    banner.appendChild(copy);
    banner.appendChild(actions);
    return banner;
  }

  function hide(banner) {
    banner.classList.remove("show");
    setTimeout(function () { if (banner.parentNode) banner.remove(); }, 400);
  }

  function maybeShow() {
    if (isStandalone()) return;
    if (isDismissed()) return;
    var visits = bumpVisits();
    if (visits < MIN_VISITS) return;

    var mode;
    if (deferredPrompt) {
      mode = "native";
    } else if (isIOSSafari()) {
      mode = "ios";
    } else {
      // Not iOS Safari, and no native prompt captured — probably desktop
      // or a browser that doesn't support install. Skip the banner.
      return;
    }

    var banner = buildBanner(mode);
    document.body.appendChild(banner);
    // Force reflow for the CSS transition
    void banner.offsetWidth;
    banner.classList.add("show");
    track("install_shown", { mode: mode });
  }

  // Wait a beat after load so the page has time to settle and
  // beforeinstallprompt has a chance to fire.
  function scheduleShow() {
    setTimeout(maybeShow, 1500);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", scheduleShow);
  } else {
    scheduleShow();
  }
})();
