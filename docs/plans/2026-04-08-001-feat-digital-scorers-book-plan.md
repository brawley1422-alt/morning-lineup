---
title: "feat: Digital Scorer's Book"
type: feat
status: active
date: 2026-04-08
origin: docs/brainstorms/2026-04-08-scorecard-book-requirements.md
---

# feat: Digital Scorer's Book

## Overview

Build a standalone web app that renders any completed MLB game as a traditional scorebook spread with interactive SVG diamond diagrams. Each at-bat is visualized as a diamond cell showing hit type, baserunning, outs, and RBIs — clean at a glance, full traditional detail on hover/tap. Ships as its own GitHub Pages site with the same dark editorial aesthetic as Morning Lineup.

## Problem Frame

Baseball's hand-scored scorecard is an iconic visual artifact, but no digital tool faithfully recreates it with real game data. This app bridges that gap — authentic enough for a scorer, accessible enough for a casual fan. Future path: embed into Morning Lineup as an expandable Cubs game detail view. (see origin: `docs/brainstorms/2026-04-08-scorecard-book-requirements.md`)

## Requirements Trace

- R1. Date picker defaults to yesterday, optional team filter (all 30 teams)
- R2. Game cards showing matchup, final score, status
- R3. Only Final games are openable
- R4. Shareable URLs (`?game=`, `?date=`)
- R5. Scorebook spread: away left, home right, innings as columns
- R6. Lineup slots 1-9 with substitute sub-rows
- R7. SVG diamond per at-bat cell
- R8. Summary stat columns (AB, R, H, RBI, BB, K)
- R9. Sticky player name/position column
- R10. Diamond: basepath highlighting, hit type, out number, RBI count, run-scored marker
- R11. Color encoding: gold hits, gray/red outs, distinct walk accent
- R12. Tooltip on hover/tap: play description, fielding notation, pitch count/sequence
- R13. Game summary header: line score, decisions, venue, date
- R14. Horizontal scroll + sticky column for extra innings
- R15. Desktop spread; tablet/mobile stacked or tabbed
- R16. Back button to game finder
- R17. Doubleheader labels (Game 1 / Game 2)
- R18. Pitching change annotations
- R19. Extra innings via scrollable columns

## Scope Boundaries

- Post-game only — no live scoring (see origin)
- No player photos, historical archives, print stylesheet, or keyboard nav in v1
- Morning Lineup embed deferred to future unit
- No dynamic team color theming in v1

## Context & Research

### Relevant Code and Patterns

- `live.js:47-56` — Existing diamond SVG: 60x60 viewBox, polygon at (30,6 54,30 30,54 6,30), circles at base positions with gold/rule-hi colors
- `build.py:951-965` — CSS root variables: `--ink`, `--paper`, `--cubs-blue`, `--cubs-red`, `--gold`, `--win`, `--loss`, font families
- `build.py:380-399` — `render_key_plays()`: parses `scoringPlays` indices into `allPlays`, extracts inning/half/description
- `build.py:1015-1026` — `.scoreboard table` CSS: monospace, border-collapse, gold RHE column styling
- `live.js:1-3` — IIFE pattern: `(function() { "use strict"; ... })();`
- Google Fonts link loads Playfair Display, Oswald, IBM Plex Mono, Lora with specific weights

### MLB API Data Structures

**Live feed** (`/api/v1.1/game/{gamePk}/feed/live`):
- `liveData.plays.allPlays[]` — each play has `result.eventType`, `result.event`, `result.description`, `result.rbi`, `result.isOut`
- `runners[]` per play — `movement.start/end/isOut/outBase`, `credits[].position.code` + `credit` type (f_assist, f_putout)
- `playEvents[]` per play — pitch sequence with `details.type` (FF, SL, etc.), `details.call.code` (B, S, X), `hitData` (launchSpeed, trajectory)
- `liveData.boxscore.teams[side].players[ID].battingOrder` — encodes lineup slot (hundreds digit) and sub order (ones digit)
- `liveData.linescore.innings[]` — per-inning runs for line score
- `gameData.teams`, `gameData.venue`, `gameData.datetime` — metadata

**Schedule** (`/api/v1/schedule`):
- `dates[0].games[]` — each game has `gamePk`, `status.abstractGameState`, `teams.away/home.team`, `.score`, `gameNumber` (for doubleheaders)

### eventType → Scoring Notation Mapping

| eventType | Notation | Diamond rendering |
|-----------|----------|-------------------|
| `single` | 1B | Gold basepath to 1B |
| `double` | 2B | Gold basepath to 2B |
| `triple` | 3B | Gold basepath to 3B |
| `home_run` | HR | All basepaths gold + run marker |
| `strikeout` | K | Empty diamond, K text |
| `walk` | BB | Blue-ish dot on 1B |
| `intent_walk` | IBB | Blue-ish dot on 1B |
| `hit_by_pitch` | HBP | Blue-ish dot on 1B |
| `field_out` | Fielding seq (6-3) | Empty diamond, gray |
| `grounded_into_double_play` | GDP + seq | DP marker |
| `double_play` | DP | DP marker |
| `force_out` | FC + seq | Basepath to where reached |
| `fielders_choice` | FC | Basepath to where reached |
| `sac_fly` | SF | SF text |
| `sac_bunt` | SAC | SAC text |
| `field_error` | E + pos# | Basepath to where reached, red text |
| `caught_stealing` | CS | Out marker on base |
| `strikeout_double_play` | K + DP | K + DP marker |
| `catcher_interf` | CI | Dot on 1B |
| `wild_pitch` / `passed_ball` / `balk` | WP / PB / BK | Runner advancement annotations (tooltip only) |

**Fielding sequence construction:** Collect `credits[]` from runners where `isOut=true`, order assists before putout, join position codes with "-" (e.g., 6-4-3).

**Strikeout looking vs. swinging:** Parse `result.description` for "called" vs "swinging" — render as backwards K (Ꝃ) vs K.

## Key Technical Decisions

- **Separate repo or same repo?** Same repo (`morning-lineup/scorecard/`). Simplifies the future embed, shares the git history, and deploys to the same GitHub Pages domain at `/morning-lineup/scorecard/`. No need for a separate repo for what will eventually be a feature of Morning Lineup.
- **Vanilla HTML/JS/CSS, no build step.** Matches Morning Lineup's constraints. Multiple JS files sharing `window.Scorecard` namespace, loaded via `<script>` tags.
- **HTML `<table>` for the scorebook grid.** Tables handle alignment of irregular rowspans (substitutes) naturally, support sticky columns, and are semantically correct for tabular data.
- **One SVG per diamond cell, not one big SVG.** Individual SVGs allow per-cell CSS hover states, event listeners, and natural tooltip positioning.
- **Single tooltip element, repositioned per interaction.** Avoids creating hundreds of hidden tooltip elements — one shared `<div>` that repositions on hover/tap.
- **Hardcoded 30-team list.** Avoids an extra API call on page load. MLB teams change very rarely.

## Open Questions

### Resolved During Planning

- **Fielding sequence source:** Use `runners[].credits[]` array — collect `f_assist` credits first, then `f_putout`, join position codes with "-". Fallback: parse `result.description` for natural-language fielding.
- **Substitution detection:** `battingOrder` field encodes lineup slot (hundreds digit) and sub index (ones digit). Group by `Math.floor(parseInt(battingOrder) / 100)`, sort by `% 100`. Sub index 0 = starter, 1+ = substitutes.
- **Pitching change visual:** Subtle dashed vertical border on the left edge of the inning column where the new pitcher entered. Pitcher name in a small annotation at the column header. Uses `pitching_substitution` action events from `playEvents`.

### Deferred to Implementation

- Exact SVG coordinates and sizing for diamond cell elements (basepath stroke width, text positioning, RBI dot placement) — will need visual iteration
- Full coverage of rare eventTypes (triple_play, catcher_interf) — handle gracefully with fallback rendering if an unknown type appears
- Mobile breakpoint behavior — whether tabbed (away/home toggle) or stacked works better will depend on seeing it rendered

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

```
scorecard/
  index.html        -- Entry point, Google Fonts, <div id="app">
  styles.css         -- CSS variables (from Morning Lineup), grid, diamond, tooltip
  app.js             -- Router, state, wires modules together
  api.js             -- MLB Stats API fetch layer
  parser.js          -- Raw API → ScorecardModel transformation
  diamond.js         -- SVG diamond cell renderer
  scorebook.js       -- Scorebook grid layout (two-page spread)
  header.js          -- Game summary header
  finder.js          -- Date picker + team filter + game cards
  tooltip.js         -- Shared hover/tap detail overlay

Data flow:
  [finder.js] → user picks date → [api.js] fetch schedule → render game cards
  → user clicks card → [api.js] fetch live feed → [parser.js] → ScorecardModel
  → [header.js] renders line score/decisions
  → [scorebook.js] renders grid, calls [diamond.js] per cell
  → [tooltip.js] attaches hover/tap listeners
```

**ScorecardModel shape (directional):**
- `away/home.lineup[0-8].batters[]` — each batter has `atBats[]` with parsed result, fielding notation, pitch sequence, runner movements
- `away/home.linescore[]` — runs per inning
- `away/home.totals` — R/H/E
- `away/home.pitchers[]` — name, IP, stats
- `decisions` — W/L/S
- `totalInnings` — drives column count

## Implementation Units

- [ ] **Unit 1: Project scaffold and CSS foundation**

  **Goal:** Create the scorecard directory, HTML entry point, and CSS file with Morning Lineup's design system variables and base styles.

  **Requirements:** Foundation for all subsequent units

  **Dependencies:** None

  **Files:**
  - Create: `scorecard/index.html`
  - Create: `scorecard/styles.css`

  **Approach:**
  - HTML scaffold with Google Fonts link, viewport meta, theme-color, `<div id="app">`
  - CSS root variables copied from `build.py:951-965` exactly
  - Base body/typography styles matching Morning Lineup
  - Script tags for all JS files (can be empty initially)

  **Patterns to follow:**
  - `build.py:951-965` — CSS variables
  - Morning Lineup's Google Fonts link with exact weights

  **Test expectation:** None — pure scaffolding. Verified by opening `scorecard/index.html` in browser and confirming fonts load and background/text colors match Morning Lineup.

  **Verification:**
  - Page loads with correct dark background, cream text, and Morning Lineup fonts

---

- [ ] **Unit 2: API layer and game finder**

  **Goal:** Build the game finder screen — date picker, team filter, and clickable game cards fetched from the MLB schedule API.

  **Requirements:** R1, R2, R3, R4, R17

  **Dependencies:** Unit 1

  **Files:**
  - Create: `scorecard/api.js`
  - Create: `scorecard/finder.js`
  - Modify: `scorecard/styles.css`

  **Approach:**
  - `api.js`: `Scorecard.api.fetchSchedule(dateStr)` wrapping fetch to `/api/v1/schedule?date=...&sportId=1&hydrate=team,linescore,decisions`
  - `finder.js`: Date input (default yesterday), team `<select>` with hardcoded 30 teams, renders game cards grid
  - Game cards show team abbreviations, final score, status badge. Non-Final games show status but are not clickable.
  - Doubleheaders: use `game.gameNumber` to show "Game 1" / "Game 2" labels
  - URL param handling: `?date=` sets the date picker, `?game=` bypasses finder (handled in Unit 6)
  - Card click dispatches a custom event or calls `Scorecard.app.loadGame(gamePk)`

  **Patterns to follow:**
  - `build.py:62-75` — schedule API call with hydration params
  - `.scoreboard` CSS patterns for card styling

  **Test scenarios:**
  - Happy path: Load page, see yesterday's games as cards with correct scores and team names
  - Happy path: Change date, cards update to that date's games
  - Happy path: Select a team, only that team's games shown
  - Edge case: Date with no games shows empty state message
  - Edge case: Doubleheader shows "Game 1" / "Game 2" labels
  - Edge case: In-progress or Preview games show status but are not clickable

  **Verification:**
  - Game finder loads, shows real game data, filters work, only Final games are clickable

---

- [ ] **Unit 3: Data parser (API → ScorecardModel)**

  **Goal:** Transform the raw MLB live feed JSON into a clean ScorecardModel that decouples API structure from rendering logic.

  **Requirements:** R5, R6, R10, R12 (data layer)

  **Dependencies:** Unit 2 (needs `api.js`)

  **Files:**
  - Create: `scorecard/parser.js`

  **Approach:**
  - `Scorecard.parser.parse(feed)` — takes raw live feed, returns ScorecardModel
  - **Lineup construction:** From `boxscore.teams[side].players`, group by `Math.floor(parseInt(battingOrder) / 100)` for slot, sort by `% 100` for starter/sub ordering
  - **At-bat mapping:** Walk `allPlays`, filter by `about.halfInning` (top=away, bottom=home), match `matchup.batter.id` to lineup slot
  - **Event type mapping:** Map `result.eventType` to display notation using the mapping table in Key Technical Decisions
  - **Fielding sequence:** From `runners[].credits[]` where `isOut=true`, collect assists then putout, join position codes
  - **Pitch sequence:** From `playEvents[]`, extract `details.type` + `details.call.code` pairs
  - **Runner movements:** From `runners[]`, extract `movement.start`, `.end`, `.isOut` for basepath rendering
  - **Pitching changes:** Detect `pitching_substitution` in `playEvents` action types, record inning and new pitcher

  **Patterns to follow:**
  - `build.py:380-399` — existing play-by-play parsing pattern

  **Test scenarios:**
  - Happy path: Parse a 9-inning game — all 9 lineup slots populated for both teams, correct number of at-bats per batter
  - Happy path: Singles produce `notation: "1B"` with basepath end at 1B; home runs produce all basepaths + run scored
  - Happy path: Strikeout produces `notation: "K"` with `isOut: true` and correct out number
  - Happy path: Fielding credits produce correct sequence (e.g., "6-3" for groundout SS to 1B)
  - Edge case: Pinch hitter appears as second batter in their lineup slot with `isStarter: false`
  - Edge case: Extra-inning game produces `totalInnings > 9` and all at-bats assigned to correct innings
  - Edge case: Walk produces `notation: "BB"` with basepath end at 1B, `isOut: false`
  - Edge case: Unknown eventType falls back to displaying `result.event` text rather than crashing
  - Integration: Pitch sequence array matches the number of pitches thrown in the at-bat

  **Verification:**
  - Feed a real gamePk through the parser, inspect the model in browser console — every at-bat accounted for, lineup slots correct, no orphaned plays

---

- [ ] **Unit 4: SVG diamond cell renderer**

  **Goal:** Build the diamond SVG component that renders a single at-bat as an interactive diamond diagram.

  **Requirements:** R7, R10, R11

  **Dependencies:** Unit 3 (needs parsed at-bat data)

  **Files:**
  - Create: `scorecard/diamond.js`
  - Modify: `scorecard/styles.css`

  **Approach:**
  - `Scorecard.diamond.render(atBat)` — returns an SVG element string
  - SVG viewBox `0 0 60 60`, diamond polygon at same coordinates as `live.js` (30,6 54,30 30,54 6,30)
  - **Basepaths** as `<line>` elements: home→1B, 1B→2B, 2B→3B, 3B→home. Highlighted (gold stroke, thicker) when batter reached that base.
  - **Hit type text** centered in diamond: `1B`, `2B`, `HR`, `K`, `BB`, `6-3`, etc.
  - **Out number** in bottom-right corner (small, red) when the at-bat resulted in an out
  - **RBI dots** in top-left area, one filled circle per RBI
  - **Run scored marker** — filled circle at home plate position when batter scored
  - **Color rules:** Hits get gold basepaths + gold text. Outs get muted gray diamond + red out number. BB/HBP get blue-ish accent on 1B. Errors get red E text.
  - CSS classes: `.diamond-cell`, `.basepath.active`, `.hit-type`, `.out-num`, `.rbi-dot`, `.run-scored`

  **Patterns to follow:**
  - `live.js:47-56` — existing diamond SVG structure (viewBox, polygon points, circle positions)

  **Test scenarios:**
  - Happy path: Single renders gold basepath from home to 1B, "1B" text centered
  - Happy path: Home run renders all four basepaths gold, "HR" text, run-scored marker at home
  - Happy path: Strikeout renders muted diamond, "K" text, red out number in corner
  - Happy path: 2-RBI double shows two gold dots in top-left area
  - Edge case: Walk renders "BB" with distinct blue accent, no basepath highlighting (just dot on 1B)
  - Edge case: Error renders red "E6" text with basepath to where batter reached
  - Edge case: Fielding out with long sequence (e.g., "5-4-3") fits in center text area without overflow
  - Edge case: Empty cell (no at-bat for that inning/slot) renders as blank/placeholder

  **Verification:**
  - Render diamonds for a variety of at-bat types side by side — visually distinct, readable at small sizes, colors match spec

---

- [ ] **Unit 5: Scorebook grid layout**

  **Goal:** Render the full two-page scorebook spread — away lineup on left, home on right, with innings as columns and diamond cells in each at-bat position.

  **Requirements:** R5, R6, R8, R9, R14, R15, R19

  **Dependencies:** Unit 3, Unit 4

  **Files:**
  - Create: `scorecard/scorebook.js`
  - Modify: `scorecard/styles.css`

  **Approach:**
  - `Scorecard.scorebook.render(model)` — takes ScorecardModel, returns HTML for the spread
  - HTML `<table>` per team page: rows = lineup slots (1-9), columns = innings + summary stats
  - **Sticky left column:** Player name + position, `position: sticky; left: 0` with solid background
  - **Substitute rows:** When a lineup slot has multiple batters, render sub-rows within the slot. Starter's diamonds in early innings, sub's diamonds in later innings. Visual grouping via left border or background tint.
  - **Summary columns** after last inning: AB, R, H, RBI, BB, K pulled from boxscore batting stats
  - **Inning headers** with inning numbers, pitching change annotations as dashed left border + small pitcher name
  - **Two-page spread:** Flexbox wrapper `.scorebook-spread` with `.scorebook-page.away` and `.scorebook-page.home` side by side, visual "binding" gap between them
  - **Extra innings:** Columns extend naturally, horizontal `overflow-x: auto` on each page with `scroll-snap-type: x mandatory` for smooth paging
  - **Responsive:** Desktop = side-by-side. Below 900px, stack vertically or use tabs (away/home toggle button)

  **Patterns to follow:**
  - `.scoreboard table` CSS from `build.py:1015-1026` for table styling conventions

  **Test scenarios:**
  - Happy path: 9-inning game renders 9 inning columns + 6 stat columns for both teams, all 9 lineup slots populated
  - Happy path: Player names visible while scrolling horizontally through innings
  - Happy path: Summary stats (AB, R, H, RBI, BB, K) match the boxscore totals
  - Edge case: Pinch hitter shows as sub-row with "PH" annotation, their diamonds appear in the innings they played
  - Edge case: 12-inning game renders 12 columns, horizontal scroll works smoothly
  - Edge case: Pitching change shows dashed border and pitcher name annotation at correct inning
  - Edge case: Lineup slot with 2 substitutes (starter + PH + PH for PH) renders 3 sub-rows
  - Integration: Every diamond cell in the grid corresponds to a real at-bat from the parser output — no missing or duplicate cells

  **Verification:**
  - Load a real game, count diamonds — total should equal total plate appearances in the game. Grid alignment is clean, no visual overflow issues.

---

- [ ] **Unit 6: Game summary header and app router**

  **Goal:** Build the game summary header (line score, decisions, venue) and wire the app router to navigate between game finder and scorecard views.

  **Requirements:** R4, R13, R16

  **Dependencies:** Unit 2, Unit 5

  **Files:**
  - Create: `scorecard/header.js`
  - Create: `scorecard/app.js`
  - Modify: `scorecard/index.html`

  **Approach:**
  - `header.js`: Renders above the scorecard — team names/abbreviations, inning-by-inning line score table (R column per inning + R/H/E totals), pitching decisions (W/L/S with pitcher names), venue, date
  - `app.js`: Manages state (`{view: "finder"|"scorecard", gamePk, date}`), URL parameter handling via `history.pushState`/`popstate`, wires all modules together
  - `?game=XXXXX` → bypass finder, load scorecard directly
  - `?date=YYYY-MM-DD` → open finder at that date
  - Back button uses browser history or explicit "← Back to games" link

  **Patterns to follow:**
  - `build.py:1015-1026` — line score table CSS
  - `live.js` — team name display patterns

  **Test scenarios:**
  - Happy path: Header shows correct teams, final score, all 9 innings in line score, R/H/E totals, venue, date
  - Happy path: Winning/losing/save pitcher names displayed correctly
  - Happy path: Navigate from finder → scorecard → back button returns to finder with same date
  - Happy path: Direct URL `?game=XXXXX` loads the scorecard without showing finder
  - Edge case: Game with no save decision omits the S field gracefully
  - Edge case: Extra-inning line score extends columns without breaking layout
  - Edge case: Browser back/forward buttons work correctly with pushState

  **Verification:**
  - Full flow: open app → pick date → click game → see header + scorecard → back → pick another game. Direct `?game=` URL works.

---

- [ ] **Unit 7: Tooltip detail overlay**

  **Goal:** Add hover/tap interaction to diamond cells that reveals full traditional scoring detail.

  **Requirements:** R12

  **Dependencies:** Unit 4, Unit 5

  **Files:**
  - Create: `scorecard/tooltip.js`
  - Modify: `scorecard/styles.css`

  **Approach:**
  - Single shared `<div class="tooltip">` element, absolutely positioned
  - `Scorecard.tooltip.init()` — attaches delegated event listeners to the scorebook grid container
  - Desktop: `mouseenter`/`mouseleave` on `.diamond-cell` elements
  - Mobile: `click` toggle (tap to show, tap elsewhere to dismiss)
  - Tooltip content: full play description, traditional fielding notation, pitch count (B-S), pitch sequence (e.g., "FF-B, SL-S, CH-X"), exit velocity/launch angle if available
  - Position: above or below the cell depending on viewport space, horizontally centered on the cell
  - Viewport-aware: flip direction when tooltip would overflow screen edge

  **Patterns to follow:**
  - Morning Lineup's `--rule`, `--ink-2` for tooltip background styling

  **Test scenarios:**
  - Happy path: Hover over a single — tooltip shows "John Doe singles on a line drive to left field", fielding notation, pitch sequence
  - Happy path: Hover over a strikeout — tooltip shows full description and pitch-by-pitch breakdown
  - Edge case: Tooltip near edge of screen repositions to stay visible
  - Edge case: On mobile, tap shows tooltip, tapping elsewhere dismisses it
  - Edge case: At-bat with no pitch data (rare) shows description only without crashing

  **Verification:**
  - Every diamond cell shows a tooltip with correct play details on interaction. Tooltip positioning works at grid edges.

## System-Wide Impact

- **Interaction graph:** Standalone app — no callbacks or middleware. Future embed via iframe with `?embed=1` parameter will need a postMessage height communication, but that's out of scope.
- **Error propagation:** API fetch failures should show user-friendly error state (not blank screen). Parser errors for unknown eventTypes should fall back gracefully.
- **State lifecycle risks:** None — all data is fetched fresh per game view, no persistent state.
- **API surface parity:** The schedule and live feed endpoints are the same ones Morning Lineup uses. No new API dependencies.
- **Unchanged invariants:** Morning Lineup's build.py, deploy.py, and live.js are not modified. The scorecard lives in its own subdirectory.

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| MLB API rate limiting on rapid date switching | Debounce date picker changes; cache schedule responses in a JS Map |
| Rare eventTypes not in mapping table | Fallback: display `result.event` text as-is in the diamond cell |
| SVG diamonds too small to read on mobile | Scale diamond cells larger on small viewports; tooltip carries the detail |
| `battingOrder` encoding edge cases | Verify with multiple real games during implementation; fallback to `allPlays` batter ordering if encoding is inconsistent |
| GitHub Pages base path for assets | Use relative paths in script/link tags since app lives in `scorecard/` subdirectory |

## Sources & References

- **Origin document:** [docs/brainstorms/2026-04-08-scorecard-book-requirements.md](docs/brainstorms/2026-04-08-scorecard-book-requirements.md)
- Related code: `live.js:47-56` (diamond SVG), `build.py:380-399` (play parsing), `build.py:951-965` (CSS variables)
- MLB Stats API: `https://statsapi.mlb.com/api/v1` (schedule, boxscore), `https://statsapi.mlb.com/api/v1.1` (live feed)
- MLB-StatsAPI community docs: `https://github.com/toddrob99/MLB-StatsAPI/wiki/Endpoints`
- Baseball scorekeeping notation: `https://en.wikipedia.org/wiki/Baseball_scorekeeping`
