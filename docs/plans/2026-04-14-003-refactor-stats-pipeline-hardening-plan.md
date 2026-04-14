---
title: "refactor: Stats pipeline hardening — MLB + farm + deploy"
type: refactor
status: completed
date: 2026-04-14
---

# Stats Pipeline Hardening — MLB + Farm + Deploy

## Overview

Close every gap the 2026-04-14 audits surfaced in the morning-lineup stats
pipeline. Ten units, sequenced critical → medium → polish, so JB can ship
incrementally and stop firefighting April thin-sample bugs and silent
GitHub Pages build failures.

## Problem Frame

Two audit agents swept the repo on 2026-04-14:

- **MLB data audit** found the Cole Ragans-style "pitcher arsenal returns
  one pitch at 51% usage" bug is a general class problem, not a one-off.
  Every Savant fetch that lacks a prior-year fallback has the same latent
  bug in April. The audit also found `deploy.py` prints "live" even when
  GitHub Pages build fails silently — the cause of yesterday's 4 failed
  builds in a row.
- **Farm audit** found prospects are a static hand-edited JSON per team
  (`teams/{slug}/prospects.json`), affiliates fetch yesterday's box score
  only (no standings, no upcoming, no season stats), and MiLB transactions
  are actively filtered out at `build.py:333-337`, so promotions and
  call-ups never surface.

The goal is durability: after this plan lands, the pipeline should degrade
gracefully on thin samples, fail loudly on deploy breakage, and refresh
farm data automatically.

## Requirements Trace

Derived from the audit findings and JB's "don't want to worry about this
again" framing.

- **R1.** Pitcher arsenal uses prior-year data as fallback when current-year
  samples are too thin (mirrors batter-side fix already shipped at
  `build.py:573`).
- **R2.** `sections/matchup.py _expected_xwoba` treats any unaccounted
  usage slice as league-average xwOBA so incomplete arsenals don't
  artificially deflate expected xwOBA.
- **R3.** Savant batter and pitcher leaderboards (`savant["batter"]`,
  `savant["pitcher"]`) have prior-year fallback for thin April samples.
- **R4.** `deploy.py` verifies GitHub Pages build success before reporting
  "live" — silent failures become loud failures.
- **R5.** Evening rebuild watcher runs for every team with a game tonight,
  not just Cubs, and has a systemd timer so it starts unattended.
- **R6.** Client-side refresh triggers when MLB posts a starting lineup, so
  scouting and matchup sections re-render the same day.
- **R7.** Prospects data refreshes automatically instead of requiring hand
  edits to `teams/{slug}/prospects.json`.
- **R8.** Affiliate standings and tonight's MiLB slate are fetched and
  rendered in `sections/farm.py`.
- **R9.** MiLB transactions (promotions, call-ups, demotions) surface in
  the pressbox section instead of being filtered out.
- **R10.** Per-prospect season stats (BA/OPS/K%) are tracked so thin-April
  box-score lines aren't the whole story.
- **R11.** Dead data (`brl_percent` on pitcher leaderboard, `xwoba_allowed`
  on pitcher arsenal) is either rendered or removed from fetch.

## Scope Boundaries

- **Not rewriting `sections/farm.py` from scratch.** Units 7–9 extend the
  existing renderer; a full rewrite is out of scope.
- **Not building a real-time push system.** R6 is a polling/event check on
  the client, not websockets.
- **Not touching MLB Stats API auth or rate-limiting.** Existing patterns
  are fine.
- **Not changing the cache storage format.** We bump `_SAVANT_SCHEMA` as
  needed but don't migrate to a DB.
- **Not rewriting the morning trigger.** External Claude scheduled agent
  stays as the entrypoint. Evening watcher is separate.
- **Not adding alerting infrastructure beyond deploy verification.** No
  Slack/email wiring — deploy.py failing loudly is enough for now.

## Context & Research

### Relevant Code and Patterns

**Savant fetch + cache pattern** (the reference for units 1 and 3):

- `build.py:705` — `fetch_savant_leaderboards(season, today)` — top-level
  fetch + cache function
- `build.py:518` — `_SAVANT_SCHEMA = 4` — version bump invalidates cache
- `build.py:573` — `_merge_batter_arsenal(current, prior)` — the exact
  merge pattern units 1 and 3 should mirror
- `build.py:789` — shows where merged batter arsenal is written to the
  `savant` dict; units 1 and 3 add siblings to this block
- `build.py:759,764` — current-year + prior-year URL pair for batter
  arsenal; units 1 and 3 add parallel URL pairs

**Matchup xwOBA math** (the reference for unit 2):

- `sections/matchup.py _expected_xwoba` — sums `usage/100 * xwoba` over
  pitches; bug is that missing usage contributes 0, not league average
- `LEAGUE_AVG_XWOBA = 0.310` is already defined at the top of the file
- `tests/test_matchup_section.py TestExpectedXwoba` — existing tests unit
  2 extends

**Deploy flow** (reference for unit 4):

- `deploy.py` — `urllib` PUTs to GitHub Contents API, prints "live →" at
  the end regardless of Pages build status
- GitHub Pages build status is reachable via
  `/repos/{owner}/{repo}/pages/builds/latest` — JSON with `status` field
  (`building` | `built` | `errored`)
- Env var `GITHUB_TOKEN` already loaded in deploy.py — same token has
  `pages:read` permission

**Evening watcher** (reference for unit 5):

- `evening.py:26` — hardcoded `CUBS_ID = 112`
- `evening.py:29` — `POLL_INTERVAL = 300` (5-min poll)
- `evening.py:31` — 6-hour max runtime
- Plan `docs/plans/2026-04-08-002-feat-morning-lineup-enhancements-plan.md`
  proposed a systemd timer but never landed one

**Live refresh hook** (reference for unit 6):

- `cubs/live.js` (and 29 symlinked copies, e.g. `orioles/live.js`,
  `red-sox/live.js`, etc. per grep) — existing client polls MLB for game
  state. Unit 6 adds a lineup-watch path alongside existing game-watch.
- `sections/scouting.py:86` — the conditional render pattern this refresh
  should target (scouting block has a stable DOM id)
- `sections/matchup.py render` — same shape; rendered node is
  `<section id="matchup">`

**Farm rendering** (reference for units 7–10):

- `build.py:294-306` — per-affiliate yesterday's game fetch; 4 levels
  (sport_id 11/12/13/14) already iterated per team
- `build.py:308-315` — where static `prospects.json` is loaded today; unit
  7 replaces the load source
- `build.py:331-341` — transactions fetch
- `build.py:333-337` — the `skip_types = {"SFA"}` + "minor league" filter
  unit 9 relaxes
- `sections/farm.py:18-193` — existing renderer; units 7–10 extend

**Dead data locations** (unit 10):

- `brl_percent` on pitcher leaderboard — fetched at
  `build.py:752-754`, never read in `sections/headlines.py`
- `xwoba_allowed` on pitcher arsenal — populated in
  `_build_savant_arsenal` (shipped yesterday), never surfaced in
  `sections/matchup.py`

### Institutional Learnings

- **Prior-year fallback is the pattern.** Already solved on the batter
  side yesterday via `_merge_batter_arsenal`. Every new fallback in this
  plan should mirror that function's shape exactly: same naming, same
  precedence (current-year wins per key), same schema bump discipline.
- **Cache invalidation via schema bump works.** Bumping `_SAVANT_SCHEMA`
  at `build.py:518` forces every team to refetch — proven twice this week.
- **"Rebuild all 30 teams" is a memory-enforced rule.** Any change that
  touches shared build logic must be followed by rebuilding every team
  before deploy, not just Cubs. This applies to every unit in this plan.
- **Silent GitHub Pages failures have bitten us.** Yesterday: 4 failed
  builds in a row, deploy.py reported success, JB had to diff HTML sizes
  manually to find the gap. Unit 4 exists to stop this class of bug.

### External References

- GitHub Pages Builds API:
  `GET /repos/{owner}/{repo}/pages/builds/latest` — returns `status`
  (`building` | `built` | `errored`) and `created_at`. Polling is the
  standard pattern since GitHub Pages doesn't push webhooks for static
  sites on default config.
- systemd `.timer` unit pattern for user-level daemons lives in
  `~/.config/systemd/user/` and is enabled with `systemctl --user enable`.

## Key Technical Decisions

- **Prior-year fallback, not multi-year.** Mirror the batter-side choice:
  current-year wins, prior-year fills gaps. No rolling 2-year average,
  no weighting — keeps the merge simple and already-proven.
- **Single schema bump per plan landing, not per unit.** All three Savant
  fallback units (1, 3) land in one commit batch, then `_SAVANT_SCHEMA`
  bumps 4 → 5 once. Avoids thrashing the cache mid-session.
- **Deploy verification is blocking, not advisory.** Unit 4's Pages check
  must exit non-zero when the build errors — advisory warnings are what
  caused yesterday's silent failures to slip through.
- **Evening watcher: one process per team, not one process per league.**
  Simpler process model, each timer-fired invocation picks its own team
  from config. Scales linearly but that's fine at 30 teams.
- **Client-side refresh uses polling, not SSE.** `live.js` already polls
  the MLB API every 20–30s for game state; unit 6 piggybacks on the
  existing poll rather than opening a second channel.
- **Prospects source: MLB Pipeline top-100 + MLB API `/teams/{id}/roster`
  for level metadata.** MLB Pipeline has a public top-100 JSON endpoint;
  affiliate level + position come from the roster endpoint we already hit.
  No scraping needed.
- **Affiliate standings: one fetch per level per division, cached daily.**
  4 levels × 3–4 divisions per level = ~16 fetches per day total. Cache
  same as Savant leaderboards (daily date-keyed JSON).
- **MiLB transactions: relax the filter, don't rewrite.** The existing
  filter at `build.py:333-337` is a 2-line check; unit 9 just removes the
  "minor league" substring match and keeps the SFA exclusion for pure
  free-agent signings.

## Open Questions

### Resolved During Planning

- **Q: Should prior-year Savant batter/pitcher leaderboards fetch the
  same columns as current-year?**
  Yes — same column set (`xwoba`, `xera`, `whiff_percent`, `brl_percent`).
  Merging is per-pid, current-year-wins, so column parity is required.
- **Q: Does the evening watcher need a separate config file to know which
  teams to watch?**
  No — it iterates `teams/*.json` the same way `build.py --landing` does.
  No new config.
- **Q: Should dead data (`brl_percent` pitcher, `xwoba_allowed`) be
  rendered or removed?**
  Render both. `brl_percent` pitcher slots naturally into the existing
  pitcher leaders panel; `xwoba_allowed` is high-value editorial color
  for matchup arsenal cards ("Skenes SL: .209 xwOBA-allowed").
- **Q: Does the lineup-post refresh trigger need server-side state, or
  can it be pure client?**
  Pure client. MLB API exposes lineup status in the live feed; `live.js`
  already polls it. Unit 6 just adds a branch that fetches the fresh
  scouting/matchup HTML fragments when lineup flips from empty to set.

### Deferred to Implementation

- **Exact MLB Pipeline top-100 endpoint path.** Needs a quick live probe
  during unit 7; the public endpoint URL is documented but version-suffixed.
- **Whether `deploy.py` should retry a failed Pages build or just fail.**
  Start with fail-loud, add retry only if unit 4 tests show transient
  errors are common.
- **Which exact DOM ids the client fragment swap targets for R6.** Depends
  on what the server-rendered markup looks like after units 1–3 land.
- **Whether systemd timer should run on `OnBootSec` or `OnCalendar`.**
  Both work; decision during unit 5.

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for
> review, not implementation specification. The implementing agent should
> treat it as context, not code to reproduce.*

Dependency graph (which units unblock which):

```
[1] Pitcher arsenal prior-year ──┐
[2] _expected_xwoba safety net ──┼──► [3] Leaderboard prior-year fallback
                                 │           (single schema bump)
                                 │
[4] Deploy Pages verification ───┴──► Ship gate — nothing else deploys
                                      confidently until unit 4 is live

[5] Evening watcher all-teams  ──► [6] Client lineup-refresh trigger

[7] Prospects auto-refresh  ──► [8] Affiliate standings + MiLB slate
                                     ──► [9] MiLB transactions unfilter

[10] Dead-data render/remove (independent, lands last as polish)
```

Prior-year fallback pattern (units 1, 3 mirror this):

```
fetch_current  ──┐
                 ├──► _merge_<thing>(current, prior) ──► savant["<thing>"]
fetch_prior    ──┘                                         (current wins per key)
```

## Implementation Units

### Unit 1: Pitcher arsenal prior-year fallback + schema bump prep

**Goal:** Close the Cole Ragans bug class. Fetch 2025 pitcher arsenal
alongside 2026 and merge with current-year precedence.

**Requirements:** R1

**Dependencies:** None

**Files:**
- Modify: `build.py` (add `_merge_pitcher_arsenal` near line 573, add
  `arsenal_stats_prev` URL in `fetch_savant_leaderboards` around line
  756, add prior fetch and merge in `_build_savant_arsenal`)
- Test: `tests/test_savant_fetch.py` (extend existing arsenal tests;
  pattern already in place for batter side)

**Approach:**
- Copy `_merge_batter_arsenal` at `build.py:573` and adapt for the
  pitcher-arsenal shape (keys are pid → list of pitch dicts, not pid →
  pitch-type-keyed dict like batters).
- Add `arsenal_stats_prev` entry to the URLs dict in
  `fetch_savant_leaderboards` parallel to `batter_arsenal_prev` at
  `build.py:764`.
- In `_build_savant_arsenal`, after building current-year output, load
  prior-year raw data, call `_merge_pitcher_arsenal`, store result.
- Do **not** bump `_SAVANT_SCHEMA` in this unit — leave that to unit 3
  so all fallback changes share a single cache invalidation.

**Patterns to follow:**
- `build.py:573 _merge_batter_arsenal` — exact shape for the merge helper
- `build.py:759-764` — URL pair pattern
- `build.py:789` — merge call site pattern

**Test scenarios:**
- Happy path: pitcher has 2026 data for FF+SL+CH, 2025 data for all four,
  merged arsenal has 4 pitches with 2026 values winning where present.
- Edge case: pitcher has 2026 data for FF only (51% usage), 2025 data for
  FF/SL/CH/SI — merged arsenal has all 4 pitches, FF uses 2026 values,
  SL/CH/SI use 2025.
- Edge case: pitcher has zero 2026 data, 2025 has full arsenal — merged
  arsenal equals 2025 arsenal exactly.
- Edge case: both empty — merged is empty dict, no crash.
- Error path: prior-year fetch 500s — function returns current-year-only
  result, logs warning, no exception propagates.

**Verification:**
- Ragans (pid 677957 per Savant) produces a 4+ pitch arsenal after unit
  1 lands, not the single-FF arsenal seen yesterday.
- Existing matchup section tests still pass.

### Unit 2: `_expected_xwoba` missing-usage safety net

**Goal:** Even with unit 1 landed, some pitchers will still have
incomplete arsenals (summing to <100%). Treat the missing slice as
league-average so expected xwOBA isn't artificially low.

**Requirements:** R2

**Dependencies:** None (can land parallel to unit 1)

**Files:**
- Modify: `sections/matchup.py` (`_expected_xwoba` function)
- Test: `tests/test_matchup_section.py` (extend `TestExpectedXwoba`)

**Approach:**
- After the existing loop, compute
  `total_usage = sum(p.usage or 0 for p in arsenal) / 100.0`.
- If `total_usage < 1.0`, add `(1.0 - total_usage) * LEAGUE_AVG_XWOBA` to
  the accumulator. `LEAGUE_AVG_XWOBA = 0.310` already defined at the top
  of the file.
- Guard against arsenals that sum to >100% (edge case from CSV rounding) —
  clamp the missing slice to 0 so we never subtract.

**Execution note:** Test-first. The bug reproduces cleanly in a unit test
(Ragans-like arsenal with only FF at 51%), so the failing test should
land before the fix.

**Patterns to follow:**
- Existing `TestExpectedXwoba` class in
  `tests/test_matchup_section.py:59` — five scenarios already cover the
  happy paths; unit 2 adds two more.

**Test scenarios:**
- Happy path (regression): full arsenal summing to 100% — result
  unchanged from pre-unit-2 behavior.
- Happy path (the fix): arsenal with only FF at 51% usage, FF xwoba
  0.280 → result is `0.51 * 0.280 + 0.49 * 0.310 = 0.2947`, not `0.1428`.
- Edge case: arsenal with FF at 51%, batter has no FF row → result uses
  league-avg for both the FF slice and the missing slice = 0.310.
- Edge case: arsenal summing to 101% (rounding) → missing slice clamps
  to 0, result ≈ full weighted sum.

**Verification:**
- Tigers-style lineup (yesterday's bug report) no longer shows every
  hitter with "safe: FF ●●●● D" against a thin Ragans arsenal.
- Existing `TestExpectedXwoba` tests still pass.

### Unit 3: Savant batter + pitcher leaderboards prior-year fallback + schema bump

**Goal:** Extend the fallback pattern to `savant["batter"]` and
`savant["pitcher"]` leaderboards so team leaders (headlines section)
don't go empty in April.

**Requirements:** R3

**Dependencies:** Unit 1 (shares the `_SAVANT_SCHEMA` bump)

**Files:**
- Modify: `build.py` (add `batter_prev` + `pitcher_prev` URLs around
  `build.py:748-754`, add two merge helpers near `_merge_batter_arsenal`,
  call them in the `savant` dict assembly)
- Modify: `build.py:518` bump `_SAVANT_SCHEMA` 4 → 5
- Test: `tests/test_savant_fetch.py` (add two new test classes mirroring
  batter arsenal tests)

**Approach:**
- Batter leaderboard merge: pid → dict of stat fields. Current-year wins
  per pid; prior-year fills missing pids entirely.
- Pitcher leaderboard merge: same shape.
- Bump `_SAVANT_SCHEMA` to 5 **once** — this is the only unit that bumps
  it. The bump invalidates yesterday's cache so the next build fetches
  fresh with the new fallback structure.

**Patterns to follow:**
- `build.py:573 _merge_batter_arsenal` — merge helper shape
- `build.py:759-764` — URL pair pattern (use `&year={season-1}`)

**Test scenarios:**
- Happy path: batter has 2026 xwoba .350 and 2025 xwoba .320 — merged
  value is .350.
- Edge case: batter has 2025 data only (thin April sample excluded
  them from 2026 leaderboard) — merged value is .320.
- Edge case: batter has 2026 data only — merged value is .350, no
  crash on missing prior.
- Schema bump: cache files from schema 4 are discarded and refetched.

**Verification:**
- `sections/headlines.py` team leaders panel populates in April even
  for teams whose hitters are below 2026 min-sample thresholds.
- Cache schema bump forces one full refetch, then stabilizes.

### Unit 4: Deploy Pages build verification

**Goal:** `deploy.py` polls GitHub Pages builds API and exits non-zero
if the latest build errored. Silent failures become loud.

**Requirements:** R4

**Dependencies:** None (can land independently, but should ship before
units 5–9 to give their rebuilds a real success signal)

**Files:**
- Modify: `deploy.py` (add post-PUT Pages-build poll loop before the
  final "live →" print)
- Test: `tests/test_deploy_pages_check.py` (new file, stdlib-only,
  stubs `urllib.request.urlopen`)

**Approach:**
- After all Contents-API PUTs complete, GET
  `/repos/brawley1422-alt/morning-lineup/pages/builds/latest` with the
  existing `GITHUB_TOKEN` header.
- Parse `status` field: `built` → success, `errored`/`failed` →
  sys.exit(2), `building`/`queued` → poll again after 15s, max 5 polls
  (~75s ceiling).
- On timeout: print a warning but do not exit non-zero (the build may
  still succeed; we just can't confirm).
- On `errored`: print the latest build SHA + error URL so JB can open
  it directly.

**Patterns to follow:**
- `deploy.py` existing `urllib` + `Authorization: token {GITHUB_TOKEN}`
  pattern

**Test scenarios:**
- Happy path: first poll returns `built` → function returns 0.
- Edge case: first two polls return `building`, third returns `built`
  → function returns 0 after polling.
- Error path: first poll returns `errored` → function sys.exits with
  code 2, prints build SHA.
- Error path: all 5 polls return `building` → function prints timeout
  warning, returns 0 (non-blocking).
- Error path: GET returns 500 → function prints warning, returns 0.

**Verification:**
- Manually trigger a known-broken build (e.g., invalid Jekyll config in
  a test branch) and confirm deploy.py exits non-zero.
- Manually trigger a known-good build and confirm deploy.py reports
  success within ~30s.

### Unit 5: Evening watcher all-teams + systemd timer

**Goal:** `evening.py` rebuilds every team that had a game tonight, not
just Cubs. Install a systemd user timer so it starts unattended.

**Requirements:** R5

**Dependencies:** Unit 4 (so evening rebuilds also get deploy verification)

**Files:**
- Modify: `evening.py` (remove hardcoded `CUBS_ID`, iterate `teams/*.json`
  and pick any team whose game today has status `Final`)
- Create: `ops/morning-lineup-evening.service` (systemd user unit)
- Create: `ops/morning-lineup-evening.timer` (systemd user timer, fires
  at 18:00 local)
- Create: `ops/README.md` (install instructions: `systemctl --user enable`)
- Test: `tests/test_evening_watcher.py` (new, stubs API fetch, asserts
  multi-team iteration and skip logic)

**Approach:**
- Replace `CUBS_ID = 112` at `evening.py:26` with a loop over
  `teams/*.json` filenames.
- For each team, check today's schedule. If game exists and is `Final`,
  run `python3 build.py --team <slug>` + `python3 deploy.py`.
- Keep existing 5-minute poll interval and 6-hour max runtime.
- Systemd unit runs `evening.py` once per day at 18:00 local time; the
  script self-exits when all watched games reach Final or 6h elapse.

**Patterns to follow:**
- `evening.py` existing poll + final-detect loop
- Plan `docs/plans/2026-04-08-002-feat-morning-lineup-enhancements-plan.md`
  has the proposed systemd shape

**Test scenarios:**
- Happy path: 3 teams have games, all 3 reach Final → all 3 rebuilt.
- Edge case: 0 teams have games tonight → watcher exits immediately
  with clean log line.
- Edge case: 5 teams have games, 3 reach Final within window, 2 don't
  → 3 rebuilt, 2 skipped with warning.
- Error path: one team rebuild fails → other teams still process,
  failure logged with team slug.

**Verification:**
- On a live evening, multiple non-Cubs teams get rebuilt automatically.
- `systemctl --user status morning-lineup-evening.timer` shows enabled.

### Unit 6: Client-side lineup-post refresh trigger

**Goal:** When MLB posts a starting lineup after the morning build, the
page re-fetches the rendered scouting + matchup sections so the reader
sees real lineup data without a manual refresh.

**Requirements:** R6

**Dependencies:** Units 1–3 (so the refreshed HTML has the new fallback
data available)

**Files:**
- Modify: `live.js` (root file; 29 symlinked copies per team pick up
  the change automatically — confirmed via grep showing identical code
  at `orioles/live.js:4`, `red-sox/live.js:4`, etc.)
- Test: `tests/test_live_js_lineup_refresh.html` (new, headless puppet
  test stubbing MLB API response)

**Approach:**
- Existing `live.js` polls MLB live feed every ~30s for game state.
- Add a side channel: on each poll, check `liveData.boxscore.battingOrder`
  for the current team. If it was empty on previous poll and is now
  populated (len ≥ 9), fire a fragment-refresh.
- Fragment refresh: `fetch('./index.html')`, parse, swap
  `#scouting` and `#matchup` inner HTML.
- Store the lineup-posted flag in `sessionStorage` so a page reload
  during the same session doesn't re-trigger.

**Patterns to follow:**
- Existing `live.js` poll loop and DOM update patterns
- Existing `sessionStorage` usage in `live.js` for game-state memoization

**Test scenarios:**
- Happy path: first poll shows empty battingOrder, second poll shows
  9 ids → fragment fetched and scouting + matchup DOM nodes swapped.
- Edge case: first poll already has battingOrder populated → no fetch
  fires (page was built post-lineup).
- Edge case: lineup shows 8 ids (partial post) → no fire until it hits 9.
- Error path: fragment fetch 404s → existing DOM left intact, error
  logged to console, no user-visible break.

**Verification:**
- Load a pre-lineup team page, wait for lineup to post in the MLB feed,
  confirm scouting + matchup sections update without a full reload.

### Unit 7: Prospects auto-refresh from MLB Pipeline

**Goal:** Replace static `teams/{slug}/prospects.json` hand-edits with a
daily fetch of MLB Pipeline top-100 + per-team top-30.

**Requirements:** R7

**Dependencies:** Unit 4 (ships before to avoid silent deploy breakage)

**Files:**
- Modify: `build.py` (add `fetch_prospects(team_id)` near existing
  affiliate fetches around `build.py:294-315`)
- Modify: `build.py:308-315` (replace static JSON load with fetch call;
  keep JSON as fallback-on-network-failure)
- Test: `tests/test_prospects_fetch.py` (new)

**Approach:**
- MLB Pipeline exposes public top-100 and per-team prospect JSON
  (exact endpoint URL confirmed during unit execution — noted as
  deferred question).
- Fetch once per build, cache to
  `data/cache/prospects/{team_id}-{date}.json` (mirror existing player
  cache pattern at `data/cache/players/`).
- On network failure, fall back to existing static
  `teams/{slug}/prospects.json` with a warning log.
- Static JSON files stay in the repo as the last-known-good fallback;
  they're just no longer the primary source.

**Patterns to follow:**
- `build.py:1704-1716` player cache pattern (daily date-keyed JSON)
- `build.py:294-306` per-team affiliate fetch pattern

**Test scenarios:**
- Happy path: fetch returns 30 prospects with rank, name, position,
  level → parsed into same shape as current `prospects.json`.
- Edge case: fetch returns empty list → fall back to static JSON.
- Error path: fetch 500s → fall back to static JSON, log warning.
- Error path: cache hit today → no refetch, uses cached data.

**Verification:**
- After a build, cache file exists at
  `data/cache/prospects/112-2026-04-14.json`.
- `sections/farm.py` renders prospect list unchanged in shape.

### Unit 8: Affiliate standings + tonight's MiLB slate

**Goal:** Fetch per-level standings and tonight's affiliate games, render
in `sections/farm.py`.

**Requirements:** R8

**Dependencies:** None (farm section already loads affiliate data)

**Files:**
- Modify: `build.py` (add affiliate standings fetch — `/standings`
  endpoint with sport_id 11/12/13/14; add tonight's affiliate schedule
  loop parallel to yesterday's game fetch at `build.py:294-306`)
- Modify: `sections/farm.py` (render standings strip + tonight block;
  reuse existing `.pc-card` and `.mr-foot` CSS)
- Test: `tests/test_farm_section.py` (extend existing farm tests)

**Approach:**
- Standings cached daily same as MLB standings at `build.py:123`.
- Tonight's MiLB slate fetched from `/schedule` with each affiliate's
  team_id and today's date.
- Render order in farm section: yesterday's game → tonight's game →
  standings line for that level.

**Patterns to follow:**
- `build.py:123` MLB standings fetch shape
- `build.py:135-145` next_games fetch shape
- `sections/farm.py` existing yesterday-render pattern

**Test scenarios:**
- Happy path: 4 affiliates, all have standings and tonight's game →
  farm section shows 4 level blocks each with yesterday/tonight/standings.
- Edge case: AAA affiliate has an off-day tonight → shows "off day"
  placeholder for tonight block, standings still renders.
- Edge case: standings fetch empty for a level → block renders without
  standings line, no crash.
- Error path: affiliate team_id missing from config → skip that level
  with warning.

**Verification:**
- Load a team page, farm section shows standings + tonight for each
  affiliate.

### Unit 9: Unfilter MiLB transactions

**Goal:** Call-ups, demotions, and minor-league signings surface in the
pressbox section instead of being dropped.

**Requirements:** R9

**Dependencies:** None

**Files:**
- Modify: `build.py:333-337` (relax `skip_types` filter)
- Modify: `sections/pressbox.py` (add MiLB-specific rendering if present;
  otherwise the existing transaction row handles it)
- Test: `tests/test_pressbox_milb.py` (new)

**Approach:**
- Remove the `"minor league" in desc.lower()` substring check at
  `build.py:337`.
- Keep the `SFA` exclusion — pure minor-league free-agent signings are
  low-signal noise.
- In pressbox, tag MiLB moves with a subtle marker so they're visually
  distinguishable from MLB moves.

**Patterns to follow:**
- `build.py:331-341` existing transactions fetch
- `sections/pressbox.py` existing row render

**Test scenarios:**
- Happy path: call-up from AAA → appears in pressbox tagged as MiLB.
- Edge case: SFA signing → still filtered out.
- Edge case: MLB trade → still appears as MLB-tagged row.
- Happy path: empty transaction list → section renders "no moves"
  placeholder unchanged.

**Verification:**
- A team with a known recent call-up (confirmable via
  baseball-reference) shows it in pressbox.

### Unit 10: Dead data render + cleanup

**Goal:** Render `brl_percent` on pitcher leaderboard and `xwoba_allowed`
on pitcher arsenal. Either use the data or delete the fetches.

**Requirements:** R11

**Dependencies:** Units 1–3 (clean slate on Savant pipeline first)

**Files:**
- Modify: `sections/headlines.py` (add `brl_percent` to pitcher leaders
  panel, parallel to the existing batter brl_percent render around
  `sections/headlines.py:447-454`)
- Modify: `sections/matchup.py` (show `xwoba_allowed` in arsenal pitch
  cards — small inline stat like "SL .209 xwOBA")
- Modify: `style.css` (minor — no new classes, reuse `.mr-pc` block)
- Test: extend `tests/test_headlines_section.py` and
  `tests/test_matchup_section.py`

**Approach:**
- Pitcher `brl_percent`: slot into the existing leaders-panel card shape
  as a secondary stat line. Low risk, additive only.
- `xwoba_allowed`: already populated in the arsenal dict per yesterday's
  work. Render inside the pitch card alongside velo/spin/whiff.
- No feature-flag, no rollout — additive rendering.

**Patterns to follow:**
- `sections/headlines.py:447-454` batter brl_percent render
- `sections/matchup.py` arsenal-card render (post-unit-1 version)

**Test scenarios:**
- Happy path: pitcher leader has `brl_percent = 6.2` → renders as
  "Brl 6.2%" below xERA.
- Happy path: Skenes arsenal has SL `xwoba_allowed = 0.209` → arsenal
  card renders ".209 xwOBA" inline.
- Edge case: missing `brl_percent` field → cell shows em-dash, no crash.
- Edge case: `xwoba_allowed` is None → field omitted from card, no
  "None" string leakage.

**Verification:**
- Both stats visible on a rendered team page.
- No regressions in existing headlines or matchup tests.

## System-Wide Impact

- **Interaction graph:** Units 1–3 touch the Savant cache layer that
  every section downstream of `build.py:404` reads from. A miscalculated
  merge would propagate to headlines, scouting, matchup, and player
  cards. Unit 4 is the gate that catches any rendering break before it
  reaches users.
- **Error propagation:** Savant fetch failures must fall back to
  current-year-only (units 1, 3) or static-JSON fallback (unit 7), never
  throw. Deploy failures (unit 4) now exit non-zero — the morning cron
  wrapper will surface this in its mail/log.
- **State lifecycle risks:** `_SAVANT_SCHEMA` bump in unit 3 invalidates
  yesterday's cache on first build after landing. Expect one slow build
  the day unit 3 ships. No data loss — the cache is fully regenerable.
- **API surface parity:** 30 symlinked `live.js` copies all pick up unit
  6's change from the root file, confirmed via grep showing identical
  content across `orioles/live.js`, `red-sox/live.js`, `blue-jays/live.js`,
  etc. No per-team patching needed.
- **Integration coverage:** Unit 6 is the only unit that spans server-side
  render + client-side refresh. It needs one integration test that
  renders a page with empty lineup, mocks the MLB API to flip lineup
  state, and asserts the DOM updates.
- **Unchanged invariants:** Cache file format, build CLI flags, section
  render ordering, client poll interval, and Contents API PUT flow all
  stay unchanged. The plan is purely additive except for the `skip_types`
  relaxation in unit 9 and the schema bump in unit 3.

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Prior-year merge miswrites current-year data (unit 1, 3) | Mirror `_merge_batter_arsenal` exactly; that helper has been in prod for 24h without issue. Test scenarios explicitly cover precedence. |
| Schema bump causes slow first-day build (unit 3) | Expected and acceptable. One-time cost on the morning of landing. |
| Deploy Pages check times out on legitimately slow builds (unit 4) | Cap at 75s, fall back to non-blocking warning. Adjust threshold if false positives appear. |
| MLB Pipeline endpoint changes format (unit 7) | Keep static `prospects.json` as fallback. Log warnings on parse failure; JB reviews weekly. |
| Evening watcher runs 30 rebuilds in parallel (unit 5) | Rebuilds run sequentially in the existing loop, not parallel. 30 teams × ~15s each = 7.5min worst case, well within 6h window. |
| Client fragment swap breaks in-flight JS state (unit 6) | Scoped to `#scouting` and `#matchup` only. Player cards, live score, and pulse are untouched. |
| MiLB transaction noise (unit 9) | Only the "minor league" substring filter is removed. SFA exclusion stays. If noise is still too high, add a curated level filter. |

## Documentation / Operational Notes

- **Ops folder:** Unit 5 creates `ops/` for systemd units. This is new
  — add a README.md in that folder with install instructions so JB can
  reinstall on a fresh machine.
- **Schema bump note:** Add a line to the top of `build.py` near
  `_SAVANT_SCHEMA = 5` noting when it was last bumped and why. Helps
  future debugging.
- **Deploy verification:** Once unit 4 lands, update any deploy runbook
  notes to reflect that a non-zero deploy.py exit means the Pages build
  failed, not the PUTs.
- **Rebuild all teams:** Every unit in this plan that touches
  `build.py` or `sections/*.py` must be followed by a full 30-team
  rebuild + deploy before closing the task (per the JB memory rule).

## Sources & References

- **MLB data audit** (2026-04-14 Explore agent) — identified the Cole
  Ragans single-pitch arsenal bug class, the dead `brl_percent` and
  `xwoba_allowed` fields, and the missing prior-year fallback on Savant
  batter/pitcher leaderboards. All file:line citations in this plan's
  "Context & Research" section trace back to that audit's findings.
- **Farm audit** (2026-04-14 Explore agent) — identified static
  `prospects.json` as a manual hand-edit bottleneck, the affiliate
  yesterday-only fetch, the MiLB transaction filter at build.py:333-337,
  and the absence of MiLB standings / tonight's slate. Findings drove
  units 7–9.
- `docs/plans/2026-04-14-002-feat-matchup-read-plan.md` — yesterday's
  matchup read plan; context for unit 2's `_expected_xwoba` fix.
- `docs/plans/2026-04-08-002-feat-morning-lineup-enhancements-plan.md` —
  earlier plan that proposed a systemd timer for evening.py but never
  landed; unit 5 closes that gap.
- Cache pattern: `build.py:518`, `build.py:573`, `build.py:705-795`,
  `build.py:1704-1716`.
- GitHub Pages Builds API:
  `GET /repos/{owner}/{repo}/pages/builds/latest`.
