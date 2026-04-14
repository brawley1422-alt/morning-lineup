---
title: "feat: Baseball Savant advanced stats in form guide and scouting report"
type: feat
status: completed
date: 2026-04-14
---

# feat: Baseball Savant advanced stats in form guide and scouting report

## Overview

Add Baseball Savant Statcast metrics to the two section files where they create the highest reader payoff: the Form Guide hot/cold block in `sections/headline.py` (phase 1) and the pitching matchup card in `sections/scouting.py` (phase 2). Data is fetched from Savant's public JSON endpoints, cached per-player daily on disk, and surfaced through the already-reserved `advanced: {}` slot on player records.

## Problem Frame

Today every stat on a team briefing comes from the MLB Stats API v1 (`statsapi.mlb.com`). That gives us traditional lines — AVG, OPS, ERA, WHIP, K — but nothing Statcast. The Scout pass on the codebase found two concrete consequences:

1. **The Form Guide is noisy.** `_render_hot_cold()` in `sections/headline.py:361-447` sorts hitters by last-7-games OPS and pitchers by last-7-games ERA. Seven games of traditional stats is a coin flip — a couple of bloopers or a bad bullpen day dominates the sort. Expected stats (xwOBA, xERA) and process stats (barrel%, whiff%) are exactly the metrics that stabilize at that sample size and distinguish skill from luck.
2. **The Scouting Report is generic.** `_sp_card()` in `sections/scouting.py:47` shows ERA/W-L/IP/K/WHIP plus last-3 game logs. That is a box score, not a scouting report. Pitch mix, velocity, spin, and per-pitch whiff rate are what turn this section from "numbers you already knew" into "the detail that makes the lede write itself."

The Scout also confirmed the instrumentation is already half-built: `build.py:1344` reserves an empty `advanced: {}` dict on every player record with the explicit comment `# Phase 1.5: Baseball Savant Statcast`, and `build.py:1382` already runs a 4-worker concurrent pool via `load_team_players()` that new per-player fetches can slot into without new infrastructure.

## Requirements Trace

- **R1.** Form Guide hitters in `sections/headline.py` must display at least one Statcast expected/process stat (xwOBA and/or barrel%) alongside existing AVG/HR/OPS columns, sourced from Savant.
- **R2.** Form Guide pitchers in `sections/headline.py` must display at least one Statcast expected/process stat (whiff% and/or xERA) alongside existing IP/ERA/K columns.
- **R3.** Form Guide sort order for hitters should shift from raw L7 OPS to a signal-over-noise metric (xwOBA preferred) so "hot" actually means "hitting it hard."
- **R4.** Scouting Report `_sp_card()` in `sections/scouting.py` must show pitch mix with velocity, spin, and per-pitch whiff% for each probable starter when Savant data is available.
- **R5.** Savant data must be fetched concurrently via the existing `load_team_players()` 4-worker pool at `build.py:1382` — no new thread pools, no new async runtime.
- **R6.** Per-player Savant payloads must be cached on disk with daily invalidation, mirroring the existing `data/cache/players/{pid}-{season}-{date}-v2.json` pattern.
- **R7.** A Savant outage or 4xx/5xx response for any single player must not break the build — the section falls back gracefully to the pre-Savant rendering for that player.
- **R8.** No new Python dependencies. Stdlib only (per CLAUDE.md: "Zero external dependencies").
- **R9.** Phase 1 (Form Guide) must be shippable independently of Phase 2 (Scouting Report) so either can land without blocking the other.

## Scope Boundaries

**In scope:**
- Form Guide hot/cold block (hitters + pitchers) in `sections/headline.py`
- Scouting Report probable-starter cards in `sections/scouting.py`
- New fetch helper + disk cache in `build.py`
- Extending the `advanced: {}` slot on player records with a stable schema

**Explicit non-goals for this plan:**
- **League Leaders section** (`sections/around_league.py:85`). Savant leaderboards exist, but the editorial payoff is low and the visual block is already crowded.
- **Farm / MiLB prospects** (`sections/farm.py`). Savant's minor-league Statcast coverage is inconsistent; not worth the fallback logic.
- **Three Stars** (yesterday's game hero stats in `sections/headline.py`). Adding xwOBA to a single-game recap is noise, not signal.
- **Historical backfill.** Daily-forward only. No one-time batch job to populate `advanced` for past dates.
- **New section or new page.** All changes land inside existing sections to keep the page envelope untouched.

## Context & Research

### Relevant Code and Patterns (from Scout findings)

Scout's repo inventory surfaced the exact files and line anchors this plan needs to modify, plus the pre-wired seams that make the integration cheap:

- **Pre-wired slot:** `build.py:1344` — `"advanced": {},  # Phase 1.5: Baseball Savant Statcast`. This dict is already attached to every player record before any section renders, so section files can read `player["advanced"]` today without a schema migration.
- **Concurrent hydration pool:** `build.py:1382` — `def load_team_players(team_id, season, today, max_workers=4):` is the entry point that fans out per-player MLB Stats API fetches. The new Savant fetch belongs in the same worker function so one player = one thread of fetches (MLB + Savant), keeping wall-clock cost constant.
- **Existing player cache pattern:** `data/cache/players/{pid}-{season}-{date}-v2.json`. Scout confirmed this is re-used across builds on the same day and invalidates naturally when the date rolls. New Savant cache follows the same shape at `data/cache/savant/{pid}-{date}.json` (no `season` key — Savant endpoints are scoped by a date window, not a season string).
- **Form Guide renderer to modify:** `sections/headline.py:361` `def _render_hot_cold(hitters_data, pitchers_data):` (ends around :447). This function today sorts hitters by OPS and pitchers by ERA, then emits two dual-column HTML blocks. Phase 1 touches this function only.
- **Scouting matchup card to modify:** `sections/scouting.py:47` `def _sp_card(sp, side_label, is_own=False, side_team_id=None):`. This is where the per-pitcher card is built. Phase 2 touches this function only.
- **Fetch helper parallel:** `build.py:474` `def fetch_pitcher_line(pid):` is the existing "fetch one pitcher's season line from MLB API" helper. The new `fetch_savant_player(pid)` should live adjacent to it and mirror its shape (small, typed-dict return, error-tolerant).
- **Call site to extend:** `build.py:1597` — `_team_players = load_team_players(TEAM_ID, _d2["season"], _d2["today"])`. No change here; the Savant fetch piggybacks inside the worker.

### Institutional Learnings

From CLAUDE.md for this project:

- **"Zero external dependencies. Uses only Python stdlib"** — rules out `requests`/`httpx`/`pybaseball`. Savant fetch uses `urllib.request` like the existing MLB Stats API callers.
- **"Always use `html.escape()` on API-returned strings before injecting into HTML"** — applies to pitch-type names and any Savant string fields rendered in `_sp_card`.
- **"Editorial lede: `generate_lede()` tries Ollama first, falls back to Anthropic API, caches result in `data/lede-{slug}-YYYY-MM-DD.txt`"** — same caching philosophy (daily file, graceful fallback) applies here.
- **Section file rule:** *"Never `from build import ...` at module top — use deferred imports inside function bodies."* If a section file needs a `build.py` helper (e.g., to re-fetch Savant on demand), import it inside the function.

### External References

- **Savant endpoints** (public, no auth):
  - `https://baseballsavant.mlb.com/player-services/statcast-player?playerId={mlbam_id}` — per-player rolling splits
  - `https://baseballsavant.mlb.com/leaderboard/expected_statistics?...&player_id={id}` — xBA/xSLG/xwOBA
  - `https://baseballsavant.mlb.com/player-services/player-pitch-mix?playerId={id}` — pitch mix, velo, spin, whiff by pitch type
- **ID mapping:** none required. Scout confirmed MLBAM `pid` already stored on every player record matches Savant's `player_id`.

## Key Technical Decisions

1. **Savant data goes into `player["advanced"]`, not a new top-level key.** Rationale: the slot is already plumbed end-to-end (`build.py:1344` → `load_team_players()` → passed to section renderers), so no callsite changes are needed outside the two target sections.
2. **Cache key is `{pid}-{date}.json`, not `{pid}-{season}-{date}-v2.json`.** Rationale: Savant endpoints accept a date window; a season tag adds no precision. Keeping the filename shorter also makes it clear at a glance that this cache is Savant-scoped.
3. **Fetch failures are silent per-player, not per-build.** Rationale (R7): Savant is third-party and not under our SLA. One 500 on one player cannot take down the team page. On error, `player["advanced"] = {}` and section renderers check-and-fall-back.
4. **Form Guide sort switches to xwOBA (hitters) and xERA (pitchers) when Savant data is present, falls back to OPS/ERA when absent.** Rationale (R3): makes the new metric load-bearing instead of decorative, while keeping the section resilient on Savant outages.
5. **Phase 2 pitch mix is rendered inline in `_sp_card`, not as a new sub-section.** Rationale: keeps the page envelope and TOC untouched (per CLAUDE.md "Adding or reordering sections" checklist — we don't want to trigger that path).
6. **No shared `sections/_helpers.py`.** Rationale: CLAUDE.md calls this out explicitly as a scope boundary the project has chosen. Any small format helpers (`_fmt_pct`, `_fmt_velo`) are inlined per section file, matching `_abbr`/`_fmt_time_ct`/`_ordinal`.
7. **Savant schema is versioned in-cache** with a `"schema": 1` field. Rationale: lets phase 2 extend the payload (pitch mix) without invalidating phase 1 caches — a bumped schema forces a rebuild of the affected records.

## Open Questions

### Resolved During Planning

- **Which Savant endpoints to hit?** → The three listed in External References. `statcast-player` and `expected_statistics` cover phase 1; `player-pitch-mix` adds phase 2.
- **How do Savant IDs map to our IDs?** → They are the same number (MLBAM). No mapping layer.
- **Where does the cache live?** → `data/cache/savant/{pid}-{date}.json`, parallel to the existing `data/cache/players/`.
- **New dependency?** → No. `urllib.request` + `json` from stdlib.

### Deferred to Implementation

- **Exact JSON shapes of the three Savant endpoints.** These are undocumented public endpoints; field names and nesting should be confirmed by fetching one live payload during implementation and pinning the parse to the actual keys, not guessed keys.
- **Timeout and retry budget per Savant call.** Pick during implementation based on observed latency; start with the same socket timeout `build.py` uses for MLB Stats API calls and adjust if needed.
- **Which Savant leaderboard filter produces the "last 15 games" window** used by `temp_strip` so the form guide can match the same window. Confirm during implementation; if Savant only exposes season-to-date, use season-to-date and note the mismatch in a comment.
- **Whether to memoize per-pitch-type whiff% inside the cache file or compute at render time.** Cheap either way; pick based on payload size once a real response is in hand.

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

**Data flow (one team build):**

```
build.py main
  └─ load_team_players(team_id, season, today)           [build.py:1382]
        └─ ThreadPoolExecutor(max_workers=4)
              └─ per player: fetch_player_record(pid)
                    ├─ MLB Stats API → season/career/temp_strip  (existing)
                    └─ fetch_savant_player(pid, today)            (NEW)
                          ├─ check data/cache/savant/{pid}-{today}.json
                          ├─ miss: GET statcast-player + expected_statistics
                          │        (+ player-pitch-mix in phase 2)
                          ├─ parse into {xwoba, barrel_pct, whiff_pct,
                          │              xera, pitch_mix, schema: 1}
                          ├─ write cache file
                          └─ return dict (or {} on any error)
              ← player["advanced"] = <savant dict or {}>

sections/headline.py _render_hot_cold(hitters, pitchers)  [sections/headline.py:361]
  ├─ hitters: sort by advanced.xwoba if present else fall back to OPS
  │           render column = xwOBA (barrel% secondary)
  └─ pitchers: sort by advanced.xera if present else fall back to ERA
              render column = whiff% (xERA secondary)

sections/scouting.py _sp_card(sp, ...)                    [sections/scouting.py:47]
  └─ if sp.advanced.pitch_mix present:
        render compact pitch mix table
        (pitch_type, usage%, avg_velo, avg_spin, whiff%)
```

**Savant "advanced" dict schema (v1):**

```
{
  "schema": 1,
  "updated": "2026-04-14",
  "hitter": {
    "xwoba": 0.389,
    "barrel_pct": 14.2,
    "xba": 0.291,
    "xslg": 0.512
  },
  "pitcher": {
    "xera": 3.12,
    "whiff_pct": 31.5,
    "chase_pct": 28.8,
    "pitch_mix": [
      {"pitch": "FF", "usage": 48.2, "velo": 96.4, "spin": 2410, "whiff": 25.3},
      {"pitch": "SL", "usage": 31.7, "velo": 88.1, "spin": 2610, "whiff": 42.1}
    ]
  }
}
```

Either `hitter` or `pitcher` sub-dict may be absent (two-way players aside, most records only fill one side).

## Implementation Units

### Phase 1 — Form Guide (shippable independently)

- [x] **Unit 1: Add `fetch_savant_player(pid, today)` helper to `build.py`**

  **Goal:** Introduce one stdlib-only fetch helper that takes an MLBAM pid and a date, hits Savant's `statcast-player` and `expected_statistics` endpoints, parses them into the `hitter`/`pitcher` schema described above, caches the result to disk, and returns the dict. On any HTTP error, parse error, or missing field, return `{}` (not raise).

  **Requirements:** R5, R6, R7, R8

  **Dependencies:** None.

  **Files:**
  - Modify: `build.py` (add `fetch_savant_player()` adjacent to `fetch_pitcher_line()` at `build.py:474`)
  - Create: `data/cache/savant/` (directory, gitignored like other cache dirs)
  - Test: `tests/test_savant_fetch.py` (new; stdlib `unittest` — project does not use pytest)

  **Approach:**
  - Mirror the shape of `fetch_pitcher_line()` at `build.py:474`: small function, typed-dict return, error-tolerant, stdlib only (`urllib.request`, `json`).
  - Cache lookup first: if `data/cache/savant/{pid}-{today}.json` exists and its `schema` matches the current version, load and return it.
  - Cache miss: fetch both phase 1 endpoints, parse into the v1 schema, write cache file, return.
  - Any `urllib.error.*`, `json.JSONDecodeError`, `KeyError`, or socket timeout → log once and return `{}`.
  - No retries in v1 (keep the blast radius small — form guide degrades to today's behavior on any failure).

  **Patterns to follow:**
  - `build.py:474` `fetch_pitcher_line(pid)` — for function shape, error handling, and stdlib-only fetch style.
  - The existing `data/cache/players/` daily-invalidation pattern for cache filename conventions.
  - CLAUDE.md rule: *"Always use `html.escape()` on API-returned strings before injecting into HTML"* — applies downstream in Units 2-3, not here, but keep returned strings raw (no pre-escaping in the cache).

  **Test scenarios:**
  - *Happy path:* given a fake Savant JSON fixture for a hitter with known xwOBA/barrel%, `fetch_savant_player()` returns a dict whose `hitter.xwoba` matches the fixture.
  - *Happy path:* same for a pitcher fixture with xERA + whiff%.
  - *Cache hit:* second call on same `(pid, today)` reads from disk without issuing a network call (mock `urllib.request.urlopen` and assert call count == 0 on second invocation).
  - *Cache miss writes file:* first call writes `data/cache/savant/{pid}-{today}.json` with `schema: 1`.
  - *Error path:* `urlopen` raises `URLError` → function returns `{}` and does not write a cache file.
  - *Error path:* endpoint returns 200 with HTML (Savant occasionally does this on malformed params) → `JSONDecodeError` is caught, returns `{}`.
  - *Error path:* endpoint returns 200 with JSON missing the expected keys → returns `{}` without KeyError.
  - *Edge case:* `pid=None` or `pid=0` short-circuits to `{}` without an HTTP call.

  **Verification:**
  - Running `python3 build.py --team cubs` on a day with game data produces a cache file at `data/cache/savant/{pid}-{today}.json` for at least one player, and the build exits 0.
  - Deleting the cache file and rerunning regenerates it.
  - Disabling network (e.g. pointing Savant host at localhost:1) still lets the build exit 0 with empty `advanced` dicts.

---

- [x] **Unit 2: Wire Savant fetch into `load_team_players()` worker**

  **Goal:** Inside the existing 4-worker pool at `build.py:1382`, call `fetch_savant_player(pid, today)` after the MLB Stats API fetches complete and assign the result to `player["advanced"]`. Do not add new worker threads or a second pool.

  **Requirements:** R5, R7

  **Dependencies:** Unit 1.

  **Files:**
  - Modify: `build.py` (inside the per-player worker invoked from `load_team_players()` at `build.py:1382`)
  - Test: `tests/test_savant_fetch.py` (extend with a small integration-style test using a monkeypatched `fetch_savant_player`)

  **Approach:**
  - The `advanced: {}` slot is already populated at `build.py:1344`. Replace the literal `{}` with the return value of `fetch_savant_player(pid, today)` at the point the player dict is assembled inside the worker.
  - Keep it inline — no new helper class, no new "service" abstraction.
  - Per-player errors are already swallowed by Unit 1 returning `{}`, so no try/except wrapping at this layer.

  **Patterns to follow:**
  - Existing assignment at `build.py:1344` — mirror the style.
  - Worker function inside `load_team_players()` at `build.py:1382` — all per-player fetches already live there; the new call slots alongside them.

  **Test scenarios:**
  - *Integration:* a test that monkeypatches `fetch_savant_player` to return a known dict and calls the worker function directly, asserting that the resulting player record has `player["advanced"]["hitter"]["xwoba"]` populated.
  - *Integration — fallback:* monkeypatch `fetch_savant_player` to return `{}`, assert the worker still produces a full player record and the build path does not raise.

  **Verification:**
  - `python3 build.py --team cubs` completes in roughly the same wall-clock time as before (no new serial fetch outside the pool).
  - Inspecting the in-memory briefing object after `load_all()` shows at least one player with a non-empty `advanced` dict.

---

- [x] **Unit 3: Render xwOBA/barrel% for hitters and whiff%/xERA for pitchers in `_render_hot_cold()`**

  **Goal:** Update the Form Guide renderer at `sections/headline.py:361` to show Statcast columns when `player["advanced"]` has data, re-sort by the new metric, and fall back to the existing OPS/ERA sort when `advanced` is empty.

  **Requirements:** R1, R2, R3, R7, R9

  **Dependencies:** Unit 2.

  **Files:**
  - Modify: `sections/headline.py` (the `_render_hot_cold()` body at lines 361-447)
  - Test: `tests/snapshot_test.py` (existing golden snapshot harness will diff; re-bless per `tests/README.md`)

  **Approach:**
  - For hitters: if `p["advanced"].get("hitter", {}).get("xwoba")` is present, sort the hot/cold list by that value; otherwise sort by the existing L7 OPS. Render a new column with `xwOBA` (primary) and `barrel%` (secondary, in small muted text next to OPS).
  - For pitchers: same pattern with `xera` for sort and `whiff%` as the visible column alongside ERA.
  - Keep column widths and CSS class names in sync with the existing form-guide grid so no stylesheet changes are needed.
  - Inline a small `_fmt_pct(v)` helper at the top of the file (matching the existing `_abbr`/`_ordinal` inline-helper convention per CLAUDE.md).
  - Escape any Savant-sourced strings via `html.escape()` before injection (CLAUDE.md rule); numeric fields do not need escaping.

  **Patterns to follow:**
  - `sections/headline.py:361-447` — existing `_render_hot_cold()` layout, sort, and HTML emission style.
  - Other inline helpers already in `sections/headline.py` (e.g., the `_abbr` pattern referenced in CLAUDE.md) for the new `_fmt_pct` helper.

  **Test scenarios:**
  - *Happy path:* synthetic briefing fixture with `advanced.hitter.xwoba` set for 4 players; rendered HTML contains the `xwOBA` column header and the expected values in the right order.
  - *Happy path:* same for pitchers with `advanced.pitcher.whiff_pct` and `xera`.
  - *Edge case — partial data:* one hitter has `advanced`, one does not. Renderer must sort the one with data above the one without and still render both rows without crashing.
  - *Edge case — all empty:* if no player in the block has `advanced.hitter`, the renderer falls back to the existing OPS sort and does not render the new columns (or renders them as `—`, implementer's pick).
  - *Integration — golden snapshot:* `python3 tests/snapshot_test.py` runs, produces a diff against the frozen Cubs and Yankees fixtures. The diff is expected (new columns are intentional) and is re-blessed per `tests/README.md`.

  **Verification:**
  - `python3 build.py --team cubs` renders a page with visible xwOBA and whiff% columns in the Form Guide section.
  - Re-running with `data/cache/savant/` deleted and the network pointed at an invalid host produces the pre-Savant form guide layout (fallback path) with exit code 0.
  - Golden snapshot test re-blessed and committed.

---

### Phase 2 — Scouting Report (ships after Phase 1)

- [x] **Unit 4: Extend `fetch_savant_player()` with pitch-mix endpoint**

  **Goal:** Add the third Savant endpoint (`player-pitch-mix`) to the fetch helper, populate `advanced.pitcher.pitch_mix` in the cache, and bump the schema to `2`.

  **Requirements:** R4, R6, R7, R8

  **Dependencies:** Unit 1.

  **Files:**
  - Modify: `build.py` (extend `fetch_savant_player()`)
  - Test: `tests/test_savant_fetch.py` (extend)

  **Approach:**
  - Add a third `urlopen` call inside `fetch_savant_player()` for the pitch-mix endpoint; only issue it when the player has pitcher data (skip the extra call for pure hitters to keep wall-clock cost minimal).
  - Parse into the `pitch_mix` list of dicts defined in the schema above.
  - Bump `schema: 1` → `schema: 2`. The cache loader should treat a stale schema as a miss and re-fetch.

  **Patterns to follow:**
  - Same stdlib fetch style as Unit 1.
  - Schema version bump pattern used elsewhere (e.g., the `v2` suffix in `data/cache/players/{pid}-{season}-{date}-v2.json`).

  **Test scenarios:**
  - *Happy path:* fixture with two pitch types returns a `pitch_mix` list of length 2 with the expected `pitch`, `usage`, `velo`, `spin`, `whiff` fields.
  - *Cache bump:* an on-disk file with `schema: 1` is treated as a miss and overwritten with a `schema: 2` file.
  - *Error path:* pitch-mix endpoint 500s but the first two endpoints succeed → returned dict still has `hitter`/`pitcher` expected-stats fields and `pitch_mix: []` (graceful partial).
  - *Edge case:* pure hitter (no pitcher data) → no pitch-mix call is issued (mock assertion) and the returned dict has no `pitcher` subkey.

  **Verification:**
  - Cache files for active starters now contain a populated `pitch_mix` list.
  - Cache files for position players do not contain a `pitcher` subkey.

---

- [x] **Unit 5: Render pitch mix in `_sp_card()`**

  **Goal:** Update the probable-starter card at `sections/scouting.py:47` to render a compact pitch-mix table (pitch type, usage%, velo, spin, whiff%) when `sp["advanced"]["pitcher"]["pitch_mix"]` is present. Fall back to today's layout when absent.

  **Requirements:** R4, R7, R9

  **Dependencies:** Unit 4.

  **Files:**
  - Modify: `sections/scouting.py` (inside `_sp_card()` at line 47)
  - Test: `tests/snapshot_test.py` (golden snapshot re-bless)

  **Approach:**
  - After the existing season-line block, append a small `<table class="pitch-mix">` only when `pitch_mix` is a non-empty list.
  - Cap display at top-4 pitches by usage to keep the card from growing tall.
  - Pitch-type codes (`FF`, `SL`, etc.) map to human labels via a small inline dict (`_PITCH_LABEL = {"FF": "Four-Seam", ...}`) — no new helper module.
  - `html.escape()` the pitch-type label before injection.
  - CSS: if existing `style.css` has table styles that cover this, reuse them. If not, add a minimal `.pitch-mix` block to `style.css` (inlined by build.py at build time per CLAUDE.md).

  **Patterns to follow:**
  - `sections/scouting.py:47` `_sp_card()` — existing card layout, data access style, and conditional rendering (`if off-day: return ""`).
  - CLAUDE.md: *"CSS lives in `style.css` and is inlined by build.py at build time. Team colors are injected by replacing CSS variable defaults with config values."* — any new CSS goes in `style.css`, not inline.

  **Test scenarios:**
  - *Happy path:* fixture with 4 pitch types → rendered card contains a `pitch-mix` table with 4 rows in usage-descending order.
  - *Edge case:* fixture with 6 pitch types → only top 4 are rendered.
  - *Edge case — empty:* `pitch_mix: []` → no table rendered, card matches pre-phase-2 layout.
  - *Edge case — missing advanced dict:* `sp["advanced"] = {}` → no table, no crash.
  - *Integration — golden snapshot:* re-bless Cubs/Yankees fixtures against the new card layout per `tests/README.md`.

  **Verification:**
  - `python3 build.py --team cubs` on a game day renders a visible pitch-mix table in the Scouting Report.
  - Off-day build still returns empty from `sections/scouting.py` (no regression to the existing conditional-render behavior).

## System-Wide Impact

- **Interaction graph:** `build.py` `load_team_players()` gains one new per-worker call. `sections/headline.py._render_hot_cold` and `sections/scouting.py._sp_card` gain conditional render branches. No other sections, no other entry points.
- **Error propagation:** All Savant errors are absorbed at the fetch boundary (Unit 1 returns `{}` on any failure). Section renderers check-and-fall-back. A Savant outage cannot fail a team build.
- **State lifecycle risks:** Daily disk cache at `data/cache/savant/`. Stale entries naturally expire when the date rolls. Schema bumps (Unit 4) invalidate prior-day entries automatically via the schema-version check.
- **API surface parity:** The pre-wired `advanced: {}` slot at `build.py:1344` is now populated for all 30 teams, not just Cubs. Nothing external consumes this dict yet; no downstream contract to preserve.
- **Integration coverage:** Golden snapshot tests in `tests/snapshot_test.py` re-bless after Units 3 and 5. Per CLAUDE.md: *"Re-bless procedure in `tests/README.md`"* — follow exactly.
- **Unchanged invariants:** The page envelope, TOC, section numbering (`_num` dict in `build.py.page()`), and section ordering are all untouched. Per CLAUDE.md, any of those changes would trigger the "Adding or reordering sections" checklist — this plan explicitly stays inside existing sections to avoid that path. `sections/around_league.py` League Leaders, `sections/farm.py` prospects, and `sections/headline.py` Three Stars are all intentionally untouched.

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Savant endpoints are undocumented and could change shape or go 404 without warning | Fetch helper returns `{}` on any parse or HTTP error (Unit 1). Section renderers fall back to today's behavior. A broken Savant = a build that looks like yesterday, not a build that fails. |
| Per-player Savant latency slows the daily build | Fetches run inside the existing 4-worker pool at `build.py:1382`, concurrent with MLB Stats API calls for the same player. Worst case adds one round-trip per player-worker, not 40 sequential calls. Unit 4 skips the third endpoint for non-pitchers to keep wall-clock cost down. |
| Savant IP-blocks or rate-limits during daily builds | Daily disk cache at `data/cache/savant/{pid}-{date}.json` means each player is fetched at most once per day. Re-runs on the same day hit cache. If Savant blocks anyway, error path (R7) degrades to pre-Savant layout and the build still ships. |
| Undocumented JSON shapes lead to KeyErrors | Deferred to implementation: confirm keys by fetching one live payload before pinning the parse. Unit 1 test scenarios include "missing key returns `{}`" to enforce defensive parsing. |
| Golden snapshot diffs block merge when only Unit 3 or Unit 5 is re-blessed | Re-bless per `tests/README.md` as part of the same PR/commit as the rendering change. CLAUDE.md calls this out explicitly in the "Adding or reordering sections" section. |
| Form Guide sort flip (OPS → xwOBA) produces a "who is this guy?" moment for readers used to the old sort | This is the point (R3). Keep both visible columns so the reader can see both signals during the transition; monitor reader reaction after phase 1 ships before deciding whether to remove the legacy column. |
| New `data/cache/savant/` directory not created on first run | Unit 1 creates the directory on first write (`pathlib.Path.mkdir(parents=True, exist_ok=True)`). Test scenario covers the cold-start case. |

## Verification

**End-to-end verification after Phase 1:**
1. Delete `data/cache/savant/` if it exists.
2. Run `python3 build.py --team cubs` — expect exit 0, cache directory populated, and visible `xwOBA` / `whiff%` columns in the Form Guide section of the generated page.
3. Run `python3 build.py --team yankees` — same expectation for a second team to confirm the fetch/cache/render path is team-agnostic.
4. Re-run `python3 build.py --team cubs` immediately — expect the Savant cache to be hit (no new fetches; observable by file mtimes not changing).
5. Temporarily point the Savant host at an unreachable IP in an `/etc/hosts` override or via a monkeypatched `urlopen`. Run `python3 build.py --team cubs` — expect exit 0 and the pre-Savant form-guide layout (fallback path).
6. Run `python3 tests/snapshot_test.py` — expect the known diff from Units 3 (and 5, if shipping together). Re-bless per `tests/README.md`.
7. Confirm no new `pip install` step was added and `grep -r 'import requests\|import httpx' build.py sections/` returns empty (R8).

**End-to-end verification after Phase 2:**
1. Same steps 1-4 above, plus: confirm `data/cache/savant/{starter_pid}-{today}.json` contains a non-empty `pitch_mix` list for today's probable starters on both teams.
2. Open the generated Scouting Report section in a browser and confirm the pitch-mix table renders with 4 rows, ordered by usage descending.
3. Off-day verification: manually pick a team with no game today and confirm `sections/scouting.py` still returns empty (existing behavior preserved).

## Sources & References

- **Scout findings on current stats inventory:** inline earlier in this conversation. Confirmed repo paths:
  - `build.py:474` `fetch_pitcher_line(pid)`
  - `build.py:1344` `"advanced": {},  # Phase 1.5: Baseball Savant Statcast`
  - `build.py:1382` `def load_team_players(team_id, season, today, max_workers=4):`
  - `build.py:1597` call site for `load_team_players`
  - `sections/headline.py:361` `def _render_hot_cold(hitters_data, pitchers_data):`
  - `sections/scouting.py:47` `def _sp_card(sp, side_label, is_own=False, side_team_id=None):`
  - `sections/around_league.py:85` `def _render_leaders(lh, lp, tmap):` (explicitly out of scope)
  - `data/cache/players/{pid}-{season}-{date}-v2.json` (existing cache pattern to mirror)
- **Project instructions:** `CLAUDE.md` — zero-dependencies rule, `html.escape()` rule, section-file import rule, golden snapshot re-bless procedure.
- **Golden snapshot harness:** `tests/snapshot_test.py`, re-bless procedure in `tests/README.md`.
- **Savant endpoints** (public, no auth):
  - `https://baseballsavant.mlb.com/player-services/statcast-player?playerId={mlbam_id}`
  - `https://baseballsavant.mlb.com/leaderboard/expected_statistics?...&player_id={id}`
  - `https://baseballsavant.mlb.com/player-services/player-pitch-mix?playerId={id}`
