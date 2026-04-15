(function () {
  "use strict";

  // First-visit welcome overlay. Appears on the landing page for users
  // who have never been here before. Three steps:
  //   1. Pick your team (grid of 30 team abbreviations)
  //   2. Install to home screen (or iOS Safari instructions)
  //   3. "Come back tomorrow" — plain acknowledgement, no email required
  //
  // Dismissal persists via localStorage.ml_onboarded = "1". Skip / close
  // at any step also marks the visitor as onboarded.
  //
  // Analytics: onboard_shown, onboard_team_picked, onboard_install_accepted,
  // onboard_install_ignored, onboard_dismissed, onboard_completed.

  var ONBOARDED_KEY = "ml_onboarded";
  var TEAM_KEY = "ml_team";

  var deferredPrompt = null;
  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferredPrompt = e;
  });

  function isOnboarded() {
    try { return localStorage.getItem(ONBOARDED_KEY) === "1"; }
    catch (e) { return false; }
  }

  function markOnboarded() {
    try { localStorage.setItem(ONBOARDED_KEY, "1"); }
    catch (e) {}
  }

  function setTeam(slug) {
    try { localStorage.setItem(TEAM_KEY, slug); }
    catch (e) {}
  }

  function track(evType, extra) {
    try {
      if (typeof window.mlTrack === "function") {
        window.mlTrack(evType, extra || {});
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

  // Fallback team list (slug, abbreviation) used if window.__TEAMS isn't
  // loaded yet. Real data with MLB IDs + branding comes from landing-teams.js.
  var FALLBACK_TEAMS = [
    ["angels", "LAA"], ["astros", "HOU"], ["athletics", "ATH"], ["blue-jays", "TOR"],
    ["braves", "ATL"], ["brewers", "MIL"], ["cardinals", "STL"], ["cubs", "CHC"],
    ["dbacks", "ARI"], ["dodgers", "LAD"], ["giants", "SF"], ["guardians", "CLE"],
    ["mariners", "SEA"], ["marlins", "MIA"], ["mets", "NYM"], ["nationals", "WSH"],
    ["orioles", "BAL"], ["padres", "SD"], ["phillies", "PHI"], ["pirates", "PIT"],
    ["rangers", "TEX"], ["rays", "TB"], ["red-sox", "BOS"], ["reds", "CIN"],
    ["rockies", "COL"], ["royals", "KC"], ["tigers", "DET"], ["twins", "MIN"],
    ["white-sox", "CWS"], ["yankees", "NYY"],
  ];

  var LOGO_CDN = "https://www.mlbstatic.com/team-logos/team-cap-on-dark/";

  function getTeams() {
    // Prefer the hydrated team list from landing-teams.js — it has MLB IDs,
    // full names, and colors. Fall back to the bare slug/abbr list so the
    // overlay still works if that script failed to load.
    if (window.__TEAMS && window.__TEAMS.length) {
      return window.__TEAMS.map(function (t) {
        return {
          slug: t.slug,
          abbr: t.abbreviation || t.slug.toUpperCase(),
          id: t.id,
          full: t.full_name || t.name || t.slug,
        };
      }).sort(function (a, b) { return a.full.localeCompare(b.full); });
    }
    return FALLBACK_TEAMS.map(function (t) {
      return { slug: t[0], abbr: t[1], id: null, full: t[0] };
    });
  }

  function renderStep1(card, onPicked) {
    card.innerHTML = '';
    var kicker = document.createElement("div");
    kicker.className = "ml-welcome-kicker";
    kicker.innerHTML = '<span>Morning Lineup &middot; Welcome</span><span class="step">Step 1 of 3</span>';
    var h = document.createElement("h2");
    h.textContent = "Pick your team.";
    var p = document.createElement("p");
    p.className = "sub";
    p.textContent = "We'll remember it. Click any team to open today's briefing.";
    var grid = document.createElement("div");
    grid.className = "ml-welcome-teams";
    var teams = getTeams();
    teams.forEach(function (t) {
      var a = document.createElement("a");
      a.className = "ml-welcome-team";
      a.href = "./" + t.slug + "/";
      a.setAttribute("aria-label", t.full);
      if (t.id) {
        var img = document.createElement("img");
        img.className = "ml-welcome-team-logo";
        img.src = LOGO_CDN + t.id + ".svg";
        img.alt = "";
        img.loading = "lazy";
        a.appendChild(img);
      }
      var label = document.createElement("span");
      label.className = "ml-welcome-team-abbr";
      label.textContent = t.abbr;
      a.appendChild(label);
      a.addEventListener("click", function () {
        setTeam(t.slug);
        track("onboard_team_picked", { team_slug: t.slug });
        markOnboarded();
        // Let the anchor navigate normally.
      });
      grid.appendChild(a);
    });
    var actions = document.createElement("div");
    actions.className = "ml-welcome-actions";
    var skip = document.createElement("button");
    skip.type = "button";
    skip.className = "ml-welcome-skip";
    skip.textContent = "Skip";
    skip.addEventListener("click", function () {
      track("onboard_skipped", { step: 1 });
      onPicked(true); // skipped
    });
    actions.appendChild(skip);
    card.appendChild(kicker);
    card.appendChild(h);
    card.appendChild(p);
    card.appendChild(grid);
    card.appendChild(actions);
  }

  function renderStep2(card, onDone) {
    card.innerHTML = '';
    var kicker = document.createElement("div");
    kicker.className = "ml-welcome-kicker";
    kicker.innerHTML = '<span>Morning Lineup &middot; Welcome</span><span class="step">Step 2 of 3</span>';
    var h = document.createElement("h2");
    h.textContent = "Install it.";
    var p = document.createElement("p");
    p.className = "sub";
    p.textContent = "Add Morning Lineup to your home screen so it loads instantly every morning.";

    card.appendChild(kicker);
    card.appendChild(h);
    card.appendChild(p);

    var actions = document.createElement("div");
    actions.className = "ml-welcome-actions";

    if (deferredPrompt) {
      var install = document.createElement("button");
      install.type = "button";
      install.className = "ml-welcome-accept";
      install.textContent = "Install";
      install.addEventListener("click", function () {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(function (choice) {
          if (choice.outcome === "accepted") {
            track("onboard_install_accepted", {});
          } else {
            track("onboard_install_ignored", {});
          }
          deferredPrompt = null;
          onDone();
        });
      });
      actions.appendChild(install);
    } else if (isIOSSafari()) {
      var ios = document.createElement("div");
      ios.className = "ml-welcome-ios-steps";
      ios.innerHTML = "Tap the <strong>Share</strong> button at the bottom of Safari, then choose <strong>Add to Home Screen</strong>.";
      card.appendChild(ios);
    } else {
      var p2 = document.createElement("p");
      p2.className = "sub";
      p2.textContent = "You're on desktop — bookmark this page to find it fast every morning.";
      card.appendChild(p2);
    }

    var next = document.createElement("button");
    next.type = "button";
    next.className = deferredPrompt ? "ml-welcome-skip" : "ml-welcome-accept";
    next.textContent = deferredPrompt ? "Skip" : "Next";
    next.addEventListener("click", function () {
      track("onboard_install_skipped", {});
      onDone();
    });
    actions.appendChild(next);
    card.appendChild(actions);
  }

  function renderStep3(card, onDone) {
    card.innerHTML = '';
    var kicker = document.createElement("div");
    kicker.className = "ml-welcome-kicker";
    kicker.innerHTML = '<span>Morning Lineup &middot; Welcome</span><span class="step">Step 3 of 3</span>';
    var h = document.createElement("h2");
    h.textContent = "Come back tomorrow.";
    var p = document.createElement("p");
    p.className = "sub";
    p.textContent = "Every morning by 7 AM Central. Last night's game, today's matchup, and every angle that matters.";
    var actions = document.createElement("div");
    actions.className = "ml-welcome-actions";
    var done = document.createElement("button");
    done.type = "button";
    done.className = "ml-welcome-accept";
    done.textContent = "Got it";
    done.addEventListener("click", function () {
      track("onboard_completed", {});
      onDone();
    });
    actions.appendChild(done);
    card.appendChild(kicker);
    card.appendChild(h);
    card.appendChild(p);
    card.appendChild(actions);
  }

  function showOverlay() {
    var overlay = document.createElement("div");
    overlay.className = "ml-welcome";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-label", "Welcome to Morning Lineup");

    var card = document.createElement("div");
    card.className = "ml-welcome-card";
    overlay.appendChild(card);

    function close() {
      overlay.classList.remove("show");
      setTimeout(function () { if (overlay.parentNode) overlay.remove(); }, 400);
      markOnboarded();
    }

    function goStep2() { renderStep2(card, function () { renderStep3(card, close); }); }
    function goStep1Done(skipped) {
      if (skipped) {
        track("onboard_dismissed", { at_step: 1 });
        close();
        return;
      }
      goStep2();
    }

    renderStep1(card, goStep1Done);
    document.body.appendChild(overlay);
    void overlay.offsetWidth;
    overlay.classList.add("show");
    track("onboard_shown", {});
  }

  function run() {
    // Only on the landing page — detected by absence of a team slug in
    // the path. If path is "/" or "/index.html" (or GH Pages variant
    // "/morning-lineup/" / "/morning-lineup/index.html"), we're on landing.
    var path = location.pathname || "";
    var isLanding = /\/(morning-lineup\/)?(index\.html)?$/.test(path);
    if (!isLanding) return;
    if (isOnboarded()) return;
    if (isStandalone()) { markOnboarded(); return; }
    // Delay so the landing page hero draws first, then the overlay
    // rises over it. Feels less like a pop-up, more like a welcome card.
    setTimeout(showOverlay, 900);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
