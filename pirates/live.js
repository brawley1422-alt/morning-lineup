(function () {
  "use strict";

  var CUBS_ID = window.TEAM_ID || 112;
  var API = "https://statsapi.mlb.com/api/v1";
  var LIVE_API = "https://statsapi.mlb.com/api/v1.1";
  var POLL_MS = 20000;
  var IDLE_MS = 300000;
  var container = document.getElementById("live-game");

  var timer = null;
  var slateTimer = null;
  var paused = false;
  var anyLive = false; // track if any game is live for slate poll rate
  var lastWidgetHTML = ""; // diff check to prevent flicker on unchanged content
  var lastResumeAt = 0; // debounce visibility changes

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

    var newHTML =
      '<div class="live-widget">' +
        '<div class="live-badge"><span class="dot"></span> LIVE &mdash; ' + esc(innLabel) + "</div>" +
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
    if (newHTML !== lastWidgetHTML) {
      container.innerHTML = newHTML;
      lastWidgetHTML = newHTML;
    }
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

  function renderPreview(game, extras) {
    if (!container) return;
    var away = game.teams.away.team;
    var home = game.teams.home.team;
    var time = fmtTime(game.gameDate);
    var isHome = home.id === CUBS_ID;
    var oppAbbr = isHome ? teamAbbr(away) : teamAbbr(home);

    var probA = "", probH = "";
    if (game.teams && game.teams.away && game.teams.away.probablePitcher) {
      probA = game.teams.away.probablePitcher.fullName || "";
    }
    if (game.teams && game.teams.home && game.teams.home.probablePitcher) {
      probH = game.teams.home.probablePitcher.fullName || "";
    }

    var probHTML = "";
    if (probA || probH) {
      probHTML =
        '<div class="live-matchup">' +
          (probA ? esc(probA) : "TBD") + " vs " + (probH ? esc(probH) : "TBD") +
        "</div>";
    }

    // Extras: opponent record, season series, lineup
    var extrasHTML = "";
    if (extras) {
      var metaParts = [];
      if (extras.oppRecord) metaParts.push('<span class="pw-opp">' + esc(oppAbbr) + ': ' + esc(extras.oppRecord) + '</span>');
      if (extras.series) metaParts.push('<span class="pw-series">Season series: ' + esc(extras.series) + '</span>');
      if (metaParts.length) extrasHTML += '<div class="pw-meta">' + metaParts.join(' &middot; ') + '</div>';
      if (extras.lineup && extras.lineup.length) {
        var luItems = "";
        for (var i = 0; i < extras.lineup.length; i++) {
          var p = extras.lineup[i];
          luItems += '<span class="pw-lu-slot"><span class="pw-lu-pos">' + esc(p.pos) + '</span> ' + esc(p.name) + '</span>';
        }
        extrasHTML += '<div class="pw-lineup"><span class="pw-lu-label">Lineup</span><div class="pw-lu-slots">' + luItems + '</div></div>';
      }
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
        extrasHTML +
      "</div>";
  }

  /* ── preview data fetcher ────────────────────────────────────── */

  var DIV_NAMES = {201:"AL East",202:"AL Central",200:"AL West",204:"NL East",205:"NL Central",203:"NL West"};

  function ordinal(n) {
    n = parseInt(n, 10);
    if (isNaN(n)) return "";
    var s = {1:"st",2:"nd",3:"rd"}[n < 20 ? n : n % 10];
    return (s || "th");
  }

  function fetchPreviewExtras(game, callback) {
    var isHome = game.teams.home.team.id === CUBS_ID;
    var oppId = isHome ? game.teams.away.team.id : game.teams.home.team.id;
    var cubsSide = isHome ? "home" : "away";
    var extras = {oppRecord: "", series: "", lineup: []};
    var pending = 3;
    function done() { pending--; if (pending <= 0) callback(extras); }

    // 1. Lineup from live feed
    fetch(LIVE_API + "/game/" + game.gamePk + "/feed/live")
      .then(function (r) { return r.json(); })
      .then(function (feed) {
        var players = (feed.gameData || {}).players || {};
        var order = ((((feed.liveData || {}).boxscore || {}).teams || {})[cubsSide] || {}).battingOrder || [];
        for (var i = 0; i < Math.min(order.length, 9); i++) {
          var p = players["ID" + order[i]] || {};
          var last = (p.fullName || "?").split(" ").pop();
          extras.lineup.push({name: last, pos: (p.primaryPosition || {}).abbreviation || "?"});
        }
        done();
      })
      .catch(done);

    // 2. Opponent record from standings
    fetch(API + "/standings?leagueId=103,104&season=" + new Date().getFullYear() + "&standingsTypes=regularSeason")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var records = data.records || [];
        for (var i = 0; i < records.length; i++) {
          var teamRecs = records[i].teamRecords || [];
          for (var j = 0; j < teamRecs.length; j++) {
            if (teamRecs[j].team.id === oppId) {
              var tr = teamRecs[j];
              var divId = (records[i].division || {}).id;
              var divName = DIV_NAMES[divId] || "";
              var rank = tr.divisionRank || "?";
              var streak = (tr.streak || {}).streakCode || "";
              extras.oppRecord = tr.wins + "-" + tr.losses + ", " + rank + ordinal(rank) + " " + divName;
              if (streak) extras.oppRecord += " (" + streak + ")";
            }
          }
        }
        done();
      })
      .catch(done);

    // 3. Season series
    var yr = new Date().getFullYear();
    fetch(API + "/schedule?sportId=1&teamId=" + CUBS_ID + "&season=" + yr + "&startDate=" + yr + "-03-20&endDate=" + today() + "&hydrate=team")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var sw = 0, sl = 0;
        var dates = data.dates || [];
        for (var i = 0; i < dates.length; i++) {
          var games = dates[i].games || [];
          for (var j = 0; j < games.length; j++) {
            var g = games[j];
            if ((g.status || {}).abstractGameState !== "Final") continue;
            var ga = g.teams.away, gh = g.teams.home;
            if (ga.team.id !== oppId && gh.team.id !== oppId) continue;
            var cubsHome = gh.team.id === CUBS_ID;
            var cs = cubsHome ? (gh.score || 0) : (ga.score || 0);
            var os = cubsHome ? (ga.score || 0) : (gh.score || 0);
            if (cs > os) sw++; else sl++;
          }
        }
        if (sw + sl > 0) extras.series = sw + "-" + sl;
        done();
      })
      .catch(done);
  }

  function renderIdle() {
    if (!container) return;
    container.innerHTML =
      '<div class="live-widget idle">' +
        '<div class="idle-msg">' + (window.TEAM_IDLE_MSG || "No game in progress") + '</div>' +
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
          fetchPreviewExtras(game, function (ex) { renderPreview(game, ex); });
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
          fetchPreviewExtras(preview, function (ex) { renderPreview(preview, ex); });
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
      if (Date.now() - lastResumeAt < 5000) return;
      lastResumeAt = Date.now();
      paused = false;
      checkCubs();
      pollSlate();
    }
  });

  /* ── init ────────────────────────────────────────────────────── */

  checkCubs();
  pollSlate();
})();
