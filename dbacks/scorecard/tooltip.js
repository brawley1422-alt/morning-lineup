(function () {
  "use strict";
  var SC = window.Scorecard = window.Scorecard || {};

  var tipEl = null;
  var activeCell = null;

  function hide() {
    if (tipEl) tipEl.classList.remove("visible");
    activeCell = null;
  }

  function show(cell, rect) {
    if (!tipEl) tipEl = document.getElementById("tooltip");
    if (!tipEl) return;

    var desc = cell.getAttribute("data-desc") || "";
    var notation = cell.getAttribute("data-notation") || "";
    var fielding = cell.getAttribute("data-fielding") || "";
    var rbi = cell.getAttribute("data-rbi") || "0";
    var pitchesJSON = cell.getAttribute("data-pitches") || "[]";

    if (!desc) { hide(); return; }

    var pitches = [];
    try { pitches = JSON.parse(pitchesJSON); } catch (e) { pitches = []; }

    var html = '<div class="tip-desc">' + escHTML(desc) + '</div>';

    if (fielding) {
      html += '<div class="tip-row"><span class="tip-label">Fielding:</span> ' + escHTML(fielding) + '</div>';
    }
    if (parseInt(rbi, 10) > 0) {
      html += '<div class="tip-row"><span class="tip-label">RBI:</span> ' + rbi + '</div>';
    }

    // Pitch count
    if (pitches.length) {
      var balls = 0, strikes = 0;
      for (var i = 0; i < pitches.length; i++) {
        var c = pitches[i].call;
        if (c === "B") balls++;
        else if (c === "S" || c === "C" || c === "F" || c === "T" || c === "L" || c === "W" || c === "M") strikes++;
      }
      html += '<div class="tip-row"><span class="tip-label">Count:</span> ' + balls + '-' + strikes +
              ' (' + pitches.length + ' pitches)</div>';

      // Pitch sequence chips
      html += '<div class="tip-pitches">';
      for (var j = 0; j < pitches.length; j++) {
        var p = pitches[j];
        var chipClass = "pitch-chip";
        if (p.call === "B") chipClass += " ball";
        else if (p.call === "X" || p.call === "E" || p.call === "D") chipClass += " inplay";
        else chipClass += " strike";
        var label = (p.type || "?") + "-" + (p.call || "?");
        html += '<span class="' + chipClass + '">' + escHTML(label) + '</span>';
      }
      html += '</div>';
    }

    tipEl.innerHTML = html;
    tipEl.classList.add("visible");

    // Position tooltip
    var tipW = tipEl.offsetWidth;
    var tipH = tipEl.offsetHeight;
    var vw = window.innerWidth;
    var vh = window.innerHeight;

    var left = rect.left + rect.width / 2 - tipW / 2;
    var top = rect.top - tipH - 8;

    // Flip below if too close to top
    if (top < 8) top = rect.bottom + 8;
    // Clamp horizontal
    if (left < 8) left = 8;
    if (left + tipW > vw - 8) left = vw - tipW - 8;
    // Clamp vertical
    if (top + tipH > vh - 8) top = vh - tipH - 8;

    tipEl.style.left = left + "px";
    tipEl.style.top = top + "px";
  }

  function escHTML(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  SC.tooltip = {
    init: function () {
      tipEl = document.getElementById("tooltip");

      // Delegated mouse events on desktop
      document.addEventListener("mouseover", function (e) {
        var cell = e.target.closest(".diamond-cell");
        if (cell && !cell.classList.contains("empty")) {
          activeCell = cell;
          show(cell, cell.getBoundingClientRect());
        }
      });

      document.addEventListener("mouseout", function (e) {
        var cell = e.target.closest(".diamond-cell");
        if (cell && cell === activeCell) {
          hide();
        }
      });

      // Touch support: tap to toggle
      document.addEventListener("click", function (e) {
        var cell = e.target.closest(".diamond-cell");
        if (cell && !cell.classList.contains("empty")) {
          if (activeCell === cell) {
            hide();
          } else {
            activeCell = cell;
            show(cell, cell.getBoundingClientRect());
          }
        } else {
          hide();
        }
      });
    }
  };
})();
