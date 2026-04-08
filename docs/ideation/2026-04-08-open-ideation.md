---
date: 2026-04-08
topic: open
focus: open-ended ideation after Scorecard Book + game intelligence ship
---

# Ideation: Morning Lineup — Post-Scorecard Improvements

## Codebase Context
Python stdlib-only static site generator for Cubs daily briefing. build.py fetches MLB Stats API data, renders full HTML with embedded CSS, deploys to GitHub Pages. live.js provides client-side live game polling. Current sections: Cubs recap (three stars, key plays, scorecard embed), hot/cold hitters, NL Central (rivals, standings), Around the League (news wire, scoreboard, leaders), Today's Slate, Next Games (enriched with pitcher stats, weather, broadcasts, dome labels), injuries, minor leagues (4 affiliates), team leaders, This Day in Cubs History. Scorecard Book app lives in scorecard/ subdirectory with live scoring, SVG diamond diagrams, game finder, broadcasts, weather with Wrigley wind interpretation, and player stats overlay.

## Ranked Ideas

### 1. Season Data Ledger (JSON Archive)
**Description:** Emit `data/YYYY-MM-DD.json` alongside each HTML archive with the structured dict `load_all()` already returns. Every day of the season automatically adds a row. Unlocks trends, streaks, comparisons, and every time-series feature downstream.
**Rationale:** Highest-leverage single change. The data is already fetched and thrown away — persisting it is ~10 lines of code that compound for 162+ games.
**Downsides:** Growing repo size (~50KB/day). Date serialization needed.
**Confidence:** 95%
**Complexity:** Low
**Status:** Unexplored

### 2. Evening Edition (Post-Game Rebuild)
**Description:** Second build trigger after Cubs game goes Final — recap arrives the same night. Could be a systemd timer polling game status or a simple cron at 11 PM CT.
**Rationale:** Biggest content gap. Most emotional fan moment (right after a W or L) gets nothing — wait until tomorrow morning for stale news.
**Downsides:** Needs a watcher script or second cron. Same-day deploy overwrites morning edition.
**Confidence:** 85%
**Complexity:** Low
**Status:** Unexplored

### 3. Auto-Populate "This Day in Cubs History"
**Description:** Use Claude to backfill history.json for all 366 calendar dates from 148 years of Cubs history. One-time generation, manual review, then commit. The section is currently empty for ~85% of dates.
**Rationale:** Most emotionally resonant section, but useless most days because manual curation doesn't scale. A single Claude session could fill the entire calendar.
**Downsides:** Needs fact-checking pass. Training data accuracy for obscure dates.
**Confidence:** 80%
**Complexity:** Low (code) / Medium (content review)
**Status:** Unexplored

### 4. Extract CSS from build.py
**Description:** Move the ~270-line CSS string constant into a standalone style.css that build.py reads and inlines at build time. Same single-file HTML output, but CSS becomes editable with syntax highlighting and DevTools.
**Rationale:** Biggest DX win. Every design tweak currently means editing a Python file. Scorecard Book already proves separate CSS works.
**Downsides:** One more file to track. Minor build.py refactor.
**Confidence:** 90%
**Complexity:** Low
**Status:** Unexplored

### 5. Prospect Watch (Minor League Tracker)
**Description:** Add a curated prospects.json watchlist (top 15-20 Cubs prospects) and cross-reference with daily affiliate boxscores. Flag when a ranked prospect has a notable game. Over time, accumulate per-prospect stat lines for trajectory tracking.
**Rationale:** Farm section already fetches full boxscores but treats all players equally. Prospect tagging turns noise into signal and compounds daily.
**Downsides:** Prospect list needs manual curation. Promotions change levels.
**Confidence:** 75%
**Complexity:** Medium
**Status:** Unexplored

### 6. PWA + Offline Morning Edition
**Description:** Add manifest.json + service worker for installable, offline-cached experience. Full-screen, no browser chrome, works on spotty cell. ~50 lines total.
**Rationale:** Most natural time to check is on phone over coffee. Home screen icon makes it feel native for zero infrastructure.
**Downsides:** Cache invalidation. Live widget won't work offline.
**Confidence:** 90%
**Complexity:** Low
**Status:** Unexplored

### 7. Claude Editorial Lede
**Description:** After load_all() gathers data, pass the blob to Claude API for a 3-4 sentence editorial paragraph synthesizing the night's action. Insert at the top of the fold as the daily "front page voice."
**Rationale:** Site has newspaper aesthetics but no newspaper voice. A generated lede would make each day feel different with real editorial personality.
**Downsides:** Adds Anthropic API dependency and cost. Generated text quality varies.
**Confidence:** 65%
**Complexity:** Medium
**Status:** Unexplored

## Rejection Summary

| # | Idea | Reason Rejected |
|---|------|-----------------|
| 1 | API retry/resilience layer | Ops concern, not a feature idea |
| 2 | Data cache with stale-serve | Infrastructure, not user-facing |
| 3 | Replace deploy.py with git push | Internal refactor |
| 4 | Merge build.py + deploy.py | Internal cleanup |
| 5 | Build performance instrumentation | Ops tooling |
| 6 | RSS/Atom feed | Single reader makes RSS overhead for no gain |
| 7 | Team-agnostic config | Breaks editorial focus that makes project distinctive |
| 8 | Email newsletter delivery | Single reader can bookmark; marginal convenience |
| 9 | Invert to live-first experience | Fights core identity; Scorecard Book fills live role |
| 10 | Pre-game auto-refresh via live.js | Fragile DOM patching; evening edition is simpler |
| 11 | Live widget inline player stats | Duplicates Scorecard Book player stats overlay |
| 12 | NLC rival depth / standings movement | Incremental; similar idea rejected in prior ideation |
| 13 | Reusable design token system | Premature abstraction; extract CSS first |
| 14 | Embeddable briefing widget | Scorecard embed already exists |
| 15 | load_all() as reusable module | Internal refactor, not standalone |
| 16 | Streak/momentum signals | Downstream of Season Data Ledger, not standalone |
| 17 | Cross-tool notification bus | Mixes unrelated tool domains; scope explosion |
| 18 | Season narrative tracker | Duplicates Data Ledger + Streaks combined |
| 19 | Structured history graph | Over-engineers history.json; auto-populate is higher leverage |
| 20 | Opponent scouting report | Overlaps enriched Next Games cards just shipped |
| 21 | Wrigley wind historical index | Niche; folds into Data Ledger downstream |
| 22 | Wrigley wind prominence | Just shipped; promotion is cosmetic |

## Session Log
- 2026-04-08: Open ideation — 38 generated across 4 agents, 7 survived. Ideas #1, #2, #6 resurfaced from 2026-04-07 ideation (still unexplored). Ideas #3, #5, #7 are new this round.
