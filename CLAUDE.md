# Morning Lineup — Daily MLB Briefing

Multi-team static site generator that produces daily MLB briefings for all 30 teams, published to GitHub Pages. Each team gets a config-driven page with its own colors, branding, affiliates, and history.

**Live:** https://brawley1422-alt.github.io/morning-lineup/
**Landing page:** Team picker with live standings, scores, and game status.

## Tech stack

- Python 3.12, stdlib only (no pip dependencies)
- Vanilla JS (no frameworks, no build step)
- GitHub Pages (static hosting)
- MLB Stats API v1 & v1.1 (no auth required)
- Fonts: Google Fonts CDN (Playfair Display, Oswald, Lora, IBM Plex Mono)
- Ollama (local LLM for editorial lede) with Anthropic API fallback

## Key files

| File | Purpose |
|------|---------|
| `build.py` | Orchestrator — fetches MLB Stats API data via `load_all()`, constructs a `TeamBriefing`, delegates section rendering to `sections/*.py`, assembles the page envelope. `--team {slug}` for any team, `--landing` for landing page. Test flags: `--fixture <path>`, `--out-dir <path>`, `--capture-fixture <path>` |
| `sections/` | One file per visible page section — each exports `render(briefing)` and reads everything from `briefing.data` / `briefing.team_name` / etc. No module-global reads, no imports from `build.py` at module top (deferred imports inside functions are OK) |
| `deploy.py` | Archives previous day's pages, deploys all 30 teams + landing to GitHub via Contents API |
| `evening.py` | Post-game watcher — polls for Cubs Final, triggers rebuild + deploy |
| `live.js` | Client-side polling for live game scores + full slate updates (team-agnostic via `window.TEAM_ID`) |
| `landing.html` | Landing page template — team picker with live standings/scores. `__TEAMS_JSON__` replaced at build time |
| `style.css` | Main stylesheet — inlined by build.py. Team colors injected via CSS variable overrides |
| `scorecard/` | The Scorecard Book — standalone game scorer (9 JS modules + CSS + HTML) |
| `sw.js` | Service worker for PWA offline caching |
| `teams/` | 30 per-team JSON configs (ID, colors, division, affiliates, branding, rivals) |
| `teams/{slug}/history.json` | Per-team "This Day in History" entries, keyed by MM-DD |
| `teams/{slug}/prospects.json` | Per-team prospect watchlist with IDs and rankings |
| `{slug}/` | Per-team output directory (index.html, live.js, scorecard/, icons/, etc.) |
| `data/` | Daily JSON data ledger + LLM-generated lede cache (`lede-{slug}-YYYY-MM-DD.txt`) |
| `archive/` | Daily snapshots of previous team pages |
| `tests/` | Golden snapshot harness — `python3 tests/snapshot_test.py` renders frozen Cubs + Yankees fixtures and diffs byte-identically against committed expected HTML. Re-bless procedure in `tests/README.md` |
| `docs/plans/` | Feature plans (living documents) |
| `docs/solutions/` | Documented solutions and best practices |

## Section files

Each file under `sections/` maps 1:1 to a visible page section and exports a `render(briefing)` function. `briefing` is a `TeamBriefing` dataclass (defined in `build.py`) with fields `config`, `data`, `team_id`, `team_name`, `div_id`, `div_name`, `affiliates`.

| File | Section | Returns |
|------|---------|---------|
| `sections/headline.py` | The {Team} — line score, three stars, key plays, scorecard embed, leaders, next games, form guide | `(inner_html, summary_tag)` |
| `sections/scouting.py` | Scouting Report (conditional — empty on off-days) | `inner_html` |
| `sections/stretch.py` | The Stretch — record, Pythagorean W-L, splits | `inner_html` |
| `sections/pressbox.py` | The Pressbox — transactions + injured list | `inner_html` |
| `sections/farm.py` | Down on the Farm — MiLB affiliates + prospect tracker | `(inner_html, minors_tag)` |
| `sections/slate.py` | Today's Slate | `inner_html` |
| `sections/division.py` | {Division} — standings + rivals | `inner_html` |
| `sections/around_league.py` | Around the League — news wire, scoreboard, all 6 divisions, league leaders. Also exports `render_lede_block(briefing)` for the page-top editorial lede | `(inner_html, news_count)` |
| `sections/history.py` | This Day in {Team} History | `inner_html` |

**Section file rules:**
- Import only stdlib and the local helpers each section needs. **Never `from build import ...` at module top** — `build.py` runs as `__main__`, and a top-level import would trigger a second full re-execution under the name `build`. Use deferred imports inside function bodies if you need `fetch_pitcher_line`, `fetch_weather_for_venue`, or other `build.py` helpers (see `sections/headline.py` for the pattern).
- Read per-team state exclusively through `briefing.*`. No module-global reads (`TEAM_ID`, `DIV_NAME`, etc.) — those are bound at import time in `build.py` and don't exist in section files.
- Small helpers (`_abbr`, `_fmt_time_ct`, `_ordinal`) are inlined per section file. Scope boundary: no shared `sections/_helpers.py` module yet.

## Adding or reordering sections

1. Create `sections/<new>.py` with a `render(briefing)` function.
2. Add `import sections.<new>` near the top of `build.py` (alphabetical).
3. Inside `page(briefing)`, call `new_html = sections.<new>.render(briefing)`.
4. Add a tuple to `_visible_sections` in `page()` — the numbering reshuffles automatically via the `_num` dict.
5. Add a `<section id="<new>">` block to the page envelope f-string with `<span class="num">{_num.get("<new>", "")}</span>`.
6. Add a `<li>` entry to the TOC.
7. Run `python3 tests/snapshot_test.py` — expect a diff (new content is intentional). Re-bless per `tests/README.md`.

## Scorecard modules

The `scorecard/` directory is a standalone app embedded via iframe:

| File | Purpose |
|------|---------|
| `app.js` | App controller — routing, polling, game loading, theme toggle |
| `parser.js` | Parses MLB live feed into scorecard data model |
| `diamond.js` | SVG diamond renderer with journey-aware basepaths |
| `panels.js` | Broadcast, weather, and player stats panels |
| `finder.js` | Date-based game finder |
| `header.js` | Game header (teams, score, decisions) |
| `scorebook.js` | Full scorecard table layout |
| `tooltip.js` | At-bat tooltips + strike zone overlay |
| `api.js` | MLB API fetch helpers with caching |
| `styles.css` | Scorecard-specific styles with dark/paper theme |

## Build & deploy

```bash
# Generate one team's briefing
python3 build.py --team cubs

# Generate landing page
python3 build.py --landing

# Deploy all 30 teams + landing to GitHub Pages
# PAT is stored at ~/.secrets/morning-lineup.env (chmod 600, outside repo)
source ~/.secrets/morning-lineup.env
python3 deploy.py

# Evening edition — watches for game Final, rebuilds + deploys
python3 evening.py          # normal mode
python3 evening.py --dry-run  # check status only
```

## Important patterns

- **Multi-team via config.** `teams/{slug}.json` drives everything: team ID, colors, division, affiliates, branding tone, rivals. `build.py --team {slug}` reads the config and generates a fully branded page.
- **CSS lives in `style.css`** and is inlined by build.py at build time. Team colors are injected by replacing CSS variable defaults with config values.
- **Zero external dependencies.** Uses only Python stdlib: `urllib`, `json`, `datetime`, `pathlib`, `html`, `zoneinfo`, `sys`.
- **Timezone:** Central Time via `ZoneInfo("America/Chicago")` — never hardcode UTC offsets.
- **HTML escaping:** Always use `html.escape()` on API-returned strings before injecting into HTML. In JS, use the `esc()` helper (defined per module).
- **Live polling:** `live.js` uses adaptive intervals — 20s when games are live, 5min when idle. Uses innerHTML diff check to prevent flicker. `window.TEAM_ID` set by build.py per team.
- **Editorial lede:** `generate_lede()` tries Ollama (qwen3:8b) first, falls back to Anthropic API, caches result in `data/lede-{slug}-YYYY-MM-DD.txt`.
- **Scorecard files are duplicated** across all 30 team directories. When changing scorecard code, update `scorecard/` (root) then copy to all team dirs.
- **API:** `API = "https://statsapi.mlb.com/api/v1"`, team ID from config (`CFG["id"]`)

## Sections generated by build.py

1. **The {Team}** — yesterday's game (line score, three stars, key plays, scorecard embed), team leaders, next 3 games, form guide (hot/cold hitters + pitchers last 7)
2. **Scouting Report** — today's pitching matchup deep dive with game logs (conditional — only when a game is scheduled)
3. **The Stretch** — season pulse: record, run differential, Pythagorean W-L, splits (home/away, vs RHP/LHP, day/night, etc.)
4. **The Pressbox** — recent transactions + injured list (side-by-side)
5. **Down on the Farm** — minor league affiliate results + prospect watch tracker
6. **Today's Slate** — full MLB schedule with probable pitchers, broadcasts, live score updates
7. **{Division}** — division standings + rival results from yesterday
8. **Around the League** — news wire (walk-offs, extras, shutouts, streaks), yesterday's scoreboard with scorecard links, all-division standings, league leaders
9. **This Day in {Team} History** — curated historical entries

## Design

Dark newspaper aesthetic with team-specific colors. Base palette: cream paper (#ece4d0), dark ink (#0d0f14), gold (#c9a24a). Team primary/accent colors injected from config. Collapsible sections via `<details>` elements. Scorecard has dark/paper theme toggle.
