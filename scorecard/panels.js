(function () {
  "use strict";
  var SC = window.Scorecard = window.Scorecard || {};

  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // Wrigley Field venue ID and azimuth (home plate faces 37° from north)
  var WRIGLEY_ID = 17;
  var WRIGLEY_AZIMUTH = 37;

  // Domed venues (skip weather)
  var DOMED_VENUES = [
    12,   // Tropicana Field
    32,   // Minute Maid Park (retractable but often closed) — keep for now
  ];

  // Weather code descriptions
  var WMO_CODES = {
    0: "Clear", 1: "Mostly Clear", 2: "Partly Cloudy", 3: "Overcast",
    45: "Foggy", 48: "Fog", 51: "Light Drizzle", 53: "Drizzle", 55: "Heavy Drizzle",
    61: "Light Rain", 63: "Rain", 65: "Heavy Rain",
    71: "Light Snow", 73: "Snow", 75: "Heavy Snow",
    80: "Light Showers", 81: "Showers", 82: "Heavy Showers",
    95: "Thunderstorm", 96: "Thunderstorm + Hail", 99: "Thunderstorm + Heavy Hail"
  };

  function windDirection(degrees) {
    var dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
    var idx = Math.round(degrees / 22.5) % 16;
    return dirs[idx];
  }

  function wrigleyWindInterpretation(windDir, windSpeed) {
    if (windSpeed < 5) return "Calm — minimal wind effect";

    // Wrigley azimuth is 37°: home plate faces 37° (roughly NE)
    // Center field is at azimuth + 180 = 217° (roughly SW)
    // "Blowing out" = wind blowing from home plate toward outfield (toward SW, ~217°)
    // "Blowing in" = wind blowing from outfield toward home plate (toward NE, ~37°)

    var centerField = (WRIGLEY_AZIMUTH + 180) % 360;
    var diff = windDir - centerField;
    if (diff > 180) diff -= 360;
    if (diff < -180) diff += 360;

    // diff near 0 = blowing out to center
    // diff near 180 or -180 = blowing in
    var absDiff = Math.abs(diff);

    if (absDiff <= 30) {
      return "Blowing out to center — favorable for hitters";
    } else if (absDiff <= 60) {
      var side = diff > 0 ? "right" : "left";
      return "Blowing out to " + side + " field — favorable for hitters";
    } else if (absDiff >= 150) {
      return "Blowing in from center — pitcher's friend";
    } else if (absDiff >= 120) {
      var side2 = diff > 0 ? "left" : "right";
      return "Blowing in from " + side2 + " field — pitcher's friend";
    } else {
      var cross = diff > 0 ? "left to right" : "right to left";
      return "Crosswind " + cross;
    }
  }

  // ── Broadcast Panel ──

  SC.panels = {
    renderBroadcasts: function (broadcasts) {
      if (!broadcasts || !broadcasts.length) return "";

      var tv = [], radio = [];
      for (var i = 0; i < broadcasts.length; i++) {
        var b = broadcasts[i];
        var entry = {
          name: b.name || "",
          homeAway: b.homeAway || "",
          language: b.language || "en"
        };
        if (b.type === "TV") tv.push(entry);
        else if (b.type === "AM" || b.type === "FM") {
          entry.band = b.type;
          radio.push(entry);
        }
      }

      var html = '<div class="panel broadcast-panel">';
      html += '<div class="panel-header">Watch & Listen</div>';
      html += '<div class="panel-body">';

      if (tv.length) {
        html += '<div class="bc-group"><span class="bc-icon">TV</span> ';
        var tvParts = [];
        for (var t = 0; t < tv.length; t++) {
          var lang = tv[t].language !== "en" ? ' <span class="bc-lang">' + esc(tv[t].language.toUpperCase()) + '</span>' : "";
          tvParts.push(esc(tv[t].name) + lang);
        }
        html += tvParts.join(" · ");
        html += '</div>';
      }

      if (radio.length) {
        html += '<div class="bc-group"><span class="bc-icon">Radio</span> ';
        var radioParts = [];
        for (var r = 0; r < radio.length; r++) {
          var lang2 = radio[r].language !== "en" ? ' <span class="bc-lang">' + esc(radio[r].language.toUpperCase()) + '</span>' : "";
          radioParts.push(esc(radio[r].name) + lang2);
        }
        html += radioParts.join(" · ");
        html += '</div>';
      }

      html += '</div></div>';
      return html;
    },

    // ── Weather Panel ──

    renderWeather: function (weatherData, venueId, venueName) {
      if (!weatherData || !weatherData.current) return "";

      var c = weatherData.current;
      var temp = Math.round(c.temperature_2m || 0);
      var windSpeed = Math.round(c.windspeed_10m || 0);
      var windDir = c.winddirection_10m || 0;
      var code = c.weathercode || 0;
      var condition = WMO_CODES[code] || "Unknown";
      var compassDir = windDirection(windDir);

      var html = '<div class="panel weather-panel">';
      html += '<div class="panel-header">Weather</div>';
      html += '<div class="panel-body">';
      html += '<span class="wx-temp">' + temp + '°F</span>';
      html += '<span class="wx-cond">' + esc(condition) + '</span>';
      html += '<span class="wx-wind">' + windSpeed + ' mph ' + compassDir + '</span>';

      // Enhanced Wrigley wind interpretation
      if (venueId === WRIGLEY_ID && windSpeed >= 5) {
        var interp = wrigleyWindInterpretation(windDir, windSpeed);
        html += '<div class="wx-wrigley">' + esc(interp) + '</div>';
      }

      html += '</div></div>';
      return html;
    },

    loadWeather: function (venueId, callback) {
      // Skip for domed venues
      if (DOMED_VENUES.indexOf(venueId) >= 0) {
        callback("");
        return;
      }

      SC.api.fetchVenue(venueId).then(function (venue) {
        var loc = venue.location || {};
        var coords = loc.defaultCoordinates || {};
        if (!coords.latitude || !coords.longitude) {
          callback("");
          return;
        }

        SC.api.fetchWeather(coords.latitude, coords.longitude).then(function (wx) {
          var html = SC.panels.renderWeather(wx, venueId, venue.name);
          callback(html);
        }).catch(function () { callback(""); });
      }).catch(function () { callback(""); });
    },

    // ── Player Stats Bottom Bar ──

    activePlayerId: null,

    ensureBar: function () {
      var bar = document.getElementById("player-bar");
      if (!bar) {
        bar = document.createElement("div");
        bar.id = "player-bar";
        bar.className = "player-bar";
        bar.innerHTML = '<div class="player-bar-inner" id="player-bar-inner"></div>' +
          '<button class="player-bar-close" id="player-bar-close">&times;</button>';
        document.body.appendChild(bar);
        document.getElementById("player-bar-close").addEventListener("click", function () {
          SC.panels.closeBar();
        });
      }
      return bar;
    },

    closeBar: function () {
      var bar = document.getElementById("player-bar");
      if (bar) {
        bar.classList.remove("visible");
        // Highlight off
        var prev = document.querySelector(".clickable-name.active");
        if (prev) prev.classList.remove("active");
      }
      this.activePlayerId = null;
    },

    togglePlayerPanel: function (playerId, playerName, side, opposingTeamId, model) {
      // If same player, toggle off
      if (this.activePlayerId === playerId) {
        this.closeBar();
        return;
      }

      this.activePlayerId = playerId;

      // Highlight active player name
      var allNames = document.querySelectorAll(".clickable-name");
      for (var i = 0; i < allNames.length; i++) allNames[i].classList.remove("active");
      var activeNames = document.querySelectorAll('.clickable-name[data-pid="' + playerId + '"]');
      for (var j = 0; j < activeNames.length; j++) activeNames[j].classList.add("active");

      // Show bar with loading state
      var bar = this.ensureBar();
      var inner = document.getElementById("player-bar-inner");
      inner.innerHTML = '<div class="panel-loading">Loading stats for ' + esc(playerName) + '...</div>';
      bar.classList.add("visible");

      // Determine opposing pitcher
      var opposingPitcherId = 0;
      var lineup = side === "away" ? model.away.lineup : model.home.lineup;
      for (var s = 0; s < lineup.length; s++) {
        for (var b = 0; b < lineup[s].batters.length; b++) {
          var batter = lineup[s].batters[b];
          if (batter.id === playerId && batter.atBats.length > 0) {
            opposingPitcherId = batter.atBats[batter.atBats.length - 1].pitcherId;
          }
        }
      }

      // Fetch and render
      SC.api.fetchPlayerStats(playerId, opposingPitcherId, opposingTeamId).then(function (data) {
        if (SC.panels.activePlayerId !== playerId) return; // user clicked away
        inner.innerHTML = SC.panels.renderPlayerStats(data, playerName, opposingPitcherId, opposingTeamId);
      }).catch(function () {
        if (SC.panels.activePlayerId !== playerId) return;
        inner.innerHTML = '<div class="panel-loading">Stats unavailable</div>';
      });
    },

    renderPlayerStats: function (data, playerName, opposingPitcherId, opposingTeamId) {
      var stats = data.stats || [];
      var html = '<div class="pstat-content">';
      html += '<div class="pstat-name">' + esc(playerName) + '</div>';

      // Parse stat groups
      var season = null, vsPlayer = null, vsTeam = null, byMonth = null, lastX = null;
      for (var i = 0; i < stats.length; i++) {
        var s = stats[i];
        var type = s.type && s.type.displayName;
        var splits = s.splits || [];
        if (type === "season" && splits.length) season = splits[0].stat;
        if (type === "vsPlayer" && splits.length) vsPlayer = splits[0].stat;
        if (type === "vsTeam" && splits.length) vsTeam = splits[0].stat;
        if (type === "byMonth") byMonth = splits;
        if (type === "lastXGames" && splits.length) lastX = splits[0].stat;
      }

      // Determine if hitter or pitcher based on available stats
      var isHitter = season && (season.avg !== undefined || season.atBats !== undefined);

      // Essential line
      html += '<div class="pstat-section">';
      html += '<div class="pstat-label">Season</div>';
      if (isHitter && season) {
        html += '<div class="pstat-line">';
        html += stat("AVG", season.avg) + stat("OBP", season.obp) + stat("SLG", season.slg) +
                stat("HR", season.homeRuns) + stat("RBI", season.rbi) + stat("H", season.hits) +
                stat("AB", season.atBats);
        html += '</div>';
      } else if (season) {
        html += '<div class="pstat-line">';
        html += stat("ERA", season.era) + stat("WHIP", season.whip) + stat("K", season.strikeOuts) +
                stat("IP", season.inningsPitched) + stat("W", season.wins) + stat("L", season.losses);
        html += '</div>';
      }
      html += '</div>';

      // Vs pitcher
      if (vsPlayer) {
        html += '<div class="pstat-section">';
        html += '<div class="pstat-label">vs. Pitcher (Career)</div>';
        html += '<div class="pstat-line">';
        html += stat("AVG", vsPlayer.avg) + stat("AB", vsPlayer.atBats) +
                stat("H", vsPlayer.hits) + stat("HR", vsPlayer.homeRuns) +
                stat("K", vsPlayer.strikeOuts) + stat("BB", vsPlayer.baseOnBalls);
        html += '</div></div>';
      }

      // Vs team
      if (vsTeam) {
        html += '<div class="pstat-section">';
        html += '<div class="pstat-label">vs. Team (Career)</div>';
        html += '<div class="pstat-line">';
        html += stat("AVG", vsTeam.avg) + stat("AB", vsTeam.atBats) +
                stat("H", vsTeam.hits) + stat("HR", vsTeam.homeRuns) +
                stat("RBI", vsTeam.rbi);
        html += '</div></div>';
      }

      // Expandable section
      html += '<details class="pstat-more"><summary class="pstat-toggle">More</summary>';

      // Last 7 games
      if (lastX) {
        html += '<div class="pstat-section">';
        html += '<div class="pstat-label">Last 7 Games</div>';
        html += '<div class="pstat-line">';
        if (isHitter) {
          html += stat("AVG", lastX.avg) + stat("H", lastX.hits) + stat("AB", lastX.atBats) +
                  stat("HR", lastX.homeRuns) + stat("RBI", lastX.rbi);
        } else {
          html += stat("ERA", lastX.era) + stat("IP", lastX.inningsPitched) +
                  stat("K", lastX.strikeOuts);
        }
        html += '</div></div>';
      }

      // Monthly splits
      if (byMonth && byMonth.length) {
        html += '<div class="pstat-section">';
        html += '<div class="pstat-label">Monthly</div>';
        for (var m = 0; m < byMonth.length; m++) {
          var ms = byMonth[m];
          var monthName = ms.month || "";
          var mstat = ms.stat || {};
          html += '<div class="pstat-month">';
          html += '<span class="pstat-month-name">' + esc(monthName) + '</span> ';
          if (isHitter) {
            html += stat("AVG", mstat.avg) + stat("H", mstat.hits) + "/" + (mstat.atBats || 0) +
                    " " + stat("HR", mstat.homeRuns);
          } else {
            html += stat("ERA", mstat.era) + stat("IP", mstat.inningsPitched);
          }
          html += '</div>';
        }
        html += '</div>';
      }

      html += '</details>';
      html += '</div>';
      return html;
    }
  };

  function stat(label, val) {
    if (val == null) val = "-";
    return '<span class="pstat-item"><span class="pstat-key">' + label + '</span> ' + val + '</span>';
  }
})();
