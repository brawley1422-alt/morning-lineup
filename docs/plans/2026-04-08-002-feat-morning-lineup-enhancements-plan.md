---
title: "feat: Morning Lineup Enhancement Suite"
type: feat
status: completed
date: 2026-04-08
origin: docs/ideation/2026-04-08-open-ideation.md
---

# feat: Morning Lineup Enhancement Suite

## Overview

Seven improvements to the Morning Lineup project, ordered by dependency and leverage. The first four are low-complexity infrastructure and content wins that unlock future capabilities. The remaining three add new features.

## Problem Frame

Morning Lineup generates a rich daily Cubs briefing but has several compounding gaps: the data it fetches is discarded after rendering (no trend analysis possible), the page rebuilds only once daily (stale by game time), the CSS is trapped in a Python string (DX friction), and the "This Day in Cubs History" section is empty 85% of the year. Additionally, it lacks prospect-level tracking for minor leagues, isn't installable as a phone app, and has no editorial voice.

(see origin: `docs/ideation/2026-04-08-open-ideation.md`)

## Requirements Trace

- R1. Persist daily structured data as JSON alongside HTML archive
- R2. Trigger a second build after the Cubs game goes Final
- R3. Backfill history.json to cover all 366 calendar dates
- R4. Extract CSS from build.py into a standalone file, inlined at build time
- R5. Tag top Cubs prospects in minor league boxscores
- R6. Make the site installable as a PWA with offline support
- R7. Generate a 3-4 sentence editorial lede via Claude API

## Scope Boundaries

- No database, no server — stays static + stdlib
- No team-agnostic config (Cubs-only focus preserved)
- No RSS, email, or push notifications
- Evening edition is cron/systemd-based, not a background daemon
- Claude editorial lede uses the Anthropic Python SDK (single new dependency) or falls back to local Ollama
- Prospect list is manually curated, not auto-discovered

## Context & Research

### Relevant Code and Patterns

- `build.py:55-210` — `load_all()` returns a rich dict with 18 keys; currently discarded after rendering
- `build.py:1080-1340` — CSS as `r"""` string constant, injected via `<style>{CSS}</style>` at line 1359
- `build.py:1523-1529` — `__main__` block: fetch, render, write. Clean entry point
- `deploy.py` — archives HTML to `archive/YYYY-MM-DD.html` via GitHub Contents API, then pushes new `index.html`
- `history.json` — 55 of 366 dates populated, keyed by `MM-DD`, entries are `[{year, text}]`
- `build.py:1068-1075` — `render_history()` silently returns `""` when no entries exist
- `build.py:170-185` — minor league boxscore fetch loop, already extracts top performers
- `scorecard/` — separate CSS file pattern (`styles.css`) already proven
- `live.js` — adaptive polling, game state awareness, visibility API pause

### Institutional Learnings

- Prior ideation (2026-04-07) ranked Season Data Ledger #2, Evening Edition #3, PWA #5 — all resurfaced
- Phased delivery with explicit scope boundaries prevents gold-plating (observed across brainstorm docs)
- Zero-dependency constraint is a project strength; new deps should be justified

## Key Technical Decisions

- **Data ledger location:** `data/YYYY-MM-DD.json` in repo root (mirrors `archive/` convention), deployed to GitHub via same `deploy.py` pattern
- **CSS extraction:** Read `style.css` at build time via `Path.read_text()` and inline into `<style>` tag. Same single-file HTML output. No behavioral change
- **Evening edition trigger:** systemd timer or cron that polls Cubs game status, fires `build.py + deploy.py` when Final. Separate script (`evening.py`) to avoid adding polling logic to build.py
- **History backfill approach:** Generate via Claude in a one-time script, output to `history.json`, human review before commit. Not part of the daily build pipeline
- **Prospect data:** Static `prospects.json` with `{id, name, position, rank, level}`. Cross-referenced in `render_minors()` at boxscore extraction time
- **PWA scope:** `manifest.json` + `sw.js` caching `index.html` and `live.js`. Service worker uses cache-first-then-network strategy. No push notifications
- **Claude lede:** Call Anthropic API (or local Ollama as fallback) with a summary of `load_all()` output. Insert as first element after masthead. Graceful fallback: if API fails, omit the lede silently

## Open Questions

### Resolved During Planning

- **Should data ledger go in repo or separate storage?** Repo (`data/` directory) — matches archive pattern, GitHub Pages serves it, no new infrastructure
- **How to handle date serialization in JSON?** Use `.isoformat()` for date objects. The dict from `load_all()` contains `date` objects that need conversion
- **Should evening edition overwrite or create a separate page?** Overwrite `index.html` — same URL, richer content. Archive already captures the morning snapshot

### Deferred to Implementation

- Exact systemd timer unit configuration (depends on user's existing cron/PM2 setup)
- Claude API model selection and prompt tuning for editorial lede
- Which Ollama model to use as local fallback for lede generation
- Exact prospect list curation (names, ranks, levels for 2026 season)

## Implementation Units

- [x] **Unit 1: Extract CSS to standalone file**

  **Goal:** Move CSS from build.py string constant to `style.css`, read and inline at build time

  **Requirements:** R4

  **Dependencies:** None — foundation unit, makes all future CSS work easier

  **Files:**
  - Create: `style.css`
  - Modify: `build.py`

  **Approach:**
  - Cut the CSS string content (lines 1080-1340) from build.py into `style.css`
  - Replace `CSS = r"""..."""` with `CSS = (Path(__file__).parent / "style.css").read_text()`
  - Keep the `<style>{CSS}</style>` injection in `page()` unchanged — output is identical
  - Delete the dead `template.html` file while here (confirmed unused in CLAUDE.md)

  **Patterns to follow:**
  - `scorecard/styles.css` — separate CSS file already exists in the project

  **Test scenarios:**
  - Happy path: `python3 build.py` produces identical HTML output before and after extraction (diff the output)
  - Edge case: `style.css` missing — build should fail with a clear error, not silently produce a page with no styles

  **Verification:**
  - `diff` of generated `index.html` before/after shows zero changes
  - build.py is ~260 lines shorter
  - `style.css` opens with syntax highlighting in any editor

- [x] **Unit 2: Season Data Ledger**

  **Goal:** Persist `load_all()` output as `data/YYYY-MM-DD.json` during each build

  **Requirements:** R1

  **Dependencies:** None (independent of Unit 1, can run in parallel)

  **Files:**
  - Create: `data/` directory (first run)
  - Modify: `build.py` (main block)
  - Modify: `deploy.py` (push data file to GitHub)

  **Approach:**
  - After `data = load_all()`, serialize to JSON with a helper that converts `date`/`datetime` objects via `.isoformat()`
  - Write to `data/YYYY-MM-DD.json` using today's date
  - In `deploy.py`, after archiving HTML, also push the day's JSON file via the same GitHub Contents API pattern
  - Skip writing if `data/` file for today already exists (idempotent re-runs)

  **Patterns to follow:**
  - `deploy.py:46-57` — archive PUT pattern with 422 handling for already-exists

  **Test scenarios:**
  - Happy path: After `build.py` runs, `data/2026-04-08.json` exists and is valid JSON containing expected keys (`today`, `standings`, `cubs_game`, etc.)
  - Edge case: Date objects serialize correctly (no `TypeError: Object of type date is not JSON serializable`)
  - Edge case: Re-running build.py on the same day overwrites the JSON file (latest data wins)
  - Integration: `deploy.py` pushes the JSON file to GitHub alongside the HTML archive

  **Verification:**
  - `data/YYYY-MM-DD.json` exists after build
  - JSON is parseable and contains all 18 keys from `load_all()`
  - File appears in GitHub repo after deploy

- [x] **Unit 3: Auto-populate Cubs History**

  **Goal:** Backfill `history.json` from 55 to 366 dates using Claude

  **Requirements:** R3

  **Dependencies:** None (independent, one-time script)

  **Files:**
  - Create: `scripts/backfill_history.py`
  - Modify: `history.json`

  **Approach:**
  - Write a one-time script that iterates through all 366 calendar dates (MM-DD)
  - For each date missing from history.json, prompt Claude with: "List 2-3 notable events in Chicago Cubs history that happened on [month day]. Include the year. Focus on memorable games, milestones, trades, and franchise moments. Be factually accurate."
  - Merge responses into the existing history.json, preserving existing hand-curated entries
  - Use the Anthropic Python SDK (pip install anthropic) for the backfill script only — build.py stays stdlib-only
  - Output a review file (`scripts/history_review.json`) for manual fact-checking before merging

  **Patterns to follow:**
  - Existing `history.json` format: `{"MM-DD": [{"year": YYYY, "text": "..."}]}`

  **Test scenarios:**
  - Happy path: After running, history.json has entries for all 366 dates
  - Edge case: Existing hand-curated entries are preserved (not overwritten)
  - Edge case: Dates with no notable Cubs events get at least 1 entry (early franchise history, spring training, etc.)
  - Error path: API failure on a specific date logs a warning and continues with remaining dates

  **Verification:**
  - `python3 -c "import json; d=json.load(open('history.json')); print(len(d))"` returns 366
  - Spot-check 10 random dates for factual accuracy
  - Existing 55 entries unchanged

- [x] **Unit 4: Evening Edition**

  **Goal:** Auto-rebuild the page after the Cubs game goes Final

  **Requirements:** R2

  **Dependencies:** None (uses existing build.py + deploy.py as-is)

  **Files:**
  - Create: `evening.py`

  **Approach:**
  - Script that polls the MLB Schedule API for today's Cubs game status every 5 minutes
  - When `abstractGameState` flips to `Final`, wait 2 minutes (let stats finalize), then run `build.py` followed by `deploy.py` via `subprocess.run()`
  - Exit after triggering the rebuild (one-shot, not a daemon)
  - Deploy via systemd timer that starts `evening.py` at 6 PM CT daily and lets it run until midnight or until it triggers
  - Include a `--dry-run` flag that skips the actual build/deploy
  - Stdlib only — same constraints as build.py

  **Patterns to follow:**
  - `build.py:103-112` — `find_cubs_final()` pattern for checking game status
  - `live.js` polling pattern (check status, act on state change)

  **Test scenarios:**
  - Happy path: Cubs game goes Final at 10:15 PM → evening.py detects it within 5 minutes, triggers build + deploy
  - Edge case: No Cubs game today → script exits cleanly after checking schedule
  - Edge case: Cubs game is already Final when script starts (afternoon game) → triggers immediately
  - Edge case: Doubleheader — waits for the last game to go Final
  - Error path: MLB API timeout → retries on next poll interval, doesn't crash
  - Edge case: `--dry-run` prints what it would do without executing

  **Verification:**
  - Run with `--dry-run` on a day the Cubs played — confirms it detects Final status
  - After real trigger, GitHub Pages shows updated content with fresh game recap

- [x] **Unit 5: Prospect Watch**

  **Goal:** Tag top Cubs prospects in minor league boxscores with rank badges

  **Requirements:** R5

  **Dependencies:** None (can be built independently)

  **Files:**
  - Create: `prospects.json`
  - Modify: `build.py` (load prospects, cross-reference in `render_minors()`)
  - Modify: `style.css` (prospect badge styling)

  **Approach:**
  - Create `prospects.json`: array of `{id, name, position, rank, level}` for top 15-20 Cubs prospects
  - In `load_all()`, load prospects.json into the data dict
  - In `render_minors()`, when extracting top performers from boxscores, check if player ID is in the prospect list
  - If prospect match, add a badge: `<span class="prospect-tag">#3</span>` next to the player name
  - Prospect IDs come from the boxscore player data (same endpoint already fetched)

  **Patterns to follow:**
  - `history.json` — static JSON data file loaded at build time
  - `build.py:1022` — existing top performer scoring: `sc = h + 3 * hr + rbi`

  **Test scenarios:**
  - Happy path: A ranked prospect appears in a boxscore → name shows with rank badge
  - Edge case: Prospect not in that day's boxscore → no badge, no error
  - Edge case: Prospect promoted to a different level → still matched by player ID regardless of level
  - Edge case: prospects.json missing → build proceeds normally, no badges (graceful degradation)

  **Verification:**
  - Build output shows prospect badges next to ranked players in minor league section
  - Non-prospect players render normally (no regression)

- [x] **Unit 6: PWA + Offline**

  **Goal:** Make Morning Lineup installable as a phone app with offline cached last edition

  **Requirements:** R6

  **Dependencies:** Unit 1 (CSS extraction — service worker needs to know which files to cache)

  **Files:**
  - Create: `manifest.json`
  - Create: `sw.js`
  - Create: `icons/` directory with app icons (192px and 512px)
  - Modify: `build.py` (add manifest link and SW registration to HTML head)

  **Approach:**
  - `manifest.json`: name "The Morning Lineup", short_name "Lineup", theme_color `#0d0f14`, background_color `#0d0f14`, display `standalone`, start_url `/morning-lineup/`, icons
  - `sw.js`: cache-first strategy for `index.html`, `live.js`, and icon files. Network-first for API calls (don't cache API responses in SW — the data ledger handles persistence). On install, pre-cache the shell. On activate, clean old caches
  - Add `<link rel="manifest" href="manifest.json">` and SW registration script to HTML head in `page()` function
  - App icons: generate a simple Cubs-themed icon (C on dark blue background) or use a placeholder

  **Patterns to follow:**
  - `scorecard/index.html` — already has `<meta name="theme-color">` and viewport meta

  **Test scenarios:**
  - Happy path: On mobile Chrome, "Add to Home Screen" prompt appears → installs as standalone app with correct name and icon
  - Happy path: After installing, open app in airplane mode → last cached edition loads
  - Edge case: live.js API calls fail gracefully when offline (already handles this with try/catch)
  - Edge case: New build deploys → service worker updates cache on next visit

  **Verification:**
  - Chrome DevTools → Application → Manifest shows valid manifest
  - Lighthouse PWA audit passes core checks
  - Offline load shows cached content (not browser error page)

- [x] **Unit 7: Claude Editorial Lede**

  **Goal:** Generate a 3-4 sentence editorial paragraph summarizing the day's action, inserted at the top of the page

  **Requirements:** R7

  **Dependencies:** Unit 2 (data ledger — useful for providing previous day context, but not strictly required)

  **Files:**
  - Modify: `build.py` (add lede generation + rendering)
  - Modify: `style.css` (lede styling)

  **Approach:**
  - After `load_all()`, extract a summary blob: Cubs game result, three stars, standings movement, notable league events, hot/cold streaks
  - Call Claude API (anthropic SDK) or Ollama (`urllib` to localhost:11434) with a prompt: "Write a 3-4 sentence editorial lede for a Cubs fan newspaper. Tone: witty, opinionated, knowledgeable. Include: [summary blob]"
  - Wrap in `<div class="lede">` and insert after the masthead, before the first section
  - Graceful fallback: if both API and Ollama fail, skip the lede silently (page renders normally)
  - Cache the generated lede in `data/lede-YYYY-MM-DD.txt` so evening edition re-run doesn't re-generate
  - Style: larger serif font, italic, slightly indented — newspaper editorial feel

  **Patterns to follow:**
  - `build.py:1068-1075` — `render_history()` pattern of conditional rendering (return `""` if no content)
  - Ollama is already running on the machine (port 11434)

  **Test scenarios:**
  - Happy path: Claude API returns a lede → renders at top of page with editorial styling
  - Fallback: Claude API fails → tries Ollama → renders Ollama output
  - Fallback: Both fail → page renders normally with no lede (no error visible to reader)
  - Edge case: No Cubs game yesterday → lede focuses on league-wide action and upcoming game
  - Edge case: Lede already cached for today → uses cached version (no API call)
  - Edge case: Evening edition re-run → uses cached morning lede or generates fresh one reflecting final game result

  **Verification:**
  - Generated lede is factually consistent with the data on the page
  - Lede renders with distinct editorial styling (visually distinct from data sections)
  - Page loads normally when API is unavailable

## System-Wide Impact

- **Build pipeline:** Units 2, 4, and 7 add steps to the build pipeline. Unit 2 adds a JSON write. Unit 4 adds a second daily trigger. Unit 7 adds an API call. All are additive — existing flow unchanged
- **Deploy pipeline:** Unit 2 adds a second file push to deploy.py. Pattern is identical to existing archive push
- **HTML output:** Units 1 and 6 add `<link>` and `<script>` tags to head. Unit 7 adds content after masthead. No existing elements change
- **File structure:** 5 new files (`style.css`, `evening.py`, `prospects.json`, `manifest.json`, `sw.js`), 1 new directory (`data/`), 1 optional directory (`icons/`), 1 optional script (`scripts/backfill_history.py`)
- **Dependencies:** Unit 3's backfill script needs `anthropic` SDK (one-time use). Unit 7 optionally uses `anthropic` SDK or falls back to Ollama via urllib. build.py stays stdlib-only for all other units
- **Unchanged invariants:** `index.html` remains a single self-contained HTML file. `live.js` unchanged. Scorecard Book unchanged. GitHub Pages hosting unchanged

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| History backfill has factual errors | Review file + spot-check before merging. Preserve existing hand-curated entries |
| Claude API adds cost to daily builds | Use Ollama as primary, Claude as fallback. Cache lede to avoid re-generation |
| Data ledger grows repo size | ~50KB/day = ~9MB/season. Acceptable for GitHub. Can prune off-season |
| Evening edition misses game end | 5-minute poll interval means max 5-minute delay. Acceptable |
| Service worker serves stale content | Network-first for API, cache-first for shell. SW updates on new deploy |

## Sources & References

- **Origin document:** [docs/ideation/2026-04-08-open-ideation.md](docs/ideation/2026-04-08-open-ideation.md)
- **Prior ideation:** [docs/ideation/2026-04-07-new-features-ideation.md](docs/ideation/2026-04-07-new-features-ideation.md)
- Related code: `build.py`, `deploy.py`, `history.json`, `live.js`
- MLB Stats API: statsapi.mlb.com/api/v1
