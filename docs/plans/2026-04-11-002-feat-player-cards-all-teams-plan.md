---
title: "feat: Scale player cards to all 30 teams (deeplink-first)"
type: feat
status: active
date: 2026-04-11
origin: docs/brainstorms/2026-04-11-player-cards-mvp-requirements.md
---

# feat: Scale player cards to all 30 teams (deeplink-first)

## Overview

Extend the Cubs-only player card MVP so every active MLB player on all 30 teams has a URL-addressable card. The card template, web component, and data shape are already shipped for Cubs — this is a data-pipeline + gating change, not a design change. Primary goal: `/<team-slug>/#p/<pid>` opens a working card for any active player. In-page clickable linking from lineup rows is explicitly deferred to a later iteration.

## Problem Frame

Based on findings from the Cubs MVP (see origin: `docs/brainstorms/2026-04-11-player-cards-mvp-requirements.md`, and the prior plan `docs/plans/2026-04-11-001-feat-player-cards-cubs-mvp-plan.md`), the card template, JSON schema, and component are production-ready for one team. The MVP intentionally gated the component at `_team_slug == 'cubs'` in `build.py:818` and at `team_id == 112` in `sections/headline.py` to keep blast radius small. With that foundation proven, the next compounding move is to lift those gates and fan the data pipeline across all 30 teams so JB can share a URL for any player on any team.

The organizing constraint from JB: **URLs first, in-page linking later.** This means the card must open purely from a hash route on any team page — it does not depend on a clickable name existing anywhere on that page.

## Requirements Trace

- **R1.** Every active player on all 30 MLB teams has a stable URL that opens their card (e.g., `/<team-slug>/#p/<mlb_person_id>`). Derived from JB's stated primary goal.
- **R2.** The `<player-card>` component loads on every team page, not just Cubs. Extends MVP requirement R6 from the origin doc (Cubs-only component shipping).
- **R3.** Per-team `players-<slug>.json` artifacts are emitted by `build.py` for all 30 teams following the existing shape at `data/players-cubs.json`. Extends MVP R4 (Cubs-only JSON artifact).
- **R4.** Hash-deeplink routing (`#p/<pid>`) resolves against the hosting page's own team JSON — no cross-team fetch required in Phase 1. Derived from "deeplink-first" scope.
- **R5.** The lineup-name `<player-card>` wrap in `sections/headline.py` (MVP R10) stays gated off non-Cubs pages until JB decides on a link placement strategy. Secondary UX concern, explicitly deferred.
- **R6.** Build-time cost must remain acceptable for a daily cron build — target under ~8 minutes wall-clock for a full 30-team run, with graceful degradation on API failures. Derived from operational context (daily 08:00 UTC trigger, from `project_morning_lineup.md` memory).
- **R7.** No regressions on existing 30-team snapshots or the Cubs snapshot — golden tests in `tests/` must continue to pass. Extends MVP R11.
- **R8.** MLB Stats API rate-limit friendliness — no unbounded parallelism; bounded concurrency with retry/backoff on 429/5xx. New requirement surfaced by scale increase.

## Scope Boundaries

- **In scope:** per-team JSON emission, dropping the `_team_slug == 'cubs'` script-tag gate, `player-card.js` reading the page's team slug to load the right JSON, hash-deeplink routing already present in `cubs/player-card.js`, slug→team_id mapping via existing `teams/<slug>.json` configs, bounded HTTP concurrency + retry, per-player record caching keyed by `(pid, season)` to avoid re-fetching on every build.
- **Out of scope (deferred):** wrapping non-Cubs lineup/SP names in `<player-card>` tags (the "how to link from the page" question JB said he'd decide later), cross-team search index, Baseball Savant / Statcast integration, a global "all players" JSON, PWA offline caching of card data, minor-league / prospect cards.

## Context & Research

### Relevant Code and Patterns

- `build.py:46` — `_team_slug` is already the per-team axis the builder runs on; the Cubs-only branch at `build.py:1099` (`if _team_slug == "cubs":`) is the precedent for "do X for this team only" and is the block this plan generalizes.
- `build.py:890` — `_fetch_player_record(pid, role, season)` is the single-player hydrator (people/season/yearByYear/gameLog). It already works for any `pid` and doesn't hardcode Cubs — reusable as-is.
- `build.py:983` — `load_player_cards(lineup, sp_pid, season)` composes the lineup + SP slice into a dict. Reusable, but needs a broader-coverage sibling that hydrates the full active roster, not just today's 9+1.
- `build.py:251-271` — the existing roster fetch pattern (`/teams/{TEAM_ID}/roster` with `rosterType="active"` and `"40Man"`) is the input source for "all active players on a team."
- `build.py:818` — the f-string conditional that currently gates `player-card.js` to Cubs only; this is the exact line to generalize.
- `sections/headline.py` (Cubs gate at `team_id == 112` in `_lu_slot` and `_pitcher_name_html`) — stays gated per R5.
- `cubs/player-card.js` — self-contained IIFE. Currently loads `../data/players-cubs.json` with a hardcoded path; needs to read the team slug from the page (e.g., from a `data-team` attribute or URL path segment). Hash routing at `openFromHash()` is already implemented and team-agnostic.
- `teams/<slug>.json` — each team config carries `"id": <team_id>`. This is the canonical slug→team_id map; no new config file needed.
- `tests/` — golden snapshot tests via `--fixture` flag. Snapshots need re-blessing for all 30 teams after the script tag is un-gated (each team page gains one line).
- `sw.js` + `cubs/sw.js` — service worker cache constant. A schema change to paths or the player-card.js location requires a cache bump (precedent: `"lineup-v6"` → `"lineup-v7"` from the MVP).

### Institutional Learnings

- Analyst found that the Cubs MVP pre-game empty-lineup fallback (top-9 hitters by games played from the active roster) was necessary because MLB doesn't post batting orders 11+ hours pre-first-pitch. For the all-teams case this is less relevant because the new work hydrates the **full** active roster, not just today's starters — the roster endpoint is always populated.
- From `feedback_rebuild_all_teams.md`: when changing shared assets, rebuild all 30 teams, not just Cubs. This plan explicitly touches shared behavior, so the verification step must run the full 30-team build.
- From the MVP's snapshot-scope-leak incident: the Yankees snapshot caught an accidental `<player-card>` wrap on a Yankees pitcher because the `_pitcher_name_html` change was missing a `team_id` gate. Snapshot tests are the load-bearing safety net for scope decisions — keep them green as the gating moves around.

### External References

- MLB Stats API `/teams/{id}/roster?rosterType=active` returns ~26–28 players per team. ~26 × 30 = ~780 active players. With `_fetch_player_record` making ~3 calls per player (people, season stats, gameLog), that's ~2,340 requests per full build. At 150ms/req serial, that's ~6 minutes. With concurrency of 4, ~90 seconds. The MLB Stats API is unauthed and tolerant of small-fleet polling, but not documented to have a specific rate limit — conservative concurrency is warranted.

## Key Technical Decisions

- **Per-team JSON, not a global index.** Rationale: keeps the HTTP payload small (each team page only needs its ~26 players), preserves the existing artifact shape, allows a team's card data to be regenerated independently on a Cubs-triggered build, and avoids a new global artifact to cache-bust. Deferring a cross-team index means cross-team deeplinks (loading a non-Cubs player's card from the Cubs page) is out of scope for Phase 1 — consistent with JB's stated priority.
- **Hydrate the full active roster, not just today's lineup.** Rationale: the primary goal is "every player has a URL." Limiting to today's 9+1 would leave 75% of each team un-addressable. Active roster (~26) is the right coverage tier for Phase 1; 40-man and IL stay deferred.
- **Bounded concurrency via a small worker pool (e.g., concurrency=4), not full async.** Rationale: `build.py` is stdlib-only per project convention; adding `aiohttp` would break that. `concurrent.futures.ThreadPoolExecutor` is stdlib and sufficient for IO-bound HTTP work at this scale.
- **Per-player disk cache keyed by `(pid, season, YYYY-MM-DD)`** under `data/cache/players/`. Rationale: a player's season-to-date stats change once per day at most; re-fetching on every build wastes time and API calls. A date-keyed cache auto-invalidates daily without manual bookkeeping.
- **`player-card.js` reads the team slug from a `data-team` attribute on `<body>`** (or equivalent DOM hook), rather than parsing `location.pathname`. Rationale: explicit is better than implicit, survives URL restructuring, and the builder already knows the slug at render time.
- **Keep `sections/headline.py` Cubs-gated for now.** Rationale: matches R5 and JB's explicit "find a better way to link them on the pages after." Un-gating this later is a one-line change — no need to pre-commit to a linking strategy.
- **Cache-bump the service worker** to `lineup-v8` so every device picks up the new `player-card.js` and the new per-team JSON paths on next load.

## Open Questions

### Resolved During Planning

- **Per-team JSON vs global index?** → Per-team (see decision above).
- **Which page hosts non-Cubs card URLs?** → Each team's own page (`/<slug>/#p/<pid>`). No routing changes needed; the hash is resolved client-side against the local `players-<slug>.json`.
- **Slug→team_id mapping?** → Already exists in `teams/<slug>.json`. No new config.
- **Coverage tier for Phase 1?** → Active roster (~26/team). 40-man and IL stay in Phase 2.
- **Build-time budget?** → Target <8 min wall-clock (see R6) with concurrency=4 + daily cache.

### Deferred to Implementation

- Exact `ThreadPoolExecutor` concurrency number (start with 4, tune if API responses show stress).
- Exact retry/backoff parameters for 429/5xx — start with exponential backoff, max 3 retries, and measure.
- Whether `data/cache/players/` should be git-committed or git-ignored (leaning ignored; decide when implementing).
- Whether the cache key should include stat fingerprint or just the date (date is simpler; stat fingerprint would let us detect mid-day stat changes but probably isn't worth the complexity).
- Whether a partial-failure build (e.g., 2 of 30 teams' player JSONs missing) should fail the build or emit a stub JSON and log a warning. Leaning: log + stub, so one flaky team doesn't kill the daily run.

## Implementation Units

- [ ] **Unit 1: Generalize the player-card data pipeline to any team**

**Goal:** Add a new `load_team_players(team_id, season)` function that hydrates the full active roster using the existing `_fetch_player_record` helper. Shape-compatible with the current `load_player_cards` output.

**Requirements:** R3, R6

**Dependencies:** None.

**Files:**
- Modify: `build.py` (add `load_team_players` near `build.py:983` beside `load_player_cards`)
- Test: `tests/test_player_pipeline.py` (new) — unit-level tests that mock HTTP and assert shape

**Approach:**
- Fetch `/teams/{team_id}/roster?rosterType=active` (pattern from `build.py:258`)
- For each roster entry, call `_fetch_player_record(pid, role, season)` where `role` is inferred from `position.code` (pitchers → `"pitcher"`, everyone else → `"hitter"`)
- Return the same dict shape as `load_player_cards`: `{str(pid): record, ...}`
- Do not break `load_player_cards` — the MVP Cubs path still uses it

**Patterns to follow:**
- `build.py:983` (`load_player_cards`) — return shape
- `build.py:890` (`_fetch_player_record`) — per-player hydration contract
- `build.py:258` — active roster fetch idiom

**Test scenarios:**
- Happy path: given a mocked roster of 3 players (2 hitters + 1 pitcher), `load_team_players` returns a dict with 3 entries, keyed by stringified pid, with the pitcher record carrying `role="pitcher"` and the hitters carrying `role="hitter"`.
- Edge case: empty roster returns `{}` without raising.
- Error path: if `_fetch_player_record` raises for one player, that player is skipped (logged) and other players still land in the output — one bad player does not kill the whole team.

**Verification:**
- Running the new function against a real team id (e.g., 112) produces ~26 records with non-null names and populated `season` dicts.
- Existing `load_player_cards` still returns the same output it did before this unit.

---

- [ ] **Unit 2: Add bounded concurrency + per-day disk cache for player records**

**Goal:** Make the per-team hydration fast enough and API-friendly enough to run across 30 teams in a single daily build.

**Requirements:** R6, R8

**Dependencies:** Unit 1.

**Files:**
- Modify: `build.py` (wrap `_fetch_player_record` with a cache layer; add a `ThreadPoolExecutor` dispatch inside `load_team_players`)
- Create: `data/cache/players/.gitkeep` (or add to `.gitignore` — decide during execution)
- Test: `tests/test_player_pipeline.py` (extend with cache tests)

**Approach:**
- Wrap `_fetch_player_record` behind `_fetch_player_record_cached(pid, role, season, today)` that checks `data/cache/players/<pid>-<season>-<YYYY-MM-DD>.json` first, falls back to network, writes on success.
- In `load_team_players`, use `concurrent.futures.ThreadPoolExecutor(max_workers=4)` (stdlib — keeps the "stdlib-only" convention from `project_morning_lineup.md` memory intact) to parallelize per-player fetches.
- Add simple retry with exponential backoff on 429 and 5xx (3 retries, 0.5s → 1s → 2s).
- On total failure for one player, skip and log — don't block the team.

**Patterns to follow:**
- Stdlib-only HTTP via `urllib` as used elsewhere in `build.py`
- Existing `save_data_ledger` pattern for on-disk JSON artifacts

**Test scenarios:**
- Happy path: a cache hit returns the cached record without hitting the network (assert the mocked fetcher is not called).
- Edge case: cache file exists but is from yesterday → cache miss, network call is made.
- Error path: fetcher raises 429 twice then succeeds → retry logic returns the successful result.
- Error path: fetcher raises 3 times → function returns `None` and does not crash the caller.
- Integration: `load_team_players` with 3 mock players and `max_workers=2` returns all 3 records (order may differ — assert by key).

**Verification:**
- A full Cubs rebuild after an initial cache-warm run takes visibly less wall-clock time than the cold run.
- Cache directory contains one file per player after a warm run.

---

- [ ] **Unit 3: Emit `players-<slug>.json` for every team in the builder**

**Goal:** Un-gate the player artifact emission so every team run produces a per-team JSON, not just Cubs.

**Requirements:** R1, R3

**Dependencies:** Unit 1, Unit 2.

**Files:**
- Modify: `build.py` (generalize the Cubs-only block starting at `build.py:1099`; rename the saver or parameterize it)

**Approach:**
- Replace `save_players_cubs(players, today)` with `save_players(team_slug, players, today)` writing to `data/players-<slug>.json` — same payload shape, new filename.
- Move the invocation out of the `if _team_slug == "cubs":` block so it runs for every team.
- Drop the Cubs-specific pre-game-lineup fallback from this code path — it's unnecessary when we're hydrating the full active roster (the roster is always populated). Keep the fallback only where `today_lineup` is still needed by `headline.py` (Cubs-only behavior).

**Patterns to follow:**
- `build.py:1099` block — existing Cubs branch is the skeleton
- `save_data_ledger` — JSON write pattern

**Test scenarios:**
- Happy path: running `python build.py --team yankees` writes `data/players-yankees.json` with a populated `players` dict.
- Edge case: a team with a network failure on its roster endpoint does not crash the build; an empty-but-well-formed `players-<slug>.json` is still written with an error flag (or is skipped and logged — decide during execution per Deferred to Implementation).
- Integration: running a full `python build.py --all` (or equivalent loop) emits 30 `players-<slug>.json` files under `data/`.

**Verification:**
- `ls data/players-*.json` shows 30 files after a full build.
- Existing `data/players-cubs.json` still contains the MVP's Cubs starter+SP slice (or, if we now hydrate the full roster for Cubs too, contains ~26 entries — either is acceptable as long as the deeplink URL works).

---

- [ ] **Unit 4: Un-gate `player-card.js` on all 30 team pages**

**Goal:** Ship the web component to every team page so `#p/<pid>` deeplinks can mount a card from any `/<slug>/` URL.

**Requirements:** R2, R4

**Dependencies:** Unit 3 (the JSON must exist before the JS tries to load it).

**Files:**
- Modify: `build.py:818` (the f-string script-tag conditional — drop the Cubs gate, always emit the tag; also add a `data-team="<slug>"` attribute somewhere accessible to the component, e.g., on `<body>` or on a meta tag)
- Modify: `cubs/player-card.js` (read team slug from `document.body.dataset.team` or equivalent; load `../data/players-<slug>.json` instead of the hardcoded Cubs path)
- Modify: every team's output (handled automatically by the builder — no per-team HTML edits)

**Approach:**
- In `build.py:818`, unconditionally emit `<script src="player-card.js" defer></script>` and ensure the body tag carries the slug.
- In `cubs/player-card.js`, replace the hardcoded `../data/players-cubs.json` load with `../data/players-${slug}.json` where `slug = document.body?.dataset?.team || 'cubs'` (fallback preserves current behavior during rollout).
- Copy `cubs/player-card.js` → repo root `player-card.js` to keep the existing dual-location pattern from the MVP (since teams output to `/<slug>/index.html` and reference `player-card.js` relative to that directory).
- **Note:** verify where `player-card.js` actually needs to live for the `defer` tag's relative path to resolve on every team page. If the build copies it into each team directory, do that; if it lives at the repo root, adjust the script src. This is a directional decision to confirm during execution.

**Execution note:** After this unit, re-bless snapshots for **all 30 teams** — each team page now carries one additional script tag.

**Patterns to follow:**
- `build.py:818` — the existing conditional is the precedent
- `cubs/player-card.js` `openFromHash()` — already team-agnostic; don't touch it

**Test scenarios:**
- Happy path: a Yankees page loaded with URL `#p/665795` (or any valid active Yankees player pid) opens the card overlay with the correct name/stats.
- Happy path: loading `/cubs/#p/665795` still opens Edward Cabrera's card (MVP regression check).
- Edge case: loading `/yankees/#p/999999` (unknown pid) shows a stub/fallback state rather than crashing the page.
- Edge case: loading any team page without a hash does nothing (no overlay auto-opens).
- Integration: clicking outside the overlay or pressing Escape dismisses it (existing behavior — ensure the un-gating didn't break it).

**Verification:**
- Every team's HTML contains `<script src="player-card.js" defer>` after the build.
- Every `/<slug>/#p/<valid_pid>` URL opens a working card.

---

- [ ] **Unit 5: Cache-bump the service worker and re-bless snapshots**

**Goal:** Ensure every device picks up the new JS + JSON paths on next load, and keep the golden test suite green.

**Requirements:** R7

**Dependencies:** Unit 4.

**Files:**
- Modify: `sw.js` (`CACHE = "lineup-v8"`)
- Modify: `cubs/sw.js` (`CACHE = "lineup-v8"`)
- Modify: `tests/fixtures/*_expected.html` (re-bless all 30 team snapshots)

**Approach:**
- Bump the cache version constant in both service workers.
- Re-run the golden fixture with `--fixture` to regenerate expected HTML for all 30 teams.
- Diff the resulting snapshot changes to confirm the only delta is the new script tag and `data-team` attribute — anything else is a regression.

**Patterns to follow:**
- MVP's cache bump from `lineup-v6` → `lineup-v7`

**Test scenarios:**
- Test expectation: none for the service worker files — they're pure constant bumps.
- Regression: after re-blessing, `pytest tests/` passes across all 30 teams.
- Regression: the snapshot diff contains only the script tag addition and body-attribute change — no accidental content shifts from other sections.

**Verification:**
- `pytest tests/` is green.
- DevTools Application tab on a refreshed team page shows `lineup-v8` as the active cache.

---

- [ ] **Unit 6: Smoke-test every team's deeplink URL**

**Goal:** Prove R1 — every active player on every team is URL-addressable.

**Requirements:** R1

**Dependencies:** Unit 5.

**Files:**
- Create: `tests/test_deeplink_smoke.py` — programmatic smoke test that, for each of 30 teams, picks one known pid from the generated `data/players-<slug>.json` and asserts the card opens when the URL is visited.

**Approach:**
- Loop over `data/players-*.json` → for each, pick the first pid → load the team page with headless Playwright (already available per memory) at `#p/<pid>` → assert an overlay element with the expected DOM shape appears.
- This is end-to-end — it verifies the whole chain (JSON written, JS loaded, hash routing fires, overlay mounts).

**Execution note:** Use Playwright MCP with chromium fallback per `feedback_screenshot_ui_loop.md`.

**Patterns to follow:**
- Existing Playwright usage in `tests/test_player_card_live.html` (MVP smoke harness) — generalize the approach across 30 teams.

**Test scenarios:**
- Happy path: for each of the 30 teams, the first-pid deeplink opens a card whose displayed name matches the JSON's `name` field.
- Error path: a synthetic broken deeplink (invalid pid) degrades gracefully without a JS exception in the page console.
- Integration: the test catches regressions where the script tag is missing, the JSON path is wrong, or the hash handler isn't installed.

**Verification:**
- All 30 team smoke assertions pass in a single test run.
- Console is clean (no errors) on every tested page.

## System-Wide Impact

- **Interaction graph:** `build.py` now writes 30 new JSON files per build and emits one additional script tag per team page. `sections/headline.py` behavior is unchanged (still Cubs-gated). `cubs/player-card.js` and its copy at repo root fan out to all team pages. The service worker intercepts and caches the new JS + JSON paths.
- **Error propagation:** A failure in one team's roster fetch should log + stub, not crash the build. A failure in the JSON load on the client should fall back gracefully (existing MVP behavior: stub card with just a name). Concurrency errors should retry with backoff and ultimately skip individual players rather than the whole team.
- **State lifecycle risks:** The per-day cache under `data/cache/players/` could grow unbounded across seasons if never pruned. Low priority for Phase 1 (files are small), but worth noting for future cleanup.
- **API surface parity:** The deeplink URL pattern `/<slug>/#p/<pid>` becomes a de facto public URL — JB may share these in Slack or social. Once shared, the hash shape is hard to change without breaking links. Pick it carefully in Unit 4 (leaning toward keeping `#p/<pid>` as established in the MVP hash handler).
- **Integration coverage:** The Unit 6 smoke test is the load-bearing check that the full chain works end-to-end across all teams. Unit tests alone won't prove the client-side hash handler fires on a team page that wasn't Cubs.
- **Unchanged invariants:** The `<player-card>` DOM contract, the JSON schema shape (name, season, career, temp_strip, advanced), the `sections/headline.py` lineup wrapping behavior (Cubs-only), and the existing MVP URL for Cubs deeplinks (`/cubs/#p/665795`, etc.) all remain unchanged.

## Risks & Dependencies

| Risk | Mitigation |
|---|---|
| MLB Stats API throttles the build during the ~30-team fan-out, causing partial failures or 429s. | Bounded concurrency (start at 4), exponential backoff, per-day cache so repeated runs don't re-hit the API, log + stub on total failure so one team doesn't kill the whole build. |
| Build wall-clock balloons past the daily cron window. | Per-day cache makes steady-state runs cheap (cache-hit path is ~milliseconds). Cold runs at concurrency=4 should stay under 5 min. If not, raise concurrency cautiously or shard by team. |
| Snapshot regressions on 30 teams after un-gating the script tag. | Unit 5 explicitly re-blesses all 30 snapshots, and Unit 6 adds a smoke test to catch future regressions. Diff every re-blessed fixture before committing. |
| `player-card.js` location mismatch (repo root vs per-team dir) breaks the relative path on some teams. | Unit 4 calls this out as a directional decision to confirm during execution. Verify with a real headless load of at least 3 team pages before committing. |
| Deeplink URL shape gets shared externally and then needs to change. | Don't change it — keep `/<slug>/#p/<pid>` matching the MVP. If structural change is ever needed, ship a client-side redirect from the old hash to the new one. |
| Stale service worker caches a mix of v7 and v8 assets on users' devices. | Cache-bump to `lineup-v8` in Unit 5; the existing activate handler already deletes old caches. |
| Per-team roster endpoint is occasionally slow or times out. | Retry with backoff + timeout guard. Skip + log on total failure. Daily re-run will self-heal. |

## Documentation / Operational Notes

- No user-facing docs yet. After Phase 1 ships, add a one-line note somewhere (README or a `docs/` entry) documenting the `/<slug>/#p/<pid>` URL pattern so JB has a reference.
- The daily 08:00 UTC trigger (per `project_morning_lineup.md` memory) will pick up the new pipeline automatically once merged — no cron changes needed.
- Post-deploy validation: hit 3 random team deeplinks from 3 different teams and confirm cards open. If Unit 6 is green, this is belt-and-suspenders.

## Sources & References

- Origin: `docs/brainstorms/2026-04-11-player-cards-mvp-requirements.md`
- Prior plan: `docs/plans/2026-04-11-001-feat-player-cards-cubs-mvp-plan.md`
- Ideation: `docs/ideation/2026-04-11-player-cards-scaling-ideation.md`
- Prototype: `docs/design/2026-04-11-player-card-prototype.html`
- Key code: `build.py:46`, `build.py:251`, `build.py:818`, `build.py:890`, `build.py:983`, `build.py:1099`, `cubs/player-card.js`, `sections/headline.py`, `teams/cubs.json`
