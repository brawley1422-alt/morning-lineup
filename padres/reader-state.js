/*
 * reader-state.js — Morning Lineup Phase 2 reader state.
 *
 * Owns all localStorage reads/writes for memory + prediction layers.
 * Exposes window.MorningLineupReaderState mirroring the MorningLineupPC pattern.
 *
 * Storage shape (one root key, one JSON blob — easy to back up, easy to nuke):
 *   localStorage["ml.readerState"] = {
 *     touches: { [pid]: { openCount, firstSeen, lastSeen } },
 *     predictions: { [pid]: { date, question_text, resolution_rule, role_tag,
 *                             context_tag, pick, madeAt, lockedAt, resolvedAt,
 *                             result, wasSeen, gameTime } },
 *     followedSet: [pid, pid, ...]
 *   }
 */
(function () {
  if (window.MorningLineupReaderState) return;

  const STORE_KEY = "ml.readerState";

  function _today() {
    return new Date().toISOString().slice(0, 10);
  }
  function _now() {
    return new Date().toISOString();
  }

  function _load() {
    try {
      const raw = localStorage.getItem(STORE_KEY);
      if (!raw) return _empty();
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object") return _empty();
      return {
        touches: parsed.touches || {},
        predictions: parsed.predictions || {},
        followedSet: Array.isArray(parsed.followedSet) ? parsed.followedSet : [],
      };
    } catch (e) {
      console.warn("[reader-state] corrupt store, resetting", e);
      return _empty();
    }
  }

  function _empty() {
    return { touches: {}, predictions: {}, followedSet: [] };
  }

  function _save(state) {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify(state));
    } catch (e) {
      console.warn("[reader-state] save failed", e);
    }
  }

  function touch(pid) {
    if (!pid) return;
    const key = String(pid);
    const state = _load();
    const today = _today();
    const existing = state.touches[key];
    if (!existing) {
      state.touches[key] = { openCount: 1, firstSeen: today, lastSeen: today };
    } else {
      existing.openCount = (existing.openCount || 0) + 1;
      existing.lastSeen = today;
      if (!existing.firstSeen) existing.firstSeen = today;
    }
    _save(state);
  }

  function getTouches(pid) {
    if (!pid) return null;
    return _load().touches[String(pid)] || null;
  }

  function getAllTouches() {
    return _load().touches;
  }

  function setFollowedSet(pids) {
    const state = _load();
    state.followedSet = Array.from(new Set((pids || []).map((p) => String(p))));
    _save(state);
  }

  function getFollowedSet() {
    return _load().followedSet || [];
  }

  function isFollowed(pid) {
    if (!pid) return false;
    return _load().followedSet.includes(String(pid));
  }

  function setPrediction(pid, predRecord) {
    if (!pid || !predRecord) return;
    const key = String(pid);
    const state = _load();
    state.predictions[key] = Object.assign({}, state.predictions[key] || {}, predRecord);
    _save(state);
  }

  function updatePrediction(pid, patch) {
    if (!pid || !patch) return;
    const key = String(pid);
    const state = _load();
    if (!state.predictions[key]) return;
    state.predictions[key] = Object.assign({}, state.predictions[key], patch);
    _save(state);
  }

  function getPrediction(pid) {
    if (!pid) return null;
    return _load().predictions[String(pid)] || null;
  }

  function getAllPredictions() {
    return _load().predictions;
  }

  /**
   * Make/revise a pick on today's prediction. Locks at gameTime (next_game_time).
   * If a pick already exists for today, update it (if not yet locked).
   * If today's question is different from a stored stale question, replace it.
   */
  function makePick(pid, pick, questionFromCard) {
    if (!pid || (pick !== "YES" && pick !== "NO")) return false;
    const key = String(pid);
    const state = _load();
    const today = _today();
    const existing = state.predictions[key];

    // Determine if we can revise
    const now = new Date();
    const gameTime = (questionFromCard && questionFromCard.gameTime) || (existing && existing.gameTime);
    if (gameTime) {
      const lockTime = new Date(gameTime);
      if (!isNaN(lockTime.getTime()) && now >= lockTime) {
        // Locked
        return false;
      }
    }

    // Build the prediction record from the question on the card
    const next = {
      date: today,
      pick: pick,
      madeAt: _now(),
      gameTime: gameTime || null,
      question_text: (questionFromCard && questionFromCard.question_text) || (existing && existing.question_text) || "",
      resolution_rule: (questionFromCard && questionFromCard.resolution_rule) || (existing && existing.resolution_rule) || null,
      role_tag: (questionFromCard && questionFromCard.role_tag) || (existing && existing.role_tag) || "",
      context_tag: (questionFromCard && questionFromCard.context_tag) || (existing && existing.context_tag) || "",
      resolvedAt: null,
      result: null,
      wasSeen: null,
    };
    state.predictions[key] = next;
    _save(state);
    return true;
  }

  function isPickLocked(pid) {
    const pred = getPrediction(pid);
    if (!pred || !pred.gameTime) return false;
    const lockTime = new Date(pred.gameTime);
    if (isNaN(lockTime.getTime())) return false;
    return new Date() >= lockTime;
  }

  /**
   * Compute scoreboard for one player from stored predictions.
   * NOTE: stored predictions are keyed by pid and only hold the most recent
   * pick per player. For a true season scoreboard we'd need a per-player
   * history list. For v1, we layer history into a separate predictions log.
   */
  function getScoreboardForPlayer(pid) {
    if (!pid) return { wins: 0, losses: 0, pushes: 0, total: 0, recent: [], record: "0-0" };
    const log = _loadHistory()[String(pid)] || [];
    let wins = 0, losses = 0, pushes = 0;
    for (const entry of log) {
      if (entry.result === "WIN") wins++;
      else if (entry.result === "LOSS") losses++;
      else if (entry.result === "PUSH") pushes++;
    }
    return {
      wins, losses, pushes,
      total: wins + losses + pushes,
      recent: log.slice(-5),
      record: wins + "-" + losses + (pushes > 0 ? " (" + pushes + " push)" : ""),
    };
  }

  function getAggregateScoreboard() {
    const history = _loadHistory();
    let wins = 0, losses = 0, pushes = 0;
    let lastDate = null;
    let currentStreak = 0;
    let streakKind = null; // "W" or "L"
    // Flatten + sort all entries
    const all = [];
    for (const pid in history) {
      for (const entry of history[pid]) {
        all.push(entry);
      }
    }
    all.sort((a, b) => (a.resolvedAt || "").localeCompare(b.resolvedAt || ""));
    for (const entry of all) {
      if (entry.result === "WIN") wins++;
      else if (entry.result === "LOSS") losses++;
      else if (entry.result === "PUSH") pushes++;
      if (entry.result === "WIN" || entry.result === "LOSS") {
        const kind = entry.result === "WIN" ? "W" : "L";
        if (streakKind === kind) currentStreak++;
        else { streakKind = kind; currentStreak = 1; }
      }
    }
    return {
      wins, losses, pushes,
      total: wins + losses + pushes,
      record: wins + "-" + losses,
      streak: streakKind ? streakKind + currentStreak : null,
    };
  }

  // ── Resolution history log ─────────────────────────────────────
  // The current prediction in `predictions[pid]` is just the latest pick.
  // When a prediction resolves, we append a record to the history log so
  // the scoreboard can accumulate a real season record.
  const HISTORY_KEY = "ml.predictionHistory";

  function _loadHistory() {
    try {
      const raw = localStorage.getItem(HISTORY_KEY);
      if (!raw) return {};
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object") return {};
      return parsed;
    } catch (e) {
      return {};
    }
  }

  function _saveHistory(history) {
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    } catch (e) {
      console.warn("[reader-state] history save failed", e);
    }
  }

  function appendHistory(pid, entry) {
    if (!pid || !entry) return;
    const key = String(pid);
    const history = _loadHistory();
    if (!history[key]) history[key] = [];
    // Dedupe by date — one resolution per pid per day
    history[key] = history[key].filter((e) => e.date !== entry.date);
    history[key].push(entry);
    _saveHistory(history);
  }

  function getHistoryForPlayer(pid) {
    if (!pid) return [];
    return _loadHistory()[String(pid)] || [];
  }

  function getAllHistory() {
    return _loadHistory();
  }

  window.MorningLineupReaderState = {
    touch,
    getTouches,
    getAllTouches,
    setFollowedSet,
    getFollowedSet,
    isFollowed,
    setPrediction,
    updatePrediction,
    getPrediction,
    getAllPredictions,
    makePick,
    isPickLocked,
    appendHistory,
    getHistoryForPlayer,
    getAllHistory,
    getScoreboardForPlayer,
    getAggregateScoreboard,
  };
})();
