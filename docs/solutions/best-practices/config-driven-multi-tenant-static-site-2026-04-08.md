---
title: Config-driven multi-tenant architecture for static site generators
date: 2026-04-08
category: best-practices
module: morning-lineup
problem_type: best_practice
component: tooling
severity: medium
applies_when:
  - Single-entity static site needs to support multiple entities from one codebase
  - Hardcoded identifiers, colors, and strings are scattered across 3+ files
  - Project deploys as static HTML with no server-side routing
  - External API provides a machine-readable roster of all entities
tags:
  - multi-tenant
  - config-extraction
  - static-site
  - build-time-injection
  - css-variables
  - json-config
  - zero-dependencies
---

# Config-driven multi-tenant architecture for static site generators

## Context

Morning Lineup was a Cubs-only daily MLB briefing site. Every file -- `build.py`, `live.js`, `evening.py`, `style.css`, HTML templates -- contained hardcoded Cubs references: team ID `112`, hex colors `#0E3386`/`#CC3433`, CSS class `.cubs`, division ID `205`, affiliate team IDs, branding strings like "Friendly Confines" and "bleeds Cubbie blue." Expanding to any MLB team meant touching 65+ hardcoded references across 6 files. The project uses zero external dependencies (Python stdlib only) and deploys as static HTML to GitHub Pages.

A friend asked for a Tigers version. Rather than forking, we extracted all team-specific values into JSON configs and parameterized the build pipeline. The result: 30 team pages generated from a single codebase in under 5 minutes.

(auto memory [claude]) The project had previously extracted CSS into a standalone `style.css` file read at build time -- this separation was a prerequisite that made the CSS variable rename feasible.

## Guidance

**Extract every entity-specific value into per-entity JSON config files, then inject them at build time via a CLI flag.**

The pattern has five layers:

### Layer 1: Per-entity config files (`teams/{slug}.json`)

One JSON file per entity with all customizable values:

```json
{
  "id": 116,
  "name": "Tigers",
  "full_name": "Detroit Tigers",
  "division_id": 202,
  "division_name": "AL Central",
  "colors": {
    "primary": "#0C2340",
    "primary_hi": "#1d4070",
    "accent": "#FA4616",
    "accent_hi": "#ff6a3d"
  },
  "venue": { "id": 2394, "name": "Comerica Park", "azimuth": 30, "nickname": "The Corner" },
  "affiliates": [
    {"id": 512, "name": "Toledo Mud Hens", "level": "AAA", "sport_id": 11}
  ],
  "branding": {
    "tagline": "A Daily Dispatch from The Corner & Beyond",
    "lede_tone": "like a beat writer who bleeds Midnight Blue and Orange",
    "idle_msg": "No Tigers game in progress"
  },
  "rivals": { "116": "Tigers", "114": "Guardians", "118": "Royals" }
}
```

### Layer 2: Build-time config loading (`build.py --team tigers`)

```python
def load_team_config(team_slug="cubs"):
    cfg_path = ROOT / "teams" / f"{team_slug}.json"
    return json.loads(cfg_path.read_text())

CFG = load_team_config(_team_slug)
TEAM_ID = CFG["id"]          # was: CUBS_ID = 112
AFFILIATES = CFG["affiliates"]
DIV_ID = CFG["division_id"]  # was: hardcoded 205
```

### Layer 3: CSS color injection via string replacement

Rather than a second `<style>` block or CSS preprocessor, replace the default color values in the stylesheet before inlining:

```python
CSS = CSS.replace(
    "--team-primary:#0E3386;--team-primary-hi:#2a56c4;",
    f"--team-primary:{colors['primary']};--team-primary-hi:{colors['primary_hi']};"
)
```

The CSS itself uses semantic names (`--team-primary`, `--team-accent`) rather than entity-specific names (`--cubs-blue`, `--cubs-red`).

### Layer 4: Client-side bridge for JS

Build-time injects entity config as global variables before JS loads:

```html
<script>var TEAM_ID=116;var TEAM_IDLE_MSG="No Tigers game in progress";</script>
<script src="live.js"></script>
```

`live.js` reads `window.TEAM_ID` instead of a hardcoded constant.

### Layer 5: Namespace caches per entity

Any file-based cache must include the entity slug to prevent cross-entity bleed:

```python
# Before: lede-2026-04-08.txt (shared -- Tigers build reads Cubs lede)
# After:  lede-tigers-2026-04-08.txt
lede_cache = DATA_DIR / f"lede-{team_slug}-{date}.txt"
```

### Bonus: Auto-generate all configs from an API

When the external API provides a complete roster:

```python
teams = fetch("/teams", sportId=1)["teams"]      # all 30 MLB teams
minors = fetch("/teams", sportIds="11,12,13,14")["teams"]  # affiliates with parentOrgId
# Map colors (well-documented), write teams/{slug}.json for each
```

This produced 30 team configs in seconds.

## Why This Matters

- **65+ edits collapse to 1 JSON file**: Adding a new entity means creating one config file. Zero code changes.
- **No runtime overhead**: Everything is baked in at build time. Output is still plain static HTML/CSS/JS.
- **No cross-entity bleed**: Namespaced caches prevent one entity's data from leaking into another's build.
- **Zero new dependencies**: The config system uses Python stdlib `json` and string replacement. No Jinja, no templating library, no CSS preprocessor.
- **Fork avoidance**: Two repos diverge immediately. Bug fixes and features must be applied to both. A single codebase with configs eliminates this entirely.
- **Scales linearly**: Auto-generation from the API produced all 30 teams. Manual work is only needed for entity-specific content (prospect lists, history entries).

## When to Apply

- A working single-entity app needs to support N entities with the same structure
- Hardcoded identifiers appear in 3+ files (the threshold where find-and-replace stops being viable)
- The project is a static site with build-time generation (no server to read config at request time)
- Each entity's output should be a standalone, self-contained directory (important for GitHub Pages, CDN, or S3 deployment)
- The external data source provides a machine-readable roster of all entities (enables auto-generation)

**Don't apply when:**
- Entity differences go beyond data (different layouts, features, or logic per entity)
- You only need 1 entity and have no realistic expectation of a second
- The project has a server that could serve config at request time (use a database instead)

## Examples

**Before -- Hardcoded single entity:**

```python
CUBS_ID = 112
```
```css
:root { --cubs-blue: #0E3386; --cubs-red: #CC3433; }
.standings tr.cubs { background: rgba(14,51,134,.28); }
```
```javascript
var CUBS_ID = 112;
```

**After -- Config-driven, any entity:**

```python
TEAM_ID = CFG["id"]  # from teams/{slug}.json
```
```css
:root { --team-primary: #0E3386; --team-accent: #CC3433; }
.standings tr.my-team { background: rgba(14,51,134,.28); }
```
```javascript
var TEAM_ID = window.TEAM_ID;  // injected by build.py
```

**Adding a new entity:**
```bash
python3 build.py --team tigers   # generates tigers/index.html
python3 build.py --landing       # regenerates team picker
```

## Related

- Implementation plan: `docs/plans/2026-04-08-004-feat-multi-team-support-plan.md`
- Enhancement plan (deferred multi-team): `docs/plans/2026-04-08-002-feat-morning-lineup-enhancements-plan.md` (scope boundary: "No team-agnostic config")
- MLB Stats API team roster: `/api/v1/teams?sportId=1` (all 30 MLB teams with IDs)
- MLB Stats API affiliate lookup: `/api/v1/teams?sportIds=11,12,13,14` (minor league teams with `parentOrgId`)
- MLB static CDN logos: `https://www.mlbstatic.com/team-logos/team-cap-on-dark/{id}.svg`
