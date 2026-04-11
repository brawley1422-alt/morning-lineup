# Player Cards at Scale — Ideation

**Date:** 2026-04-11
**Focus:** How to scale the Topps-style flip card from a Pete Crow-Armstrong prototype to every player on every team, without "making that many cards"
**Prototype:** `docs/design/2026-04-11-player-card-prototype.html`
**Status:** Ideation only — select a direction, then run `/ce:brainstorm` to define requirements

---

## The Reframe (Read This First)

The user's concern — "making that many cards might take forever" — dissolves once the card is seen correctly:

> **There is exactly one card.** It's a template (~400 lines of HTML/CSS/JS). Scaling to 1,200 players is a **data pipeline problem**, not a design problem. Nightly `build.py` already fetches MLB data per team. Extending it to emit a `players-{team}.json` alongside `index.html` gives full coverage as a free side-effect of work that already runs every morning.

No cards are built by hand. Ever.

---

## Survivors (7)

Ideas that survived adversarial filtering across data-pipeline, click-wiring, and scope-ramp angles.

### 1. `players-{team}.json` as the Unlock Artifact ⭐ CORE

Build one canonical per-team JSON blob (~40 players each) during the nightly cron. Contains everything the card needs: identity (name, position, ID, headshot URL), season slash/pitching line, 15-game temp array, advanced metrics. Card reads from it; Scorecard Book can read from it later; Brain wiki can ingest it.

**Why it wins:** Turns "1,200 cards" into "30 small JSON files, regenerated every night." One source of truth, zero duplication, scales to every future feature that needs player data (scouting notes, injury timeline, prospect drilldown). Matches the project's existing per-team artifact pattern.

**Hook:** `build.py` already loops team-by-team writing `{team}/index.html` — the JSON is the natural sibling artifact.

---

### 2. Hybrid Data Tier: Front-Inline, Back-Lazy

The team page inlines the cheap stuff the front of the card needs (name, slash line, photo URL, temp array) directly into the lineup/pitching/bullpen HTML. Expensive advanced metrics (xwOBA, Barrel%, Stuff+, sprint speed) live in the team's `players.json` and only load when the user flips the card.

**Why it wins:** Front-of-card renders instantly with zero extra HTTP. Back-of-card fetches on demand (often never). Maps cleanly to the flip card's two faces and matches the two-audience split (tired fan = front, try-hard fan = back).

---

### 3. `<player-card>` Web Component ⭐ CORE

One custom element, defined in one JS file. `build.py` wraps every known player in `<player-card pid="691718">Pete Crow-Armstrong</player-card>`. The element renders as inline text until clicked, then injects the Topps overlay and fetches the right players.json chunk.

**Why it wins:** Encapsulation — card styling, fetch logic, flip state, and a11y all live in one portable file. Works on Morning Lineup team pages today, drops into Scorecard Book or the landing rollup with zero changes. Upgrade is automatic; no global event delegation.

---

### 4. Scope Ramp: "Nine and the Arm" → Active 40-Man → Everything Else ⭐ CORE

- **Phase 1 (MVP — days, not weeks):** Cards work for today's lineup (9 hitters) + starting pitcher on all 30 teams. ~300 players, full fidelity. Ship this first.
- **Phase 2:** Full active 40-man rosters. ~1,200 players, full fidelity.
- **Phase 3:** Bullpen/bench = slash line only. IL/transactions = stub card (name + status). Prospects + historical players stay plain text. **No card at all** for anyone off the 40-man.

**Why it wins:** First value in days. Matches the "rebuild all 30 teams" preference. Clean conceptual rule ("if active 40-man, render card") avoids the worst data problem (low-minors prospects with no standardized stats).

---

### 5. Tiered Card Fidelity by Role

Same component, three data-completeness states driven by where the player appears:

| Tier       | Where                   | What shows                           |
| ---------- | ----------------------- | ------------------------------------ |
| **Hero**   | Starting lineup, SP     | Full card, advanced stats, blurb     |
| **Standard** | Bullpen, bench        | Slash line only, no advanced back    |
| **Stub**   | IL, transactions        | Name, photo, status — no flip        |

**Why it wins:** Lets you claim 100% coverage day one while only doing the hard data work for the ~15 high-leverage players per team. Visual hierarchy matches editorial importance.

---

### 6. Precomputed 15-Game Temp Strip (Implementation Detail)

`build.py` pulls each player's last 15 `gameLog` entries from the MLB Stats API (free, unauthed), computes rolling wOBA or OPS per game, normalizes to 0–1, and stores a 15-element array in `players.json`. The card's temp strip renders straight from that array — no client-side computation, no raw game logs shipped to the browser.

**Why it wins:** Keeps the "hot/cold" feel instant and tiny (15 floats per player). Necessary detail for the front-of-card to feel alive.

---

### 7. Dagger Footnote Affordance (†)

Clickable player names get a subtle superscript dagger instead of a blue underline: "Pete Crow-Armstrong†". Tapping the name or the dagger opens the card.

**Why it wins:** Preserves the bold-editorial newsprint aesthetic. Wikipedia-blue links would scream through the columnist prose. The dagger reads as an editorial footnote mark — native to broadsheet — and becomes a signature Morning Lineup micro-detail.

---

## Honorable Mentions

Worth revisiting after the MVP ships:

- **Player-of-the-Day shareable PNG** (compounds into social surface — pick the biggest performer from last night's box score, render the card, post as image)
- **IntersectionObserver pre-warm** on scroll (mobile-fast feel without upfront fetch)
- **Deep-linkable `#p/691718` URLs** (shareable card state, natural back-button close)
- **Brain/Qdrant ingest of `players.json`** (semantic search over every MLB player — feeds future scouting narrative features)

---

## Rejected (With Reasons)

| Idea                                       | Why not                                                                            |
| ------------------------------------------ | ---------------------------------------------------------------------------------- |
| Per-player JSON files (1,200 files)        | Breaks the clean single-artifact pattern; complicates builds                       |
| SQLite + sql.js in browser                 | WASM runtime for a problem JSON solves at 1/10th the complexity                    |
| Cloudflare Worker proxy to Savant          | Adds infra; the daily cron is the right cadence for stats                          |
| Runtime `/api/player/:id` endpoint         | Contradicts the static GitHub Pages architecture                                   |
| Long-press for card on mobile              | Fights scroll gestures; discoverability is zero                                    |
| Two-Rodriguez disambiguation picker        | Edge case; page-scoped ID map from structured data solves 95% for free             |
| Persistent roster strip instead of name-click | Redundant once in-prose clicks work; can add later as a second surface             |
| Ship UI with zero real data                | Undermines trust; stats ARE the point of the card                                  |
| Scorecard Book integration first           | Distracts from Morning Lineup momentum; do after MVP                               |
| Client-side regex across free prose only   | Fragile (nicknames, diacritics, possessives); hybrid wrapping-at-build-time wins   |

---

## Suggested Next Step

Run `/ce:brainstorm` on **Idea 1 + 3 + 4 combined** — "per-team `players.json` emitted by `build.py`, consumed by a `<player-card>` web component, rolled out in a Nine-and-the-Arm → 40-man → everything-else phased ramp." That's the MVP path. Brainstorm should settle acceptance criteria, data sources for advanced metrics (MLB Stats API alone vs + Baseball Savant CSV), and what the Phase 1 shipping definition looks like.
