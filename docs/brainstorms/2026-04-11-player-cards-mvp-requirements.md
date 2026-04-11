# Player Cards MVP — Requirements

**Date:** 2026-04-11
**Author:** JB + Claude (brainstorm session)
**Source ideation:** `docs/ideation/2026-04-11-player-cards-scaling-ideation.md`
**Prototype:** `docs/design/2026-04-11-player-card-prototype.html`
**Status:** Ready for `/ce:plan`

---

## Overview

Scale the Topps-style flip card from the Pete Crow-Armstrong prototype into a working feature on the Morning Lineup Cubs page. Click any lineup or starting-pitcher name on `cubs/index.html` → the flip card opens with real MLB data sourced via the nightly `build.py` cron. Phase 1 ships Cubs-only to validate the full pipeline (data → JSON → component → click handler) before fanning out to all 30 teams in later phases.

The user-facing magic stays invisible: no underlines, no visual hints. Names look like plain text but reveal a collectible card on tap — an Easter egg that rewards curiosity.

---

## Requirements

Stable IDs for traceability into planning.

### Data Layer

- **R1 — Per-team `players-{team}.json` artifact** `[HIGH]`
  `build.py` emits one JSON blob per team alongside the existing `{team}/index.html`, containing every player needed by that team's card experience. File lives at `data/players-{team}.json` (repo-relative). Regenerated every nightly cron run.

- **R2 — Tiered advanced-stat sourcing** `[HIGH]`
  Phase 1 data comes **only** from the MLB Stats API (public, unauthed). Card back shows what MLB exposes: traditional slash, OPS+, ERA+, wOBA, career year-by-year, IP/K/BB rates. Baseball Savant Statcast fields (xwOBA, Barrel%, HardHit%, Sprint Speed, Stuff+) are **deferred to Phase 1.5**. The card template renders those fields as "—" when absent.

- **R3 — Precomputed 15-game temperature strip** `[HIGH]`
  For each hitter, `build.py` pulls the last 15 `gameLog` entries from the MLB Stats API, computes a rolling metric (wOBA or OPS, TBD in planning), normalizes 0–1, and stores a 15-element array in `players-{team}.json`. The front-of-card strip reads directly from that array with zero client-side math. Pitchers get an equivalent strip based on their last 5–10 appearances (exact cadence TBD).

- **R4 — Phase 1 player coverage: "Nine and the Arm" for Cubs** `[HIGH]`
  Data pipeline must produce full card-ready records for every Cubs player who appears in today's lineup (9 hitters) plus the starting pitcher. Anything beyond that (bullpen, bench, IL, transactions, prospects) is **out of scope for Phase 1**.

- **R5 — Headshot URLs sourced from MLB CDN** `[HIGH]`
  Use the existing MLB Stats API headshot pattern (`https://img.mlbstatic.com/mlb-photos/.../{player_id}/...`) — proven in the prototype. Store the URL in `players-cubs.json`; the card loads the image directly from MLB's CDN at render time. No self-hosted photos.

### Component Layer

- **R6 — `<player-card>` web component** `[HIGH]`
  A single self-contained custom element. `build.py` wraps known player names in `<player-card pid="691718">Pete Crow-Armstrong</player-card>`. The element renders as inline plain text by default (no underline, no marker) and injects the Topps flip overlay on click. Source lives in one JS file consumed by every team page's HTML.

- **R7 — Lazy card construction** `[HIGH]`
  The overlay DOM is built only when the user clicks. The team page pays no layout cost for unopened cards. The component fetches `data/players-cubs.json` once per session on first click and caches it in memory for subsequent opens.

- **R8 — Flip interaction preserved** `[HIGH]`
  The flip-to-back behavior from the prototype must work identically in the production component: click card → rotateY(180deg) → back face with career table and advanced metric bars. Press F or Escape for keyboard users.

- **R9 — Invisible affordance** `[MEDIUM]`
  Clickable player names render as plain text with no underline, color change, or icon. Hover state may apply a subtle cursor or faint tint but must not disrupt the newsprint aesthetic. Discoverability is accepted as low for Phase 1; a visible affordance can be added later if user testing demands it.

### Build Pipeline

- **R10 — Cubs-only in Phase 1** `[HIGH]`
  `build.py --team cubs` is the only path that must produce working cards. The other 29 teams continue building as today — no regression. A `--player-cards` flag (or equivalent) gates the new pipeline work so it doesn't slow existing builds.

- **R11 — Nightly refresh via existing cron trigger** `[HIGH]`
  No new scheduled job. The same `trig_01SYeMH3jjCZAnRnEoj1sE7n` trigger at 08:00 UTC regenerates `players-cubs.json` as part of the daily Cubs build.

- **R12 — Graceful fallback when data missing** `[MEDIUM]`
  If a player name is wrapped in `<player-card pid="X">` but `players-cubs.json` has no record for `X`, clicking shows a minimal stub card ("Pete Crow-Armstrong · Cubs · Card coming soon") rather than an error. The page never breaks.

### Compounding Assets

- **R13 — `players-cubs.json` as a first-class artifact** `[MEDIUM]`
  The JSON blob is designed to be consumed by future features beyond the card: Scorecard Book player lookups, Brain wiki ingest, potential Rolodex or scouting-note surfaces. Schema decisions in planning should prioritize readability and stability over card-specific convenience.

---

## Success Criteria

Observable outcomes that mean "Phase 1 is done."

- **SC1 — Click-to-card works end-to-end on Cubs page** `[HIGH]`
  On the live Cubs page (`https://brawley1422-alt.github.io/morning-lineup/cubs/`), clicking any of the 9 starting hitters or the starting pitcher opens the Topps flip card with real data pulled from that day's MLB API ledger.

- **SC2 — Front of card matches prototype fidelity** `[HIGH]`
  Each card shows: headshot, name, jersey number, position, bats/throws/age, season slash line (AVG/OBP/SLG for hitters; W-L/ERA/WHIP for pitchers), 15-game temperature strip with real per-game values, diagonal "Chicago Cubs" banner, bottom rail with card serial number.

- **SC3 — Back of card shows real MLB-API advanced stats** `[HIGH]`
  Flipping reveals the year-by-year career table (populated from MLB Stats API) and the Advanced section with OPS+, wOBA, IP/BB/K rates as appropriate. Savant-sourced metrics (xwOBA, Barrel%, HardHit%, Sprint, Stuff+) render "—" with no broken layout.

- **SC4 — Nightly regeneration is automatic** `[HIGH]`
  The next morning after Phase 1 ships, the cron trigger alone produces a fresh `players-cubs.json` with updated stats and a new 15-game strip. No human runs anything.

- **SC5 — Non-Cubs pages are unaffected** `[HIGH]`
  The other 29 team pages continue to build and render identically to today. No new HTML is shipped to them, no broken component references, no regressions in build time.

- **SC6 — Card opens in under 300ms on mobile** `[MEDIUM]`
  Subjective "feels instant" threshold. Measured on a mid-range phone on 4G. Accounts for JSON fetch + DOM injection + flip animation start.

- **SC7 — Zero-effort Phase 2 path exists** `[MEDIUM]`
  The `<player-card>` component and `players-{team}.json` schema are both team-agnostic. Expanding to the other 29 teams in Phase 2 requires only running the data pipeline per team and rebuilding their pages — no component changes.

---

## Scope Boundaries

### In Scope (Phase 1)

- Cubs page only (`cubs/index.html`)
- Today's lineup hitters (9) + starting pitcher (1) = ~10 cards per day
- `<player-card>` web component in one JS file
- `data/players-cubs.json` generated nightly
- MLB Stats API as the only advanced-stats source
- Invisible click affordance (plain text)
- Flip interaction from the prototype
- Graceful stub fallback for missing player data

### Out of Scope (Phase 1, deferred)

- **Phase 1.5**: Baseball Savant Statcast CSV integration (xwOBA, Barrel%, HardHit%, Sprint, Stuff+)
- **Phase 2**: Expansion to the other 29 teams (same data pipeline, same component, different inputs)
- **Phase 3**: Full 40-man roster coverage per team; tiered fidelity for bullpen (slash-only) and bench/IL (stub cards)
- **Later**: Prospects and historical players (no standardized data source)
- **Later**: Scouting blurb on the card footnote (AI-generated narrative layer)
- **Later**: Shareable player-of-the-day PNG export
- **Later**: Deep-link URLs (`#p/691718`)
- **Later**: Persistent roster strip / hover previews / dagger affordance
- **Later**: Ambiguity disambiguation for prose mentions (two-Rodriguez problem)
- **Later**: Pre-warm on scroll via IntersectionObserver
- **Later**: Integration into Scorecard Book or landing page rollups
- **Later**: Brain wiki ingest of `players-*.json`

---

## Open Questions (for `/ce:plan`)

These are technical decisions that planning should resolve, not ambiguities in product intent:

1. **Temp strip metric choice** — rolling wOBA, rolling OPS, or something simpler like hits-per-game? Planning should confirm what MLB's gameLog endpoint exposes cleanly.
2. **Pitcher temp strip cadence** — 5 starts, 10 appearances, or calendar-based (last 15 days)? Depends on role (SP vs RP).
3. **Where does the component JS live** — `assets/player-card.js` referenced from each team's HTML, or inlined into `index.html`? Affects SW cache strategy.
4. **JSON schema stability** — versioned (`"schema": "v1"`) or not? Affects graceful handling of future Savant additions.
5. **Name-to-ID wrapping locus** — does `build.py` wrap names only in the structured lineup/pitching HTML blocks, or also in transactions/columnist prose? Phase 1 likely structured-only; prose comes later.
6. **Service worker cache bump strategy** — bumping `lineup-v3` → `lineup-v4` on every pipeline deploy, or a separate cache key for player data?
7. **Build time budget impact** — how much does the new per-player `gameLog` fetch add to `build.py --team cubs` runtime? Acceptable ceiling for Phase 1?

---

## Next Steps

1. Run `/ce:plan` on this requirements doc to produce a step-by-step implementation plan.
2. After plan review, begin Phase 1 build.
3. Ship Phase 1 to production via the existing daily cron + commit/push flow.
4. Observe one nightly cycle before starting Phase 1.5 (Savant integration).
