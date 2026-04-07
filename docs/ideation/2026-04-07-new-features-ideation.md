---
date: 2026-04-07
topic: new-features
focus: new features - on the farm section, etc
---

# Ideation: Morning Lineup New Features

## Codebase Context
Python stdlib-only static site generator for Cubs daily briefing. build.py fetches MLB Stats API data, generates index.html, deploys to GitHub Pages. live.js provides client-side live game polling. Current sections: Cubs recap, NL Central, Around the League, Today's Slate. Template prototypes exist for Down on the Farm and Fantasy Desk but are not wired to build.py.

## Ranked Ideas

### 1. Down on the Farm (Minor League Results)
**Description:** Populate the template-prototyped section with real data from all 4 Cubs affiliates (Iowa/AAA, Tennessee/AA, South Bend/A+, Myrtle Beach/A) — scores, W/L, top performers.
**Rationale:** Highest-visibility gap. Template CSS already built. Prospect tracking is core for superfans.
**Downsides:** 4-8 extra API calls. Minor league boxscore availability varies.
**Confidence:** 90%
**Complexity:** Medium
**Status:** Explored (built 2026-04-07)

### 2. Season Data Ledger (JSON Archive)
**Description:** Write data/YYYY-MM-DD.json alongside HTML archive with structured load_all() output.
**Rationale:** Highest-leverage infrastructure. Enables sparklines, milestones, trends. Every day adds value.
**Downsides:** Growing repo size. Need date serialization.
**Confidence:** 95%
**Complexity:** Low
**Status:** Unexplored

### 3. Evening Edition (Post-Game Rebuild)
**Description:** Second build trigger after Cubs game goes Final — recap within minutes of final out.
**Rationale:** Most emotional fan moment is right after the game. 10:15 PM recap > 7 AM stale news.
**Downsides:** Needs polling watcher or second cron.
**Confidence:** 85%
**Complexity:** Low
**Status:** Unexplored

### 4. Expected Stats vs. Actual (Luck Index)
**Description:** Fetch Baseball Savant CSV for Cubs hitters, show xBA vs BA, xSLG vs SLG, xwOBA vs wOBA.
**Rationale:** Most powerful signal for impending regression/breakout. No mainstream coverage surfaces this daily.
**Downsides:** External data source could break.
**Confidence:** 80%
**Complexity:** Low
**Status:** Unexplored

### 5. PWA + Offline Morning Edition
**Description:** Web app manifest + service worker for installable, offline-cached experience.
**Rationale:** Home screen icon, no browser chrome, works on spotty cell. ~50 lines.
**Downsides:** Cache invalidation complexity. Live widget won't work offline.
**Confidence:** 90%
**Complexity:** Low
**Status:** Unexplored

### 6. Pitcher Matchup Preview
**Description:** Detailed matchup card for today's probable starters — season line, last 3 starts, career vs. opponent.
**Rationale:** First question before any game: who's pitching and should I feel good?
**Downsides:** Pitchers sometimes unannounced. Career splits sparse for young pitchers.
**Confidence:** 75%
**Complexity:** Medium
**Status:** Unexplored

### 7. This Day in Cubs History
**Description:** 2-3 notable events from today's calendar date. Static history.json curated once.
**Rationale:** Pure editorial soul. Newspaper metaphor demands it. Zero runtime cost.
**Downsides:** Content curation effort for 365 entries.
**Confidence:** 85%
**Complexity:** Low (code) / Medium (content)
**Status:** Explored (built 2026-04-07)

## Rejection Summary

| # | Idea | Reason Rejected |
|---|------|-----------------|
| 1 | Multi-team Wire Service | Scope explosion — breaks editorial focus |
| 2 | Print PDF Edition | Requires external dep (weasyprint/chromium) |
| 3 | Umpire Scouting Report | No MLB API endpoint for tendency data |
| 4 | NLC Prospect Pulse | 10 extra API calls for marginal value |
| 5 | Starter Command Chart | Hard to render beautifully in text |
| 6 | AI Game Narratives | Adds API cost for single reader |
| 7 | Build Manifest | Too ops-focused for editorial site |
| 8 | Trending Platoon Splits | Too granular for morning briefing |
| 9 | Run Expectancy on Key Plays | Marginal insight, complex to implement |
| 10 | Ticker Tape Score Crawl | CSS gimmick — live slate does it better |
| 11 | H2H Season Splits | Overlaps pitcher matchup preview |
| 12 | Cumulative Context Line | Weaker duplicate of other ideas |
| 13 | Deploy JSON to GitHub | Subset of Season Data Ledger |
| 14 | Auto Headline Generator | Refinement of detect_league_news, not a feature |
| 15 | NLC Rivalry Tracker | Incremental improvement to existing section |

## Session Log
- 2026-04-07: Initial ideation — 38 generated, 7 survived. User selected #1 (Down on the Farm) and #7 (This Day in Cubs History) to build immediately.
