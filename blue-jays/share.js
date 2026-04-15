(function () {
  "use strict";

  // Share button handler — wires `.share-btn` in the masthead to the Web
  // Share API on mobile with a clipboard-copy fallback on desktop.
  // Fires `share_click` analytics events via window.mlTrack.
  //
  // Graceful degrade: if neither share nor clipboard APIs are available,
  // a tiny prompt shows the URL selected so the user can copy manually.

  function showToast(msg) {
    var existing = document.getElementById("ml-toast");
    if (existing) existing.remove();
    var toast = document.createElement("div");
    toast.id = "ml-toast";
    toast.textContent = msg;
    toast.setAttribute("role", "status");
    toast.setAttribute("aria-live", "polite");
    document.body.appendChild(toast);
    // Force reflow so the CSS transition fires
    void toast.offsetWidth;
    toast.classList.add("show");
    setTimeout(function () {
      toast.classList.remove("show");
      setTimeout(function () { if (toast.parentNode) toast.remove(); }, 400);
    }, 2200);
  }

  function fallbackPrompt(url) {
    try { window.prompt("Copy this link:", url); }
    catch (e) { /* noop */ }
  }

  function track(extra) {
    try {
      if (typeof window.mlTrack === "function") {
        window.mlTrack("share_click", extra || {});
      }
    } catch (e) { /* noop */ }
  }

  function getShareData() {
    return {
      title: document.title || "The Morning Lineup",
      text: "The Morning Lineup — daily briefing",
      url: location.href,
    };
  }

  function handleClick(ev) {
    ev.preventDefault();
    var data = getShareData();
    // Prefer the native share sheet on mobile.
    if (navigator.share) {
      navigator.share(data).then(function () {
        track({ method: "native" });
      }).catch(function () {
        // User cancelled or share failed — no toast.
      });
      return;
    }
    // Desktop fallback: copy to clipboard + toast.
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(data.url).then(function () {
        showToast("Link copied to clipboard");
        track({ method: "clipboard" });
      }).catch(function () {
        fallbackPrompt(data.url);
        track({ method: "prompt" });
      });
      return;
    }
    fallbackPrompt(data.url);
    track({ method: "prompt" });
  }

  function attach() {
    var btns = document.querySelectorAll(".share-btn");
    for (var i = 0; i < btns.length; i++) {
      btns[i].addEventListener("click", handleClick);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", attach);
  } else {
    attach();
  }
})();
