(function () {
  "use strict";
  var SC = window.Scorecard = window.Scorecard || {};

  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function yesterday() {
    var d = new Date();
    d.setDate(d.getDate() - 1);
    return d.toISOString().slice(0, 10);
  }

  function teamAbbr(teamId) {
    for (var i = 0; i < SC.teams.length; i++) {
      if (SC.teams[i].id === teamId) return SC.teams[i].abbr;
    }
    return "???";
  }

  SC.finder = {
    currentDate: null,
    currentTeam: null,

    render: function (container) {
      var self = this;
      var date = this.currentDate || yesterday();
      this.currentDate = date;

      var html = '<div class="finder">';

      // Controls
      html += '<div class="finder-controls">';
      html += '<label for="date-pick">Date</label>';
      html += '<input type="date" id="date-pick" value="' + date + '">';
      html += '<label for="team-pick">Team</label>';
      html += '<select id="team-pick"><option value="">All Teams</option>';
      for (var i = 0; i < SC.teams.length; i++) {
        var t = SC.teams[i];
        var sel = this.currentTeam === t.id ? " selected" : "";
        html += '<option value="' + t.id + '"' + sel + '>' + esc(t.name) + '</option>';
      }
      html += '</select>';
      html += '</div>';

      // Cards container
      html += '<div class="game-cards" id="game-cards"></div>';
      html += '</div>';

      container.innerHTML = html;

      // Bind events
      var datePick = document.getElementById("date-pick");
      var teamPick = document.getElementById("team-pick");

      datePick.addEventListener("change", function () {
        self.currentDate = datePick.value;
        self.loadGames();
        SC.app.updateURL();
      });
      teamPick.addEventListener("change", function () {
        self.currentTeam = teamPick.value ? parseInt(teamPick.value, 10) : null;
        self.loadGames();
      });

      this.loadGames();
    },

    loadGames: function () {
      var self = this;
      var cardsEl = document.getElementById("game-cards");
      if (!cardsEl) return;

      cardsEl.innerHTML = '<div class="loading">Loading games...</div>';

      SC.api.fetchSchedule(this.currentDate).then(function (games) {
        self.renderCards(cardsEl, games);
      }).catch(function (err) {
        cardsEl.innerHTML = '<div class="error-state">Failed to load games: ' + esc(err.message) + '</div>';
      });
    },

    renderCards: function (container, games) {
      if (!games || !games.length) {
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

      if (!filtered.length) {
        container.innerHTML = '<div class="empty-state">No games found for this team</div>';
        return;
      }

      var html = "";
      for (var i = 0; i < filtered.length; i++) {
        var g = filtered[i];
        var isFinal = g.status && g.status.abstractGameState === "Final";
        var awayAbbr = teamAbbr(g.teams.away.team.id);
        var homeAbbr = teamAbbr(g.teams.home.team.id);
        var awayScore = g.teams.away.score != null ? g.teams.away.score : "";
        var homeScore = g.teams.home.score != null ? g.teams.home.score : "";
        var status = g.status ? g.status.detailedState : "";
        var isDH = g.gameNumber && g.gameNumber > 1;

        html += '<div class="game-card' + (isFinal ? "" : " disabled") + '" ' +
                (isFinal ? 'data-gamepk="' + g.gamePk + '"' : '') + '>';
        html += '<div class="matchup">';
        html += '<span>' + esc(awayAbbr) + ' @ ' + esc(homeAbbr) + '</span>';
        if (isFinal) {
          html += '<span class="score">' + awayScore + ' - ' + homeScore + '</span>';
        }
        html += '</div>';
        html += '<div class="meta">';
        html += '<span class="status-' + (isFinal ? "final" : "live") + '">' + esc(status) + '</span>';
        if (isDH) {
          html += '<span class="dh-label">Game ' + g.gameNumber + '</span>';
        }
        html += '</div>';
        html += '</div>';
      }

      container.innerHTML = html;

      // Bind card clicks
      var cards = container.querySelectorAll('.game-card[data-gamepk]');
      for (var c = 0; c < cards.length; c++) {
        cards[c].addEventListener("click", function () {
          var pk = parseInt(this.getAttribute("data-gamepk"), 10);
          SC.app.loadGame(pk);
        });
      }
    }
  };
})();
