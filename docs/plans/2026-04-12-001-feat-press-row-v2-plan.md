---
title: "feat: Press Row 2.0 — integrated fictional beat-writer universe"
type: feat
status: active
date: 2026-04-12
origin: docs/brainstorms/2026-04-12-press-row-v2-brainstorm.md
---

# Press Row 2.0 — Implementation Plan

## Overview

Press Row 2.0 rebuilds the shelved prototype at `docs/future/pressrow.py` as a separate Python subpackage at `pressrow/` that generates a daily JSON artifact consumed by a thin renderer in `sections/pressrow.py`. The v1 prototype failed because a single monolithic LLM call hoped for banter; v2 treats banter as architecture — state, pre-computation, focused per-writer generation, and an editor rewrite pass.

The build is structured as 10 implementation units across 4 phases. Phase 0 is shared infrastructure. Phase 1 (Comedy Editor Pipeline + Writer Obsessions) is the minimum viable relaunch that fixes the "boring tweets" problem. Phases 2-4 compound character, texture, and rare moments on top.

**Total effort:** ~10-14 days of focused work. **Minimum viable relaunch:** Phases 0+1, ~4-5 days.

## Problem Frame

The brainstorm at `docs/brainstorms/2026-04-12-press-row-v2-brainstorm.md` found that the shelved prototype (`docs/future/pressrow.py`) has working structural pieces — avatars, handles, reply threads, quote tweets, caching — but produces boring, repetitive tweets that nobody would come back to read. The qwen3:8b local model, when asked in a single call to "generate 20 interconnected tweets with banter," averages every persona's voice into the same bland take.

The ideation pass (`docs/ideation/2026-04-12-press-row-pop-ideation.md`) identified 7 survivors across three frames (character/lore, format/hooks, LLM craft). The brainstorm then composed all 7 into a unified system where each feature reinforces the others: obsessions feed the Comedy Pipeline, Memory feeds the Beef Engine, etc.

This plan converts the brainstorm's specs into executable implementation units.

## Requirements Trace

Traced from the brainstorm's "7 Features" section and "Shared Infrastructure" section:

- **R1. Tweet quality must be measurably funnier than the shelved prototype.** From brainstorm Feature 1 — the 3-pass Comedy Editor Pipeline (angles → petty draft → editor rewrite) is the single biggest quality lever. Without R1, nothing else matters.
- **R2. Every writer must have hand-authored worldview beyond signature phrase.** From brainstorm Feature 2 — 2-3 load-bearing obsessions injected into every prompt as mandatory context.
- **R3. Writers must remember and reference their own past tweets and predictions.** From brainstorm Feature 3 — per-writer memory with prediction extraction, resolution checking, and callback injection.
- **R4. Interactions must be architected, not emergent.** From brainstorm Feature 4 — pre-generation DAG planning + persistent cross-team rivalries in `relationships.json`.
- **R5. Feed must contain serialized non-writer voices.** From brainstorm Feature 5 — recurring cast of ~20 fictional fans with per-character state advancing daily.
- **R6. Feed must contain daily-novelty newspaper formats.** From brainstorm Feature 6 — classifieds column generating 5/day (Help Wanted, Missed Connections, For Sale).
- **R7. Feed must have rare scheduled event moments.** From brainstorm Feature 7 — Breakdown Arc (7-day meltdown, ~2x/season) + Walk-Off Ghost (trigger-based cryptic persona).
- **R8. Press Row must run as a separate build pipeline feeding ML via JSON artifact.** From the user's architecture decision in the conversation — pressrow subpackage writes `data/pressrow-{date}.json`; ML's section reads it.
- **R9. ML must degrade gracefully if Press Row generation fails.** From the user's operational concern — Press Row failures must not block the daily briefing build.
- **R10. All Press Row state must persist across builds.** From brainstorm Shared Infrastructure I2 — per-writer state files, relationships file, cast state, event state all live in the repo and evolve day-to-day.

## Scope Boundaries

**In scope:**
- New subpackage `pressrow/` with its own build command
- New JSON artifact contract at `data/pressrow-{date}.json`
- Thin renderer at `sections/pressrow.py` (≤100 lines)
- CSS additions to `style.css` (the existing Press Row CSS block from the shelved prototype, refined)
- Integration points in `build.py` (import, section call, TOC entry, HTML block)
- State files under `pressrow/state/` and config files under `pressrow/config/`
- Authoring ~270 writer obsessions (as data, not code)
- Seeding ~10 initial feuds and ~15 initial recurring fans (as data)
- Hand-authored shadow personas (30, one per team)

**Non-goals for v2 launch:**
- UI for inspecting Press Row state (no Rivalries sidebar, no Predictions Tracker — state stays invisible in v2)
- Fan-to-fan interactions (Letters feature only does fan → writer replies in v2)
- Obsession drift over time (obsessions stay fixed in v2)
- Anniversary callbacks beyond the memory window (year-two feature)
- Auto-generated glossary of inside jokes (year-two feature)
- Inline editing of generated tweets through a UI (manual JSON editing only for v2)
- Theming Press Row differently per team (shared feed across all 30 pages in v2)
- Non-English support

**Explicitly deferred to later phases or future work:**
- Migration of the shelved prototype's cache data — v2 starts fresh
- Backfilling historical memory from v1 tweets — memory starts empty on v2 launch day

## Context & Research

### Relevant Code and Patterns

The brainstorm identifies specific existing patterns to mirror, and exploration earlier in this session verified each:

- **LLM generation with Ollama → Anthropic fallback:** `sections/columnists.py:142-191` defines `_try_ollama()` and `_try_anthropic()` using Python stdlib `urllib.request`. Every LLM call in `pressrow/llm.py` should mirror this exact pattern — same timeouts (Ollama 120s, Anthropic 30s for short calls, extend to 180s/60s for long calls), same error handling, same `<think>` tag stripping via `_strip_thinking()`.

- **Cache-first pattern:** `sections/columnists.py:53-70` shows the `_load_cache()` / `_save_cache()` pattern writing to `data/columnists-{slug}-{date}.json`. Press Row adopts the same pattern but writes to `pressrow/state/` and `data/pressrow-{date}.json`.

- **Section render contract:** Every `sections/*.py` exports a `render(briefing)` function that returns HTML (or `(html, badge)` tuples for badged sections). The thin renderer at `sections/pressrow.py` follows this contract. Its job is ~50 lines of "read the JSON artifact, build HTML, return."

- **Data access via briefing dataclass:** `build.py` defines `TeamBriefing` with fields `config`, `data`, `team_id`, `team_name`, etc. Sections read from `briefing.data["games_y"]` (yesterday's games) never from module globals. See `sections/around_league.py:332-335` for the canonical pattern.

- **Yesterday's games data shape:** `build.py:95-107` shows `load_all()` fetching `games_y` via MLB Stats API with hydration for `team,linescore,decisions,probablePitcher,venue`. Press Row's `_build_game_digest()` reads from this exact structure; reference `sections/around_league.py:35-55` for the canonical scoreboard iteration pattern.

- **Persona config schema:** `teams/cubs.json:59-81` shows the columnists array with `name`, `role`, `backstory`, `signature_phrase`, `voice_sample` fields. Press Row extends this schema with new `obsessions` and optional `shadow_personas` arrays on each team JSON.

- **Section integration points in `build.py`:** The shelved prototype successfully wired at `build.py:25` (import), `build.py:666` (render call), `build.py:670-680` (`_visible_sections` list), `build.py:740-752` (TOC), and `build.py:829-847` (HTML block between Around the League and History). V2 uses the same integration points; the shelved prototype in `docs/future/pressrow.py` and its README describe the exact patch locations.

- **The shelved prototype itself:** `docs/future/pressrow.py` contains ~450 lines of structural code that still has value: `_make_handle()`, `_make_initials()`, `_load_all_columnists()`, `_build_game_digest()`, `_normalize_timestamp()`, `_extract_json()`, `_render_tweet()`, `_render_quoted()`. V2's `pressrow/` subpackage should port and refactor these helpers — do not rewrite from scratch.

- **CSS aesthetic:** The shelved prototype's CSS block (saved in the plan file `~/.claude/plans/shimmering-wiggling-newell.md`) defines `.pressrow-feed`, `.pr-tweet`, `.pr-avatar`, `.pr-quoted`, `.pr-metrics`, reply connector, and home-team highlight styles. V2 reuses this CSS with minor additions for Letters and Classifieds render blocks. The CSS variable palette (`--ink`, `--paper`, `--gold`, `--team-primary`, `--team-accent`) is already established in `style.css:1-50` — Press Row uses these, does not invent new variables.

- **Deployment pipeline:** `deploy.py` pushes `data/*.json` as well as per-team HTML. The new `data/pressrow-{date}.json` artifact will be picked up automatically because it matches the existing glob; no deployment changes required.

- **CLAUDE.md guardrails:** `CLAUDE.md` at the repo root states: "Never `from build import ...` at module top — `build.py` runs as `__main__`, and a top-level import would trigger a second full re-execution under the name `build`." Press Row's section renderer must never import from `build.py` at module level. Use deferred imports inside function bodies only.

### Institutional Learnings

- **The columnists LLM fallback pattern works and should be copied wholesale.** The brainstorm notes that `sections/columnists.py` has been running in production with the Ollama→Anthropic fallback pattern. Its timeout values, error handling, and `MIN_COLUMN_CHARS` sanity check have all been battle-tested.

- **The shelved v1 prototype's failure mode is documented.** Testing in this session (see conversation earlier) showed qwen3:8b with `"format": "json"` enabled returned malformed output but with `"format"` disabled returned valid JSON. V2's `pressrow/llm.py` must NOT use `"format": "json"` in the Ollama request body.

- **Timestamp normalization is required.** The shelved prototype's `_normalize_timestamp()` function exists because qwen sometimes returns ISO timestamps instead of "10:34 PM" format. V2 must preserve this normalization.

- **Per-team rebuild discipline:** From the auto-memory at `~/.claude/projects/-home-tooyeezy/memory/feedback_rebuild_all_teams.md` — when changing shared assets, rebuild all 30 teams not just Cubs. Press Row's shared JSON artifact means one regeneration powers all 30 team pages, which matches this guidance perfectly (generate once, render 30 times).

- **Derived subscribers don't need timers:** From `~/.claude/projects/-home-tooyeezy/memory/feedback_derived_subscribers_timerless.md` — in polling/subscribe systems, event-kick derived subscribers instead of giving them timers. Press Row applies this: ML's build reads the cached artifact, doesn't trigger generation. Generation is its own scheduled event via `python3 -m pressrow build`.

### External References

No external research required. The brainstorm made all non-local decisions already (LLM provider choice, token budget, 3-pass pipeline structure). Existing local patterns cover everything technical.

## Key Technical Decisions

1. **Subpackage architecture, not new section module.** Press Row runs as `python3 -m pressrow build`, writes `data/pressrow-{date}.json`, and ML reads it. Rationale: ML builds stay fast (~30 sec/team instead of 3-5 min with LLM calls inline), Press Row can regenerate mid-day without touching ML, and Press Row failures don't block the daily briefing. Decision from the user's architecture conversation earlier in this session.

2. **Shared daily artifact, not per-team artifacts.** One `data/pressrow-{date}.json` powers all 30 team HTML pages. The thin renderer at `sections/pressrow.py` adds a `pr-home` class to tweets from the current team's writers for highlighting. Rationale: the feed is a league-wide social feed; per-team generation would 30× the LLM cost and fragment beefs across files.

3. **All state lives under `pressrow/state/` not `data/`.** Per-writer memory, relationships, cast state, and event state live co-located with the subpackage that writes them. Only the render-ready artifact (`data/pressrow-{date}.json`) and the obsolete-cache artifact (`data/pressrow-*-YYYY-MM-DD.*` if any) live in `data/`. Rationale: state is internal to Press Row; co-locating it with the code that owns it keeps mental model clean and makes the subpackage portable.

4. **Sonnet for the editor pass, Ollama for everything else.** The brainstorm's token budget shows ~$0.05/day in Sonnet cost, ~3-5 min of Ollama runtime. This is the biggest quality lever per dollar. If `ANTHROPIC_API_KEY` is unset, fall back to Ollama for the editor pass too (graceful degradation).

5. **Graceful degradation at every layer.** Each LLM pass has an Ollama → Anthropic → skip chain. If the Comedy Editor Pipeline fails for a specific writer, that writer doesn't tweet that day. If the whole generation fails, `data/pressrow-{date}.json` is missing, and `sections/pressrow.py` returns `""` — ML builds still succeed without the section.

6. **Start Phase 2 memory empty.** No migration from v1. On launch day, every writer has an empty `last_tweets` array and no predictions. Memory compounds from day one of v2. Rationale: v1 data is unusable (low quality); starting fresh is cleaner than filtering.

7. **Obsession authoring: LLM drafts + JB edits.** From the brainstorm's open questions (answer #2). Use a one-shot script that generates 3 candidate obsessions per writer via Sonnet, writes them to a review JSON, and JB edits by hand in ~1 hour instead of writing from scratch over a weekend. The script is a Phase 1 deliverable but runs once, not every build.

8. **Feud seeding: hand-authored first 10.** From the brainstorm's open questions (answer #3). JB writes the first 10 rivalries with origin stories and opening tallies before launch. After that, the Beef Engine can organically introduce new feuds by observing cross-team interaction patterns.

9. **Breakdown arc tone: always petty, never dark.** From the brainstorm's open questions (answer #5). The unraveling prompt must explicitly constrain the topic: the meltdown is about bullpen ERAs, umpire grudges, or analytics debates — never about anything heavy. This is enforced in the prompt, not post-hoc.

10. **Visibility: state stays invisible.** From the brainstorm's open questions (answer #6). No UI for relationships, predictions, or breakdown arcs in v2. All state shows up through tweet content. Rationale: mystery drives engagement; inspection UI is a different product decision.

## Open Questions

### Resolved During Planning

- **How does Press Row know when to run?** Answer: A separate cron job at 5:30am CT runs `python3 -m pressrow build`. ML's existing 6:00am build reads the artifact. If Press Row hasn't produced an artifact yet (first run, failure, manual trigger), ML's section returns empty.

- **How does the obsession authoring script work?** Answer: Phase 1, Unit 5 includes a one-shot `python3 -m pressrow seed obsessions` command that generates candidate obsessions for every writer and writes to `pressrow/config/obsessions.draft.json` for human review. After review, JB renames to `obsessions.json` to activate.

- **Where does the handle-normalization code live?** Answer: `pressrow/util.py` — the existing `_make_handle()` and `_make_initials()` from `docs/future/pressrow.py` move here.

- **How do we prevent the DAG generation pass from hallucinating writers that don't exist?** Answer: The DAG prompt receives the cast list as a constrained vocabulary. Post-processing validates every `writer` field against `pressrow/state/writers/` known handles and drops unknown entries. Pattern: `docs/future/pressrow.py` line ~260-290 (`_parse_and_validate`).

- **Should the Walk-Off Ghost and Breakdown writers count as the "30 team × 3 roles" cast or be extras?** Answer: Extras. The Ghost is one persona for the whole league (in `pressrow/config/cast.json`). Breakdown arcs temporarily modify an existing writer's generation prompt but don't add a new persona. Shadow personas ARE additions (one per team, 30 total new entries).

### Deferred to Implementation

- **Exact token counts per prompt.** Planning estimates from the brainstorm suggest ~500-800 input + 150 output per draft call. Real tuning happens during Unit 4 implementation when prompt length stabilizes.

- **Prediction extraction heuristics.** The brainstorm proposes an LLM classifier pass, but a regex-only pass might catch 80% of cases cheaper. Unit 6 will prototype both and pick.

- **Exact filename for the cron trigger.** Whether `daily-build.sh` gains a new line or a new `pressrow-build.sh` is created depends on how the existing daily build is wired; verify during Unit 3.

- **Render order in HTML output.** Whether Letters and Classifieds render as separate sibling sections or inline blocks within Press Row depends on how the CSS feels when rendered. Decide in Unit 8 with a screenshot iteration.

- **Breakdown arc trigger probability tuning.** Target is 2-3 arcs per 180-day season, so random roll should be ~1/60 per day. Exact number requires calibration against the real build schedule. Unit 10 ships with the 1/60 default and a config override.

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

**Subpackage layout:**

```
morning-lineup/
├── build.py                    # ML daily build (unchanged logic, adds pressrow section call)
├── sections/
│   ├── columnists.py           # existing, unchanged — reference pattern only
│   └── pressrow.py             # NEW — thin ~60 line renderer reading data/pressrow-{date}.json
├── pressrow/                   # NEW subpackage
│   ├── __init__.py
│   ├── __main__.py             # CLI: `python3 -m pressrow build` / `seed obsessions` / `seed feuds`
│   ├── orchestrator.py         # top-level build() coordinator
│   ├── llm.py                  # shared Ollama/Anthropic helper (ports columnists.py pattern)
│   ├── util.py                 # handle/initials/timestamp/json extraction helpers
│   ├── config_loader.py        # loads obsessions, cast, relationships, events from config/state
│   ├── game_digest.py          # reads briefing data shape, produces text digest
│   ├── pipeline/
│   │   ├── angles.py           # Feature 1 pass 1: angle generation
│   │   ├── draft.py            # Feature 1 pass 2: petty draft writing
│   │   └── editor.py           # Feature 1 pass 3: editor rewrite
│   ├── memory.py               # Feature 3: per-writer memory read/write + prediction extraction
│   ├── beef.py                 # Feature 4: DAG planner + relationship state advancer
│   ├── letters.py              # Feature 5: recurring-fan letter generation
│   ├── classifieds.py          # Feature 6: classifieds generation
│   ├── events.py               # Feature 7: breakdown arc scheduler + walk-off ghost trigger
│   ├── renderer.py             # writes the final data/pressrow-{date}.json artifact
│   ├── config/
│   │   ├── obsessions.json     # 270 hand-edited obsessions, 2-3 per writer
│   │   ├── shadow_personas.json # 30 one-topic lurker personas, 1 per team
│   │   ├── recurring_fans.json # 15-20 fictional fans with voice and starting state
│   │   ├── relationships.json  # 10 initial feuds with origin stories
│   │   └── cast.json           # walk-off ghost identity + scheduled event defaults
│   └── state/                  # runtime state, read at build start, written at build end
│       ├── writers/
│       │   └── {handle}.json   # per-writer memory, predictions, moods
│       ├── relationships.json  # evolving feud tallies and phases
│       ├── fans.json           # evolving fan state (mood, life events, grudges)
│       └── events.json         # active breakdown arc, triggered ghost posts history
└── data/
    └── pressrow-{date}.json    # the contract artifact: feed + letters + classifieds + events
```

**Daily build flow (high level):**

```
5:30 AM cron: python3 -m pressrow build
  ├── Load all config/ and state/ files
  ├── Fetch yesterday's games (via briefing equivalent OR by invoking build.load_all() carefully)
  ├── beef.py → generate DAG for today's interactions
  ├── memory.py → inject per-writer memory context into each planned tweet
  ├── pipeline/angles.py → generate 3 angles per planned writer
  ├── pipeline/draft.py → write petty drafts (one writer at a time)
  ├── pipeline/editor.py → editor rewrite each draft (Sonnet if available)
  ├── letters.py → generate 3-5 letters from recurring fans
  ├── classifieds.py → generate 5 classifieds
  ├── events.py → check breakdown arc + walk-off ghost triggers
  ├── memory.py → extract any new predictions, advance state
  ├── renderer.py → write data/pressrow-{date}.json
  └── Save all state/*.json files

6:00 AM cron: python3 build.py --team X (for each team)
  └── sections/pressrow.py reads data/pressrow-{date}.json, renders HTML block
```

**The JSON artifact contract:**

```
data/pressrow-{date}.json
{
  "generated": ISO timestamp,
  "tweets": [ ... full tweet objects as defined in the shelved prototype ... ],
  "letters": [ { fan_name, team_slug, text, mood, timestamp }, ... ],
  "classifieds": [ { type, team_context, text, attributed_to }, ... ],
  "events": [ { type: "breakdown_arc" | "walkoff_ghost", ... } ]
}
```

`sections/pressrow.py` reads this file, renders the 4 content blocks (feed, letters, classifieds, events) into HTML, and returns the concatenated string.

**Dependency graph across implementation units:**

```
Phase 0 (Infrastructure)
  Unit 1 (package scaffold) ──┐
  Unit 2 (LLM helper + state) ┤
  Unit 3 (ML renderer + cache contract) ──┐
                                           │
Phase 1 (Quality Foundation)               │
  Unit 4 (Comedy Editor Pipeline) ◄────── Units 1, 2, 3
  Unit 5 (Obsession config + authoring) ◄─ Units 1, 4 (injection point)

Phase 2 (Continuity & Character)
  Unit 6 (Memory + Receipts) ◄──────────── Units 4, 5
  Unit 7 (Beef Engine) ◄────────────────── Units 4, 6

Phase 3 (Universe Expansion)
  Unit 8 (Letters to the Editor) ◄──────── Units 1, 2, 3
  Unit 9 (Classifieds) ◄───────────────── Units 1, 2, 3

Phase 4 (Rare Moments)
  Unit 10 (Scheduled Events) ◄──────────── Units 4, 6
```

Units 8 and 9 can run in parallel with Phase 2 work because they depend only on Phase 0. Unit 10 must come last because it modifies active writers' generation.

## Implementation Units

### Phase 0: Infrastructure

- [ ] **Unit 1: Subpackage scaffold + CLI entry point**

**Goal:** Create the `pressrow/` subpackage with its directory layout, `__main__.py` CLI, and config/state loaders stubbed. This unit produces a package that can be invoked but does nothing useful yet.

**Requirements:** R8

**Dependencies:** None

**Files:**
- Create: `pressrow/__init__.py`
- Create: `pressrow/__main__.py`
- Create: `pressrow/orchestrator.py` (stub `build()` that logs "not implemented")
- Create: `pressrow/config_loader.py`
- Create: `pressrow/util.py` (port `_make_handle`, `_make_initials`, `_normalize_timestamp`, `_extract_json`, `_strip_thinking` from `docs/future/pressrow.py`)
- Create: `pressrow/config/.gitkeep`
- Create: `pressrow/state/.gitkeep`
- Create: `pressrow/state/writers/.gitkeep`
- Create: `tests/test_pressrow_util.py`

**Approach:**
- CLI supports three subcommands: `build`, `seed obsessions`, `seed feuds`. For this unit, only `build` needs to exist (as a stub).
- `config_loader.py` exposes `load_obsessions()`, `load_cast()`, `load_relationships()`, `load_fans()`, `load_writer_state(handle)`, `save_writer_state(handle, state)`. Each returns an empty-but-valid default if the file is missing.
- `util.py` ports helpers verbatim from the shelved prototype — do not rewrite, copy and clean up imports.
- The `pressrow` directory must be discoverable by Python's import system; since Morning Lineup runs `python3 build.py` from the repo root, `pressrow/` at the repo root is importable via `import pressrow`.
- `CLAUDE.md` guardrail: Never `from build import ...` at module top. `pressrow/game_digest.py` (Unit 2) will need `load_all()` data shapes but must import deferred inside function bodies.

**Patterns to follow:**
- `sections/columnists.py:36-70` for the data-directory helper pattern and cache-file JSON I/O
- `docs/future/pressrow.py:28-52` for the util helpers being ported
- `build.py` stdlib-only discipline — no pip dependencies

**Test scenarios:**
- Happy path: `pressrow._make_handle("Tony Gedeski")` returns `"tony_gedeski"`.
- Happy path: `pressrow._make_initials("Beatrice 'Bee' Vittorini")` returns `"BV"`.
- Happy path: `pressrow._normalize_timestamp("2023-10-05T21:30:00Z")` returns `"9:30 PM"`.
- Happy path: `pressrow._normalize_timestamp("9:30 PM")` returns `"9:30 PM"` unchanged.
- Edge case: `pressrow._make_handle("Dottie 'Verlander No Relation'")` — verify special chars strip cleanly.
- Edge case: `pressrow._extract_json('```json\n[]\n```')` returns `[]`.
- Edge case: `pressrow._extract_json('{"tweets": []}')` returns `[]`.
- Edge case: `pressrow._extract_json('not json at all')` returns `[]` (not an exception).
- Happy path: `config_loader.load_obsessions()` with no file present returns `{}` without raising.
- Happy path: `python3 -m pressrow build` runs without error, prints "not implemented yet".

**Verification:**
- The package imports cleanly from the repo root.
- The CLI runs and exits 0.
- All ported util helpers pass their tests.
- `pressrow/state/writers/` exists as an empty directory (via `.gitkeep`).

---

- [ ] **Unit 2: Shared LLM helper + game digest builder**

**Goal:** Build `pressrow/llm.py` with Ollama → Anthropic fallback and `pressrow/game_digest.py` that produces a plain-text digest of yesterday's real MLB games.

**Requirements:** R1, R4, R8

**Dependencies:** Unit 1

**Files:**
- Create: `pressrow/llm.py`
- Create: `pressrow/game_digest.py`
- Create: `tests/test_pressrow_llm.py` (mocked HTTP)
- Create: `tests/test_pressrow_game_digest.py` (static fixture)
- Create: `tests/fixtures/games_y_2026-04-12.json` (captured real response)

**Approach:**
- `llm.py` exposes one function: `call(prompt, *, max_tokens=1024, prefer="ollama", timeout_ollama=120, timeout_anthropic=30, min_chars=50)`. Tries Ollama first unless `prefer="anthropic"`, falls back to the other, returns empty string on total failure.
- Port `_try_ollama()` and `_try_anthropic()` verbatim from `sections/columnists.py:142-191`. Do NOT use `"format": "json"` in the Ollama request body — the session's debugging showed qwen returns malformed output with that flag set.
- `game_digest.py` exposes `build(games_y)` which takes the raw games list from `briefing.data["games_y"]` and returns a multi-line plain-text digest. Adopt the iteration pattern from `sections/around_league.py:35-55` — filter for `status.abstractGameState == "Final"`, extract team names and scores, format one line per game.
- For Press Row's independent build cycle (not inside `build.py --team X`), the orchestrator needs to fetch `games_y` itself. Easiest path: deferred-import `build.load_all()` inside `orchestrator.build()`. The `CLAUDE.md` guardrail only forbids module-top imports. Alternative: call the MLB Stats API directly from `pressrow/game_digest.py`. Decision: deferred-import `build.load_all()` to avoid duplicating API-fetch logic.

**Patterns to follow:**
- `sections/columnists.py:142-191` for the exact Ollama/Anthropic request bodies, headers, error handling.
- `sections/around_league.py:35-55` for the games_y iteration shape.
- `docs/future/pressrow.py:101-127` for the existing `_build_game_digest()` implementation as a starting point — the shelved version is already close.

**Test scenarios:**
- Happy path: `llm.call(prompt)` returns a non-empty string when Ollama is mocked to return a valid response.
- Happy path: `llm.call(prompt)` returns the Anthropic response when Ollama raises a timeout.
- Error path: `llm.call(prompt)` returns `""` when both Ollama and Anthropic fail.
- Error path: `llm.call(prompt)` returns `""` when the response is shorter than `min_chars`.
- Happy path: `game_digest.build(fixture)` includes every Final game from the fixture.
- Edge case: `game_digest.build([])` returns "No MLB games were played yesterday..." (matching the shelved prototype's fallback message).
- Edge case: `game_digest.build(games_with_live_game)` excludes games that are not Final.
- Edge case: `game_digest.build(double_header)` handles both games of a double-header correctly.

**Verification:**
- `pressrow.llm.call` succeeds end-to-end against a live Ollama instance in a dev environment (manual smoke test).
- The game digest output is a human-readable text block identical in shape to the shelved prototype's output.

---

- [ ] **Unit 3: Thin ML renderer + cache contract + build.py integration**

**Goal:** Wire Press Row back into ML via `sections/pressrow.py` (reads the JSON artifact, returns HTML) and the integration points in `build.py`. Add the CSS block to `style.css`. This unit makes ML capable of displaying a Press Row section once the artifact exists, but does not yet generate any content.

**Requirements:** R8, R9

**Dependencies:** Unit 1 (for config loader, though this unit only reads the final artifact, not state)

**Files:**
- Create: `sections/pressrow.py` (thin renderer, ≤100 lines)
- Modify: `build.py` (lines ~25, ~666, ~670-680, ~740-752, ~829-847 — same patches the shelved prototype applied)
- Modify: `style.css` (append Press Row CSS block — the same block the shelved prototype used, saved in `~/.claude/plans/shimmering-wiggling-newell.md`)
- Create: `data/pressrow-example.json` (hand-authored fixture for rendering tests)
- Create: `tests/test_sections_pressrow.py`

**Approach:**
- `sections/pressrow.py` must: (1) compute today's ISO date from `briefing.data["today"]`, (2) look for `data/pressrow-{iso}.json`, (3) if missing, return `""` (graceful degradation per R9), (4) if present, render the feed + letters + classifieds + events blocks and return the HTML string.
- Port the render helpers from `docs/future/pressrow.py:372-455` (`_render_tweet`, `_render_quoted`, `_REPLY_SVG`, `_RT_SVG`, `_HEART_SVG`).
- Add new render helpers for letters, classifieds, and events blocks. Each returns an HTML snippet; the top-level `render()` concatenates them with section dividers.
- `build.py` patches are identical to the shelved prototype's — the 5 patch points at lines 25, 666, 670-680, 740-752, 829-847. Apply them via `Edit` tool operations matching those exact surrounding lines.
- CSS additions: the Press Row block already exists as a saved patch. Append it to `style.css`. Add two new blocks for `.pr-letters` and `.pr-classifieds` — letters use an italic newspaper-letter-column style, classifieds use a 3-column tight-set mono block.
- Current-team highlighting: any tweet whose `author.team_slug` matches `briefing.config["slug"]` gets a `pr-home` class.

**Patterns to follow:**
- `docs/future/pressrow.py:407-458` for `_render_tweet()` and `_render_quoted()`.
- `docs/future/pressrow.py` README patch instructions for the `build.py` wiring.
- `sections/columnists.py:261-295` for the `render(briefing)` entry-point contract.

**Test scenarios:**
- Happy path: `render(briefing)` returns empty string when `data/pressrow-{today}.json` is missing.
- Happy path: `render(briefing)` renders the fixture file into HTML containing one `<article class="pr-tweet">` per tweet in the fixture.
- Happy path: the current team's tweets get the `pr-home` class.
- Edge case: `render(briefing)` handles a fixture with zero tweets, zero letters, zero classifieds gracefully (returns a near-empty feed container, not a crash).
- Edge case: a quote tweet whose `quote_of` references a non-existent tweet renders as an original (drop the embed, do not crash).
- Integration: running `python3 build.py --team cubs` with the fixture in place produces a Cubs HTML page that includes a valid Press Row section.
- Integration: running `python3 build.py --team cubs` with NO artifact file produces a valid Cubs HTML page without a Press Row section (R9: graceful degradation).

**Verification:**
- Visual screenshot of `cubs/index.html` shows the Press Row section rendering with fixture data.
- `python3 tests/snapshot_test.py` passes after re-blessing the new snapshot (the new section is intentional).

---

### Phase 1: Quality Foundation

- [ ] **Unit 4: Comedy Editor Pipeline (3-pass generation)**

**Goal:** Build the core generation pipeline — angles, petty draft, editor rewrite — that produces one tweet per target writer per build. At the end of this unit, `python3 -m pressrow build` generates 20-25 tweets that are measurably funnier than the shelved prototype's output.

**Requirements:** R1

**Dependencies:** Units 1, 2, 3

**Files:**
- Create: `pressrow/pipeline/__init__.py`
- Create: `pressrow/pipeline/angles.py`
- Create: `pressrow/pipeline/draft.py`
- Create: `pressrow/pipeline/editor.py`
- Create: `pressrow/renderer.py` (writes the JSON artifact)
- Modify: `pressrow/orchestrator.py` (wire the pipeline into `build()`)
- Create: `tests/test_pressrow_pipeline.py` (mocked LLM)
- Create: `tests/fixtures/pipeline_expected.json`

**Approach:**
- `angles.py` exposes `generate(writer, game_digest, obsessions)` returning a JSON object `{stat, narrative, grievance}` with one-sentence angles. Ollama-only call, tight token budget (~200 output).
- `draft.py` exposes `write(writer, angles, game_digest, memory_context)` returning one tweet draft (max 240 chars). Prompt instructs the model to pick the PETTIEST angle. Required fields in output: at least one real player name, at least one specific number, one clear emotion. Use the existing schema-validation approach from `docs/future/pressrow.py:_parse_and_validate`.
- `editor.py` exposes `rewrite(draft, writer)` taking the draft and returning a rewritten version. Prefers Sonnet via `llm.call(..., prefer="anthropic")`. Prompt explicitly forbids phrases like "buckle up," "what a night in baseball," "folks," "speaking of," "meanwhile" — test this constraint.
- `orchestrator.py`'s `build()` loops over target writers (20-25, chosen by the Beef Engine in Unit 7; for Unit 4, use a round-robin over all 90 with a cap at 22): for each, generate angles → draft → editor. Collect results.
- `renderer.py` takes the collected tweets + (for now empty) letters/classifieds/events and writes the artifact to `data/pressrow-{date}.json`.
- Each tweet stores `draft_text` and `final_text` fields for before/after inspection.

**Technical design:** *(directional guidance)*

```
for writer in target_writers(~22):
  angles = angles.generate(writer, digest, obsessions[writer])   # Ollama
  draft  = draft.write(writer, angles, digest, memory)           # Ollama
  final  = editor.rewrite(draft, writer)                         # Anthropic if key set, else Ollama
  tweets.append({id, author, type, draft_text, final_text, ...})

renderer.write(data/pressrow-{date}.json, { tweets, letters:[], classifieds:[], events:[] })
```

**Patterns to follow:**
- `sections/columnists.py:102-135` for the per-persona prompt structure.
- `docs/future/pressrow.py:130-170` for the existing prompt template as a starting point.
- `docs/future/pressrow.py:260-360` for the JSON parsing and validation patterns.

**Test scenarios:**
- Happy path: `angles.generate(writer, digest, obs)` returns a dict with three non-empty keys when LLM is mocked to return valid JSON.
- Edge case: `angles.generate` returns `None` when LLM returns malformed JSON and the orchestrator skips that writer.
- Happy path: `draft.write(...)` returns a string ≤240 chars containing at least one real player name from the game digest.
- Edge case: `draft.write(...)` regenerates once when the first draft lacks required fields (real_player, specific_number).
- Happy path: `editor.rewrite("The Cubs lost again")` returns a different string with none of the banned phrases.
- Error path: `editor.rewrite` falls back to the draft when both LLM providers fail (not "" — the draft is better than nothing).
- Integration: `orchestrator.build()` end-to-end produces a valid `data/pressrow-{date}.json` file with ≥15 tweets.
- Integration: Running the full build with mocked LLM returning repetitive content demonstrates the editor pass detects and rejects duplicated tweets across writers.

**Verification:**
- Manual smoke test: run `python3 -m pressrow build` against a real Ollama + Sonnet setup and read the output. Subjective but required — the tweets must be visibly funnier than the v1 shelved prototype output (see `docs/future/pressrow.py` and the saved example output in the session log).
- `data/pressrow-{date}.json` contains ≥15 tweets, each with both `draft_text` and `final_text` populated.
- Rendering with the new artifact produces a Cubs page that displays the real generated content.

---

- [ ] **Unit 5: Writer Obsession config + seeding script + prompt injection**

**Goal:** Extend the team persona schema with a mandatory `obsessions` array, build a one-shot `python3 -m pressrow seed obsessions` command that generates LLM drafts for human review, and wire obsession injection into the draft pipeline.

**Requirements:** R2

**Dependencies:** Unit 4 (needs the draft prompt to inject into)

**Files:**
- Create: `pressrow/config/obsessions.json` (initially empty, populated after seed run + JB review)
- Create: `pressrow/config/shadow_personas.json` (30 entries, hand-authored)
- Create: `pressrow/seed_obsessions.py`
- Modify: `pressrow/__main__.py` (add `seed obsessions` subcommand)
- Modify: `pressrow/pipeline/draft.py` (inject obsessions into prompt)
- Modify: `pressrow/config_loader.py` (load obsessions by writer handle)
- Create: `tests/test_pressrow_obsessions.py`

**Approach:**
- Obsession schema (per writer): `{topic, angle, trigger_phrases}`. Store in `pressrow/config/obsessions.json` keyed by writer handle. Each writer has 2-3 obsessions.
- The seed script loops over all 90 writers. For each, calls Sonnet once with a prompt that includes the writer's name, role, backstory, signature phrase, and asks for 3 candidate obsessions matching the schema. Writes all output to `pressrow/config/obsessions.draft.json`. JB reviews and manually renames/edits to `obsessions.json`.
- Draft prompt injection: `draft.write()` looks up the writer's obsessions and appends a block: "Your load-bearing obsessions: [topic] — you believe [angle]. At least 50% of your tweets must pivot back to one of these, whether or not it's directly relevant."
- Shadow personas schema (per team): `{name, handle, team_slug, monomaniac_topic, post_probability}`. 30 entries in `pressrow/config/shadow_personas.json`. These are NOT generated by seeding — JB writes them by hand (they're the running gag, they need authorial taste). Shadow personas get pulled into the target writer pool in `orchestrator.build()` at their `post_probability` rate.

**Patterns to follow:**
- `teams/cubs.json:59-81` for the existing persona schema shape that obsessions extend.
- `sections/columnists.py:102-135` for the prompt-injection pattern inside a writer-specific prompt.

**Test scenarios:**
- Happy path: `config_loader.load_obsessions()["tony_gedeski"]` returns a list of 3 obsession dicts.
- Happy path: `config_loader.load_obsessions()["unknown_writer"]` returns `[]` (does not raise).
- Happy path: `draft.write(writer, ...)` with obsessions loaded generates a prompt that contains the obsession strings (test via prompt-capture mock).
- Happy path: `seed_obsessions.py` when mocked writes a file with 90 top-level keys.
- Edge case: `seed_obsessions.py` continues across individual LLM failures (failure for 1 writer doesn't block the rest).
- Happy path: `config_loader.load_shadow_personas()["cubs"]` returns the Cubs shadow persona.
- Integration: The orchestrator respects `shadow_persona.post_probability` — a shadow persona with `0.3` posts roughly 30% of builds over a 100-build simulation.

**Verification:**
- Running `python3 -m pressrow seed obsessions` produces a `pressrow/config/obsessions.draft.json` with 90 top-level keys, each having 3 candidate obsessions.
- After JB reviews and activates, draft tweets visibly reference obsessions in ≥40% of output samples.
- 30 shadow personas hand-authored in `pressrow/config/shadow_personas.json`.

**Manual task for JB (outside this unit):** Author 270 obsessions by editing the seed output (~1 hour). Author 30 shadow personas (~1 hour). Both are data, not code, but are prerequisites for Phase 2.

---

### Phase 2: Continuity & Character

- [ ] **Unit 6: Per-writer memory + prediction extraction**

**Goal:** Make every writer remember their last 3 tweets and any unresolved predictions. Inject memory context into draft prompts. Extract predictions from generated tweets and check resolution against yesterday's real data.

**Requirements:** R3, R10

**Dependencies:** Units 4, 5

**Files:**
- Create: `pressrow/memory.py`
- Modify: `pressrow/pipeline/draft.py` (accept memory context, include in prompt)
- Modify: `pressrow/orchestrator.py` (call memory before and after generation)
- Create: `tests/test_pressrow_memory.py`
- Create: `tests/fixtures/writer_state_tony.json`

**Approach:**
- Per-writer state file format (at `pressrow/state/writers/{handle}.json`):
  ```
  { handle, last_tweets: [ {date, text, type, id}, ... ],
    predictions: [ {date_made, text, resolves_by, resolved, outcome} ],
    active_beefs: [ handle, ... ], mood: str,
    last_signature_use: iso_date }
  ```
- `memory.load(handle)` returns the state dict (empty defaults if missing). `memory.save(handle, state)` writes it.
- `memory.context_for(handle)` returns a prompt-injectable text block: "Your last 3 tweets were: [...]. Unresolved predictions: [...]."
- `memory.extract_prediction(tweet_text)` uses a cheap Ollama classifier pass returning either `None` or `{predicted_what, resolves_by}`. First prototype: regex-based (look for future-tense patterns like "will", "by July", "next month"). If regex hit rate is low, fall back to LLM classifier.
- `memory.check_resolutions(state, games_y)` walks unresolved predictions, compares against yesterday's real outcomes, marks `resolved: true` with `outcome: hit | miss`.
- Orchestrator flow: BEFORE generation, load state for each writer, produce memory_context, pass to draft.write(). AFTER generation, for each generated tweet, extract any new prediction and append to the writer's state; save state.
- Memory injection into draft prompt is additive — the existing obsessions block stays, memory block appends.
- Receipt injection: if writer A has a recently-resolved prediction with `outcome: miss`, the orchestrator tags it as a "callback available" for OTHER writers. Probability 20% that a non-A writer's prompt includes: "RECEIPTS AVAILABLE: @A predicted on [date] that [...]. It just missed. You may quote-tweet or dunk."

**Patterns to follow:**
- `sections/columnists.py:53-70` for the cache-file JSON read/write pattern.
- `docs/future/pressrow.py:308-336` for the validation-with-remap pattern (useful for the prediction extract/match).

**Test scenarios:**
- Happy path: `memory.load("tony_gedeski")` returns the fixture state dict.
- Happy path: `memory.load("never_existed")` returns a default empty state without raising.
- Happy path: `memory.context_for(handle)` returns a string containing the last 3 tweet texts.
- Edge case: `memory.context_for(handle)` with empty `last_tweets` returns a string like "This is your first tweet in the feed."
- Happy path: `memory.extract_prediction("Ricketts will trade Bellinger by July")` returns a prediction dict.
- Edge case: `memory.extract_prediction("Hoerner had a great game")` returns `None`.
- Happy path: `memory.check_resolutions(state, games_y)` updates a prediction to `resolved: true` when the condition fires.
- Integration: An end-to-end 3-day simulation (3 builds in sequence) shows day 3's tweets referencing day 1's predictions.
- Integration: After 5 builds, `tony_gedeski.json` has 5+ entries in `last_tweets` (capped at some retention window).

**Verification:**
- Memory state files accumulate correctly across simulated builds.
- A tweet sample from day N references content from days N-1 or N-2 with visible frequency.
- The receipt callback mechanic fires at least once in a 5-day simulation.

---

- [ ] **Unit 7: Beef Engine — DAG planner + persistent rivalries**

**Goal:** Replace the round-robin writer selection with a pre-generation DAG that explicitly architects who interacts with whom today. Add persistent cross-team rivalries with origin stories. One daily feud arc gets mandatory advancement.

**Requirements:** R4

**Dependencies:** Units 4, 6

**Files:**
- Create: `pressrow/beef.py`
- Create: `pressrow/config/relationships.json` (10 hand-authored initial feuds)
- Modify: `pressrow/orchestrator.py` (replace round-robin with DAG-driven target selection)
- Modify: `pressrow/pipeline/draft.py` (accept parent tweet context for replies/quotes)
- Create: `tests/test_pressrow_beef.py`

**Approach:**
- `relationships.json` (config) stores feud origins:
  ```
  { feuds: [ { id, writers: [h1, h2], origin: {date, event}, running_tally: {h1: 4, h2: 3}, current_phase: active|dormant|resolved, last_interaction: date } ] }
  ```
- State counterpart at `pressrow/state/relationships.json` — same shape, but evolving. Config is seed, state is current reality. On first run, state is copied from config; subsequent runs update state only.
- `beef.plan_dag(writers, digest, relationships_state)` makes ONE Ollama call with a planning prompt: "Generate 8 interactions for today. Each interaction is a root tweet + 1-2 replies or quotes. Specify writers by handle, an interaction type, and a one-line intent." Returns a JSON DAG like:
  ```
  [ { id, root: {writer, intent}, replies: [ {writer, intent}, ... ] } ]
  ```
- Post-process DAG: validate all writer handles exist, drop unknown entries, cap at ~20 total tweets (DAG root + 2 replies × 8 threads ≈ 24, trim as needed).
- Orchestrator flow update: call `beef.plan_dag()` first, then walk the DAG. For each root, call `draft.write(writer, angles, digest, memory, parent=None)`. For each reply, call `draft.write(writer, angles, digest, memory, parent=parent_tweet_text, relationship_context=feud_note)`.
- Daily featured feud: before DAG planning, `beef.pick_featured_feud(relationships_state)` selects one active feud whose `last_interaction` is >=3 days old. The planning prompt must include: "This interaction must advance the [A vs B] feud. Opening state: [tally + phase]."
- After generation, `beef.update_relationships(state, tweets)` increments tallies and updates `last_interaction` for any feud whose writers tweeted at each other.

**Patterns to follow:**
- `docs/future/pressrow.py:260-360` for the JSON parsing, ID remapping, and orphan-reference handling patterns that the DAG output needs.

**Test scenarios:**
- Happy path: `beef.plan_dag(writers, digest, rels)` with a mocked LLM returns a list of interaction objects with valid writer handles.
- Edge case: `beef.plan_dag` silently drops interactions referencing unknown writers.
- Edge case: `beef.plan_dag` respects the writer-count cap (no more than ~24 tweets even if LLM returns more).
- Happy path: `beef.pick_featured_feud(state)` returns a feud whose last_interaction is ≥3 days old.
- Happy path: `beef.update_relationships` increments the tally for both writers in an interaction.
- Integration: End-to-end build with 10 seeded feuds produces a tweet stream where ≥2 reply threads correspond to active feuds.
- Integration: After 5 builds, at least 3 different feuds have had their `last_interaction` updated.

**Verification:**
- Generated tweet feed has visible reply chains that correspond to pre-planned DAG structure.
- `pressrow/state/relationships.json` evolves across builds.
- At least one featured feud advances every build.
- Manual JB task: author 10 initial feuds in `pressrow/config/relationships.json` with origin stories and opening tallies.

---

### Phase 3: Universe Expansion

- [ ] **Unit 8: Letters to the Editor (recurring fans)**

**Goal:** Add a daily letters column from a recurring cast of ~20 fictional fans with names, voices, and per-character state that advances day-to-day. Writers can reply to letters.

**Requirements:** R5, R10

**Dependencies:** Units 1, 2, 3

**Files:**
- Create: `pressrow/letters.py`
- Create: `pressrow/config/recurring_fans.json` (15-20 hand-authored fans)
- Create: `pressrow/state/fans.json` (mirror of config at build-start, evolves over time)
- Modify: `pressrow/orchestrator.py` (call letters after main feed generation)
- Modify: `pressrow/renderer.py` (write letters into the artifact)
- Modify: `sections/pressrow.py` (render the letters block)
- Modify: `style.css` (add `.pr-letters` CSS block)
- Create: `tests/test_pressrow_letters.py`

**Approach:**
- Fan schema:
  ```
  { name, team_slug, voice, state: { mood, recent_life_events: [], current_grudge }, post_probability }
  ```
- `letters.select_active(fans_state)` picks 3-5 fans per build, weighted by `post_probability` and recency (a fan who posted yesterday is less likely to post today).
- `letters.generate(fan, yesterday_game_for_team)` produces a 100-150 word letter in the fan's voice, using the fan's current state. Also returns an advanced state (new life event flag, updated mood).
- After generation, `letters.maybe_writer_reply(letter, writers)` — 20% of letters get a one-line reply from one of the 90 writers. Use Ollama for this cheap call.
- State advancement: after each build, the fan's `state` is updated based on what the LLM produced. Uses a small classifier pass to extract state deltas from the letter text.

**Patterns to follow:**
- `sections/columnists.py:194-220` for the per-persona LLM generation + cache pattern.
- `pressrow/memory.py` (Unit 6) for the state read/write pattern.

**Test scenarios:**
- Happy path: `letters.select_active(fans_state)` returns 3-5 fans respecting post_probability.
- Happy path: `letters.generate(fan, game)` returns a non-empty letter string using the fan's voice.
- Happy path: a fan who posted yesterday has a reduced probability of posting today.
- Edge case: `letters.generate` for a fan whose team had no game yesterday produces a non-game-related letter.
- Happy path: `maybe_writer_reply` hits at ~20% rate over a large simulation.
- Integration: After 5 builds, `pressrow/state/fans.json` shows evolved state across 3+ fans.
- Integration: The artifact's `letters` array contains 3-5 entries per build.

**Verification:**
- Letters render visually in the Cubs page with their own `.pr-letters` styling distinct from the tweet feed.
- Fans develop visible arcs over 10 simulated builds.
- Manual JB task: author 15-20 recurring fans with distinct voices and starting states.

---

- [ ] **Unit 9: Classifieds**

**Goal:** Add a daily classifieds column generating 5 short newspaper-style ads in various categories attributed to writer personas.

**Requirements:** R6

**Dependencies:** Units 1, 2, 3

**Files:**
- Create: `pressrow/classifieds.py`
- Modify: `pressrow/orchestrator.py` (call classifieds alongside letters)
- Modify: `pressrow/renderer.py` (write classifieds into the artifact)
- Modify: `sections/pressrow.py` (render the classifieds block)
- Modify: `style.css` (add `.pr-classifieds` CSS block)
- Create: `tests/test_pressrow_classifieds.py`

**Approach:**
- `classifieds.generate(game_digest, writers)` makes ONE Ollama call returning 5 classifieds as JSON. Prompt: "Generate 5 newspaper classifieds. Types: help_wanted | missed_connections | for_sale | personals. Max 60 words each. Voice: bone-dry, specific, absurd. Leverage yesterday's games [digest]. Match each to a writer persona so their voice shows through."
- Schema: `{type, team_context, text, attributed_to}`.
- Validation: reject outputs shorter than 2 classifieds, missing required fields, or exceeding 80 words. Retry once on validation failure, else return an empty list (graceful degradation — the classifieds block just renders empty).
- CSS block: 3-column tight-set mono or condensed font, newspaper-style header band, each classified has a uppercase category label.

**Patterns to follow:**
- `docs/future/pressrow.py:260-360` for the JSON parsing and validation patterns.

**Test scenarios:**
- Happy path: `classifieds.generate(digest, writers)` with mocked LLM returns 5 validated classifieds.
- Edge case: returns `[]` when LLM fails both providers.
- Edge case: discards any classified exceeding 80 words.
- Happy path: each returned classified has a non-empty `attributed_to` field matching a known writer handle.
- Integration: Full build includes a `classifieds` array of 3-5 entries in the artifact.
- Integration: Rendering shows a visually distinct 3-column classifieds block.

**Verification:**
- Classifieds render in a 3-column block with distinct typography.
- Manual taste test: 3 of 5 classifieds per build should be recognizably in a writer's voice.

---

### Phase 4: Rare Moments

- [ ] **Unit 10: Scheduled Events — Breakdown Arc + Walk-Off Ghost**

**Goal:** Add two rare event types: a 7-day writer breakdown arc that fires ~2x per season, and a walk-off ghost persona that only posts when a game ends dramatically.

**Requirements:** R7

**Dependencies:** Units 4, 6

**Files:**
- Create: `pressrow/events.py`
- Create: `pressrow/state/events.json` (tracks active breakdown + ghost post history)
- Modify: `pressrow/orchestrator.py` (inject breakdown context into target writer's prompt when active; check ghost trigger after DAG)
- Modify: `pressrow/pipeline/draft.py` (accept breakdown_context parameter)
- Modify: `pressrow/renderer.py` (write ghost posts into the artifact)
- Modify: `sections/pressrow.py` (render ghost posts with distinct styling)
- Modify: `style.css` (add `.pr-ghost` and subtle breakdown-day class markers)
- Modify: `pressrow/config/cast.json` (add walk-off ghost identity)
- Create: `tests/test_pressrow_events.py`

**Approach:**

*Breakdown Arc:*
- `events.check_breakdown(state, writers)`: if no active breakdown and random roll < 1/60, pick a random writer and initialize `{writer_handle, day: 1, started: today}`. Override via `pressrow/config/override.json` for manual triggering.
- If breakdown is active, the orchestrator injects breakdown context into that writer's draft prompt: "You are in day N of a slow public unraveling over [petty_topic]. Your tweets should feel 30% more unhinged. Reference [personal_detail]. Topic constraint: NEVER heavy or dark. Always petty." Day→tone mapping is hand-coded (day 1: subtle, day 4: confessional, day 6: going on leave, day 7: silent, day 8: return with new signature).
- Day 7: that writer does NOT tweet. Absence is the feature.
- Day 8: the writer returns with ONE config change (new signature phrase, new obsession added, or retired one old obsession).

*Walk-Off Ghost:*
- `events.check_walkoff_triggers(games_y)`: rule-based scan. Trigger types: walk-off home run, walk-off hit (any kind), extra innings 12+, no-hitter, blown save in 9th. Returns a list of triggered events with venue + inning.
- For each triggered event, `events.generate_ghost_post(event)`: single Ollama call producing ONE tweet max 120 chars, second-person, cryptic, never names players, always mentions a physical venue detail.
- Ghost posts go into the artifact's `events` array, rendered by the renderer with `.pr-ghost` styling (centered, italic, no avatar).

**Technical design:** *(directional guidance)*

```
State shape for events.json:
{
  breakdown_arc: null | {writer_handle, day: 1..8, started, petty_topic},
  ghost_posts_this_season: [ {date, event_type, text} ]
}

Breakdown day → prompt tone map (hardcoded):
  1: "10% weirder than normal"
  2: "slipping, references 'tired'"
  3: "unraveling, personal references at odd hours"
  4: "confessional long thread"
  5: "one cryptic post only"
  6: "single tweet announcing break"
  7: NO TWEETS
  8: "return with one change: new sig phrase OR new obsession"
```

**Patterns to follow:**
- `docs/future/pressrow.py:_render_tweet` for the rendering pattern — ghost rendering is a simplified variant.
- `pressrow/memory.py` (Unit 6) for the state read/write pattern.

**Test scenarios:**
- Happy path: `events.check_breakdown(state, writers)` returns `None` when no arc is active and random roll > threshold.
- Happy path: `events.check_breakdown` initializes a new arc when random roll < threshold, respecting the deterministic random seed for test.
- Happy path: On day 7 of a breakdown, the target writer's tweet is explicitly suppressed in orchestrator output.
- Happy path: On day 8, the writer's state shows an updated signature_phrase or obsessions array.
- Happy path: `events.check_walkoff_triggers(fixture_walkoff_hr)` detects the trigger.
- Edge case: `events.check_walkoff_triggers(fixture_regular_games)` returns `[]`.
- Happy path: `events.generate_ghost_post(event)` returns a string ≤120 chars with no player names (regex check).
- Edge case: Override file `pressrow/config/override.json` with `{"breakdown_start": "tony_gedeski"}` forces a breakdown on next build.
- Integration: Simulated 180-day run produces 2-4 breakdown arcs (statistical check).
- Integration: The override mechanism triggers a breakdown correctly and the arc advances over 8 builds.

**Verification:**
- A simulated breakdown arc runs end-to-end across 8 builds with appropriate tone changes.
- Ghost posts appear only on days with triggering events.
- Manual JB task: decide ghost name and voice in `pressrow/config/cast.json`.

---

## System-Wide Impact

- **Interaction graph:**
  - New cron trigger at 5:30am CT runs `python3 -m pressrow build`. The existing 6:00am `build.py` run reads the artifact. These are now two coupled scheduled events; operational docs must mention the dependency.
  - `build.py` integration points (import, section call, TOC, HTML block) are identical to the shelved prototype's patches — no novel integration shapes.
  - `sections/pressrow.py` never imports from `build.py` at module top (CLAUDE.md guardrail).

- **Error propagation:**
  - Press Row generation failures: the artifact file is missing or malformed → `sections/pressrow.py` returns `""` → ML omits the section → page renders normally (R9 graceful degradation).
  - Partial LLM pass failures: each pass has local Ollama→Anthropic→skip chain. A single writer's failure costs one tweet, not the feed.
  - Anthropic API key missing: `llm.call(prefer="anthropic")` silently falls back to Ollama. The editor pass quality drops but doesn't crash.

- **State lifecycle risks:**
  - Per-writer state files accumulate indefinitely. Each build prunes `last_tweets` to 3 entries and expires resolved predictions older than 30 days.
  - The `data/pressrow-*.json` artifact files are NOT pruned in v2 — they're small (~20-50KB) and useful for debugging. Add a future cleanup task.
  - Concurrent builds could race on state files. The daily build is single-threaded, so no lock needed in v2, but document the assumption.
  - If `pressrow build` is interrupted mid-run, partial state writes could corrupt. Mitigation: write to `{file}.tmp`, rename atomically.

- **API surface parity:**
  - The artifact shape is the contract between Press Row and ML. Any change to the schema requires updating both `pressrow/renderer.py` and `sections/pressrow.py` together.
  - Any new config file must have a graceful `load_*()` that returns a valid empty default.

- **Integration coverage:**
  - End-to-end build → render → display must be tested at the HTML level, not just JSON.
  - Multi-day simulations are the only way to verify memory, beefs, fans, and events compound correctly. Build a `pressrow/test_simulate.py` harness that fakes the daily loop.

- **Unchanged invariants:**
  - Morning Lineup's daily briefing build (`build.py`) remains stateless per team and still completes in <30 seconds per team. Press Row adds zero latency to ML builds because all LLM work happens in the separate 5:30am process.
  - Existing sections (`columnists.py`, `around_league.py`, etc.) are unchanged. No existing function signature changes.
  - The `teams/{slug}.json` schema gains an optional `obsessions` field (backward compatible — if missing, Press Row loads from its own config).
  - Existing CSS variables in `style.css` are reused, not redefined.
  - The MLB Stats API call pattern in `build.load_all()` is reused as-is via deferred import — no new API fetch logic.

## Risks & Dependencies

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LLM output quality still fails to "pop" even with the 3-pass pipeline | Medium | High | Unit 4 has a subjective smoke test gate. If the v2 output is still bland, stop and iterate on prompts before proceeding to Phase 2. Budget extra time for prompt tuning. Consider upgrading the base model. |
| Obsession authoring takes longer than estimated (8-10 hours vs 1) | Medium | Medium | The seeding script produces candidates — JB only needs to edit, not write from scratch. Obsessions can also be backfilled gradually; Phase 1 can ship with 1 obsession per writer and expand. |
| Sonnet costs exceed the $0.05/day estimate | Low | Medium | The estimate assumes 25 editor-pass calls × 500 input + 150 output. If real usage creeps higher, cap editor passes at 15/day and let the rest ship as drafts. Or gate editor pass behind an env var. |
| State files corrupt across builds | Low | High | Atomic writes via `{file}.tmp` + rename. Add a state validator that runs at build start. Keep backups of the last 7 days of state in `pressrow/state/archive/`. |
| The DAG planner hallucinates writers or produces invalid JSON | Medium | Medium | Strict post-processing validation from `docs/future/pressrow.py:_parse_and_validate`. Unknown handles dropped silently. Invalid JSON retries once, then falls back to round-robin. |
| Cron coupling (5:30am + 6:00am) creates ops brittleness | Medium | Medium | R9 graceful degradation means ML works without the artifact. Document the coupling prominently. Add a `--sync-pressrow` flag to `build.py` that runs both sequentially as a manual fallback. |
| Memory window retention grows unbounded | Low | Low | Cap `last_tweets` at 3 entries per writer. Expire predictions older than 30 days. Prune state files via a weekly cleanup job (add to Phase 4 scope if it becomes a problem). |
| Breakdown arc tone drifts dark despite prompt constraints | Medium | Medium | Constraint is encoded in the prompt AND validated post-generation by a classifier pass. If a breakdown tweet contains heavy keywords (mental health, real personal trauma terms), reject and regenerate with stronger constraint. |
| Recurring fan state advancement produces incoherent arcs over long runs | Medium | Low | Hand-review fans after 30 days of runtime; tune or reset state if needed. Acceptable for v2 — this is explicitly a tuning task after launch. |
| Press Row generation runtime exceeds 10 minutes | Low | Medium | One-writer-at-a-time inherently scales with writer count. Cap target writer pool at 25. Use local Ollama for all non-editor passes. If still slow, parallelize angle-generation calls (stdlib `concurrent.futures`). |
| Deployment doesn't pick up the new JSON artifact | Low | High | `deploy.py` already ships `data/*.json`. Verify during Unit 3 with a dry-run deploy. |

## Dependencies / Prerequisites

- **Ollama running locally** with `qwen3:8b-q4_K_M` pulled. Already present (see existing columnists pipeline).
- **ANTHROPIC_API_KEY** available at build time, ideally via `~/.secrets/morning-lineup.env`. Optional but strongly recommended for the editor pass.
- **JB's authorial time** for three data-authoring tasks:
  1. Review + edit 270 seeded obsessions (~1 hour)
  2. Author 30 shadow personas from scratch (~1 hour)
  3. Author 15-20 recurring fans with voices and starting states (~1 hour)
  4. Author 10 initial feuds with origin stories (~30 min)
  5. Name and voice the walk-off ghost (~15 min)
- **Cron coordination** — the existing ML daily build runs at 6:00am CT. Add a Press Row build at 5:30am CT. Verify the order.
- **Testing harness** — `tests/` directory pattern must support Press Row tests. Existing `tests/snapshot_test.py` pattern is a template.

## Alternative Approaches Considered

1. **Keep Press Row inline in `sections/pressrow.py` (no subpackage).** Rejected because it would add 3-5 minutes of LLM calls to every daily ML build. ML builds must stay fast. Subpackage with JSON artifact contract is the right boundary.

2. **Generate per-team artifacts instead of one shared artifact.** Rejected because the feed is inherently league-wide (writers from different teams interact). Per-team generation would 30× the LLM cost and fragment feuds across files.

3. **Move Press Row to a separate git repo.** Rejected because it would add deployment pipeline complexity for zero benefit. Same repo, subpackage structure captures all the separation-of-concerns benefits without the ops cost.

4. **Use only Ollama, skip Anthropic entirely.** Rejected because Unit 4's subjective smoke test is unlikely to pass without the editor pass. Sonnet for editor-only is the best quality-per-dollar lever.

5. **Skip Phase 2-4, ship only Comedy Pipeline + Obsessions.** Accepted as the minimum viable relaunch. Phase 1 alone is a shippable product. Phases 2-4 are compounding value that can ship iteratively over weeks.

6. **Build a real UI for inspecting state.** Rejected for v2 — keeps scope focused. State inspection via reading JSON files directly is acceptable. UI can come in v3.

## Phased Delivery

**Phase 0 (Infrastructure) — ~1-2 days.** Units 1-3 land together. Deliverable: the package exists, ML can render an artifact, no content yet. Verify: `python3 -m pressrow build` runs and exits 0, `python3 build.py --team cubs` still produces a valid page.

**Phase 1 (Quality Foundation) — ~2-3 days engineering + ~2 hours authoring.** Units 4-5 land together. Deliverable: the minimum viable relaunch. Tweets generate, they're noticeably funnier than v1, obsessions are authored. This is the decision gate — if Phase 1 output doesn't pass the subjective smoke test, pause and iterate on prompts before committing to Phases 2-4.

**Phase 2 (Continuity & Character) — ~3-4 days.** Units 6-7. Memory and beefs. Deliverable: feed develops arcs across days. Predictions callback, feuds advance. This is where return-visit behavior starts to materialize.

**Phase 3 (Universe Expansion) — ~2-3 days engineering + ~2 hours authoring.** Units 8-9. Letters and classifieds. Can run in parallel with Phase 2 since they have no dependency on memory or beefs. Deliverable: feed has texture beyond the main tweet stream.

**Phase 4 (Rare Moments) — ~1-2 days.** Unit 10. Scheduled events. Deliverable: breakdown arcs and ghost posts. This is the last layer — if earlier phases are shipped and working, Phase 4 is additive polish.

**Total: ~10-14 days of focused engineering.** Phase 1 alone is ~4-5 days and is a shippable product. Everything after Phase 1 is compounding.

## Success Metrics

- **Quality (subjective, required):** After Phase 1, JB reads a full day's Press Row output and finds it noticeably funnier than the shelved v1 prototype. If this fails, the project stops at Phase 1 for prompt iteration.
- **Return value (observable):** After Phase 2, a 7-day simulated run shows at least 3 instances of writers referencing their own previous tweets or predictions across days.
- **Interaction density (observable):** After Phase 2, ≥30% of tweets are replies or quote tweets (vs the v1 prototype's ~55% that were falsely labeled but not actually architected).
- **Structural integrity (measurable):** Zero builds where ML's daily briefing fails because of a Press Row generation error.
- **Content variety (measurable):** After Phase 3, each daily artifact contains ≥15 tweets + ≥3 letters + ≥3 classifieds + occasional events. No single build is dominated by one type.

## Documentation / Operational Notes

- Add a new entry to `docs/solutions/` after Phase 1 documenting the 3-pass Comedy Editor Pipeline pattern — this is a reusable institutional learning.
- Add `pressrow/README.md` explaining the subpackage structure, config files, state files, and the cron pattern. Should be enough for JB to resume work after a long gap.
- Update `CLAUDE.md` with a new section on the Press Row subpackage: entry point, config vs state distinction, the JSON artifact contract, the graceful degradation invariant.
- Update `deploy.py` — or at least verify it — that the `data/pressrow-*.json` glob matches existing patterns and the new files ship.
- Add a new entry in `docs/plans/` referencing this plan's execution status as it progresses (existing Morning Lineup pattern — see other `-plan.md` files).

## Sources & References

- **Origin document:** `docs/brainstorms/2026-04-12-press-row-v2-brainstorm.md` (brainstorm findings synthesizing 7 ideas into a unified system)
- **Ideation document:** `docs/ideation/2026-04-12-press-row-pop-ideation.md` (30 raw candidates → 7 survivors → brainstorm input)
- **Shelved prototype:** `docs/future/pressrow.py` (v1 code to port helpers from)
- **Prototype README:** `docs/future/pressrow-README.md` (describes v1 failure modes)
- **LLM pattern reference:** `sections/columnists.py:142-191` (Ollama/Anthropic fallback pattern to copy)
- **Section render contract:** `sections/columnists.py:261-295`
- **Games data shape:** `build.py:95-107` and `sections/around_league.py:35-55`
- **Persona schema:** `teams/cubs.json:59-81`
- **Build integration points:** `build.py:25, 666, 670-680, 740-752, 829-847`
- **CLAUDE.md guardrails:** `CLAUDE.md` (repo root) — section on section file rules
- **Institutional memory:** `~/.claude/projects/-home-tooyeezy/memory/feedback_rebuild_all_teams.md` and `feedback_derived_subscribers_timerless.md`
- **Architecture decision:** This session's conversation where JB and I discussed subpackage vs integrated layout and landed on the subpackage approach.
