---
title: "feat: Expand Morning Lineup to full nine-section lineup card"
type: feat
status: active
date: 2026-04-08
---

# Expand Morning Lineup to Nine Sections

## Overview

Add 4 new sections to Morning Lineup, bringing the total from 5 (plus conditional history) to a full 9-section lineup card. The new sections fill gaps in the daily briefing: a deep dive on today's Cubs matchup, a weekly/season pulse check, a dedicated roster health section, and a promoted history section.

## Problem Frame

The current 5 sections cover yesterday's game, today's slate, minors, NL Central, and league-wide news. Missing: any preview of *today's* Cubs game beyond a card in Next Games, any trend/pulse context beyond a single game, and a dedicated home for roster moves (injuries are buried inside the game recap and invisible on off-days). History exists but is conditional and hidden when no entries match today's date.

## Final Section Order

| # | ID | Section Name | Status |
|---|-----|-------------|--------|
| 1 | cubs | The Cubs | Exists |
| 2 | scout | Scouting Report | **NEW** |
| 3 | pulse | The Stretch | **NEW** |
| 4 | pressbox | The Pressbox | **NEW** |
| 5 | farm | Down on the Farm | Exists |
| 6 | today | Today's Slate | Exists |
| 7 | nlc | NL Central | Exists |
| 8 | league | Around the League | Exists |
| 9 | history | This Day in Cubs History | Exists (promote) |

## Scope Boundaries

- No new Python dependencies (stdlib only)
- No new JS files or client-side behavior
- No new external APIs beyond MLB Stats API
- Styling uses existing CSS patterns and variables — new CSS classes only as needed
- `history.json` coverage gaps are out of scope (backfilling entries is a separate task)

## Key Technical Decisions

- **Scouting Report uses game log, not vsTeam splits**: The `vsTeam` career endpoint doesn't work on the current API version. Instead, use `/people/{pid}/stats?stats=gameLog&season=YYYY&group=pitching` for each starter's last 3 starts, plus season line from existing `fetch_pitcher_line()`.
- **The Stretch reuses existing standings data**: `runsScored`, `runsAllowed`, `runDifferential`, and all `splitRecords` (home/away, day/night, L10, 1-run, extras, grass/turf) are already in the standings response. Zero new API calls needed.
- **The Pressbox splits injuries out of Section 1**: Injuries move from the Cubs recap to their own section alongside transactions. Section 1 gets lighter; Pressbox shows roster health even on off-days.
- **Transactions from `/transactions` endpoint**: `GET /transactions?teamId=112&startDate=YYYY-MM-DD&endDate=YYYY-MM-DD` returns IL moves, callups, DFA, trades, signings with full descriptions. Pull last 7 days.
- **History gets an always-visible section**: Instead of conditionally hiding when no entries exist, show the section with a "No entries for today" fallback message.

## Files to Modify

- `build.py` — all data fetching + rendering + page assembly changes
- `style.css` — new CSS classes for new section components
- `history.json` — no changes (coverage backfill is separate)

## Implementation Units

### Phase 1: Data Layer (build.py — load_all)

- [ ] **Unit 1: Add transactions fetch to load_all()**

**Goal:** Fetch Cubs transactions from the last 7 days and add to the data dict.

**Approach:**
- Add `fetch("/transactions", teamId=CUBS_ID, startDate=(today - timedelta(days=7)).isoformat(), endDate=today.isoformat())` 
- Filter to meaningful types: IL placements (DIS, DTD), activations (ACT), optioned (OPT), recalled (RCL), DFA, trades, signings to MLB roster
- Exclude minor league signings (typeCode SFA where description contains "minor league") to reduce noise
- Add `"transactions"` key to return dict
- Wrap in try/except like all other fetches

**Files:**
- Modify: `build.py` (inside `load_all()`, around line 280)

**Test expectation:** Run `python3 build.py` — should print no errors. Check `data/YYYY-MM-DD.json` for `transactions` key.

---

- [ ] **Unit 2: Add pitcher game log fetch for Scouting Report**

**Goal:** Fetch game logs for both probable pitchers in today's Cubs game.

**Approach:**
- From `next_games[0]`, extract Cubs probable pitcher ID and opponent probable pitcher ID
- For each, call `/people/{pid}/stats?stats=gameLog&season=YYYY&group=pitching` 
- Take last 3 starts (splits) — each has date, opponent, IP, ER, K, HR, hits, walks
- Also grab season totals via existing `fetch_pitcher_line()` pattern
- Add `"scout_data"` key to return dict: `{"cubs_sp": {...}, "opp_sp": {...}, "cubs_sp_log": [...], "opp_sp_log": [...]}`
- Graceful fallback: if no probable pitchers announced, `scout_data` is empty dict

**Files:**
- Modify: `build.py` (inside `load_all()`, after the today's game enhancement block ~line 186)

**Test expectation:** Run `python3 build.py` — no errors. `scout_data` key in data ledger JSON.

---

### Phase 2: Render Functions (build.py)

- [ ] **Unit 3: render_scouting_report()**

**Goal:** Render the Scouting Report section — a head-to-head pitching matchup card for today's Cubs game.

**Approach:**
- If `scout_data` is empty, return empty string (section hidden on off-days or TBD pitchers)
- Layout: two-column matchup card. Left = Cubs SP, Right = opponent SP
- Each side shows: name, season line (ERA, W-L, IP, K, WHIP), last 3 starts as compact rows (date, vs OPP, IP/ER/K)
- Bottom: today's game time, venue, weather (reuse `fetch_weather_for_venue` if available from next_games)
- Use existing CSS classes where possible: `.two`, `.tempbox` pattern for the matchup cards, `.data` table for game log rows
- New CSS class: `.matchup-card` for the head-to-head container

**Files:**
- Modify: `build.py` (new function after `render_cubs_leaders`, ~line 1095)

---

- [ ] **Unit 4: render_stretch()**

**Goal:** Render The Stretch section — season pulse and trend data for the Cubs.

**Approach:**
- All data from existing `cubs_rec` in standings (no new API calls)
- Display components:
  - **Record bar**: W-L, PCT, GB, streak, division rank
  - **Run differential**: RS, RA, run diff with +/- color coding (green positive, red negative), pythagorean W-L (calculated: `RS^2 / (RS^2 + RA^2) * G`)
  - **Splits grid**: 2-column grid of split records — Home/Away, Day/Night, vs LHP/RHP, 1-Run games, Extras, Grass/Turf, Last 10
  - Each split as a compact row: label + W-L + PCT
- Use existing patterns: `.two` grid, `.data` table for splits, monospace for numbers
- New CSS: `.pulse-bar` for the record summary, `.run-diff` for the differential display

**Files:**
- Modify: `build.py` (new function)

---

- [ ] **Unit 5: render_pressbox()**

**Goal:** Render The Pressbox section — injuries + recent transactions.

**Approach:**
- Reuse existing `render_injuries()` output directly (it already renders a nice `<dl>`)
- Add transactions list below injuries: each transaction as a compact row with date, type badge, and description
- Transaction type badges: color-coded by type (IL = red, activated = green, optioned = gold, recalled = blue, trade = red, DFA = red)
- If no transactions in last 7 days, show "No roster moves in the last 7 days"
- New CSS: `.transac-row` for transaction items, `.transac-type` for type badges (reuse `.blurb-tag` pattern)

**Files:**
- Modify: `build.py` (new function)

---

- [ ] **Unit 6: Update render_history() for always-visible section**

**Goal:** Make history section always visible with a fallback message.

**Approach:**
- Change `render_history()` to return content even when `history_items` is empty
- Empty state: `<p class="idle-msg">No historical entries for today's date.</p>` (reuses existing `.idle-msg` class)
- Keep the existing 3-item limit and year/text format

**Files:**
- Modify: `build.py` (update `render_history` function, ~line 1358)

---

### Phase 3: Page Assembly + Section Reordering

- [ ] **Unit 7: Rewire page() for 9 sections**

**Goal:** Update the page assembly to include all 9 sections in the correct order, update TOC, update section numbering.

**Approach:**
- Call new render functions: `render_scouting_report()`, `render_stretch()`, `render_pressbox()`
- Remove injuries from Section 1 (The Cubs) — they move to The Pressbox
- Reorder sections in the HTML template:
  1. `#cubs` — The Cubs (minus injuries)
  2. `#scout` — Scouting Report (conditional: hidden if no game today / TBD pitchers)
  3. `#pulse` — The Stretch
  4. `#pressbox` — The Pressbox (injuries + transactions)
  5. `#farm` — Down on the Farm
  6. `#today` — Today's Slate
  7. `#nlc` — NL Central
  8. `#league` — Around the League
  9. `#history` — This Day in Cubs History (always visible)
- Update TOC nav to list all 9 sections (conditional entries for scout if hidden)
- Update section number badges (01-09)
- Conditional sections: Scouting Report uses same pattern as existing history conditional but wraps the whole `<section>` tag

**Files:**
- Modify: `build.py` (in `page()` function, ~line 1373)

---

### Phase 4: Styling

- [ ] **Unit 8: CSS for new sections**

**Goal:** Add CSS classes for Scouting Report, The Stretch, and The Pressbox components.

**Approach — new classes needed:**

**Scouting Report:**
- `.matchup-vs` — the head-to-head container (2-column grid, centered divider)
- `.sp-card` — individual pitcher card (reuse `.star` pattern: ink-2 bg, border, border-radius)
- `.sp-name` — pitcher name (condensed font, uppercase)
- `.sp-season` — season stat line (mono font, gold numbers)
- `.sp-log` — game log table (reuse `.data` table pattern, compact)
- `.sp-log .opp` — opponent name in game log row

**The Stretch:**
- `.pulse-record` — top-line record bar (flex row, large text)
- `.pulse-diff` — run differential display (centered, large number, +/- color)
- `.pulse-pyth` — pythagorean record (smaller, muted)
- `.splits-grid` — 2-column grid of split records (reuse `.two`)
- `.split-row` — individual split (flex, space-between)
- `.split-label` — split name (condensed, muted)
- `.split-val` — W-L record (mono, paper)
- `.split-pct` — winning pct (mono, gold)

**The Pressbox:**
- `.transac-list` — transaction list container
- `.transac-item` — individual transaction row (flex, baseline aligned)
- `.transac-date` — date column (mono, muted, fixed width)
- `.transac-badge` — type badge (reuse `.blurb-tag` size/font pattern, color by type)
- `.transac-desc` — description text (body font, paper-dim)
- Badge color variants: `.transac-badge.il`, `.transac-badge.act`, `.transac-badge.opt`, `.transac-badge.rcl`

**Files:**
- Modify: `style.css`

---

## Verification

1. Run `python3 build.py` — should complete without errors
2. Open `index.html` in browser — verify all 9 sections render
3. Check TOC lists all 9 sections and anchor links work
4. Verify Scouting Report shows pitcher matchup (or is hidden gracefully if no game today)
5. Verify The Stretch shows correct record, run differential, and splits
6. Verify The Pressbox shows injuries + recent transactions
7. Verify History section shows even when no entries exist for today
8. Test responsive at 900px, 720px, 640px, 420px breakpoints
9. Commit and push to GitHub Pages
