/*
 * resolution-pass.js — Phase 2 silent prediction resolution.
 *
 * On any page load where Phase 2 state exists, walk unresolved predictions,
 * fetch each pid's gamelog from MLB Stats API, apply the resolution_rule
 * against the prediction date's game, and write the result into the
 * history log via MorningLineupReaderState.
 *
 * Runs at most once per session (sessionStorage flag) and is fire-and-forget.
 */
(function () {
  const SESSION_FLAG = "ml.resolutionPassRan";

  function alreadyRanThisSession() {
    try { return sessionStorage.getItem(SESSION_FLAG) === "1"; }
    catch (e) { return false; }
  }

  function markRan() {
    try { sessionStorage.setItem(SESSION_FLAG, "1"); } catch (e) {}
  }

  function todayISO() {
    return new Date().toISOString().slice(0, 10);
  }

  // Find the gamelog split that matches a target date for a given pid+season.
  // Tries hitter group first then pitcher (single fetch per group, cached).
  const _gameLogCache = {};

  async function fetchGameLog(pid, season, group) {
    const key = pid + "-" + season + "-" + group;
    if (_gameLogCache[key]) return _gameLogCache[key];
    const url = "https://statsapi.mlb.com/api/v1/people/" + pid +
                "/stats?stats=gameLog&season=" + season + "&group=" + group;
    try {
      const res = await fetch(url);
      if (!res.ok) {
        _gameLogCache[key] = null;
        return null;
      }
      const data = await res.json();
      _gameLogCache[key] = data;
      return data;
    } catch (e) {
      _gameLogCache[key] = null;
      return null;
    }
  }

  function findGameOnDate(gamelog, dateISO) {
    if (!gamelog || !gamelog.stats) return null;
    for (const block of gamelog.stats) {
      for (const split of (block.splits || [])) {
        if (split.date === dateISO) return split;
      }
    }
    return null;
  }

  function applyRule(rule, stat) {
    if (!rule || !stat) return null;
    const statName = rule.stat;
    const op = rule.op;
    const target = rule.value;
    let actual;

    // Special: qualityStart = pitched 6+ IP, ≤3 ER
    if (statName === "qualityStart") {
      const ipStr = stat.inningsPitched || "0.0";
      const ip = parseFloat(ipStr) || 0;
      const er = parseInt(stat.earnedRuns || 0, 10) || 0;
      const isQS = ip >= 6 && er <= 3;
      return isQS === target;
    }

    // Numeric stats
    if (statName === "hits") actual = parseInt(stat.hits || 0, 10);
    else if (statName === "homeRuns") actual = parseInt(stat.homeRuns || 0, 10);
    else if (statName === "strikeOuts") actual = parseInt(stat.strikeOuts || 0, 10);
    else if (statName === "rbi") actual = parseInt(stat.rbi || 0, 10);
    else if (statName === "stolenBases") actual = parseInt(stat.stolenBases || 0, 10);
    else return null;

    if (isNaN(actual)) return null;

    if (op === ">=") return actual >= target;
    if (op === ">") return actual > target;
    if (op === "<=") return actual <= target;
    if (op === "<") return actual < target;
    if (op === "==") return actual === target;
    return null;
  }

  async function resolveOne(pid, pred) {
    const RS = window.MorningLineupReaderState;
    if (!RS) return;

    // Only resolve predictions made before today
    const today = todayISO();
    if (!pred.date || pred.date >= today) return;
    if (pred.resolvedAt) return;
    if (!pred.pick || !pred.resolution_rule) return;

    const season = pred.date.slice(0, 4);
    const group = pred.role_tag === "pitcher" ? "pitching" : "hitting";

    const gamelog = await fetchGameLog(pid, season, group);
    if (!gamelog) return; // network failure → retry next session

    const game = findGameOnDate(gamelog, pred.date);
    if (!game) {
      // DNP — push, no record change but mark resolved so we don't re-process
      const entry = {
        date: pred.date,
        question: pred.question_text,
        pick: pred.pick,
        result: "PUSH",
        resolvedAt: new Date().toISOString(),
        wasSeen: false,
      };
      RS.appendHistory(pid, entry);
      RS.updatePrediction(pid, { resolvedAt: entry.resolvedAt, result: "PUSH", wasSeen: false });
      return;
    }

    const stat = game.stat || {};
    const conditionMet = applyRule(pred.resolution_rule, stat);
    if (conditionMet === null) return;

    const userPickYes = pred.pick === "YES";
    const win = (userPickYes && conditionMet) || (!userPickYes && !conditionMet);
    const result = win ? "WIN" : "LOSS";

    const entry = {
      date: pred.date,
      question: pred.question_text,
      pick: pred.pick,
      actualMet: conditionMet,
      result: result,
      resolvedAt: new Date().toISOString(),
      wasSeen: false,
    };
    RS.appendHistory(pid, entry);
    RS.updatePrediction(pid, { resolvedAt: entry.resolvedAt, result: result, wasSeen: false });
  }

  async function runPass() {
    if (alreadyRanThisSession()) return;
    const RS = window.MorningLineupReaderState;
    if (!RS) return;
    markRan();

    const all = RS.getAllPredictions();
    const pids = Object.keys(all);
    if (pids.length === 0) return;

    // Process in parallel but bounded — modest concurrency for client fetches
    const queue = pids.slice();
    const concurrency = 4;
    const workers = Array.from({ length: concurrency }, async () => {
      while (queue.length > 0) {
        const pid = queue.shift();
        try { await resolveOne(pid, all[pid]); }
        catch (e) { /* swallow per-pid errors */ }
      }
    });
    await Promise.all(workers);

    // Notify any subscribers (the binder header listens for this)
    try {
      window.dispatchEvent(new CustomEvent("ml:predictions-resolved"));
    } catch (e) {}
  }

  // Kick off after page load — async, doesn't block rendering
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", runPass);
  } else {
    runPass();
  }

  window.MorningLineupResolutionPass = { run: runPass };
})();
