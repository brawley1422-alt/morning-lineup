---
date: 2026-04-10
topic: unified-live-core
source_ideation: docs/ideation/2026-04-10-affordance-debt-ideation.md (idea #4)
---

# Unified Live-Polling Core — Requirements

## Context

Morning Lineup has two independent live-polling implementations today:

1. **`live.js`** (root, mirrored to all 30 team dirs) — polls the team's widget via `/v1.1/game/{pk}/feed/live` (adaptive 20s live / 5min idle) AND polls today's full slate via `/v1/schedule` and updates `.g[data-gpk]` cards in place (`live.js:312-362`). Owns visibility-API pause/resume, preview-extras fetch for opponent record + season series + lineup, and idle rendering.
2. **`scorecard/app.js`** (mirrored to all 30 team dirs) — polls `/v1.1/game/{pk}/feed/live` at 20s intervals for the currently-viewed scorebook game (`scorecard/app.js:192-219`). Updates diamonds, situation bar, and linescore via in-place DOM mutation. No visibility pause, no idle rate.

These share zero code. They duplicate fetch helpers, retry logic, state machines, and poll loops. They were built at different times for different contexts.

**What's actually frozen today** (despite the ideation's framing — the slate is NOT frozen, `live.js` polls it): `sections/division.py` standings tables, `sections/around_league.py` all-division standings blocks, and `sections/around_league.py` yesterday's scoreboard for late-finishing games. All three render at morning build time and never update, even though the underlying data can change (standings flip as games end; late West Coast games finalize after the morning build).

## Goal

Collapse both poll loops into a single shared module `/assets/live-core.js` with a subscribe API. Light up standings + yesterday's late-finals as new subscribers so division.py and around_league.py stop being frozen. Delete the old per-file polling code — this is a big-bang replacement, not a parallel rollout.

## Requirements

### R1 — Shared core module at `/assets/live-core.js` <!-- HIGH -->
A single vanilla-JS IIFE exposing `window.LiveCore` with a subscribe API. Mirrored to each team dir alongside the existing `live.js` and `scorecard/` mirrors. Build process copies it like it copies `live.js` today.

### R2 — Independent instance per frame <!-- HIGH (JB answered) -->
Both the briefing page and the scorebook iframe load their own copy of `live-core.js` and each runs independently. No `postMessage` protocol, no cross-frame state sharing. Duplicate polling of the one game viewed in the scorebook is accepted as a minor cost.

### R3 — Subscribe API owns polling + visibility + errors <!-- HIGH -->
`LiveCore.subscribe({endpoint, intervalMs, idleIntervalMs, onData, onError})` registers a subscriber. Core handles: HTTP fetch, interval scheduling, `visibilitychange` pause/resume, retry-on-error, and calling the subscriber's `onData` callback with parsed JSON. Subscribers bring their own DOM rendering and data parsing. No domain-typed channels — core is a polling primitive, not a state manager. <!-- MEDIUM: subscribe API surface to be refined in planning -->

### R4 — Cubs widget migrates to the core <!-- HIGH -->
The existing Cubs-widget polling (`live.js:393-434` — `checkCubs`, `pollFeed`, `fetchPreviewExtras`, `renderLive`, `renderFinal`, `renderPreview`, `renderIdle`) becomes a subscriber that registers a game feed endpoint when a game is live and a schedule endpoint when idle. Reader-visible behavior must not regress — same widget, same adaptive rate, same visibility handling.

### R5 — Slate cards migrate to the core <!-- HIGH -->
The slate-updating loop (`live.js:312-362` — `updateSlate`, `pollSlate`) becomes a subscriber that polls today's `/v1/schedule` and calls `updateSlate(games)`. Same adaptive cadence: fast when any game is live, idle otherwise. Same `.g[data-gpk]` card update semantics as today.

### R6 — Scorebook migrates to the core <!-- HIGH -->
`scorecard/app.js:192-219` (`startPolling`, the `poll` inner function) becomes a subscriber. Situation bar updates, diamond re-renders, and linescore updates all remain unchanged — this requirement only changes how the poll is scheduled, not what happens in the render callback.

### R7 — Standings live as a new subscriber <!-- HIGH -->
New subscriber polls `/v1/standings?leagueId=103,104&season={year}&standingsTypes=regularSeason`. On each response, updates matching rows in `sections/division.py`'s standings table AND `sections/around_league.py`'s six all-division standings blocks. Updates W/L, PCT, GB, L10, streak code, and row ordering (division rank changes reshuffle rows).
- **Cadence:** 5min default, 60s when any today game is Live (so standings reflect a W/L flip within a minute of a game ending). <!-- MEDIUM: cadence values are a sensible default, JB to confirm -->
- **DOM markup change:** `sections/division.py:28-31` and `sections/around_league.py:64-66` must add `data-team-id="{tid}"` attributes so the subscriber can find rows without re-rendering the whole table. <!-- LOW: exact hook selector to be finalized in planning -->

### R8 — Yesterday's late-finals as a new subscriber <!-- HIGH -->
New subscriber polls `/v1/schedule?date={yesterday}&sportId=1&hydrate=linescore,decisions` every 2 minutes *while any game from yesterday is still non-Final*. When a game finalizes, updates the matching row in `sections/around_league.py:28-47`'s yesterday-scoreboard table (scores, winner, WP) AND the matching rival row in `sections/division.py`'s rival-results block if it's in the user's division. Subscriber self-unsubscribes once all yesterday games are Final. <!-- MEDIUM: 2min cadence is a sensible default -->
- **DOM markup change:** `sections/around_league.py:41` already emits `data-href="scorecard/?game={pk}"` — extend to also emit `data-gpk="{pk}"` so the subscriber can address the row. <!-- LOW -->
- **Boundary condition:** subscriber should only run until ~noon local time, to avoid pointless polling of a fully-final slate. <!-- LOW: exact cutoff TBD -->

### R9 — Delete the old polling code <!-- HIGH -->
After the migration lands, `live.js`'s polling internals (`checkCubs`, `pollFeed`, `pollSlate`, `updateSlate`, the visibility handler at lines 438-450, the `timer`/`slateTimer`/`paused` state) are removed. The file shrinks to just the render functions (`renderLive`, `renderFinal`, `renderPreview`, `renderIdle`, `diamond`) which become exports the core's subscriber callbacks use. `scorecard/app.js:192-219` `startPolling`/`stopPolling` is removed — the core takes over. Per `feedback_commit_push.md` and JB's fast-ship style, this is a big-bang replacement, not a parallel rollout.

### R10 — Service-worker cache bump <!-- HIGH -->
`sw.js` (and all 30 team mirrors) bump cache version lineup-v6 → lineup-v7. `/assets/live-core.js` added to the cached asset list at the appropriate path for root + each team mirror.

### R11 — 30-team mirroring preserved <!-- HIGH -->
`build.py`'s per-team output pipeline must copy `/assets/live-core.js` into each team dir the same way it copies `live.js` and `scorecard/*.js` today. Script/build changes must be idempotent with re-runs. <!-- LOW: exact copy mechanism to be confirmed against build.py in planning -->

## Success Criteria

### SC1 — No Cubs-widget regression <!-- HIGH -->
On the Cubs team page during a live Cubs game: the Cubs widget renders the same situation bar, diamond, linescore, AB/P matchup, and last-play caption as before. Adaptive polling cadence matches current behavior (20s live, 5min idle). Visibility API still pauses when tab is hidden and resumes (with 5s debounce) on focus. Verified via: load the page during a live Cubs game, take screenshots at t=0 and t=40s, diff for expected cell changes.

### SC2 — No slate regression <!-- HIGH -->
`.g[data-gpk]` cards still update in place with score + inning indicator while any game is live. Card classes (`g-live`, `g-final`) toggle correctly. Screenshot-verified.

### SC3 — No scorebook regression <!-- HIGH -->
Open `/scorecard/?game={pk}` on a live game. Situation bar appears, diamonds update in place as new at-bats happen, linescore ticks, and the transition to Final correctly removes the situation bar and shows the final badge. Manual smoke test + screenshot at live+Final transition.

### SC4 — Standings tick through the day <!-- HIGH -->
Load a team page at 1pm after the morning build. When a game ends anywhere in MLB, the division standings table + all-division blocks in around_league update within ~60 seconds to reflect the new W/L, GB, and ordering. My-team highlight stays on the correct row after a rank reshuffle. Verified manually by watching a late-afternoon game finalize.

### SC5 — Late finals propagate <!-- HIGH -->
Load a team page at 8am after a night where a West Coast game finished after the build trigger ran (game status = "In Progress" or "Manager Challenge" in the morning build). Within ~2min, the yesterday's-scoreboard row updates with final score, winner abbreviation, and WP. If that game was in the user's division, the division rival-results block also updates. Self-unsubscribes once complete.

### SC6 — One poll loop, not two <!-- HIGH -->
Code audit: `live.js` contains no `setTimeout`/`setInterval` calls for polling. `scorecard/app.js` contains no polling loop. Both delegate to `LiveCore.subscribe`. Grep confirms single source of truth. <!-- Accept: the two frames each have their own LiveCore instance; that's by R2. -->

### SC7 — Visibility pause works for all subscribers <!-- HIGH -->
Hide the tab for 30 seconds. Verify no fetches happen during that window (DevTools Network tab). Unhide. Verify all subscribers resume on the next tick. Applies to all five subscribers (Cubs widget, slate, scorebook, standings, late-finals).

### SC8 — Snapshot tests pass <!-- HIGH -->
`python3 tests/snapshot_test.py` passes. The DOM markup changes in R7 (`data-team-id` attributes) and R8 (`data-gpk` on yesterday's scoreboard rows) WILL break snapshots — expect a re-bless, not an unchanged pass. The re-bless is part of the ship.

## Scope Boundaries

### In scope
- New file: `/assets/live-core.js` and its 30 team mirrors
- Edits: `live.js` (delete polling, keep render helpers as exports) + 30 team mirrors
- Edits: `scorecard/app.js` (delete polling, keep render code) + 30 team mirrors
- Edits: `sections/division.py` (add `data-team-id` to standings rows + rival-results markup hooks)
- Edits: `sections/around_league.py` (add `data-team-id` to all-division blocks + `data-gpk` to yesterday-scoreboard rows)
- Edits: `build.py` (mirror `/assets/live-core.js` into each team dir during build)
- Edits: `sw.js` + 30 team mirrors (cache version bump v6 → v7, add new asset)
- Edits: briefing `<script>` tags so team pages load `/assets/live-core.js` before `live.js`
- Edits: `scorecard/index.html` so the scorebook loads `/assets/live-core.js` before `app.js`
- Re-bless of golden snapshots after DOM markup changes

### Out of scope (punt to future work)
- **`postMessage` protocol between briefing page and scorebook iframe** — R2 explicitly says independent instances. A shared singleton service is a bigger architectural effort and can be added later if duplicate polling becomes measurably wasteful.
- **Request coalescing across subscribers** — if two subscribers both ask for the same URL at the same interval, the core will fetch it twice in v1. Deduplication is an optimization for later. <!-- LOW: could be added cheaply; flag in planning -->
- **Domain-typed channels (`game:pk`, `standings`, etc.)** — v1 is a raw-polling primitive. If the subscribe API accumulates duplication, typed channels become a refactor; until then, keep it thin.
- **WebSocket or SSE streaming** — MLB Stats API doesn't offer streaming anyway; polling is the only option.
- **Exponential backoff on errors** — v1 retries at the normal interval on error, matching current behavior (`live.js:388-390`, `scorecard/app.js:212-215`). More sophisticated error posture is a follow-up.
- **Shared HTTP cache across frames** — each frame has its own cache. Out of scope per R2.
- **Unifying `live.js`'s `fetchPreviewExtras` (opponent record, season series, lineup) with the new standings subscriber** — both fetch `/v1/standings` but for different purposes. Deduping them is an optimization for later.
- **Live-updating rival results for non-my-division rivals in division.py** — yesterday's late-finals only update rival rows that are in the user's division; out-of-division rivals aren't shown in division.py anyway.

### Non-goals (will not ship, even as a follow-up)
- **Adding new polling endpoints beyond what's listed** — no game-state push, no league news polling, no Twitter/X embeds.
- **Deprecating the morning-build static HTML in favor of a fully client-rendered SPA** — the static build remains the source of truth. The live-core only patches specific DOM nodes.

## Open Questions

### OQ1 — Exact standings cadence <!-- MEDIUM -->
R7 proposes 5min idle / 60s when any today game is live. Alternative: always 60s (simpler, more reader-delightful, slight API cost) or always 5min (barely noticeable reader impact). JB to confirm during planning.

### OQ2 — Late-finals time cutoff <!-- LOW -->
R8 proposes self-unsubscribing around noon local. Alternative: subscribe only until all yesterday games are Final, regardless of clock time. Simpler — no time check needed. JB to confirm.

### OQ3 — Where exactly does `/assets/` live in the per-team dir? <!-- LOW -->
Current mirroring: `live.js` sits at root AND per-team dir. `scorecard/*.js` sits at root `scorecard/` AND per-team `{slug}/scorecard/`. New module could sit at `/assets/live-core.js` root + `/{slug}/assets/live-core.js` per team, OR flatter at `/live-core.js` root + `/{slug}/live-core.js` per team. Flatter matches existing mirroring style. JB to confirm. <!-- Probably flat: `live-core.js` at root. -->

## Session Log
- 2026-04-10: Brainstorm from ideation #4. JB confirmed: full unified rewrite, independent instance per frame, first ship includes core + standings live + yesterday's late-finals. Discovery during grounding: the slate is already live via `live.js:312-362` — ideation's framing was partially wrong. Real frozen surfaces are standings (division.py + around_league.py) and yesterday's late-finals.
