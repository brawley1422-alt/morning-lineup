(function () {
  "use strict";
  var SC = window.Scorecard = window.Scorecard || {};

  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function buildPitchingChangeMap(changes, halfInning) {
    // Away page shows pitching changes during the Top half (away batting),
    // Home page shows pitching changes during the Bottom half (home batting)
    var map = {};
    var targetHalf = halfInning === "away" ? "Top" : "Bottom";
    for (var i = 0; i < changes.length; i++) {
      if (changes[i].halfInning === targetHalf) {
        map[changes[i].inning] = changes[i];
      }
    }
    return map;
  }

  function renderPage(teamData, totalInnings, pitchingChanges, side) {
    var lineup = teamData.lineup;
    var changeMap = buildPitchingChangeMap(pitchingChanges, side);

    var html = '<div class="scorebook-page ' + side + '">';
    html += '<div class="page-label">' + esc(teamData.team.abbreviation) +
            ' &mdash; ' + (side === "away" ? "Visitors" : "Home") + '</div>';
    html += '<table class="scorebook-grid"><thead><tr>';

    // Player column header
    html += '<th class="player-header">Batter</th>';

    // Inning headers
    for (var inn = 1; inn <= totalInnings; inn++) {
      html += '<th class="inning-header">' + inn + '</th>';
    }

    // Stat headers
    var stats = ["AB", "R", "H", "RBI", "BB", "K"];
    for (var s = 0; s < stats.length; s++) {
      html += '<th class="stat-header">' + stats[s] + '</th>';
    }
    html += '</tr></thead><tbody>';

    // Rows per lineup slot
    for (var slot = 0; slot < lineup.length; slot++) {
      var batters = lineup[slot].batters;
      for (var bi = 0; bi < batters.length; bi++) {
        var batter = batters[bi];
        var isFirst = bi === 0;
        var isSub = !batter.isStarter;

        html += '<tr class="' + (isFirst ? "slot-first" : "") + '">';

        // Player cell
        html += '<td class="player-cell' + (isSub ? " sub-row" : "") + '" data-pid="' + batter.id + '">';
        html += '<span class="name clickable-name" data-pid="' + batter.id + '" data-side="' + side + '">' + esc(batter.name) + '</span>';
        html += '<span class="pos">' + esc(batter.position) + '</span>';
        if (isSub) {
          html += '<span class="sub-label">PH</span>';
        }
        html += '</td>';

        // Diamond cells per inning
        for (var inn2 = 1; inn2 <= totalInnings; inn2++) {
          var ab = null;
          for (var a = 0; a < batter.atBats.length; a++) {
            if (batter.atBats[a].inning === inn2) {
              ab = batter.atBats[a];
              break;
            }
          }
          var changeClass = changeMap[inn2] ? " pitching-change" : "";
          var cellId = side + "-" + batter.id + "-" + inn2;
          html += '<td class="diamond-td' + changeClass + '" id="cell-' + cellId + '">';
          if (ab) {
            html += SC.diamond.render(ab);
          }
          html += '</td>';
        }

        // Stat cells
        var bs = batter.stats || {};
        var statKeys = ["atBats", "runs", "hits", "rbi", "baseOnBalls", "strikeOuts"];
        var statVals = [
          bs.atBats || 0,
          bs.runs || 0,
          bs.hits || 0,
          bs.rbi || 0,
          bs.baseOnBalls || 0,
          bs.strikeOuts || 0
        ];
        for (var sv = 0; sv < statVals.length; sv++) {
          html += '<td class="stat-cell" id="stat-' + side + "-" + batter.id + "-" + statKeys[sv] + '">' + statVals[sv] + '</td>';
        }

        html += '</tr>';
      }
    }

    // Totals row
    html += '<tr class="slot-first totals-row"><td class="player-cell">Totals</td>';
    for (var ti = 1; ti <= totalInnings; ti++) {
      var innRuns = teamData.linescore[ti - 1];
      html += '<td class="diamond-td inning-total" id="inn-' + side + '-' + ti + '">' +
              (innRuns != null ? innRuns : "") + '</td>';
    }
    // Total stats for team
    var teamTotals = computeTeamTotals(lineup);
    var tVals = [teamTotals.ab, teamTotals.r, teamTotals.h, teamTotals.rbi, teamTotals.bb, teamTotals.k];
    for (var tt = 0; tt < tVals.length; tt++) {
      html += '<td class="stat-cell total-stat">' + tVals[tt] + '</td>';
    }
    html += '</tr>';

    html += '</tbody></table></div>';
    return html;
  }

  function computeTeamTotals(lineup) {
    var ab = 0, r = 0, h = 0, rbi = 0, bb = 0, k = 0;
    for (var i = 0; i < lineup.length; i++) {
      for (var j = 0; j < lineup[i].batters.length; j++) {
        var s = lineup[i].batters[j].stats || {};
        ab += s.atBats || 0;
        r += s.runs || 0;
        h += s.hits || 0;
        rbi += s.rbi || 0;
        bb += s.baseOnBalls || 0;
        k += s.strikeOuts || 0;
      }
    }
    return { ab: ab, r: r, h: h, rbi: rbi, bb: bb, k: k };
  }

  SC.scorebook = {
    render: function (model, embed) {
      var awayHtml = renderPage(model.away, model.totalInnings, model.pitchingChanges, "away");
      var homeHtml = renderPage(model.home, model.totalInnings, model.pitchingChanges, "home");

      if (embed) {
        var awayAbbr = esc(model.away.team.abbreviation);
        var homeAbbr = esc(model.home.team.abbreviation);
        return '<div class="scorebook-tabs">' +
          '<button class="sb-tab active" data-side="away">' + awayAbbr + '</button>' +
          '<button class="sb-tab" data-side="home">' + homeAbbr + '</button>' +
          '</div>' +
          '<div class="scorebook-spread embed-spread">' +
          '<div class="scorebook-tab-pane active" data-side="away">' + awayHtml + '</div>' +
          '<div class="scorebook-tab-pane" data-side="home">' + homeHtml + '</div>' +
          '</div>';
      }

      return '<div class="scorebook-spread">' + awayHtml + homeHtml + '</div>';
    }
  };
})();
