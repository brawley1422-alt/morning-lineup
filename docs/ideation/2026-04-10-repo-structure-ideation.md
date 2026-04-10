---
date: 2026-04-10
topic: repo-structure
focus: folder structure improvements to support section-level tweaking
---

# Ideation: Morning Lineup Repo Structure

## Codebase Context

Python stdlib-only static site generator producing 30 GitHub Pages team subsites from a single codebase. Daily auto-build script (`build.py` + `deploy.py` + `evening.py`) runs on a schedule and pushes 30+ commits/day to `main`.

**Layout:**
- `teams/<slug>.json` + `teams/<slug>/{history,prospects}.json` — **input** configs (hand-edited)
- `<slug>/` at repo root (angels/, astros/, ..., yankees/) — **output** dirs holding generated `index.html`, `live.js`, `manifest.json`, `sw.js`, plus per-team copies of `scorecard/` and `icons/`
- `archive/<team>/` + dated `YYYY-MM-DD.html` at root — historical snapshots (mixed conventions)
- `data/YYYY-MM-DD.json` (~2.2MB daily ledger) + `data/lede-<slug>-YYYY-MM-DD.txt` (per-team LLM lede caches) — flat folder
- `scripts/` — utility scripts (backfill, populate_prospects, prospects cache)
- `scorecard/` — root source for Scorecard Book; copied into all 30 team output dirs on each build
- `build.py` — 1972 lines, reads config + API data, renders 9 sections via `render_*()` functions, writes one team's `index.html`

**Institutional knowledge** (from `docs/solutions/best-practices/config-driven-multi-tenant-static-site-2026-04-08.md`): the multi-tenant pattern was deliberate — extract Cubs-specific values into per-team configs, parameterize the build, generate 30 pages from one codebase.

**Key finding from grounding:** the dual `teams/<slug>/` (input) vs `<slug>/` (output) structure looks like duplication but isn't — it's a clean input/output split forced by GitHub Pages serving each team URL from `/<team>/`. The real friction is not folder layout; it's that section logic, data fetching, and HTML generation are interleaved in one 1972-line file, with no intermediate "team briefing object" passed between sections.

## Ranked Ideas

### 1. Sectioned `build.py` with single `TeamBriefing` object
**Description:** Split `build.py` into a `sections/` package — one file per section (`sections/headline.py`, `sections/standings.py`, etc.), each exporting `render(briefing) -> html`. Build a `TeamBriefing` dataclass once per team per day holding config + API data + computed flags, then pass it to every render function. Section list becomes a registry, killing the hardcoded numbering and the "fragile when sections hide" bug class.
**Rationale:** Direct hit on the "tweaking sections" workflow — open one file, see one function, typed inputs. Compounds across every future section tweak, addition, or removal. Makes the build path testable for the first time.
**Downsides:** Medium-effort refactor across the largest file in the repo. Has to be done in one coherent pass; half-converted state would be worse than current. Daily auto-build script must keep working throughout.
**Confidence:** 85%
**Complexity:** Medium
**Status:** Explored — handed off to ce:brainstorm 2026-04-10

### 2. Symlink shared assets instead of copying
**Description:** Replace the per-build copy of `scorecard/` (and any other shared dirs) into all 30 team output folders with a single source served once — via symlink, `_shared/` dir referenced by relative path, or GitHub Pages serving from a known root location.
**Rationale:** Currently every build copies `scorecard/` into 30 places. Every scorecard tweak shows up as 30 file changes in `git diff`, every daily build redoes 30 copies, partial failures leave drift. Quickest win in the set.
**Downsides:** Need to verify GitHub Pages serves symlinks correctly. Browser/PWA caching may have quirks if paths shift.
**Confidence:** 90%
**Complexity:** Low
**Status:** Unexplored

### 3. Golden-file snapshot test for one team
**Description:** Commit a reference `tests/fixtures/cubs_index.html` snapshot. Add a pre-build (or pre-commit) check that builds Cubs against frozen inputs and diffs against the fixture; flags any unintentional change. Re-bless via one command when the change is intentional.
**Rationale:** No safety net today for the scariest failure mode — a tweak that works for Cubs but silently breaks Yankees. Saved feedback already names this rule ("always rebuild all teams"). A snapshot test catches the regression class without you having to remember the rule, and makes survivor #1 safe to attempt.
**Downsides:** Fixture must snapshot a frozen-input run, not a live run, since live game data changes every build. Getting that nuance right is part of the work.
**Confidence:** 75%
**Complexity:** Low-Medium
**Status:** Unexplored

## Rejection Summary

| # | Idea | Reason Rejected |
|---|------|-----------------|
| 4 | Dry-run section preview CLI | DX tooling, not structural; partially redundant once #1 lands |
| 5 | Move team output dirs under `site/` or `dist/` | Touches deploy.py + Pages config + 30 archive paths; cosmetic gain doesn't justify infra risk on a live site |
| 6 | Split `data/` into `daily/` and `ledes/` | Cosmetic cleanup, no leverage |
| 7 | Normalize `archive/` convention | Low-leverage tidying — chore, not a project |
| 8 | Section feature flags per team config | Subsumed by survivor #1's section registry |
| 9 | Single-page app reading config at runtime | Massive rewrite, breaks deploy model, kills SEO/social previews — violates "remain compatible" constraint |
| 10 | Kill `archive/`, let git be the archive | Loses browseable URL access to past days |
| 11 | One commit/day instead of 30+ | Worth doing eventually but adjacent to section tweaks, not load-bearing |
| 12 | Derive `history.json` from MLB API | API doesn't cover narrative history; hand-curated for editorial reasons |
| 13 | Derive `prospects.json` from scrape | Already shipped (`populate_prospects.py`) |
| 14 | Client-side `briefing.json` render | Same problem as #9 |
| 15 | `teams.csv` replaces 30 JSON configs | JSON is richer for nested fields; CSV is worse for diffs |
| 16 | Jinja2 templates per section | Reasonable but a separate, larger transformation; #1 should land first |
| 17 | JSON schema validator for team config | Engineer-brain idea; running build catches the same failures |
| 18 | Briefing cache by (team, date, hash) | Premature optimization; build is already fast |
| 19 | `make` task runner with named targets | DX cleanup; JB asks Claude to run things, doesn't think in make targets |

## Session Log

- 2026-04-10: Initial ideation — 30 raw ideas generated across 3 frames (pain/friction, inversion/removal, leverage/compounding), 21 distinct after dedupe, 3 survived strict filtering (volume override "top 2-3"). Survivor #1 selected for brainstorm.
