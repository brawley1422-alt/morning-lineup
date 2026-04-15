(function () {
  "use strict";

  // Morning Lineup times are all rendered as Central Time on the server,
  // e.g. "7:05 CT". This walker rewrites those tokens in place to the
  // viewer's local zone. Runs once on DOM ready. If anything fails,
  // the original CT strings stay intact — graceful degrade.
  //
  // Known edge cases we accept for v1:
  //  - MLB game times are never overnight, so AM/PM is inferred from the
  //    CT hour (11 = AM day game, 12 = noon, 1–10 = PM evening game).
  //  - Rollover across midnight when shifting east (e.g. a late Cubs game
  //    "10:10 CT" → "11:10p ET") does NOT adjust adjacent date labels.
  //    Harmless in practice — MLB games don't start at 11 PM CT.
  //  - DST transitions within the same day can drift by an hour once or
  //    twice a year. Acceptable v1 skew.

  var CT_ZONE = "America/Chicago";
  // Match " 7:05 CT", "12:40 CT", "1:20 CT". Word boundary on the left
  // prevents mangling of things like "5-PCT" or "10%CT" (not that we
  // have those, but cheap to be safe).
  var RE = /(^|[\s\>&;])(\d{1,2}):(\d{2})\s*CT\b/g;

  function tzOffsetMinutes(tz, date) {
    // Returns the offset in minutes such that localWallTime = UTC + offset
    // Uses Intl to read back the wall-clock time of `date` in `tz`, then
    // reconstructs a UTC instant from those fields and diffs it.
    try {
      var dtf = new Intl.DateTimeFormat("en-US", {
        timeZone: tz, hour12: false,
        year: "numeric", month: "2-digit", day: "2-digit",
        hour: "2-digit", minute: "2-digit", second: "2-digit",
      });
      var parts = dtf.formatToParts(date);
      var get = function (type) {
        for (var i = 0; i < parts.length; i++) if (parts[i].type === type) return parts[i].value;
        return "0";
      };
      var asUtc = Date.UTC(
        parseInt(get("year"), 10),
        parseInt(get("month"), 10) - 1,
        parseInt(get("day"), 10),
        parseInt(get("hour"), 10) === 24 ? 0 : parseInt(get("hour"), 10),
        parseInt(get("minute"), 10),
        parseInt(get("second"), 10)
      );
      return (asUtc - date.getTime()) / 60000;
    } catch (e) {
      return 0;
    }
  }

  function tzAbbreviation(tz, date) {
    try {
      var dtf = new Intl.DateTimeFormat("en-US", { timeZone: tz, timeZoneName: "short" });
      var parts = dtf.formatToParts(date);
      for (var i = 0; i < parts.length; i++) {
        if (parts[i].type === "timeZoneName") {
          var v = parts[i].value;
          // Fold EST/EDT → ET, CST/CDT → CT, MST/MDT → MT, PST/PDT → PT, etc.
          if (/^[A-Z]ST$|^[A-Z]DT$/.test(v)) return v[0] + "T";
          if (/^AKST$|^AKDT$/.test(v)) return "AKT";
          return v;
        }
      }
    } catch (e) {}
    return "LT";
  }

  function run() {
    var localTz;
    try { localTz = Intl.DateTimeFormat().resolvedOptions().timeZone; }
    catch (e) { return; }
    if (!localTz || localTz === CT_ZONE) return;

    var now = new Date();
    var ctOff = tzOffsetMinutes(CT_ZONE, now);
    var localOff = tzOffsetMinutes(localTz, now);
    var deltaMin = localOff - ctOff;  // +60 for ET, -60 for MT, -120 for PT
    if (deltaMin === 0) return;

    var abbr = tzAbbreviation(localTz, now);

    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
    var node, toReplace = [];
    while ((node = walker.nextNode())) {
      // Skip script/style content
      var p = node.parentNode;
      if (!p) continue;
      var tag = p.nodeName;
      if (tag === "SCRIPT" || tag === "STYLE" || tag === "NOSCRIPT") continue;
      if (RE.test(node.nodeValue)) toReplace.push(node);
      RE.lastIndex = 0;
    }

    for (var i = 0; i < toReplace.length; i++) {
      var n = toReplace[i];
      n.nodeValue = n.nodeValue.replace(RE, function (m, lead, hStr, mStr) {
        var h = parseInt(hStr, 10);
        var mm = parseInt(mStr, 10);
        // Infer 24h from MLB convention: 11 = AM, else PM (12 = noon, 1–10 = evening)
        var h24;
        if (h === 11) h24 = 11;
        else if (h === 12) h24 = 12;
        else h24 = h + 12;
        var total = h24 * 60 + mm + deltaMin;
        total = ((total % 1440) + 1440) % 1440;
        var newH24 = Math.floor(total / 60);
        var newMm = total % 60;
        var newH12 = newH24 % 12;
        if (newH12 === 0) newH12 = 12;
        var mmStr = newMm < 10 ? "0" + newMm : "" + newMm;
        return lead + newH12 + ":" + mmStr + " " + abbr;
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
