---
title: "feat: Multi-team support — single repo, per-team configs"
type: feat
status: active
date: 2026-04-08
---

# Multi-Team Morning Lineup

## Overview

Refactor Morning Lineup from a Cubs-only site into a single codebase that generates a daily briefing for any MLB team. First target: Detroit Tigers for JB's buddy. The Cubs version stays identical — this is additive, not a rewrite.

## Problem Frame

65+ hardcoded Cubs references across 6 files (build.py, style.css, live.js, evening.py, scorecard/panels.js, data files). To support a second team, all team-specific values need to be extracted into a config file. The logic and layout stay the same.

## Architecture

```
morning-lineup/
  teams/
    cubs.json          ← team config (ID, colors, affiliates, branding, etc.)
    tigers.json
    cubs/
      history.json     ← team-specific curated history
      prospects.json   ← team-specific prospect watchlist
    tigers/
      history.json
      prospects.json
  build.py             ← reads --team flag, loads config, generates output
  style.css            ← CSS variables renamed from --cubs-* to --team-*
  live.js              ← reads TEAM_ID from inline config injected by build.py
  evening.py           ← reads --team flag
  deploy.py            ← reads --team flag, deploys to team-specific repo
  output/              ← generated per-team (output/cubs/index.html, output/tigers/index.html)
```

## Team Config Schema (e.g., `teams/tigers.json`)

```json
{
  "id": 116,
  "name": "Tigers",
  "full_name": "Detroit Tigers",
  "abbreviation": "DET",
  "division_id": 202,
  "division_name": "AL Central",
  "colors": {
    "primary": "#0C2340",
    "primary_hi": "#1d4070",
    "accent": "#FA4616",
    "accent_hi": "#ff6a3d"
  },
  "venue": {
    "id": 2394,
    "name": "Comerica Park",
    "azimuth": 30,
    "nickname": "The Corner"
  },
  "affiliates": [
    {"id": 512, "name": "Toledo Mud Hens", "level": "AAA", "sport_id": 11},
    {"id": 570, "name": "Erie SeaWolves", "level": "AA", "sport_id": 12},
    {"id": 582, "name": "West Michigan Whitecaps", "level": "A+", "sport_id": 13},
    {"id": 547, "name": "Lakeland Flying Tigers", "level": "A", "sport_id": 14}
  ],
  "branding": {
    "tagline": "A Daily Dispatch from The Corner & Beyond",
    "footer_tag": "A Comerica Park Broadsheet",
    "lede_tone": "like a beat writer who bleeds Midnight Blue and Orange",
    "idle_msg": "No Tigers game in progress"
  },
  "rivals": {
    "116": "Tigers", "114": "Guardians", "118": "Royals",
    "142": "Twins", "145": "White Sox"
  },
  "deploy": {
    "repo": "brawley1422-alt/morning-lineup-tigers",
    "branch": "main"
  }
}
```

## Implementation Units

### Phase 1: Extract Config

- [ ] **Unit 1: Create team config files**

**Goal:** Create `teams/cubs.json` and `teams/tigers.json` with all team-specific values.

**Files:**
- Create: `teams/cubs.json`, `teams/tigers.json`
- Create: `teams/cubs/` (move existing `history.json` and `prospects.json`)
- Create: `teams/tigers/history.json` (start empty `{}`)
- Create: `teams/tigers/prospects.json` (start empty `[]`)

**Approach:**
- Cubs config mirrors current hardcoded values exactly
- Tigers config uses their actual team/division/affiliate IDs (verify via MLB Stats API)
- Venue azimuth for Comerica Park: ~30 degrees (verify)
- Tigers affiliates: Toledo (AAA), Erie (AA), West Michigan (A+), Lakeland (A)
- Tigers colors: Midnight Blue #0C2340, Orange #FA4616

---

- [ ] **Unit 2: Rename CSS variables from `--cubs-*` to `--team-*`**

**Goal:** Make style.css team-agnostic by renaming color variables.

**Files:**
- Modify: `style.css` (~20 references)

**Approach:**
- `--cubs-blue` → `--team-primary`
- `--cubs-blue-hi` → `--team-primary-hi`
- `--cubs-red` → `--team-accent`
- `--cubs-red-hi` → `--team-accent-hi`
- `.standings tr.cubs` → `.standings tr.my-team`
- Find-and-replace across the file
- Also update any references in `scorecard/styles.css` if they use these variables

---

- [ ] **Unit 3: Parameterize `build.py`**

**Goal:** Replace all 40+ hardcoded Cubs references with config lookups.

**Files:**
- Modify: `build.py`

**Approach:**
- Add `--team` CLI argument (default: `cubs`)
- Load `teams/{team}.json` at startup
- Replace `CUBS_ID` with `cfg["id"]`
- Replace `AFFILIATES` with `cfg["affiliates"]`
- Replace division ID `205` with `cfg["division_id"]`
- Replace all "Cubs" strings in HTML templates with `cfg["name"]`
- Replace branding strings (tagline, footer, etc.) with `cfg["branding"]`
- Replace lede prompt tone with `cfg["branding"]["lede_tone"]`
- Rename `render_cubs_leaders()` → `render_team_leaders()`
- Inject CSS variable overrides at build time: write `--team-primary` etc. from config colors into the `<style>` block
- Load `teams/{team}/history.json` and `teams/{team}/prospects.json`
- Build rivals dict from `cfg["rivals"]` instead of hardcoded NLC dict
- Output to `output/{team}/index.html` (or current root for backwards compat)

**Key detail:** CSS color injection. At the top of the inlined `<style>`, override the `:root` variables:
```css
:root { --team-primary: #0C2340; --team-primary-hi: #1d4070; ... }
```
This way `style.css` stays team-agnostic and the config drives the palette.

---

- [ ] **Unit 4: Parameterize `live.js`**

**Goal:** Remove hardcoded `CUBS_ID = 112` and Cubs-specific variable names.

**Files:**
- Modify: `live.js`

**Approach:**
- `build.py` injects a `<script>var TEAM_ID = 116;</script>` before `live.js` loads
- Replace `CUBS_ID` → `TEAM_ID` (already set by build)
- Rename `cubsSide` → `teamSide`, `checkCubs` → `checkTeam`, `scheduleCubs` → `scheduleTeam`
- Replace "No Cubs game in progress" → config-injected idle message (also via inline script var)

---

- [ ] **Unit 5: Parameterize `evening.py`**

**Goal:** Support `--team` flag for the post-game watcher.

**Files:**
- Modify: `evening.py`

**Approach:**
- Add `--team` argument, load config same as build.py
- Replace `CUBS_ID` with config team ID
- Rename `get_cubs_game_today()` → `get_team_game_today()`

---

- [ ] **Unit 6: Parameterize scorecard venue logic**

**Goal:** Make wind interpretation work for any stadium, not just Wrigley.

**Files:**
- Modify: `scorecard/panels.js`

**Approach:**
- `build.py` injects venue config (ID, azimuth, name) as inline script vars
- Replace `WRIGLEY_ID = 17` → `VENUE_ID` from config
- Replace `WRIGLEY_AZIMUTH = 37` → `VENUE_AZIMUTH` from config
- Wind interpretation logic already works generically — it just needs the azimuth value swapped

---

### Phase 2: Tigers-Specific Content

- [ ] **Unit 7: Build Tigers prospect watchlist**

**Goal:** Create `teams/tigers/prospects.json` with current Tigers top prospects.

**Approach:**
- Research current Tigers top 15-20 prospects from Pipeline rankings
- Look up MLB Stats API player IDs for each
- Verify IDs match boxscore endpoint (same issue we hit with Cubs)

---

- [ ] **Unit 8: Landing page with team picker**

**Goal:** Build a root `index.html` that lists all configured teams and links to their briefings.

**Files:**
- Create: `landing.html` (template) or generate in build pipeline
- Modify: `build.py` (add `--landing` flag or auto-generate after team builds)

**Approach:**
- Dark background, Morning Lineup masthead (same fonts/aesthetic), centered grid of team cards
- Auto-generated from the `teams/` folder — scan for `*.json` configs, read team name + colors
- Each card shows team name, primary color accent, links to `/{team}/`
- No JS framework — static HTML, same CSS variable system
- Responsive grid: 3-4 columns desktop, 2 mobile
- Lives at the repo root: `brawley1422-alt.github.io/morning-lineup/`
- Team pages move to subdirectories: `/cubs/index.html`, `/tigers/index.html`
- Build pipeline: `build.py --team cubs` outputs to `cubs/`, then a final pass generates root `index.html`

**URL structure:**
```
/                    ← landing page (team picker)
/cubs/               ← Cubs daily briefing
/cubs/scorecard/     ← Cubs scorecard app
/tigers/             ← Tigers daily briefing
/tigers/scorecard/   ← Tigers scorecard app
```

---

- [ ] **Unit 9: Deploy pipeline for multiple teams**

**Goal:** Update `deploy.py` to support `--team` flag and deploy all teams + landing page to a single repo.

**Files:**
- Modify: `deploy.py`

**Approach:**
- Single repo `brawley1422-alt/morning-lineup` with subdirectories per team
- `deploy.py` handles: archive previous day per team, commit all team pages + landing page
- Build script: loop through all team configs, build each, generate landing page, deploy once
- GitHub Pages serves from repo root — landing page at `/`, teams at `/{team}/`

---

### Phase 3: Trigger Setup

- [ ] **Unit 10: Triggers for all teams**

**Goal:** Set up daily build + deploy triggers that build all configured teams.

**Approach:**
- Single trigger that loops through teams:
  ```
  for team in cubs tigers; do
    python3 build.py --team $team
  done
  python3 build.py --landing
  python3 deploy.py --all
  ```
- Evening watcher: one process per team, or combined watcher that checks all configured teams
- Adding a new team = add config JSON + trigger picks it up automatically

---

## Risks

| Risk | Mitigation |
|------|------------|
| CSS variable rename breaks something subtle | Test Cubs output diff before/after — should be byte-identical HTML |
| Tigers affiliate IDs wrong | Verify against `/teams/{id}/roster` endpoint before building prospects |
| Extra innings break scorecard embed (existing bug) | Out of scope for this plan, tracked separately |
| Two daily triggers doubles API calls | MLB Stats API has no auth/rate limit — not a real concern |

## Verification

1. Run `python3 build.py --team cubs` — output should be identical to current `index.html`
2. Run `python3 build.py --team tigers` — generates Tigers-branded page with correct colors, affiliates, division
3. Run `python3 build.py --landing` — generates root team picker with Cubs + Tigers cards
4. Open both team pages in browser — verify colors, team names, section headers, standings highlighting
5. Open landing page — verify team cards link correctly to `/cubs/` and `/tigers/`
6. Test `live.js` on both teams — correct team ID, correct idle message
7. Verify scorecard embed works for both teams
8. Test responsive: landing page grid collapses properly on mobile
