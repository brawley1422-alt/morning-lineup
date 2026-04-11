---
title: "feat: Player Cards MVP — Cubs lineup + SP"
type: feat
status: active
date: 2026-04-11
origin: docs/brainstorms/2026-04-11-player-cards-mvp-requirements.md
---

# feat: Player Cards MVP — Cubs lineup + SP

## Overview

Ship the Topps-style flip card from the prototype (`docs/design/2026-04-11-player-card-prototype.html`) as a working feature on the Cubs briefing page. Click any of today's 9 Cubs starters or the starting pitcher → the card opens with real MLB Stats API data pulled during the nightly cron. No underlines, no visual hints — names look like plain text but reward a tap with a collectible card.

This plan covers Phase 1 only: Cubs-only, lineup + SP, MLB-API stats. Baseball Savant Statcast metrics and the other 29 teams are explicitly deferred.

Based on findings from `docs/brainstorms/2026-04-11-player-cards-mvp-requirements.md`, the feature is a data-pipeline problem dressed as a card-design problem. One card template, one data artifact, one web component.

## Problem Frame

The prototype demonstrates the visual and interaction target. What's missing: a way to get real player data into it, wire clicks on player names in the rendered Cubs page, and let the nightly cron keep everything fresh. `build.py` already fetches rosters, game logs, and lineups for the Cubs today (`build.py:251` roster fetch, `build.py:357` gameLog fetch, `build.py:143-172` lineup fetch) — but it throws that data away after rendering narrative prose. The plan lifts that data into a structured artifact the card can consume.

(See origin: `docs/brainstorms/2026-04-11-player-cards-mvp-requirements.md`)

## Requirements Trace

Every requirement and success criterion from brainstorm findings maps to at least one implementation unit below.

- **R1** — Per-team `players-{team}.json` artifact → Unit 1
- **R2** — Tiered advanced-stat sourcing (MLB API only, Savant deferred) → Unit 1, Unit 2
- **R3** — Precomputed 15-game temp strip → Unit 2
- **R4** — Phase 1 player coverage: Cubs lineup + SP → Unit 1, Unit 6
- **R5** — Headshot URLs sourced from MLB CDN → Unit 1
- **R6** — `<player-card>` web component → Unit 3
- **R7** — Lazy card construction → Unit 3
- **R8** — Flip interaction preserved → Unit 3
- **R9** — Invisible click affordance → Unit 4
- **R10** — Cubs-only in Phase 1 → Unit 5
- **R11** — Nightly refresh via existing cron trigger → Unit 6
- **R12** — Graceful fallback when data missing → Unit 3
- **R13** — `players-cubs.json` as a first-class artifact → Unit 1

- **SC1** — Click-to-card works end-to-end on live Cubs page → Units 1+3+4+5+6
- **SC2** — Front of card matches prototype fidelity → Unit 3
- **SC3** — Back of card shows real MLB-API advanced stats → Unit 1, Unit 3
- **SC4** — Nightly regeneration is automatic → Unit 6
- **SC5** — Non-Cubs pages are unaffected → Unit 5
- **SC6** — Card opens in under 300ms on mobile → Unit 3
- **SC7** — Zero-effort Phase 2 path exists → Unit 1 (schema), Unit 3 (component)

## Scope Boundaries

- **In scope:** Cubs page only. Today's 9 starting hitters + 1 starting pitcher. `players-cubs.json` generated nightly. `<player-card>` web component in one JS file. MLB Stats API as the only data source. Invisible click affordance. Flip interaction from prototype. Stub fallback for missing data.
- **Out of scope:** Baseball Savant CSV (Phase 1.5). Other 29 teams (Phase 2). Bullpen/bench/IL coverage (Phase 3). Prospects, historical players, scouting blurb, PNG export, deep-link URLs, dagger affordance, hover preview, disambiguation picker, Scorecard Book integration, Brain wiki ingest.

## Context & Research

### Relevant Code and Patterns

- `build.py:36` — `load_team_config(team_slug="cubs")` — entry point for per-team configuration. Pattern to follow: new pipeline work should run inside the existing per-team loop, not alongside it.
- `build.py:72` — `fetch()` helper wrapping MLB Stats API calls with a consistent User-Agent. Reuse for all new endpoints.
- `build.py:95` — `load_all()` — orchestrates every MLB API pull for the day. Best place to add a `load_player_cards()` step.
- `build.py:143-172` — existing lineup fetch logic reads `feed.get("gameData", {}).get("players", {})`. Every player ID for today's lineup is already in hand here.
- `build.py:251` — `fetch(f"/teams/{TEAM_ID}/roster", rosterType="40Man")` — already retrieves the 40-man roster. Phase 2 expansion has zero API work beyond this.
- `build.py:357` — existing gameLog fetch `fetch(f"/people/{pid}/stats", stats="gameLog", ...)` — the temp strip precomputation (R3) can mirror this exact pattern.
- `build.py:421` — `build_briefing(team_slug)` — renders the briefing dict into the template. The place to inject player-card anchor wrapping.
- `build.py:569` — `page(briefing)` — HTML render function. The `<player-card>` wrapping happens here, in the lineup/pitching matchup sections specifically.
- `build.py:835` — `save_data_ledger(data)` — writes `data/{date}.json`. `save_players_cubs(players)` should mirror this shape and write to `data/players-cubs.json`.
- `docs/design/2026-04-11-player-card-prototype.html` — prototype with working flip, temp strip interpolation, and advanced-stat layout. Source of truth for the component's DOM and CSS.
- `sections/` subpackage (`sections.scouting`, `sections.pressbox`, etc.) — existing pattern for encapsulating page-section logic. If Unit 1's data pull grows beyond ~50 lines, extract to `sections/player_cards.py`.

### Institutional Learnings

- Brainstorm findings (`docs/brainstorms/2026-04-11-player-cards-mvp-requirements.md` R11) mandate no new cron trigger. The existing `trig_01SYeMH3jjCZAnRnEoj1sE7n` at 08:00 UTC already regenerates the Cubs page — Unit 6 piggybacks on it with zero trigger-config changes.
- Prior `chore(sw): bump cache version to lineup-v3` commits (recent git log) show the service worker's cache-versioning pattern. Any new static asset (`assets/player-card.js`) must bump that version.
- User preference from memory: "always rebuild all teams" when changing shared assets. Unit 5 enforces this by ensuring the non-Cubs teams rebuild unchanged — the `<player-card>` script is loaded but the wrapping pass is gated to Cubs.

### External References

No external research dispatched — the codebase has strong local patterns for every piece (API fetching, JSON ledger writing, per-team build, HTML rendering, service-worker cache versioning). MLB Stats API contracts are stable and already in active use in `build.py:72` and `build.py:357`.

## Key Technical Decisions

- **Decision: `players-cubs.json` is a sibling artifact to `data/{date}.json`, not part of it.** Rationale: keeps the existing 2.2MB daily ledger focused on game/lineup data; isolates player-card schema evolution; matches the per-team artifact pattern already implied by `build.py:421` `build_briefing(team_slug)`.
- **Decision: `<player-card>` is a web component, not a React/Vue component or a global event-delegated modal.** Rationale: brainstorm R6 (HIGH confidence); one self-contained file; portable to Scorecard Book and future surfaces with zero dependency changes; upgrade is automatic when the element is defined.
- **Decision: Name-to-ID wrapping happens in `build.py:569` `page()` on structured data only (lineup + pitching matchup blocks), not on prose or transactions.** Rationale: brainstorm open question 5; structured blocks already carry player IDs from `build.py:143-172`; prose wrapping is Phase 2+ and needs a separate name-resolution strategy.
- **Decision: Temp strip metric is rolling OPS for hitters, rolling ERA (last 5 starts) for SP.** Rationale: both are directly computable from the same gameLog endpoint already called at `build.py:357`; simpler than wOBA (which needs linear weights); matches what the prototype visually implies.
- **Decision: Headshot URLs are stored in `players-cubs.json` but images load directly from MLB CDN.** Rationale: brainstorm R5 (HIGH); zero image hosting, zero bandwidth cost, proven in the prototype.
- **Decision: JSON schema is unversioned for Phase 1, with a top-level `"generated_at"` timestamp.** Rationale: brainstorm open question 4; premature versioning without a consumer fleet; Phase 1.5 can introduce `"schema": "v1"` if needed.
- **Decision: Component JS lives at `assets/player-card.js`, loaded via `<script defer>` from each team's `index.html` template.** Rationale: brainstorm open question 3; lets the service worker cache it as a static asset; defers parsing past first paint.
- **Decision: Invisible affordance means `player-card` elements render exactly like the surrounding text node — no underline, no color change, no cursor change, no hover tint.** Rationale: brainstorm R9 (MEDIUM) and explicit user choice during brainstorm session. Acceptable discoverability trade for editorial purity.

## Open Questions

### Resolved During Planning

- **Temp strip metric** → Rolling OPS (hitters) and rolling ERA over last 5 starts (pitchers). See Key Technical Decisions.
- **Component JS location** → `assets/player-card.js`. See Key Technical Decisions.
- **JSON schema versioning** → Unversioned for Phase 1, add `"generated_at"` timestamp. See Key Technical Decisions.
- **Name-to-ID wrapping locus** → Structured blocks only (lineup, pitching matchup). See Key Technical Decisions.
- **Service worker cache bump strategy** → Bump `lineup-v3` → `lineup-v4` as part of Unit 5 since it adds a new static asset.

### Deferred to Implementation

- **Build time budget impact** — The added per-player gameLog fetch (10 calls for 10 players, ~200ms each serial) likely adds 2–3s to `build.py --team cubs`. Measure during Unit 1; if over 15s, parallelize via `concurrent.futures.ThreadPoolExecutor` using the pattern already available to `urllib.request`.
- **Pitcher temp strip edge case** — A starter with fewer than 5 career starts (callup, rehab) needs a fallback. Decide during Unit 2: pad with "—" or shorten the strip.
- **Exact field names in the advanced-metrics back section** — Planning is stopping at "whatever MLB Stats API exposes." Specific field-to-cell mapping resolved in Unit 3 against the prototype's layout.

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

```
                    ┌────────────────────────────────────────────┐
                    │  Nightly cron (trig_01SYeMH3jjCZAnRnEoj1sE7n)│
                    │  08:00 UTC                                  │
                    └──────────────────┬─────────────────────────┘
                                       │
                                       ▼
    ┌──────────────────────────────────────────────────────────────────┐
    │  build.py --team cubs                                             │
    │                                                                   │
    │  load_all()                                                       │
    │    ├── existing MLB API fetches (lineup, roster, gameLog)         │
    │    └── NEW: load_player_cards(lineup_ids + sp_id)                 │
    │                └── for each pid:                                   │
    │                    fetch /people/{pid}                             │
    │                    fetch /people/{pid}/stats?type=season           │
    │                    fetch /people/{pid}/stats?stats=gameLog&last=15 │
    │                    compute rolling_ops | rolling_era               │
    │                    build player_record dict                        │
    │                                                                   │
    │  page(briefing)                                                   │
    │    └── in lineup + pitching-matchup HTML blocks:                  │
    │        wrap known player names in <player-card pid="X">...</>     │
    │                                                                   │
    │  save_players_cubs(players) → data/players-cubs.json              │
    │  render                      → cubs/index.html                    │
    └──────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
                           ┌──────────────────────────┐
                           │  git commit + push        │
                           │  GitHub Pages deploys     │
                           └────────────┬──────────────┘
                                        │
                                        ▼
    ┌──────────────────────────────────────────────────────────────────┐
    │  Browser — cubs/index.html                                        │
    │                                                                   │
    │  <script defer src="../assets/player-card.js"></script>          │
    │                                                                   │
    │  <player-card pid="691718">Pete Crow-Armstrong</player-card>     │
    │         │                                                         │
    │         │ (plain text until click)                                │
    │         ▼                                                         │
    │  click → element fetches data/players-cubs.json (once, cached)   │
    │       → looks up pid                                              │
    │       → injects Topps overlay into DOM                            │
    │       → flip animation on click                                   │
    └──────────────────────────────────────────────────────────────────┘
```

## Implementation Units

- [ ] **Unit 1: Player card data pipeline in `build.py`**

**Goal:** Extend `build.py --team cubs` to fetch per-player data for today's lineup + SP and write `data/players-cubs.json` alongside the existing page render.

**Requirements:** R1, R2, R4, R5, R13, SC3

**Dependencies:** None.

**Files:**
- Modify: `build.py` (add `load_player_cards()` near `build.py:95` `load_all()`; add `save_players_cubs()` near `build.py:835` `save_data_ledger()`)
- Create: `data/players-cubs.json` (build artifact, initial sample committed for reference)
- Test: `tests/test_player_cards.py` (new file; Morning Lineup has no test dir today — if absent, create it and use stdlib `unittest` since no pytest dependency is declared)

**Approach:**
- New function `load_player_cards(pids: list[int]) -> dict[int, dict]` that for each player ID calls `/people/{pid}` (biographical), `/people/{pid}/stats?stats=season&group=hitting|pitching` (season line), and `/people/{pid}/stats?stats=gameLog&group=hitting|pitching` (temp strip source). Reuses the `fetch()` helper at `build.py:72`.
- Output schema: `{ "generated_at": ISO-8601, "team": "cubs", "players": { "691718": { "id", "name", "position", "jersey", "bats_throws", "age", "height", "weight", "headshot_url", "season": {...}, "career": [...], "temp_strip": [0.0..1.0] x 15, "advanced": {...} } } }`.
- Call site inside `load_all()` after the existing lineup fetch at `build.py:143-172` — reuse the `pids` list already being built.
- `save_players_cubs()` mirrors `save_data_ledger()` at `build.py:835` but writes to `data/players-cubs.json`.

**Patterns to follow:**
- `build.py:72` `fetch()` helper for all MLB API calls.
- `build.py:357` existing gameLog fetch as the template for per-player gameLog calls.
- `build.py:835` `save_data_ledger()` for the write pattern.

**Test scenarios:**
- Happy path: given a list of 10 valid player IDs (9 hitters + 1 SP), `load_player_cards()` returns a dict keyed by id with every schema field populated. Assert the temp_strip has exactly 15 floats in [0,1].
- Edge case: a player with fewer than 15 gameLog entries (e.g., an early-season callup) returns a temp_strip padded with None/null for missing games; card will render those cells neutral.
- Edge case: a starting pitcher with fewer than 5 career starts — pitcher temp strip falls back to "appearances" cadence; assert it still returns a non-empty list.
- Error path: MLB API returns 404 for a player ID (retired, wrong ID) — function logs a warning and omits that player from the output dict rather than raising.
- Error path: MLB API returns 500 or times out on one player — the other 9 still complete; overall function does not raise.
- Integration: the JSON file on disk validates against the schema (key presence, temp_strip length, numeric ranges).

**Verification:**
- After running `python3 build.py --team cubs`, `data/players-cubs.json` exists and contains records for every player in today's lineup plus the SP.
- The file is under 100KB (sanity check — 10 players × ~5KB each).
- Running `python3 build.py --team dodgers` does not touch `data/players-cubs.json` (Cubs-only gating in place).

---

- [ ] **Unit 2: Precomputed temp-strip helper**

**Goal:** Isolate the rolling-OPS (hitters) / rolling-ERA (pitchers) temp strip computation into a small pure function so it's trivially testable and reusable when Phase 2 fans out to other teams.

**Requirements:** R3

**Dependencies:** Unit 1 (calls the helper).

**Files:**
- Modify: `build.py` (add `compute_temp_strip(game_log: list, role: str) -> list[float]` — pure function, no IO)
- Test: `tests/test_temp_strip.py`

**Approach:**
- Input: raw gameLog list from MLB API for one player, and role ∈ {"hitter", "pitcher"}.
- For hitters: compute OPS per game, then normalize by clamping to a reasonable season range (e.g., 0.0 to 1.500) and rescaling to [0,1].
- For pitchers: compute ERA over last 5 starts (rolling per game), normalize inversely (lower = hotter) to [0,1].
- Returns a 15-length list of floats, padded with `None` for missing games.

**Patterns to follow:**
- Keep it stdlib-only. No numpy, no pandas. Matches `build.py`'s zero-dependency philosophy (`build.py:7-24` imports are all stdlib + local sections).

**Test scenarios:**
- Happy path (hitter): given a 15-game log of realistic hitter stats, returns 15 floats in [0,1]. Assert the player with perfect games scores near 1.0 and 0-for games score near 0.0.
- Happy path (pitcher): given 5 starts, returns a 5-element array (or 15 padded); sub-2.00 ERA games score near 1.0, 8.00+ ERA games score near 0.0.
- Edge case: empty gameLog → returns 15 None values.
- Edge case: gameLog with 3 entries → returns [val, val, val, None, None, ...None].
- Edge case: a game where the hitter had 0 ABs (pinch-runner) → that slot is None, not 0.0.
- Edge case: a pitcher with a single blow-up (12.00 ERA in 1 inning) → bounds-clamped to 0.0, not a wild negative.

**Verification:**
- Pure function with no IO. Unit tests alone prove correctness.
- Called from Unit 1; sample output in `data/players-cubs.json` passes visual inspection against the prototype's expected temp-strip colors.

---

- [ ] **Unit 3: `<player-card>` web component**

**Goal:** Port the prototype card HTML/CSS/JS into a reusable custom element that reads from `data/players-cubs.json` and renders the flip overlay on click.

**Requirements:** R6, R7, R8, R12, SC2, SC3, SC6

**Dependencies:** Unit 1 (for the JSON schema shape).

**Files:**
- Create: `assets/player-card.js` (component source)
- Create: `assets/player-card.css` (extracted from the prototype's inline styles, or co-located in JS via adopted stylesheets)
- Test: `tests/test_player_card.html` (manual browser fixture — opens the component with a fixture JSON; no headless runner needed for Phase 1)

**Approach:**
- Define `class PlayerCard extends HTMLElement` with `connectedCallback` attaching a click listener to itself. Default rendering = inline text from the element's own textContent (the player name).
- On first click anywhere on the page across any `<player-card>`, fetch `data/players-cubs.json` once, cache the result in a module-level variable.
- On click: look up `this.getAttribute('pid')` in the cached JSON. If present, inject the Topps overlay (body-scoped div, fixed positioning, backdrop blur) and flip-to-back behavior from the prototype. If absent, render the stub fallback: "{name} · Cubs · Card coming soon".
- Overlay is created once per card click, removed on close (Escape, click outside, X button). No persistent DOM.
- Flip behavior copied verbatim from `docs/design/2026-04-11-player-card-prototype.html` including the `-webkit-backface-visibility` + `translateZ(0.1px)` fix.

**Patterns to follow:**
- Morning Lineup's `live.js` (referenced in `project_morning_lineup.md` memory) — vanilla JS IIFE, no dependencies, no frameworks. Match that pattern.
- Service worker caching: bump version (Unit 5) so the new asset is picked up.

**Test scenarios:**
- Happy path: clicking a `<player-card pid="691718">` where the pid exists in the fixture JSON opens the overlay with the correct headshot, name, slash line, temp strip, and back-face stats.
- Happy path: clicking the overlay flips to the back face. Pressing Escape closes.
- Edge case: clicking a `<player-card pid="999999">` with no record in the JSON shows the stub fallback — "{name} · Cubs · Card coming soon" — and does not throw.
- Edge case: the component renders correctly when `<player-card>` is upgraded after the document is already parsed (simulate dynamic content).
- Error path: `data/players-cubs.json` returns 404 or invalid JSON — every click shows the stub fallback; no uncaught exceptions in the console.
- Integration: opening two different cards in sequence reuses the cached JSON (single network request in devtools).
- Integration: card front → flip → back → flip → front → close → reopen renders with animations reset correctly each time.

**Verification:**
- Manual: open `tests/test_player_card.html`, click through the happy and edge cases. All render without console errors.
- Performance: first-click overlay injection under 300ms on a mid-range phone (SC6).

---

- [ ] **Unit 4: Wrap Cubs lineup + SP names in `<player-card>` tags in `build.py` render**

**Goal:** Emit `<player-card pid="X">Name</player-card>` around every player name rendered in the Cubs lineup and pitching-matchup HTML sections.

**Requirements:** R6, R9, SC1

**Dependencies:** Unit 3.

**Files:**
- Modify: `build.py` (the `page()` function starting at `build.py:569` and any section templates it delegates to — `sections/slate.py`, `sections/pressbox.py` likely candidates)
- Test: `tests/test_page_wrap.py`

**Approach:**
- Identify the HTML string-building sites where lineup hitters and starting pitcher names are written out in the current Cubs page render.
- Replace `<span class="lineup-name">{name}</span>` (or equivalent) with `<player-card pid="{pid}">{name}</player-card>` when a player ID is known.
- When pid is not known (edge case — lineup data missing a mapping), fall back to the old plain-text render so nothing breaks.
- Do not touch the prose-rendering sections (columnists, transactions, farm reports) — those are out of scope per the name-to-ID wrapping decision.

**Patterns to follow:**
- Existing HTML-string building in `build.py:569` `page()` — f-strings, no templating framework.

**Test scenarios:**
- Happy path: given a lineup with 9 players all having pids, the rendered HTML contains exactly 9 `<player-card>` tags, each with a `pid` attribute and correct inner text.
- Happy path: the starting pitcher name in the pitching matchup section is wrapped similarly.
- Edge case: a lineup slot with no pid (data missing) renders as plain text, no `<player-card>` tag.
- Edge case: a player whose name contains an apostrophe or hyphen (e.g., Crow-Armstrong, O'Neill) renders correctly inside the tag — no broken HTML.
- Integration: the page renders as valid HTML (no unclosed tags) and the service worker pre-cache step does not choke on it.

**Verification:**
- Running `python3 build.py --team cubs` produces a `cubs/index.html` that contains `<player-card` at least 10 times (9 hitters + SP).
- Non-Cubs teams render with zero `<player-card>` tags (Cubs-only gating confirmed).

---

- [ ] **Unit 5: Load component + bump service worker cache**

**Goal:** Reference `assets/player-card.js` and `assets/player-card.css` from the Cubs page template and bump the service worker cache version so existing users pick up the new assets.

**Requirements:** R10, SC5

**Dependencies:** Unit 3.

**Files:**
- Modify: `build.py:569` (or the shared HTML head template it produces) — add `<link rel="stylesheet" href="/morning-lineup/assets/player-card.css">` and `<script defer src="/morning-lineup/assets/player-card.js"></script>` to the Cubs page head
- Modify: `sw.js` (team-level) — bump cache name from `lineup-v3` to `lineup-v4` and add the new assets to the pre-cache list
- Test: manual smoke — open the Cubs page in an incognito window, confirm `player-card.js` loads in the network tab

**Approach:**
- Gate the script/stylesheet injection so only `--team cubs` outputs it. Other teams' pages remain byte-identical to today (SC5).
- Bump `lineup-v3` → `lineup-v4` exactly once in `sw.js`. Add `/morning-lineup/assets/player-card.js` and `/morning-lineup/assets/player-card.css` to the precache list.

**Patterns to follow:**
- Prior commits `50bad20 chore(sw): bump team sw.js cache to lineup-v3` and `030fe4f chore(sw): bump cache version to lineup-v3` (recent git log) — exactly this pattern, one version up.

**Test scenarios:**
- Test expectation: smoke-only — this unit is pure config/wiring. Verification via the live Cubs page loading the new assets without 404s.

**Verification:**
- `curl -sI https://brawley1422-alt.github.io/morning-lineup/assets/player-card.js` returns 200 after deploy.
- Opening cubs/index.html in a fresh incognito window shows the new cache key in devtools → Application → Cache Storage.
- Opening any non-Cubs team page shows zero new network requests for player-card assets.

---

- [ ] **Unit 6: Trigger-prompt audit (no change unless needed)**

**Goal:** Confirm the existing `trig_01SYeMH3jjCZAnRnEoj1sE7n` cron trigger regenerates `players-cubs.json` correctly without any trigger-prompt modification, since Unit 1 already wires the new artifact into the existing `build.py --team cubs` loop.

**Requirements:** R11, SC4

**Dependencies:** Units 1, 4, 5 all deployed to main.

**Files:**
- Audit: trigger prompt via `RemoteTrigger` `get` action
- Modify (only if needed): trigger prompt via `RemoteTrigger` `update` action

**Approach:**
- Fetch the current trigger prompt. The prompt today runs `for team in ...; do python3 build.py --team "$team"; done` followed by `python3 deploy.py`. As long as Unit 1's `save_players_cubs()` writes to a path that `deploy.py` already pushes (`data/*.json` appears to be globbed — verify), no trigger change is needed.
- If `deploy.py` does not currently include `data/players-cubs.json` in its push list, modify `deploy.py` rather than the trigger prompt.

**Patterns to follow:**
- Existing `data/{date}.json` ledger write is already picked up by `deploy.py` nightly (confirmed by memory project state). Mirror that pattern.

**Test scenarios:**
- Test expectation: none — verification is observational (watch tomorrow's cron run land).

**Verification:**
- 24 hours after Phase 1 deploys, pull `https://brawley1422-alt.github.io/morning-lineup/data/players-cubs.json` and confirm its `generated_at` timestamp is from this morning's cron run.
- The live Cubs page shows updated player stats (e.g., yesterday's box score reflected in season totals).

## System-Wide Impact

- **Interaction graph:** `<player-card>` element listens for its own clicks only. No global event delegation. No interference with existing live-game widget (`live.js`) — separate namespace, separate concerns.
- **Error propagation:** Component catches JSON fetch errors and falls back to the stub card (R12). `build.py` catches per-player API failures and omits the player rather than crashing the build (Unit 1 error-path tests).
- **State lifecycle risks:** Card overlay is ephemeral — created on click, removed on close. No persistent state, no leaks. JSON cache is module-scoped, lives for the page session only.
- **API surface parity:** The `<player-card>` element is team-agnostic by design (reads its JSON source from a path derived from the page context). Phase 2 reuses the same component with `data/players-{team}.json`.
- **Integration coverage:** Build-time wrapping + runtime component rendering is a two-layer concern. Unit 4's integration test (HTML contains expected tags) + Unit 3's manual fixture test (component renders correctly against fixture JSON) cover both halves.
- **Unchanged invariants:** Non-Cubs team pages render byte-identically to today (SC5). `data/{date}.json` ledger format unchanged. `live.js` live-game widget unchanged. Service worker structure unchanged (only cache name bumped).

## Risks & Dependencies

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Per-player gameLog fetches blow the 15-min cron budget | Medium | High | Unit 1 deferred note: measure during build; parallelize with `ThreadPoolExecutor` if over 15s added. MLB API is historically fast (~200ms per call, 10 calls = ~2s serial). |
| MLB API headshot CDN URL pattern changes | Low | Medium | Proven stable in prototype. Fallback to initials-in-colored-block if 404 detected (Unit 3 can add a `<img onerror>` handler). |
| Service worker caches old `index.html` + new `player-card.js` and component errors because `<player-card>` tags aren't in old HTML | Low | Low | Cache bump in Unit 5 forces refresh. Component gracefully no-ops on pages without `<player-card>` elements. |
| Backface-visibility bug in iOS Safari (separate from the one already fixed in the prototype) | Low | Medium | Manual test on JB's phone during Unit 3. Prototype already has the `translateZ(0.1px)` fix. |
| Edge case: a player with a hyphen or apostrophe in name breaks HTML attribute escaping | Low | Medium | Unit 4 test scenario covers this. Use `html.escape()` on the name before wrapping. |
| `deploy.py` doesn't ship `data/players-cubs.json` and the cron silently doesn't publish it | Medium | High | Unit 6 audits this before considering Phase 1 shipped. Fix in `deploy.py` not the trigger prompt. |
| Build time for Unit 1 data pull pushes total `build.py --team cubs` over the user's acceptable threshold | Low | Medium | Parallelize per-player fetches as noted above. Even worst case keeps Cubs build under the existing full-league rebuild time. |

**Dependencies (external):**
- MLB Stats API availability (already a hard dep of the entire project — no new surface)
- MLB CDN headshot URLs (proven stable in prototype)
- GitHub Pages static hosting (already the shipping path)

**Dependencies (internal, must land in order):**
- Unit 1 → Unit 2 (Unit 1 calls `compute_temp_strip`)
- Unit 1 → Unit 3 (Unit 3 consumes the JSON schema Unit 1 produces)
- Unit 3 → Unit 4 (Unit 4 wraps names expecting the component exists)
- Unit 3 → Unit 5 (Unit 5 loads the component asset)
- Units 1, 4, 5 all merged → Unit 6 (observational verification)

## Documentation / Operational Notes

- After Unit 6 verification, update `docs/brainstorms/2026-04-11-player-cards-mvp-requirements.md` status from "Ready for /ce:plan" to "Shipped 2026-04-XX".
- Add a one-line mention to `README.md` under "Features" so the portfolio-grade README (commit `529f6de`) reflects the new capability.
- No operational monitoring needed. Failure mode is "cards don't open" — observable on next visit, no silent data corruption risk.
- Phase 1.5 (Savant integration) and Phase 2 (other 29 teams) get their own plans. Do not preemptively scaffold either in Phase 1.

## Sources & References

- **Origin document:** `docs/brainstorms/2026-04-11-player-cards-mvp-requirements.md`
- **Upstream ideation:** `docs/ideation/2026-04-11-player-cards-scaling-ideation.md`
- **Prototype:** `docs/design/2026-04-11-player-card-prototype.html`
- **Key code references:**
  - `build.py:36` — `load_team_config()`
  - `build.py:72` — `fetch()` helper
  - `build.py:95` — `load_all()` orchestration
  - `build.py:143-172` — existing lineup fetch
  - `build.py:251` — existing roster fetch
  - `build.py:357` — existing gameLog fetch
  - `build.py:421` — `build_briefing()`
  - `build.py:569` — `page()` HTML render
  - `build.py:835` — `save_data_ledger()`
- **Recent git history patterns:**
  - `50bad20` / `030fe4f` — service worker cache version bump pattern
  - `c8504b7` — daily data refresh commit pattern
  - `529f6de` — portfolio README context
