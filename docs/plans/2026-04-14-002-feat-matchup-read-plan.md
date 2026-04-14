---
title: "feat: Matchup Read — lineup × opposing arsenal section"
type: feat
status: completed
date: 2026-04-14
origin: null
---

# Matchup Read — lineup × opposing arsenal section

## Overview

Add a new gameday section, "Matchup Read," that grades every hitter in today's lineup against the opposing starter's arsenal. The editorial hero is per-hitter vulnerability tags (worst pitch weighted by usage × xwOBA gap) and a bottom-line "exploit: SL (2), FS (1)" money line that tells the reader which pitch the pitcher will lean on to win tonight.

Builds directly on the Savant infrastructure already shipped in `docs/plans/2026-04-14-001-feat-savant-advanced-stats-plan.md`: pitcher arsenals (usage, velo, spin, whiff%) are already cached per build in `build.py:692` via `_build_savant_arsenal`. This plan adds the other half — batter performance by pitch type — and a new section file that joins them.

## Problem Frame

The Form Guide (shipped in phase 1 of the prior plan) shows *who's hot*, and the Scouting Report shows *what the pitcher throws*. Neither tells the reader the one thing that predicts tonight's outcome: **does this specific pitcher's mix match this specific lineup's weaknesses?** A slider-heavy pitcher facing a lineup of slider-vulnerable bats is the story of the game. Today that story is buried — the reader has to eyeball the arsenal card and mentally run it against hitters they might not even recognize.

Live shape-check done in the brainstorm confirmed the missing data exists as one clean CSV:
- Endpoint: `baseballsavant.mlb.com/leaderboard/pitch-arsenal-stats?type=batter&year={season}&min=50&csv=true`
- Size: 166 KB, 1,221 rows, 389 batters × ~3.1 pitch types each
- Schema: `player_id, pitch_type, pa, est_woba (xwOBA), whiff_percent, hard_hit_percent, ...`
- Pitch codes align with pitcher side on FF, SI, SL, CH, CU, ST, FC (7 types)
- Gap: pitcher-only codes FS, SV not in batter CSV → league-average fallback required

## Requirements Trace

- **R1.** Fetch batter pitch-arsenal CSV from Baseball Savant and cache it daily alongside existing Savant data, following the schema-versioned pattern at `build.py:517` (`_SAVANT_SCHEMA = 2`) so cache invalidation works identically.
- **R2.** Extend pitcher arsenal entries to also store `xwoba_allowed` per pitch (already present in the `arsenal_stats` CSV fetched at `build.py:670` but currently dropped by `_build_savant_arsenal` at `build.py:519`).
- **R3.** Compute per-hitter expected xwOBA as `Σ(pitcher_usage[pt] × batter_xwOBA_vs[pt])` with league-average fallback (≈.310) for any pitch type where the batter has no qualifying row, or any pitch type the batter CSV omits (FS, SV).
- **R4.** Assign each hitter a letter grade (A/B/C/D) using the Form Guide tier thresholds already defined in `sections/headline.py`: A ≥ .360, B .320–.360, C .290–.320, D < .290 — keeping tier colors consistent across sections.
- **R5.** Surface a single "vulnerability" or "safe" tag per hitter: the pitch with the largest weighted gap (usage × (batter_xwOBA − league_avg)) or, inverted, the pitch the hitter handles best that the pitcher relies on. Show PA-sample confidence as 1–4 dots (●●●●).
- **R6.** Handle hitters with zero Savant coverage honestly: em-dash row, no grade, no fabricated tag.
- **R7.** Render a bottom "exploit: SL (2), FS (1)" money line that counts how many lineup hitters are vulnerable to each pitch type, sorted by the pitcher's own usage of that pitch.
- **R8.** Place the section between Scouting Report and Form Guide in the existing section order (`build.py:888–901` `page()` assembly, plus `_visible_sections` registration).
- **R9.** Section must render cleanly on off-days (no game scheduled) or when either the opposing starter or the opponent lineup is missing — return empty string, same conditional pattern as `sections/scouting.py:86`.
- **R10.** Reuse existing CSS tier classes (`.t-elite`, `.t-solid`, `.t-rough` in `style.css`) and existing typographic scale; no new font variables, no new color tokens.
- **R11.** Golden snapshot tests in `tests/test_snapshot.py` must stay green through re-blessing, and new unit tests must cover the math (weighted xwOBA, fallback, tag selection, team grade).

## Scope Boundaries

- **Not doing:** handedness splits (LHB vs LHP slider ≠ LHB vs RHP slider). Savant has this on a different endpoint; accept noise for v1.
- **Not doing:** platoon matrix or pinch-hitter predictions. Only the 9 names in `today_lineup[opponent_side]` at build time.
- **Not doing:** historical head-to-head (batter vs *this specific* pitcher). That's a different data product with severe sample-size issues.
- **Not doing:** live in-game updates. Section is baked at daily build time, same as Scouting.
- **Not doing:** a player-card surface for per-pitch batter performance. That's a natural follow-up if the matchup card lands well.
- **Not doing:** changing Scouting Report layout. The new section sits below it, untouched.

## Context & Research

### Relevant Code and Patterns

Based on grep of `build.py` and reads of the sections directory, the patterns to mirror are all local and strong — no external research needed:

- **Savant CSV fetch pattern:** `build.py:625–705` `fetch_savant_leaderboards()` already batches 5 CSV fetches into one daily cache file (`data/cache/savant/leaderboards-{season}-{date}.json`), schema-versioned via `_SAVANT_SCHEMA` at `build.py:517`. The new batter arsenal CSV is a 6th fetch added to the same `urls` dict at `build.py:661` and a new top-level key on the result dict at `build.py:686`. In-memory cache via `_SAVANT_MEM` at `build.py:638`.
- **CSV parser:** `build.py:485` `_parse_savant_csv()` handles BOM stripping and returns `{pid_str: {col: value}}`. For batter arsenal we need a sibling parser that returns `{pid_str: {pitch_type: {pa, xwoba, whiff, hardhit}}}` because the CSV has multiple rows per player.
- **Arsenal merge:** `build.py:519` `_build_savant_arsenal()` already joins three CSVs (`arsenal_stats`, `arsenal_speed`, `arsenal_spin`) into the per-pitcher list. Add `xwoba_allowed` pulled from the `arsenal_stats` CSV's `est_woba` column (R2 — free upgrade, no new network calls).
- **Section render pattern:** `sections/scouting.py:77–151` `render(briefing)` is the cleanest reference. Reads `briefing.data["savant"]`, early-returns empty string if conditional fails, uses `briefing.data["next_games"]` for opponent detection, `briefing.data["tmap"]` for logo lookup. The new section mirrors this almost exactly.
- **Opponent lineup source:** `build.py:147–177` populates `today_lineup = {"home": [...], "away": [...]}` from the MLB Stats API `game/{pk}/boxscore` endpoint. Each entry has `{"id": pid, "name": ..., "pos": ...}`. Section picks the opposing side based on `is_home` check identical to `sections/scouting.py:135`.
- **Section registration:** `build.py:16–25` alphabetical imports, `build.py:898` `scout_html = sections.scouting.render(briefing)`, and the `_visible_sections` tuple + `_num` dict drive auto-numbering. Adding the new section between scouting and form guide means: new `import sections.matchup`, new `matchup_html = sections.matchup.render(briefing)` call, new `(section_id, html)` entry in `_visible_sections`, new `<section>` block in the page envelope.
- **Tier classes:** `style.css` already defines `.t-elite` (green #8bc48f), `.t-solid` (gold var), `.t-rough` (red #c87a74). These were introduced for Form Guide in the Savant phase-1 plan and are now reused across `.tempbox` and `.pitch-card`. The new section's grade pills and vulnerability dots use the same palette — no new colors.
- **Pitch-card grid:** `style.css` `.sp-arsenal` + `.pitch-card` block (added in Savant phase 2) is already the editorial treatment for pitch mix. The matchup card's arsenal strip reuses this grid at a smaller scale; no new component.
- **Test harness:** `tests/test_savant_fetch.py` is the blueprint — 25 tests, class-per-concern, fixtures inline, `--fixture` mode bypass verified. New tests for the matchup section follow the same structure: `TestParseBatterArsenal`, `TestMatchupMath`, `TestRenderMatchup`.
- **Golden snapshots:** `tests/fixtures/cubs_2026_04_05_expected.html` and `yankees_2026_04_05_expected.html` will need re-blessing once the new section renders. Same procedure as the Savant phase 1 and 2 re-blessings already documented in `tests/README.md`.
- **CLAUDE.md section-file rules (`/home/tooyeezy/morning-lineup/CLAUDE.md`):** never `from build import ...` at module top (build runs as `__main__`), import helpers inside function bodies when needed, read state exclusively from `briefing.*`. The new section file must follow these rules — they're the reason section-file imports look different from the rest of the codebase.

### Institutional Learnings

- **Schema-version the cache** (`build.py:517` `_SAVANT_SCHEMA = 2`). Adding `batter_arsenal` to the Savant result dict is an additive schema change; bump to 3 so yesterday's caches invalidate cleanly. The Savant phase 2 work already proved this pattern works — tests referenced `build._SAVANT_SCHEMA` rather than hardcoding the number, so the bump should propagate without test churn.
- **Save on build-time, not request-time.** Existing pattern (`build.py:684`) fetches all CSVs in one pass per build and writes one cache file. Follow it. Do not introduce per-hitter on-demand fetches.
- **Degrade gracefully.** `build.py:637` docstring: "Any network or parse failure degrades gracefully — the caller must tolerate missing data per player." The matchup section must render a believable card even when the batter arsenal fetch returned `{}`.
- **Stdlib only.** Per `CLAUDE.md`, no pip dependencies. CSV parsing stays on `csv.DictReader` + `io.StringIO`. Already proven at `build.py:485`.

### External References

Not needed. The Savant CSV endpoint shape was verified live during the brainstorm phase (see conversation above — Swanson row sample, 1,221 rows, 166 KB confirmed). The math is a straightforward weighted sum. The codebase has 3+ direct precedents for every implementation concern. Per `ce:plan` Phase 1.2 guidance, skip external research.

## Key Technical Decisions

- **One new CSV fetch, not per-player scraping.** The brainstorm considered (and the phase-1 plan originally documented) per-player Savant calls. The league-wide CSV is 166 KB and covers 389 batters in one call — O(1) lookups, zero extra infra. Rationale: matches the precedent already set at `build.py:661` where 5 league-wide CSVs replaced what would have been ~40 per-player calls.
- **League-average fallback at .310.** Derived from 2025 MLB league xwOBA across all qualifying pitch types. Stored as a module constant in `sections/matchup.py` so tests can import and assert it. Rationale: better to show a believable grade with a known floor than to drop the hitter or show "?".
- **Schema bump to 3** for the Savant cache. Additive change (new `batter_arsenal` key), but yesterday's cache wouldn't have it and sections would crash on `KeyError`. Precedent: the phase-2 bump from 1 → 2 when arsenal shape changed.
- **Section placement: between Scouting and Form Guide, not folded into Scouting.** Rationale: Scouting is about the pitcher's stuff in isolation; Matchup is about the stuff × the lineup. Conflating them would bloat the Scouting card and bury the money line. A standalone section also makes the editorial grade pills and the team grade the visual anchor readers scan for.
- **Conditional render same as Scouting** (`sections/scouting.py:86`). Section returns empty string if: no game today, no opponent starter known, or no opponent lineup posted. This reuses the exact off-day skip logic that Scouting has battle-tested.
- **Sample-size confidence via dots, not numbers.** PA thresholds: ● 50–75, ●● 75–100, ●●● 100–150, ●●●● 150+. Rationale: four visible dots are faster to parse than "n=127" and fit the editorial tone.
- **Team grade = average of individual expected xwOBAs, then band.** Simple aggregate — no weighting by lineup slot. Rationale: over-engineering; the per-hitter grades already tell the story and a weighted slot average adds opacity for negligible accuracy gain.
- **`--fixture` mode returns deterministic empty batter arsenal**, same as the existing Savant fetch at `build.py:644–647`. Rationale: keeps golden snapshots stable and isolates the math tests from the network.

## Open Questions

### Resolved During Planning

- **Can we join pitcher and batter arsenals on pitch code?** Yes — 7 types overlap (FF, SI, SL, CH, CU, ST, FC). Pitcher side also has FS, SV; batter side doesn't meet min-50 threshold for those. Resolved via league-average fallback.
- **Does MLB API give us opponent lineup?** Yes — `today_lineup[home/away]` already populated at `build.py:147`. The opposing side is picked with the same `is_home` check already in `sections/scouting.py:135`.
- **Which season to use for the batter CSV?** Current season (`season` variable already threaded through `fetch_savant_leaderboards` at `build.py:625`). Early 2026 (today is 2026-04-14) will have thin samples; accept that — the 50-pitch threshold plus confidence dots already communicate reliability to readers.

### Deferred to Implementation

- **Exact league-average xwOBA constant.** Pick a defensible value at implementation time by averaging the `est_woba` column of the batter CSV on the day of implementation. Document the source and date inline.
- **Dot threshold tuning.** 50/75/100/150 is a first cut. The implementer should compare dot distributions on a Cubs and a Yankees lineup and adjust if all dots come out the same tier.
- **Money-line copy exact phrasing.** "exploit: SL (2), FS (1)" is the design. The implementer may find a cleaner phrasing once the section renders in context. Acceptable alternatives: "keys: SL, FS" or "lean: SL (2)". Not a contract.
- **Whether to render a secondary "hard-hit" surface.** The batter CSV has `hard_hit_percent` per pitch. Useful for context but may bloat the card. Decide at implementation time based on how the primary row feels.

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

Data flow:

```
build.py load_all()
    └─> fetch_savant_leaderboards(season, today)
            ├─> existing: batter xstats, pitcher xstats, arsenal
            └─> NEW: batter_arsenal CSV  →  _parse_batter_arsenal()
                                        →  {pid: {pt: {pa, xwoba, whiff, hardhit}}}

briefing.data["savant"]["batter_arsenal"]
briefing.data["savant"]["arsenal"]  (now also with xwoba_allowed per pitch — R2)
briefing.data["today_lineup"]
briefing.data["next_games"]

        ↓

sections/matchup.py render(briefing)
    ├─> resolve opposing side, opposing starter pid, opposing arsenal  (existing helpers pattern from scouting)
    ├─> resolve own lineup (today_lineup[own_side])
    ├─> for each hitter: compute expected_xwOBA, vuln_tag, confidence_dots, letter_grade
    ├─> compute team_grade, exploit_counts
    └─> render card HTML (arsenal strip + lineup table + money line)
```

Math sketch (directional, not implementation):

```
expected_xwOBA(batter, pitcher):
    total = 0
    for each pitch pt in pitcher.arsenal:
        usage = pt.usage / 100
        batter_row = batter.arsenal.get(pt.code)
        if batter_row and batter_row.pa >= MIN_PA:
            x = batter_row.xwoba
        else:
            x = LEAGUE_AVG_XWOBA  # ~.310
        total += usage * x
    return total

vuln_tag(batter, pitcher):
    for each pitch pt in pitcher.arsenal:
        gap = (batter.xwoba_vs[pt.code] or LEAGUE_AVG) - LEAGUE_AVG
        weighted_gap[pt.code] = pt.usage * gap
    worst = argmax(weighted_gap)  # most negative for vuln, most positive for safe
    dots = confidence_dots(batter.pa_vs[worst])
    return (worst, dots)
```

## Implementation Units

- [ ] **Unit 1: Extend Savant fetch to pull batter arsenal CSV**

**Goal:** Add the 6th Savant CSV fetch (batter pitch-arsenal-stats), parse it into a per-batter per-pitch-type map, and surface it on the result dict. Schema bump 2 → 3.

**Requirements:** R1, R11

**Dependencies:** None (builds on existing infrastructure at `build.py:625`)

**Files:**
- Modify: `build.py` — add URL to `urls` dict at `build.py:661`, add new `_parse_batter_arsenal()` near existing `_parse_savant_csv()` at `build.py:485`, add `batter_arsenal` key to result dict at `build.py:686`, bump `_SAVANT_SCHEMA` at `build.py:517` from 2 to 3
- Test: `tests/test_savant_fetch.py` — add `TestParseBatterArsenal` class alongside existing `TestParseSavantCsv`

**Approach:**
- New endpoint URL follows the existing `lbase` template: `f"{lbase}/pitch-arsenal-stats?year={season}&type=batter&min=50&csv=true"`
- Parser returns `{pid_str: {pitch_type: {pa: int, xwoba: float, whiff: float, hardhit: float}}}` — different shape from `_parse_savant_csv` which assumes one row per player
- Fixture mode (`--fixture` in `sys.argv`) returns empty `{}` for the new key, matching the existing pattern at `build.py:644`
- Cache file schema is unchanged in location (`data/cache/savant/leaderboards-{season}-{date}.json`) but the new key triggers schema mismatch so prior-day caches naturally invalidate via the existing check at `build.py:653`

**Patterns to follow:**
- `build.py:485` `_parse_savant_csv()` — BOM stripping, dict reader, type coercion
- `build.py:625` `fetch_savant_leaderboards()` — URL dict, `_get` helper, in-memory cache key
- `tests/test_savant_fetch.py` — `TestParseSavantCsv` has the exact test structure to mirror

**Test scenarios:**
- Happy path: parse a minimal 2-batter × 3-pitch CSV → map returns correct nested dict with PA, xwOBA, whiff, hardhit
- Happy path: one batter has 4 pitch types, another has 2 → map reflects both shapes correctly
- Edge case: empty CSV body → returns `{}`, does not raise
- Edge case: header-only CSV → returns `{}`
- Edge case: row with missing `est_woba` value → that pitch entry is either omitted or stored as `None` (document the choice in the test)
- Edge case: BOM-prefixed CSV → first column parses correctly (same as existing BOM test at `tests/test_savant_fetch.py`)
- Integration: `fetch_savant_leaderboards` in fixture mode returns a dict with `batter_arsenal: {}` key present
- Integration: schema bump from 2 → 3 invalidates a schema-2 cache file on disk and triggers refetch (mock the network to verify the refetch happens)
- Integration: happy-path fetch writes cache file containing `"schema": 3` and `"batter_arsenal"` key

**Verification:**
- All existing `test_savant_fetch.py` tests still pass (schema bump updated via `build._SAVANT_SCHEMA` reference, not hardcoded)
- New parser tests pass
- Running `python3 build.py --team cubs` produces a cache file at `data/cache/savant/leaderboards-2026-*.json` whose top-level keys include `batter_arsenal`

---

- [ ] **Unit 2: Store xwOBA-allowed on pitcher arsenal entries**

**Goal:** Extend `_build_savant_arsenal()` at `build.py:519` to carry `xwoba_allowed` for each pitch, pulled from the `est_woba` column already present in the `arsenal_stats` CSV we fetch at `build.py:670`.

**Requirements:** R2

**Dependencies:** None (purely additive — no schema change beyond what Unit 1 bumps)

**Files:**
- Modify: `build.py` — `_build_savant_arsenal()` near `build.py:519`, add one field to each pitch dict in the per-pitcher list
- Test: `tests/test_savant_fetch.py` — extend `TestBuildSavantArsenal` assertions

**Approach:**
- `arsenal_stats` CSV already has `est_woba` alongside `pitch_usage` and `whiff_percent` — just thread it through the merge
- Existing per-pitch entries look like `{pitch, name, usage, velo, spin, whiff}`; add `xwoba_allowed`
- Matchup section will consume this in Unit 4, but it's useful on its own for scouting enhancements in a future plan

**Patterns to follow:**
- `build.py:519` existing merge logic — just one more column to read from the stats row

**Test scenarios:**
- Happy path: merge includes `xwoba_allowed` for each pitch when `est_woba` is present in stats CSV
- Edge case: `est_woba` missing or empty for one pitch → that pitch's `xwoba_allowed` is `None`, other pitches unaffected
- Edge case: pitcher present in stats but not in speed/spin CSVs → `xwoba_allowed` still populated (don't gate on the other two files)

**Verification:**
- Existing `TestBuildSavantArsenal` tests still pass after adding `xwoba_allowed` assertions to the happy-path fixture
- Inspecting a live `leaderboards-*.json` cache file shows `xwoba_allowed` populated on Skenes's entries (happy-path manual spot check)

---

- [ ] **Unit 3: Matchup section scaffold + conditional render + opponent lineup resolution**

**Goal:** Create `sections/matchup.py` with a `render(briefing)` that returns empty string when any precondition fails, and otherwise resolves the opposing starter pid, opposing arsenal, and own lineup. No math or HTML yet — just the plumbing.

**Requirements:** R8, R9

**Dependencies:** Unit 1 (needs `batter_arsenal` on briefing.data["savant"])

**Files:**
- Create: `sections/matchup.py`
- Test: `tests/test_matchup_section.py` (new file)

**Approach:**
- Copy the top-of-file pattern from `sections/scouting.py` (imports, `_CT` zoneinfo fallback, `_abbr`, `_logo` helpers — each section file inlines its own small helpers per CLAUDE.md section-file rules)
- `render(briefing)` reads `briefing.data["savant"]`, `briefing.data["today_lineup"]`, `briefing.data["next_games"]`, `briefing.team_id`
- Early-return empty string if: no `next_games`, no savant data, no opposing starter in scout data, or opponent lineup is empty
- Resolve own side from `next_games[0].teams.{home,away}.team.id` vs `briefing.team_id` (same pattern as `sections/scouting.py:135`)
- Resolve own lineup list as `today_lineup[own_side]`; opposing starter pid comes from `briefing.data["scout_data"]["opp_sp"]["id"]`
- Resolve opposing arsenal as `briefing.data["savant"]["arsenal"][str(opp_sp_pid)]`
- For now, return a placeholder HTML string with the starter name and lineup count — full render lands in Unit 5

**Patterns to follow:**
- `sections/scouting.py:77–151` — especially the early-return on `if not scout_data` at line 86 and the `is_home` branch at line 135
- `/home/tooyeezy/morning-lineup/CLAUDE.md` section-file rules: no top-level `from build import`, read state only through `briefing.*`

**Test scenarios:**
- Happy path: briefing with full game, lineup, arsenal → returns non-empty HTML string containing starter name and lineup count
- Edge case: `next_games` empty → returns empty string
- Edge case: `savant` missing → returns empty string
- Edge case: `scout_data` missing `opp_sp` → returns empty string
- Edge case: opponent lineup empty (home/away both `[]`) → returns empty string
- Edge case: opposing starter not in `arsenal` map (new pitcher, no Savant rows yet) → returns empty string (don't fabricate a card from a league-average pitcher)
- Integration: when Cubs are home, own lineup comes from `today_lineup["home"]`; when Cubs are away, from `today_lineup["away"]`

**Verification:**
- All new `test_matchup_section.py` scaffolding tests pass
- `python3 build.py --team cubs` runs without error (section not yet wired into page, so HTML won't appear — that's Unit 6)

---

- [ ] **Unit 4: Matchup math — expected xwOBA, vuln tag, grade, dots**

**Goal:** Implement the pure-function core of the section — given an opposing arsenal and a batter arsenal map, compute per-hitter expected xwOBA, vulnerability tag, confidence dots, and letter grade. Team grade aggregate and exploit counter.

**Requirements:** R3, R4, R5, R6, R7

**Dependencies:** Unit 3 (needs a section file to hold the functions)

**Files:**
- Modify: `sections/matchup.py` — add `_expected_xwoba`, `_vuln_tag`, `_letter_grade`, `_team_grade`, `_exploit_counts`, plus the `LEAGUE_AVG_XWOBA` module constant
- Test: `tests/test_matchup_section.py` — add `TestMatchupMath` class

**Execution note:** Write failing unit tests for each pure function before implementing — the math is the core product claim and deserves characterization up front.

**Approach:**
- `LEAGUE_AVG_XWOBA = 0.310` as module-level constant (test imports it)
- `_expected_xwoba(pitcher_arsenal, batter_arsenal_map)` returns a float — iterates pitcher pitches, weights each by `usage/100 * (batter xwOBA for that pitch, or league avg)`, sums
- `_vuln_tag(pitcher_arsenal, batter_arsenal_map)` returns `(pitch_code, dots_int, is_vuln_bool)` — computes weighted gap per pitch, picks worst/best by absolute value, returns None when batter has zero per-pitch data
- `_letter_grade(expected_xwoba)` returns one of `"A"`, `"B"`, `"C"`, `"D"` using the R4 bands
- `_team_grade(grades_list)` returns a letter from the mean expected xwOBA
- `_exploit_counts(lineup_tags, pitcher_arsenal)` returns an ordered list of `(pitch_code, vuln_count)` sorted by the pitcher's usage of that pitch (so "exploit: SL (2)" shows the pitch the pitcher throws most, not alphabetical)
- `_dots(pa)` returns 1–4 from the thresholds in the Decisions section
- All functions are pure — no IO, no HTML, no `briefing` access

**Patterns to follow:**
- `sections/headline.py` tier threshold constants and helper-per-metric structure introduced in Savant phase 1

**Test scenarios:**
- Happy path: pitcher throws 50% FF (batter xwOBA .400 vs FF) + 50% SL (batter xwOBA .200 vs SL) → expected_xwoba ≈ .300
- Happy path: pitcher throws 40% FF / 30% SL / 30% FS (batter has no FS row) → FS slot uses league avg .310
- Edge case: batter arsenal map is empty → expected equals league avg (pitcher throws 100% of pitches against league avg)
- Edge case: pitcher throws 100% of one pitch the batter has no row for → expected equals league avg
- Edge case: batter has a row for every pitcher pitch → fallback never fires
- Edge case: pitcher arsenal contains a pitch with `usage: 0` or `usage: None` → that pitch contributes zero, does not raise
- Grade boundaries: expected = .360 → A, .320 → B, .290 → C, .289 → D (test all four band edges + one value inside each band)
- Vuln tag: given a clear worst pitch (large negative gap × high usage), returns that pitch code with confidence dots matching PA
- Vuln tag: given all pitches at league average, returns `None` (no story to tell — test that the section knows when to shut up)
- Vuln tag: batter has no per-pitch data at all → returns `None`
- Dots: PA 49 → 0 dots (sub-threshold), 50 → 1, 75 → 2, 100 → 3, 150 → 4, 300 → 4 (capped)
- Team grade: all 9 hitters A → team grade A; mix of A/B/C/D → team grade computed from mean expected xwOBA, not mean of letters
- Exploit counts: lineup where 2 hitters are vulnerable to SL and 1 to FS → returns `[("SL", 2), ("FS", 1)]` ordered by pitcher usage of each pitch, not alphabetical

**Verification:**
- All `TestMatchupMath` tests pass
- Functions are importable from `sections.matchup` without raising (no circular imports, no top-level `from build import`)

---

- [ ] **Unit 5: Matchup card HTML render**

**Goal:** Produce the final HTML for the Matchup Read card — arsenal strip, lineup table with per-row grade pills and vulnerability tags, team grade, money line.

**Requirements:** R4, R5, R6, R7, R10

**Dependencies:** Units 3 and 4

**Files:**
- Modify: `sections/matchup.py` — flesh out `render(briefing)` to emit the full card
- Modify: `style.css` — add `.matchup-read` block and scoped descendants; reuse existing tier classes
- Test: `tests/test_matchup_section.py` — add `TestRenderMatchup` class

**Approach:**
- Render order: `<section>` wrapper (numbered via build.py `_num` — Unit 6), then arsenal strip (reuse `.pitch-card` grid pattern from `sections/scouting.py:65` `_render_arsenal`), then lineup table, then team grade + money line footer
- Lineup table: one row per hitter from `today_lineup[own_side]`. Columns: batting order, name, position, tag line, grade pill
- Tag line: `vuln: SL ●●●` or `safe: CH ○○` or `—` if no story; color via tier class on the pitch code
- Grade pill: right-aligned letter with tier color (`.t-elite` for A, `.t-solid` for B, `.t-rough` for C/D); serif italic matching Form Guide treatment
- For hitters with zero Savant coverage, render `—` in both tag and grade columns (no fabrication — R6)
- Team grade footer: `TEAM GRADE: B- · exploit: SL (2), FS (1)` — single line, muted paper color except for the letter and pitch codes
- All user-facing strings via `html.escape()` (per `CLAUDE.md` escaping rule)

**Patterns to follow:**
- `sections/scouting.py:65–74` `_render_arsenal` — exact f-string pattern for pitch cards
- `sections/headline.py` Form Guide tier-colored primary spans (the `.primary.t-elite` treatment introduced in Savant phase 1)
- `sections/scouting.py:110` data table structure for the lineup table
- `style.css` existing `.tempbox li` grid pattern (Form Guide row layout) is a good reference for the per-hitter row

**Test scenarios:**
- Happy path: render a Cubs lineup vs Skenes-like arsenal → HTML contains all 9 names, arsenal strip with top pitches, team grade letter, money line with "exploit:" prefix
- Happy path: one hitter has clear SL vulnerability → row contains `vuln: SL` with tier-colored pitch code and correct dot count
- Happy path: one hitter handles FF well and pitcher throws FF heavy → row contains `safe: FF` with the `safe` styling
- Edge case: one hitter has no Savant data → row shows `—` in both tag and grade columns, renders without raising
- Edge case: no hitter has a clear vuln (all expected ≈ league avg) → each row shows `—`; team grade is C-ish; money line shows empty exploit list or a neutral phrasing
- Edge case: arsenal has 2 pitches only (rare opener usage) → arsenal strip has 2 cards, math still works
- Integration: rendered HTML passes through `html.escape()` for any API-sourced strings (names with apostrophes like "O'Hearn" don't break)
- Integration: section output is a single string, not a tuple — matches the `sections/scouting.py` contract and survives the `build.py:898` assignment pattern

**Verification:**
- All `TestRenderMatchup` tests pass
- Hand inspection of `python3 build.py --team cubs --fixture tests/fixtures/cubs_2026_04_05.json` HTML output shows a visually credible card in the right position
- No CSS selectors defined outside `.matchup-read` scope (except tier classes which are already shared)

---

- [ ] **Unit 6: Wire section into page, re-bless snapshots**

**Goal:** Register `sections.matchup` in `build.py` between Scouting and Form Guide; update `_visible_sections` and the page envelope; re-bless the two golden snapshot fixtures.

**Requirements:** R8, R11

**Dependencies:** Units 3, 4, 5

**Files:**
- Modify: `build.py` — add `import sections.matchup` near `build.py:16–25`, add `matchup_html = sections.matchup.render(briefing)` near `build.py:898` (between scout and form guide), add entry to `_visible_sections` tuple, add `<section id="matchup">` block to the page envelope f-string with `<span class="num">{_num.get("matchup", "")}</span>`, add TOC `<li>` entry
- Modify: `tests/fixtures/cubs_2026_04_05_expected.html` — re-blessed
- Modify: `tests/fixtures/yankees_2026_04_05_expected.html` — re-blessed

**Approach:**
- Follow the exact "adding or reordering sections" procedure documented in `/home/tooyeezy/morning-lineup/CLAUDE.md` — this is the canonical reference
- Since `--fixture` mode returns empty Savant data, the matchup section will correctly return empty string for the frozen test dates (game was played 2026-04-05 but fixture has no Savant data), meaning snapshots may not diff at all — verify this before re-blessing. If the section does emit HTML with fixture data, re-bless both fixtures and diff the output for sanity before committing
- Run `python3 tests/snapshot_test.py` before and after re-blessing to confirm only the expected diff

**Execution note:** This is integration glue — no new logic. The risk is section ordering and number-dict coupling; verify by comparing rendered page against the existing Scouting → Form Guide handoff visually.

**Patterns to follow:**
- `build.py:16–25` alphabetical import block
- `build.py:888–901` section render call block
- `build.py` page envelope template (grep for `id="scout"` to find the pattern)
- `tests/README.md` re-bless procedure (documented during Savant phase 1 and 2)

**Test scenarios:**
- Integration: `python3 tests/snapshot_test.py` passes after re-blessing with expected diff (new section present) and no unexpected diffs in adjacent sections
- Integration: `python3 build.py --team cubs` produces an HTML file containing `id="matchup"` when Savant data is present
- Integration: `python3 build.py --team cubs --fixture tests/fixtures/cubs_2026_04_05.json` produces HTML where the matchup section is empty (fixture has no Savant data) and the page numbering still looks correct

**Verification:**
- All 30 team builds succeed: `python3 build.py --team cubs`, a spot-check of 2 other teams (Yankees, Dodgers) complete without error
- Snapshot test green
- Visual spot-check of the Cubs page: matchup section renders between Scouting and Form Guide, numbered correctly, on a day with a real game

---

## System-Wide Impact

- **Interaction graph:** `build.py load_all()` → `fetch_savant_leaderboards()` now fetches one additional CSV and writes one additional top-level key on the Savant result dict. The Savant schema bump triggers a one-time cache refresh across all teams on next build — acceptable, ~20s per team per day. No other upstream callers of `fetch_savant_leaderboards` exist; the in-memory cache at `build.py:640` is keyed on season+date and rebuilds naturally.
- **Error propagation:** New fetch is additive and wrapped in the existing `_get()` helper at `build.py:675`, which already catches network errors and returns empty string. Parser treats empty body as `{}`. Section's early-return covers the "no data" path. No new error surfaces.
- **State lifecycle risks:** Cache file is daily and idempotent. Schema bump invalidates prior-day caches cleanly via the existing check at `build.py:653`. No partial-write risk — existing code uses `cache_path.write_text` which is atomic enough for this use case (documented pattern at `build.py:699`).
- **API surface parity:** The matchup section is a new reader surface. No changes to player-card.js, live.js, or landing.html. Player cards will continue to show the Savant phase-1 and phase-2 metrics they already show; batter-per-pitch data is intentionally *not* wired into player cards in this plan (scope boundary — follow-up opportunity).
- **Integration coverage:** Unit 1's schema-bump cache-invalidation test is the key cross-layer scenario. Unit 6's snapshot tests cover the section → page wiring. Unit 5's render test covers the section → briefing coupling.
- **Unchanged invariants:** Scouting Report section (`sections/scouting.py`), Form Guide section (`sections/headline.py` `_render_hot_cold`), player card component (`player-card.js`), landing page, all team configs, CSS tier class definitions, and the Savant fetch signature (`fetch_savant_leaderboards(season, today) -> dict`) all remain unchanged. The new section reads from existing briefing fields and one new Savant result key; it does not modify any other section's inputs or outputs.

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Batter CSV endpoint changes URL or schema | Wrapped in the existing `_get()` try/except at `build.py:675`; parser treats empty body as `{}`; section degrades to empty string. Same graceful-degrade pattern that protected Savant phase 1 and 2 |
| Early-season sample sizes are tiny (fewer than 389 batters have 50+ pitches by mid-April) | Confidence dots (R5) explicitly communicate sample weight to readers; hitters below the 50-pitch threshold simply show `—` (R6) |
| Schema bump breaks cache for all teams for one day | Acceptable — Savant phase 2 already paid this cost; 30 × ~20s rebuild at worst once |
| Pitch-code join misses FS/SV | League-average fallback for those codes; verified necessary during brainstorm (Skenes throws 13.5% splitters, no batter CSV row for FS) |
| Handedness is conflated (LHP sliders ≠ RHP sliders for some batters) | Scope boundary — explicitly v2. Accept the noise; the dots + tier colors already communicate "this is a read, not a guarantee" |
| Rendered card overwhelms the page visually | Designed to match existing `.pitch-card` and Form Guide typography exactly; no new color tokens. Unit 5 visual verification step catches this before commit |
| Team grade letter misleads when lineup is partial (only 7 of 9 hitters have data) | Team grade is computed over whatever hitters had data; the `—` rows communicate the missing coverage. Document this in the section docstring |
| Fixture-based snapshot tests don't exercise real Savant data | Unit 5 includes an explicit non-fixture spot-check; Unit 4's pure-function tests cover the math independently |
| Section placement disrupts TOC numbering readers are used to | Unit 6's snapshot re-bless catches any TOC/numbering diff; auto-numbering via `_num` dict means no manual renumbering needed |
| Early-season MLB lineups may not post until shortly before first pitch | Existing `today_lineup` fetch at `build.py:147` already handles this — if lineup is empty, section returns empty string (R9) and rebuilds later pick it up when evening edition runs |

## Documentation / Operational Notes

- No runbook changes. Daily build cadence already produces the Savant cache; new section piggybacks on it.
- Re-bless procedure already documented in `tests/README.md` from Savant phase 1 and 2.
- Commit message should reference this plan path: `docs/plans/2026-04-14-002-feat-matchup-read-plan.md`.

## Sources & References

- **Origin:** Direct user request in conversation (2026-04-14); no `ce:brainstorm` requirements doc
- **Prior plan (foundation):** `docs/plans/2026-04-14-001-feat-savant-advanced-stats-plan.md` — Savant infrastructure this plan builds on
- **Related code:**
  - `build.py:485` `_parse_savant_csv()` — CSV parser pattern
  - `build.py:517` `_SAVANT_SCHEMA` — cache schema versioning
  - `build.py:519` `_build_savant_arsenal()` — per-pitcher merge logic (Unit 2 extends this)
  - `build.py:625` `fetch_savant_leaderboards()` — daily fetch orchestration (Unit 1 extends this)
  - `build.py:147` `today_lineup` population — opponent lineup source
  - `sections/scouting.py:77` `render()` — section template to mirror
  - `sections/scouting.py:33` `_render_arsenal()` — pitch-card grid pattern
  - `sections/headline.py` `_render_hot_cold()` — tier-colored primary span pattern
  - `style.css` `.pitch-card`, `.t-elite`, `.t-solid`, `.t-rough` — reused classes
  - `/home/tooyeezy/morning-lineup/CLAUDE.md` — section-file import rules and "adding a section" procedure
- **External endpoint (verified live in brainstorm):** `https://baseballsavant.mlb.com/leaderboard/pitch-arsenal-stats?type=batter&year={season}&min=50&csv=true`
