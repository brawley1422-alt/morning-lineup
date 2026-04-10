---
title: "refactor: Sectioned build.py with TeamBriefing Object"
type: refactor
status: active
date: 2026-04-10
deepened: 2026-04-10
origin: docs/brainstorms/2026-04-10-sectioned-build-requirements.md
---

# refactor: Sectioned build.py with TeamBriefing Object

## Overview

`build.py` (1972 lines) holds 27 `render_*()` functions, the `load_all()` data fetcher, top-level helpers, the `page(data)` orchestrator at `build.py:1647`, and a `__main__` block at `build.py:1961-1972`. This plan implements the strangler-fig refactor approved in the brainstorm — splitting `build.py` into a `sections/` package of 9 files (one per visible page section) with a `TeamBriefing` dataclass passed to every section.

**This is the deepened revision of an earlier draft.** Three independent reviewers (an operational risk reviewer, an over-engineering reviewer, and an execution-readiness reviewer) audited the original plan and found landmines: the snapshot harness as originally specified would not work because `build.py` writes to a file rather than stdout, the editorial lede pipeline is non-deterministic from day one (not just at Unit 11), several render functions reach into module-level globals that section files cannot trivially access, the page envelope and section wrappers are not cleanly separable, the original section registry referenced a `today_scheduled` data key that does not exist, and `fetch_pitcher_line` is called from `load_all()` and therefore cannot move into `sections/slate.py`. This plan addresses every one of those findings explicitly. See the **Revision History from Independent Review** section near the end for the full changelog.

## Problem Frame

Brainstorm origin (`docs/brainstorms/2026-04-10-sectioned-build-requirements.md`) found the core friction: section logic, data fetching, and HTML generation are interleaved across a 1972-line file with no isolation between sections. JB is at the "tweaking sections" stage of product maturity and the current monolithic structure punishes that workflow. The Morning Lineup project is shipped, live, and is built daily via a cron loop (the cron loop itself lives outside this repo and iterates `python3 build.py --team <slug>` over the 30 team configs in `teams/*.json`) followed by `deploy.py` which pushes all 30 outputs to GitHub Pages. `evening.py` is a separate post-game watcher that rebuilds Cubs only (no `--team` flag, defaults to "cubs" at `build.py:34-37`) when the Cubs game reaches Final, then runs `deploy.py`. Per CLAUDE.md, the project is Python 3.12 stdlib-only with zero external dependencies — any tooling introduced by this refactor must respect that constraint.

## Requirements Trace

Each implementation unit traces back to a requirement (R1-R6) or success criterion (SC1-SC6) from the origin document. **One amendment to R2** is requested in this plan and propagated below: the `TeamBriefing` dataclass exposes per-team constants that are direct aliases of config keys (`team_id`, `team_name`, `div_name`, `div_id`, `affiliates`), in addition to the raw `config` and `data` dicts. This is not a "computed convenience field" because each constant is a one-line read of an existing config value — it is unavoidable because section files need access to these constants and the only alternatives are circular imports or copying global lookups into every section file.

- **R1** — Section files match user's mental model (9 files matching visible page sections). Addressed by Units 3-11.
- **R2 (amended)** — `TeamBriefing` dataclass holds raw config, raw data, and per-team config-alias constants only. No computed convenience fields like Pythagorean W-L or pre-formatted record strings. Addressed by Unit 2.
- **R3** — Daily auto-build script keeps working uninterrupted. Addressed by all units via byte-identical output verification (Unit 1 provides the safety net).
- **R4** — Strangler-fig migration with prep step. The entire 12-unit sequence is structured around this requirement.
- **R5** — Each extraction PR produces byte-identical output. Enforced by Unit 1's snapshot test serving as a gate for Units 3-11.
- **R6** — `build.py` ends shaped as an orchestrator. Addressed by Unit 12.
- **SC1** — `build.py` under 600 lines after the refactor. Verified at Unit 12 completion.
- **SC2** — Section tweaks become "open one file." Verified subjectively by JB after Unit 5 (third extraction).
- **SC3** — Zero failed cron runs traceable to refactor PRs. Verified continuously across all units via `archive/<team>/YYYY-MM-DD.html` existence checks.
- **SC4** — Snapshot test catches at least one regression (or migration completes cleanly with permanent safety net). Either outcome valid.
- **SC5** — Section registry kills hardcoded numbering bug class. Addressed by Unit 12.
- **SC6** — JB can describe the new structure in one sentence. Verified at Unit 12 completion.

## Scope Boundaries

Carried forward from the origin document's "Out of Scope" section. Confidence: HIGH.

- **Out of scope:** Jinja2 templates per section, symlinking scorecard/shared assets (ideation survivor #2 — separate effort), moving team output dirs under `site/`, single-page-app conversion, JSON schema validators, briefing cache by `(team, date, hash)`, `make` task runner, refactoring helpers (`fmt_time_ct`, `_ordinal`, etc.) into their own module, pre-computing convenience fields on `TeamBriefing` beyond direct config aliases, unit tests for individual section render functions, changes to what `load_all()` fetches.
- **Explicitly deferred:** Per-team section visibility flags in config (Unit 12's section registry makes this trivial to add later), automatic cleanup of obsolete `archive/` snapshots, refactoring `build.py`'s module-level state into a `main()` function (subprocess-based testing dodges this so it isn't required for the migration to succeed).

## Context & Research

### Relevant Code and Patterns

Findings from prior brainstorm grounding scan, direct file inspection during planning, and the deepening review:

- **`build.py:1`-`51`** — Module top: imports, `ROOT` path, `load_team_config()`, the `--team` argv parser at lines 33-37, and the module-level globals `CFG`, `TEAM_ID`, `TEAM_NAME`, `AFFILIATES`, `DIV_ID`, `DIV_NAME`, `OUT`, `HISTORY_FILE`, `PROSPECTS_FILE`, `DATA_DIR`. These are computed at import time after the argv parse. They are read by `load_all()`, by render functions, and by the page envelope.
- **`build.py:60`-`80`** — `fetch()`, `teams_map()`, `_ordinal()` helpers.
- **`build.py:83`-`386`** — `load_all()`. The single API/data fetcher. Returns the dict that flows into `page()`. **Critically, `load_all()` reads `TEAM_ID`, `AFFILIATES`, and `DIV_ID` directly from module globals** (e.g., `build.py:112`, `build.py:120`, `build.py:274`, `build.py:577`). It also calls `fetch_pitcher_line()` at `build.py:342` — confirmed during deepening review. This means `fetch_pitcher_line` cannot move into `sections/slate.py`; it must remain in `build.py`.
- **`build.py:370`-`386`** — The exact return shape of `load_all()`. Keys: `today, yest, season, tmap, games_y, games_t, standings, cubs_rec, next_games, today_lineup, today_series, today_opp_info, cubs_game, cubs_game_date, boxscore, plays, injuries, cubs_hitters, cubs_pitchers, cubs_season, leaders_hit, leaders_pit, minors, prospects, history, transactions, scout_data`. **There is no `today_scheduled` key.** The earlier draft of this plan invented one for the Unit 12 visibility lambda — corrected below.
- **`build.py:626`** — `fetch_pitcher_line(pid)`. Called at lines 342 (inside `load_all`), 717, 718 (inside `render_next_games`). **Must stay in `build.py`** because of the `load_all` callsite.
- **`build.py:645`** — `fetch_weather_for_venue(venue)`. Called only at line 741 (inside `render_next_games`). May move with `sections/slate.py`.
- **`build.py:1366`** — `generate_lede(data)`. **Has a deterministic cache lookup at `build.py:1368`-`1372`**: it reads `DATA_DIR / f"lede-{_team_slug}-{data['today'].isoformat()}.txt"` and returns the cached text if present. This is the lever for snapshot test determinism — committing the fixture-date lede cache files makes the test bypass Ollama/Anthropic entirely without any code changes to `generate_lede`.
- **`build.py:1624`** — `render_history(history_items)`. The proof-of-concept extraction target. Smallest section, single input, reads only from `teams/<slug>/history.json`.
- **`build.py:1647`** — `page(data)`. The orchestrator. Receives `data` directly, calls render functions inline (lines 1660-1707), returns one giant f-string for the entire page. **Reads module globals** `DIV_NAME`, `CSS`, `TEAM_NAME`, `DIV_NAME`, `TEAM_ID`, `CFG['branding'][...]` inside the f-string.
- **`build.py:1660`-`1664`** — `render_line_score` returns a tuple `(html, summary_tag)` consumed by the section header at line 1772. Unit 8 (headline) must preserve this.
- **`build.py:1690`-`1694`** — `render_minors` returns a tuple `(html, minors_tag)` consumed by the section header at line 1822. **Unit 7 (farm) must also preserve this** — the original plan missed it.
- **`build.py:1712`-`1923`** — The page envelope. One giant f-string. Section wrappers (`<section id="team">`, `<section id="scout">`, etc.) are part of the f-string and are NOT cleanly separable from the envelope. Hardcoded section numbering: `<span class="num">01</span>` for Team, then `"03" if scout_html else "02"` for Pulse at line 1800, etc. The TOC at lines 1750-1761 has its own conditional `{'<li>...</li>' if scout_html else ''}` for the scout entry. This entire block is the surface area Unit 12 must address.
- **`build.py:1933`** — `save_data_ledger(data)`. Already serializes the data dict to `data/YYYY-MM-DD.json` using `_json_default` at `build.py:1927` which calls `obj.isoformat()` on date/datetime objects. **This is the fixture format for Unit 1.** A fixture reader must rehydrate ISO strings back into `date` objects for the keys `today`, `yest`, and `cubs_game_date` (the only `date`-typed values in the dict).
- **`build.py:1961`-`1972`** — `__main__` block. Calls `load_all()`, `save_data_ledger(data)`, `page(data)`, then `OUT.write_text(html)`. **Writes to file, not stdout.** The earlier draft of this plan assumed stdout. Corrected: Unit 1 adds `--out-dir <path>` to override the destination directory, and the snapshot test reads the resulting file.
- **`evening.py:84`** — `subprocess.run([sys.executable, str(ROOT / "build.py")], cwd=str(ROOT))`. **No `--team` flag.** Builds Cubs only (the `--team` default at `build.py:34`). The new flags introduced in Unit 1 are additive and not passed by `evening.py`, so they cannot accidentally activate.
- **`deploy.py:67-72`** — Iterates `teams_dir.glob("*.json")`, reads each `<slug>/index.html`, pushes via GitHub Contents API. `deploy.py` itself never calls `build.py`. **The morning cron loop that builds all 30 teams lives outside this repo.** Inferred behavior: a shell or systemd timer wrapper that runs `python3 build.py --team <slug>` for each team config, then runs `python3 build.py --landing`, then `python3 deploy.py`. Verification step in Unit 1: confirm with JB whether this loop ever passes flags other than `--team` and `--landing`. If it does, Unit 1 must rename its new flags to avoid collision.
- **CLAUDE.md "Zero external dependencies" constraint** — forces Unit 1 to use stdlib `difflib`, `json`, `pathlib`, `subprocess` only. This is a hard constraint, not a preference.

### Institutional Learnings

From the prior ideation grounding agent's findings against `docs/solutions/`:

- **`docs/solutions/best-practices/config-driven-multi-tenant-static-site-2026-04-08.md`** — confirms the multi-tenant config pattern is intentional and should be preserved. The refactor must not collapse the per-team config into shared state.
- **JB's saved feedback** ("always rebuild all teams when changing shared assets") is the human version of what the snapshot test will automate. Unit 1 is essentially codifying this rule.

### External References

Skipped per Phase 1.2 — the codebase has strong local patterns for stdlib-only file IO and JSON handling, and the refactor is mechanical rather than novel. No external research needed.

## Key Technical Decisions

1. **Snapshot test uses stdlib `difflib.unified_diff` and runs `build.py` as a subprocess.** Confidence: HIGH. CLAUDE.md mandates zero external dependencies. Subprocess-based testing dodges Python's import-time global state in `build.py:34-51` so we do not need to refactor module-level state into a `main()` function as a prerequisite.

2. **The snapshot test diffs files written to a tempdir, not stdout.** Confidence: HIGH. `build.py:1971` does `OUT.write_text(html)` — there is no stdout HTML. Unit 1 adds an `--out-dir <path>` flag that overrides the destination directory. The test invocation is `python3 build.py --team cubs --fixture <input.json> --out-dir <tempdir>`, then the test reads `<tempdir>/cubs/index.html` and diffs against the expected fixture.

3. **Frozen API inputs are committed JSON fixtures captured via `save_data_ledger`'s existing format.** Confidence: HIGH. `save_data_ledger` at `build.py:1933` already writes the data dict to `data/YYYY-MM-DD.json` via `json.dumps(data, default=_json_default)`. Unit 1 reuses this format. A new `--capture-fixture <path>` flag in `build.py` runs `load_all()` and then writes its output to the given path using the existing serializer, then exits.

4. **The fixture reader explicitly rehydrates ISO date strings.** Confidence: HIGH. `_json_default` at `build.py:1927` converts `date` objects to ISO strings during serialization. The reverse path is not symmetric — `json.loads` returns the ISO strings as plain `str`. The fixture loader in `build.py` (added in Unit 1) reads the JSON, then explicitly does `data["today"] = date.fromisoformat(data["today"])`, `data["yest"] = date.fromisoformat(data["yest"])`, and (if present) `data["cubs_game_date"] = date.fromisoformat(data["cubs_game_date"])`. The expression `(t - date(t.year, 1, 1)).days` at `build.py:1709` requires `t` to be a real `date`, so missing this rehydration crashes the test.

5. **Lede determinism is achieved by committing the fixture-date lede cache files**, not by changing `generate_lede`. Confidence: HIGH. `generate_lede` at `build.py:1368-1372` reads `DATA_DIR / f"lede-{_team_slug}-{data['today'].isoformat()}.txt"` first and returns it if present, bypassing Ollama and Anthropic entirely. Unit 1 commits `data/lede-cubs-2026-04-05.txt` and `data/lede-yankees-2026-04-05.txt` (matching the fixture date) as part of the test fixtures. No code changes to `generate_lede`. **This was the single biggest landmine the operational reviewer caught — without this fix, Unit 1 would have made live LLM calls on every test run.**

6. **Two test teams: Cubs and Yankees.** Confidence: HIGH. Cubs is the canonical default (`build.py:34`) and the highest-risk regression target. Yankees is a deliberately different team — different division (AL East vs NL Central), different colors, different rivals, different `CFG['rivals']` lookup at `build.py:980`. Cubs-only testing would miss any bug that surfaces only when `TEAM_ID != 112` (the Cubs ID). The over-engineering reviewer argued one team is enough; I'm overruling that argument because the multi-tenant rivalry/division logic is exactly the kind of code path Cubs alone would not exercise.

7. **`TeamBriefing` exposes per-team constants as direct config-alias fields, not just `config` and `data`.** Confidence: HIGH. The original brainstorm R2 said "raw config + raw data only, no computed fields." That is preserved in spirit but amended in letter: `team_id`, `team_name`, `div_name`, `div_id`, `affiliates` become fields on the dataclass because they are direct one-line aliases for `config["id"]`, `config["name"]`, `config["division_name"]`, `config["division_id"]`, `config["affiliates"]`. They are NOT computed (no parsing, no derivation, no formatting). Without this amendment, every section file would either need to import `TEAM_NAME` from `build.py` (circular import risk per the execution-readiness reviewer's Landmine 1) or read `briefing.config["name"]` everywhere (mechanically tedious and error-prone during the 9-section migration).

8. **`TeamBriefing` does NOT hold `CSS`.** Confidence: HIGH. The CSS substitution at `build.py:1636-1644` is consumed only by the page envelope's `<style>{CSS}</style>` tag at line 1724. Section files do not need CSS. Keeping CSS out of `TeamBriefing` preserves the "raw aliases only" principle.

9. **Section files import only stdlib and `TeamBriefing`.** Confidence: HIGH. Each `sections/<name>.py` does `from html import escape` and (if it needs `TeamBriefing` as a type hint) `from build import TeamBriefing` — but the function body never references module-level globals from `build.py`. All per-team state comes through the `briefing` parameter. This avoids the circular-import trap the execution-readiness reviewer flagged.

10. **`sections/__init__.py` is empty (namespace package only).** Confidence: HIGH. No re-exports, no shared imports. Each section file is independently importable. Avoids the trap where `sections/__init__.py` becomes a second monolith.

11. **Section render functions return inner HTML only; the page envelope and section wrappers stay in `build.py` until Unit 12.** Confidence: HIGH. This is the only way Units 3-11 are byte-identical refactors. The page envelope at lines 1768-1877 keeps its hardcoded section wrappers and conditional numbering during the migration. Unit 12 is what addresses the wrappers.

12. **Units 2-12 form a chain that must be reverted in reverse order.** Confidence: HIGH. The original plan claimed every PR is "independently mergeable." That was wrong. Once Unit 2 introduces `TeamBriefing` and Unit 3 changes `page(data)` to `page(briefing)`, every later unit depends on the dataclass existing. If you need to roll back Unit 3, you must NOT also roll back Unit 2 — the dataclass needs to remain. If you need to roll back Unit 2, you must roll back Units 3-12 first. Unit 1 (the snapshot harness) IS independently mergeable and revertible, since it only adds new flags and new test files without touching the production render path.

13. **`fetch_pitcher_line` stays in `build.py`.** Confidence: HIGH. It is called at `build.py:342` inside `load_all()`. Moving it into `sections/slate.py` would break scouting data. The execution-readiness reviewer caught this. `fetch_weather_for_venue` is only called at line 741 inside `render_next_games`, so it MAY move into `sections/slate.py` — Unit 10's choice.

14. **Section registry computes numbering dynamically, not from a hardcoded list.** Confidence: MEDIUM. The original Unit 12 specified a `(name, render_fn, visible_when)` tuple list with a `today_scheduled` lambda — but `today_scheduled` is not a key in the data dict. The corrected approach: section visibility is determined by whether the rendered HTML is non-empty, matching the current `if scout_html` post-render check at `build.py:1796`. The registry iterates sections, calls each render function, and assigns numbering only to sections whose rendered HTML is truthy. This is structurally what `page()` already does — Unit 12 just makes the iteration explicit.

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

**Before (current shape):**

```
build.py (1972 lines)
├── (module top) sys.argv parse, CFG, TEAM_ID, TEAM_NAME, OUT, CSS — globals
├── load_team_config()
├── load_all() — reads TEAM_ID, AFFILIATES, DIV_ID from globals
├── render_line_score, render_three_stars, ..., render_history  (27 functions)
├── page(data) — calls render_*() inline at lines 1660-1707, returns f-string envelope
└── __main__ — load_all() → save_data_ledger() → page(data) → OUT.write_text(html)
```

**After (target shape):**

```
build.py (~600 lines)
├── (module top) sys.argv parse, CFG, TEAM_ID, ... — globals (UNCHANGED — Unit 0 was rejected)
├── load_team_config()
├── load_all()
├── @dataclass TeamBriefing(config, data, team_id, team_name, div_name, div_id, affiliates)
├── build_briefing(team_slug) -> TeamBriefing
├── load_briefing_from_fixture(fixture_path) -> TeamBriefing  (Unit 1)
├── fetch_pitcher_line(), fetch_weather_for_venue() — stay (load_all uses fetch_pitcher_line)
├── SECTIONS = [...]   # registry — Unit 12
├── page(briefing) — iterates SECTIONS, assembles envelope
└── __main__ — branches on --fixture / --capture-fixture / --out-dir flags

sections/
├── __init__.py                (empty)
├── headline.py                (line score + three stars + key plays + cubs leaders + next games + hot/cold)
├── stretch.py                 (record + Pythagorean + splits)
├── pressbox.py                (injuries + transactions)
├── farm.py                    (minor leagues + prospects — returns tuple (html, minors_tag))
├── slate.py                   (today's slate + next games — fetch_weather_for_venue may move here)
├── division.py                (NL Central rivals + standings)
├── around_league.py           (news + scoreboard + leaders + lede pipeline)
├── history.py                 (this day in team history)
└── scouting.py                (conditional pre-game scouting)

tests/
├── __init__.py                (empty)
├── snapshot_test.py           (subprocess runner using difflib)
└── fixtures/
    ├── cubs_2026_04_05_input.json     (load_all() output, frozen)
    ├── cubs_2026_04_05_expected.html  (golden render)
    ├── yankees_2026_04_05_input.json
    └── yankees_2026_04_05_expected.html

data/
├── lede-cubs-2026-04-05.txt           (committed lede cache for fixture date — bypasses Ollama)
└── lede-yankees-2026-04-05.txt
```

**Section file shape (uniform across all 9):**

```
# sections/<name>.py
from html import escape
from build import TeamBriefing  # type-only

def render(briefing):
    cfg = briefing.config
    data = briefing.data
    team_name = briefing.team_name
    div_name = briefing.div_name
    # ... existing render_* logic, transcribed verbatim, with parameter
    #     references rewritten to read from briefing.* and the local aliases
    return html_string
```

For sections that currently return tuples (`render_line_score` → headline, `render_minors` → farm), the section's `render(briefing)` continues to return a tuple. The orchestrator unpacks it the same way `page()` does today.

**The sequencing principle:** each PR moves logic without changing it. Cosmetic improvements happen as separate follow-up PRs after extraction is complete.

## Implementation Units

- [ ] **Unit 1: Golden snapshot harness with frozen fixtures**

**Goal:** Build the safety net that gates every subsequent extraction PR. After this unit lands, anyone can run `python3 tests/snapshot_test.py` and verify that Cubs and Yankees both render byte-identically against committed reference HTML, with no live API calls and no LLM calls.

**Requirements:** R3, R5, SC4

**Dependencies:** None — this is the prep PR. Independently mergeable and independently revertible.

**Files:**
- Create: `tests/__init__.py` (empty)
- Create: `tests/snapshot_test.py`
- Create: `tests/fixtures/cubs_2026_04_05_input.json`
- Create: `tests/fixtures/cubs_2026_04_05_expected.html`
- Create: `tests/fixtures/yankees_2026_04_05_input.json`
- Create: `tests/fixtures/yankees_2026_04_05_expected.html`
- Create: `data/lede-cubs-2026-04-05.txt` (committed lede cache for fixture date)
- Create: `data/lede-yankees-2026-04-05.txt`
- Modify: `build.py` — add three new flags to the `__main__` block: `--fixture <path>`, `--out-dir <path>`, `--capture-fixture <path>`. Add a `load_data_from_fixture(path)` helper that reads the JSON and rehydrates `today`, `yest`, `cubs_game_date` to `date` objects.

**Approach:**

The new flags slot into `build.py`'s existing `__main__` block at `build.py:1961-1972`. The new control flow:

1. If `--landing` is in argv: call `build_landing()` and exit (unchanged).
2. If `--capture-fixture <path>` is in argv: call `load_all()`, write the result to `<path>` using `json.dumps(data, default=_json_default)`, print confirmation, exit.
3. If `--fixture <path>` is in argv: call `load_data_from_fixture(<path>)` instead of `load_all()`. Then proceed normally — call `save_data_ledger`, `page(data)`, write output.
4. If `--out-dir <path>` is in argv: override `OUT` to `<path> / _team_slug / "index.html"` before writing. (`OUT` is currently a module global computed at `build.py:51`; the override happens inside `__main__` at write time.)
5. Default path (no new flags): unchanged behavior.

`load_data_from_fixture(path)` reads the JSON via `json.loads(Path(path).read_text())`, then performs explicit date rehydration:
- `data["today"] = date.fromisoformat(data["today"])`
- `data["yest"] = date.fromisoformat(data["yest"])`
- If `data.get("cubs_game_date")`: `data["cubs_game_date"] = date.fromisoformat(data["cubs_game_date"])`

`tests/snapshot_test.py` is a plain Python script that:
1. Defines a list of `(slug, fixture_input, fixture_expected)` tuples for Cubs and Yankees.
2. For each tuple, creates a temp dir via `tempfile.mkdtemp()`.
3. Runs `subprocess.run([sys.executable, "build.py", "--team", slug, "--fixture", fixture_input, "--out-dir", tempdir], cwd=ROOT, check=True)`.
4. Reads `<tempdir>/<slug>/index.html`.
5. Reads the expected HTML from `fixture_expected`.
6. If they differ, prints a `difflib.unified_diff` and exits non-zero.
7. If both match, prints "Cubs snapshot OK; Yankees snapshot OK" and exits 0.
8. Cleans up tempdirs.

**Bootstrap sequence (to capture the initial fixtures and expected HTML):**
1. Implementer adds the three flags and the fixture loader.
2. Implementer runs `python3 build.py --team cubs --capture-fixture tests/fixtures/cubs_2026_04_05_input.json` once. This writes the captured `load_all()` output as JSON.
3. Implementer manually edits the resulting JSON file to set `today`, `yest`, `cubs_game_date` to ISO strings for `2026-04-05` (the chosen fixture date) — this is necessary because `load_all()` captures values for the actual run date, but we want the fixture frozen to a specific date so the lede cache lookup is stable.
4. Implementer manually creates `data/lede-cubs-2026-04-05.txt` with a chosen lede text (one or two sentences).
5. Implementer runs `python3 build.py --team cubs --fixture tests/fixtures/cubs_2026_04_05_input.json --out-dir /tmp/snap-bless`, copies `/tmp/snap-bless/cubs/index.html` to `tests/fixtures/cubs_2026_04_05_expected.html`. This is the manual blessing step.
6. Implementer eyeballs the resulting `expected.html` to confirm it looks right (this is the only manual verification — after this, all future runs are automated).
7. Implementer repeats steps 2-5 for Yankees.
8. Implementer runs `python3 tests/snapshot_test.py` and confirms it passes.

The bootstrap is a one-time manual step. After Unit 1 ships, the snapshot test runs hands-off.

**Patterns to follow:**
- `build.py:1933` `save_data_ledger()` — already serializes the same dict to JSON. The fixture format is exactly the same shape. Reuse `json.dumps(data, default=_json_default)`.
- `build.py:1927` `_json_default()` — handles date/datetime serialization. The fixture loader is the inverse.
- CLAUDE.md "Zero external dependencies" — `difflib`, `json`, `pathlib`, `subprocess`, `tempfile` only. No pytest, no syrupy, no third-party libraries.
- Existing argv parsing in `build.py:33-37` and `__main__` block in `build.py:1961-1972` — add the new flags inline alongside `--team` and `--landing`.

**Test scenarios:**
- Happy path: `python3 tests/snapshot_test.py` exits 0 with "Cubs snapshot OK; Yankees snapshot OK".
- Regression detected: introduce a one-character whitespace change inside `render_history()` at `build.py:1624`, run the test, confirm it exits non-zero with a diff highlighting the affected line, on at least one of the two teams.
- Multi-team regression: introduce a change in a shared render function (e.g., `render_line_score`), run the test, confirm both Cubs and Yankees diffs appear in output.
- Re-bless workflow: after an intentional change, re-run the bootstrap blessing step manually for both teams, run the test again, confirm it now passes. Document the re-blessing procedure in `tests/README.md` (add this file as part of Unit 1).
- Network independence: disconnect the machine from the internet, run the test, confirm it still passes. This proves `--fixture` bypasses live API and the committed lede cache bypasses LLM calls.
- Date rehydration check: confirm the test does NOT crash at `build.py:1709` `(t - date(t.year, 1, 1)).days` — that would mean `today` is still a string. If it crashes here, the rehydration step is broken.
- Lede cache miss: temporarily rename `data/lede-cubs-2026-04-05.txt`, run the test, confirm it crashes or hangs (proves the cache is the bypass mechanism). Restore the file and re-run.

**Verification:**
- `python3 tests/snapshot_test.py` exits 0 with both teams reporting OK.
- Removing or breaking any `render_*` function in `build.py` causes the test to fail with a readable diff on at least one team.
- `git status` shows only the new test files, fixtures, lede cache files, the new flag handling in `build.py`, and `tests/README.md`. Nothing else.
- `python3 build.py --team cubs` (the cron command) still works exactly as before — the new flags are inert when not passed.
- **Verification with JB before merging:** ask JB to grep his cron config (wherever it lives — outside this repo) for `build.py` invocations and confirm none of them pass `--fixture`, `--out-dir`, or `--capture-fixture`. If any of them do, those flag names must be renamed to avoid collision.

---

- [ ] **Unit 2: `TeamBriefing` dataclass and `build_briefing()` constructor**

**Goal:** Add the dataclass and constructor that all subsequent section extractions will depend on, without changing any existing render path or output.

**Requirements:** R2 (amended), R3

**Dependencies:** Unit 1 (snapshot test must exist so this unit can prove it changed nothing).

**Files:**
- Modify: `build.py` — add `TeamBriefing` dataclass and `build_briefing(team_slug)` function near the top, after `load_all()` at `build.py:386`.

**Approach:**

`TeamBriefing` is a `@dataclass` with these fields (per Decision 7):
- `config: dict` — the full per-team JSON config (the return of `load_team_config`)
- `data: dict` — the raw API/data dictionary (the return of `load_all`)
- `team_id: int` — alias for `config["id"]`
- `team_name: str` — alias for `config["name"]`
- `div_id: int` — alias for `config["division_id"]`
- `div_name: str` — alias for `config["division_name"]`
- `affiliates: list` — alias for `config["affiliates"]`

`build_briefing(team_slug)` calls the existing `load_team_config(team_slug)` (which uses the module global `_team_slug` indirectly — but accepts an explicit slug parameter, so this works), then `load_all()`, then constructs and returns a `TeamBriefing(config=..., data=..., team_id=..., ...)`.

**Important caveat about module-level state:** `load_all()` reads `TEAM_ID`, `AFFILIATES`, `DIV_ID` from module globals. Those globals are set at `build.py:34-44` from the `--team` argv parse at import time. So `build_briefing(team_slug)` only works correctly when called with the same team slug that was passed via `--team`. Calling `build_briefing("yankees")` while the process was started with `--team cubs` would return Cubs data tagged as Yankees. This is a real footgun but acceptable for now — Unit 2 does NOT call `build_briefing` from anywhere except inside the `__main__` block (which already has the right `_team_slug`). If a future unit needs to call `build_briefing` from a non-`__main__` context, it must first refactor the module-level globals (out of scope for this plan).

`page()` is **not modified** in this unit. It still receives `data` directly. The dataclass exists alongside but is not yet wired into the production render path. This is deliberate — Unit 2 has zero behavior change.

**Patterns to follow:**
- `build.py:24` `load_team_config()` — returns the dict that becomes `briefing.config`.
- `build.py:83` `load_all()` — returns the dict that becomes `briefing.data`.
- `build.py:39-44` — the existing module-global pattern is the source for the alias values.
- Stdlib `dataclasses` module is part of Python 3.12 standard library — confirmed compatible with CLAUDE.md constraint.

**Test scenarios:**
- Happy path: snapshot test from Unit 1 still passes byte-identically (no behavior changed).
- Smoke test (subprocess-based, NOT import-based): add a small test in `tests/snapshot_test.py` that runs `python3 -c "import sys; sys.path.insert(0, '.'); from build import TeamBriefing; print('ok')"` as a subprocess and asserts the output is "ok". Note: this DOES trigger build.py's import-time CLI parse, which will default to `--team cubs`. That's fine — the smoke test only confirms the symbol exists.
- Constructor check: the snapshot test still passes after this unit — the existence of the new dataclass and constructor cannot affect production output because nothing calls them yet.

**Verification:**
- Snapshot test passes unchanged.
- `wc -l build.py` is roughly 1990-2010 lines (1972 + small additions).
- `grep -c "@dataclass" build.py` returns at least 1.

---

- [ ] **Unit 3: Proof-of-concept — extract `sections/history.py`**

**Goal:** Move `render_history` out of `build.py` and into `sections/history.py`. Prove the strangler-fig pattern end-to-end on the smallest, lowest-dependency section. Wire `build_briefing()` into the `__main__` path so subsequent units can build on it.

**Requirements:** R1, R5

**Dependencies:** Unit 2 (needs `TeamBriefing`).

**Files:**
- Create: `sections/__init__.py` (empty)
- Create: `sections/history.py`
- Modify: `build.py` — remove `render_history` definition at `build.py:1624`; modify `page()` at `build.py:1647` to take `briefing` and call `sections.history.render(briefing)` in place of `render_history(data["history"])` at `build.py:1703`; modify the `__main__` block at `build.py:1961-1972` to call `build_briefing()` and pass the result to `page()`.

**Approach:**

`sections/history.py` contains:
```
from html import escape
from build import TeamBriefing  # type-only import for clarity

def render(briefing):
    history_items = briefing.data["history"]
    # ... existing render_history body verbatim, with `history_items` references unchanged ...
    return html_string
```

`page()` is renamed from `def page(data):` to `def page(briefing):`. The first line becomes `data = briefing.data` so all the existing `data["..."]` references inside `page()` continue to work without modification. The single change inside `page()` is replacing `history_html = render_history(data["history"])` at `build.py:1703` with `history_html = sections.history.render(briefing)`. Add `from sections import history` at the top of `build.py` (after the existing imports — circular import risk is dodged because `sections/history.py` only imports `TeamBriefing` which is defined before `from sections import history` is encountered at module load).

The `__main__` block changes:
```
# Before:
data = load_all()
save_data_ledger(data)
html = page(data)

# After:
briefing = build_briefing(_team_slug)
save_data_ledger(briefing.data)
html = page(briefing)
```

The `--fixture` path from Unit 1 also branches here: when `--fixture` is passed, the `__main__` block constructs the briefing from the fixture-loaded data instead of from `build_briefing`:
```
if "--fixture" in sys.argv:
    fixture_path = sys.argv[sys.argv.index("--fixture") + 1]
    data = load_data_from_fixture(fixture_path)
    briefing = TeamBriefing(
        config=CFG, data=data,
        team_id=TEAM_ID, team_name=TEAM_NAME,
        div_id=DIV_ID, div_name=DIV_NAME,
        affiliates=AFFILIATES,
    )
else:
    briefing = build_briefing(_team_slug)
```

The snapshot test must produce zero diff after this unit lands. Any diff is a sign the extraction was not verbatim.

**Patterns to follow:**
- `build.py:1624` `render_history` — the source function being moved.
- `build.py:1703` — the call site inside `page()` that gets rewritten.
- `build.py:1647` `page(data)` signature — gets rewritten to `page(briefing)`.

**Test scenarios:**
- Happy path: snapshot test passes byte-identically for both Cubs and Yankees.
- Reachability: `grep -n "def render_history" build.py` returns zero matches after this unit; `grep -n "render_history" build.py` returns zero matches.
- Cron compatibility: `python3 build.py --team cubs` (the cron command) runs without errors and produces non-empty `cubs/index.html`.
- Section file independence: `python3 -c "from sections.history import render"` works as a subprocess.
- Branch correctness: `python3 build.py --team cubs --fixture tests/fixtures/cubs_2026_04_05_input.json --out-dir /tmp/test-3` writes the expected file and the snapshot test still passes.

**Verification:**
- Snapshot test passes byte-identically.
- `build.py` no longer contains `def render_history`.
- `python3 build.py --team cubs` writes a non-empty `cubs/index.html`.
- `wc -l build.py` is smaller than after Unit 2 by roughly 20-25 lines.

---

- [ ] **Unit 4: Extract `sections/stretch.py`**

**Goal:** Second-easiest extraction. Establishes the pattern is reusable.

**Requirements:** R1, R5

**Dependencies:** Unit 3 (proves the pattern).

**Files:**
- Create: `sections/stretch.py`
- Modify: `build.py` — remove `render_stretch` at `build.py:1514`; rewrite the call site inside `page()` at `build.py:1701`.

**Approach:**

Same pattern as Unit 3. Move `render_stretch` body verbatim into `sections/stretch.py`. The single parameter `cubs_rec` becomes `briefing.data["cubs_rec"]`. Add `from sections import stretch` to `build.py` imports. Update the call at `build.py:1701` to `stretch_html = sections.stretch.render(briefing)`.

If `render_stretch` reads any module globals (likely `DIV_NAME` for the rank suffix at `build.py:1571`), replace those reads with `briefing.div_name`.

**Test scenarios:**
- Happy path: snapshot test passes byte-identically for both teams.
- Pattern check: `sections/stretch.py` follows the same `def render(briefing):` shape as `sections/history.py`.

**Verification:**
- Snapshot test passes.
- `wc -l build.py` is smaller than after Unit 3.

---

- [ ] **Unit 5: Extract `sections/scouting.py`**

**Goal:** Conditional section. First extraction that exercises the "section may not render" path. Includes the SC2 subjective verification gate.

**Requirements:** R1, R5, SC2

**Dependencies:** Unit 4.

**Files:**
- Create: `sections/scouting.py`
- Modify: `build.py` — remove `render_scouting_report` at `build.py:1459`; rewrite the call site at `build.py:1700`.

**Approach:**

`render_scouting_report(scout_data, next_games, tmap)` takes three parameters. All three become reads from `briefing.data` (`scout_data`, `next_games`, `tmap` are all keys at `build.py:370-386`). The conditional rendering ("only when a game is scheduled" — actually controlled by whether `scout_data` is non-empty per the current logic) stays inside the section file. The section file returns an empty string when there's nothing to render, matching current behavior.

If `render_scouting_report` reads `TEAM_NAME` (it does at `build.py:1508` for the SP card), replace with `briefing.team_name`.

**SC2 verification gate:** after this unit lands, JB should subjectively check — does opening `sections/scouting.py` and tweaking it feel meaningfully different from opening `build.py` and scrolling to line 1459? If yes, SC2 is verified. If no, the section files are not actually achieving the user-facing benefit and Unit 12's value proposition is in question.

**Test scenarios:**
- Happy path with game scheduled: snapshot test passes byte-identically (the chosen fixture day must include a scheduled game so `scout_data` is populated).
- Conditional path (nice-to-have, not required): if convenient, capture a second pair of fixtures for an off-day where `scout_data` is empty, and confirm the section returns empty output cleanly. If not convenient, defer this to manual verification.

**Verification:**
- Snapshot test passes for the standard fixture.
- JB confirms SC2 subjectively.

---

- [ ] **Unit 6: Extract `sections/pressbox.py`**

**Goal:** Two-input section (injuries + transactions).

**Requirements:** R1, R5

**Dependencies:** Unit 5.

**Files:**
- Create: `sections/pressbox.py`
- Modify: `build.py` — remove `render_pressbox` at `build.py:1583`; rewrite the call site at `build.py:1702`.

**Approach:**

Same pattern. `render_pressbox(injuries, transactions)` becomes reads from `briefing.data["injuries"]` and `briefing.data.get("transactions", [])`. The `.get()` fallback at `build.py:1702` is preserved inside the section file because some fixtures may lack a `transactions` key.

**Test scenarios:**
- Happy path: snapshot test passes.
- Missing-transactions edge case: confirm the existing `.get(..., [])` fallback is preserved.

**Verification:**
- Snapshot test passes.

---

- [ ] **Unit 7: Extract `sections/farm.py` — preserves `(html, minors_tag)` tuple return**

**Goal:** The largest single section. Also the first section with a tuple return value (this was missed in the original plan).

**Requirements:** R1, R5

**Dependencies:** Unit 6.

**Files:**
- Create: `sections/farm.py`
- Modify: `build.py` — remove `render_minors` at `build.py:1173` (~193 lines); rewrite the call site at `build.py:1690-1694` to preserve the tuple unpack.

**Approach:**

`render_minors(minors_data, prospects=None)` is the longest single render function in `build.py` (~193 lines). It returns either an HTML string OR a tuple `(html, minors_tag)` per the existing isinstance check at `build.py:1691`. The current call site at `build.py:1690-1694`:

```
minors_out = render_minors(data["minors"], data.get("prospects", {}))
if isinstance(minors_out, tuple):
    minors_html, minors_tag = minors_out
else:
    minors_html, minors_tag = minors_out, "No games"
```

`sections/farm.py` exports a single `render(briefing)` function that returns the same tuple-or-string shape. The call site in `page()` becomes:

```
minors_out = sections.farm.render(briefing)
if isinstance(minors_out, tuple):
    minors_html, minors_tag = minors_out
else:
    minors_html, minors_tag = minors_out, "No games"
```

`minors_tag` is consumed at `build.py:1822` inside the section wrapper f-string, so it must remain accessible to the envelope. The `briefing.affiliates` field is used here (currently reads the module global `AFFILIATES` at `build.py:274` inside `load_all`, and possibly inside `render_minors` itself — confirm during extraction).

**Test scenarios:**
- Happy path: snapshot test passes for both teams. Cubs has prospects data; Yankees may or may not.
- Tuple-return preservation: `minors_tag` value must be threaded correctly to the section header at line 1822. Snapshot diff would catch any mismatch.
- Prospects-empty check: confirm a team with no prospect data still renders the affiliate scores section.

**Verification:**
- Snapshot test passes for both teams.
- `wc -l build.py` is at least 190 lines smaller than after Unit 6.
- The `<span class="tag">{minors_tag}</span>` slot at `build.py:1822` still receives the same value as before extraction.

---

- [ ] **Unit 8: Extract `sections/headline.py` — multi-function, preserves `(html, summary_tag)` tuple return**

**Goal:** First multi-function section. Combines `render_line_score`, `render_three_stars`, `render_key_plays`, `render_cubs_leaders`, `render_next_games`, `render_hot_cold` (all the components of "The Team" section per CLAUDE.md). Also preserves the `summary_tag` tuple return from `render_line_score`.

**Requirements:** R1, R5

**Dependencies:** Unit 7.

**Files:**
- Create: `sections/headline.py`
- Modify: `build.py` — remove `render_line_score` (line ~407), `render_three_stars` (line 484), `render_key_plays` (line 553), `render_cubs_leaders` (line 1116), `render_next_games` (line 690), `render_hot_cold` (line 797). Rewrite the call sites at `build.py:1660-1679, 1697`.

**Approach:**

`sections/headline.py` exports one `render(briefing)` function. Internally it calls private helpers `_render_line_score`, `_render_three_stars`, `_render_key_plays`, `_render_cubs_leaders`, `_render_next_games`, `_render_hot_cold` and assembles their outputs in the order `page()` currently does. The scorecard embed `<details>` wrapper at `build.py:1671-1674` also moves into `sections/headline.py` since it logically belongs to the headline section.

`render_line_score` returns a tuple `(html, summary_tag)` per `build.py:1660-1664`. `summary_tag` is consumed at `build.py:1772` inside the section header. The new `sections.headline.render(briefing)` returns a tuple `(html, summary_tag)` so the caller can continue to extract it. The call site in `page()` becomes:

```
headline_out = sections.headline.render(briefing)
if isinstance(headline_out, tuple):
    headline_html, summary_tag = headline_out
else:
    headline_html, summary_tag = headline_out, "No game"
```

**Important: `fetch_pitcher_line` and `fetch_weather_for_venue` are NOT moved by this unit.** `render_next_games` calls both at `build.py:717, 718, 741`, but `fetch_pitcher_line` is also called from `load_all()` at `build.py:342`. Both helpers stay in `build.py` and are imported into `sections/headline.py` at function-call time:

```
def render(briefing):
    from build import fetch_pitcher_line, fetch_weather_for_venue
    # ... use them ...
```

The deferred-import pattern dodges the circular-import risk because `build.py` is fully loaded by the time `sections.headline.render` is called. Alternatively, both helpers can be passed via `briefing` as method references — implementer's choice.

**Test scenarios:**
- Happy path: snapshot test passes for both teams on a day with a completed game.
- Edge case: snapshot test passes on the chosen fixture date (which should include a completed Cubs game and a completed Yankees game — verify when capturing fixtures).
- Tuple-return preservation: confirm `summary_tag` still flows correctly into the `<span class="tag">` slot at `build.py:1772`.
- Helper accessibility: confirm `sections/headline.py` can call `fetch_pitcher_line` without circular-import errors. Run `python3 build.py --team cubs --fixture ... --out-dir /tmp/test-8` end-to-end.

**Verification:**
- Snapshot test passes for both fixtures.
- Six render functions are gone from `build.py`.
- `fetch_pitcher_line` is still in `build.py` and still callable from `load_all()` (which still works because the snapshot test would catch a regression there).

---

- [ ] **Unit 9: Extract `sections/division.py`**

**Goal:** Combines `render_nlc_standings`, `render_nlc_rivals`, `render_all_divisions` into one section.

**Requirements:** R1, R5

**Dependencies:** Unit 8.

**Files:**
- Create: `sections/division.py`
- Modify: `build.py` — remove `render_nlc_standings` (line 574), `render_nlc_rivals` (line 979), `render_all_divisions` (line 891). Rewrite the call sites at `build.py:1675, 1681, 1684`.

**Approach:**

The "{Division}" section per CLAUDE.md combines division standings + rival results from yesterday. `render_all_divisions` (used at `build.py:1681` for the standings table inside "Around the League") is shared between two sections. Decision during extraction: leave `render_all_divisions` in `build.py` as a helper imported by both `sections/division.py` and `sections/around_league.py`, OR move it into `sections/division.py` and have `around_league.py` import it from there.

**Default rule (per the deepening review's landmine 1 mitigation):** when a render function is called from multiple sections, leave it in `build.py` and import it from `build` at function-call time inside both section files. This avoids creating shared modules between section files and keeps the dependency graph one-directional (sections → build.py).

`render_nlc_standings` reads `DIV_ID` (module global) at `build.py:577`. Replace with `briefing.div_id`.
`render_nlc_rivals` reads `CFG["rivals"]` and `TEAM_ID` at `build.py:980, 985, 986`. Replace with `briefing.config["rivals"]` and `briefing.team_id`.

**Test scenarios:**
- Happy path: snapshot test passes for both teams.
- Cross-section helper: confirm `render_all_divisions` is still accessible from both `division.py` and `around_league.py` after Unit 11 lands.

**Verification:**
- Snapshot test passes.

---

- [ ] **Unit 10: Extract `sections/slate.py`**

**Goal:** Combines `render_slate_today` (line 949) and `render_next_games` if not already moved by Unit 8. Note: `render_next_games` was likely moved into `sections/headline.py` by Unit 8 because it belongs to "The Team" section per CLAUDE.md (next 3 games is part of the team headline). If so, this unit only extracts `render_slate_today`.

**Requirements:** R1, R5

**Dependencies:** Unit 9.

**Files:**
- Create: `sections/slate.py`
- Modify: `build.py` — remove `render_slate_today` (line 949). Rewrite the call site at `build.py:1683`.

**Approach:**

`render_slate_today(games_t, tmap)` is straightforward — two inputs from `briefing.data`. Move verbatim. `fetch_weather_for_venue` may move into `sections/slate.py` IF and ONLY IF the weather fetch is exclusively used by `render_slate_today` after Unit 8 has consolidated `render_next_games` into headline. Otherwise it stays in `build.py`. Verify with `grep -n "fetch_weather_for_venue" build.py` after Unit 8 lands.

**Note:** if Unit 8 did not move `render_next_games` into headline (because the implementer decided next-games belongs to slate), then this unit takes `render_next_games` as well. Default position: `render_next_games` belongs in `sections/headline.py` because CLAUDE.md groups "next 3 games" with "The {Team}" section, but the implementer's call.

**Test scenarios:**
- Happy path: snapshot test passes for both teams.

**Verification:**
- Snapshot test passes.

---

- [ ] **Unit 11: Extract `sections/around_league.py`**

**Goal:** The largest grab-bag section. Combines `render_league_news_from_items` (line 1101), `render_scoreboard_yest` (line 870), `render_leaders` (line 918), `detect_league_news` (line 1007), `generate_lede` (line 1366), `render_lede` (line 1453). May also include `render_all_divisions` if Unit 9 left it as a build-level helper.

**Requirements:** R1, R5

**Dependencies:** Unit 10.

**Files:**
- Create: `sections/around_league.py`
- Modify: `build.py` — remove the listed render functions; rewrite the call sites at `build.py:1680, 1682, 1685-1687, 1706-1707`.

**Approach:**

This is the most complex extraction. The editorial lede pipeline (`generate_lede` at `build.py:1366`, `render_lede` at `build.py:1453`) calls Ollama and falls back to Anthropic per CLAUDE.md, with caching to `data/lede-{slug}-YYYY-MM-DD.txt`. All of this moves into `sections/around_league.py`.

`generate_lede` reads `_team_slug` (module global) at `build.py:1368` for the cache key. After moving, the section file uses `briefing.config["slug"]` instead.
`generate_lede` also reads `TEAM_NAME`, `DIV_NAME`, `CFG['branding']['lede_tone']` at lines 1382, 1388, 1391 — replace with `briefing.team_name`, `briefing.div_name`, `briefing.config['branding']['lede_tone']`.

The frozen-lede mechanism from Unit 1 still works because it relies on the cache file existing at the path computed inside `generate_lede`. After moving, the path computation uses `briefing.config["slug"]` instead of `_team_slug`, but the value is the same string ("cubs" or "yankees"), so the cache lookup still hits the committed fixture file.

**Pre-approved split:** if this unit's PR feels too large, split into:
- Unit 11a: extract `render_league_news_from_items`, `render_scoreboard_yest`, `render_leaders`, `detect_league_news` (the "news + scoreboard + leaders" subset)
- Unit 11b: extract `generate_lede`, `render_lede` (the editorial lede pipeline subset)

The split is mechanical, not semantic. Either ordering works.

**Test scenarios:**
- Happy path: snapshot test passes for both teams using the frozen lede.
- Lede cache lookup: confirm the moved `generate_lede` still hits `data/lede-cubs-2026-04-05.txt` and skips Ollama.
- Multi-function consistency: confirm all render functions that moved produce the same combined HTML as before.

**Verification:**
- Snapshot test passes for both fixtures.
- `wc -l build.py` is now near or under 700 lines (Unit 12 will trim further).

---

- [ ] **Unit 12: Replace hardcoded section numbering with dynamic numbering**

**Goal:** Kill the hardcoded section numbering bug class. **NOTE: this is a SCOPED-DOWN version of the original Unit 12, addressing the over-engineering reviewer's concern that a full registry is too ambitious for a one-person project.** A future unit may add a fuller section registry; this unit only fixes the specific fragility called out in SC5.

**Requirements:** R6, SC1, SC5, SC6

**Dependencies:** Units 3-11 (all sections must be extracted first).

**Files:**
- Modify: `build.py` — replace the hardcoded numbering inside `page()` at `build.py:1768-1877` with a small helper that computes section numbers from a list of `(section_id, html_value)` pairs at runtime. The page envelope f-string still has 9 hardcoded `<section>` blocks, but the `<span class="num">{NN}</span>` inside each is computed from the helper instead of the hardcoded `"03" if scout_html else "02"` pattern.

**Approach:**

Inside `page(briefing)`, after all section HTMLs are computed, build a list:
```
visible_sections = [
    ("team", headline_html),         # always visible
    ("scout", scout_html),           # visible only if non-empty
    ("pulse", stretch_html),
    ("pressbox", pressbox_html),
    ("farm", minors_html),
    ("today", slate_html),
    ("div", division_html),
    ("league", around_league_html),
    ("history", history_html),
]
section_nums = {}
n = 1
for sid, html in visible_sections:
    if html:
        section_nums[sid] = f"{n:02d}"
        n += 1
```

Then in the f-string envelope, replace `<span class="num">01</span>` with `<span class="num">{section_nums.get("team", "")}</span>`, replace `"03" if scout_html else "02"` with `{section_nums.get("pulse", "")}`, and so on. The TOC at `build.py:1750-1761` similarly iterates `visible_sections` to build its `<li>` entries dynamically.

This is structurally minimal: it does NOT push section wrappers into section files, it does NOT create a `SECTIONS` registry data structure, it does NOT change the f-string shape beyond replacing the hardcoded numbers with dict lookups. It addresses SC5 (hardcoded numbering bug class) without the full ceremony of the original Unit 12 design.

**A future Unit 13 (NOT included in this plan)** could push wrappers into section files and create a true registry. That work is intentionally deferred until JB has a concrete need (e.g., adding a 10th section).

After this unit, `wc -l build.py` should be under 600 lines (SC1).

**Test scenarios:**
- Happy path with scouting visible: snapshot test passes byte-identically (numbers come out as 01, 02, 03, ..., 09).
- Happy path with scouting hidden: snapshot test passes byte-identically using a fixture without scout data (numbers come out as 01, 02, ..., 08, with "scout" missing from the dict).
- Section ordering: rendered HTML has sections in the same order as before.
- Number accuracy: when scouting is hidden, "pulse" gets "02" not "03"; when scouting is visible, "pulse" gets "03".

**Verification:**
- Snapshot test passes for both fixtures (with-scout and without-scout).
- `wc -l build.py` is under 600 lines (SC1 verified).
- `grep -c "^def render_" build.py` returns 0 (all render functions have moved). Note: helper functions like `fetch_pitcher_line`, `fetch_weather_for_venue`, `_ordinal`, `fmt_time_ct`, `fmt_date`, `abbr`, `team_name` may remain — they are not section renders.
- `grep -n '"03" if' build.py` returns no matches (the conditional numbering is gone).
- JB can describe the structure in one sentence (SC6 verified subjectively).

## System-Wide Impact

- **Interaction graph:** The cron-driven daily build (a shell loop outside this repo, plus `evening.py`) calls `python3 build.py --team <slug>` (morning loop) or `python3 build.py` with no team flag (`evening.py:84`, defaults to Cubs). Neither knows anything about `build.py`'s internals — they only depend on the CLI interface and the output file location (`<slug>/index.html`). Both are preserved by every unit. **The new flags (`--fixture`, `--out-dir`, `--capture-fixture`) are additive and inert when not passed. Verification with JB before merging Unit 1 is required to confirm cron does not pass these flag names.**
- **Error propagation:** Section render errors today crash `page()` and abort the build. After the refactor, the same behavior is preserved — errors propagate up from `sections.<name>.render(briefing)` exactly as they did from `render_*()`. This is intentional; the cron's failure mode (entire team build fails) is unchanged.
- **State lifecycle risks:** The build is single-pass and stateless within a process. The lede cache (`data/lede-<slug>-YYYY-MM-DD.txt`) is the only persistent state and its writer (in `generate_lede` at `build.py:1366`) moves with the around_league extraction in Unit 11 — its file path and format are unchanged. Critically, the snapshot test depends on this cache existing for the fixture date (`2026-04-05`). Those committed cache files are added in Unit 1 and must not be deleted by any later unit.
- **API surface parity:** `build.py`'s CLI (`--team <slug>`, `--landing`, plus the new test flags `--fixture`, `--out-dir`, `--capture-fixture`) is the public surface. The new flags are additive only — no existing flag changes behavior.
- **Integration coverage:** The snapshot test (Unit 1) is the only integration test introduced. It exercises the full build path (`load_data_from_fixture` → `TeamBriefing` construction → `page` → all 9 sections → assembled HTML → file write) for two teams, which is sufficient to catch cross-section regressions during migration. Section-level unit tests are deliberately deferred per the brainstorm scope boundaries.
- **Unchanged invariants:**
  - `build.py --team <slug>` continues to read `teams/<slug>.json` and write `<slug>/index.html`.
  - `build.py` (with no flags) defaults to Cubs and behaves exactly as today, preserving `evening.py` compatibility.
  - `deploy.py` continues to find output in `<slug>/` directories.
  - `evening.py` continues to call `build.py` the same way.
  - The published HTML output is byte-identical to pre-refactor output (enforced by snapshot test).
  - `data/YYYY-MM-DD.json` daily ledger format is unchanged (`save_data_ledger()` at `build.py:1933` is not touched).
  - `_team_slug` module global at `build.py:34` continues to be set by argv parse at import time.
  - No new pip dependencies are introduced (CLAUDE.md constraint preserved).
  - `fetch_pitcher_line` continues to be callable from `load_all()` at `build.py:342`.

## Risks & Dependencies

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Snapshot test fixture goes stale (MLB API schema changes) | Medium | Medium | Re-capture fixtures with `--capture-fixture` whenever the schema legitimately changes; commit the new fixture in the same PR as the schema-handling code change. The fixture is intentionally a snapshot of the dict, not a live API recording, so schema changes are easy to handle. The test does not catch live-API drift on its own — it is not a production canary. **Mitigation: add a separate manual smoke step before merging any PR — `python3 build.py --team cubs` against the live API — to confirm the new code path also works against real data.** |
| New `--fixture` / `--out-dir` / `--capture-fixture` flag names collide with the morning cron's argv | Low | High | **Verify with JB before merging Unit 1.** Ask him to grep his crontab/systemd timer/shell wrapper for `build.py` invocations and report any flags being passed. If any collision exists, rename the new flags before Unit 1 ships. |
| Cron pushes a build mid-extraction-PR review and `main` no longer matches the local branch | Medium | Low | Each extraction PR is small and can be rebased quickly. The strangler-fig sequence is designed for this — the snapshot test catches any regression introduced by the rebase. |
| Partial migration: JB stops at Unit 6 or 7 and `build.py` is left in a hybrid state forever | Medium | Low | Accepted outcome. Each unit leaves the codebase strictly better than the previous state. The hybrid-state risk is "the structure isn't fully consistent" not "anything is broken." |
| Shared helpers (`fmt_time_ct`, `_ordinal`, etc.) get duplicated across section files | Low | Medium | Default rule: shared helpers stay in `build.py`. Section files import them at function-call time inside the render function (deferred import dodges circular import). Unit 12 reviews and consolidates if duplication accumulated. |
| The `around_league.py` extraction (Unit 11) is too large to ship as one PR | Medium | Low | Pre-approved exit hatch: split Unit 11 into 11a (render extractions) and 11b (lede pipeline). Either ordering works. |
| `render_cubs_leaders` is misclassified between sections | Low | Low | Per CLAUDE.md, "Cubs Leaders" belongs to "The {Team}" section (headline). It was called at `build.py:1697` and inserted at `build.py:1780-1781` inside the team section. Move into `sections/headline.py` during Unit 8. |
| Cron daily build fails on a day when a refactor PR is mid-review | Low | High | The snapshot test enforces zero diff before any PR can merge. The probability of a successfully-snapshot-tested PR breaking the cron is near zero. If it ever happens, revert the offending PR — every PR is small enough to bisect quickly. |
| Unit 2-12 chain revert ordering is misunderstood and someone reverts Unit 2 while later units still depend on it | Low | High | **Explicitly documented: Units 2-12 form a chain. Reverts must happen in reverse order (revert 12, then 11, ..., then 2). Unit 1 alone is independently revertible.** This is in the Risks section because the original plan claimed each PR was "independently mergeable" which was false past Unit 2. |
| `build_briefing(team_slug)` returns wrong-team data because module globals were set from a different `--team` argv | Low | Medium | `build_briefing` is only called from `__main__` (which has the correct `_team_slug`) and from the snapshot test subprocess (which always passes `--team` matching the fixture). If a future unit needs to call `build_briefing` from a different context, that unit must first refactor module-level state (out of scope for this plan). Documented in Decision 7. |
| Fixture lede cache files get accidentally deleted by a "cleanup data/" PR | Low | High | The `data/` directory contains both daily ledgers (auto-rotating) and the committed fixture lede caches. A cleanup script that nukes old `data/lede-*.txt` files would silently break the snapshot test. **Mitigation: add a comment to the top of each fixture lede cache file: `# DO NOT DELETE: snapshot test fixture for tests/snapshot_test.py`. Add a defensive note to `tests/README.md`.** |
| Bootstrap blessing of the initial fixture has a typo or capture-time bug, and the "expected" HTML is wrong from day one | Medium | Medium | The bootstrap is manual and requires JB or implementer to eyeball the first rendered output. **Mitigation: open the blessed `expected.html` in a browser before committing it. If it looks right visually, it's the source of truth. After commit, the test enforces "stay this way."** |

## Documentation / Operational Notes

- Add `tests/README.md` in Unit 1 documenting how to run the snapshot test, how to re-bless fixtures after intentional changes, and the warning that `data/lede-cubs-2026-04-05.txt` and `data/lede-yankees-2026-04-05.txt` are committed test fixtures and must not be deleted.
- Update CLAUDE.md after Unit 12 lands to reflect the new structure (sections/ package, TeamBriefing dataclass). The "Key files" table needs a new row for `sections/`. The "Important patterns" section gets a new bullet about the section file convention.
- **Update `docs/brainstorms/2026-04-10-sectioned-build-requirements.md` R2** to reflect the amendment: TeamBriefing holds raw config, raw data, and per-team config-alias constants. This is a one-line edit to the requirements doc. Done as part of Unit 2's PR.
- No changes to deployment, monitoring, or rollout procedures. The cron continues to run on the same schedule.
- No new environment variables or secrets.
- The brainstorm requirements doc should be marked `status: in-progress` when Unit 1 lands and `status: complete` when Unit 12 lands.

## Open Questions

### Resolved During Planning

- **What library handles the snapshot test and HTML diff?** Stdlib `difflib.unified_diff`. Forced by CLAUDE.md zero-dependency constraint. (Decision 1.)
- **What does "frozen API inputs" look like?** Committed JSON fixtures captured via the existing `save_data_ledger` serialization format, with a one-time `--capture-fixture` flag and explicit ISO date rehydration on load. (Decisions 3 and 4.)
- **How is lede non-determinism handled?** Commit the fixture-date lede cache files (`data/lede-cubs-2026-04-05.txt`, `data/lede-yankees-2026-04-05.txt`) as test fixtures. The existing cache lookup at `build.py:1368-1372` bypasses Ollama and Anthropic when the file is present. (Decision 5.)
- **How does the snapshot test deal with `build.py` writing to a file instead of stdout?** New `--out-dir <path>` flag overrides the destination directory; the test reads the resulting file. (Decision 2.)
- **How do section files access per-team constants without circular imports?** TeamBriefing exposes `team_id`, `team_name`, `div_id`, `div_name`, `affiliates` as direct config-alias fields. Section files read them via `briefing.team_name` etc. R2 is amended to permit this. (Decision 7.)
- **What does the section visibility check use, since `today_scheduled` does not exist?** Post-render truthiness of the rendered HTML, matching the existing `if scout_html` pattern at `build.py:1796`. The Unit 12 dynamic numbering helper iterates `(section_id, html_value)` pairs and skips entries with falsy HTML. (Decision 14.)
- **Where does `fetch_pitcher_line` live after the refactor?** In `build.py`. It is called from `load_all()` at `build.py:342`, so it cannot move into a section file. `fetch_weather_for_venue` may move into `sections/slate.py` if the implementer confirms it has no other callers. (Decision 13.)
- **Are the units actually "independently mergeable"?** Unit 1 is. Units 2-12 form a chain that must be reverted in reverse order. The original plan's claim was wrong. (Decision 12.)
- **Why not refactor module-level globals into a `main()` function as Unit 0?** Subprocess-based testing dodges the import-time global state. Refactoring `main()` would be a large, risky change for marginal benefit. Out of scope for this plan; may be a future unit. (Decision 1.)
- **How is `(html, summary_tag)` and `(html, minors_tag)` handled?** Both Unit 7 (farm) and Unit 8 (headline) preserve the tuple return shape. The call sites in `page()` continue to use `isinstance(out, tuple)` to unpack. The original plan missed the `minors_tag` case — corrected. (Decisions in Unit 7 and Unit 8 Approach sections.)

### Deferred to Implementation

- **Where do shared helpers (`fmt_time_ct`, `_ordinal`, `fmt_date`, `abbr`, `team_name`) live during the migration?** Default to staying in `build.py`. Decided per-extraction during Units 9-11 based on actual usage patterns.
- **Does Unit 11 need to be split into 11a + 11b?** Decided during Unit 11 review based on PR size. Split is pre-approved if needed.
- **Does `render_next_games` belong in `sections/headline.py` (Unit 8) or `sections/slate.py` (Unit 10)?** CLAUDE.md groups it with "The Team" section, so default is Unit 8. Implementer's call.
- **Does `fetch_weather_for_venue` move into `sections/slate.py` or stay in `build.py`?** Decided during Unit 10 by grepping for callsites. Default is stay in `build.py` if there's any doubt.

## High-Level Technical Design (revised) — Unit 12 visibility numbering helper

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

```
# inside page(briefing), after all sections are rendered:

candidates = [
    ("team", headline_html),
    ("scout", scout_html),
    ("pulse", stretch_html),
    ("pressbox", pressbox_html),
    ("farm", minors_html),
    ("today", slate_html),
    ("div", division_html),
    ("league", around_league_html),
    ("history", history_html),
]

nums = {}
n = 1
for sid, html in candidates:
    if html:
        nums[sid] = f"{n:02d}"
        n += 1

# Then in the envelope f-string:
#   <span class="num">{nums.get("team", "")}</span>          # was hardcoded "01"
#   <span class="num">{nums.get("scout", "")}</span>         # was hardcoded "02" inside conditional
#   <span class="num">{nums.get("pulse", "")}</span>         # was '"03" if scout_html else "02"'
#   ... etc.
#
# TOC <li> entries similarly iterate `[(sid, html, label) for ...]` to build dynamically.
```

This is the minimum change that addresses SC5 without rewriting the envelope's f-string shape. A more aggressive registry-based design is deferred to a hypothetical future Unit 13.

## Sources & References

- **Origin document:** [docs/brainstorms/2026-04-10-sectioned-build-requirements.md](../brainstorms/2026-04-10-sectioned-build-requirements.md)
- **Upstream ideation:** [docs/ideation/2026-04-10-repo-structure-ideation.md](../ideation/2026-04-10-repo-structure-ideation.md) (survivor #1)
- **Relevant institutional knowledge:** [docs/solutions/best-practices/config-driven-multi-tenant-static-site-2026-04-08.md](../solutions/best-practices/config-driven-multi-tenant-static-site-2026-04-08.md)
- **Project conventions:** `CLAUDE.md` at repo root (Python stdlib-only, multi-team config pattern, 9-section page structure)
- **Related code:**
  - `build.py:24` `load_team_config`
  - `build.py:33-51` module-global parse and CFG/TEAM_ID/CSS/OUT computation
  - `build.py:83-386` `load_all` (uses `TEAM_ID`, `AFFILIATES`, `DIV_ID` from globals; calls `fetch_pitcher_line` at line 342)
  - `build.py:626` `fetch_pitcher_line` (stays in build.py — load_all dependency)
  - `build.py:645` `fetch_weather_for_venue` (may move with Unit 10)
  - `build.py:1366-1451` `generate_lede` (cache lookup at lines 1368-1372 enables fixture determinism)
  - `build.py:1647` `page(data)` orchestrator
  - `build.py:1660-1664` tuple unpack for `render_line_score` (Unit 8)
  - `build.py:1690-1694` tuple unpack for `render_minors` (Unit 7 — caught in deepening review)
  - `build.py:1712-1923` page envelope f-string with hardcoded section wrappers and conditional numbering
  - `build.py:1933` `save_data_ledger` (precedent for stdlib JSON snapshot pattern; reused as fixture format)
  - `build.py:1961-1972` `__main__` block (writes to file via `OUT.write_text`, not stdout)
  - `evening.py:84` (Cubs-only rebuild, no `--team` flag)
  - `deploy.py:67-72` (iterates teams to push but does not call build.py — the morning build loop is outside this repo)
- **Confidence on overall plan:** HIGH for Units 1-7, MEDIUM for Units 8-11 (multi-function sections still have some discovered-during-extraction questions), HIGH for Unit 12 (now scoped down from the original aggressive registry design).

## Revision History from Independent Review

This plan was strengthened by an adversarial review pass on 2026-04-10. Three independent reviewers were dispatched in parallel with no shared context: an operational risk reviewer, an over-engineering reviewer, and an execution-readiness reviewer. Findings:

**Operational risk reviewer (sharpest finding first):**
1. Original plan assumed `build.py` writes to stdout. **It does not** — `build.py:1971` does `OUT.write_text(html)`. The original snapshot test would have either silently passed (diffing status messages) or clobbered the live `cubs/index.html` and risked pushing a fixture build to production. **Fixed:** Decision 2 — added `--out-dir <path>` flag, snapshot test reads the file from a tempdir.
2. `generate_lede` makes live LLM calls at render time. The original plan only addressed lede determinism in Unit 11. **Fixed:** Decision 5 — commit fixture-date lede cache files in Unit 1, no code changes needed because `generate_lede` already has a cache-first lookup at `build.py:1368-1372`.
3. Module-level CLI parse and global state at `build.py:34-51` make `from build import TeamBriefing` trigger import-time work. **Mitigated:** all tests are subprocess-based, not import-based, dodging the issue. Module-level refactor is explicitly out of scope.
4. Original "every PR is independently mergeable" claim was wrong. **Fixed:** Decision 12 — Units 2-12 are a chain that must revert in reverse order. Documented in risks table.
5. `evening.py` rebuilds Cubs only with no `--team` flag — a fact the original plan missed. **Fixed:** noted in the Problem Frame and System-Wide Impact sections.

**Over-engineering reviewer:**
1. Argued for deleting Unit 1 entirely and using `cp + diff`. **Partially accepted:** the snapshot harness is retained because lede non-determinism and across-PR safety still need automation, but Unit 12 is scoped down from a full registry to a minimal numbering helper to address the broader over-engineering concern.
2. Argued the section registry was over-engineering. **Accepted:** Unit 12 is now "compute section numbering dynamically" instead of a full `(name, render_fn, visible_when)` registry. A future Unit 13 may add the full registry if needed.
3. Argued one test team is enough. **Rejected** — Yankees catches multi-tenant rivalry/division logic that Cubs alone (the default) wouldn't exercise.
4. Argued `TeamBriefing` is just dict-wrapping. **Partially accepted** — TeamBriefing is retained but the R2 amendment exposes per-team constants directly so section files don't have to dig through `briefing.config["..."]` for every alias.

**Execution-readiness reviewer (landmines that would halt an implementer):**
1. **Globals create circular import trap.** `CSS, CFG, TEAM_ID, TEAM_NAME, DIV_NAME` are module-level. **Fixed:** Decision 7 (TeamBriefing exposes constants as fields) + Decision 9 (section files import only stdlib + TeamBriefing, no module globals from build.py).
2. **Fixture date rehydration missing.** JSON serialization converts `date` to ISO string; reader must rehydrate. **Fixed:** Decision 4 — explicit rehydration documented in Unit 1's `load_data_from_fixture` helper.
3. **Missed the `(html, minors_tag)` tuple return from `render_minors`.** Original Unit 7 had no mention. **Fixed:** Unit 7 now explicitly preserves the tuple shape, with the call site update spelled out.
4. **Page envelope is not cleanly separable from sections.** Section wrappers and hardcoded numbering are inside the page f-string. **Fixed:** Unit 12 redesigned to NOT touch the wrappers — it only replaces the hardcoded numbers with dict lookups computed by a helper. Section wrappers stay in the envelope. This is the minimum surgical change.
5. **`today_scheduled` data key does not exist.** The original Unit 12 invented it. **Fixed:** Decision 14 + Unit 12 redesign — visibility uses post-render HTML truthiness, matching the existing `if scout_html` pattern.
6. **`fetch_pitcher_line` is also called from `load_all` at `build.py:342`** — cannot move to slate.py. **Fixed:** Decision 13 — `fetch_pitcher_line` stays in `build.py`. Unit 10 explicitly notes this. Unit 8 uses deferred import (`from build import fetch_pitcher_line` inside the function body) when headline.py needs it.
7. **`__main__` block branching for `--fixture` is more than a one-line change.** Original plan understated it. **Fixed:** Unit 3 spells out the full branching logic for the fixture path.
8. **CSS injection unspecified.** `CSS` is module-level and only used in the envelope. **Fixed:** Decision 8 — CSS stays in `build.py`, not on TeamBriefing, because section files don't need it.

This deepening pass took the plan from "would halt an implementer at Unit 1" to "should be safe to execute as-is."
