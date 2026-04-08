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

  SC.diamond = {
    render: function (atBat) {
      if (!atBat) return '<div class="diamond-cell empty"></div>';

      var reached = atBat.basesReached || 0;
      var type = atBat.type || "out";
      var notation = atBat.notation || "?";

      // Determine color class for basepaths and text
      var pathClass = "hit";
      var textClass = "hit-text";
      if (type === "walk") { pathClass = "walk"; textClass = "walk-text"; }
      else if (type === "error") { pathClass = "error"; textClass = "error-text"; }
      else if (type === "fc") { pathClass = "fc"; textClass = "out-text"; }
      else if (type === "out") { pathClass = ""; textClass = "out-text"; }

      var svg = '<svg viewBox="0 0 60 60" width="56" height="56">';

      // Diamond outline
      svg += '<polygon points="' + HP.join(",") + " " + B1.join(",") + " " +
             B2.join(",") + " " + B3.join(",") + '" class="diamond-outline"/>';

      // Basepaths
      for (var i = 0; i < PATHS.length; i++) {
        var p = PATHS[i];
        var active = false;
        if (type === "walk" || type === "error" || type === "fc") {
          // walks/errors/FC: show dot only, no basepath lines
          active = false;
        } else if (reached >= (i + 1)) {
          active = true;
        }
        svg += '<line x1="' + p.from[0] + '" y1="' + p.from[1] +
               '" x2="' + p.to[0] + '" y2="' + p.to[1] +
               '" class="basepath ' + (active ? "active " + pathClass : "") + '"/>';
      }

      // Base dots (1B, 2B, 3B)
      var bases = [B1, B2, B3];
      var dotClass = "reached";
      if (type === "walk") dotClass = "walk-reached";
      else if (type === "error") dotClass = "error-reached";

      for (var b = 0; b < bases.length; b++) {
        var baseReached = reached >= (b + 1);
        svg += '<circle cx="' + bases[b][0] + '" cy="' + bases[b][1] +
               '" class="base-dot' + (baseReached ? " " + dotClass : "") + '"/>';
      }

      // Hit type text (center)
      var fontSize = notation.length > 3 ? 9 : (notation.length > 2 ? 10 : 11);
      svg += '<text x="30" y="31" class="hit-type ' + textClass + '" ' +
             'style="font-size:' + fontSize + 'px">' + esc(notation) + '</text>';

      // Out number (bottom-right)
      if (atBat.isOut && atBat.outNumber > 0) {
        svg += '<text x="50" y="56" class="out-num">' + atBat.outNumber + '</text>';
      }

      // RBI dots (top-left area)
      for (var r = 0; r < (atBat.rbi || 0); r++) {
        svg += '<circle cx="' + (8 + r * 7) + '" cy="8" r="2.5" class="rbi-dot"/>';
      }

      // Run scored marker (filled circle at home)
      if (atBat.runScored) {
        svg += '<circle cx="' + HP[0] + '" cy="' + HP[1] + '" r="4" class="run-scored"/>';
      }

      svg += '</svg>';

      // Wrap with data attributes for tooltip
      return '<div class="diamond-cell" ' +
             'data-desc="' + esc(atBat.description) + '" ' +
             'data-notation="' + esc(notation) + '" ' +
             'data-fielding="' + esc(atBat.fieldingSeq || "") + '" ' +
             'data-pitches="' + esc(JSON.stringify(atBat.pitchCount || [])) + '" ' +
             'data-rbi="' + (atBat.rbi || 0) + '">' +
             svg + '</div>';
    },

    renderEmpty: function () {
      return '<div class="diamond-cell empty"></div>';
    }
  };
})();
