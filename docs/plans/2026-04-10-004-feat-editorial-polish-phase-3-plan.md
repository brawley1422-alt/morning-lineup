---
title: "Editorial Polish Phase 3 — Finish what tonight started"
type: feat
status: in-progress
date: 2026-04-10
---

> **Progress as of 2026-04-10 end-of-session:** Unit 1 shipped (`56ea6f2`), Unit 3 shipped (`0bc90ef`). Unit 2 gated on intent confirmation from JB. Units 4 and 5 pending. See `~/.claude/projects/-home-tooyeezy/memory/project_morning_lineup_design_backlog.md` for the live backlog.

# Editorial Polish Phase 3 — Finish what tonight started

## Overview

Tonight (2026-04-10) we shipped editorial redesigns for auth, reset, 404, the scorecard masthead, and the columnist section on every team briefing page. That leaves the site in a visually inconsistent half-done state: the brand-new columnist accordion (rubric badges, persona sigils, drop caps, full-width top stripe on open) sits on the same team page as the old-treatment headline card, linescore, section chrome, and TOC. This plan finishes the editorial pass so the rest of the team briefing page matches the voice of the columnist block, lands JB's "section numbers should persist on the left" request as a sticky rail, rescues the design-direction prototypes out of `~/tmp/` into a durable location, and queues up the two bigger-scope items (landing authed + scorecard finder view) that got deferred tonight.

No new features. No new data sources. No new backend. Pure CSS + small build-template tweaks + one small JS snippet for the sticky rail's active-section highlight. All 30 teams rebuild with each shipped unit.

## Problem Frame

Readers landing on `/cubs/` tomorrow will see:

- **Top of page** — old editorial lede + old section-header treatment (inline "01 · The Cubs" rubric, old linescore table, no visual three-stars card)
- **Middle of page** — the new columnist accordion we just shipped (rubric badges, sigils, drop caps, full-width open stripe)
- **Rest of page** — old chrome for Stretch, Pressbox, Farm, Slate, Division, Around the League, This Day in History

That inconsistency dilutes the columnist win. The site feels half-finished, not intentionally designed. This plan closes the gap.

Second problem: the set of prototypes we built tonight (`~/tmp/ml-*.html`) are fragile files in a tmp directory. Half of them represent design direction we plan to ship (team polish, landing authed, scorecard finder view); the other half (home, 404, reset, login) represent the source of truth for work already shipped. Either way they need a durable home.

Third problem: JB flagged "section numbers should persist on the left side entirely" but I misread it twice in conversation. The intent (best reconstruction): the per-section rubric numbers currently sit inline with each section heading (`01 · The Cubs`, `02 · Scouting Report`, etc.). He wants them in a sticky left-margin rail visible the whole way down the page, with the currently-scrolled section highlighted — a running table-of-contents column.

## Requirements Trace

- **R1.** Team briefing pages (`/cubs/`, `/yankees/`, ..., all 30) have editorial polish that matches the columnist section's voice: upgraded linescore card, three-stars presentation, section head treatment, TOC bar at the top.
- **R2.** Section numbers persist on the left side of the viewport as a sticky rail with active-section highlighting, visible on all 30 team briefing pages.
- **R3.** Prototype HTML files currently in `~/tmp/ml-*.html` are committed into a durable location in the repo (`docs/design/`) so they survive reboots and are reviewable as reference.
- **R4.** The authed landing page (`/`, built from `landing.html`) gets an editorial pass matching the prototype at `~/tmp/ml-landing-redesign.html`: greeting bar, "Your Team" featured card, team grid with live-game glows.
- **R5.** The scorecard landing state (when hitting `/scorecard/` with no game param) renders today's slate as a game-card grid matching `~/tmp/ml-scorecard-redesign.html`, instead of falling through to the finder's default output.
- **R6.** Every shipped unit maintains current behavior: auth, scorecard app, columnist data pipeline, section rendering all keep working. `sw.js` cache bumped on any change that touches inlined CSS or user-facing HTML. All 30 teams rebuilt per shipped unit.

## Scope Boundaries

**Non-goals / explicit exclusions:**

- **No refactor of `sections/columnists.py`** — it was polished tonight and is done.
- **No changes to `scorecard/app.js`, `scorecard/parser.js`, `scorecard/diamond.js`, `scorecard/scorebook.js`, or the interactive scorecard rendering.** Only the finder's landing-state DOM output changes (Unit 5).
- **No changes to `auth/auth.js`, `auth/reset.js`, `auth/session.js`, `home/home.js`.** Visual polish only.
- **No changes to the `/home/` page.** It already has a functional guest preview flow; the prototype at `~/tmp/ml-home-redesign.html` is a regression in information density and is intentionally not shipping. Document that decision in the backlog note.
- **No backend changes.** No new API calls, no new data fetches, no changes to `data/` format.
- **No new Python dependencies.** Stdlib only.
- **No new JS frameworks.** One small vanilla JS snippet for the sticky rail active-section highlight is the only new JS.
- **No golden snapshot test re-bless unless Unit 1 or Unit 2 changes the rendered HTML for Cubs or Yankees.** If those tests break, re-bless per `tests/README.md`.
- **No changes to daily data refresh or rebuild cadence.**

## Context & Research

### Relevant Code and Patterns

- `sections/headline.py` (479 lines) — renders "The {Team}" section: linescore, three stars, key plays, scorecard embed, team leaders, next three games, form guide (hot/cold hitters + pitchers last 7). Unit 1 target.
- `build.py` (926 lines) — page orchestrator. Relevant regions:
  - `_num = {}` dict (line ~614) builds the section number map for visible sections
  - Page envelope f-string (starts around line ~691) wraps each section with `<section id="...">` + `<span class="num">{_num.get("...","")}</span>` in the header. Unit 2 target for the sticky rail mount point.
- `style.css` — main stylesheet inlined by `build.py` at build time. Unit 1, 2, 4 targets. Tonight's columnist rewrite lives at lines 313–482.
- `landing.html` (253 lines) — landing template with `__TEAMS_JSON__` placeholder replaced at build time. Unit 4 target.
- `scorecard/finder.js` — renders the "find a game" landing state of the scorecard app. Unit 5 target. The rest of the scorecard's 9 JS modules stay untouched.
- `tests/snapshot_test.py` (84 lines) — golden snapshot test for Cubs and Yankees pages. Unit 1 and Unit 2 will likely need a re-bless after shipping.
- `sw.js` + `*/sw.js` (31 copies) — PWA cache version. Currently at `lineup-v4`. Bump with each visual-affecting unit.

### Institutional Learnings (from this session)

- **Screenshot-driven verification catches real bugs before they ship.** The "READ →READ" duplicate-text bug in the column toggle chip would have reached production without the screenshot loop. Every unit in this plan should follow the same loop: local build → screenshot → compare before commit.
- **PWA cache bump needs to mirror across all 30 team sw.js copies.** Tonight's `sed` pattern works: `for f in */sw.js; do sed -i 's/lineup-v[0-9]*/lineup-vN/' "$f"; done` + the root `sw.js`.
- **Rebuild all 30 teams after style.css or build.py changes.** Loop: `for t in $(ls teams/*.json | xargs -n1 basename | sed 's/.json//'); do python3 build.py --team "$t"; done`. Tonight's experience: only rebuilding Cubs leaves the other 29 teams inconsistent for hours.
- **Preserve element IDs when rewriting templates.** The auth/reset pages kept working because every form element ID was preserved for `auth.js`/`reset.js` to bind to. Same rule applies here: don't rename `#columnists`, `section id="team"`, etc.
- **Prototypes in `~/tmp/` rot.** Move them into the repo as reference docs before they get wiped.

### External References

Not needed for this plan — all patterns already exist in the codebase.

## Key Technical Decisions

- **Sticky left rail: `position: sticky` CSS + small IntersectionObserver for active highlight.** Not a fixed-position sidebar (steals horizontal space at narrow widths), not a framework. The rail lives inside the existing `<main>` grid as a left column on wide viewports and collapses to the existing inline section header treatment below a responsive breakpoint (~900px). Sections already have `id` attributes — the rail is just a new `<nav>` block in `build.py`'s page envelope that maps `_num` → `#section-id` links, with one ~30-line vanilla JS snippet for active highlighting.
- **Prototypes land at `docs/design/`** (new directory), not `docs/brainstorms/`. Brainstorms is requirements-doc territory; design-direction HTML mockups are different asset type. Each prototype gets copied verbatim with a header comment noting its origin session and whether it shipped or is pending.
- **Team briefing polish happens in `sections/headline.py` + `style.css` only.** No changes to the section's data model, no new API calls. The three-stars card, linescore upgrade, and TOC bar are pure markup + CSS additions on existing data the section already has in `briefing.data`.
- **Landing authed redesign stays in `landing.html` + inline JS.** The current landing page already fetches live scores and standings at page-load via vanilla fetch to the MLB Stats API. Unit 4 restructures the markup/CSS around those fetches, doesn't rewire them.
- **Scorecard Phase 2B rewrites `finder.js`'s DOM output only.** The data flow (MLB Stats API → schedule → game cards) already exists; we change the HTML that finder generates to match the prototype's game-card grid.
- **Cache bump cadence: one bump per shipped unit.** Currently at `lineup-v4`. Unit 1 ships at `v5`, Unit 2 at `v6`, etc. That's noisy in git history but means a reader hitting the site between units sees a consistent state, not a half-applied visual.
- **Ship units sequentially, not in parallel.** Each unit gets its own commit + push + cache bump + live screenshot verification before the next starts. No stacking uncommitted work.

## Open Questions

### Resolved During Planning

- **"Section numbers persist on left side" — what does JB actually mean?** Best reconstruction: a sticky left-margin rail listing all section numbers with active-section highlight as you scroll. Confirmed with JB before Unit 2 starts if ambiguous (see Unit 2 verification).
- **Do we rebuild all 30 teams or only Cubs for local verification?** Rebuild only Cubs during screenshot iteration (fast loop). Rebuild all 30 immediately before the commit that ships the unit.
- **Where do the prototypes go — `docs/design/`, `docs/brainstorms/`, or a new `reference/`?** Decision: `docs/design/` (new dir). See key technical decisions above.

### Deferred to Implementation

- **Will Unit 1 and Unit 2 break the golden snapshot test?** Almost certainly yes — any markup change to the team page envelope or headline section diffs against the frozen Cubs/Yankees fixtures. Re-bless per `tests/README.md` after the visual is verified.
- **What's the exact responsive breakpoint for the sticky rail to collapse?** Decide during Unit 2 by screenshotting at 1280 / 1024 / 768 / 480 and picking the cutoff where the rail starts to steal content width.
- **Does the landing authed page need a greeting time-of-day aware ("Good morning" vs "Good afternoon")?** Prototype shows "Good morning JB"; decide during Unit 4 whether to make it time-aware (adds ~10 lines of JS) or ship it flat.
- **Does the scorecard finder view need to gracefully fall back when there are no games scheduled?** Decide during Unit 5 — the current finder handles this; the new card grid needs to as well.

## Implementation Units

- [x] **Unit 1: Team briefing polish — headline section + section-head treatment** — shipped in commit `56ea6f2` (2026-04-10). 65 files: sections/headline.py + style.css + all 30 team rebuilds + 2 re-blessed snapshot fixtures + sw.js v4→v5 across 31 copies.

**Goal:** Bring the team briefing page's headline section ("The Cubs", "The Yankees", etc.) up to the editorial voice of the columnist block: upgraded linescore card, dedicated three-stars card, bylined lede block, section-head rubric rework across all numbered sections.

**Requirements:** R1, R6

**Dependencies:** None. This is the first ship.

**Files:**
- Modify: `sections/headline.py` (add three-stars card markup, upgrade linescore rendering)
- Modify: `style.css` (new `.headline-*`, `.linescore-*`, `.three-stars-*`, `.section-head-*` classes)
- Modify: `build.py` (page envelope section header rework if the rubric pattern needs tweaking)
- Rebuild: all 30 `{team}/index.html` files via `python3 build.py --team {slug}` loop
- Bump: `sw.js` + `*/sw.js` (30 copies) to `lineup-v5`
- Test: `tests/snapshot_test.py` — expect a diff; re-bless per `tests/README.md` after visual verification

**Approach:**
- Reference prototype: `~/tmp/ml-team-polish.html`. Match its linescore + three-stars treatment closely.
- Linescore upgrade: replace the plain table with a framed editorial card (double-rule top border, italic Playfair score digits, mono inning headers, persona-color-matched team cells).
- Three-stars card: add a dedicated `<div class="three-stars">` block with three horizontal rows (rank rubric `★ FIRST · ★ SECOND · ★ THIRD`, player headshot or initials, player name italic Playfair, line of stats in mono).
- Section-head rework: the existing `<span class="num">01</span>` inside each section header stays but gets a new treatment matching the columnist `No. I` rubric badge (dashed gold border, mono rubric, matched hover). This also pre-establishes the rail mount points for Unit 2.
- NO changes to the data model. `briefing.data` already has `three_stars`, `linescore`, etc. Just change how they render.

**Patterns to follow:**
- Columnist `No. I/II/III` rubric badge in `style.css` lines ~340 (post-tonight) as the visual template for the new section-head rubric.
- Existing `.linescore` class in `style.css` as the starting point; rewrite, don't layer.

**Test scenarios:**
- Happy path: `python3 build.py --team cubs` produces a page where the headline section shows the new linescore card + three-stars card with all live data present.
- Happy path: `python3 build.py --team yankees` produces the same treatment with Yankees-specific colors (team-primary, team-accent) injected correctly.
- Edge case: A team with no game yesterday (off day) renders without the linescore/three-stars cards but with a styled "No game yesterday" placeholder that doesn't break the section rhythm.
- Edge case: A team with a walk-off win in extra innings renders all 10+ innings in the linescore without overflowing the card width.
- Integration: `python3 tests/snapshot_test.py` runs, produces a diff against the Cubs + Yankees golden snapshots, and the diff is visually correct (not byte-identical — the unit intentionally changes rendered HTML).
- Screenshot verification: rebuild Cubs locally, shoot with Playwright at 1280x900, compare against the columnist section on the same page — they should feel cohesive, not like two different designers' work.

**Verification:**
- Local `file:///home/tooyeezy/morning-lineup/cubs/index.html` screenshot shows the headline section + columnist section as one cohesive editorial treatment.
- All 30 teams rebuild without errors.
- Golden snapshot test is re-blessed and committed.
- Live `https://brawley1422-alt.github.io/morning-lineup/cubs/` screenshot (after push + Pages rebuild) matches local.
- `sw.js` is at `lineup-v5` and all 30 team mirrors match.
- No console errors in the rendered page.

---

- [ ] **Unit 2: Sticky left section rail with active-section highlight**

**Goal:** JB's P1 request — "section numbers should persist on the left side entirely." Add a sticky left-margin rail on team briefing pages listing all section numbers + titles, with the currently-scrolled section highlighted as the reader moves down the page.

**Requirements:** R2, R6

**Dependencies:** Unit 1 (the section-head rubric pattern established there is reused in the rail).

**Files:**
- Modify: `build.py` (inject a new `<nav class="section-rail">` element at the top of the page envelope's `<main>` block, populated from the `_num` dict)
- Modify: `style.css` (new `.section-rail`, `.section-rail-item`, `.section-rail-item.active`, responsive collapse)
- Create (inline in `build.py`): ~30 lines of vanilla JS for IntersectionObserver-based active-section highlighting. Inlined in the page envelope, not a new file.
- Rebuild: all 30 `{team}/index.html` files
- Bump: `sw.js` + `*/sw.js` to `lineup-v6`
- Test: `tests/snapshot_test.py` — expect a diff; re-bless after verification

**Approach:**
- **Confirm intent with JB before starting.** The "sticky left rail" interpretation is my best reconstruction, not a confirmed spec. Post a screenshot mock or quick description before writing code. If the actual intent is different (e.g., move the inline `01 · The Cubs` rubric to the left margin but not sticky, or make the whole section header left-aligned), the design shifts.
- Rail is a `<nav>` element inside the page `<main>` as a flex/grid sibling to the content column. On wide viewports (>1080px): rail is 160px wide, content is fluid. On narrow viewports: rail collapses to `display:none` and the inline section headers stay as the primary nav cue.
- Rail items: one per visible section, each showing `No. I` / `No. II` / `No. III` rubric (matching Unit 1's new rubric pattern) + section title below in Oswald uppercase + a persona-accent dot on hover.
- Active-section highlight: IntersectionObserver watches `section[id]` elements. When a section's top edge crosses the viewport's 30% line, its corresponding rail item gets `.active` class. Remove from all others. Throttle not needed — IO handles it.
- Rail stays pinned via `position: sticky; top: 20px;` on the `<nav>`. Inside the main flex/grid, the content column scrolls while the rail's sticky offset keeps it visible.
- Mobile fallback: `<nav class="section-rail">` is hidden below 1080px. The inline section headers and TOC bar (from Unit 1) handle navigation.

**Patterns to follow:**
- The `_num` dict construction in `build.py` — reuse it directly for the rail's item list instead of hand-maintaining a second list.
- Existing `section[id]` attribute set is the scroll anchor — no new IDs needed.

**Test scenarios:**
- Happy path: Load `/cubs/` at 1280px wide. Rail is visible on the left, shows all sections numbered I–IX. First section is highlighted.
- Happy path: Scroll to "Around the League" — rail active highlight moves to that item.
- Happy path: Click a rail item — smooth-scrolls to that section, active highlight updates.
- Edge case: Load at 800px wide — rail collapses, inline section headers remain the primary nav.
- Edge case: A team with no scouting report (off-day — the scouting section conditionally renders empty) does NOT show "Scouting Report" in the rail.
- Error path: If IntersectionObserver fails to register (very old browser), the rail still renders but without active highlighting — graceful degradation via feature-detect.
- Integration: `python3 tests/snapshot_test.py` produces a diff; re-bless.
- Screenshot verification: shoot at 1280, 1024, 800, 480px.

**Verification:**
- JB confirmed intent before code written.
- All 30 teams render the rail with correct section lists (a team with an empty scouting section has 8 rail items; a team with scouting has 9).
- Active-section highlight updates smoothly during scroll on all tested viewports.
- Mobile fallback hides the rail cleanly, no layout shift.
- Live push + Pages rebuild + screenshot match.
- `sw.js` at `lineup-v6`.

---

- [x] **Unit 3: Rescue prototypes from ~/tmp/ into docs/design/** — shipped in commit `0bc90ef` (2026-04-10). 9 files: 8 prototype HTMLs + README.md index mapping each to shipped/pending status.

**Goal:** Move the 8 HTML prototypes currently in `~/tmp/ml-*.html` into a git-tracked directory in the repo so they survive reboots and are reviewable as reference. Annotate each with origin session + shipped status.

**Requirements:** R3

**Dependencies:** None (can run in parallel with Unit 1 or 2 if needed, but prefer sequential for commit cleanliness).

**Files:**
- Create: `docs/design/README.md` (index of prototypes with shipped/pending status)
- Create: `docs/design/2026-04-10-auth-redesign.html` (from `~/tmp/ml-login-redesign.html`)
- Create: `docs/design/2026-04-10-auth-signup-variant.html` (from `~/tmp/ml-login-redesign-signup.html`)
- Create: `docs/design/2026-04-10-reset-redesign.html` (from `~/tmp/ml-reset-redesign.html`)
- Create: `docs/design/2026-04-10-404-redesign.html` (from `~/tmp/ml-404-redesign.html`)
- Create: `docs/design/2026-04-10-scorecard-finder-redesign.html` (from `~/tmp/ml-scorecard-redesign.html`)
- Create: `docs/design/2026-04-10-team-briefing-polish.html` (from `~/tmp/ml-team-polish.html`)
- Create: `docs/design/2026-04-10-landing-authed-redesign.html` (from `~/tmp/ml-landing-redesign.html`)
- Create: `docs/design/2026-04-10-home-wedge-alternate.html` (from `~/tmp/ml-home-redesign.html`) — marked "NOT shipping — see README"

**Approach:**
- Each file is copied verbatim. No content changes. Self-contained (inline CSS, no external deps beyond Google Fonts).
- The README.md has a table mapping each prototype to: origin date, "Shipped to" column (if applicable — e.g., "auth/index.html + auth/auth.css on 2026-04-10"), "Status" column (Shipped / Pending / Not Shipping).
- The `/home/` wedge prototype gets a one-paragraph note explaining why it's not shipping: the current live `/home/` page has a functional guest preview flow, and this alternate is a regression in information density. Documented so a future reader doesn't think it was forgotten.
- `docs/design/README.md` is linked from the top of `docs/plans/2026-04-10-004-feat-editorial-polish-phase-3-plan.md` (this plan) so future-me can find it.

**Patterns to follow:**
- `docs/solutions/` and `docs/plans/` precedent for "docs subdir with README index of dated files."
- Date-prefixed filenames (`YYYY-MM-DD-<slug>.html`) to match plan filename convention.

**Test scenarios:**
- Test expectation: none — pure file move + README. No runtime behavior.
- Verification by inspection: each file renders correctly when opened locally, README table is accurate.

**Verification:**
- All 8 prototypes exist in `docs/design/` and open correctly in a browser.
- `docs/design/README.md` exists with accurate shipped/pending table.
- `~/tmp/ml-*.html` files can be safely deleted (don't delete yet — keep the tmp copies until Unit 5 ships, in case we need to iterate).
- Commit is small and reviewable (~9 files, no HTML edits).

---

- [ ] **Unit 4: Landing (authed) redesign — greeting + Your Team + team grid glow**

**Goal:** Restructure `landing.html` to match the editorial direction of the rest of the site. Add a greeting bar ("Good morning JB"), a featured "Your Team" hero card for the reader's primary team, and upgrade the team grid with live-game colored glows on cards whose games are currently active.

**Requirements:** R4, R6

**Dependencies:** Unit 1 (reuses some of the new `.linescore`, `.section-head` patterns). Unit 3 (prototype lives in `docs/design/`).

**Files:**
- Modify: `landing.html` (new top greeting bar, Your Team hero markup, team grid restructure)
- Modify: `build.py` (if the `__TEAMS_JSON__` injection needs additional fields like "is the current user's team" — though the reader's team comes from `localStorage` on the client, so probably no build.py change)
- Modify: `style.css` (new `.landing-greeting`, `.landing-hero`, `.landing-grid-card.live` classes)
- Rebuild: `python3 build.py --landing` (single file rebuild, not per-team)
- Bump: `sw.js` + `*/sw.js` to `lineup-v7`
- Test: N/A — landing page has no golden snapshot test

**Approach:**
- Reference prototype: `docs/design/2026-04-10-landing-authed-redesign.html` (from Unit 3).
- Greeting bar: top strip above the masthead, shows `Good morning, <Reader>` on left and today's date + edition number on right. Reader name from `localStorage.getItem('reader_name')` or falls back to "Reader." No auth check — `landing.html` is the first page anyone sees, authenticated or not.
- Your Team hero: if `localStorage.getItem('primary_team')` is set, render a large featured card for that team with masthead-adjacent treatment — italic Playfair team name, live score if playing, next-game time if not, link to `/{team}/`. If no primary team is set, this card is hidden or replaced with a "Pick your team" CTA.
- Team grid: existing 30-team grid stays, but each card gets a new editorial treatment. Cards where the team is currently playing get a pulsing gold border + "LIVE" rubric badge. Cards where the game finished today get a gold win/red loss indicator.
- Live game detection: `landing.html` already fetches live MLB Stats API data on load — reuse that data, don't add new fetches.
- No auth dependency. Do NOT require the reader to be signed in to see the new landing.

**Patterns to follow:**
- The columnist `data-role` persona-color pattern from `style.css` tonight — apply the same trick to team cards using team ID as the selector.
- The existing `__TEAMS_JSON__` substitution pattern in `build.py`.

**Test scenarios:**
- Happy path: Fresh visit with no localStorage — greeting shows "Good morning, Reader", no Your Team hero, team grid renders.
- Happy path: Visit with `primary_team=cubs` in localStorage — Your Team hero shows Cubs with live score if playing.
- Happy path: Mid-game — team cards for teams currently playing pulse with gold border and show live score.
- Edge case: All games final for the day — cards show final score indicator, no LIVE badges anywhere.
- Edge case: No games scheduled (off day in February) — team grid renders without any game state, greeting + hero still work.
- Edge case: Reader whose primary team is on a rest day — hero shows next game time, not a live score.
- Screenshot verification: shoot at 1280x900 with the prototype open in a second tab for side-by-side.

**Verification:**
- `python3 build.py --landing` produces a page matching the prototype.
- Greeting bar adapts to reader name in localStorage.
- Your Team hero adapts to primary team selection.
- Live game detection correctly pulses cards during an active game.
- Live push + screenshot matches local.
- `sw.js` at `lineup-v7`.

---

- [ ] **Unit 5: Scorecard Phase 2B — finder view game-picker grid**

**Goal:** When a reader hits `/scorecard/` with no game ID in the URL, show today's slate as a game-card grid (matching the prototype's editorial treatment) instead of the current default finder output. Clicking a card loads that game into the interactive scorecard app.

**Requirements:** R5, R6

**Dependencies:** Unit 1 (reuses `.linescore`, `.three-stars` patterns for the expanded game view), Unit 3 (prototype lives in `docs/design/`).

**Files:**
- Modify: `scorecard/finder.js` (rewrite the DOM output of the "no game selected" landing state)
- Modify: `scorecard/styles.css` (new `.game-picker`, `.game-picker-card`, `.game-picker-card.live` classes — build on the masthead polish shipped tonight)
- Mirror: copy `scorecard/finder.js` + `scorecard/styles.css` to all 30 `{team}/scorecard/` mirrors (per the "scorecard is duplicated per team" pattern in `CLAUDE.md`)
- Bump: `sw.js` + `*/sw.js` to `lineup-v8`
- Test: N/A — scorecard has no golden snapshot test

**Approach:**
- Reference prototype: `docs/design/2026-04-10-scorecard-finder-redesign.html` (from Unit 3).
- Scope: ONLY the "no game selected" landing state of the finder. When a game IS selected (URL has `?gamePk=...`), the existing scorecard app renders unchanged.
- Data flow: the finder already fetches today's MLB schedule to populate its date picker. Reuse that data — don't add new API calls. Transform the schedule array into a game-card grid DOM.
- Card states: `.live`, `.final`, `.upcoming`, `.no-game-today`. Each card shows: venue, status (LIVE · T6 / Final / 1:20 CT), matchup rows with team logos + names + scores, foot line with WP/LP or pitcher matchup.
- Click handler on each card: sets the URL param and triggers the existing scorecard app's load-game flow. Zero changes to `app.js`, `parser.js`, `diamond.js`, `scorebook.js`.
- Empty state: if no games today, show an editorial "No games on the slate" card with a date picker to pick another day. The existing finder already handles this; reuse its date-picker HTML.

**Patterns to follow:**
- The game-card grid CSS from the prototype's `.games` + `.game` + `.game-row` classes.
- The existing finder's data-fetch logic in `finder.js` — rewrite the render function only.
- The "mirror scorecard files across all 30 team dirs" pattern from tonight's commit `d7807ab`.

**Test scenarios:**
- Happy path: Hit `/scorecard/` with no URL params during the MLB regular season — card grid shows today's slate, at least some games visible.
- Happy path: Click a final game — scorecard app loads that game and renders the full scorebook.
- Happy path: Click a live game — scorecard app loads the live feed, updates as the game progresses.
- Edge case: Load during a double-header — both games render as separate cards.
- Edge case: Load on an MLB off-day — "no games" empty state renders with a working date picker to browse other days.
- Edge case: Load at 2am Central, before MLB schedule rolls over — card grid still shows "yesterday's" games as `.final`.
- Error path: MLB Stats API fetch fails — graceful fallback to the original finder's date picker (don't leave the page blank).
- Integration: Hit `/scorecard/?gamePk=12345` directly — the card grid does NOT render; the game loads straight into scorebook (no regression to the game-selected flow).
- Screenshot verification: local file shot, compare to prototype. Live shot after push.
- Mirror verification: `/cubs/scorecard/` renders the same new card grid as root `/scorecard/`.

**Verification:**
- Root `/scorecard/` and all 30 `{team}/scorecard/` mirrors show the new game-card grid.
- Clicking a card loads that game's full scorebook (regression test).
- Direct-URL game loading still works.
- All existing scorecard app features (diamond rendering, at-bat tooltips, line score, three stars, etc.) unchanged.
- `sw.js` at `lineup-v8`.

## System-Wide Impact

- **Interaction graph:** Units 1, 2, and 4 touch `style.css` which is inlined by `build.py`. Any CSS addition ripples into all 30 team pages + landing at rebuild time. Units 2 and 5 touch behavior (IntersectionObserver for the rail, click handlers on game cards) but both are scoped to new elements, not modifications to existing event handlers.
- **Error propagation:** Unit 2's IntersectionObserver feature-detects and gracefully degrades (rail renders without active highlight if IO fails). Unit 5 wraps the MLB API fetch in a try/catch and falls back to the original finder's date picker UI on error.
- **State lifecycle risks:** None. No data model changes, no new persistent state, no migrations. The only client-side state touched is `localStorage.reader_name` and `localStorage.primary_team` in Unit 4 — both already exist, just being read differently.
- **API surface parity:** The scorecard app's URL-parameter contract (`?gamePk=...`) is unchanged. Unit 5 only changes what happens when the param is absent.
- **Integration coverage:** Golden snapshot test for Cubs + Yankees (`tests/snapshot_test.py`) will diff after Units 1 and 2. Re-bless procedure in `tests/README.md`. No test changes needed for Units 3, 4, or 5 (no snapshot coverage there).
- **Unchanged invariants:** `auth.js`, `reset.js`, `session.js`, `app.js`, `parser.js`, `diamond.js`, `scorebook.js`, `panels.js`, `tooltip.js`, `api.js`, `header.js`, `sections/columnists.py`, `sections/around_league.py`, `sections/stretch.py`, `sections/pressbox.py`, `sections/farm.py`, `sections/slate.py`, `sections/division.py`, `sections/history.py`, `sections/scouting.py`, `home/home.js`, `home/index.html`, `home/home.css`, `build.py` (except for Unit 1's optional page-envelope tweak and Unit 2's rail injection), all team config JSONs, all columnist cache JSONs, all daily data JSONs, `deploy.py`, `evening.py`, `live.js`, `manifest.json`. The daily rebuild cadence and external-deploy flow are untouched.

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Golden snapshot test breaks after Unit 1 or Unit 2, blocking the commit | Expected behavior; re-bless per `tests/README.md` as part of the unit's verification step |
| Sticky rail eats content width at narrow viewports, creating awkward layout | Responsive collapse to `display:none` below 1080px, inline headers handle nav |
| "Sections persist on left" intent mismatch — JB meant something different than sticky rail | Unit 2 gates on confirming intent with JB before writing code |
| Rebuilding all 30 teams after each unit is slow (~2 min per unit × 5 units = 10 min of rebuild time) | Run rebuilds in background while preparing the next unit; not a blocker |
| Team briefing polish creates inconsistency during the ~2 min window between rebuilding all 30 and pushing | Acceptable — nobody hits the site in that window, and the rebuild loop is sequential not staged |
| PWA cache bump cadence — bumping v5/v6/v7/v8 in consecutive commits feels noisy | Accepted cost for consistent visual state per unit; alternative (batching bumps) means intermediate inconsistency for any reader who hits the site between units |
| Unit 4 depends on `localStorage.primary_team` being set — if most readers haven't picked a team, Your Team hero doesn't render | Acceptable; ship it, let the empty state be a clear "Pick your team" CTA |
| Unit 5's click-to-load flow might conflict with existing scorecard app state machine | Mitigated by scoping changes to `finder.js` only and verifying the `?gamePk=...` direct-URL path as an integration test |
| `~/tmp/ml-*.html` files get accidentally deleted before Unit 3 moves them | Unit 3 runs as early as possible; can run concurrent with Unit 1 since there's no code overlap |

## Documentation / Operational Notes

- Each unit's commit message follows the established pattern: `feat(<area>): <one-line summary>` with a multi-line body describing visual + technical changes. Reference `6b0199f` (the columnist editorial redesign commit) as the tonight template.
- Every commit that touches `style.css` or team-facing HTML must also bump `sw.js` + all 30 `*/sw.js` mirrors in the same commit. Non-negotiable.
- Screenshot verification pattern: local build → Playwright shoot → inline via Read → push → wait ~60s for Pages rebuild → shoot live URL → inline → confirm match. `shot-columnists.mjs` is the template.
- Daily rebuild automation (whatever cron/hook is pushing the `daily update {team}` commits) should NOT interfere with these unit commits. If it does, rebase this plan's commits on top of the daily refresh rather than fighting the automation.
- No rollout flag, no feature gate, no A/B. Morning Lineup is a hobby/editorial project with a small readership; ship it straight.
- After Unit 5 ships, update `project_morning_lineup_design_backlog.md` memory to mark the relevant items done.
- After all units ship, write a follow-up memory or `docs/solutions/` note capturing the "rebuild-all-teams → bump-sw → sequential commit" operational pattern so it's discoverable in future sessions.

## Sources & References

- Origin context: conversational recap in Claude Code session 2026-04-10 (no formal brainstorm doc).
- Tonight's commits: `9ff98b2` (auth+reset+404), `b89b849` (columnist accordion), `c8504b7` (daily data), `d7807ab` (scorecard masthead + mirror), `030fe4f` + `50bad20` (sw.js bumps), `6b0199f` (columnist editorial redesign + full team rebuild).
- Design backlog memory: `~/.claude/projects/-home-tooyeezy/memory/project_morning_lineup_design_backlog.md`
- Prototype source-of-truth (to be moved in Unit 3): `~/tmp/ml-*.html`
- Tonight's screenshot artifacts: `~/tmp/screenshots/columnists-{collapsed,expanded}{,-local}.png`
- Relevant tests: `tests/snapshot_test.py`, `tests/README.md`
- Build/deploy docs: `CLAUDE.md` (root of `~/morning-lineup/`)
