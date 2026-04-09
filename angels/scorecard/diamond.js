(function () {
  "use strict";
  var SC = window.Scorecard = window.Scorecard || {};

  // Diamond geometry (60x60 viewBox)
  // Home plate at bottom (30,52), 1B right (52,30), 2B top (30,8), 3B left (8,30)
  var HP = [30, 52], B1 = [52, 30], B2 = [30, 8], B3 = [8, 30];

  var PATHS = [
    { from: HP, to: B1, cls: "first" },   // home → 1B
    { from: B1, to: B2, cls: "second" },   // 1B → 2B
    { from: B2, to: B3, cls: "third" },    // 2B → 3B
    { from: B3, to: HP, cls: "home" }      // 3B → home
  ];

  function esc(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
  }

  // Map base names to path indices (HP→1B=0, 1B→2B=1, 2B→3B=2, 3B→HP=3)
  var BASE_INDEX = { "1B": 0, "2B": 1, "3B": 2, "score": 3 };
  // Midpoints for advancement cause labels
  var PATH_MID = [[41,41],[41,19],[19,19],[19,41]];

  function getPathRange(from, to) {
    // Returns array of path indices covered by this movement
    var startIdx = (from == null) ? 0 : (BASE_INDEX[from] != null ? BASE_INDEX[from] + 1 : 0);
    var endIdx = BASE_INDEX[to] != null ? BASE_INDEX[to] + 1 : 0;
    var indices = [];
    for (var i = startIdx; i < endIdx && i < 4; i++) indices.push(i);
    return indices;
  }

  SC.diamond = {
    render: function (atBat) {
      if (!atBat) return '<div class="diamond-cell empty"></div>';

      var reached = atBat.basesReached || 0;
      var type = atBat.type || "out";
      var notation = atBat.notation || "?";
      var journey = atBat.journey || null;

      // Determine color class for basepaths and text
      var pathClass = "hit";
      var textClass = "hit-text";
      if (type === "walk") { pathClass = "walk"; textClass = "walk-text"; }
      else if (type === "error") { pathClass = "error"; textClass = "error-text"; }
      else if (type === "fc") { pathClass = "fc"; textClass = "out-text"; }
      else if (type === "out") { pathClass = ""; textClass = "out-text"; }

      var svg = '<svg viewBox="0 0 60 60" width="56" height="56">';

      // Filled diamond background for runs scored
      if ((journey && journey.scored) || atBat.runScored) {
        svg += '<polygon points="' + HP.join(",") + " " + B1.join(",") + " " +
               B2.join(",") + " " + B3.join(",") + '" class="diamond-scored"/>';
      }

      // Diamond outline
      svg += '<polygon points="' + HP.join(",") + " " + B1.join(",") + " " +
             B2.join(",") + " " + B3.join(",") + '" class="diamond-outline"/>';

      // Journey-aware basepaths
      if (journey && journey.segments && journey.segments.length > 0) {
        // Track which paths are rendered and how
        var pathRendered = [false, false, false, false];

        for (var si = 0; si < journey.segments.length; si++) {
          var seg = journey.segments[si];
          var indices = getPathRange(seg.from, seg.to);
          var isDashed = seg.how !== "initial";
          var segClass = pathClass;
          if (seg.how === "SB") segClass = "sb";
          else if (seg.how === "CS") segClass = "cs";

          for (var pi = 0; pi < indices.length; pi++) {
            var idx = indices[pi];
            if (pathRendered[idx]) continue;
            pathRendered[idx] = true;
            var p = PATHS[idx];
            var dashAttr = isDashed ? ' stroke-dasharray="4,3"' : '';
            var cls = isDashed ? "basepath active advance " + segClass : "basepath active " + segClass;
            svg += '<line x1="' + p.from[0] + '" y1="' + p.from[1] +
                   '" x2="' + p.to[0] + '" y2="' + p.to[1] +
                   '" class="' + cls + '"' + dashAttr + '/>';
          }

          // Advancement cause label (for non-initial segments)
          if (isDashed && seg.cause && indices.length > 0) {
            var labelIdx = indices[0];
            var mid = PATH_MID[labelIdx];
            svg += '<text x="' + mid[0] + '" y="' + mid[1] +
                   '" class="advance-label">' + esc(seg.cause) + '</text>';
          }
        }

        // Render remaining untraversed paths as inactive
        for (var ri = 0; ri < 4; ri++) {
          if (!pathRendered[ri]) {
            var rp = PATHS[ri];
            svg += '<line x1="' + rp.from[0] + '" y1="' + rp.from[1] +
                   '" x2="' + rp.to[0] + '" y2="' + rp.to[1] +
                   '" class="basepath"/>';
          }
        }
      } else {
        // No journey data — use existing basesReached logic
        for (var i = 0; i < PATHS.length; i++) {
          var p = PATHS[i];
          var active = false;
          if (type === "walk" || type === "error" || type === "fc") {
            active = false;
          } else if (reached >= (i + 1)) {
            active = true;
          }
          svg += '<line x1="' + p.from[0] + '" y1="' + p.from[1] +
                 '" x2="' + p.to[0] + '" y2="' + p.to[1] +
                 '" class="basepath ' + (active ? "active " + pathClass : "") + '"/>';
        }
      }

      // Base dots (1B, 2B, 3B)
      var bases = [B1, B2, B3];
      var dotClass = "reached";
      if (type === "walk") dotClass = "walk-reached";
      else if (type === "error") dotClass = "error-reached";

      // Determine highest base reached (accounting for journey)
      var effectiveReached = reached;
      if (journey && journey.finalEnd) {
        var finalBase = { "1B": 1, "2B": 2, "3B": 3, "score": 4 };
        var fb = finalBase[journey.finalEnd] || 0;
        if (fb > effectiveReached) effectiveReached = fb;
      }

      for (var b = 0; b < bases.length; b++) {
        var baseReached = effectiveReached >= (b + 1);
        svg += '<circle cx="' + bases[b][0] + '" cy="' + bases[b][1] +
               '" class="base-dot' + (baseReached ? " " + dotClass : "") + '"/>';
      }

      // Hit type text (center)
      var fontSize = notation.length > 3 ? 10 : (notation.length > 2 ? 11 : 12);
      svg += '<text x="30" y="31" class="hit-type ' + textClass + '" ' +
             'style="font-size:' + fontSize + 'px">' + esc(notation) + '</text>';

      // Out number (bottom-right) — circled, traditional convention
      if (atBat.isOut && atBat.outNumber > 0) {
        svg += '<circle cx="50" cy="52" r="6" class="out-circle"/>';
        svg += '<text x="50" y="53" class="out-num">' + atBat.outNumber + '</text>';
      }

      // RBI dots (top-left area)
      for (var r = 0; r < (atBat.rbi || 0); r++) {
        svg += '<circle cx="' + (8 + r * 7) + '" cy="8" r="2.5" class="rbi-dot"/>';
      }

      // Run scored marker (small dot at home, in addition to filled diamond)
      if ((journey && journey.scored) || atBat.runScored) {
        svg += '<circle cx="' + HP[0] + '" cy="' + HP[1] + '" r="3" class="run-scored"/>';
      }

      svg += '</svg>';

      // Wrap with data attributes for tooltip
      var journeyData = journey ? esc(JSON.stringify(journey.segments)) : "";
      return '<div class="diamond-cell" ' +
             'data-desc="' + esc(atBat.description) + '" ' +
             'data-notation="' + esc(notation) + '" ' +
             'data-fielding="' + esc(atBat.fieldingSeq || "") + '" ' +
             'data-pitches="' + esc(JSON.stringify(atBat.pitchCount || [])) + '" ' +
             'data-rbi="' + (atBat.rbi || 0) + '" ' +
             'data-journey="' + journeyData + '">' +
             svg + '</div>';
    },

    renderEmpty: function () {
      return '<div class="diamond-cell empty"></div>';
    }
  };
})();
