---
title: Unified Live-Polling Core
type: feat
status: active
date: 2026-04-10
origin: docs/brainstorms/2026-04-10-unified-live-core-requirements.md
---

# Unified Live-Polling Core

## Overview

Collapse the two independent polling implementations (`live.js` for the Cubs widget + slate; `scorecard/app.js` for the scorebook iframe) into one shared module — `live-core.js` — exposing a minimal subscribe API. Use the new core to light up two surfaces that are frozen today: standings (`sections/division.py` + `sections/around_league.py`) and yesterday's late-finals (`sections/around_league.py` + rival-results in `sections/division.py`). Big-bang replacement: old polling internals are deleted in the same ship.

The design insight from JB: subscribers that can be *derived* from another polled stream don't need timers. Only the source-of-truth subscribers (Cubs feed, today slate, scorebook feed, yesterday schedule) run on intervals. Standings is derived — it's refreshed once on page load and then only when another subscriber observes a Live→Final transition and kicks it via a `refreshNow()` handle. Cleaner, fewer fetches, sharper updates.

## Problem Frame

Two codebases duplicate fetch helpers, retry logic, visibility handling, and interval scheduling. They were written in different eras for different contexts and share zero code. Meanwhile, three reader-facing surfaces stay stale all day despite their underlying data moving: division standings, all-division standings blocks, and yesterday's scoreboard for games that finalized after the morning build ran. See origin: `docs/brainstorms/2026-04-10-unified-live-core-requirements.md`.

## Requirements Trace

- **R1** Shared `live-core.js` vanilla IIFE exposing `window.LiveCore`.
- **R2** Independent instance per frame (briefing + scorebook iframe each load their own).
- **R3** `subscribe({endpoint, intervalMs, idleIntervalMs, onData, onError})` with handle return value; core owns fetch, scheduling, visibility pause/resume, retry.
- **R4** Cubs widget migrates to a subscriber; reader-visible behavior unchanged.
- **R5** Slate cards migrate to a subscriber; reader-visible behavior unchanged.
- **R6** Scorebook polling migrates to a subscriber; rendering unchanged.
- **R7** Standings live — derived, timerless, kicked by slate/late-finals transitions.
- **R8** Yesterday's late-finals live, self-unsubscribing once all games Final.
- **R9** Old polling code (`live.js` timers + `scorecard/app.js` `startPolling`) deleted.
- **R10** Service worker cache bump `lineup-v6` → `lineup-v7`, `live-core.js` added to SHELL.
- **R11** 30-team mirroring preserved (formalized via `build.py`).

## Scope Boundaries

**In scope:** new `live-core.js` + mirrors, surgery on `live.js` and `scorecard/app.js`, DOM hook additions in `sections/division.py` and `sections/around_league.py`, `build.py` mirroring step, `sw.js` cache bump + SHELL update, `<script>` tag additions on briefing and scorebook HTML, snapshot re-bless.

**Out of scope (deferred):** `postMessage` cross-frame sharing, request coalescing across subscribers, domain-typed channels, exponential backoff, shared HTTP cache, merging `fetchPreviewExtras` standings call with the new standings subscriber, out-of-division rival live updates.

**Non-goals:** new polling endpoints beyond R1–R8, client-rendered SPA migration.

## Resolved Open Questions

- **OQ1 — Standings cadence:** Timerless. Standings is derived; slate and late-finals kick it via `refreshNow()` on Live→Final transitions. Page-load fetch is the only unconditional fetch. *(Sharper than the origin doc's 5min/60s adaptive proposal, and fewer fetches.)*
- **OQ2 — Late-finals stop condition:** Unsubscribe when every yesterday game reports Final. No clock cutoff.
- **OQ3 — File location:** Flat. `/live-core.js` at repo root and `/{slug}/live-core.js` per team. Matches existing `live.js` convention.
- **Mirroring mechanism:** Formalize via `build.py` for all mirrored static assets (`live-core.js`, `live.js`, `scorecard/*.js`, `scorecard/*.css`, `scorecard/index.html`, `sw.js`, `manifest.json`, `icons/*`). Idempotent per-team copy step runs during `build.py --team {slug}`. This kills the manual-copy footgun that affects `live.js` and the scorecard modules too.

## Context & Research

### Relevant Code and Patterns

- `live.js:11-15` — module-level `timer`/`slateTimer`/`paused` state; the thing being extracted.
- `live.js:60-219` — `renderLive`, `renderFinal`, `renderPreview`, `renderIdle` — **keep these**; they become callback bodies the Cubs subscriber invokes. Promote to `window.LiveRenderers` or a small export surface.
- `live.js:232-302` — `fetchPreviewExtras`; stays as a plain helper called from the Cubs subscriber's preview branch. Don't try to unify with the new standings subscriber (explicitly out of scope).
- `live.js:304-310` — `renderIdle`; keep.
- `live.js:312-362` — `updateSlate` + `pollSlate`; `updateSlate` keeps living but becomes a subscriber callback. `pollSlate` deleted.
- `live.js:366-434` — `scheduleCubs`, `pollFeed`, `checkCubs`; logic migrates into the Cubs subscriber config (endpoint + interval selection + onData branching). Functions themselves deleted.
- `live.js:438-450` — visibility handler; **deleted**, the core owns visibility now.
- `scorecard/app.js:190-227` — `startPolling` / `stopPolling` / inner `poll`; deleted. `updateScorecard` / `updateSituationBar` / `removeSituationBar` / `showFinalBadge` are kept and called from the new subscriber's `onData`.
- `sections/division.py:20-36` — standings table row template (needs `data-team-id`).
- `sections/division.py:39-68` — rival-results cards (need `data-gpk` on rival card divs for late-finals updates).
- `sections/around_league.py:28-47` — yesterday's scoreboard rows (need `data-gpk`; already have `data-href`).
- `sections/around_league.py:50-74` — all-division standings tables (need `data-team-id`).
- `build.py:63` — `OUT = ROOT / _team_slug / "index.html"` — the per-team output path convention the mirroring step will mirror alongside.
- `build.py:817` — `<script src="live.js"></script>` — add `<script src="live-core.js"></script>` immediately before this line.
- `sw.js:1-2` — `CACHE = "lineup-v6"` and `SHELL` list; both need updating.
- `deploy.py:135-150` — `STATIC_ASSETS` list; add `live-core.js` (root asset) so deploy pushes it.

### Institutional Learnings

- `feedback_commit_push.md` — when JB says ship, ship. This is a big-bang replacement, not a parallel rollout.
- `feedback_rebuild_all_teams.md` — when changing shared assets, rebuild **all 30 teams**, not just Cubs. Re-run `build.py --team {slug}` for every slug after the DOM hook changes land.
- Snapshot harness at `tests/snapshot_test.py` — DOM markup changes will intentionally break the golden snapshots; a re-bless is part of the ship.

### Mirroring Reality Check

Current state: `live.js`, `scorecard/*`, `sw.js`, `manifest.json`, `icons/*` in `{slug}/` dirs are git-tracked and identical to the root copies (verified: `md5sum live.js cubs/live.js mets/live.js` all match). There is **no script** that copies them today — they've been kept in sync by manual `cp` commands and ad-hoc editing. `deploy.py` only pushes `{slug}/index.html` + root assets; the per-team JS/SW files are pushed via regular `git push`. Formalizing the mirroring in `build.py` is cheap insurance against future drift and makes this plan's 30× `live-core.js` propagation trivial.

## Key Technical Decisions

- **Timerless standings via `refreshNow()` on the subscribe handle.** Rationale: every meaningful standings change is bracketed by a Live→Final transition that either the slate or late-finals subscriber will see on its next tick. Polling standings independently is duplicated work. The core exposes a `refreshNow()` method on the handle returned by `subscribe()`; derived subscribers are kicked by other subscribers' callbacks.
- **Core is a raw polling primitive, not a state manager.** No domain-typed channels in v1. Subscribers bring their own parsing and rendering. If duplication accumulates across subscribers later, typed channels become a refactor.
- **Independent instance per frame.** No `postMessage`. The briefing and scorebook iframe each load `live-core.js` and run their own copy. The one cost — the scorebook's active game gets polled twice (once by the slate subscriber, once by the scorebook subscriber) — is accepted per origin R2.
- **Fetch + retry + visibility pause owned by core.** Subscribers should never touch `setTimeout`, `fetch`, or `visibilitychange` directly. Verifiable via SC6 code audit.
- **Big-bang deletion of old polling.** No parallel rollout, no feature flag. Old `pollFeed`/`checkCubs`/`pollSlate`/`startPolling` are removed in the same commit that introduces the subscribers. Reduces the window where two polling loops could race or conflict on visibility state.
- **Build-time mirroring over runtime symlinks.** Simpler to reason about, works on GitHub Pages static hosting, idempotent re-runs. `build.py --team {slug}` becomes the single source of truth for what lands in `{slug}/`.
- **`live-core.js` loads BEFORE `live.js` / `scorecard/app.js`** in every HTML file that uses it. The core is a dependency; load order matters because `live.js` calls `window.LiveCore.subscribe` at IIFE init time.

## High-Level Technical Design

> *This illustrates the intended subscribe API shape and the timerless-standings wiring. It is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

**Subscribe API sketch:**

```
window.LiveCore = (function () {
  // returns handle: { unsubscribe(), refreshNow(), setInterval(ms) }
  function subscribe(options) { ... }
  return { subscribe };
})();

// options shape:
// {
//   endpoint: "https://..."  OR  () => "https://..."   // function for time-dependent URLs (today, yesterday)
//   intervalMs: 20000                                  // when active
//   idleIntervalMs: 300000                             // when core wants to slow down (optional)
//   isActive: (data) => boolean                        // optional; if false, core uses idleIntervalMs. Default: always active.
//   onData: (parsedJson, handle) => void               // required
//   onError: (err, handle) => void                     // optional
//   startPaused: boolean                               // optional; default false
// }
```

**Subscriber wiring (userland):**

```
// Slate (source of truth for Live→Final transitions on today's slate)
var slateHandle = LiveCore.subscribe({
  endpoint: () => API + "/schedule?sportId=1&date=" + today() + "&hydrate=linescore,team",
  intervalMs: 20000,
  idleIntervalMs: 300000,
  isActive: (data) => data.dates?.[0]?.games?.some(g => g.status.abstractGameState === "Live"),
  onData: (data) => {
    var games = data.dates?.[0]?.games || [];
    var transitioned = updateSlate(games); // returns true if any card flipped Live→Final
    if (transitioned) standingsHandle.refreshNow();
  },
});

// Standings (derived — no interval)
var standingsHandle = LiveCore.subscribe({
  endpoint: API + "/standings?leagueId=103,104&season=" + year + "&standingsTypes=regularSeason",
  intervalMs: 0,           // 0 = never auto-poll; only fetches on subscribe() and on refreshNow()
  onData: (data) => { updateStandingsRows(data); updateAllDivisionBlocks(data); },
});

// Late-finals (source of truth for yesterday transitions; also kicks standings)
var lateFinalsHandle = LiveCore.subscribe({
  endpoint: () => API + "/schedule?date=" + yesterday() + "&sportId=1&hydrate=linescore,decisions",
  intervalMs: 120000,
  onData: (data, handle) => {
    var games = data.dates?.[0]?.games || [];
    var transitioned = updateYesterdayRows(games);
    if (transitioned) standingsHandle.refreshNow();
    if (games.length && games.every(g => g.status.abstractGameState === "Final")) {
      handle.unsubscribe();
    }
  },
});
```

**Key points the sketch illustrates:**
- `intervalMs: 0` means "never auto-poll" — the standings subscriber fetches on `subscribe()` (page load) and on every `refreshNow()` call, nothing else.
- `refreshNow()` is idempotent and safe to call multiple times; if one is in flight, the call is collapsed.
- `endpoint` can be a string or a function; functions are called at fetch time so date-dependent URLs refresh correctly.
- The `handle` argument passed into `onData` lets a subscriber unsubscribe itself (late-finals self-termination).
- Visibility pause/resume is entirely owned by core — subscribers don't see it.

## Implementation Units

- [ ] **Unit 1: Ship `live-core.js` core module**

**Goal:** Create the shared polling primitive at repo root with the subscribe API above. Self-contained, vanilla JS IIFE, no dependencies.

**Requirements:** R1, R2, R3

**Dependencies:** None.

**Files:**
- Create: `live-core.js`
- Test: `tests/live_core_test.html` *(manual harness — see Test scenarios; no automated JS test runner exists in this repo)*

**Approach:**
- Single IIFE exports `window.LiveCore = { subscribe }`.
- Internal state: a `subscribers` array; each entry has `{options, timer, paused, inFlight, lastRefreshPromise}`.
- `subscribe(options)` pushes the entry, performs an initial fetch, and returns a handle `{unsubscribe, refreshNow, setInterval}`.
- `refreshNow()` — if `inFlight`, return the existing promise; else trigger an immediate fetch, reset the interval timer. This collapses concurrent kicks into one fetch.
- `intervalMs: 0` — the scheduler explicitly skips `setTimeout` for that entry. Only subscribe-time and `refreshNow()` trigger fetches.
- `isActive(data)` — called after each successful fetch; result chooses between `intervalMs` and `idleIntervalMs` for the *next* timer. Default behavior when `isActive` is absent: always use `intervalMs`.
- One global `visibilitychange` handler: pauses all subscribers on hide, resumes on unhide with a 5s debounce (matches current `live.js:444-445` behavior). On resume, each subscriber fires once immediately (so the tab shows fresh data on focus).
- Error handling: on fetch failure, call `onError` if provided, and schedule the next retry using the same interval the subscriber is currently on. Matches current per-file retry posture.
- No logging in production path beyond `onError` callbacks — keep the primitive quiet.

**Patterns to follow:**
- Vanilla IIFE shape from `live.js:1-3` and `scorecard/app.js`.
- `esc()` / `today()` helper patterns — but the core itself doesn't need them; subscribers bring their own.

**Test scenarios:**
- Happy path: subscribe with `intervalMs: 5000`, assert fetch fires at subscribe-time and again at ~5s.
- Happy path: subscribe with `intervalMs: 0`, assert exactly one fetch occurs until `refreshNow()` is called; assert a second fetch after `refreshNow()`.
- Edge case: `refreshNow()` called while a fetch is in flight returns the same promise and does not double-fetch.
- Edge case: `refreshNow()` resets the next-tick timer so a subscriber doesn't double-fire (kick + scheduled tick within milliseconds).
- Edge case: `isActive` returning `false` selects `idleIntervalMs`; flipping back to `true` on a subsequent tick selects `intervalMs`.
- Edge case: `unsubscribe()` from inside `onData` stops all future fetches and timer callbacks.
- Error path: `fetch` rejects — `onError` called once, next fetch scheduled at current interval, no runaway loops.
- Error path: `onData` throws — error is caught and reported to `onError` (or console), scheduling continues.
- Visibility: hide tab → all subscribers' timers clear, no fetches during hidden window (verified in DevTools Network tab). Unhide → each subscriber fires once immediately, 5s debounce prevents double-fires on rapid hide/unhide.
- Integration: two subscribers, one derived via `refreshNow()` kick from the other — verify the kick triggers the derived fetch within one tick.

**Verification:** Manual harness page loads the module and exercises each scenario above against a mock endpoint (local JSON file or `https://statsapi.mlb.com`). DevTools Network tab confirms fetch cadence.

- [ ] **Unit 2: Formalize per-team asset mirroring in `build.py`**

**Goal:** Make `build.py --team {slug}` idempotently copy all mirrored static assets (including the new `live-core.js`) into `{slug}/` so drift becomes impossible. Removes the manual-`cp` footgun for `live.js`, `scorecard/*`, `sw.js`, `manifest.json`, `icons/*`.

**Requirements:** R11 (and indirectly R1, R4, R5, R6)

**Dependencies:** Unit 1 (needs `live-core.js` to exist at root; otherwise the mirror list would be fictional).

**Files:**
- Modify: `build.py`
- Test: manual — run `python3 build.py --team cubs` and diff `cubs/` against root before/after.

**Approach:**
- Add a `MIRROR_ASSETS` constant near the top of `build.py`:
  - Files: `live-core.js`, `live.js`, `sw.js`, `manifest.json`
  - Dirs: `scorecard/`, `icons/`
- Add `_mirror_static_assets(slug)` helper, called from the same code path that writes `{slug}/index.html` (`build.py:925-926` vicinity).
- Use `shutil.copy2` for files, `shutil.copytree(..., dirs_exist_ok=True)` for dirs.
- Skip copying if source mtime ≤ destination mtime (cheap idempotence).
- Runs for every `--team {slug}` invocation, including the all-teams loop (verify `build.py:868-870` still catches it).
- Do **not** mirror `{slug}/index.html` into the list — that's already written by the main build path.

**Patterns to follow:**
- Stdlib-only (`shutil`, `pathlib`) per the "zero external dependencies" rule from CLAUDE.md.
- Deferred-import pattern inside the helper function if anything cross-imports from `build.py`.

**Test scenarios:**
- Happy path: run `build.py --team cubs`, verify `cubs/live-core.js` exists and `md5sum` matches root.
- Happy path: run `build.py --team cubs` twice in a row — second run does no work (mtime check) or at worst re-copies identical bytes.
- Edge case: touch root `live.js`, re-run — per-team copy is refreshed.
- Edge case: run with a team that's missing from disk (e.g., a never-built slug) — the mirror step creates the dir.
- Integration: run all-teams loop end-to-end, verify every 30 `{slug}/live-core.js` appears.

**Verification:** After running the all-teams build, `find . -name live-core.js | wc -l` returns 31 (root + 30 teams).

- [ ] **Unit 3: Migrate `live.js` (Cubs widget + slate) to subscribers**

**Goal:** Delete `live.js`'s timer/visibility/fetch machinery. Keep the render functions. Wire two subscribers — one for the Cubs widget, one for the slate — that delegate to `LiveCore.subscribe`.

**Requirements:** R4, R5, R9

**Dependencies:** Unit 1 (core must exist).

**Files:**
- Modify: `live.js` (root — Unit 2 propagates)
- Modify: `build.py:817` (add `<script src="live-core.js"></script>` immediately before `<script src="live.js"></script>`)

**Approach:**
- Delete: `timer`, `slateTimer`, `paused`, `lastResumeAt` state vars (`live.js:11-16`); `scheduleCubs`, `pollFeed`, `checkCubs`, `pollSlate` functions; the `visibilitychange` handler at `live.js:438-450`; the `checkCubs(); pollSlate();` init calls at `live.js:454-455`.
- Keep and reuse as-is: `today()`, `esc()`, `teamAbbr()`, `fmtTime()`, `diamond()`, `renderLive`, `renderFinal`, `renderPreview`, `renderIdle`, `updateSlate`, `fetchPreviewExtras`, `ordinal()`, `DIV_NAMES`.
- Expose a `window.LiveRenderers = { updateSlate, renderLive, renderFinal, renderPreview, renderIdle, fetchPreviewExtras }` bag so other subscribers (late-finals) could reach into the slate update path in the future. Not strictly required for this ship, but a small hook that keeps subscribers from reaching into IIFE internals.
- Refactor `updateSlate(games)` to return a boolean: `true` if any card transitioned Live→Final on this call, `false` otherwise. Caller uses this to decide whether to kick standings.
- New Cubs-widget subscriber logic (replaces `checkCubs` / `pollFeed`):
  - Two-phase: first subscribe to the team schedule endpoint to decide which state the team is in; when a live game is found, the `onData` callback swaps the endpoint by calling `handle.unsubscribe()` and subscribing to the game-feed URL instead. Alternative: single subscriber with dynamic endpoint function that returns either the schedule URL or the game-feed URL based on current known state. **Choose:** the dynamic-endpoint approach — one handle, simpler lifecycle.
  - `isActive`: true when widget shows a live game; false otherwise (selects 20s vs 5min interval).
- New slate subscriber:
  - `endpoint`: `() => API + "/schedule?sportId=1&date=" + today() + "&hydrate=linescore,team"`
  - `intervalMs: 20000`, `idleIntervalMs: 300000`
  - `isActive`: any game in the response has `abstractGameState === "Live"`
  - `onData`: calls `updateSlate(games)`; if transition detected, calls `standingsHandle.refreshNow()` (the handle will be created by Unit 6 — until Unit 6 lands, guard the call with `if (window.standingsHandle)` so Unit 3 can ship standalone).
- Keep `updateSlate`'s anyLive tracking for `isActive` purposes, but don't use it for scheduling — that's now the core's job.

**Execution note:** Land Units 3 and 4 after Unit 1 is verified working via the manual harness. Do not interleave — each migration should be a clean swap.

**Patterns to follow:**
- Existing `live.js` IIFE shape; this unit trims it, not restructures it.

**Test scenarios:**
- Happy path: load Cubs team page during a live game — widget shows situation bar, diamond, linescore, AB/P, last play. Screenshot at t=0 and t=40s; diff shows expected changes (pitch count, outs).
- Happy path: load Cubs team page in idle state — `renderIdle` shows the no-game message. `fetchPreviewExtras` still fires for Preview state.
- Happy path: load during idle state — slate cards update at 5min interval (verify via Network tab).
- Happy path: load during any-game-live state — slate cards update at 20s interval.
- Edge case: Cubs game transitions Preview → Live — subscriber switches endpoint on the next tick.
- Edge case: Cubs game transitions Live → Final — `renderFinal` fires, widget stops ticking.
- Integration: `updateSlate` returns `true` on a slate-wide Live→Final transition and (once Unit 6 lands) kicks standings.
- Regression: all existing `live.js` render helpers produce byte-identical DOM to current output for a given fixture (snapshot-level check).

**Verification:** SC1 (no Cubs widget regression) and SC2 (no slate regression) pass via manual screenshot diff on the live site.

- [ ] **Unit 4: Migrate `scorecard/app.js` scorebook polling to a subscriber**

**Goal:** Delete `startPolling` / `stopPolling` from `scorecard/app.js`. Replace with a single `LiveCore.subscribe` call. Rendering code unchanged.

**Requirements:** R6, R9

**Dependencies:** Unit 1, Unit 2 (so `live-core.js` is present in `{slug}/scorecard/` loader path).

**Files:**
- Modify: `scorecard/app.js`
- Modify: `scorecard/index.html` (add `<script src="../live-core.js"></script>` before `<script src="app.js"></script>`; use `../live-core.js` since the scorebook iframe loads from `{slug}/scorecard/` and `live-core.js` lives at `{slug}/live-core.js`)

**Approach:**
- Delete `startPolling` / `stopPolling` / inner `poll` (`scorecard/app.js:190-227`). Delete `pollTimer`, `paused`, `POLL_MS` module state where applicable (keep `POLL_MS` as a constant used in the new subscriber config).
- Replace with: on game load, call `LiveCore.subscribe({endpoint: () => SC.api.feedUrl(gamePk), intervalMs: POLL_MS, onData: (feed, handle) => { newModel = SC.parser.parse(feed); if (isLive(newModel)) { updateScorecard(newModel); updateSituationBar(feed); } else { updateScorecard(newModel); removeSituationBar(); showFinalBadge(); handle.unsubscribe(); } }, onError: () => {}})`.
- Store the returned handle on module state so "load a different game" can unsubscribe the previous one.
- The visibility-pause behavior that `scorecard/app.js` doesn't currently have now comes for free from the core. This is a minor improvement, not a regression.

**Patterns to follow:**
- The existing `poll()` inner function body — the new `onData` is essentially a rename of that.

**Test scenarios:**
- Happy path: open `/cubs/scorecard/?game={pk}` on a live game — situation bar renders, diamond updates on new at-bats, linescore ticks.
- Happy path: live → Final transition — situation bar removed, Final badge appears, subscription unsubscribes (verify no further fetches in Network tab).
- Edge case: navigate between games (if finder routing exists) — previous subscription unsubscribes before the new one starts.
- Integration: hide tab for 30s during a live game — no fetches, unhide resumes.
- Regression: existing scorecard rendering (diamonds, inning columns, stat cells) is byte-identical to current output for a frozen feed fixture.

**Verification:** SC3 (no scorebook regression) passes via manual test on a live game.

- [ ] **Unit 5: Add DOM hooks to `sections/division.py` and `sections/around_league.py`**

**Goal:** Emit stable attributes on the rows the standings and late-finals subscribers need to target. Subscribers can then patch individual cells without re-rendering whole tables.

**Requirements:** R7 (DOM markup), R8 (DOM markup)

**Dependencies:** None — can ship before the JS subscribers exist (markup is harmless when nothing reads it).

**Files:**
- Modify: `sections/division.py` (add `data-team-id="{tid}"` to standings `<tr>` at line 28-31 and to rival card `<div>`s at lines 62-65)
- Modify: `sections/around_league.py` (add `data-team-id="{tid}"` to all-division standings rows at lines 64-66; add `data-gpk="{pk}"` to yesterday's scoreboard `<tr>` at line 41 — the `data-href` already exists, just add `data-gpk` alongside it)
- Modify: `tests/expected/*.html` (re-bless — see Unit 9)

**Approach:**
- `sections/division.py:28-31`: change `<tr{cls}>` to `<tr{cls} data-team-id="{tid}">`.
- `sections/division.py:62-65`: add `data-gpk="{pk}"` to the `<div class="rival">` open tag so the late-finals subscriber can find the rival card for a finishing game. `g.get("gamePk")` is already available in the loop.
- `sections/around_league.py:64-66`: change `<tr{cls}>` to `<tr{cls} data-team-id="{tid}">`.
- `sections/around_league.py:41`: change `<tr class="scorecard-link" data-href="scorecard/?game={pk}">` to `<tr class="scorecard-link" data-href="scorecard/?game={pk}" data-gpk="{pk}">`.

**Patterns to follow:**
- `_render_all_divisions` already uses `tid` in the loop at line 59 — the attribute addition is trivial.
- Existing `data-href` on the scoreboard row is the precedent for per-row data attributes.

**Test scenarios:**
- Happy path: build Cubs page, grep output for `data-team-id="112"` in the NL Central standings row. Expect exactly one match in `sections/division.py`'s output block and one in `sections/around_league.py`'s all-division NL Central block.
- Happy path: grep output for `data-gpk="` in the yesterday-scoreboard section — expect one per Final game.
- Happy path: build Yankees page — `data-team-id="147"` appears in AL East standings rows.
- Edge case: division.py rival card block with no rivals playing yesterday — no `data-gpk` anywhere in that block (handled by the existing "All off yesterday" fallback).
- Regression: snapshot test fails with a clear diff showing only the added attributes.

**Verification:** `python3 tests/snapshot_test.py` fails with expected diffs; re-bless in Unit 9.

- [ ] **Unit 6: Standings live subscriber (derived, timerless)**

**Goal:** New subscriber that fetches MLB standings once on page load and then only on `refreshNow()` kicks from slate / late-finals. Updates division.py's standings table, around_league.py's six all-division blocks, and maintains the my-team highlight across row reshuffles.

**Requirements:** R7

**Dependencies:** Unit 1, Unit 3 (slate subscriber needs to exist to kick this), Unit 5 (DOM hooks).

**Files:**
- Modify: `live.js` (add the standings subscriber registration and the `updateStandingsRows` / `updateAllDivisionBlocks` helpers)

**Approach:**
- New helper `updateStandingsRows(data, myTeamId)`:
  - For each division record, for each team record, find `tr[data-team-id="{tid}"]` in both the primary standings table (`.standings`, first one on page is `division.py`'s) and all six all-division tables in `#around-league`.
  - Update W, L, PCT, GB, L10 cells. Preserve the `.my-team` class on rows (don't clobber classList).
  - If the division rank order changes, re-sort the rows within their `<tbody>`. Detect by comparing the current DOM order of `data-team-id` values against the order in the fresh `data` response; if different, reorder nodes via `parentNode.appendChild()` in the new order.
- Subscribe config: `intervalMs: 0`, `onData: updateStandingsRows + updateAllDivisionBlocks`, no `isActive`.
- Expose the handle as `window.standingsHandle` so the slate (Unit 3) and late-finals (Unit 7) subscribers can call `refreshNow()`.
- Initial fetch happens automatically at subscribe time — no manual kick needed on page load.

**Patterns to follow:**
- `fetchPreviewExtras` (`live.js:256-276`) already shows how to walk the `/v1/standings` response. Reuse that traversal logic for the update helper.

**Test scenarios:**
- Happy path: page loads at 1pm — standings table matches the current MLB state within the time it takes one fetch to complete.
- Happy path: at 9pm a game ends — slate observes Live→Final, calls `standingsHandle.refreshNow()`, standings table updates within one tick (~20s latency from the slate's next poll + one HTTP roundtrip). My-team row stays highlighted.
- Edge case: division rank reshuffle — e.g., Cubs pass Brewers for 1st. Rows re-order; `.my-team` row stays highlighted on Cubs.
- Edge case: game ends but no standings change (team was already eliminated / already mathematically locked) — `refreshNow` fetches, `updateStandingsRows` produces identical DOM, no visual flicker.
- Error path: `/v1/standings` returns 500 — `onError` logs, next `refreshNow()` call retries. No timer means no runaway retry loop.
- Integration: verify `refreshNow()` is idempotent — two transitions in the same slate tick collapse into one fetch.

**Verification:** SC4 (standings tick through the day) passes via manual observation of a late-afternoon game finalizing.

- [ ] **Unit 7: Yesterday's late-finals subscriber**

**Goal:** New subscriber polls yesterday's schedule every 2 minutes while any yesterday game is non-Final. On transition to Final, updates `around_league.py`'s yesterday-scoreboard row and (if in user's division) the rival-results card in `division.py`. Self-unsubscribes when all yesterday games are Final. Kicks standings on every transition.

**Requirements:** R8

**Dependencies:** Unit 1, Unit 5 (DOM hooks), Unit 6 (standings handle to kick).

**Files:**
- Modify: `live.js` (add the subscriber + `updateYesterdayRows` helper)

**Approach:**
- On page init, check: are there any `tr[data-gpk]` in the yesterday-scoreboard whose corresponding game state from the morning build was non-Final? If the morning build only renders Final games into the table (per `sections/around_league.py:31` — `if g.get("status", {}).get("abstractGameState") != "Final": continue`), then rows that *should* exist for late-running games **aren't rendered at all**. This is a latent bug: a game that was "In Progress" at morning build time is simply missing from the table.
  - **Decision:** the morning build should emit the row for non-Final games too, with placeholder scores, so the subscriber has a target to patch. Add a tiny extension to `sections/around_league.py:31` — keep the `continue` only when the game is in Preview (never started); for Live / In Progress / Manager Challenge / Suspended, emit a row with empty score cells and `data-pending="1"` so the subscriber can find it.
  - Flag this as an origin-doc gap: R8 assumed rows exist; they don't. Add to Unit 7's scope.
- Subscriber config:
  - `endpoint: () => API + "/schedule?date=" + yesterday() + "&sportId=1&hydrate=linescore,decisions"`
  - `intervalMs: 120000`
  - `onData`: iterate games; for each Final game, find `tr[data-gpk="{pk}"]` in the yesterday scoreboard and update its score / winner / WP cells. Clear `data-pending`. If the game involves a team in the user's division rival list, also find `.rival[data-gpk="{pk}"]` in `division.py`'s rival block and update its score / winner / WP. Call `standingsHandle.refreshNow()` once if any transition occurred this tick.
  - Self-termination: if `games.every(g => g.status.abstractGameState === "Final")`, call `handle.unsubscribe()`.
- On page load, if no pending rows exist (grep for `data-pending="1"` returns zero), don't subscribe at all — nothing to watch.

**Patterns to follow:**
- `updateSlate` (`live.js:314-345`) for the "walk response, find DOM node by data attribute, patch cells" shape.

**Test scenarios:**
- Happy path: morning build runs at 7am after a West Coast game is still "In Progress". Page loads at 8am. Pending row for that game is visible with placeholder cells. Within 2 min the subscriber detects Final and fills in scores, winner, WP.
- Happy path: the late-finalized game belongs to a division rival (e.g., Brewers finish late, user is on Cubs page). The rival-results card in `sections/division.py` also updates. Standings subscriber is kicked.
- Happy path: all yesterday games are already Final at morning build time — subscriber never subscribes. `data-pending` is absent everywhere.
- Happy path: last pending game transitions — subscriber unsubscribes itself, no further fetches.
- Edge case: a game is Suspended → resumed the next day. Treated as pending until Final; the subscriber waits.
- Edge case: the same game is Final in the response but our row already shows Final (e.g., a double-fetch race) — `updateYesterdayRows` is idempotent, no visual change.
- Error path: `/v1/schedule?date=yesterday` returns 500 — retry at 2min interval.
- Integration: transition kicks standings; standings refreshes; both DOM regions update in the same user-visible beat.

**Verification:** SC5 (late finals propagate) passes via manual observation the morning after a game finishes after the morning build runs.

- [ ] **Unit 8: Service worker cache bump + SHELL update**

**Goal:** Bump `sw.js` cache version `lineup-v6` → `lineup-v7` at root and all 30 team mirrors, and add `/morning-lineup/live-core.js` to the SHELL. After Unit 2, the team mirrors are automatic.

**Requirements:** R10

**Dependencies:** Unit 1 (file must exist), Unit 2 (mirroring handles the 30× propagation).

**Files:**
- Modify: `sw.js` (root)
- Modify: `deploy.py:135` (add `live-core.js` to `STATIC_ASSETS`)

**Approach:**
- `sw.js:1`: `const CACHE = "lineup-v7";`
- `sw.js:2`: add `"/morning-lineup/live-core.js"` to `SHELL`.
- Per-team `sw.js` propagation happens via Unit 2's mirroring step during the next `build.py` run.
- Add `"live-core.js"` to `deploy.py`'s `STATIC_ASSETS` list so the root asset lands on GitHub Pages.
- Per-team `{slug}/live-core.js` reaches GitHub via normal git commit + push (same mechanism as `{slug}/live.js` today — `deploy.py` doesn't push per-team JS).

**Patterns to follow:**
- `2026-04-09` columnist redesign ship: `50bad20 chore(sw): bump team sw.js cache to lineup-v3`, `030fe4f chore(sw): bump cache version to lineup-v3` — same pattern, one commit.

**Test scenarios:**
- Happy path: after deploy, browser shows new SW activating, `lineup-v7` cache appears in DevTools Application tab, `live-core.js` is in the cache.
- Happy path: old `lineup-v6` cache is deleted on activation (existing code at `sw.js:14-18` handles this).
- Edge case: user with a cached v6 SW hits the site — new SW installs, skips waiting, takes over, v6 cache is purged, v7 is populated.
- Regression: existing precached assets (index.html, live.js) still load offline.

**Verification:** DevTools Application → Service Workers shows `lineup-v7` active; Application → Cache Storage → `lineup-v7` contains `live-core.js`.

- [ ] **Unit 9: Snapshot re-bless**

**Goal:** Accept the DOM markup changes from Unit 5 as the new golden output. Update `tests/expected/*.html` to match.

**Requirements:** Supports SC8.

**Dependencies:** Unit 5 must be landed; Units 6–8 do not affect snapshots (runtime-only changes).

**Files:**
- Modify: `tests/expected/cubs.html`, `tests/expected/yankees.html` (re-bless per `tests/README.md`)

**Approach:**
- Run `python3 tests/snapshot_test.py`, confirm the diff is *only* the added `data-team-id` and `data-gpk` attributes (plus any `data-pending` rows from Unit 7's morning-build extension).
- If the diff shows anything else, stop and investigate before re-blessing.
- Re-bless via the documented procedure in `tests/README.md`.

**Test scenarios:**
- Test expectation: none — this is the test-update unit itself. Correctness is verified by the diff being confined to intentional markup changes.

**Verification:** `python3 tests/snapshot_test.py` passes.

- [ ] **Unit 10: Rebuild all 30 teams + deploy**

**Goal:** Ensure every team page ships the new markup and loads `live-core.js` in the correct order. Big-bang across all teams per `feedback_rebuild_all_teams.md`.

**Requirements:** R11 operationally.

**Dependencies:** Units 1–9 all landed.

**Files:**
- None modified in this unit — it's a build + deploy invocation.

**Approach:**
- `python3 build.py` (the all-teams loop at `build.py:868-870`, which now picks up Unit 2's mirroring step for every slug).
- Spot-check Cubs, Yankees, Mets, Dodgers `index.html` for `<script src="live-core.js">` appearing before `<script src="live.js">`.
- Spot-check a few `{slug}/live-core.js` for md5 match with root.
- `source ~/.secrets/morning-lineup.env && python3 deploy.py`.
- Hard-refresh live site, confirm new SW activates.

**Test scenarios:**
- Test expectation: none — operational step. Verification via smoke test on the live site.

**Verification:** All five success criteria (SC1–SC5, SC7) verified on the live site. SC6 (code audit) verified via `grep -n "setTimeout\|setInterval\|visibilitychange" live.js scorecard/app.js` returning no polling-related matches.

## System-Wide Impact

- **Interaction graph:** The slate subscriber and late-finals subscriber both hold a reference to the standings handle and call `refreshNow()` on transitions. If the standings subscription fails to initialize (e.g., endpoint 500 at page load), both kick calls should be no-ops — verify via `if (window.standingsHandle) standingsHandle.refreshNow()` guards.
- **Error propagation:** Each subscriber's `onError` is called in isolation; errors don't cascade. A standings fetch failure does not affect the slate subscriber.
- **State lifecycle risks:** Two subscribers mutating the same DOM region is possible in theory (standings subscriber updates `.standings` rows; the morning-build-rendered `.standings` is initially present). Subscribers must be additive (patch cells by `data-team-id`) not destructive (no `innerHTML = ""` on `<tbody>`). The my-team highlight class is a particular concern — don't clobber `classList`.
- **API surface parity:** The subscribe API should feel identical for any future subscriber (league news, etc.) even though v1 only ships five. Review unit scenarios should confirm the core never assumes a subscriber shape.
- **Integration coverage:** The key behavior that unit tests alone can't prove: slate-sees-transition → calls `standingsHandle.refreshNow()` → standings DOM updates. This is integration territory and is covered by SC4 manual verification, not a unit test.
- **Unchanged invariants:** `live.js`'s render functions produce byte-identical DOM to current output. `scorecard/app.js`'s `updateScorecard` / `updateSituationBar` / `showFinalBadge` produce byte-identical DOM. Morning-build HTML output changes only by the added `data-team-id` / `data-gpk` / optional `data-pending` attributes — no content shifts, no reflows, no visual deltas.

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Load-order bug — `live.js` tries to call `LiveCore.subscribe` before `live-core.js` has loaded | `<script>` tags are synchronous by default; placing `live-core.js` before `live.js` in the HTML guarantees order. Verified in Unit 3's `build.py:817` edit. |
| `refreshNow()` stampede — multiple transitions in the same tick fire multiple fetches | Core collapses concurrent `refreshNow()` into one in-flight promise (Unit 1 test scenario). |
| Per-team drift between root and `{slug}/live-core.js` | Unit 2's mirroring step eliminates manual sync. Idempotent, runs on every `build.py` invocation. |
| Morning-build lacks rows for non-Final yesterday games, so late-finals subscriber has no target to patch | Unit 7 adds placeholder row emission for non-Final games in `sections/around_league.py:31`. Flagged as an origin-doc gap. |
| Visibility-pause regression — core owns it now, but a subscriber that holds its own `setTimeout` would escape the pause | SC6 code audit grep for `setTimeout`/`setInterval` in userland JS. Any hit is a review-blocker. |
| `<tbody>` row reorder while user is reading — subtle visual disruption | Only reorder when rank actually changes. Minimal scroll disruption at that point because it's below-the-fold. Accepted cost. |
| Snapshot false negative — the re-bless accidentally accepts an unrelated regression | Unit 9 requires diff to be confined to intentional attrs; stop and investigate if anything else changes. |
| Scorebook iframe loads `../live-core.js` but the path is wrong on local dev vs. GitHub Pages | Verify path works in both: local `python3 -m http.server` from repo root serves `/live-core.js`; GitHub Pages serves `/morning-lineup/live-core.js`. The `../live-core.js` relative path from `{slug}/scorecard/index.html` resolves correctly in both cases. |

## Documentation / Operational Notes

- Update CLAUDE.md's "Live polling" line under "Important patterns" to describe the new architecture (one shared core, subscribe API, derived/source-of-truth subscriber distinction).
- After ship, document the `refreshNow()` event-driven pattern in `docs/solutions/` as a reusable technique for future derived subscribers.
- PM2 / Cloudflare Tunnel: no impact. This ship is all client-side.
- Evening watcher (`evening.py`): unchanged. It triggers full rebuilds, not in-page updates.

## Sources & References

- **Origin document:** [docs/brainstorms/2026-04-10-unified-live-core-requirements.md](../brainstorms/2026-04-10-unified-live-core-requirements.md)
- Related code:
  - `live.js` (root, 30 team mirrors)
  - `scorecard/app.js` (root, 30 team mirrors)
  - `sections/division.py`, `sections/around_league.py`
  - `build.py:817`, `build.py:868-870`, `build.py:925-926`
  - `sw.js:1-2`
  - `deploy.py:135-150`
- Related prior ship: `6b0199f feat(columnists): editorial redesign of columnist rows + sw bump` — most recent cache-bump precedent.
- Memory: `feedback_rebuild_all_teams.md`, `feedback_commit_push.md`.
