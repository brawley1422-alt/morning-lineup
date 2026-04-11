---
date: 2026-04-10
topic: affordance-debt
focus: under-utilized features and inconsistent affordances — UI elements that hint at interactivity but aren't wired up, features built for one context that should be reused elsewhere, data already fetched but not surfaced
---

# Ideation: Morning Lineup — Affordance Debt & Feature Reuse

## Codebase Context

Python stdlib static site generator → 30 MLB team pages + standalone Scorecard Book app. Main briefing sections live in `sections/*.py` (headline, scouting, stretch, pressbox, farm, slate, division, around_league, history, columnists). Scorecard at `scorecard/*.js` (9 modules: api, parser, diamond, finder, panels, header, scorebook, tooltip, app).

### Phase 1 findings (grounded citations)

1. **Section headers already collapse.** ALL 9 section `<summary>` elements in `build.py:692-777` are functional `<details>` triggers with cursor:pointer + chevron rotation (`style.css:55-63`). They work. JB's "sections are clickable but do nothing" is likely actually hitting the subsection h3/h4 headers inside sections — those have no hover or click (`style.css:64-65`). Nested-collapse candidates: `scouting.py` game logs, `stretch.py` splits grid, `division.py` all-division tables, `around_league.py` news wire beyond top 3.

2. **Player-name tooltip trapped in scorebook iframe.** `scorecard/tooltip.js:264-268` triggers on mouseover of `.diamond-cell` elements; player stat overlay lives at `scorecard/panels.js:209-340`. Player names render as dead text across the briefing:
   - `headline.py:160,171,180` — Three Stars
   - `headline.py:250-251` — Probable pitchers for next 3 games
   - `around_league.py:92` — League leaders
   - `around_league.py:39` — Winning pitcher in yesterday's scoreboard
   - `farm.py:58,83,86` — Minor league top hitter/pitcher
   - `farm.py:134,170,179` — Prospect tracker rows
   - `pressbox.py:20` — Injured list

3. **Data fetched but discarded in `load_all()`**:
   - Streak codes (`W4`/`L2`) from standings — rendered in division only, dropped everywhere else
   - Weather embedded in live gameData — never surfaced
   - Venue attendance, game duration, game notes — dropped
   - Pitcher game logs (last 3 starts) — rendered raw in `scouting.py`, no ERA trend / K/BB evolution computed
   - Run differential per team from standings — dropped
   - Minor league bench/relief stats — only top-line shown

4. **Scorecard capabilities not reused in briefing:**
   - Dark/paper theme toggle (`scorecard/app.js:354-380`) — iframe only, persists to localStorage
   - Full linescore table (`scorecard/header.js` + `scorebook.js`) vs briefing's simplified 5-col (`headline.py:79-124`)
   - Weather panel with WMO codes + Wrigley wind (`scorecard/panels.js:130-200`) vs briefing's bare temp/condition
   - Broadcast panel with language tags + home/away (`scorecard/panels.js:70-128`) vs briefing's raw list
   - Strike zone SVG viz (`scorecard/tooltip.js:127-257`) — isolated
   - At-bat journey narrative (`scorecard/tooltip.js:62-78`) — isolated

5. **Static where live should win.** `live.js` only polls the Cubs widget. `slate.py`, `division.py`, `around_league.py` all render frozen snapshots despite `scorecard/app.js:122-149` having working 20s polling infra.

6. **Cosmetic hover without handler.** `style.css:118` — `table.data tr:hover td` brightens league leader rows with no click target.

7. **`prospects.json` is read only by `farm.py`.** Never cross-referenced when a prospect pitches in scouting, gets called up in pressbox transactions, or debuts in around_league.

8. **30-team multiplier.** Every primitive ships to 30 pages immediately via the multi-tenant build.

### Past learnings

None directly relevant. `docs/solutions/best-practices/config-driven-multi-tenant-static-site-2026-04-08.md` is the only solutions doc and covers the architectural decision to extract Cubs-specific values into per-team configs — tangential to affordance debt.

## Ranked Ideas

### 1. Universal player-tooltip service
**Description:** Lift `scorecard/tooltip.js` + `panels.js` player-overlay out of the scorebook iframe into a shared `/assets/player-tooltip.js`. Wrap every player mention in `sections/*.py` with `<span class="player" data-id="{mlb_id}">`. One listener hydrates them all. Directly answers JB's verbatim example #1.
**Rationale:** 1 primitive → 30 teams × 9 sections × thousands of player instances. Unlocks prospect badges (#6) and any future player-scoped feature. The capability already exists — it's just trapped in the scorebook.
**Downsides:** Every section file needs a lightweight refactor to emit the wrapper. Tooltip may need positioning rework outside the scorebook grid. Mobile tap-vs-hover UX decision needed.
**Confidence:** 95%
**Complexity:** Medium
**Status:** Unexplored
**Evidence:** `scorecard/tooltip.js:264-268`, `scorecard/panels.js:209-340`, `headline.py:160-191,250-251`, `around_league.py:39,92`, `farm.py:58-87,134-183`, `pressbox.py:20`

### 2. Nested collapse for subsection headers
**Description:** Promote h3/h4 subsection headers inside `scouting.py` (game logs), `stretch.py` (splits grid), `division.py` (all-division tables), `around_league.py` (news items beyond top 3), `farm.py` (prospect deep stats) to `<details>` triggers with the same chevron affordance as top-level sections. *Note: top-level section headers already collapse — JB may actually be hitting these h3/h4 dead zones when he says "sections do nothing."*
**Rationale:** Low-risk reuse of an already-proven pattern (`style.css:55-63`). Directly answers JB's verbatim example #2. Reduces scroll burden on dense sections.
**Downsides:** Will break snapshot tests — expect a re-bless. Some subsections may look visually odd when collapsed by default; need to decide open vs closed initial state per subsection.
**Confidence:** 90%
**Complexity:** Low
**Status:** Unexplored
**Evidence:** `build.py:692-777`, `style.css:55-65`, `scouting.py`, `stretch.py`, `division.py`, `around_league.py`

### 3. Resurrect discarded data (streaks, run diff, weather, attendance, pitcher trends)
**Description:** `load_all()` already fetches streak codes, run differentials, weather (live gameData), venue attendance, game duration, and last-3-starts pitcher game logs — then drops most of it. Surface as inline chips: `W4`/`L2` pills in division + around_league standings, run diff next to records, ERA/K/BB trend arrows in scouting, attendance in the linescore card, weather icon above the Cubs widget.
**Rationale:** Free data — already on the wire, zero new API calls. Reader gets context they didn't know to ask for. Smallest diff with the widest ripple across all 30 team pages.
**Downsides:** Chip visual design needs a pass — easy to clutter the editorial aesthetic. Pitcher trend arrows need a simple math helper (last-3 avg vs season avg).
**Confidence:** 95%
**Complexity:** Low
**Status:** Unexplored
**Evidence:** `build.py` standings fetch, `headline.py:79-124`, `scorecard/panels.js:130-200` (weather reference), `sections/scouting.py` game logs

### 4. Unified live-polling core
**Description:** Collapse `live.js` (Cubs widget polling) and `scorecard/app.js` poll loop (20s/5min adaptive) into one `/assets/live-core.js` module that owns MLB Stats API state and exposes a subscribe API. Every live-capable DOM node subscribes: the Cubs widget, slate game cards (`slate.py`), division standings (`division.py`), around-league scoreboard (`around_league.py`), the scorebook. Briefing stops being "morning snapshot" and becomes a live document that evolves through the day.
**Rationale:** Two parallel polling implementations already exist, duplicating state and API calls. Unifying them unlocks live updates everywhere a DOM node asks — slate/standings/scoreboard stop lying to the reader at 4 PM. Biggest infrastructure leverage available.
**Downsides:** Highest-complexity item in this list. Touches the two most load-bearing JS files. Risk of regression on the working Cubs widget and scorebook polling — both need regression testing. Service worker cache behavior needs review.
**Confidence:** 75%
**Complexity:** High
**Status:** Explored (brainstorm started 2026-04-10)
**Evidence:** `live.js` (Cubs widget only), `scorecard/app.js:6-8,122-149`, `slate.py`, `division.py`, `around_league.py`

### 5. Lift scorecard widgets into briefing
**Description:** Four self-contained scorecard modules are trapped inside the iframe. Lift them into briefing pages:
  - (a) Full linescore (`scorecard/header.js` + `scorebook.js`) replaces `headline.py:79-124`'s truncated 5-column stub
  - (b) Weather panel with WMO codes + Wrigley wind interpretation (`scorecard/panels.js:130-200`) replaces bare temp/condition in headline
  - (c) Broadcast panel with language tags + home/away (`scorecard/panels.js:70-128`) replaces raw list
  - (d) Dark/paper theme toggle (`scorecard/app.js:354-380`) moves to the site header with shared `localStorage` persistence

**Rationale:** Four capabilities already built, tested, and shipping — just siloed. Pure lift-and-shift. No new data, no new fetches. Unghettoizes the scorecard.
**Downsides:** (a) may conflict with the editorial 5-col aesthetic — check with JB. (d) needs testing across both theme-aware contexts to avoid flash-of-wrong-theme.
**Confidence:** 85%
**Complexity:** Low-Medium
**Status:** Unexplored
**Evidence:** `headline.py:79-124`, `scorecard/header.js`, `scorecard/scorebook.js`, `scorecard/panels.js:70-200`, `scorecard/app.js:354-380`

### 6. Prospect cross-reference primitive
**Description:** Load `prospects.json` once at build time into a lookup set keyed by MLB ID. Any player mention (via idea #1's `data-id` primitive) checks the set and renders a `.prospect` badge with rank number. Auto-flags prospects when they pitch in scouting, appear in pressbox IL or transactions, get called up, or surface in around_league. Also: diff `prospects.json` against active roster at build time and inject a "from the farm" callout in pressbox when a call-up happens.
**Rationale:** `prospects.json` is only read by `farm.py` today — a significant data asset that never shows up at the moment it's most relevant (when the kid actually takes the mound). Builds on idea #1's primitive for near-free.
**Downsides:** Depends on idea #1 landing first. Requires a roster-diff helper. Badge visual needs to be unobtrusive to avoid every page lighting up like a Christmas tree.
**Confidence:** 80%
**Complexity:** Low (given #1 exists)
**Status:** Unexplored
**Evidence:** `farm.py:58-87,134-183` (sole consumer), `pressbox.py:20`, `sections/scouting.py`

### 7. Persistent fold memory
**Description:** `localStorage`-back every `<details>` open/closed state keyed by section id. Second visit, the page wakes up exactly how you left it. Your "morning shape" is remembered across the 30 team pages via shared storage key.
**Rationale:** Small, delightful, compounds daily. Readers stop re-collapsing Farm every morning. Minimal diff — tiny JS snippet in the page envelope.
**Downsides:** Choice paradox if the default state drifts from reader preference over time. Needs a "reset layout" escape hatch for users who get stuck.
**Confidence:** 85%
**Complexity:** Low
**Status:** Unexplored
**Evidence:** `build.py:692-777`, `style.css:55-63`

## Rejection Summary

| # | Idea | Reason rejected |
|---|------|-----------------|
| R1 | Hover-to-expand row drill-ins (dead `table.data tr:hover`) | Subsumed by #1 once player rows become hoverable |
| R2 | Default-folded collapse inversion | Contradicts JB's ask for discoverability; hides things harder |
| R3 | Sticky left section rail / mini-map | JB explicitly killed in backlog 2026-04-10 (intent never confirmed) |
| R4 | Scorebook dissolves into native briefing sections | Too architectural; scorebook-as-iframe is working |
| R5 | Side drawer instead of tooltip | A design variant inside #1's brainstorm, not a distinct idea |
| R6 | Section-as-card horizontal deck | Contradicts editorial broadsheet aesthetic |
| R7 | Team-abbreviation → mini-team drawer | Natural follow-up after #1 primitive lands; not standalone yet |
| R8 | Cmd-K spotlight jump-to-player | Depends on #1; power-user follow-up, not a first move |
| R9 | Typed `Mention` dataclass meta-primitive | Absorbed into #1 as the "how," not a separate idea |
| R10 | Pitcher trend lines as dedicated section | Merged into #3 (resurrect discarded data) |
| R11 | At-bat journey + strike zone in three-stars | High-risk variant of #5; defer until #1 primitive lands |
| R12 | Live Everywhere density toggle | Merged into #3 as a natural extension |

## Session Log
- 2026-04-10: Initial ideation — 40 raw candidates across 4 frames (user pain, inversion/removal, reframing, leverage) → 18 after dedupe → 7 survivors. JB's verbatim framing captured in focus field.
- 2026-04-10: JB selected #4 (Unified live-polling core) — "dude i've been thinking about #4 for a while." Handing off to `/ce-brainstorm` to define scope before planning.
