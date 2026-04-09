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

    // Journey narrative
    var journeyJSON = cell.getAttribute("data-journey") || "";
    if (journeyJSON) {
      var segs = [];
      try { segs = JSON.parse(journeyJSON); } catch (e) {}
      if (segs.length > 1) {
        html += '<div class="tip-journey">';
        for (var si = 0; si < segs.length; si++) {
          var seg = segs[si];
          if (seg.how === "initial") continue;
          var arrow = '<span class="tip-journey-arrow">\u2192</span>';
          var label = (seg.to === "score" ? "Scored" : seg.to) + " on " + (seg.cause || seg.how);
          html += '<div class="tip-journey-step">' + arrow + ' ' + escHTML(label) + '</div>';
        }
        html += '</div>';
      }
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

  // ── Strike Zone Overlay ──

  var zoneOverlay = null;

  function hideZone() {
    if (zoneOverlay) zoneOverlay.classList.remove("visible");
  }

  // Pitch type → color mapping
  var PITCH_COLORS = {
    FF: "#e8544f", SI: "#d94f8a", FC: "#c0554f",   // fastballs — reds
    SL: "#5b8dd9", CU: "#4fc4e8", KC: "#4fc4e8",   // breaking — blues
    CH: "#6ea86a", FS: "#8bc76e",                    // offspeed — greens
    ST: "#b87fd9", SV: "#b87fd9",                    // sweeper — purple
    KN: "#c9a24a"                                     // knuckle — gold
  };
  var DEFAULT_PITCH_COLOR = "#8b836d";

  function showZone(cell) {
    if (!zoneOverlay) {
      zoneOverlay = document.getElementById("zone-overlay");
      if (!zoneOverlay) return;
    }

    var pitchesJSON = cell.getAttribute("data-pitches") || "[]";
    var desc = cell.getAttribute("data-desc") || "";
    var notation = cell.getAttribute("data-notation") || "";
    var pitches;
    try { pitches = JSON.parse(pitchesJSON); } catch (e) { return; }

    // Need at least one pitch with coordinates
    var hasCoords = false;
    for (var i = 0; i < pitches.length; i++) {
      if (pitches[i].pX != null && pitches[i].pZ != null) { hasCoords = true; break; }
    }
    if (!hasCoords) return;

    // Average strike zone top/bottom from pitches (personalized per batter)
    var szTop = 3.5, szBot = 1.5;
    var topSum = 0, botSum = 0, szCount = 0;
    for (var j = 0; j < pitches.length; j++) {
      if (pitches[j].szTop != null && pitches[j].szBot != null) {
        topSum += pitches[j].szTop;
        botSum += pitches[j].szBot;
        szCount++;
      }
    }
    if (szCount > 0) {
      szTop = topSum / szCount;
      szBot = botSum / szCount;
    }

    // Build SVG strike zone
    // Coordinate system: pX is in feet from center of plate (-0.83 to 0.83 for the zone)
    // pZ is height in feet. We map to a 200x240 SVG viewport.
    var svgW = 200, svgH = 240;
    var plateHalf = 0.83; // half plate width in feet (17 inches / 2 / 12)
    var margin = 1.2; // show this many feet beyond zone edges

    var xMin = -margin, xMax = margin;
    var zMin = szBot - 0.6, zMax = szTop + 0.6;

    function mapX(px) { return ((px - xMin) / (xMax - xMin)) * svgW; }
    function mapZ(pz) { return svgH - ((pz - zMin) / (zMax - zMin)) * svgH; }

    var svg = '<svg viewBox="0 0 ' + svgW + ' ' + svgH + '" class="zone-svg">';

    // Strike zone box
    var zLeft = mapX(-plateHalf), zRight = mapX(plateHalf);
    var zTop = mapZ(szTop), zBottom = mapZ(szBot);
    svg += '<rect x="' + zLeft + '" y="' + zTop + '" width="' + (zRight - zLeft) +
           '" height="' + (zBottom - zTop) + '" class="zone-box"/>';

    // Zone grid lines (3x3)
    var thirdW = (zRight - zLeft) / 3;
    var thirdH = (zBottom - zTop) / 3;
    svg += '<line x1="' + (zLeft + thirdW) + '" y1="' + zTop + '" x2="' + (zLeft + thirdW) + '" y2="' + zBottom + '" class="zone-grid"/>';
    svg += '<line x1="' + (zLeft + thirdW * 2) + '" y1="' + zTop + '" x2="' + (zLeft + thirdW * 2) + '" y2="' + zBottom + '" class="zone-grid"/>';
    svg += '<line x1="' + zLeft + '" y1="' + (zTop + thirdH) + '" x2="' + zRight + '" y2="' + (zTop + thirdH) + '" class="zone-grid"/>';
    svg += '<line x1="' + zLeft + '" y1="' + (zTop + thirdH * 2) + '" x2="' + zRight + '" y2="' + (zTop + thirdH * 2) + '" class="zone-grid"/>';

    // Home plate shape at bottom
    var hpY = mapZ(szBot - 0.45);
    var hpCx = svgW / 2;
    svg += '<polygon points="' +
           (hpCx - 12) + ',' + hpY + ' ' +
           (hpCx + 12) + ',' + hpY + ' ' +
           (hpCx + 12) + ',' + (hpY + 6) + ' ' +
           hpCx + ',' + (hpY + 12) + ' ' +
           (hpCx - 12) + ',' + (hpY + 6) +
           '" class="zone-plate"/>';

    // Pitch dots — numbered in sequence
    for (var k = 0; k < pitches.length; k++) {
      var p = pitches[k];
      if (p.pX == null || p.pZ == null) continue;
      var cx = mapX(p.pX);
      var cy = mapZ(p.pZ);
      var color = PITCH_COLORS[p.type] || DEFAULT_PITCH_COLOR;
      var r = 8;

      svg += '<circle cx="' + cx + '" cy="' + cy + '" r="' + r +
             '" fill="' + color + '" fill-opacity="0.85" stroke="' + color +
             '" stroke-width="1.5" stroke-opacity="0.4" class="zone-pitch"/>';
      svg += '<text x="' + cx + '" y="' + (cy + 3.5) + '" class="zone-pitch-num">' + (k + 1) + '</text>';
    }

    svg += '</svg>';

    // Legend
    var legend = '<div class="zone-legend">';
    var seen = {};
    for (var m = 0; m < pitches.length; m++) {
      var pt = pitches[m].type || "?";
      if (seen[pt]) continue;
      seen[pt] = true;
      var col = PITCH_COLORS[pt] || DEFAULT_PITCH_COLOR;
      legend += '<span class="zone-leg-item"><span class="zone-leg-dot" style="background:' + col + '"></span>' + escHTML(pt) + '</span>';
    }
    legend += '</div>';

    // Pitch sequence detail
    var seq = '<div class="zone-seq">';
    for (var n = 0; n < pitches.length; n++) {
      var pi = pitches[n];
      var chipCls = "zone-chip";
      if (pi.call === "B") chipCls += " ball";
      else if (pi.call === "X" || pi.call === "E" || pi.call === "D") chipCls += " inplay";
      else chipCls += " strike";
      var speedStr = pi.speed ? ' ' + Math.round(pi.speed) : '';
      seq += '<span class="' + chipCls + '"><span class="zone-chip-num">' + (n + 1) + '</span>' +
             escHTML(pi.type || "?") + speedStr + '</span>';
    }
    seq += '</div>';

    // Result line
    var result = '<div class="zone-result">' + escHTML(notation) + ' — ' + escHTML(desc) + '</div>';

    zoneOverlay.innerHTML =
      '<div class="zone-card">' +
        '<button class="zone-close" aria-label="Close">&times;</button>' +
        svg + legend + seq + result +
      '</div>';

    zoneOverlay.classList.add("visible");

    // Close button
    zoneOverlay.querySelector(".zone-close").addEventListener("click", function (e) {
      e.stopPropagation();
      hideZone();
    });
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

      // Click → open strike zone overlay
      document.addEventListener("click", function (e) {
        // Close zone overlay if clicking backdrop
        if (e.target.classList && e.target.classList.contains("zone-overlay")) {
          hideZone();
          return;
        }

        var cell = e.target.closest(".diamond-cell");
        if (cell && !cell.classList.contains("empty")) {
          hide(); // hide tooltip
          showZone(cell);
        }
      });
    }
  };
})();
