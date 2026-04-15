(function () {
  "use strict";

  // Per-section collapse state for Morning Lineup team pages.
  // Graceful degradation: if JS fails, sections stay in whatever default
  // state the server rendered. If localStorage is blocked, toggles still
  // work in-session but don't persist across reloads.

  var STORAGE_KEY = "ml_section_state_v1";

  // Smart defaults when the reader has no stored preference.
  // "Above the fold" (team, tonight's game, stretch, slate) starts open;
  // reference sections (pressbox, farm, division, league, history) start
  // collapsed. Readers who prefer the old all-open behavior will get it
  // with one click per section, persisted from then on.
  var DEFAULT_STATE = {
    team:     true,
    scout:    true,
    matchup:  true,
    pulse:    true,
    today:    true,
    pressbox: false,
    farm:     false,
    div:      false,
    league:   false,
    history:  false,
  };

  function readState() {
    try {
      var raw = window.localStorage && window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return {};
      var parsed = JSON.parse(raw);
      return (parsed && typeof parsed === "object") ? parsed : {};
    } catch (e) {
      return {};
    }
  }

  function writeState(state) {
    try {
      if (window.localStorage) {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      }
    } catch (e) { /* storage blocked — in-session only */ }
  }

  function applyState(state) {
    var sections = document.querySelectorAll("main > section[id]");
    for (var i = 0; i < sections.length; i++) {
      var s = sections[i];
      var id = s.id;
      var stored = state.hasOwnProperty(id) ? state[id] : undefined;
      var wanted = (stored === undefined)
        ? (DEFAULT_STATE.hasOwnProperty(id) ? DEFAULT_STATE[id] : true)
        : !!stored;
      if (wanted) {
        s.setAttribute("open", "");
      } else {
        s.removeAttribute("open");
      }
    }
  }

  function attachToggleHandlers(state) {
    var sections = document.querySelectorAll("main > section[id]");
    for (var i = 0; i < sections.length; i++) {
      var s = sections[i];
      var summary = s.querySelector(":scope > summary");
      if (!summary) continue;
      (function (section, sum) {
        sum.addEventListener("click", function (ev) {
          ev.preventDefault();
          var isOpen = section.hasAttribute("open");
          if (isOpen) {
            section.removeAttribute("open");
          } else {
            section.setAttribute("open", "");
          }
          state[section.id] = !isOpen;
          writeState(state);
        });
        // Keyboard accessibility: Enter/Space toggles, same as details
        sum.setAttribute("tabindex", "0");
        sum.setAttribute("role", "button");
        sum.addEventListener("keydown", function (ev) {
          if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            sum.click();
          }
        });
      })(s, summary);
    }
  }

  function init() {
    var state = readState();
    applyState(state);
    attachToggleHandlers(state);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
