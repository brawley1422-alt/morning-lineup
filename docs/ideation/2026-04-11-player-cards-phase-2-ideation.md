---
date: 2026-04-11
topic: player-cards-phase-2
focus: highest-leverage next move after Phase 1 (deeplinks, Tier 1 affordance, dark binder My Players)
---

# Ideation: Player Cards Phase 2

## Codebase Context

Phase 1 shipped today (2026-04-11) — see `docs/plans/2026-04-11-001-feat-player-cards-cubs-mvp-plan.md` and `docs/plans/2026-04-11-002-feat-player-cards-all-teams-plan.md`. State on disk:

- 30 teams × ~26 active-roster players, written to `data/players-<slug>.json` daily by `build.py`
- Topps-style flip card web component (`cubs/player-card.js`, mirrored to root + every team dir + `home/`) with front (banner, headshot, slash, hot/cold strip) and back (advanced stats grid, currently empty placeholder `{}`)
- `MorningLineupPC.mountInline()` API exposed for inline rendering (used by My Players binder)
- Deeplinks `/<slug>/#p/<pid>` work everywhere
- Tier 1 in-page click affordance: `sections/headline.py` (lineup, SP, Three Stars, Leaders, Form Guide hot/cold) + `sections/scouting.py` (own-team SP) — own-team only
- "My Players" home section (`home/home.js` + `home/home.css`) is now a dark navy binder grid rendering real flippable cards
- Build pipeline: stdlib Python, `ThreadPoolExecutor(4)`, per-day disk cache `data/cache/players/`, ~5min cold / ~2min warm
- Global pid→slug index `data/player-index.json` (779 entries) for orphan player resolution
- 30/30 deeplink smoke checks pass (`tests/test_deeplink_smoke.py`)
- Per-team JSONs explicitly EXCLUDE: IL, 40-man non-active, prospects, minors
- Cross-team click affordance NOT shipped — slate, league leaders, scoreboard, key plays text, transactions, news wire, Around the League stay plain text
- Scorecard iframe NOT wired (cross-team, iframe-isolated)
- Statcast/Baseball Savant integration NOT shipped (`advanced` field is empty placeholder)

## Ranked Ideas

### 1. Complete the affordance — DOM walker + IL inclusion
**Description:** A page-load IIFE walks text nodes on every team page and auto-wraps any plain-text name matching `data/player-index.json` in `<player-card>`. Pairs with adding IL/40-man recent-callups to the per-team JSONs (with a `roster_status` flag) so names in transactions/news wire/IL section also resolve.
**Rationale:** ~80% of player names on every team page are dead text today — slate, league leaders, scoreboard, key plays, news wire, transactions, Around the League. Readers train on Tier 1 then hit a wall everywhere else. One walker pass solves them all and any future plain-text section gets it for free. IL inclusion fixes the most newsworthy dead-link cases (just-called-up, just-IL'd).
**Downsides:** Walker has to handle already-wrapped nodes and ambiguous last names ("Rodriguez" matches multiple pids). Needs first-name disambiguation or whole-name matching.
**Confidence:** 85%
**Complexity:** Medium
**Status:** Unexplored

### 2. Card memory layer — snapshot tape + reader state
**Description:** Build emits per-day player snapshots (`data/snapshots/<pid>.json` or one combined file) appending today's slash line + advanced stats per player, retaining last 30 days. localStorage tracks `{pid: {firstSeen, lastSeen, openCount}}`. Cards show "+3 RBI since you last looked", "you've opened this 14 times", and a 30-day sparkline. End-of-season "Your Season" recap built from the same data.
**Rationale:** The strongest single compound investment of the survivors. Unlocks personal deltas, sparklines, "what changed since yesterday", the prediction market (idea #4), Spotify-Wrapped recaps, "you also viewed", returning-reader hooks. Turns the card from a snapshot into a relationship.
**Downsides:** Snapshot tape grows daily (~30 days × 779 players = small but real); needs a janitor. Reader state is per-device with no cross-device sync without auth.
**Confidence:** 80%
**Complexity:** Medium
**Status:** Explored — brainstormed 2026-04-11 (jointly with #4)

### 3. Opinionated editorial voice on every card
**Description:** Each card carries a one-line editorial micro-take generated at build time from a template + stat-trigger rule system in Python (no LLM at runtime). Lives on the back of the card above the stats grid. Example: "Pete Crow-Armstrong: still more vibes than value, but the vibes are loud."
**Rationale:** Most baseball stats sites are voiceless reference. Morning Lineup is an editorial newspaper. A card with a take is shareable, memorable, hand-feels in a way no aggregator can match. Differentiates immediately and costs nothing per render.
**Downsides:** Writing the template/trigger rule library is real work. Risk of robotic phrasing if rules are too narrow. Need editorial judgment to avoid offensive or wrong takes.
**Confidence:** 70%
**Complexity:** Medium
**Status:** Unexplored

### 4. Daily prediction market with yourself
**Description:** Each morning's card back offers a tappable micro-prediction: "Will Ian Happ get a hit today? YES/NO." One tap, stored locally, no account. Tomorrow's card opens with "You picked YES. He went 2-for-4. You're 7-for-12 on Happ this season." Builds a personal scoreboard per followed player.
**Rationale:** Strongest possible daily-return hook for a daily-cadence product. Aligns the card's loop with the site's loop. Compounds with #2. Zero backend. Turns "I check Morning Lineup with coffee" into "I check Morning Lineup to see if I was right."
**Downsides:** Daily build needs a small step to resolve yesterday's predictions from final box scores. Privacy/sharing edges if/when accounts are added later.
**Confidence:** 75%
**Complexity:** Low–Medium
**Status:** Explored — brainstormed 2026-04-11 (jointly with #2)

### 5. Player search — command palette
**Description:** A `/`-press (or single keyboard shortcut) opens a fuzzy search modal over the 779-player index. Type "skub" → Tarik Skubal. Hit Enter → his card opens via the existing modal. Works on every page including the home page. Backed by `data/player-index.json` plus a tiny client-side fuzzy matcher.
**Rationale:** The card system is a database with no front door. Readers think of a player mid-read and have no way to summon them unless a related section happens to mention them. Cheapest big utility win.
**Downsides:** Needs an unused keyboard shortcut that doesn't fight browser shortcuts. Mobile UX needs a button trigger too.
**Confidence:** 90%
**Complexity:** Low
**Status:** Unexplored

### 6. Season weather temp strip
**Description:** Replace the 8-segment hot/cold strip on the card front with a 162-pixel season-long timeline — one pixel per game played, colored by per-game contribution (wOBA, WPA, GameScore for pitchers). Streaks, slumps, debut, IL stints all visible at a glance. Hover/tap a pixel surfaces that day's game line.
**Rationale:** Temp strip is the only data viz on the card. Extending it to a full season turns the front of every card into the most information-dense pattern-recognition viz on the site without adding chrome. Distinctive — nobody does this.
**Downsides:** Needs per-game gamelog data (already fetched for the existing temp strip — extend to full season). 162 px is tight on mobile; needs responsive scaling.
**Confidence:** 70%
**Complexity:** Medium
**Status:** Unexplored

### 7. Compare mode — two cards side by side
**Description:** Click a player while a card is already open → the new card slides in next to the first. Slash lines align, deltas highlight. Deeplink extends to `/<slug>/#p/<pid1>,<pid2>`. Click a third → oldest drops out.
**Rationale:** Every baseball conversation is comparative. Today the reader has to memorize numbers across modal opens. Compare mode makes the most native fan behavior trivial. Uses the existing component, adds no new data.
**Downsides:** Two-up layout on mobile is constrained — probably reverts to vertical stack. Comparison logic for hitter-vs-pitcher edge cases.
**Confidence:** 75%
**Complexity:** Medium
**Status:** Unexplored

## Rejection Summary

| # | Idea | Reason Rejected |
|---|------|-----------------|
| 1 | Walk-up song audio on flip | Fun but B-tier; copyright/asset cost; one-shot novelty |
| 2 | Recent cards sticky rail | JB killed the P1 sticky rail in Phase 3; respect prior feedback |
| 3 | Kill per-team JSONs for one delta | Pure refactor with no user value; current pipeline works |
| 4 | Kill build entirely, fetch from MLB API client-side | Destroys daily editorial snapshot cadence |
| 5 | Auto-derived follows from team affinity | Removes user agency over a personal collection |
| 6 | Auto-unfollow via TTL | Silent decay feels punishing |
| 7 | Versioned card schema + renderer registry | Premature abstraction; current schema is 1 day old |
| 8 | Card context object (alone) | Pure infra without a user-visible feature |
| 9 | Card event bus (alone) | Pure infra without a user-visible feature |
| 10 | Reader state bus (alone) | Folds into #2 (memory layer) as substrate |
| 11 | Stable /p/<pid> deep-link router | Already shipped via `#p/<pid>` hash routing |
| 12 | Lazy Statcast on first flip | Real complexity (auth, rate limits, parsing); deserves its own brainstorm |
| 13 | Scorecard iframe wiring | Real but isolated; better as a Phase 2.5 micro-project |
| 14 | Live mode (card knows current game) | Highest "wow" but polling complexity; deserves its own brainstorm later |
| 15 | B-side archive (time-travel) | Cool but lower urgency than the memory layer |
| 16 | Lineup-aware mesh (card knows neighbors) | Interesting but lower urgency than the survivors |
| 17 | Sendable share-card PNG | Strong, but social comes after the product is sticky (post #4) |
| 18 | Daily Events artifact (call-ups, DFAs) | Folds naturally into the snapshot tape (#2) |
| 19 | Cards-only-summoned (no listing pages) | Too restrictive; conflicts with binder |
| 20 | Service worker pre-warms binder | Incremental; current SW already partial |
| 21 | Assets pipeline manifest | Minor optimization |
| 22 | Cards speak (auto-NL blurb) | Weaker version of #3 (opinionated voice) |
| 23 | Temp strip explains itself on hover | Weaker version of #6 (season weather) |
| 24 | Cards remember reader (open-count alone) | Folds into #2 (memory layer) |
| 25 | IL/40-man as filter flag (alone) | Pairs with #1 inside that survivor |
| 26 | Two-Up mode alone | Folds into #7 (compare mode) |

## Session Log
- 2026-04-11: Initial ideation — 40 raw candidates generated across 4 frames (pain, inversion, reframe, leverage), 7 survived.
- 2026-04-11: User selected #2 + #4 to brainstorm jointly (memory layer is the substrate for prediction market).
