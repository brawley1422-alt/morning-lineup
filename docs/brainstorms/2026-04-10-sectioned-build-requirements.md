---
date: 2026-04-10
topic: sectioned-build-py
source: docs/ideation/2026-04-10-repo-structure-ideation.md (survivor #1)
status: ready-for-planning
---

# Requirements: Sectioned `build.py` with `TeamBriefing` Object

## Context

`build.py` is a 1972-line file holding 27 `render_*()` functions, the `load_all()` data fetcher, top-level helpers, and a `page()` orchestrator at line 1647. Every render function reaches into globals, parses raw API data inline, and assembles HTML. This makes section-level tweaks slow and risky for a vibe-coder workflow because there is no isolation between sections, and a change inside one render can subtly affect another via shared global state or shared parsing patterns.

The Morning Lineup project is shipped, live, and pushes 30+ commits per day from a cron-driven daily build. JB is at the "tweaking sections" stage of product maturity — making frequent small adjustments to one section at a time — and the current monolithic file structure punishes that workflow.

This requirements document captures **WHAT** the refactor must accomplish. It does not specify implementation details that belong in `/ce-plan` (e.g., exact dataclass field names, specific extraction order beyond the proof-of-concept section, snapshot test framework choice).

## Requirements

### R1. Section files match the user's mental model — Confidence: HIGH
Each visible section on the rendered page becomes one file under a new `sections/` package — nine files total, one per section JB sees:
- `sections/headline.py` (line score, three stars, key plays — was `render_line_score`, `render_three_stars`, `render_key_plays`)
- `sections/stretch.py` (was `render_stretch`)
- `sections/pressbox.py` (injuries + transactions — was `render_pressbox`)
- `sections/farm.py` (minor leagues + prospects — was `render_minors`)
- `sections/slate.py` (was `render_slate_today`, `render_next_games`)
- `sections/division.py` (NL Central rivals + standings — was `render_nlc_standings`, `render_nlc_rivals`, `render_all_divisions`)
- `sections/around_league.py` (news + scoreboard + leaders + hot/cold — was `render_league_news_from_items`, `render_scoreboard_yest`, `render_leaders`, `render_hot_cold`)
- `sections/history.py` (was `render_history`)
- `sections/scouting.py` (conditional pre-game scouting report — was `render_scouting_report`)

Each file exports one `render(briefing) -> str` entry point. Internal helper functions may exist within the file but are not exported. Section files are the only place section-specific logic lives after the refactor completes.

### R2. `TeamBriefing` dataclass is the single argument to every section — Confidence: HIGH
A new `TeamBriefing` dataclass is constructed once per team per build by an extracted `build_briefing(team_slug)` function. It holds **only**:
- `config: dict` — the per-team JSON config (currently the return of `load_team_config`)
- `data: dict` — the raw API/data dictionary (currently the return of `load_all`)

It does **not** hold computed convenience fields, typed sub-objects, or pre-parsed structures. Any parsing, derivation, or computation that section render functions need stays inside those section files. This minimizes the surface area of the refactor and ensures byte-identical output during the strangler-fig migration.

### R3. Daily auto-build script must keep working uninterrupted — Confidence: HIGH
The cron-driven daily build (`build.py` invoked with `--team <slug>` plus `deploy.py` and `evening.py`) must continue running successfully on every day of the migration. No PR in this refactor may leave `main` in a state where the daily cron job fails. `build.py` retains its current CLI interface and is still the entrypoint cron calls.

### R4. Strangler-fig migration with a prep step — Confidence: HIGH
The refactor lands as a sequence of small, independently shippable PRs:

1. **Prep PR — golden snapshot harness.** Implement survivor #3 from the ideation doc: a fixture-based snapshot test that builds Cubs (and at least one other team — recommended Yankees, for visual contrast) against frozen API inputs and diffs the rendered HTML against a committed reference. Frozen inputs are committed alongside the fixture so the test is deterministic across runs. Provides the safety net that makes every subsequent PR verifiable.
2. **Prep PR — `TeamBriefing` dataclass and `build_briefing()` constructor.** Add the dataclass and the constructor function. No existing `render_*` functions are modified yet. The dataclass exists, is importable, and is unit-testable, but is not yet used in the production render path.
3. **Proof-of-concept PR — extract `sections/history.py`.** Move `render_history` into `sections/history.py` exporting `render(briefing)`. Update `page()` in `build.py` to call the new module. Snapshot test must pass with byte-identical output. This is the smallest, lowest-dependency section in `build.py` (line 1624, reads only from `teams/<slug>/history.json`) and proves the pattern works end-to-end.
4. **Subsequent PRs — extract one section per PR**, in order of increasing complexity. Each PR follows the same shape: create `sections/<name>.py`, move the relevant `render_*` functions into it, update `page()` to call the new module, verify snapshot test passes. The cron daily build keeps running between every PR.
5. **Finalization PR — section registry and `page()` simplification.** Once all 9 sections are extracted, replace the hand-written `page()` body with a section list that the orchestrator iterates. This kills the hardcoded section numbering and the "fragile when sections hide" bug class.

The graceful exit point: if JB decides to stop partway through, every shipped PR is independently valuable and the daily build keeps working.

### R5. Each extraction PR must produce byte-identical output — Confidence: HIGH
Every PR after the prep PRs must result in zero diff against the golden snapshot for the test team(s). If a section extraction would change output even cosmetically, the change must be split — extract first (zero diff), then make the cosmetic change as a separate follow-up PR. This is the only mechanism preventing subtle behavior shifts from accumulating across the migration.

### R6. The refactor leaves `build.py` smaller and shaped as an orchestrator — Confidence: MEDIUM
After the finalization PR, `build.py` should contain:
- the CLI/entrypoint plumbing
- `load_team_config`, `load_all` (or whatever `build_briefing` calls into)
- `build_briefing(team_slug) -> TeamBriefing`
- the section registry / `page()` orchestrator
- file-writing logic
- top-level helpers that don't belong inside any one section (`fmt_time_ct`, `_ordinal`, etc.)

Confidence is MEDIUM here because the exact line count and the placement of helpers will be discovered during the extraction PRs, not designed up front. The principle is firm; the specific landing spot for each helper is not.

## Success Criteria

### SC1. `build.py` is meaningfully smaller — Confidence: HIGH
After all 9 sections are extracted, `build.py` is under 600 lines (down from 1972). The 1372+ lines that moved out are distributed across the 9 `sections/<name>.py` files plus any new infrastructure in `build.py` itself.

### SC2. Section tweaks become "open one file" instead of "scroll a wall" — Confidence: HIGH
Tweaking the standings display means opening `sections/division.py` and editing one function. No grep-and-pray across a 1972-line file. Verified subjectively by JB after the third extraction PR: he picks a section to tweak and confirms the workflow feels different.

### SC3. The daily auto-build runs successfully on every day of the migration — Confidence: HIGH
Zero failed cron runs traceable to refactor PRs. Verified by checking that `archive/<team>/YYYY-MM-DD.html` exists for every team every day from the start of the refactor through finalization.

### SC4. Golden snapshot test catches at least one regression during the migration — Confidence: MEDIUM
Confidence is MEDIUM because this might not happen — the migration could go cleanly. But if it does, the snapshot test is doing its job. If the migration completes with zero snapshot failures, that is also a valid outcome and the test still earns its keep as a permanent safety net.

### SC5. The section registry kills the hardcoded numbering bug class — Confidence: HIGH
After the finalization PR, conditionally hidden sections (like the pre-game scouting report) no longer require manual renumbering elsewhere in the code. Adding a new section is a one-line addition to the registry.

### SC6. JB can describe the new structure in one sentence — Confidence: HIGH
After the refactor, JB can say something like "each section is a file in `sections/`, and they all take a `TeamBriefing` object." If he can't, the abstraction is wrong and we should reconsider.

## Scope Boundaries

### In Scope
- New `sections/` package with 9 files matching visible page sections
- `TeamBriefing` dataclass holding only raw config and raw data
- `build_briefing()` constructor function in `build.py`
- Golden snapshot test harness for at least 2 teams (Cubs + 1 other)
- Section registry / orchestrator simplification in finalization PR
- Strangler-fig migration sequence as described in R4

### Out of Scope (Confidence: HIGH)
- **Jinja2 templates per section.** A separate, larger transformation. May be brainstormed later. Render functions stay in Python for now.
- **Symlinking scorecard / shared assets.** This is ideation survivor #2 and a separate effort.
- **Moving team output dirs under `site/` or `dist/`.** Touches deploy.py and GitHub Pages config. Out of scope.
- **Single-page app / client-side rendering.** Rejected in ideation; violates the "auto-build must keep working" constraint.
- **JSON schema validator for team configs.** Rejected in ideation as engineer-brain idea.
- **Briefing cache by `(team, date, hash)`.** Rejected as premature optimization.
- **`make` task runner.** Rejected as DX cleanup outside the structural concern.
- **Refactoring the helper functions** (`fmt_time_ct`, `_ordinal`, etc.) into their own module. They stay in `build.py` unless a specific section extraction makes a clear case otherwise.
- **Pre-computing convenience fields on `TeamBriefing`.** Explicitly rejected in R2 to keep the refactor minimal-risk. May be revisited as a follow-up after the migration finishes.
- **Adding unit tests for individual section render functions.** The golden snapshot test is the only test required by this work. Section-level unit tests are a follow-up if the snapshot proves insufficient.
- **Changing what data `load_all()` fetches.** The refactor wraps existing data; it does not change what data gets fetched or how.

### Explicitly Deferred (Confidence: MEDIUM)
- **Per-team section visibility flags in config.** The section registry in the finalization PR makes this trivial to add later, but adding it now would expand scope. Defer until JB has a real use case (e.g., "the Athletics page should hide the prospects section because their farm system is empty").
- **Automatic cleanup of obsolete `archive/` snapshots.** Unrelated cleanup, not part of this work.

## Open Questions for Planning

These are not product decisions; they belong in `/ce-plan`:

1. What library handles the snapshot test and HTML diff? (`difflib` from stdlib is the obvious low-cost option; `pytest` adds discoverability. To be decided in planning.)
2. What does "frozen API inputs" look like in practice — committed JSON fixtures, a recorded HTTP cassette, or something simpler? (Implementation choice.)
3. Where do shared helpers live during the migration — stay in `build.py`, move to `lib/helpers.py`, or move into the section files that use them? (Discovered during extraction.)
4. How does the section registry actually work — list of `(name, render_fn)` tuples, dict, or class? (Implementation choice.)
5. Does the proof-of-concept extraction (history.py) get its own snapshot fixture or share Cubs's? (Implementation detail.)

## Session Log

- 2026-04-10: Brainstorm session. Three product decisions made: strangler-fig migration with prep step, raw-data-only `TeamBriefing`, one file per visible section (9 files). Sequenced ahead of golden snapshot harness as the prep PR.
