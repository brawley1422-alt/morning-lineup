(function () {
  "use strict";

  // Mobile app shell — Broadcast Package direction.
  //
  // Turns the team briefing from a scrolling document into something that
  // behaves like a broadcast: the score bug stays pinned, the section rail
  // tracks where you are, and segments cut in rather than fade up.
  //
  // Everything here is additive and mobile-only in effect: the CSS that
  // reveals .app-bug / .app-rail / .app-tabs is inside a max-width query,
  // so on desktop these observers run against elements that never display.
  // No-ops safely if any hook is missing.

  var MOBILE = window.matchMedia("(max-width: 720px)");

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  // ── Standalone (installed PWA) ────────────────────────────────────────
  // When launched from the home screen there is no browser chrome, so the
  // shell gets the status-bar inset and drops the "add to home" affordances.
  function markStandalone() {
    var standalone = false;
    try {
      standalone = (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) ||
                   ("standalone" in navigator && navigator.standalone) || false;
    } catch (e) {}
    if (standalone) document.body.classList.add("is-standalone");
  }

  // ── Score bug ─────────────────────────────────────────────────────────
  // Pinned condensed header. Appears once the masthead scrolls past, the
  // way a broadcast drops the bug in after the open.
  function initBug() {
    var bug = $(".app-bug");
    var mast = $("header.masthead");
    if (!bug || !mast) return;

    if (!("IntersectionObserver" in window)) { bug.classList.add("is-on"); return; }

    new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        bug.classList.toggle("is-on", !en.isIntersecting);
      });
    }, { rootMargin: "-8px 0px 0px 0px", threshold: 0 }).observe(mast);
  }

  // ── Section rail ──────────────────────────────────────────────────────
  // Horizontal chip rail that tracks scroll position. Replaces the stacked
  // "Sections" block, which was the strongest mobile-site tell on the page.
  function initRail() {
    var rail = $(".app-rail");
    if (!rail) return;
    var chips = $$("a", rail);
    if (!chips.length) return;

    var byId = {};
    var targets = [];
    chips.forEach(function (chip) {
      var id = (chip.getAttribute("href") || "").replace(/^#/, "");
      if (!id) return;
      var sec = document.getElementById(id);
      if (!sec) return;
      byId[id] = chip;
      targets.push(sec);
    });
    if (!targets.length) return;

    var current = null;
    function setActive(id) {
      if (id === current) return;
      current = id;
      chips.forEach(function (c) { c.classList.remove("is-active"); });
      var chip = byId[id];
      if (!chip) return;
      chip.classList.add("is-active");
      // Keep the active chip in view without yanking the whole page.
      var left = chip.offsetLeft - (rail.clientWidth / 2) + (chip.offsetWidth / 2);
      if (rail.scrollTo) rail.scrollTo({ left: left, behavior: "smooth" });
      else rail.scrollLeft = left;
    }

    if (!("IntersectionObserver" in window)) return;

    // Band across the upper-middle of the viewport: whichever section owns
    // that band is the one being read.
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) setActive(en.target.id);
      });
    }, { rootMargin: "-96px 0px -55% 0px", threshold: 0 });
    targets.forEach(function (t) { io.observe(t); });
  }

  // ── Section sheet ─────────────────────────────────────────────────────
  // Bottom sheet listing every section. Eleven sections is too many for a
  // rail alone when you know where you're going.
  function initSheet() {
    var sheet = $(".app-sheet");
    var scrim = $(".app-scrim");
    var openBtn = $('[data-app-action="sections"]');
    if (!sheet || !scrim || !openBtn) return;

    function open() {
      sheet.classList.add("is-open");
      scrim.classList.add("is-open");
      document.body.classList.add("sheet-open");
      sheet.setAttribute("aria-hidden", "false");
      var first = $("a", sheet);
      if (first) first.focus();
    }
    function close() {
      sheet.classList.remove("is-open");
      scrim.classList.remove("is-open");
      document.body.classList.remove("sheet-open");
      sheet.setAttribute("aria-hidden", "true");
    }

    openBtn.addEventListener("click", function (e) {
      e.preventDefault();
      sheet.classList.contains("is-open") ? close() : open();
    });
    scrim.addEventListener("click", close);
    $$("a", sheet).forEach(function (a) { a.addEventListener("click", close); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && sheet.classList.contains("is-open")) close();
    });
  }

  // ── Tab actions ───────────────────────────────────────────────────────
  function initTabs() {
    var top = $('[data-app-action="top"]');
    if (top) {
      top.addEventListener("click", function (e) {
        e.preventDefault();
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    }
    // Share reuses the existing masthead share button so there is one
    // implementation of the share/copy fallback, not two.
    var share = $('[data-app-action="share"]');
    if (share) {
      share.addEventListener("click", function (e) {
        e.preventDefault();
        var real = $("header.masthead .share-btn");
        if (real) real.click();
      });
    }
  }

  // ── Segment cut-ins ───────────────────────────────────────────────────
  // 180ms hard-easing slide, once per section, only on mobile and only if
  // the reader hasn't asked for reduced motion.
  function initReveal() {
    if (!MOBILE.matches) return;
    try {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    } catch (e) {}
    if (!("IntersectionObserver" in window)) return;

    var secs = $$("main > section");
    if (!secs.length) return;
    secs.forEach(function (s) { s.classList.add("app-cut"); });

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        en.target.classList.add("is-in");
        io.unobserve(en.target);
      });
    }, { rootMargin: "0px 0px -12% 0px", threshold: 0.02 });
    secs.forEach(function (s) { io.observe(s); });
  }

  function init() {
    markStandalone();
    initBug();
    initRail();
    initSheet();
    initTabs();
    initReveal();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
