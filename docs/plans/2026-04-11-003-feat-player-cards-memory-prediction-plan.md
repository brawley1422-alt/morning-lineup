---
title: "feat: Player Cards Phase 2 — Memory + Prediction Loop"
type: feat
status: active
date: 2026-04-11
origin: docs/brainstorms/2026-04-11-player-cards-memory-prediction-requirements.md
---

# feat: Player Cards Phase 2 — Memory + Prediction Loop

## Overview

Turn the player card from a one-shot lookup into a relationship. Based on findings in `docs/brainstorms/2026-04-11-player-cards-memory-prediction-requirements.md`, Phase 2 ships three tightly interlocked pieces as one v1:

1. **Last-10-games sparkline** as the card's universal memory anchor (visible to any reader, no account required)
2. **Daily contextual prediction tile** on followed-player cards, question selected by build-side stat-trigger rules, locked at first pitch, silently resolved next morning
3. **Personal scoreboard** — per-player on card back + aggregate in My Players binder header — backed entirely by localStorage reader state

No backend, no auth, no snapshot tape. Every new state lives in localStorage; every new data point piggybacks on build-time player record hydration that already runs.

## Problem Frame

Phase 1 shipped today: deeplinks, 30-team active-roster cards, Tier 1 click affordance, dark binder My Players. The analyst found (in the brainstorm's Problem Frame) that what's missing is "a reason to come back tomorrow and a reason to care about a specific player over time." Right now every card is a cold read with no acknowledgement that you've been here before.

Phase 2's loop: **open card → see last-10 sparkline → make prediction (if followed) → return tomorrow → see result in pre-resolved scoreboard**. Based on the brainstorm decision R6, v1 is not a v1 win unless the full loop lands as one unit — memory without the prediction loop is just a visual polish; prediction without memory has nothing to anchor.

## Requirements Trace

This plan satisfies the following requirements from the origin document (see origin: `docs/brainstorms/2026-04-11-player-cards-memory-prediction-requirements.md`):

- **R1** Reader state in localStorage (openCount, firstSeen, lastSeen) → Unit 3
- **R2** Last-10-games sparkline anchor → Units 1 + 2
- **R3** Daily micro-prediction on followed-player cards → Units 1 + 4
- **R4** Personal scoreboard accumulation → Units 3 + 6
- **R5** End-of-season recap *(stretch, acknowledged in plan but not shipped in v1)* → noted in Open Questions
- **R6** Ship full loop as one unit → shipping discipline; no partial unit checkpoint
- **R7** Memory accumulates on every card opened → Unit 3 (ReaderState.touch called unconditionally by card mount)
- **R8** Prediction prompts only on followed-player cards → Unit 4 (followed-set gate)
- **R9** Daily build selects contextual question via stat-trigger rules → Unit 1
- **R10** Each prediction carries question text, resolution rule, context tag → Unit 1 (data shape)
- **R11** Per-player scoreboard on card back → Unit 6
- **R12** Aggregate scoreboard in binder header → Unit 6
- **R13** DNP = push → Unit 5 (resolution logic)
- **R14** Card back surfaces reader touches → Unit 6
- **R15** Silent resolution pass → Unit 5
- **R16** "You missed this one" marker → Unit 5 (resolution record tracks `wasSeen`)
- **R17** Picks lock at first pitch of next game → Unit 1 (next_game_time emitted) + Unit 4 (lock enforcement)

Success criteria SC1, SC2, SC3, SC5, SC6, SC8, SC10 are covered end-to-end by Units 2–6 working together. SC4 (season recap is shareable) and SC7 (questions feel written not templated) are MEDIUM and depend on the starter rule set quality — tracked in Open Questions.

## Scope Boundaries

Explicit non-goals from the origin document, carried forward unchanged:

- **[HIGH]** No cross-device sync via auth — localStorage-only
- **[HIGH]** No server-side prediction storage
- **[HIGH]** No prediction prompts on non-followed-player cards
- **[HIGH]** No per-day snapshot tape — last-10 sparkline is computed from live gamelog
- **[MEDIUM]** No memory/prediction for non-active-roster players (IL, 40-man non-active, prospects)
- **[MEDIUM]** No reader-authored custom predictions
- **[MEDIUM]** No end-of-season recap UX surface in v1 (localStorage schema is recap-compatible so it ships later without data migration)

## Context & Research

### Relevant Code and Patterns

- **`build.py:_fetch_player_record`** (around `build.py:890`) — the per-player hydrator already fetches season stats, yearByYear career, and gameLog. Unit 1 extends this with a per-game extraction pass (OPS for hitters, GameScore for pitchers) from the gameLog the function already pulls. No new HTTP requests required for the sparkline data.
- **`build.py:compute_temp_strip`** (around `build.py:840`) — the existing hot/cold strip computation is the load-bearing precedent for per-game metric extraction. It already walks the first 15 gamelog splits and computes a normalized [0,1] score. Unit 1 mirrors this idiom but returns last-10 raw values (not normalized) for the sparkline's shape.
- **`build.py:save_players`** (around `build.py:1005` — the helper added during Phase 1) — Unit 1's stat-trigger question selection runs inside this path, appended to each `rec` before it hits the JSON wrapper. No new write step; extends the record.
- **`build.py:save_player_index`** (from Phase 1's `02` plan) — precedent for post-build aggregate artifact emission. Unit 1 does not add a new aggregate file; the prediction + last-10 data rides inside existing `data/players-<slug>.json`.
- **`cubs/player-card.js` `renderFront`/`renderBack`/`mountInline`** — the component already exposes a render API via `window.MorningLineupPC`. Units 2, 4, 6 extend these render functions without adding a new component. The existing temp strip lives on the front (around the slash line area); the sparkline extends this placement precedent in Unit 2.
- **`cubs/player-card.js` `window.MorningLineupPC.mountInline`** (Phase 1 addition) — the inline mount path is how the My Players binder renders cards. Unit 6's aggregate scoreboard reads from the same ReaderState module these inline cards write to, so the binder header stays in sync without a pub/sub layer.
- **`home/home.js` `renderMyPlayersSection`** (around the binder rewrite from Phase 1) — the binder already iterates over followed players, mounts a card per pocket, and has a header area with the "Approved" stamp. Unit 6 adds the aggregate W-L strip into the existing `.binder-head` / `.bh-meta` structure.
- **`home/home.js` `loadFollowedPlayers`** — existing Supabase query that returns the user's followed roster. Unit 4 uses this to write the followed-pid set into localStorage on home page load so non-home pages (team pages, deeplinks) can tell "is this player followed" without hitting Supabase.
- **`data/player-index.json`** (Phase 1 artifact) — already loaded by `home.js`'s `loadPlayerIndex()`. Unit 5's silent resolution pass uses this to route "which team's gamelog endpoint resolves this pid's prediction."
- **`sections/headline.py`** — precedent for the Cubs-only `team_id == 112` gate pattern that was dropped in Phase 1 Tier 1. No new gating; prediction tile's gate is client-side (followed-set), not server-side.
- **`tests/snapshot_test.py`** — golden Cubs + Yankees byte-identical snapshot test. New data emitted in `data/players-<slug>.json` does not affect snapshot HTML because card content is rendered client-side from JSON — the fixture `.html` files are unchanged by Unit 1's data additions. Verified by Phase 1's experience: the Phase 1 plan also added fields to the JSON wrapper (team_full_name, team_abbreviation) without snapshot regression.

### Institutional Learnings

- From `docs/solutions/` and recent session memory: when changing shared assets (player-card.js, sw.js), rebuild all 30 teams and re-distribute the component to every team directory (the precedent established in Phase 1 via `cp player-card.js <slug>/player-card.js`). Unit 2's sparkline change and Unit 4's prediction tile change both require this full re-distribution.
- Phase 1's cache versioning learning: bumping `sw.js` and `cubs/sw.js` `CACHE = "lineup-vN"` is how clients pick up new component versions. Unit 2 or Unit 4 (whichever lands last) must bump the cache version.
- Phase 1's snapshot-scope-leak learning: Yankees snapshot caught an accidental `<player-card>` wrap leaking across teams. No equivalent risk in Phase 2 because all new behavior is client-side and data-driven rather than HTML-template-driven, but Unit 2's sparkline changes the rendered card DOM — that's client-side so snapshots stay clean.

### External References

- MLB Stats API `/people/{pid}/stats?stats=gameLog&season=X` — already used by `_fetch_player_record` for the temp strip. Unit 1 reuses the same response, just extracts more fields. Unit 5 (client-side resolution) fetches this endpoint on demand for prediction resolution — no auth, public, CORS-friendly.
- MLB Stats API `/schedule?teamId=X&date=Y` — for Unit 1's `next_game_time` lookup. Already referenced implicitly by the existing build's "next games" section in `sections/headline.py`.

## Key Technical Decisions

- **All prediction state lives in localStorage, never on the server.** Rationale: Brainstorm R1/SC scope boundary. Zero backend investment, ships faster, and aligns with the existing home page pattern (followed_teams and followed_players are Supabase-backed but *preferences* and *session state* are localStorage in home.js). Acceptable tradeoff: no cross-device sync in v1.

- **Silent resolution runs client-side on page load, not in the build.** Rationale: Because predictions live in localStorage, the build has no per-user state to resolve against. On home/team-page load, JS scans localStorage for unresolved predictions, fetches the relevant gamelog endpoints, applies the resolution rule, and writes results. The loop still appears silent to the reader — they don't click to resolve; resolution happens on any page visit, not per-card. Matches R15's intent while respecting the no-backend constraint.

- **The last-10-games data rides inside `data/players-<slug>.json`, not a separate artifact.** Rationale: The data is already in the gamelog response `_fetch_player_record` fetches. Emitting a new `data/last-10-<slug>.json` file would duplicate write cost and cache-invalidation surface for no gain. Extending the existing record shape is the Phase 1 precedent (see `team_full_name`/`team_abbreviation` addition).

- **Prediction tile's "is this player followed?" gate reads from localStorage, not Supabase.** Rationale: Non-home pages (team pages, `#p/<pid>` deeplinks) don't have Supabase loaded. The home page writes the followed-pid set to localStorage on its mount; the card component reads it. Stale state is possible if the user follows from one tab and views a card in another, but the next home page visit refreshes it — acceptable for v1.

- **Stat-trigger rule library is a Python module called from `save_players`, not a separate artifact.** Rationale: The rules need the full `rec` dict (season stats, gameLog, career) which is only assembled inside the build pipeline. Emitting a separate `data/questions.json` would force re-joining data the build already has. Keep it inline in `build.py` or a new `sections/predictions.py` helper module (final location decided during execution — file path doesn't affect the plan).

- **Sparkline renders on the card front, not the back.** Rationale: SC1 says "any card immediately shows the last-10 trend." If the sparkline were on the back, the reader has to flip to see it — defeats "immediately." The front already has the temp strip at the bottom; the sparkline replaces or augments that area. Final visual placement (replace vs. stack) is deferred to implementation (see Open Questions).

- **Cache version bump is one cache-version increment (`lineup-v9`), not one per unit.** Rationale: All four client-visible changes (sparkline, prediction tile, scoreboard, binder header) land together per R6. One cache-bump per shipping unit is sufficient.

## Open Questions

### Resolved During Planning

- **Where is the stat-trigger rule library located?** Inline Python in `build.py` or a helper module (e.g. `sections/predictions.py`). Resolution: final path is an execution-time decision; the plan commits to "build-side Python module called from inside `save_players`." Both options satisfy the plan.
- **What does the sparkline viz actually look like?** SVG line, single metric (OPS for hitters, GameScore for pitchers), cream-on-ink palette matching the card. Starter dimensions: ~120×28px on the card front. Responsive scaling deferred (see below).
- **How is "is this player followed" known on non-home pages?** Home page writes the followed-pid set to localStorage on mount; the card component reads it. No Supabase load outside the home page.
- **What's the starter stat-trigger rule set?** Resolved during planning per the brainstorm's deferred question: slump-snap (BA < .200 over last 10 for hitters / ERA > 5 over last 3 starts for pitchers), hot-streak-continuation (OPS > 1.000 over last 10 / 10+ K in last start), milestone-watch (within 2 of a round HR/K total), pitcher-day-matchup (SP starts today), generic-role-fallback (hit? / 5+ K?). Rule priority order: milestone > pitcher-day > slump-snap > hot-streak > generic. Priority is a tuning knob for future iterations.

### Deferred to Implementation

- **Exact localStorage key namespace** (`morning-lineup.*` flat keys vs. one JSON blob under `morning-lineup.readerState`). Resolution shape depends on collision checks against existing home.js localStorage usage.
- **Sparkline visual polish** — exact dimensions, color stops, mobile scaling. Implementation discovers the right balance after seeing it rendered against a few real player records.
- **Per-card scoreboard copy format** — "7-for-12 on Happ" vs. "W-L: 7-5 on Happ" vs. a badge icon. Implementation picks the variant that reads best after assembling the actual DOM.
- **Binder header scoreboard layout** — inline next to the "Approved" stamp vs. below the rule. Implementation picks after seeing the rendered width.
- **Resolution pass trigger frequency** — does it run on every page load or only once per calendar day per device? Implementation decides based on gamelog fetch cost.
- **Whether the client-side gamelog fetch in Unit 5 goes through the component's cache layer or direct fetch**. Decide when wiring it.

## Implementation Units

- [ ] **Unit 1: Build-side data additions — last-10 trend, next game time, contextual prediction**

**Goal:** Extend every player record written to `data/players-<slug>.json` with three new fields: `last_10_games` (per-game metric sequence for the sparkline), `next_game_time` (ISO string of the next scheduled first pitch, for prediction lock), and `prediction` (the selected contextual question + resolution rule + context tag).

**Requirements:** R2, R9, R10, R17

**Dependencies:** None — foundation unit.

**Files:**
- Modify: `build.py` (extend `_fetch_player_record` to emit `last_10_games`; add a stat-trigger rule library either inline or under a new helper; call rule selection from inside `save_players` or `load_team_players`)
- Possibly create: `sections/predictions.py` or a build-side helper module for the stat-trigger rule library (final location is an execution-time decision)
- Test: `tests/test_player_record_phase2.py` (new)

**Approach:**
- Reuse the existing `/people/{pid}/stats?stats=gameLog` fetch in `_fetch_player_record` around `build.py:890` — extract OPS per game for hitters, GameScore per game for pitchers, keep the last 10 in chronological order with date + opponent abbreviation attached to each entry.
- `next_game_time` comes from `/schedule?teamId=X` filtered to the player's team — the builder already hits this endpoint in the "next games" section, so the URL pattern is a proven path.
- Stat-trigger rule selection runs after the record is otherwise assembled: takes the full `rec` dict, walks the rule set in priority order (milestone → pitcher-day → slump-snap → hot-streak → generic fallback), returns `{question_text, resolution_rule, role_tag, context_tag}` for the first rule that fires.
- `resolution_rule` is a machine-readable descriptor (`{stat: "hits", op: ">=", value: 1}` or similar) so Unit 5's client-side resolver can apply it without re-parsing text.

**Execution note:** Starter rule set is enumerated in the brainstorm and plan; implementation writes them as pure Python functions keyed by priority order.

**Patterns to follow:**
- `build.py:compute_temp_strip` for per-game metric extraction idiom
- `build.py:save_players` for the save-time augmentation hook
- `build.py:_fetch_player_record` return shape — extend, don't replace

**Test scenarios:**
- Happy path: a player with 10+ games played has `last_10_games` with exactly 10 entries, ordered oldest-to-newest, each carrying {date, opponent, metric_value}
- Happy path: a hitter with a .150 BA over his last 10 gets the slump-snap question
- Happy path: a pitcher starting today gets the pitcher-day question regardless of other triggers (priority)
- Edge case: a player with fewer than 10 career games has `last_10_games` padded with nulls or returns the shorter list (implementer decides; document the choice)
- Edge case: a player with no upcoming scheduled game (end-of-season, released mid-day) has `next_game_time` as null and the fallback generic question
- Edge case: a player triggering multiple rules gets the highest-priority rule's question (unit test each priority boundary)
- Integration: running `python3 build.py --team cubs` produces `data/players-cubs.json` where every record has all three new fields populated

**Verification:**
- `data/players-cubs.json` contains, for every active Cub, `last_10_games` (array), `next_game_time` (string or null), and `prediction` (object with question_text, resolution_rule, role_tag, context_tag)
- Snapshot tests (`tests/snapshot_test.py`) stay green — added JSON data doesn't affect the rendered HTML fixture
- Cold full 30-team build stays under 10 minutes; warm runs under 3 minutes (cache hits)

---

- [ ] **Unit 2: Last-10-games sparkline render on card front**

**Goal:** Render an SVG sparkline on the card front using `last_10_games` data. Visible on every card regardless of follow or deeplink context.

**Requirements:** R2, SC1

**Dependencies:** Unit 1 (needs `last_10_games` in the JSON)

**Files:**
- Modify: `cubs/player-card.js` (`renderFront`)
- Sync: `player-card.js` (repo root), `home/player-card.js`, and the 30 `<slug>/player-card.js` copies (Phase 1 established this distribution pattern)
- Test: `tests/test_player_card_sparkline.html` (new manual test harness — matches the existing `tests/test_player_card_live.html` pattern)

**Approach:**
- Replace or augment the existing temp strip area on the card front with an SVG `<polyline>` or `<path>` rendered from `last_10_games`
- Min/max scaling computed per-player; single stroke color from the existing card palette (gold or red accent)
- Null entries in `last_10_games` break the line into segments
- Keep the existing hot/cold temp bar too, or replace it — decision deferred to implementation after visual inspection (see Open Questions)

**Patterns to follow:**
- Existing `renderFront` SVG/HTML composition in `cubs/player-card.js`
- Existing CSS variable palette in the inlined component styles

**Test scenarios:**
- Happy path: a card with 10 game entries renders a continuous sparkline; verify the SVG path's point count matches entry count
- Happy path: the sparkline's min/max aligns with the highest/lowest game value in `last_10_games`
- Edge case: a player with 3 game entries and 7 nulls renders a truncated sparkline without crashing
- Edge case: a player with all-null entries renders a placeholder (flat dashed line or "no recent games" label — implementer picks)
- Edge case: sparkline remains readable at the binder's reduced card size (~220px wide in `home/home.css .binder-grid .pocket`)
- Integration: opening a card via `/yankees/#p/592450` shows Aaron Judge's sparkline on the front, not just the temp strip

**Verification:**
- Every card opened via modal, inline binder, or deeplink shows a sparkline on the front
- Manual harness page renders 6 sample cards with visually distinct sparklines (hot player, cold player, pitcher, partial data, etc.)

---

- [ ] **Unit 3: ReaderState JS module — localStorage interface**

**Goal:** A single module that owns all localStorage reads/writes for Phase 2 state. Exposes: `touch(pid)`, `getTouches(pid)`, `getAllTouches()`, `setPrediction(pid, predRecord)`, `getPrediction(pid)`, `getAllPredictions()`, `updatePrediction(pid, patch)`, `setFollowedSet(pids)`, `getFollowedSet()`, `getScoreboardForPlayer(pid)`, `getAggregateScoreboard()`.

**Requirements:** R1, R4, R7, R11, R12, R14

**Dependencies:** None — pure client-side, no build dependency.

**Files:**
- Create: `reader-state.js` (repo root), sync to every team directory, `home/`, and `cubs/` following the Phase 1 player-card.js distribution pattern
- Modify: `cubs/player-card.js` (import or inline-call ReaderState on mount — needs to be decided; probably inline-call via `window.MorningLineupReaderState` to match the MorningLineupPC pattern)
- Modify: `home/home.js` (use ReaderState for the followed-set write on page load)
- Modify: `home/index.html`, every team's `index.html` via `build.py:818` script tag emission
- Test: `tests/test_reader_state.html` (new manual harness)

**Approach:**
- Single global `window.MorningLineupReaderState` mirroring the `MorningLineupPC` shape from Phase 1
- Storage schema (initial proposal; implementation may collapse into one root key):
  ```
  localStorage["ml.touches"] = { [pid]: { openCount, firstSeen, lastSeen } }
  localStorage["ml.predictions"] = { [pid]: { question, pick, madeAt, lockedAt, resolvedAt, result, wasSeen } }
  localStorage["ml.followedSet"] = [pid, pid, ...]
  ```
- All writes are synchronous + idempotent. `touch()` bumps openCount and updates lastSeen.
- Scoreboard computation (`getScoreboardForPlayer`, `getAggregateScoreboard`) is pure over the stored prediction records — no derived persistence.

**Patterns to follow:**
- `window.MorningLineupPC` IIFE shape in `cubs/player-card.js` for namespacing
- Phase 1's component distribution pattern (`cp` to every team dir) for script delivery
- `build.py:818` script tag emission pattern for including `reader-state.js` in every team page

**Test scenarios:**
- Happy path: `touch(691718)` on a fresh localStorage creates `{openCount: 1, firstSeen: today, lastSeen: today}`
- Happy path: calling `touch(pid)` five times over multiple days leaves `openCount: 5`, `firstSeen: day1`, `lastSeen: day5`
- Happy path: `setPrediction()` then `getPrediction()` round-trips the exact record
- Happy path: `getScoreboardForPlayer(pid)` with 7 wins and 5 losses returns `{wins: 7, losses: 5, record: "7-5", streak: ..., recentPicks: [...]}`
- Edge case: `getScoreboardForPlayer(pid)` on a player with no predictions returns a zero/empty state without throwing
- Edge case: localStorage quota exceeded (extremely unlikely at this scale, but surface a console warning rather than crashing)
- Edge case: corrupt/malformed localStorage JSON is caught, reset to defaults, logged
- Integration: a card mount triggers `touch()` before rendering; the next mount shows `openCount: 2`
- Integration: `setFollowedSet([pid1, pid2])` from home.js makes the prediction tile render on those pids' cards when opened elsewhere

**Verification:**
- Manual harness shows touches and predictions accumulating correctly across page reloads
- Opening a card twice shows `openCount: 2` in the card's reader-touches line
- Corrupt-localStorage recovery path leaves the state clean and the page functional

---

- [ ] **Unit 4: Prediction tile on card back + pick lock logic**

**Goal:** Render the daily prediction tile on the back of followed-player cards. YES/NO tap writes through ReaderState. Tile disables after first pitch (`next_game_time` from Unit 1).

**Requirements:** R3, R8, R17

**Dependencies:** Unit 1 (prediction data in JSON), Unit 3 (ReaderState module)

**Files:**
- Modify: `cubs/player-card.js` (`renderBack`)
- Sync: all distributed copies of `player-card.js`

**Approach:**
- `renderBack` reads `data.players[pid].prediction.question_text` and renders a tile with two tap targets (YES/NO) above the existing advanced stats grid
- Before rendering, check `ReaderState.getFollowedSet().includes(pid)` — if not followed, render the back without the tile (no wasted DOM)
- Tile reads current prediction state from ReaderState — if resolved, show the result inline ("You picked YES. He went 2-for-4. ✓"). If unresolved and unlocked, show YES/NO tappable. If locked (`now >= next_game_time`), show the pick locked with a "lock" marker.
- Tap handler writes via `ReaderState.setPrediction()` and re-renders the tile in place

**Patterns to follow:**
- Existing `renderBack` composition in `cubs/player-card.js`
- The MorningLineupPC IIFE pattern for accessing the ReaderState global

**Test scenarios:**
- Happy path: open a followed-player card → flip → see YES/NO prediction tile with today's question
- Happy path: tap YES → tile re-renders showing "You picked YES · locks at 7:10 PM" and ReaderState has the record
- Happy path: re-open the same card later in the day → tile shows the saved pick
- Happy path: next morning, re-open the card → tile shows the resolved result
- Edge case: non-followed player's card back shows no prediction tile
- Edge case: `next_game_time` has already passed when the card is opened → tile shows "locked" and no taps work
- Edge case: a player with no valid prediction (all rules failed to match) → falls back to generic question; test that the generic still renders
- Edge case: tapping YES then tapping NO before the lock updates the stored pick (revisable until first pitch per R17)
- Integration: the tile is absent from the non-followed rendering path even on the same page where other followed cards show it

**Verification:**
- Followed cards show the tile; non-followed cards don't
- Taps persist across page reloads via ReaderState
- Post-lock cards render in a visually distinct locked state

---

- [ ] **Unit 5: Silent resolution pass — client-side**

**Goal:** On any page load where Phase 2 state exists, walk unresolved predictions in localStorage, fetch the relevant gamelog entries, apply each prediction's `resolution_rule`, write the result back to localStorage. Mark predictions that resolved during the user's absence with `wasSeen: false` for the missed-marker UI.

**Requirements:** R13, R15, R16, SC2, SC10

**Dependencies:** Unit 3 (ReaderState), Unit 1 (predictions in JSON carry the `resolution_rule`)

**Files:**
- Create: `resolution-pass.js` (repo root, distributed like player-card.js) OR fold into `reader-state.js` — implementer picks
- Modify: `cubs/player-card.js` and/or `home/home.js` to trigger the pass on mount
- Test: `tests/test_resolution_pass.html` (new manual harness)

**Approach:**
- On first page load per session (or first per calendar day — see Open Questions), walk `ReaderState.getAllPredictions()` filtered to `resolvedAt === null`
- For each unresolved prediction, if `prediction.madeAt < today`, fetch `/people/{pid}/stats?stats=gameLog&season=X` from MLB Stats API (same endpoint `build.py` uses — public, CORS-friendly)
- Find the game matching the prediction's target date
- DNP = push → update prediction with `{result: "push", resolvedAt: now, wasSeen: currentDate == predictionDate + 1}`
- Apply the prediction's `resolution_rule` (e.g. `{stat: "hits", op: ">=", value: 1}`) against the found game's stats
- Write result back via `ReaderState.updatePrediction(pid, {result, resolvedAt, wasSeen})`
- Run asynchronously — don't block card rendering. Fire-and-forget, update UI when each resolves.

**Patterns to follow:**
- Phase 1's client-side gamelog fetch from `cubs/player-card.js` `loadData` pattern for fetch + error handling
- No new caching layer — resolution only fetches unresolved predictions, and each pid is fetched at most once per session

**Test scenarios:**
- Happy path: yesterday's prediction (YES on "will Happ get a hit") resolves to WIN when yesterday's game shows Happ 2-for-4
- Happy path: yesterday's prediction resolves to LOSS when the game shows 0-for-4
- Happy path: yesterday's prediction resolves to PUSH when Happ didn't play (DNP)
- Happy path: user returns after 3 days → all 3 days of predictions resolve in one pass with `wasSeen: false` on days 1 and 2
- Edge case: MLB API returns 500 for a pid's gamelog → that prediction stays unresolved, pass retries next session, no crash
- Edge case: a prediction from today (not yet played) is skipped (not resolvable yet)
- Edge case: a prediction whose target game was postponed/rescheduled finds no matching game → stays unresolved
- Edge case: resolution_rule references a stat not in the returned boxscore → log warning, leave unresolved
- Integration: after a multi-day absence, opening the home page shows an aggregate scoreboard that includes the auto-resolved picks

**Verification:**
- Yesterday's prediction resolves on any page visit the next day without manual action
- Missed-day predictions show the "you missed this one" marker on the scoreboard
- Network failures degrade gracefully (retry next session)

---

- [ ] **Unit 6: Scoreboard rendering — per-player on card back + aggregate in binder header**

**Goal:** Render the scoreboard UI in both locations using ReaderState as the data source. Per-player version lives on the card back alongside the prediction tile; aggregate version lives in `home/home.js`'s binder header.

**Requirements:** R4, R11, R12, R14, SC3, SC8, SC9

**Dependencies:** Unit 3 (ReaderState), Unit 5 (so the scoreboard reflects resolved state)

**Files:**
- Modify: `cubs/player-card.js` (`renderBack` — add scoreboard block + reader-touches line)
- Sync: all distributed `player-card.js` copies
- Modify: `home/home.js` (`renderMyPlayersSection` — add aggregate block into `.binder-head`)
- Modify: `home/home.css` (styles for new `.binder-scoreboard` elements inside `.binder-head`)

**Approach:**
- Per-player scoreboard: a small block on the card back showing `ReaderState.getScoreboardForPlayer(pid).record` plus current streak. Placement: below the prediction tile, above advanced stats. Renders even if there are zero predictions ("No picks yet — be the first to call it")
- Reader touches: a one-liner ("You've opened this 14 times · first seen Apr 4") rendered from `getTouches(pid)`, placed at the bottom of the back inside the `.pc-back-foot` area
- Aggregate binder scoreboard: lives in `.binder-head` beside the "Approved" stamp (inline if width allows, stacked if not — decision deferred to implementation after seeing rendered width). Shows season record + current streak from `ReaderState.getAggregateScoreboard()`
- Aggregate strip updates reactively: after a silent resolution (Unit 5) writes new state, the binder header re-reads ReaderState and updates. Simplest mechanism: home.js re-renders the binder head after the resolution pass completes (already an async callback from Unit 5)
- The "you missed this one" marker from R16 renders inline on the per-player scoreboard (small icon or dot on any resolved pick where `wasSeen === false`)

**Patterns to follow:**
- `cubs/player-card.js` `renderBack` existing DOM structure
- `home/home.js` `renderMyPlayersSection` binder head composition
- `home/home.css` `.binder-head` / `.bh-meta` class conventions

**Test scenarios:**
- Happy path: a followed player with 7 wins, 5 losses shows "7-5 · won last 3" on the back
- Happy path: a followed player with 14 opens shows "You've opened this 14 times · first seen Apr 4"
- Happy path: the binder header shows an aggregate record computed across all followed players
- Happy path: after a resolution pass fires asynchronously, the binder header updates without a manual page refresh
- Edge case: a newly followed player with 0 picks shows "No picks yet" on the back
- Edge case: a player opened for the first time shows "First visit" or open count 1 correctly
- Edge case: the aggregate scoreboard on a binder with zero followed players renders a neutral "Start predicting to build your record"
- Edge case: missed-while-away picks show with the "you missed this one" marker inline
- Integration: making a prediction in Unit 4, triggering resolution in Unit 5, and seeing the scoreboard update in Unit 6 is the end-to-end loop

**Verification:**
- Open any followed-player card → see scoreboard block on back
- Open the home page → see aggregate record + streak in the binder header before clicking any card
- Make a prediction → next day, open any page → scoreboard has incremented

## System-Wide Impact

- **Interaction graph:** `build.py` → `data/players-<slug>.json` (new fields) → `cubs/player-card.js` `renderFront`/`renderBack` → `window.MorningLineupReaderState` → localStorage. `home/home.js` reads followed set from Supabase → writes to ReaderState → card components on all pages read followed set from ReaderState. Silent resolution pass reads MLB Stats API directly from client, writes back to ReaderState.
- **Error propagation:** MLB API failures during resolution degrade silently (retry next session). Corrupt localStorage resets to defaults on next touch. Missing `last_10_games` or `prediction` fields on a player record render a fallback (empty sparkline, no tile) rather than crash the card.
- **State lifecycle risks:** localStorage is the single source of truth for Phase 2 state. A user clearing browser data loses all touches, predictions, and scoreboard history — acceptable for v1 per the brainstorm's no-auth decision. Documented in the season-recap stretch goal (R5) as a known limitation.
- **API surface parity:** The card component's modal path (`openOverlay`) and inline path (`mountInline`) must both call `ReaderState.touch()` on mount. Missing the touch call on one path would create phantom "never opened" states for cards opened through that path. Unit 3 test scenarios explicitly cover both mount paths.
- **Integration coverage:** The full loop (predict → lock → resolve → scoreboard update) requires Units 1+3+4+5+6 working together. No unit's tests alone prove the loop is functional. Unit 6's integration scenario ("make prediction → run resolution → see scoreboard update") is the load-bearing end-to-end check.
- **Unchanged invariants:** Phase 1's deeplink URL pattern `/<slug>/#p/<pid>` is unchanged. Tier 1 click affordance (lineup, SP, Three Stars, Leaders, Form Guide, Scouting SP) is unchanged. The `data/player-index.json` artifact shape is unchanged. The 30-team daily build cron is unchanged. The `sections/headline.py` and `sections/scouting.py` wrapping logic is unchanged — all Phase 2 behavior is client-side over new data fields.

## Risks & Dependencies

| Risk | Mitigation |
|---|---|
| Silent resolution fetches MLB API for every unresolved prediction on every page load → O(followed × missed days) requests on a cold return visit. | Rate-limit: bound the pass to one fetch per pid per session. Long absences still resolve eventually over multiple sessions. Acceptable degradation. |
| localStorage state becomes inconsistent across tabs (user follows in tab A while tab B has a stale followed set). | Accept staleness for v1. Next tab refresh reloads the set. Document as known limitation. A `storage` event listener is a trivial post-v1 enhancement. |
| Stat-trigger rules produce a wooden or awkward question under an edge case stat pattern. | Start with 5 rules + generic fallback. Log the selected rule in dev console during build so implementer can eyeball the starter output across all 779 players. Iterate rule text after shipping. |
| The sparkline on very-small mobile viewports (binder pockets shrink to ~150px) becomes unreadable. | Sparkline is decorative-first; readability at tiny sizes is nice-to-have. Responsive scaling is deferred to implementation polish (see Open Questions). |
| `next_game_time` is null for off-day players and the lock logic has to handle "no upcoming game." | Treat null `next_game_time` as "pick stays revisable until tomorrow's build." Unit 4 test scenarios explicitly cover this edge. |
| Resolution pass tries to resolve a prediction whose target date is today (game in progress or later). | Explicit check: only resolve predictions where `prediction.madeAt < today`. Unit 5 test scenarios cover. |
| Rules library bitrots as the season progresses and player stat distributions shift. | Rule thresholds are constants in the Python module; adjusting them is a one-file edit. Accept as normal seasonal tuning. |
| The daily build gains a new step (stat-trigger rule evaluation per player) and goes over budget. | Rule evaluation is pure Python over data already in-memory. Cost is negligible compared to the HTTP fan-out. No new risk to the build budget. |
| Snapshot tests fail because Unit 2 or Unit 4 accidentally changes rendered HTML. | Cards are rendered client-side from JSON; `tests/fixtures/*_expected.html` is static and unaffected by data changes. Only the one-line script/tag additions from the cache-bump or new JS includes would affect HTML — call out in the implementing unit to re-bless if needed. |
| Cache-bump doesn't propagate; users see stale component. | Standard `sw.js` + `cubs/sw.js` version bump (Phase 1 precedent `lineup-v7` → `lineup-v8`). Unit 6 or whichever unit lands last bumps the cache version. |

## Documentation / Operational Notes

- No user-facing docs for v1. Post-ship, consider a short README entry explaining the prediction loop mechanic for new readers.
- No new cron step — existing 08:00 UTC daily build handles Unit 1's new data emission inline. No schedule change.
- Post-deploy validation: open the home page on a desktop that's had Phase 1 installed, confirm the binder header shows a "0-0" aggregate, follow a player, wait for next day's build, make a prediction, verify next-day resolution lands. Two-day manual walk.
- Consider logging `prediction.context_tag` frequencies post-ship to understand which rules fire most — data for future rule library tuning.

## Sources & References

- **Origin document:** `docs/brainstorms/2026-04-11-player-cards-memory-prediction-requirements.md`
- **Ideation:** `docs/ideation/2026-04-11-player-cards-phase-2-ideation.md` (ideas #2 and #4)
- **Phase 1 plans:** `docs/plans/2026-04-11-001-feat-player-cards-cubs-mvp-plan.md`, `docs/plans/2026-04-11-002-feat-player-cards-all-teams-plan.md`
- **Related code:** `build.py:890` (_fetch_player_record), `build.py:840` (compute_temp_strip), `build.py:1005` (save_players), `cubs/player-card.js` (MorningLineupPC, renderFront, renderBack, mountInline), `home/home.js` (renderMyPlayersSection, loadFollowedPlayers), `home/home.css` (.binder, .binder-head), `data/players-<slug>.json`, `data/player-index.json`, `sections/headline.py`, `sections/scouting.py`, `tests/snapshot_test.py`
- **External docs:** MLB Stats API `/people/{pid}/stats?stats=gameLog` and `/schedule?teamId=X` — public, unauthed, CORS-friendly
