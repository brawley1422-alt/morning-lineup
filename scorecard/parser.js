(function () {
  "use strict";
  var SC = window.Scorecard = window.Scorecard || {};

  // eventType → display notation
  var NOTATION = {
    single: "1B", double: "2B", triple: "3B", home_run: "HR",
    strikeout: "K", strikeout_double_play: "K",
    walk: "BB", intent_walk: "IBB", hit_by_pitch: "HBP",
    sac_fly: "SF", sac_bunt: "SAC", sac_fly_double_play: "SF",
    grounded_into_double_play: "GDP", double_play: "DP", triple_play: "TP",
    fielders_choice: "FC", fielders_choice_out: "FC",
    catcher_interf: "CI",
    field_error: "E",
    caught_stealing: "CS", stolen_base: "SB",
    pickoff: "PO", wild_pitch: "WP", passed_ball: "PB", balk: "BK"
  };

  var HIT_TYPES = { single: 1, double: 1, triple: 1, home_run: 1 };
  var WALK_TYPES = { walk: 1, intent_walk: 1, hit_by_pitch: 1, catcher_interf: 1 };
  var OUT_TYPES = {
    strikeout: 1, strikeout_double_play: 1, field_out: 1,
    grounded_into_double_play: 1, double_play: 1, triple_play: 1,
    fielders_choice_out: 1, sac_fly: 1, sac_bunt: 1, sac_fly_double_play: 1,
    force_out: 1
  };

  function getFieldingSequence(runners) {
    var credits = [];
    for (var i = 0; i < runners.length; i++) {
      var r = runners[i];
      if (r.credits) {
        for (var j = 0; j < r.credits.length; j++) {
          var c = r.credits[j];
          var pos = c.position && c.position.code;
          if (!pos) continue;
          credits.push({ pos: pos, type: c.credit });
        }
      }
    }
    if (!credits.length) return "";
    // assists first, then putout
    var assists = [], putouts = [];
    for (var k = 0; k < credits.length; k++) {
      if (credits[k].type === "f_putout") putouts.push(credits[k].pos);
      else assists.push(credits[k].pos);
    }
    // deduplicate consecutive (e.g., "6-6-3" → "6-3")
    var seq = assists.concat(putouts);
    var deduped = [seq[0]];
    for (var m = 1; m < seq.length; m++) {
      if (seq[m] !== seq[m - 1]) deduped.push(seq[m]);
    }
    return deduped.join("-");
  }

  function getNotation(play) {
    var et = play.result.eventType || "";
    var base = NOTATION[et];

    // field_out: use fielding sequence
    if (et === "field_out" || et === "force_out") {
      var fs = getFieldingSequence(play.runners || []);
      return fs || (play.result.event || "Out");
    }
    // field_error: add position number
    if (et === "field_error") {
      var errFs = getFieldingSequence(play.runners || []);
      if (errFs) return "E" + errFs.charAt(0);
      return "E";
    }
    // GDP/DP: include fielding sequence
    if (et === "grounded_into_double_play" || et === "double_play" || et === "triple_play") {
      var dpFs = getFieldingSequence(play.runners || []);
      return dpFs || (base || "DP");
    }
    // strikeout looking vs swinging
    if (et === "strikeout" || et === "strikeout_double_play") {
      var desc = (play.result.description || "").toLowerCase();
      return desc.indexOf("called") >= 0 ? "\u0198" : "K"; // Ƙ for looking
    }

    return base || play.result.event || "?";
  }

  function getBatterEnd(play) {
    var runners = play.runners || [];
    for (var i = 0; i < runners.length; i++) {
      var r = runners[i];
      var start = r.movement && r.movement.start;
      if (!start || start === "") {
        // This is the batter
        return {
          end: r.movement.end || null,
          isOut: r.movement.isOut || false
        };
      }
    }
    return { end: null, isOut: play.result.isOut || false };
  }

  function classifyType(et) {
    if (HIT_TYPES[et]) return "hit";
    if (WALK_TYPES[et]) return "walk";
    if (et === "field_error") return "error";
    if (et === "fielders_choice" || et === "force_out") return "fc";
    return "out";
  }

  function basesReached(endBase) {
    if (!endBase) return 0;
    if (endBase === "1B") return 1;
    if (endBase === "2B") return 2;
    if (endBase === "3B") return 3;
    if (endBase === "score") return 4;
    return 0;
  }

  function getPitchSequence(playEvents) {
    if (!playEvents) return [];
    var pitches = [];
    for (var i = 0; i < playEvents.length; i++) {
      var pe = playEvents[i];
      if (pe.isPitch) {
        var d = pe.details || {};
        pitches.push({
          type: (d.type && d.type.code) || "",
          call: (d.call && d.call.code) || "",
          desc: (d.call && d.call.description) || "",
          speed: pe.pitchData && pe.pitchData.startSpeed
        });
      }
    }
    return pitches;
  }

  function parseAtBat(play) {
    var et = play.result.eventType || "";
    var batter = getBatterEnd(play);
    var outCount = 0;
    var outNumber = 0;
    var runners = play.runners || [];
    for (var i = 0; i < runners.length; i++) {
      if (runners[i].movement && runners[i].movement.isOut) {
        outCount++;
        var on = runners[i].movement.outNumber;
        if (on && on > outNumber) outNumber = on;
      }
    }

    return {
      inning: play.about.inning,
      halfInning: play.about.halfInning,
      atBatIndex: play.about.atBatIndex,
      batterId: play.matchup.batter.id,
      batterName: play.matchup.batter.fullName,
      pitcherId: play.matchup.pitcher.id,
      pitcherName: play.matchup.pitcher.fullName,
      eventType: et,
      notation: getNotation(play),
      type: classifyType(et),
      description: play.result.description || "",
      rbi: play.result.rbi || 0,
      isOut: play.result.isOut || false,
      outsOnPlay: outCount,
      outNumber: outNumber,
      batterEnd: batter.end,
      batterOut: batter.isOut,
      basesReached: basesReached(batter.end),
      runScored: batter.end === "score",
      pitchCount: getPitchSequence(play.playEvents || []),
      fieldingSeq: getFieldingSequence(runners)
    };
  }

  function buildLineup(boxPlayers) {
    var slots = {};
    var playerKeys = Object.keys(boxPlayers);
    for (var i = 0; i < playerKeys.length; i++) {
      var key = playerKeys[i];
      var p = boxPlayers[key];
      var bo = p.battingOrder;
      if (!bo) continue;
      var boNum = parseInt(bo, 10);
      var slot = Math.floor(boNum / 100);
      var subIdx = boNum % 100;
      if (!slots[slot]) slots[slot] = [];
      slots[slot].push({
        id: p.person.id,
        name: p.person.fullName,
        position: (p.position && p.position.abbreviation) || "",
        jerseyNumber: p.jerseyNumber || "",
        isStarter: subIdx === 0,
        subIndex: subIdx,
        atBats: [],
        stats: (p.stats && p.stats.batting) || {}
      });
    }

    var lineup = [];
    for (var s = 1; s <= 9; s++) {
      var batters = slots[s] || [];
      batters.sort(function (a, b) { return a.subIndex - b.subIndex; });
      lineup.push({ slot: s, batters: batters });
    }
    return lineup;
  }

  function detectPitchingChanges(allPlays) {
    var changes = [];
    for (var i = 0; i < allPlays.length; i++) {
      var play = allPlays[i];
      var events = play.playEvents || [];
      for (var j = 0; j < events.length; j++) {
        var ev = events[j];
        if (ev.type === "action" && ev.details &&
            ev.details.eventType === "pitching_substitution") {
          changes.push({
            inning: play.about.inning,
            halfInning: play.about.halfInning,
            description: ev.details.description || "",
            pitcherName: ev.player && ev.player.fullName || ""
          });
        }
      }
    }
    return changes;
  }

  function buildPitchers(boxPlayers) {
    var pitchers = [];
    var keys = Object.keys(boxPlayers);
    for (var i = 0; i < keys.length; i++) {
      var p = boxPlayers[keys[i]];
      if (p.stats && p.stats.pitching && p.stats.pitching.inningsPitched) {
        var ps = p.stats.pitching;
        pitchers.push({
          id: p.person.id,
          name: p.person.fullName,
          ip: ps.inningsPitched,
          h: ps.hits || 0,
          r: ps.runs || 0,
          er: ps.earnedRuns || 0,
          bb: ps.baseOnBalls || 0,
          k: ps.strikeOuts || 0,
          pitchCount: ps.numberOfPitches || 0
        });
      }
    }
    return pitchers;
  }

  SC.parser = {
    parse: function (feed) {
      var gd = feed.gameData;
      var ld = feed.liveData;
      var box = ld.boxscore;
      var ls = ld.linescore;
      var allPlays = ld.plays.allPlays || [];

      // Build lineups
      var awayLineup = buildLineup(box.teams.away.players);
      var homeLineup = buildLineup(box.teams.home.players);

      // Map batter IDs to lineup slot/index
      var batterMap = {};
      function mapBatters(lineup, side) {
        for (var i = 0; i < lineup.length; i++) {
          var slot = lineup[i];
          for (var j = 0; j < slot.batters.length; j++) {
            batterMap[slot.batters[j].id] = { side: side, slot: i, batter: j };
          }
        }
      }
      mapBatters(awayLineup, "away");
      mapBatters(homeLineup, "home");

      // Parse all at-bats and assign to lineup
      for (var i = 0; i < allPlays.length; i++) {
        var play = allPlays[i];
        if (play.result.type !== "atBat") continue;
        var ab = parseAtBat(play);
        var loc = batterMap[ab.batterId];
        if (!loc) continue;
        var lineup = loc.side === "away" ? awayLineup : homeLineup;
        lineup[loc.slot].batters[loc.batter].atBats.push(ab);
      }

      // Linescore arrays
      var innings = ls.innings || [];
      var awayLine = [], homeLine = [];
      for (var n = 0; n < innings.length; n++) {
        awayLine.push(innings[n].away ? (innings[n].away.runs || 0) : 0);
        homeLine.push(innings[n].home != null ? (innings[n].home.runs || 0) : 0);
      }

      var decisions = ld.decisions || {};

      return {
        gamePk: gd.game.pk,
        date: gd.datetime.officialDate || "",
        time: gd.datetime.time || "",
        ampm: gd.datetime.ampm || "",
        venue: (gd.venue && gd.venue.name) || "",
        status: gd.status.abstractGameState,

        away: {
          team: {
            id: gd.teams.away.id,
            name: gd.teams.away.name,
            abbreviation: gd.teams.away.abbreviation,
            teamName: gd.teams.away.teamName
          },
          record: gd.teams.away.record || {},
          lineup: awayLineup,
          pitchers: buildPitchers(box.teams.away.players),
          linescore: awayLine,
          totals: {
            runs: (ls.teams.away && ls.teams.away.runs) || 0,
            hits: (ls.teams.away && ls.teams.away.hits) || 0,
            errors: (ls.teams.away && ls.teams.away.errors) || 0
          }
        },

        home: {
          team: {
            id: gd.teams.home.id,
            name: gd.teams.home.name,
            abbreviation: gd.teams.home.abbreviation,
            teamName: gd.teams.home.teamName
          },
          record: gd.teams.home.record || {},
          lineup: homeLineup,
          pitchers: buildPitchers(box.teams.home.players),
          linescore: homeLine,
          totals: {
            runs: (ls.teams.home && ls.teams.home.runs) || 0,
            hits: (ls.teams.home && ls.teams.home.hits) || 0,
            errors: (ls.teams.home && ls.teams.home.errors) || 0
          }
        },

        decisions: {
          winner: decisions.winner ? { id: decisions.winner.id, name: decisions.winner.fullName } : null,
          loser: decisions.loser ? { id: decisions.loser.id, name: decisions.loser.fullName } : null,
          save: decisions.save ? { id: decisions.save.id, name: decisions.save.fullName } : null
        },

        pitchingChanges: detectPitchingChanges(allPlays),
        totalInnings: innings.length
      };
    }
  };
})();
