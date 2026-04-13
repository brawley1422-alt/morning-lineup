---
title: "feat: Press Row Writer's Room — hybrid chat/swipe/card authoring tool"
type: feat
status: active
date: 2026-04-12
origin: (inline conversation — hybrid design in chat; ideation at docs/ideation/ pending)
companion: docs/plans/2026-04-12-001-feat-press-row-v2-plan.md
authoring_companion: docs/plans/2026-04-12-002-press-row-v2-authoring-work-plan.md
---

# Press Row Writer's Room — Implementation Plan

## Overview

Press Row Writer's Room is a local Python web app that eliminates the 4-hour JSON-editing grind required to complete the Press Row 2.0 authoring work (see `docs/plans/2026-04-12-002-press-row-v2-authoring-work-plan.md`). It's a single tool with three specialized modes — **Chat**, **Swipe**, and **Card** — each optimized for a different shape of authoring work. All three modes share one server, one design system, and write directly to `pressrow/config/*.json`.

**The target end-to-end authoring session:** JB sits down on a Saturday morning and completes all 5 authoring tasks (270 obsessions + 30 shadow personas + 20 recurring fans + 10 feuds + 1 walk-off ghost) in **~90-100 minutes instead of 4 hours**, with more authorial voice preserved than the Philosophy B "Invisible Tool" approach and less grinding friction than the Philosophy A "beautiful editor" approach.

The build is 7 implementation units across 4 phases totaling ~3.5 days of focused engineering. The tool is independent enough that it can ship BEFORE Press Row 2.0 itself begins — in fact, it should, because its whole purpose is to produce the config data Press Row 2.0 needs.

## Problem Frame

The Press Row 2.0 plan (`docs/plans/2026-04-12-001-feat-press-row-v2-plan.md`) requires substantial hand-authored data:
- 270 writer obsessions (3 per 90 characters)
- 30 shadow persona one-topic lurkers
- 15-20 recurring fictional fan characters
- 10 initial writer feuds with origin stories
- 1 Walk-Off Ghost persona

The authoring work plan (`docs/plans/2026-04-12-002-press-row-v2-authoring-work-plan.md`) estimates ~4 hours of focused writing across these five tasks. Without a tool, JB would edit five JSON files directly in a text editor — a genuinely grinding workflow for a creative task, especially for Task 1's 270 entries across 90 distinct voices.

The ideation pass earlier in today's session generated 30 candidates across three frames (flow-state UX, LLM leverage, removal/reframing) and surfaced a strategic fork: Philosophy A ("make the editor great") vs Philosophy B ("skip the editor"). Analysis of JB's working style (ideation-strong, verbal monologue preference, "describe what I want and Claude builds it" pattern) pointed toward Philosophy B — but a pure-B approach (Invisible Tool: overnight generation + Y/N approval) waters down authorial voice too much.

The hybrid design that emerged from the ideation conversation keeps Chat as the home base (conversational, matches JB's natural working style) for the design-shaped tasks (shadow personas, fans, feuds), uses a Swipe mode for the volume-shaped task (270 obsessions), and a ritualistic Card mode for the sacred one (Walk-Off Ghost). Different tasks, different shapes, different interfaces.

## Requirements Trace

- **R1. Chat mode must handle Tasks 2 (shadow personas), 3 (recurring fans), and 4 (feuds) conversationally.** From the hybrid design — these are relational/design-shaped tasks that benefit from iterative conversation rather than form-filling. Commits happen inline as Claude proposes and JB reacts.
- **R2. Swipe mode must handle Task 1 (270 obsessions) via batch pre-generation + curation.** From the hybrid design — the volume task inverts from authorship to curation. Overnight Sonnet run produces ~800 candidates; JB swipes through them in ~25 minutes.
- **R3. Card mode must handle Task 5 (Walk-Off Ghost) with focused, ritualistic UI, and be reusable for any one-off edit.** From the hybrid design — the ghost deserves bespoke interface; card mode also covers the "let me just edit this one entry by hand" case.
- **R4. All modes must write directly to `pressrow/config/*.json` via atomic writes.** From the architecture decision — state lives in the JSON files that Press Row 2.0 will consume. No separate database or localStorage.
- **R5. Progress status must be derived from the JSON files, not stored separately.** From state discipline — files are the single source of truth. Progress indicators scan files on load.
- **R6. Editorial dark aesthetic must match Morning Lineup palette.** From JB's preferences in auto-memory (`feedback_frontend_aesthetic.md`) and the Morning Lineup style at `style.css`. Same CSS variables, same fonts, same team color palette.
- **R7. Python stdlib only + vanilla JS, no frameworks.** From Morning Lineup's discipline (`CLAUDE.md` at repo root) — no pip dependencies, no build step.
- **R8. Total authoring session time must be ≤100 minutes end-to-end.** From the ideation target — the hybrid's promise is sub-2-hours, a 2.4× speedup from the 4-hour baseline.
- **R9. Anchor + Variants regeneration must preserve voice from user-anchored writes.** From the ideation hybrid survivor — when JB loves one obsession for a writer, the other two get regenerated in matching cadence. Taste compounds from JB outward.
- **R10. All three modes must share one server process, one design system, and one data layer.** From the "one tool, three rooms" framing — the modes are different routes, not different apps.
- **R11. The tool must be independent of Press Row 2.0 itself.** Because the Writer's Room ships *first* to produce the data Press Row 2.0 will consume. It cannot depend on any code inside `pressrow/` that doesn't exist yet.

## Scope Boundaries

**In scope:**
- New subpackage `pressrow_writer/` at the repo root
- Single-page web UI served from `pressrow_writer/static/`
- Three interactive modes: Chat, Swipe, Card
- One overnight batch script: `batch_obsessions.py` (pre-generates 800 candidates)
- LLM helper co-located in `pressrow_writer/llm.py` (ported from `sections/columnists.py:142-191` — deliberate duplication for independence from Press Row 2.0)
- Atomic writes to `pressrow/config/*.json` (the files Press Row 2.0 will read)
- CLI entry point: `python3 -m pressrow_writer` launches the server on `localhost:8787` and opens browser
- Progress status derived from files, rendered in a persistent header bar

**Non-goals:**
- Deployment — local-only, no hosting, no auth
- Collaboration — single user, no multi-writer sessions
- Real-time sync across browser tabs — one tab at a time
- Mobile-first design — mobile-friendly for Swipe mode specifically, but not a goal for Chat or Card
- Testing mode for Press Row 2.0's generated output — that's `python3 -m pressrow build` in the other plan
- Undo/redo beyond file-system git — you edit the file, you commit (literal commit, later, manually)
- Advanced text editor affordances (markdown preview, find/replace, etc.) — this is a form/chat tool
- Offline LLM fallback gymnastics — Sonnet is the primary path; if ANTHROPIC_API_KEY is unset, the batch generation and Anchor features degrade gracefully but the tool is primarily designed for Sonnet access
- Theming different from Morning Lineup — one visual style, period

**Explicitly deferred:**
- Voice-memo / Whisper input pipeline (R1 "Walking Mic" survivor from ideation) — deferred to v2; could be added as a fourth input mode later
- Saved chat transcripts / session history — the JSON files are the durable artifact; chat history lives in-browser only
- Cross-character callbacks and drift detection (L2, L6 from ideation rejections) — deferred; not needed for a one-time authoring session

## Context & Research

### Relevant Code and Patterns

- **LLM helper pattern:** `sections/columnists.py:142-191` defines `_try_ollama()` and `_try_anthropic()` with the exact timeout, error-handling, and retry behavior the Writer's Room should inherit. Port into `pressrow_writer/llm.py` as a single `call(prompt, *, prefer="anthropic", max_tokens=1024)` function. The rationale for preferring Anthropic first in the Writer's Room (vs Ollama-first in columnists) is that this is a one-time authoring session where quality matters more than speed — Sonnet is worth the cost.

- **Atomic JSON writes:** `sections/columnists.py:63-70` shows the `_save_cache()` pattern. For the Writer's Room, wrap it with atomic semantics: write to `{path}.tmp`, then `os.rename({path}.tmp, {path})`. This matters because the Writer's Room writes on every UI interaction and a crash mid-write would corrupt config files Press Row 2.0 depends on.

- **Morning Lineup CSS design system:** `style.css` at the repo root defines the full palette — `--ink: #0d0f14`, `--paper: #ece4d0`, `--gold: #c9a24a`, `--team-primary`, `--team-accent`, font stack (`--serif: "Playfair Display"`, `--cond: "Oswald"`, `--body: "Lora"`, `--mono: "IBM Plex Mono"`). Writer's Room's `pressrow_writer/static/styles.css` imports these values as-is and extends with mode-specific blocks. Do not invent new colors or fonts.

- **Team color palette:** `teams/{slug}.json` at lines ~8-13 (see `teams/cubs.json:8-13` for the canonical example) has the 4-color team palette. The Writer's Room loads these at startup to color team caps in the left rail (Chat mode) and card backgrounds (Card mode).

- **Persona config schema:** `teams/{slug}.json` at lines ~59-81 (`teams/cubs.json:59-81` for reference) shows the existing columnists array structure. The Writer's Room reads this to populate the character list. Task 1 (obsessions) extends each writer's entry with an `obsessions` field — schema matches the Press Row 2.0 plan's Unit 5.

- **Shelved prototype's rendering helpers:** `docs/future/pressrow.py` lines 28-55 have `_make_handle()`, `_make_initials()` — the Writer's Room needs these for handle generation when committing new personas. Copy into `pressrow_writer/util.py`.

- **Stdlib HTTP server pattern:** Python's `http.server.BaseHTTPRequestHandler` with custom route handling is the exact pattern needed. Reference implementation patterns at https://docs.python.org/3/library/http.server.html. Writer's Room server is ~100 lines of stdlib code routing GET/POST/PUT to handler functions.

- **Static HTML + vanilla JS pattern:** `scorecard/` subdirectory in Morning Lineup is the closest reference — `scorecard/app.js`, `scorecard/parser.js`, `scorecard/diamond.js` show vanilla JS module organization without a build step. The Writer's Room's `static/` directory mirrors this layout.

- **Auto-memory constraints:** `~/.claude/projects/-home-tooyeezy/memory/feedback_frontend_aesthetic.md` records JB's preference for bold editorial design over generic dashboards. The Writer's Room must feel like Morning Lineup, not like a generic admin panel. `~/.claude/projects/-home-tooyeezy/memory/feedback_screenshot_ui_loop.md` records the preference for iterative UI screenshots during development — plan to screenshot each mode as it's built.

### Institutional Learnings

- **The shelved Press Row v1 prototype (`docs/future/pressrow.py`) validated that vanilla JS + static HTML + Python stdlib server works for Morning Lineup-adjacent tools.** The Writer's Room adopts the same boundaries. No React, no Tailwind, no bundler.

- **Morning Lineup's discipline around deferred imports (`CLAUDE.md`: "Never `from build import ...` at module top")** applies here too. The Writer's Room should never import from `build.py` or `sections/*` at module top. Use deferred imports inside function bodies.

- **LLM quality degrades with bulk prompts.** From the earlier shelved v1 prototype testing in this session — qwen3:8b returned better JSON when `"format": "json"` was NOT set and the prompt was smaller and more focused. The Writer's Room's batch obsession generator should generate per-writer (one prompt per writer × 90 = 90 calls), not in one massive call. Per the brainstorm's "one-writer-at-a-time" infrastructure principle.

- **Atomic file writes matter for shared config files.** The Writer's Room writes to `pressrow/config/*.json` which Press Row 2.0 will later depend on. A crash mid-write would corrupt the config. Wrap all writes in the temp-file-then-rename pattern.

### External References

None required. All technical patterns have local precedents in Morning Lineup's codebase.

## Key Technical Decisions

1. **Subpackage independence, not shared code with Press Row 2.0.** The Writer's Room has its own `pressrow_writer/llm.py` that duplicates ~50 lines from `sections/columnists.py:142-191`. Rationale: the Writer's Room must ship before Press Row 2.0 begins, so it cannot depend on any code inside `pressrow/`. When Press Row 2.0 Phase 0 lands and creates `pressrow/llm.py`, the two copies will exist side-by-side. Dedupe later if it becomes a maintenance issue.

2. **One HTTP server, three modes as routes.** Not three separate apps. Rationale: modes share the same config files, same LLM helper, same design system. Keeping them in one server simplifies state derivation and avoids port juggling. Routes: `/` (mode selector, defaults to Chat), `/chat`, `/swipe`, `/card`, and API endpoints under `/api/*`.

3. **State is derived from files, not stored separately.** Every page load scans `pressrow/config/*.json` to compute progress. No database, no session storage, no localStorage for progress. Rationale: single source of truth means consistent state across modes, across browser tabs, across crashes. The JSON files ARE the state.

4. **Sonnet first, Ollama fallback.** `pressrow_writer/llm.py` defaults to `prefer="anthropic"` because quality is paramount for a one-time authoring session. Rationale: the Writer's Room is used for ~90 minutes per JB's workflow; Sonnet at ~$0.05-0.10 per session is acceptable. Ollama fallback exists for graceful degradation if the API key is missing.

5. **Overnight batch generation for Task 1, on-demand for the rest.** The batch obsession script runs once (taking ~10-20 minutes against Sonnet) and writes 800 candidates to `pressrow_writer/state/batch_obsessions.json`. The Swipe UI reads from this file. Chat mode prompts Claude on-demand for Tasks 2-4. Card mode calls Claude on-demand for Task 5.

6. **Progress status header in every mode.** A thin sticky header at the top of every page shows: `Task 1: 47/90 writers · Task 2: 12/30 personas · Task 3: 8/20 fans · Task 4: 3/10 feuds · Task 5: ⚪`. Rationale: the status acts as navigation between modes AND shows progress. Click a task to jump to its mode.

7. **Chat mode commits inline, not at the end.** When Claude proposes a shadow persona and JB accepts it, the commit happens immediately via an API call. Rationale: matches how JB actually works (react fast, move on) and avoids catastrophic-loss if the browser crashes mid-session.

8. **Swipe mode pre-computes assignments.** The batch script doesn't just generate 800 candidate obsessions — it also pre-assigns each candidate to its best-fit writer via the same LLM call that generates it. The UI just presents the writer-candidate pair; JB accepts or rejects. Rationale: avoids a separate embedding-similarity assignment step that adds complexity and dependencies.

9. **Card mode ritual is a visual commitment, not a technical feature.** The Walk-Off Ghost ritualistic UI is mostly CSS (full-screen black, one cursor, fade-in oracle text). Rationale: the "ceremony" is about how it *feels*, not what it *does* under the hood. Keep it simple technically.

10. **Shadow persona and recurring fan handles auto-generate from names.** JB types "Bullpen Hawk" → the handle `bullpen_hawk` is computed via the ported `_make_handle()` helper. Rationale: reduces typing, enforces consistency, matches the pattern from `docs/future/pressrow.py:28-35`.

## Open Questions

### Resolved During Planning

- **Where does the Writer's Room run?** On `localhost:8787` (same style as Press Row 2.0's assumed port). Single user, no auth, browser opens automatically via `webbrowser.open()` from `__main__.py`.

- **How does the Writer's Room know the LLM API key?** Same pattern as `sections/columnists.py:165-168` — reads `ANTHROPIC_API_KEY` from environment. If unset, Chat mode shows a warning banner and Anchor regeneration is disabled (Swipe mode still works on pre-generated candidates).

- **What happens if the batch obsession script hasn't run yet when JB opens Swipe mode?** The Swipe UI shows: "No candidate obsessions yet. Run `python3 -m pressrow_writer batch` to pre-generate." Clicking that message opens a terminal instruction modal with the exact command.

- **How are progress counts computed?** `pressrow_writer/progress.py` has one function per task that reads its config file and counts completed entries. Task 1 counts writers with non-empty `obsessions` arrays of length ≥2. Task 2 counts `shadow_personas` dict keys. Task 3 counts fans with non-empty names. Task 4 counts feuds in the `feuds` array. Task 5 checks if `cast.json` has a `walkoff_ghost` key with non-empty `voice`.

- **What file format does the batch obsession script output?** `pressrow_writer/state/batch_obsessions.json` structured as `[ {writer_handle, obsession_object, seen: false, accepted: false}, ... ]`. The UI updates `seen` and `accepted` as JB swipes.

- **How does the Anchor regeneration work mechanically?** When JB swipes right AND hits the 🪨 Anchor button on an obsession, the server: (1) commits that obsession to `pressrow/config/obsessions.json`, (2) calls Sonnet with the anchored obsession as a few-shot example plus the writer's voice sample, asking for 2 more in the same register, (3) skips all other unseen candidates for that writer in the batch (they've been replaced).

- **How does Chat mode persist across page reloads?** It doesn't. Chat history lives in-browser only. The durable output is the commits to `pressrow/config/*.json` — those persist. Rationale: chat history is conversation scaffolding, not canonical data.

### Deferred to Implementation

- **Exact Chat prompt wording for each task type.** Needs iterative tuning during Unit 3 implementation. Plan ships with rough templates that get refined in practice.

- **Swipe card animation feel.** The ideation talked about "card flip" and "slide in from random direction." Actual animation choices land during Unit 5 and require screenshot iteration.

- **Keyboard shortcut set.** Unit 7 polish. Will include at minimum: Y/N for swipe accept/reject, Enter to send chat, Esc to exit current mode.

- **Browser auto-open behavior.** `webbrowser.open()` may or may not work cleanly in all environments. Decide during Unit 1 whether to auto-open or just print the URL to stdout.

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

**Subpackage layout:**

```
morning-lineup/
├── pressrow_writer/                     # NEW subpackage (root-level, sibling to sections/)
│   ├── __init__.py
│   ├── __main__.py                      # CLI entry: `python3 -m pressrow_writer [serve|batch]`
│   ├── server.py                        # stdlib http.server with custom routing
│   ├── routes.py                        # API route handlers (GET/POST/PUT)
│   ├── llm.py                           # LLM helper (ported from sections/columnists.py:142-191)
│   ├── config_io.py                     # atomic writes to pressrow/config/*.json
│   ├── progress.py                      # derive task progress from config files
│   ├── util.py                          # _make_handle, _make_initials ported from docs/future/pressrow.py
│   ├── batch_obsessions.py              # overnight script: 90 writers × ~9 candidates each
│   ├── prompts/                         # prompt templates (stdlib f-strings, no framework)
│   │   ├── __init__.py
│   │   ├── chat_shadow_personas.py
│   │   ├── chat_recurring_fans.py
│   │   ├── chat_feuds.py
│   │   ├── batch_obsessions.py
│   │   ├── anchor_variants.py
│   │   └── card_ghost.py
│   ├── state/                           # runtime state (gitignored by default)
│   │   └── batch_obsessions.json        # pre-generated candidates for Swipe
│   └── static/
│       ├── index.html                   # single-page shell with mode switcher
│       ├── styles.css                   # imports Morning Lineup vars, adds mode styles
│       ├── app.js                       # mode switching + shared state + progress header
│       ├── chat.js                      # chat mode UI + API calls
│       ├── swipe.js                     # swipe mode UI + gesture handling
│       └── card.js                      # card mode UI + ghost ritual
```

**Daily flow (the target session):**

```
The night before (or any time before the session):
  python3 -m pressrow_writer batch
    ├── Loads all 90 writers from teams/*.json columnists arrays
    ├── For each writer, calls Sonnet with a per-writer prompt for ~9 obsession candidates
    ├── Writes all candidates to pressrow_writer/state/batch_obsessions.json
    └── Reports: "800 candidates ready for swipe. Launch with `python3 -m pressrow_writer serve`."

Saturday morning:
  python3 -m pressrow_writer serve
    ├── Starts http.server on localhost:8787
    ├── Opens browser to http://localhost:8787
    └── Shell shows progress header: "0/5 tasks complete"

  JB navigates modes freely:
    Chat mode  → Tasks 2 (shadow personas), 3 (recurring fans), 4 (feuds)
    Swipe mode → Task 1 (obsessions)
    Card mode  → Task 5 (ghost) and ad-hoc edits
```

**Mode interaction diagram:**

```
┌─────────────────────────────────────────────────────────────┐
│                    Progress Header (sticky)                  │
│  T1: 47/90  T2: 12/30  T3: 8/20  T4: 3/10  T5: ⚪  ← click to switch mode
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Mode content area (Chat | Swipe | Card)                   │
│                                                              │
│   Chat:  scrollable message list + composer at bottom       │
│   Swipe: full-screen card stack + swipe gestures            │
│   Card:  black-page ritual + side oracle                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘

All modes:
  ↓ user actions
  ↓
  POST /api/{mode}/commit   → config_io.atomic_write() → pressrow/config/*.json
  ↓
  GET /api/progress          ← progress.py scans files ← pressrow/config/*.json
  ↓
  header status updates, progress bar re-renders
```

**API route table (minimum viable):**

| Method | Route | Purpose |
|---|---|---|
| GET | `/` | Mode selector (defaults to Chat) |
| GET | `/chat` | Chat mode page |
| GET | `/swipe` | Swipe mode page |
| GET | `/card` | Card mode page |
| GET | `/api/progress` | Returns task completion counts as JSON |
| GET | `/api/writers` | Returns list of 90 writers from teams/*.json |
| POST | `/api/chat/message` | Sends a chat message to Claude, returns response |
| POST | `/api/chat/commit/shadow` | Commits a shadow persona from chat |
| POST | `/api/chat/commit/fan` | Commits a recurring fan from chat |
| POST | `/api/chat/commit/feud` | Commits a feud from chat |
| GET | `/api/swipe/next` | Returns next unseen candidate for a writer |
| POST | `/api/swipe/accept` | Accepts a candidate (commits to obsessions.json) |
| POST | `/api/swipe/reject` | Marks a candidate seen, no commit |
| POST | `/api/swipe/anchor` | Commits + regenerates other 2 for same writer |
| POST | `/api/card/ghost/commit` | Commits the ghost persona |
| GET | `/api/card/character/{handle}` | Returns character data for card mode editing |

**The one-file-is-state invariant:**

```
Single source of truth (Press Row 2.0 will read these):
  pressrow/config/obsessions.json          ← Task 1 output
  pressrow/config/shadow_personas.json     ← Task 2 output
  pressrow/config/recurring_fans.json      ← Task 3 output
  pressrow/config/relationships.json       ← Task 4 output
  pressrow/config/cast.json                ← Task 5 output

Writer's Room runtime state (not shared with Press Row 2.0):
  pressrow_writer/state/batch_obsessions.json  ← pre-generated candidates

No other persistent state. No database. No localStorage for canonical data.
```

**Dependency graph across implementation units:**

```
Phase 0 (Scaffold)
  Unit 1 (subpackage + server + static shell) ──┐
                                                  │
Phase 1 (Chat Mode)                              │
  Unit 2 (chat UI + API routes + commits) ◄──── Unit 1
  Unit 3 (task-specific chat prompts) ◄──────── Unit 2

Phase 2 (Swipe Mode)
  Unit 4 (batch obsession generator) ◄────────── Unit 1
  Unit 5 (swipe UI + anchor flow) ◄───────────── Units 1, 4

Phase 3 (Card Mode)
  Unit 6 (card UI + ghost conjuring) ◄────────── Unit 1

Phase 4 (Polish)
  Unit 7 (progress derivation + mode sync) ◄──── Units 2, 3, 5, 6
```

Units 2, 4, and 6 can run in parallel with different modes — Chat, Batch/Swipe, and Card are independent from each other. The dependency is only on the scaffold (Unit 1). This means the build can parallelize once Unit 1 lands, or ship incrementally (Chat first → Swipe next → Card last, or any order).

## Implementation Units

### Phase 0: Scaffold

- [ ] **Unit 1: Subpackage scaffold, HTTP server, and static shell**

**Goal:** Create the `pressrow_writer/` subpackage with a minimal HTTP server, the CLI entry point, and a static HTML shell that loads the mode-switcher UI. At the end of this unit, `python3 -m pressrow_writer serve` starts a server, opens the browser, and shows an empty mode selector — no working modes yet, but the skeleton is alive.

**Requirements:** R7, R10, R11

**Dependencies:** None

**Files:**
- Create: `pressrow_writer/__init__.py`
- Create: `pressrow_writer/__main__.py`
- Create: `pressrow_writer/server.py`
- Create: `pressrow_writer/routes.py`
- Create: `pressrow_writer/config_io.py`
- Create: `pressrow_writer/util.py` (port `_make_handle`, `_make_initials` from `docs/future/pressrow.py:28-55`)
- Create: `pressrow_writer/llm.py` (port `_try_ollama`, `_try_anthropic` from `sections/columnists.py:142-191`)
- Create: `pressrow_writer/static/index.html`
- Create: `pressrow_writer/static/styles.css`
- Create: `pressrow_writer/static/app.js`
- Create: `pressrow_writer/state/.gitkeep`
- Create: `tests/test_pressrow_writer_util.py`
- Create: `tests/test_pressrow_writer_server.py`
- Create: `tests/test_pressrow_writer_llm.py` (mocked HTTP)

**Approach:**
- The CLI entry in `__main__.py` supports two subcommands: `serve` (default) and `batch`. `serve` starts the HTTP server. `batch` is a stub that logs "not implemented" (Unit 4 fills it in).
- `server.py` subclasses `http.server.BaseHTTPRequestHandler` with a router that matches path prefixes to handler functions from `routes.py`. Static files from `pressrow_writer/static/` are served for `/static/*` paths. The root `/` returns `index.html`.
- `config_io.py` exposes `atomic_write(path, data)` and `read_json(path, default)`. Atomic write uses the temp-file-then-rename pattern from `sections/columnists.py:63-70` wrapped in an `os.rename()` call.
- `util.py` ports handle generation verbatim.
- `llm.py` is a ~50 line file with one public function: `call(prompt, *, max_tokens=1024, prefer="anthropic", timeout_anthropic=60, timeout_ollama=120)`. Reads `ANTHROPIC_API_KEY` from env. Returns a string or empty string on failure.
- `index.html` is a shell with a sticky header for progress status, a main content area, and three buttons to switch modes: Chat | Swipe | Card. Clicking a button swaps the content area via JS (no page reload). In Unit 1, all three modes show a "coming soon" placeholder.
- `styles.css` imports Morning Lineup's CSS variables by copying them from `style.css` lines 1-50 (the custom-properties block). Adds Writer's Room-specific classes prefixed with `wr-` to avoid collisions.
- `app.js` handles mode switching (show/hide content blocks) and fetches `/api/progress` on load to populate the header status.
- The CLI uses `webbrowser.open()` to launch `http://localhost:8787` after the server is listening. If it fails, print the URL to stdout.

**Patterns to follow:**
- `sections/columnists.py:142-191` for the LLM helper pattern (verbatim port, adjust defaults for Anthropic-first).
- `docs/future/pressrow.py:28-55` for util helpers (verbatim port).
- `style.css` (lines 1-50 approximately) for the CSS variable block to import.
- `scorecard/app.js` for the vanilla JS module organization pattern (no framework, no build step).
- Python `http.server` stdlib docs for the server pattern.

**Test scenarios:**
- Happy path: `pressrow_writer.util.make_handle("Bullpen Hawk")` returns `"bullpen_hawk"`.
- Happy path: `pressrow_writer.util.make_initials("Marge from Toledo")` returns `"MT"`.
- Happy path: `pressrow_writer.llm.call(prompt)` returns a non-empty string when Anthropic is mocked to return a valid response.
- Happy path: `pressrow_writer.llm.call(prompt)` falls back to Ollama when Anthropic fails.
- Error path: `pressrow_writer.llm.call(prompt)` returns `""` when both providers fail.
- Happy path: `pressrow_writer.config_io.atomic_write(path, data)` writes the file.
- Integration: Atomic write followed by a simulated crash (exception between temp-write and rename) leaves the original file untouched.
- Happy path: Starting the server and GETting `/` returns 200 with HTML content.
- Happy path: GETting `/static/app.js` returns the JS file.
- Happy path: GETting `/api/progress` returns valid JSON with all 5 task counts at 0.
- Edge case: GETting a non-existent route returns 404.
- Happy path: `python3 -m pressrow_writer serve` starts the server, prints the URL, and exits cleanly on Ctrl+C.

**Verification:**
- `python3 -m pressrow_writer serve` starts without error.
- Opening `http://localhost:8787` in a browser shows a page with the Morning Lineup palette, a progress header at 0/5, and three mode-switch buttons.
- Clicking each mode button swaps the content area to a "coming soon" placeholder.
- Screenshot the shell and verify the aesthetic matches Morning Lineup (dark ink background, cream text, gold accents).

---

### Phase 1: Chat Mode

- [ ] **Unit 2: Chat UI + API routes + commit pipeline**

**Goal:** Build the Chat mode UI and its backing API routes. At the end of this unit, JB can have a conversation with Claude in the browser, and conversations produce commits to `pressrow/config/*.json` files. The task-specific prompt templates are placeholders; Unit 3 replaces them with production-quality prompts.

**Requirements:** R1, R4, R6, R7, R10

**Dependencies:** Unit 1

**Files:**
- Create: `pressrow_writer/static/chat.js`
- Modify: `pressrow_writer/static/index.html` (replace Chat placeholder with full Chat UI markup)
- Modify: `pressrow_writer/static/styles.css` (append `.wr-chat-*` styles)
- Modify: `pressrow_writer/routes.py` (add `/api/chat/message`, `/api/chat/commit/*`)
- Create: `pressrow_writer/prompts/__init__.py`
- Create: `pressrow_writer/prompts/chat_shadow_personas.py` (stub — real prompts in Unit 3)
- Create: `pressrow_writer/prompts/chat_recurring_fans.py` (stub)
- Create: `pressrow_writer/prompts/chat_feuds.py` (stub)
- Create: `tests/test_pressrow_writer_chat.py`

**Approach:**
- Chat UI: scrollable message list (JB's messages right-aligned, Claude's left-aligned, both in the Morning Lineup palette), a composer at the bottom with a text field and Send button, and a task-selector dropdown at the top ("Shadow Personas / Recurring Fans / Feuds"). Selecting a task loads that prompt template for the session.
- When JB sends a message, the UI POSTs to `/api/chat/message` with `{task, history, user_message}`. The server constructs a full prompt from the task template + history, calls `llm.call()`, returns the response. The UI appends Claude's message to the chat.
- When Claude's response contains a committable entry (a shadow persona, fan, or feud), the UI shows inline action buttons: ✓ Commit / ✗ Discard / ✏ Edit. Clicking ✓ sends a POST to the appropriate commit endpoint.
- Commit endpoints do one thing: atomic-write the new entry into the target config file. If the target file doesn't exist, create it with a valid empty structure (e.g., `{}` for shadow personas, `[]` for fans).
- "Committable entry" detection: the chat_*.py prompt templates instruct Claude to always return committable entries in a fenced JSON block. The UI regex-scans for ```` ```json ... ``` ```` blocks and renders them as action cards.
- Commit endpoints also recompute progress and return updated counts so the header can re-render.
- No chat history persistence beyond the current browser session — history is in-memory JS state only.

**Patterns to follow:**
- `sections/columnists.py:194-220` for the LLM call + cache-commit flow pattern.
- `scorecard/panels.js` for the vanilla JS UI patterns (show/hide sections, fetch API calls, DOM updates without a framework).
- `docs/future/pressrow.py:260-360` for the JSON-in-markdown extraction pattern.

**Test scenarios:**
- Happy path: POST `/api/chat/message` with a valid task + history returns a 200 with Claude's response text.
- Happy path: POST `/api/chat/commit/shadow` with a valid persona body writes to `pressrow/config/shadow_personas.json` atomically.
- Happy path: Committing a shadow persona when the file doesn't exist creates it with valid structure.
- Happy path: Committing a second shadow persona to the same team replaces the first (or extends — decide during impl).
- Edge case: POST `/api/chat/commit/shadow` with malformed body returns 400.
- Edge case: POST `/api/chat/commit/fan` with a name that already exists returns 409 Conflict with the existing entry.
- Integration: End-to-end chat session in the browser — type a message, see Claude's response, click Commit, verify the file was written.
- Integration: Opening the file in another process during a commit (race) is safe — atomic write prevents partial reads.
- Integration: Progress header updates after a commit without a page reload.

**Verification:**
- Screenshot the Chat mode showing a multi-turn conversation with committable actions.
- Manually commit a test shadow persona and verify the JSON file was written correctly.
- Check that the progress header increments from `T2: 0/30` to `T2: 1/30` after the commit.
- Verify that a crash simulated mid-commit leaves the original file intact.

---

- [ ] **Unit 3: Task-specific chat prompt templates**

**Goal:** Replace the stub chat prompt templates with production-quality prompts that produce good-quality shadow personas, fans, and feuds in the Morning Lineup voice. This unit is mostly prompt engineering + iterative tuning.

**Requirements:** R1, R6

**Dependencies:** Unit 2

**Files:**
- Modify: `pressrow_writer/prompts/chat_shadow_personas.py`
- Modify: `pressrow_writer/prompts/chat_recurring_fans.py`
- Modify: `pressrow_writer/prompts/chat_feuds.py`
- Create: `tests/fixtures/chat_shadow_persona_example.json`
- Create: `tests/fixtures/chat_recurring_fan_example.json`
- Create: `tests/fixtures/chat_feud_example.json`

**Approach:**
- Each prompt template is a Python function `build(history, user_message, existing_entries)` returning a string. The function injects:
  - The task context: "You are casting shadow personas for a fictional MLB beat-writer universe called Press Row..."
  - The Morning Lineup voice and tone guide (editorial, dark, specific, Midwestern-when-relevant, never generic)
  - The schema constraints (required fields, max lengths, handle format)
  - Examples of good output (2-3 from the authoring work plan at `docs/plans/2026-04-12-002-press-row-v2-authoring-work-plan.md`)
  - Existing entries so Claude can avoid duplicates
  - The conversation history + user's current message
- The prompt explicitly instructs Claude to always return committable JSON blocks in ```` ```json ... ``` ```` fences so the UI can parse them.
- Shadow personas: 1 entry per response (don't batch — JB wants to react one at a time). Schema from Task 2 spec.
- Recurring fans: 1 entry per response. Schema from Task 3 spec with required voice + starting_state + post_probability.
- Feuds: 1 entry per response, but with an emphasis on the origin story being specific (2 sentences of action + reaction).
- Each prompt also has a "brainstorm mode" variant: if JB's message is empty or says "suggest some," Claude pitches a fresh candidate; if JB's message gives direction, Claude responds to the direction.
- Tone guardrails baked into every prompt: no real player tragedies, no heavy themes, keep it sitcom-warm, specific over generic.

**Patterns to follow:**
- `sections/columnists.py:102-135` for the prompt-building pattern with persona context.
- `docs/plans/2026-04-12-002-press-row-v2-authoring-work-plan.md` (Tasks 2-4 sections) for the schema, example entries, and tone guidance.

**Test scenarios:**
- Happy path: `chat_shadow_personas.build(history=[], msg="pitch me a Pirates persona", existing=[])` produces a prompt that contains the schema, at least one example, and the user's request.
- Happy path: Sending that prompt to a mocked LLM returning a valid JSON block produces a parseable committable entry.
- Edge case: The prompt includes existing entries as "already taken" context to prevent duplicates.
- Edge case: A prompt with a very long history gets truncated to the last N turns to stay within context limits.
- Integration: Manual test — run a real Sonnet call with each prompt and grade the output quality subjectively. Iterate on prompts until output feels right.

**Verification:**
- A manual JB smoke test: spend 10 minutes with each task in Chat mode and subjectively grade the output quality. "Does this sound like Morning Lineup?" If no, tune prompts. Target: 80% of Claude's pitches are good enough to commit without edits.

---

### Phase 2: Swipe Mode

- [ ] **Unit 4: Batch obsession generator**

**Goal:** Build the overnight batch script that pre-generates ~9 candidate obsessions per writer (810 total) and writes them to `pressrow_writer/state/batch_obsessions.json` for Swipe mode to consume.

**Requirements:** R2, R7

**Dependencies:** Unit 1

**Files:**
- Create: `pressrow_writer/batch_obsessions.py`
- Create: `pressrow_writer/prompts/batch_obsessions.py`
- Modify: `pressrow_writer/__main__.py` (wire `batch` subcommand to `batch_obsessions.main()`)
- Create: `tests/test_pressrow_writer_batch.py`

**Approach:**
- The batch script loads all 90 writers from `teams/*.json` (looking at the `columnists` array in each team config).
- For each writer, it calls Sonnet once with a per-writer prompt: "You are seeding obsession candidates for {writer name}, {role}. Their voice sample: {voice_sample}. Their backstory: {backstory}. Their signature phrase: {phrase}. Generate exactly 9 candidate obsessions, each as a JSON object with {topic, angle, trigger_phrases}. Make them specific, petty, in-character. Return as a JSON array."
- The script iterates sequentially (not in parallel — rate-limit-friendly and easier to debug), shows progress output as it goes ("45/90 writers done..."), and catches individual failures without stopping the run.
- All candidates are written to `pressrow_writer/state/batch_obsessions.json` structured as:
  ```json
  [
    { "writer_handle": "tony_gedeski", "candidate": {topic, angle, trigger_phrases},
      "seen": false, "accepted": false },
    ...
  ]
  ```
- Total Sonnet cost estimate: 90 calls × ~600 input + 800 output = ~126k tokens = ~$0.30 at Sonnet 4 pricing. Acceptable one-time cost.
- Total runtime: ~15-25 minutes for 90 sequential calls.
- The `batch` subcommand in `__main__.py` prints a progress bar and a completion summary: "810 candidates generated. Run `python3 -m pressrow_writer serve` to swipe."

**Patterns to follow:**
- `sections/columnists.py:194-220` for the per-persona LLM call + save pattern.
- `docs/plans/2026-04-12-001-feat-press-row-v2-plan.md` Unit 5 (Writer Obsessions config) for the seed script approach — the Writer's Room's `batch_obsessions.py` is essentially the same script with a different output shape.

**Test scenarios:**
- Happy path: `batch_obsessions.main()` with a mocked LLM returning valid JSON produces a file with 810 entries.
- Edge case: One writer's LLM call fails — the script continues with the other 89 and reports the failure in the summary.
- Edge case: Running the script twice doesn't duplicate entries — the second run either skips existing candidates or prompts for overwrite.
- Integration: End-to-end run against a mocked Sonnet producing realistic-shape responses yields a file ready for Swipe mode to consume.

**Verification:**
- `python3 -m pressrow_writer batch` runs to completion.
- `pressrow_writer/state/batch_obsessions.json` contains ~810 well-formed entries.
- Spot-check 5 random entries and confirm they're in-voice for their writer (subjective).

---

- [ ] **Unit 5: Swipe UI + Anchor regeneration**

**Goal:** Build the Swipe mode UI — a full-screen card stack with gesture-based swipe-right / swipe-left / Anchor interactions. At the end of this unit, JB can blow through 800 candidate obsessions in ~25 minutes.

**Requirements:** R2, R4, R6, R9, R10

**Dependencies:** Units 1, 4

**Files:**
- Create: `pressrow_writer/static/swipe.js`
- Modify: `pressrow_writer/static/index.html` (replace Swipe placeholder with full UI)
- Modify: `pressrow_writer/static/styles.css` (append `.wr-swipe-*` styles)
- Modify: `pressrow_writer/routes.py` (add `/api/swipe/*` endpoints)
- Create: `pressrow_writer/prompts/anchor_variants.py`
- Create: `tests/test_pressrow_writer_swipe.py`

**Approach:**
- Swipe UI is a full-screen overlay when the user switches to Swipe mode. Big card in the center showing: writer's team cap (using the `--team-primary` color), writer name, writer's voice sample (small italic text), and ONE candidate obsession displayed large. Below: three big buttons — ✗ Reject / ✓ Accept / 🪨 Anchor.
- Keyboard shortcuts: Left arrow = reject, Right arrow = accept, Space = anchor.
- On accept: POST `/api/swipe/accept` with the candidate ID. Server appends to `pressrow/config/obsessions.json` (atomic write), marks the candidate `accepted: true`, `seen: true` in `state/batch_obsessions.json`, and returns the next unseen candidate.
- On reject: POST `/api/swipe/reject`, mark `seen: true`, return next.
- On anchor: POST `/api/swipe/anchor` with the candidate. Server: (1) commits the candidate to obsessions.json, (2) calls Sonnet with the Anchor + Variants prompt asking for 2 more obsessions in the same voice/cadence, (3) commits those 2 as well, (4) marks ALL other unseen candidates for that writer as `seen: true, accepted: false` (they're replaced by the anchor family), (5) returns the next candidate for a DIFFERENT writer.
- Progress indicator: "Writer 47/90 · Candidate 3/9 for this writer" in the top corner. Shows remaining unseen count for the current writer.
- Card animations: slide out to the appropriate side on swipe, slide in from the opposite direction for the next card. Pure CSS transitions.
- When the deck is empty (all candidates seen or all writers have ≥2 obsessions accepted), show a completion screen: "Task 1 complete: 90/90 writers obsessed. 🎯"

**Patterns to follow:**
- `scorecard/diamond.js` for vanilla JS DOM animation patterns.
- `docs/future/pressrow.py:260-360` for JSON parsing/validation on the Anchor response.

**Test scenarios:**
- Happy path: GET `/api/swipe/next` returns the first unseen candidate when the state file has data.
- Happy path: POST `/api/swipe/accept` with a candidate ID commits it to `pressrow/config/obsessions.json` and marks the candidate seen.
- Happy path: POST `/api/swipe/anchor` with a candidate generates 2 more obsessions and commits all 3 to the writer's entry.
- Edge case: POST `/api/swipe/accept` when the obsessions file doesn't exist creates it with valid structure.
- Edge case: Anchoring a writer who already has 3 obsessions in their file — decide: replace all 3? Keep existing? Plan: confirm with a modal ("This writer already has obsessions. Replace them?"), default to replace.
- Edge case: GET `/api/swipe/next` when the deck is empty returns a completion signal.
- Integration: Full browser test — swipe through 10 candidates, verify the progress counter updates and the obsessions file grows.
- Integration: Anchor test — click Anchor, verify 3 obsessions commit and other candidates for that writer are marked seen.

**Verification:**
- Screenshot the Swipe UI in the Morning Lineup aesthetic.
- Manual swipe session: clear 20 candidates in <1 minute (averaging 3 seconds each).
- Anchor a writer and verify the committed 3 obsessions are in matching voice (subjective).
- Progress header shows `T1: 5/90 writers obsessed` after accepting 5 distinct writers.

---

### Phase 3: Card Mode

- [ ] **Unit 6: Card mode UI + Walk-Off Ghost ritual**

**Goal:** Build the Card mode — a full-screen focused editor for individual entries, with a special ritualistic sub-mode for the Walk-Off Ghost. Card mode is also reusable for editing any single entry by hand after the fact.

**Requirements:** R3, R4, R6, R10

**Dependencies:** Unit 1

**Files:**
- Create: `pressrow_writer/static/card.js`
- Modify: `pressrow_writer/static/index.html` (replace Card placeholder with full UI)
- Modify: `pressrow_writer/static/styles.css` (append `.wr-card-*` and `.wr-ghost-*` styles)
- Modify: `pressrow_writer/routes.py` (add `/api/card/*` endpoints)
- Create: `pressrow_writer/prompts/card_ghost.py`
- Create: `tests/test_pressrow_writer_card.py`

**Approach:**
- Card mode has two sub-modes:
  1. **Ghost Mode** — accessed via the Card tab's "Walk-Off Ghost" option. Shows a full-screen black page with one centered text input for the ghost's voice description. On the right side, a thin "oracle" panel shows cryptic fragments suggested by Claude (one at a time, low temperature, one sentence each). JB can accept/reject each fragment into the growing voice block. When JB hits save, the ghost commits to `pressrow/config/cast.json` under the `walkoff_ghost` key.
  2. **Character Edit Mode** — accessed via any writer or entry's "Edit as Card" link (deferred: not required for v1, but the structure supports it). Shows a full-screen card with the entry's existing fields editable. Save commits back to the appropriate config file.
- Ghost oracle mechanics: Claude is called with `temperature=0.4`, `max_tokens=40`, one call per fragment. Prompt: "You are composing the voice of the Walk-Off Ghost — a cryptic MLB persona that posts only after dramatic game endings, never names players, always mentions one physical detail of the venue. Give ONE new cryptic sentence in that voice. Max 20 words."
- Voice sample builder: as JB accepts fragments, they're appended to a `sample_tweets` array. Target: 3-5 samples before save.
- Save flow: POST `/api/card/ghost/commit` with `{name, handle, voice, sample_tweets}`. Server writes to `pressrow/config/cast.json` atomically under `walkoff_ghost`.
- Character edit mode (if built in v1): POST `/api/card/character/{handle}` to fetch, PUT to save. Card UI is the same editor style, just populated with the character's current fields.
- Styling: `.wr-card-mode` is a full-screen overlay. `.wr-ghost-mode` has extra treatment — true-black background, only text, a candle-flicker CSS animation on the cursor, fade-in for each new oracle line. Matches the "ritual" framing from the ideation.

**Patterns to follow:**
- `docs/future/pressrow.py:407-458` for the rendering helper pattern (though Card mode renders differently — fewer elements, bigger typography).
- `style.css` existing sections with full-screen overlays (there may not be one; treat as a new pattern).

**Test scenarios:**
- Happy path: GET `/api/card/ghost` returns the current ghost if committed, else empty state.
- Happy path: POST `/api/card/ghost/commit` writes to `pressrow/config/cast.json` under `walkoff_ghost`.
- Happy path: Starting the ghost ritual with no existing ghost, accepting 3 oracle fragments, and committing produces a valid cast.json entry.
- Edge case: POST commit with empty `voice` field returns 400.
- Edge case: Re-committing the ghost overwrites the previous version.
- Integration: Full browser flow — open Card mode, navigate to Ghost, accept 5 fragments, save, verify cast.json.
- Integration: Progress header updates from `T5: ⚪` to `T5: ✓`.

**Verification:**
- Screenshot the Ghost mode with visible cursor flicker and accepted fragments.
- Subjective test: does the oracle text actually feel cryptic and in-voice? Tune the prompt if not.
- `pressrow/config/cast.json` contains a valid `walkoff_ghost` entry after the session.

---

### Phase 4: Polish

- [ ] **Unit 7: Progress derivation, mode sync, and session-end polish**

**Goal:** Final polish pass. Implement the `pressrow_writer/progress.py` that computes task completion counts from file contents. Wire the progress header to update after every commit. Add keyboard shortcuts. Add a completion celebration.

**Requirements:** R5, R8

**Dependencies:** Units 2, 3, 5, 6

**Files:**
- Create: `pressrow_writer/progress.py`
- Modify: `pressrow_writer/routes.py` (ensure every commit endpoint returns updated progress)
- Modify: `pressrow_writer/static/app.js` (progress header updates, global keyboard shortcuts, completion screen)
- Modify: `pressrow_writer/static/styles.css` (progress bar styles, completion screen)
- Create: `tests/test_pressrow_writer_progress.py`

**Approach:**
- `progress.py` exposes one function: `compute()` returning a dict: `{task1: {done, total}, task2: {done, total}, ...}`. Each task has its own derivation function that reads the relevant config file and counts completed entries.
- Task 1 (obsessions): count writers whose obsessions array has length ≥ 2. Total: 90.
- Task 2 (shadow personas): count keys in `shadow_personas.json`. Total: 30.
- Task 3 (recurring fans): count entries in `recurring_fans.json` with non-empty `name`. Total target: 15 (configurable).
- Task 4 (feuds): count entries in `relationships.json` under `feuds`. Total: 10.
- Task 5 (ghost): boolean — does `cast.json` have a `walkoff_ghost` with non-empty `voice`?
- Every commit endpoint returns `{committed: true, progress: {...}}` so the UI can re-render the header without an extra fetch.
- Global keyboard shortcuts: `1` = Chat, `2` = Swipe, `3` = Card, `Esc` = back to mode selector.
- When all 5 tasks complete, show a full-screen celebration: big "Press Row Writer's Room complete. 🎯" with a subtle Morning Lineup header and the total session time. No confetti, no modals, just a moment.

**Patterns to follow:**
- `sections/columnists.py` for JSON file reads with graceful defaults.
- `scorecard/app.js` for global event listener patterns.

**Test scenarios:**
- Happy path: `progress.compute()` with empty files returns all zeros.
- Happy path: After committing 5 shadow personas, `progress.compute()` returns `task2: {done: 5, total: 30}`.
- Edge case: `progress.compute()` with a missing file returns 0 for that task (doesn't raise).
- Edge case: `progress.compute()` with a malformed file returns 0 for that task and logs a warning.
- Happy path: POST to any commit endpoint returns the updated progress in the response body.
- Happy path: After all 5 tasks complete, the celebration screen appears.
- Integration: Full session simulation — start at 0/5, commit entries across all tasks, verify final state is 5/5 and celebration fires.

**Verification:**
- Full end-to-end session manual test: start from 0/5, complete all tasks using all three modes, reach 5/5. Total session time should be ≤100 minutes (R8 target).
- Screenshot the completion screen.

---

## System-Wide Impact

- **Interaction graph:**
  - The Writer's Room writes to `pressrow/config/*.json` which Press Row 2.0 will later read. This creates a build-order dependency: Writer's Room must run (and produce data) before Press Row 2.0 Phase 0 needs it.
  - `sections/pressrow.py` (which doesn't exist yet — it's in Press Row 2.0 Phase 0) is not affected by Writer's Room at all. The Writer's Room is pre-Press-Row-2.0 tooling.
  - No existing Morning Lineup code is modified. The Writer's Room is a new subpackage with zero overlap.

- **Error propagation:**
  - LLM failures fall back to Ollama (if available) or return empty. UI shows a retry button.
  - Commit failures (e.g., file permission errors) return 500 with a user-visible message.
  - Browser crashes lose in-memory chat history but preserve all committed entries.
  - Server crashes require a restart but lose no data (all state is in files).

- **State lifecycle risks:**
  - Two browser tabs editing simultaneously could cause overwrites. Mitigation for v1: single-tab only (document the assumption; don't build file-locking).
  - Mid-commit crashes are safe via atomic writes (temp file + rename).
  - `pressrow_writer/state/batch_obsessions.json` can accumulate over multiple batch runs. Each run overwrites the file fully (no merging); JB is expected to run batch once and then swipe through it.

- **API surface parity:**
  - No existing APIs change. The Writer's Room is purely additive.
  - The `pressrow/config/*.json` schemas are the contract — they must match what Press Row 2.0's `config_loader.py` will expect. Schema is defined by the authoring work plan at `docs/plans/2026-04-12-002-press-row-v2-authoring-work-plan.md` for each task.

- **Integration coverage:**
  - Full browser-based end-to-end testing of each mode.
  - Cross-mode state verification (commit in Chat, see progress update in Swipe, etc.).
  - Atomic write safety under simulated crash.

- **Unchanged invariants:**
  - Morning Lineup's `build.py`, `sections/*`, `deploy.py`, `evening.py` are all untouched.
  - Morning Lineup's existing tests (`tests/snapshot_test.py`) continue to pass — the Writer's Room adds new files, doesn't modify existing ones.
  - Morning Lineup's deploy pipeline is unaffected — Writer's Room is a local-only tool; `deploy.py` does not ship `pressrow_writer/` or `pressrow_writer/state/*`.

## Risks & Dependencies

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LLM output quality is not good enough for Chat mode's task templates | Medium | High | Unit 3 includes manual iterative tuning. Budget a full afternoon for prompt engineering if initial output is weak. |
| Batch obsession script takes longer than 25 minutes | Medium | Low | Sequential calls are easy to parallelize with `concurrent.futures` if needed. Start sequential, measure, optimize only if required. |
| Swipe animations feel janky on JB's hardware | Low | Medium | Pure CSS transitions are reliable. Test on the target rig (ROG Strix G18) early. |
| Anchor regeneration produces obsessions that don't match the anchor's voice | Medium | Medium | Tune the Anchor prompt during Unit 5. Show before/after diffs during QA. If it fails consistently, degrade to "commit anchor only" without variants. |
| Atomic write fails on Windows (if anyone ever tries to run this there) | Low | Low | Morning Lineup targets Ubuntu (JB's machine). Document Linux-only as a constraint. Not a v1 concern. |
| Progress header flickers on every commit due to full re-render | Low | Low | Update only the relevant task count, not the whole header. Handle in Unit 7. |
| Browser tab refresh loses chat history mid-session | Medium | Low | Document the limitation. If it becomes a pain point, add sessionStorage persistence in a future unit. |
| The tool is more fun to build than to use | Medium | Medium | Enforce a personal discipline: after Unit 1 lands, use it to commit ONE real entry in each task before moving to the next unit. "Eat your own dog food" keeps the tool grounded. |
| Scope creep: adding more modes or features while building | Medium | Medium | This plan is the scope contract. Adding a mode = a new plan document. |
| The Anthropic API key isn't available during development | Low | High | Mock the LLM helper in all tests. Provide an Ollama-only fallback path for local dev without Anthropic. |

## Dependencies / Prerequisites

- **Ollama** running locally with `qwen3:8b-q4_K_M` pulled (already present per the existing columnists pipeline).
- **`ANTHROPIC_API_KEY`** available in the environment — loaded from `~/.secrets/morning-lineup.env` or exported directly. Strongly recommended; the tool works without it but with degraded quality.
- **Python 3.12+** (Morning Lineup's baseline).
- **A modern browser** (Chromium, Firefox — both stdlib HTTP server compatible).
- **JB's authoring time** — ~100 minutes of actual session time to complete all 5 tasks after the tool is built.

## Alternative Approaches Considered

1. **A rich single-editor form-based tool.** Rejected — doesn't match how JB works (he prefers conversation + curation over form-filling) and the 4-hour friction remains.
2. **A static HTML + localStorage + export button tool.** Rejected — adds a manual copy step to move data from browser state to JSON files. Creates drift risk.
3. **A terminal CLI tool.** Rejected — wrong form factor for JB. Terminal UIs are not JB's natural interface.
4. **Philosophy B only: Tinder-for-obsessions without Chat or Card.** Rejected — leaves Tasks 2-5 unsolved. The hybrid is specifically better because it handles all 5 tasks in their natural shapes.
5. **Philosophy A only: the Immersive Card Mode editor for everything.** Rejected — Tasks 2-4 are inherently conversational and don't fit a single-entry editor well. And the 4-hour friction remains.
6. **Build the Walking Mic (voice memo + Whisper) as the primary input.** Deferred to v2 — adds moving parts and isn't strictly necessary to hit the 100-minute target. Can layer in later.
7. **Reuse the Press Row 2.0 `pressrow/llm.py` instead of duplicating.** Rejected because Writer's Room must ship before Press Row 2.0 begins. Can dedupe later.
8. **Put everything in `pressrow/` instead of a separate `pressrow_writer/` subpackage.** Rejected — they serve different purposes (Writer's Room is authoring, Press Row 2.0 is runtime). Separating them keeps concerns clean.

## Phased Delivery

**Phase 0 (Scaffold) — ~0.5 day.** Unit 1. Deliverable: server runs, shell opens, mode selector works, all helpers ported. No real functionality yet.

**Phase 1 (Chat Mode) — ~1 day.** Units 2 + 3. Deliverable: Chat mode fully functional for Tasks 2, 3, 4. JB can complete all three conversational tasks. At the end of this phase, the tool is ~60% done by task count (3/5 tasks shippable).

**Phase 2 (Swipe Mode) — ~1 day.** Units 4 + 5. Deliverable: Batch script produces candidates, Swipe mode lets JB curate them. After this phase, Task 1 (the biggest task) is solved.

**Phase 3 (Card Mode) — ~0.5 day.** Unit 6. Deliverable: Walk-Off Ghost ritual works. Task 5 is solved. All 5 tasks now have working interfaces.

**Phase 4 (Polish) — ~0.5 day.** Unit 7. Deliverable: progress bars update correctly, keyboard shortcuts work, celebration screen shows at completion. The tool is polished enough to use for real.

**Total: ~3.5 days of focused engineering.**

**Minimum viable delivery:** Phases 0 + 1 alone (1.5 days). This ships the Chat mode and solves Tasks 2, 3, 4 immediately. JB can use it to complete those tasks while Phases 2-4 are still being built. Task 1 (the biggest) waits for Swipe mode, Task 5 waits for Card mode.

**Alternative delivery order:** If Task 1 feels most urgent (it's 4 hours' worth of work alone), build Phases 0 + 2 first (Scaffold + Swipe). Chat and Card come later. Each phase is independent of the others past the scaffold.

## Success Metrics

- **Time to complete all 5 tasks end-to-end:** ≤100 minutes in a single session. (R8)
- **Subjective quality:** JB rates the final output as "authentic Morning Lineup voice" without heavy post-hoc editing.
- **Tool reliability:** Zero data-loss incidents across the full session.
- **Authorial pride:** JB feels like he authored the universe, not like Claude did while he approved.
- **Shipping velocity:** The tool completes and is used within 1 week of starting the build.

## Documentation / Operational Notes

- Create `pressrow_writer/README.md` explaining the subpackage, CLI subcommands, and the batch-then-serve flow.
- Update `CLAUDE.md` with a new section on the Writer's Room: entry point, modes, config file outputs.
- No deployment changes — the Writer's Room is local-only and `deploy.py` does not ship it.
- Add a note to the Press Row 2.0 plan (`docs/plans/2026-04-12-001-feat-press-row-v2-plan.md`) that the authoring data will come from the Writer's Room, and link to this plan.

## Sources & References

- **Companion: Press Row 2.0 plan:** `docs/plans/2026-04-12-001-feat-press-row-v2-plan.md`
- **Companion: Authoring work plan:** `docs/plans/2026-04-12-002-press-row-v2-authoring-work-plan.md`
- **Ideation session:** Inline conversation on 2026-04-12 (30 candidates across 3 frames, 7 survivors, hybrid design emerged from A/B fork discussion)
- **LLM helper reference:** `sections/columnists.py:142-191` (Ollama/Anthropic fallback pattern)
- **Cache/atomic write pattern:** `sections/columnists.py:53-70`
- **CSS design system:** `style.css` (lines ~1-50 for the variable block)
- **Util helpers to port:** `docs/future/pressrow.py:28-55`
- **Persona schema:** `teams/cubs.json:59-81`
- **Team color palette:** `teams/cubs.json:8-13`
- **Static-HTML-and-vanilla-JS precedent:** `scorecard/` subdirectory
- **CLAUDE.md guardrails:** `CLAUDE.md` at repo root
- **Auto-memory context:** `~/.claude/projects/-home-tooyeezy/memory/feedback_frontend_aesthetic.md`, `feedback_screenshot_ui_loop.md`
