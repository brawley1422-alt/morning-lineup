(function () {
  "use strict";
  var SC = window.Scorecard = window.Scorecard || {};

  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  SC.header = {
    render: function (model) {
      var away = model.away;
      var home = model.home;

      var html = '<div class="game-header">';

      // Title row: TEAM SCORE vs SCORE TEAM
      html += '<div class="title-row">';
      html += '<span class="team-name">' + esc(away.team.teamName) + '</span>';
      html += '<span class="final-score">' + away.totals.runs + '</span>';
      html += '<span class="vs">&ndash;</span>';
      html += '<span class="final-score">' + home.totals.runs + '</span>';
      html += '<span class="team-name">' + esc(home.team.teamName) + '</span>';
      html += '</div>';

      // Details row
      var dateStr = model.date || "";
      html += '<div class="details-row">';
      html += esc(model.venue) + ' &bull; ' + esc(dateStr);
      if (model.time) html += ' &bull; ' + esc(model.time + " " + (model.ampm || ""));
      html += '</div>';

      // Line score table
      html += '<table class="line-score"><thead><tr>';
      html += '<th></th>';
      for (var i = 1; i <= model.totalInnings; i++) {
        html += '<th>' + i + '</th>';
      }
      html += '<th>R</th><th>H</th><th>E</th>';
      html += '</tr></thead><tbody>';

      // Away row
      html += '<tr><td class="team-col">' + esc(away.team.abbreviation) + '</td>';
      for (var a = 0; a < model.totalInnings; a++) {
        html += '<td>' + (away.linescore[a] != null ? away.linescore[a] : "") + '</td>';
      }
      html += '<td class="rhe">' + away.totals.runs + '</td>';
      html += '<td class="rhe">' + away.totals.hits + '</td>';
      html += '<td class="rhe">' + away.totals.errors + '</td>';
      html += '</tr>';

      // Home row
      html += '<tr><td class="team-col">' + esc(home.team.abbreviation) + '</td>';
      for (var h = 0; h < model.totalInnings; h++) {
        html += '<td>' + (home.linescore[h] != null ? home.linescore[h] : "") + '</td>';
      }
      html += '<td class="rhe">' + home.totals.runs + '</td>';
      html += '<td class="rhe">' + home.totals.hits + '</td>';
      html += '<td class="rhe">' + home.totals.errors + '</td>';
      html += '</tr>';

      html += '</tbody></table>';

      // Decisions
      html += '<div class="decisions">';
      if (model.decisions.winner) {
        html += '<span><span class="label">W:</span> ' + esc(model.decisions.winner.name) + '</span>';
      }
      if (model.decisions.loser) {
        html += '<span><span class="label">L:</span> ' + esc(model.decisions.loser.name) + '</span>';
      }
      if (model.decisions.save) {
        html += '<span><span class="label">S:</span> ' + esc(model.decisions.save.name) + '</span>';
      }
      html += '</div>';

      html += '</div>';
      return html;
    }
  };
})();
