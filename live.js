(function () {
  "use strict";

  var CUBS_ID = 112;
  var API = "https://statsapi.mlb.com/api/v1";
  var LIVE_API = "https://statsapi.mlb.com/api/v1.1";
  var POLL_MS = 20000;
  var IDLE_MS = 300000;
  var container = document.getElementById("live-game");

  var timer = null;
  var slateTimer = null;
  var paused = false;
  var anyLive = false; // track if any game is live for slate poll rate

  /* ── helpers ──────────────────────────────────────────────────── */

  function today() {
    var d = new Date();
    return d.getFullYear() + "-" +
      String(d.getMonth() + 1).padStart(2, "0") + "-" +
      String(d.getDate()).padStart(2, "0");
  }

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function teamAbbr(team) {
    return team.abbreviation || team.teamName || "???";
  }

  function fmtTime(iso) {
    var d = new Date(iso);
    var h = d.getHours(), m = d.getMinutes();
    var ampm = h >= 12 ? "PM" : "AM";
    h = h % 12 || 12;
    return h + ":" + String(m).padStart(2, "0") + " " + ampm;
  }

  /* ── diamond SVG ─────────────────────────────────────────────── */

  function diamond(first, second, third) {
    var on = "var(--gold)";
    var off = "var(--rule-hi)";
    return '<svg viewBox="0 0 60 60" width="48" height="48" class="diamond">' +
      '<polygon points="30,6 54,30 30,54 6,30" fill="none" stroke="var(--rule-hi)" stroke-width="1.5"/>' +
      '<circle cx="54" cy="30" r="6" fill="' + (first ? on : off) + '"/>' +
      '<circle cx="30" cy="6" r="6" fill="' + (second ? on : off) + '"/>' +
      '<circle cx="6" cy="30" r="6" fill="' + (third ? on : off) + '"/>' +
      "</svg>";
  }

  /* ── Cubs widget renderers ───────────────────────────────────── */

  function renderLive(game, feed) {
    if (!container) return;
    var ls = feed.liveData.linescore;
    var away = game.teams.away.team;
    var home = game.teams.home.team;
    var ar = ls.teams.away.runs != null ? ls.teams.away.runs : 0;
    var hr = ls.teams.home.runs != null ? ls.teams.home.runs : 0;
    var inn = ls.currentInning || 1;
    var half = ls.inningHalf || "Top";
    var outs = ls.outs || 0;
    var balls = ls.balls || 0;
    var strikes = ls.strikes || 0;

    var onFirst = !!(ls.offense && ls.offense.first);
    var onSecond = !!(ls.offense && ls.offense.second);
    var onThird = !!(ls.offense && ls.offense.third);

    var batter = "", pitcher = "";
    var cp = feed.liveData.plays && feed.liveData.plays.currentPlay;
    if (cp && cp.matchup) {
      batter = cp.matchup.batter ? cp.matchup.batter.fullName : "";
      pitcher = cp.matchup.pitcher ? cp.matchup.pitcher.fullName : "";
    }

    var lastPlay = "";
    var plays = feed.liveData.plays;
    if (plays && plays.scoringPlays && plays.scoringPlays.length > 0) {
      var idx = plays.scoringPlays[plays.scoringPlays.length - 1];
      var sp = plays.allPlays[idx];
      if (sp && sp.result) lastPlay = sp.result.description || "";
    }

    var situationHTML =
      '<div class="situation">' +
        '<span class="count">' +
          '<span class="count-label">B</span><span class="count-val">' + balls + '</span>' +
          '<span class="count-label">S</span><span class="count-val">' + strikes + '</span>' +
          '<span class="count-label">O</span><span class="count-val">' + outs + '</span>' +
        "</span>" +
        diamond(onFirst, onSecond, onThird) +
      "</div>";

    var matchupHTML = "";
    if (batter || pitcher) {
      matchupHTML =
        '<div class="live-matchup">' +
          (batter ? "AB: <strong>" + esc(batter) + "</strong>" : "") +
          (batter && pitcher ? " &mdash; " : "") +
          (pitcher ? "P: <strong>" + esc(pitcher) + "</strong>" : "") +
        "</div>";
    }

    var lastPlayHTML = "";
    if (lastPlay) {
      lastPlayHTML = '<div class="last-play">' + esc(lastPlay) + "</div>";
    }

    var state = game.status.detailedState || "";
    var innLabel = half.substring(0, 3) + " " + inn;
    if (state === "Delayed" || state === "Delayed Start") {
      innLabel = "Delayed";
    }

    container.innerHTML =
      '<div class="live-widget">' +
        '<div class="live-badge"><span class="dot"></span> LIVE &mdash; ' + innLabel + "</div>" +
        '<div class="score-row">' +
          '<span class="team-abbr">' + esc(teamAbbr(away)) + '</span>' +
          '<span class="runs">' + ar + '</span>' +
          '<span class="score-sep">&mdash;</span>' +
          '<span class="runs">' + hr + '</span>' +
          '<span class="team-abbr">' + esc(teamAbbr(home)) + '</span>' +
        "</div>" +
        situationHTML +
        matchupHTML +
        lastPlayHTML +
      "</div>";
  }

  function renderFinal(game) {
    if (!container) return;
    var away = game.teams.away;
    var home = game.teams.home;
    var ar = away.score != null ? away.score : 0;
    var hr = home.score != null ? home.score : 0;
    var innings = "";
    if (game.linescore && game.linescore.currentInning > 9) {
      innings = " / F" + game.linescore.currentInning;
    }

    container.innerHTML =
      '<div class="live-widget final">' +
        '<div class="live-badge"><span class="flag">&#9873;</span> FINAL' + innings + "</div>" +
        '<div class="score-row">' +
          '<span class="team-abbr">' + esc(teamAbbr(away.team)) + '</span>' +
          '<span class="runs">' + ar + '</span>' +
          '<span class="score-sep">&mdash;</span>' +
          '<span class="runs">' + hr + '</span>' +
          '<span class="team-abbr">' + esc(teamAbbr(home.team)) + '</span>' +
        "</div>" +
      "</div>";
  }

  function renderPreview(game) {
    if (!container) return;
    var away = game.teams.away.team;
    var home = game.teams.home.team;
    var time = fmtTime(game.gameDate);

    var probA = "", probH = "";
    if (game.probablePitcher) {
      if (game.probablePitcher.away) probA = game.probablePitcher.away.fullName || "";
      if (game.probablePitcher.home) probH = game.probablePitcher.home.fullName || "";
    }

    var probHTML = "";
    if (probA || probH) {
      probHTML =
        '<div class="live-matchup">' +
          (probA ? esc(probA) : "TBD") + " vs " + (probH ? esc(probH) : "TBD") +
        "</div>";
    }

    container.innerHTML =
      '<div class="live-widget preview">' +
        '<div class="live-badge"><span class="flag">&#9888;</span> FIRST PITCH &mdash; ' + time + "</div>" +
        '<div class="score-row">' +
          '<span class="team-abbr">' + esc(teamAbbr(away)) + '</span>' +
          '<span class="score-sep">at</span>' +
          '<span class="team-abbr">' + esc(teamAbbr(home)) + '</span>' +
        "</div>" +
        probHTML +
      "</div>";
  }

  function renderIdle() {
    if (!container) return;
    container.innerHTML =
      '<div class="live-widget idle">' +
        '<div class="idle-msg">No Cubs game in progress</div>' +
      "</div>";
  }

  /* ── slate updater ───────────────────────────────────────────── */

  function updateSlate(allGames) {
    anyLive = false;
    for (var i = 0; i < allGames.length; i++) {
      var g = allGames[i];
      var card = document.querySelector('.g[data-gpk="' + g.gamePk + '"]');
      if (!card) continue;

      var state = g.status.abstractGameState;
      var timeEl = card.querySelector(".time");
      if (!timeEl) continue;

      if (state === "Live") {
        anyLive = true;
        var ls = g.linescore || {};
        var ar = (ls.teams && ls.teams.away) ? (ls.teams.away.runs != null ? ls.teams.away.runs : 0) : 0;
        var hr = (ls.teams && ls.teams.home) ? (ls.teams.home.runs != null ? ls.teams.home.runs : 0) : 0;
        var inn = ls.currentInning || 1;
        var half = (ls.inningHalf || "Top").substring(0, 3);
        timeEl.innerHTML = '<span class="slate-live">' + ar + '&ndash;' + hr + '</span> ' +
          '<span class="slate-inn">' + half + ' ' + inn + '</span>';
        card.classList.add("g-live");
        card.classList.remove("g-final");
      } else if (state === "Final") {
        var as_ = g.teams.away.score != null ? g.teams.away.score : 0;
        var hs = g.teams.home.score != null ? g.teams.home.score : 0;
        var extra = (g.linescore && g.linescore.currentInning > 9) ? " / F" + g.linescore.currentInning : "";
        timeEl.innerHTML = '<span class="slate-final">' + as_ + '&ndash;' + hs + extra + '</span>';
        card.classList.add("g-final");
        card.classList.remove("g-live");
      }
    }
  }

  function pollSlate() {
    if (paused) { slateTimer = setTimeout(pollSlate, POLL_MS); return; }

    var url = API + "/schedule?sportId=1&date=" + today() + "&hydrate=linescore,team";
    fetch(url)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.dates && data.dates.length && data.dates[0].games) {
          updateSlate(data.dates[0].games);
        }
        slateTimer = setTimeout(pollSlate, anyLive ? POLL_MS : IDLE_MS);
      })
      .catch(function () {
        slateTimer = setTimeout(pollSlate, POLL_MS);
      });
  }

  /* ── Cubs widget polling ─────────────────────────────────────── */

  function scheduleCubs(ms, fn) {
    clearTimeout(timer);
    timer = setTimeout(fn, ms);
  }

  function pollFeed(gamePk, game) {
    if (paused) { scheduleCubs(POLL_MS, function () { pollFeed(gamePk, game); }); return; }

    fetch(LIVE_API + "/game/" + gamePk + "/feed/live")
      .then(function (r) { return r.json(); })
      .then(function (feed) {
        var state = feed.gameData.status.abstractGameState;
        if (state === "Live") {
          renderLive(game, feed);
          scheduleCubs(POLL_MS, function () { pollFeed(gamePk, game); });
        } else if (state === "Final") {
          renderFinal(game);
        } else {
          renderPreview(game);
          scheduleCubs(IDLE_MS, checkCubs);
        }
      })
      .catch(function () {
        scheduleCubs(POLL_MS, function () { pollFeed(gamePk, game); });
      });
  }

  function checkCubs() {
    if (paused) { scheduleCubs(IDLE_MS, checkCubs); return; }
    if (!container) return;

    var url = API + "/schedule?sportId=1&date=" + today() +
      "&teamId=" + CUBS_ID + "&hydrate=linescore,probablePitcher,team";

    fetch(url)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.dates || data.dates.length === 0 || !data.dates[0].games.length) {
          renderIdle();
          scheduleCubs(IDLE_MS, checkCubs);
          return;
        }

        var games = data.dates[0].games;
        var live = null, preview = null, final_ = null;
        for (var i = 0; i < games.length; i++) {
          var st = games[i].status.abstractGameState;
          if (st === "Live") { live = games[i]; break; }
          else if (st === "Preview" && !preview) preview = games[i];
          else if (st === "Final") final_ = games[i];
        }

        if (live) {
          pollFeed(live.gamePk, live);
        } else if (preview) {
          renderPreview(preview);
          scheduleCubs(IDLE_MS, checkCubs);
        } else if (final_) {
          renderFinal(final_);
          scheduleCubs(IDLE_MS, checkCubs);
        } else {
          renderIdle();
          scheduleCubs(IDLE_MS, checkCubs);
        }
      })
      .catch(function () {
        scheduleCubs(IDLE_MS, checkCubs);
      });
  }

  /* ── visibility API ──────────────────────────────────────────── */

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
      paused = true;
      clearTimeout(timer);
      clearTimeout(slateTimer);
    } else {
      paused = false;
      checkCubs();
      pollSlate();
    }
  });

  /* ── init ────────────────────────────────────────────────────── */

  checkCubs();
  pollSlate();
})();
