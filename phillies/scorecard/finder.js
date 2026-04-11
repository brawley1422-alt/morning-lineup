(function () {
  "use strict";
  var SC = window.Scorecard = window.Scorecard || {};

  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function today() {
    var d = new Date();
    return d.toISOString().slice(0, 10);
  }

  function formatDate(ymd) {
    try {
      var parts = ymd.split("-");
      var d = new Date(parseInt(parts[0],10), parseInt(parts[1],10) - 1, parseInt(parts[2],10));
      var opts = { weekday: "short", month: "short", day: "2-digit", year: "numeric" };
      var s = d.toLocaleDateString("en-US", opts).toUpperCase().replace(/,/g, "");
      var p = s.split(/\s+/);
      if (p.length === 4) return p[0] + " · " + p[1] + " " + p[2] + " · " + p[3];
      return s;
    } catch (e) { return ymd; }
  }

  function teamMeta(teamId) {
    for (var i = 0; i < SC.teams.length; i++) {
      if (SC.teams[i].id === teamId) return SC.teams[i];
    }
    return null;
  }
  function teamAbbr(teamId) {
    var t = teamMeta(teamId);
    return t ? t.abbr : "???";
  }

  // Cached standings for today's records
  var standingsCache = null;
  function fetchStandings() {
    if (standingsCache) return Promise.resolve(standingsCache);
    var year = new Date().getFullYear();
    return fetch("https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=" + year + "&standingsTypes=regularSeason")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var out = {};
        var divNames = {201:"AL East",202:"AL Central",200:"AL West",204:"NL East",205:"NL Central",203:"NL West"};
        for (var i = 0; i < (data.records || []).length; i++) {
          var rec = data.records[i];
          var divName = divNames[rec.division.id] || "";
          for (var j = 0; j < rec.teamRecords.length; j++) {
            var tr = rec.teamRecords[j];
            out[tr.team.id] = { w: tr.wins, l: tr.losses, div: divName };
          }
        }
        standingsCache = out;
        return out;
      })
      .catch(function () { return {}; });
  }

  SC.finder = {
    currentDate: null,
    currentTeam: null,

    render: function (container) {
      var self = this;
      var date = this.currentDate || today();
      this.currentDate = date;

      var html = '<div class="finder">';

      // Controls bar
      html += '<div class="finder-controls-bar"><div class="finder-controls-inner">';
      html += '<div class="ctrl"><label for="date-pick">◆ Date</label>';
      html += '<input type="date" id="date-pick" value="' + esc(date) + '"></div>';
      html += '<div class="ctrl"><label for="team-pick">◆ Team Filter</label>';
      html += '<select id="team-pick"><option value="">All Teams</option>';
      for (var i = 0; i < SC.teams.length; i++) {
        var t = SC.teams[i];
        var sel = this.currentTeam === t.id ? " selected" : "";
        html += '<option value="' + t.id + '"' + sel + '>' + esc(t.name) + '</option>';
      }
      html += '</select></div>';
      html += '<div class="ctrl-spacer"></div>';
      html += '<div class="ctrl-stats">';
      html += '<div class="stat live"><span class="n" id="finder-n-live">—</span>Live Now</div>';
      html += '<div class="stat"><span class="n" id="finder-n-final">—</span>Final</div>';
      html += '<div class="stat"><span class="n" id="finder-n-preview">—</span>Upcoming</div>';
      html += '</div>';
      html += '</div></div>';

      // Slate header
      html += '<div class="slate-wrap">';
      html += '<div class="slate-head">';
      html += '<span class="num">01</span>';
      html += '<h2 class="h" id="finder-slate-title">Today\'s Slate</h2>';
      html += '<span class="tag" id="finder-slate-tag">' + esc(formatDate(date)) + '</span>';
      html += '</div>';
      html += '<div class="games" id="game-cards"></div>';
      html += '</div>';

      html += '</div>';
      container.innerHTML = html;

      var datePick = document.getElementById("date-pick");
      var teamPick = document.getElementById("team-pick");

      datePick.addEventListener("change", function () {
        self.currentDate = datePick.value;
        document.getElementById("finder-slate-tag").textContent = formatDate(self.currentDate);
        var title = document.getElementById("finder-slate-title");
        title.textContent = self.currentDate === today() ? "Today's Slate" : "Slate";
        self.loadGames();
        SC.app.updateURL();
      });
      teamPick.addEventListener("change", function () {
        self.currentTeam = teamPick.value ? parseInt(teamPick.value, 10) : null;
        self.loadGames();
      });

      var title = document.getElementById("finder-slate-title");
      title.textContent = date === today() ? "Today's Slate" : "Slate";

      this.loadGames();
    },

    loadGames: function () {
      var self = this;
      var cardsEl = document.getElementById("game-cards");
      if (!cardsEl) return;

      cardsEl.innerHTML = '<div class="loading">Loading games...</div>';

      Promise.all([
        SC.api.fetchSchedule(this.currentDate),
        fetchStandings()
      ]).then(function (results) {
        self.renderCards(cardsEl, results[0], results[1] || {});
      }).catch(function (err) {
        cardsEl.innerHTML = '<div class="empty-state">Failed to load games: ' + esc(err.message) + '</div>';
      });
    },

    renderCards: function (container, games, standings) {
      if (!games || !games.length) {
        document.getElementById("finder-n-live").textContent = "0";
        document.getElementById("finder-n-final").textContent = "0";
        document.getElementById("finder-n-preview").textContent = "0";
        container.innerHTML = '<div class="empty-state">No games scheduled</div>';
        return;
      }

      var filtered = games;
      if (this.currentTeam) {
        filtered = games.filter(function (g) {
          return g.teams.away.team.id === this.currentTeam ||
                 g.teams.home.team.id === this.currentTeam;
        }.bind(this));
      }

      // Count states from filtered set
      var nLive = 0, nFinal = 0, nPreview = 0;
      for (var ci = 0; ci < filtered.length; ci++) {
        var st = filtered[ci].status && filtered[ci].status.abstractGameState;
        if (st === "Live") nLive++;
        else if (st === "Final") nFinal++;
        else nPreview++;
      }
      document.getElementById("finder-n-live").textContent = nLive;
      document.getElementById("finder-n-final").textContent = nFinal;
      document.getElementById("finder-n-preview").textContent = nPreview;

      if (!filtered.length) {
        container.innerHTML = '<div class="empty-state">No games found for this team</div>';
        return;
      }

      var html = "";
      for (var i = 0; i < filtered.length; i++) {
        var g = filtered[i];
        var gameState = g.status && g.status.abstractGameState;
        var isFinal = gameState === "Final";
        var isLive = gameState === "Live";
        var isPreview = !isFinal && !isLive;
        var isClickable = isFinal || isLive;

        var awayId = g.teams.away.team.id;
        var homeId = g.teams.home.team.id;
        var awayAbbr = teamAbbr(awayId);
        var homeAbbr = teamAbbr(homeId);
        var awayFull = g.teams.away.team.name || awayAbbr;
        var homeFull = g.teams.home.team.name || homeAbbr;
        var awayScore = g.teams.away.score;
        var homeScore = g.teams.home.score;
        var awayRec = standings[awayId];
        var homeRec = standings[homeId];

        var venue = (g.venue && g.venue.name) || "";
        var status = (g.status && g.status.detailedState) || "";
        var isDH = g.gameNumber && g.gameNumber > 1;

        var cls = "game";
        if (isLive) cls += " live";
        else if (isFinal) cls += " final";
        else cls += " upcoming";
        if (!isClickable) cls += " disabled";

        var statusText = "";
        if (isLive) {
          var ls = g.linescore || {};
          var half = ls.isTopInning ? "T" : "B";
          statusText = "Live · " + half + (ls.currentInning || "");
        } else if (isFinal) {
          statusText = "Final" + (g.linescore && g.linescore.currentInning > 9 ? " · " + g.linescore.currentInning : "");
        } else {
          try {
            var d = new Date(g.gameDate);
            statusText = d.toLocaleTimeString("en-US", {hour:"numeric",minute:"2-digit",timeZone:"America/Chicago"});
          } catch(e){ statusText = status; }
        }

        var awayWins = isFinal && awayScore > homeScore;
        var homeWins = isFinal && homeScore > awayScore;

        var tag = isClickable ? "a" : "div";
        var attrs = isClickable ? ' data-gamepk="' + g.gamePk + '" href="#"' : "";
        html += "<" + tag + ' class="' + cls + '"' + attrs + '>';
        html += '<div class="game-head">';
        html += '<span class="venue">' + esc(venue) + '</span>';
        html += '<span class="status">' + esc(statusText) + '</span>';
        html += '</div>';

        html += '<div class="game-matchup">';
        html += this.renderRow(awayFull, awayAbbr, awayRec, awayScore, awayWins, isPreview);
        html += this.renderRow(homeFull, homeAbbr, homeRec, homeScore, homeWins, isPreview);
        html += '</div>';

        html += '<div class="game-foot">';
        if (isDH) {
          html += '<span class="detail">Game ' + g.gameNumber + '</span>';
        } else if (isLive) {
          html += '<span class="detail">' + esc(status) + '</span>';
        } else if (isPreview) {
          var prob = "";
          if (g.teams.away.probablePitcher && g.teams.home.probablePitcher) {
            prob = g.teams.away.probablePitcher.lastName + " vs " + g.teams.home.probablePitcher.lastName;
          }
          html += '<span class="detail">' + esc(prob) + '</span>';
        } else {
          html += '<span class="detail">&nbsp;</span>';
        }
        html += '<span class="link">' + (isClickable ? "Open Scorecard →" : "Unavailable") + '</span>';
        html += '</div>';
        html += "</" + tag + ">";
      }

      container.innerHTML = html;

      var cards = container.querySelectorAll('a.game[data-gamepk]');
      for (var c = 0; c < cards.length; c++) {
        cards[c].addEventListener("click", function (ev) {
          ev.preventDefault();
          var pk = parseInt(this.getAttribute("data-gamepk"), 10);
          SC.app.loadGame(pk);
        });
      }
    },

    renderRow: function (fullName, abbr, rec, score, isWinner, isPreview) {
      var recLine = rec ? (rec.w + "-" + rec.l + (rec.div ? " · " + rec.div : "")) : "";
      var scoreText = "";
      if (isPreview) scoreText = "—";
      else scoreText = (score != null ? score : "");
      var rowCls = "game-row" + (isWinner ? " winner" : "");
      var html = '<div class="' + rowCls + '">';
      html += '<div class="logo">' + esc(abbr) + '</div>';
      html += '<div class="name">' + esc(fullName);
      if (recLine) html += '<span class="rec">' + esc(recLine) + '</span>';
      html += '</div>';
      html += '<div class="score">' + esc(String(scoreText)) + '</div>';
      html += '</div>';
      return html;
    }
  };
})();
