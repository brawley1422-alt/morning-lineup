(function () {
  "use strict";
  var SC = window.Scorecard = window.Scorecard || {};

  var mainEl = null;
  var POLL_MS = 20000;
  var pollTimer = null;
  var paused = false;
  var currentModel = null;
  var currentGamePk = null;
  var lastResumeAt = 0;

  function getParams() {
    var params = {};
    var search = window.location.search.slice(1);
    if (!search) return params;
    var parts = search.split("&");
    for (var i = 0; i < parts.length; i++) {
      var kv = parts[i].split("=");
      params[decodeURIComponent(kv[0])] = decodeURIComponent(kv[1] || "");
    }
    return params;
  }

  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function isLive(model) {
    return model && model.status === "Live";
  }

  // ── Situation bar ──

  function renderSituationBar(feed) {
    if (!feed || !feed.liveData) return "";
    var ls = feed.liveData.linescore;
    var cp = feed.liveData.plays && feed.liveData.plays.currentPlay;
    if (!ls || !cp) return "";

    var inning = ls.currentInning || 0;
    var half = ls.inningHalf || "";
    var outs = ls.outs || 0;
    var balls = (ls.balls != null) ? ls.balls : 0;
    var strikes = (ls.strikes != null) ? ls.strikes : 0;

    var batter = cp.matchup && cp.matchup.batter ? cp.matchup.batter.fullName : "";
    var pitcher = cp.matchup && cp.matchup.pitcher ? cp.matchup.pitcher.fullName : "";

    var offense = ls.offense || {};
    var first = !!offense.first;
    var second = !!offense.second;
    var third = !!offense.third;

    var html = '<div class="situation-bar" id="situation-bar">';
    html += '<div class="sit-live-badge"><span class="dot"></span> LIVE</div>';
    html += '<div class="sit-inning">' + esc(half) + " " + inning + '</div>';
    html += '<div class="sit-matchup">';
    html += '<span class="sit-label">AB:</span> ' + esc(batter);
    html += ' <span class="sit-label">P:</span> ' + esc(pitcher);
    html += '</div>';
    html += '<div class="sit-count">';
    html += '<span class="sit-label">B:</span>' + balls + ' ';
    html += '<span class="sit-label">S:</span>' + strikes + ' ';
    html += '<span class="sit-label">O:</span>' + outs;
    html += '</div>';
    // Baserunner diamond
    var on = "var(--gold)", off = "var(--rule-hi)";
    html += '<svg viewBox="0 0 60 60" width="40" height="40" class="sit-diamond">' +
      '<polygon points="30,6 54,30 30,54 6,30" fill="none" stroke="var(--rule-hi)" stroke-width="1.5"/>' +
      '<circle cx="54" cy="30" r="5" fill="' + (first ? on : off) + '"/>' +
      '<circle cx="30" cy="6" r="5" fill="' + (second ? on : off) + '"/>' +
      '<circle cx="6" cy="30" r="5" fill="' + (third ? on : off) + '"/>' +
      '</svg>';
    html += '</div>';
    return html;
  }

  function updateSituationBar(feed) {
    var el = document.getElementById("situation-bar");
    var newHTML = renderSituationBar(feed);
    if (el) {
      // Replace existing bar
      var wrapper = document.createElement("div");
      wrapper.innerHTML = newHTML;
      if (wrapper.firstChild) {
        el.parentNode.replaceChild(wrapper.firstChild, el);
      }
    } else {
      // Insert after header
      var header = document.querySelector(".game-header");
      if (header && newHTML) {
        header.insertAdjacentHTML("afterend", newHTML);
      }
    }
  }

  function removeSituationBar() {
    var el = document.getElementById("situation-bar");
    if (el) el.remove();
  }

  // ── In-place diamond updates ──

  function updateScorecard(newModel) {
    if (!currentModel) return;
    var sides = ["away", "home"];

    for (var s = 0; s < sides.length; s++) {
      var side = sides[s];
      var newLineup = newModel[side].lineup;
      var oldLineup = currentModel[side].lineup;

      // Update diamonds
      for (var slot = 0; slot < newLineup.length; slot++) {
        for (var bi = 0; bi < newLineup[slot].batters.length; bi++) {
          var batter = newLineup[slot].batters[bi];
          var oldBatter = (oldLineup[slot] && oldLineup[slot].batters[bi]) || null;
          var oldAbCount = oldBatter ? oldBatter.atBats.length : 0;

          for (var a = 0; a < batter.atBats.length; a++) {
            var ab = batter.atBats[a];
            var cellId = "cell-" + side + "-" + batter.id + "-" + ab.inning;
            var cell = document.getElementById(cellId);
            if (cell && a >= oldAbCount) {
              // New at-bat — animate it in
              cell.innerHTML = SC.diamond.render(ab);
              cell.classList.add("diamond-new");
              setTimeout((function (c) {
                return function () { c.classList.remove("diamond-new"); };
              })(cell), 600);
            } else if (cell && !cell.querySelector(".diamond-cell")) {
              // Cell exists but empty — fill it
              cell.innerHTML = SC.diamond.render(ab);
            }
          }

          // Update stat cells
          var stats = batter.stats || {};
          var statKeys = ["atBats", "runs", "hits", "rbi", "baseOnBalls", "strikeOuts"];
          for (var sk = 0; sk < statKeys.length; sk++) {
            var statEl = document.getElementById("stat-" + side + "-" + batter.id + "-" + statKeys[sk]);
            if (statEl) {
              var val = stats[statKeys[sk]] || 0;
              if (statEl.textContent !== String(val)) statEl.textContent = val;
            }
          }
        }
      }

      // Update inning run totals
      for (var inn = 1; inn <= newModel.totalInnings; inn++) {
        var innEl = document.getElementById("inn-" + side + "-" + inn);
        var innRuns = newModel[side].linescore[inn - 1];
        if (innEl && innRuns != null) {
          if (innEl.textContent !== String(innRuns)) innEl.textContent = innRuns;
        }
      }
    }

    // Update header scores
    var headerEl = document.querySelector(".game-header");
    if (headerEl) {
      headerEl.outerHTML = SC.header.render(newModel);
    }

    // Check if new innings appeared (need new columns)
    if (newModel.totalInnings > currentModel.totalInnings) {
      // Full re-render needed for structural change
      renderFull(newModel);
    }

    currentModel = newModel;
  }

  // ── Polling ──

  function startPolling(gamePk) {
    stopPolling();
    currentGamePk = gamePk;

    function poll() {
      if (paused) return;
      SC.api.fetchGameFeedLive(gamePk).then(function (feed) {
        var newModel = SC.parser.parse(feed);

        if (isLive(newModel)) {
          updateScorecard(newModel);
          updateSituationBar(feed);
          pollTimer = setTimeout(poll, POLL_MS);
        } else {
          // Game went Final
          updateScorecard(newModel);
          removeSituationBar();
          showFinalBadge();
          stopPolling();
        }
      }).catch(function () {
        // Retry on error
        pollTimer = setTimeout(poll, POLL_MS);
      });
    }

    pollTimer = setTimeout(poll, POLL_MS);
  }

  function stopPolling() {
    if (pollTimer) {
      clearTimeout(pollTimer);
      pollTimer = null;
    }
    currentGamePk = null;
  }

  function showFinalBadge() {
    var badge = document.querySelector(".sit-live-badge");
    if (badge) {
      badge.innerHTML = "FINAL";
      badge.classList.add("final");
    }
    // Also add to header area
    var header = document.querySelector(".game-header");
    if (header && !header.querySelector(".live-badge")) {
      var finalEl = document.createElement("div");
      finalEl.className = "live-badge final";
      finalEl.textContent = "FINAL";
      header.querySelector(".title-row").appendChild(finalEl);
    }
  }

  function renderFull(model, feed) {
    var html = '';
    if (!SC.app.embed) {
      html += '<button class="back-btn" onclick="Scorecard.app.showFinder()">&larr; Back to games</button>';
    }
    if (isLive(model)) {
      html += '<div class="live-badge"><span class="dot"></span> LIVE</div>';
    }
    html += SC.header.render(model);
    html += '<div id="panels-area"></div>';
    html += SC.scorebook.render(model, self.embed);
    mainEl.innerHTML = html;
    currentModel = model;

    // Bind tab switching in embed mode
    if (self.embed) {
      var tabs = mainEl.querySelectorAll(".sb-tab");
      var panes = mainEl.querySelectorAll(".scorebook-tab-pane");
      for (var ti = 0; ti < tabs.length; ti++) {
        tabs[ti].addEventListener("click", function () {
          var side = this.getAttribute("data-side");
          for (var j = 0; j < tabs.length; j++) { tabs[j].classList.remove("active"); }
          for (var k = 0; k < panes.length; k++) { panes[k].classList.remove("active"); }
          this.classList.add("active");
          for (var m = 0; m < panes.length; m++) {
            if (panes[m].getAttribute("data-side") === side) panes[m].classList.add("active");
          }
        });
      }
    }

    // Load panels
    loadPanels(model, feed);
    bindPlayerClicks(model);
  }

  function loadPanels(model, feed) {
    var panelsArea = document.getElementById("panels-area");
    if (!panelsArea) return;

    // Broadcasts from the feed
    var broadcasts = [];
    if (feed && feed.gameData && feed.gameData.broadcasts) {
      broadcasts = feed.gameData.broadcasts;
    }
    // Also check game object from schedule
    if (!broadcasts.length && SC.app._currentGameSchedule) {
      broadcasts = SC.app._currentGameSchedule.broadcasts || [];
    }

    var html = "";
    if (broadcasts.length) {
      html += SC.panels.renderBroadcasts(broadcasts);
    }
    panelsArea.innerHTML = html;

    // Load weather async
    if (model.venueId) {
      SC.panels.loadWeather(model.venueId, function (wxHtml) {
        if (wxHtml) {
          panelsArea.insertAdjacentHTML("beforeend", wxHtml);
        }
      });
    }
  }

  function bindPlayerClicks(model) {
    document.addEventListener("click", function handler(e) {
      var nameEl = e.target.closest(".clickable-name");
      if (!nameEl) return;
      var pid = parseInt(nameEl.getAttribute("data-pid"), 10);
      var side = nameEl.getAttribute("data-side");
      var playerName = nameEl.textContent;
      var opposingTeamId = side === "away" ? model.home.team.id : model.away.team.id;
      SC.panels.togglePlayerPanel(pid, playerName, side, opposingTeamId, model);
    });
  }

  // ── Visibility API ──

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
      paused = true;
      if (pollTimer) {
        clearTimeout(pollTimer);
        pollTimer = null;
      }
    } else {
      if (Date.now() - lastResumeAt < 5000) return;
      lastResumeAt = Date.now();
      paused = false;
      if (currentGamePk && isLive(currentModel)) {
        startPolling(currentGamePk);
      }
    }
  });

  // ── App controller ──

  SC.app = {
    view: "finder",
    embed: false,

    init: function () {
      mainEl = document.getElementById("main");
      SC.tooltip.init();

      var params = getParams();
      this.embed = params.embed === "1";

      if (this.embed) {
        document.body.classList.add("embed-mode");
      }

      if (params.game) {
        this.loadGame(parseInt(params.game, 10));
      } else {
        if (params.date) {
          SC.finder.currentDate = params.date;
        }
        this.showFinder();
      }

      window.addEventListener("popstate", function () {
        var p = getParams();
        if (p.game) {
          SC.app.loadGame(parseInt(p.game, 10), true);
        } else {
          if (p.date) SC.finder.currentDate = p.date;
          SC.app.showFinder(true);
        }
      });
    },

    showFinder: function (skipPush) {
      stopPolling();
      this.view = "finder";
      if (!skipPush) this.updateURL();
      SC.finder.render(mainEl);
    },

    loadGame: function (gamePk, skipPush) {
      var self = this;
      stopPolling();
      this.view = "scorecard";
      if (!skipPush) {
        var url = "?game=" + gamePk;
        history.pushState({ game: gamePk }, "", url);
      }

      mainEl.innerHTML = '<div class="loading">Loading scorecard...</div>';

      SC.api.fetchGameFeedLive(gamePk).then(function (feed) {
        var model = SC.parser.parse(feed);
        currentModel = model;
        renderFull(model, feed);

        if (isLive(model)) {
          updateSituationBar(feed);
          startPolling(gamePk);
        }

        // Embed height
        if (self.embed && window.parent !== window) {
          try {
            var h = document.documentElement.scrollHeight;
            window.parent.postMessage({ type: "scorecard-height", height: h }, "*");
          } catch (e) {}
        }
      }).catch(function (err) {
        var msg = esc(err.message || "Unknown error");
        mainEl.innerHTML = '<div class="error-state">Failed to load game: ' +
          msg + '</div>' +
          '<button class="back-btn" onclick="Scorecard.app.showFinder()">&larr; Back to games</button>';
      });
    },

    updateURL: function () {
      var params = [];
      if (SC.finder.currentDate) params.push("date=" + SC.finder.currentDate);
      var url = params.length ? "?" + params.join("&") : window.location.pathname;
      history.replaceState({}, "", url);
    }
  };

  // Boot
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { SC.app.init(); });
  } else {
    SC.app.init();
  }
})();
