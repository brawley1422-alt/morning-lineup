---
title: "feat: Columnist Personas — three voices per team"
type: feat
status: active
date: 2026-04-10
origin: docs/brainstorms/2026-04-10-columnist-personas-requirements.md
---

# feat: Columnist Personas — three voices per team

## Overview

Replace the current single editorial lede with a new Columnists section at the top of every team page. Each team gets three persona columns — Straight Beat, Optimist, Pessimist — written in distinct per-team voices (90 unique personas total, already drafted and approved). Columns are 300+ words, generated once per day per team, displayed side-by-side on wide screens and stacked on narrow screens. The section mirrors into `/home` as a collapsible block per followed team.

This is the move that turns Morning Lineup from a generated feed into an authored newspaper.

## Problem Frame

The existing lede is one voice, one tone, one paragraph — flat by design because it's trying to be everything to every reader. Fans come back for characters they love (or love to hate), not for "witty, opinionated, knowledgeable." Three distinct personas per team give readers a voice to return for, a foil to argue with, and a foil-of-a-foil for comic relief. The per-team naming (Cubs Optimist is Bee Vittorini, not a shared "The Optimist" who spans all 30 teams) is what makes the product feel *written* instead of generated.

See origin: `docs/brainstorms/2026-04-10-columnist-personas-requirements.md`

## Requirements Trace

- **R1.** Every team page shows a Columnists section at the very top of the page, above all nine existing sections (see origin: R1, R6)
- **R2.** Three cards per section, one per persona, in randomized order on each render (see origin: R2)
- **R3.** Each card displays the writer's name, role, and 300+ word column for today (see origin: R3)
- **R4.** Per-team personas stored in `teams/{slug}.json`, 90 total (see origin: R4, R5)
- **R5.** Columns generated via existing Ollama→Anthropic fallback pipeline, cached one file per team per day (see origin: R7)
- **R6.** `/home` merged view wraps each followed team's columnists block in a `<details>` collapsible, collapsed by default (see origin: R8)
- **R7.** Single-writer failures degrade gracefully to a "{Name} is off today" placeholder card; total generation failure omits the section without crashing the build (see origin: R9, R11)
- **R8.** Guardrails baked into every persona prompt: no slurs, no personal attacks on real players, no betting advice, no off-field commentary (see origin: R10)
- **R9.** Guest preview on `/home` shows the Columnists section unblurred above the existing unlocked sections — it is the wedge (see origin: R12)

## Scope Boundaries

- **Not building:** a user setting to hide/mute writers they don't like. Future work
- **Not building:** headshots, avatars, writer portraits
- **Not building:** cross-team columnist pieces ("The Division Roundup")
- **Not building:** writer archives / past-column browsing
- **Not building:** live/breaking-news updates — one column per writer per day, at build time
- **Not touching:** the nine existing numbered sections. This adds a new editorial block above them and removes the current single lede, nothing else
- **Not touching:** the `scorecards`, `followed_teams`, or `followed_players` tables. Columnists are build-time content, not per-user data

## Context & Research

### Relevant Code and Patterns

- **`sections/around_league.py`** — `generate_lede()` at L221 is the pattern to mirror. It already handles: (1) Ollama call to qwen3:8b with timeout, (2) Anthropic Claude fallback via `ANTHROPIC_API_KEY` env var, (3) per-team per-day caching at `data/lede-{slug}-{date}.txt`, (4) graceful degrade if both fail. The new `generate_column()` will be an extended version of this function taking an extra `persona` parameter
- **`sections/around_league.py`** — `render_lede_block(briefing)` at L310 is called from `build.py` `page()`. The new columnists block replaces this call
- **`build.py`** — section modules imported at top, `page()` at ~L580 assembles the envelope. New module `sections/columnists.py` follows the same shape
- **`teams/{slug}.json`** — per-team config that already holds `branding.lede_tone`. New `columnists` array lives at the top level (not under branding, since it's content not style)
- **`docs/brainstorms/2026-04-10-columnist-personas-draft.json`** — the 90-persona draft, approved. A one-time merge script folds these into the 30 team configs
- **`home/home.js`** — `SECTION_ID_MAP` translates profile keys to HTML section IDs. Columnists do not belong in this map because they are cross-section (not user-orderable), but the extraction logic in `renderMergedView()` needs a new parallel path for always-on blocks
- **`home/home.js`** — `renderPreview()` (guest flow) currently extracts sections by ID from a static team page and shows first 3 unlocked. Columnists insert above the unlock list
- **`style.css`** — the main stylesheet, inlined by `build.py`. New `.columnists`, `.column`, `.column-byline` rules added here

### Institutional Learnings

- **Per-team CSS variable cascade** (from `docs/solutions/best-practices/config-driven-multi-tenant-static-site-2026-04-08.md`) — every team page uses the same template with team-specific colors injected. Columnists should also get team-accent coloring on card borders so each team's trio feels owned
- **DOMParser extraction pattern** (Phase B of the accounts plan) — `/home` already reuses built team pages by parsing them. Columnists will fit into this model trivially since they're just another `<section>` on each team page

### External References

- None. The LLM prompt engineering is within this repo's existing patterns and Claude-era best practices the assistant already knows

## Key Technical Decisions

- **Single section, not nine new sections** — the Columnists block is ONE `<section id="columnists">` containing three `<article class="column">` children. Not three numbered sections. This keeps the existing nine-section model intact and lets the whole editorial block be treated as one unit in `/home`
- **Top-level `columnists` key in team configs, not nested under `branding`** — it's a content asset, not a style knob. Keeps the schema honest
- **Randomized order is client-side, not build-time** — build generates the three cards in a canonical order (Straight Beat, Optimist, Pessimist) wrapped in a container with a tiny inline script that shuffles them on `DOMContentLoaded`. Pure CSS/JS, no server-side randomization needed. This gives per-page-load variety without per-build cache churn
- **One cache file per team per day, all three writers in one JSON** — `data/columnists-{slug}-{YYYY-MM-DD}.json`. Structure: `{"straight_beat": {"name": "...", "column": "..."}, "optimist": {...}, "pessimist": {...}}`. Single file because all three get generated together and a missing writer can be tracked as an empty string in the JSON rather than a missing file
- **Three LLM calls per team, sequential not parallel** — 3 calls × 30 teams = 90 calls per daily build. Ollama on Yeezy can handle them sequentially without thrash; parallel hitting Ollama with three concurrent requests would queue anyway. Sequential keeps the code simple. Revisit if daily build time becomes a problem
- **Failure mode is per-writer, not per-section** — if one writer's call fails, its card becomes "{Name} is off today." in gold italics. If all three fail, the section is still rendered with three "off today" cards (not omitted) so the layout is stable and debugging is visible
- **Guest preview shows columnists unblurred** — the columnists are *the wedge*. Guests should taste this first. The guest-preview code path needs a small fork: columnists renders above the numbered sections in its own always-visible position, separate from the first-3-unlocked logic
- **`/home` merged view wraps each team's columnists in `<details>` collapsed by default** — otherwise a user following five teams sees 15 columns pinned at the top of their feed. Summary text in the `<summary>` reads "Columnists: {Name}, {Name}, {Name}"
- **Prompt structure is persona-forward, not team-forward** — the prompt leads with the persona's name, backstory, signature phrase, and voice sample; then feeds the day's context; then restates the persona's rules one more time at the end. LLMs drift. Double-bookend the identity

## Open Questions

### Resolved During Planning

- **Where do persona definitions live?** — Top-level `columnists` array in `teams/{slug}.json`, three objects per team keyed by position in the array (not by role, so random order is easier at render time). Each object has `{name, role, backstory, signature_phrase, voice_sample}` plus an implicit `role_key` field derived from `role` text
- **How is the 90-persona content generated?** — Already done. The draft at `docs/brainstorms/2026-04-10-columnist-personas-draft.json` is approved and gets merged in Unit 1
- **Visual treatment** — Three cards side-by-side on wide screens (CSS grid), stacked vertically on narrow. Each card: gold top-border accent inherited from the team's `primary` color, persona name as a bold italic serif, role as uppercase condensed gold, column text in body serif at a slightly smaller size than article copy. Byline styled like an op-ed section
- **Randomization scope** — Per page load (client-side shuffle), not per day. Cheap to implement, maximum freshness
- **Guest-preview interaction** — Columnists always-visible above the numbered sections in the guest `/home` flow. The existing blur-paywall logic keeps operating on sections 4-9 unchanged
- **Generation cost** — 90 calls per daily build, ~60s on Ollama at qwen3:8b estimated worst-case if each call takes ~20s. Real-world experience with the existing `generate_lede()` pipeline suggests ~5-15s each. Acceptable. If daily build time becomes a concern, revisit with a parallel executor

### Deferred to Implementation

- **Exact prompt wording** — the plan specifies the *structure* of the prompt (persona-forward, context sandwich, length instruction, guardrails). The exact wording should be tuned against real generations during implementation. Target: can you identify which writer wrote which column from voice alone? If no, the prompt is too loose or the personas are too similar — iterate
- **Client-side shuffle script location** — inline `<script>` at the end of the columnists `<section>` is simplest but violates CSP if one gets added later. Could instead be a named helper in an existing JS file. Implementation can pick the lightest-touch option; prefer inline for now since the site has no CSP
- **Ollama concurrency** — the plan says sequential. If the implementing agent finds sequential adds more than ~30s to the daily build, testing a small concurrent pool (asyncio or threads) is fair game
- **Byline format on cards** — "by Bee Vittorini" vs "— BEE VITTORINI" vs just "BEE VITTORINI / The Optimist" as a two-line byline. All three feel editorial; implementation can eyeball which reads best

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification.*

### Data flow

```
teams/cubs.json (persona config)
        │
        ▼
build.py --team cubs
        │
        ├─► sections/columnists.py :: render(briefing)
        │       │
        │       ├─► for each persona in briefing.config["columnists"]:
        │       │       │
        │       │       ├─► generate_column(briefing, persona)
        │       │       │       │
        │       │       │       ├─► cache hit? → return cached text
        │       │       │       ├─► Ollama POST → column text (or empty)
        │       │       │       └─► Anthropic fallback → column text (or empty)
        │       │       │
        │       │       └─► (name, role, column_text) tuple
        │       │
        │       └─► render HTML: <section id="columnists"> with 3 <article class="column">
        │
        └─► page envelope: columnists_html placed ABOVE the wrap/TOC, replacing the old lede
```

### Team config shape (extension)

```jsonc
// teams/cubs.json (excerpt)
{
  "slug": "cubs",
  "name": "Cubs",
  "id": 112,
  "colors": { ... },
  "branding": { "lede_tone": "..." },
  "columnists": [
    { "name": "Walt Kieniewicz", "role": "The Straight Beat", "backstory": "...", "signature_phrase": "...", "voice_sample": "..." },
    { "name": "Beatrice 'Bee' Vittorini", "role": "The Optimist", "backstory": "...", "signature_phrase": "...", "voice_sample": "..." },
    { "name": "Tony Gedeski", "role": "The Pessimist", "backstory": "...", "signature_phrase": "...", "voice_sample": "..." }
  ]
}
```

### Cache file shape

```jsonc
// data/columnists-cubs-2026-04-11.json
{
  "straight_beat": { "name": "Walt Kieniewicz", "column": "..." },
  "optimist":      { "name": "Beatrice 'Bee' Vittorini", "column": "..." },
  "pessimist":     { "name": "Tony Gedeski", "column": "" }    // empty string = generation failed
}
```

### HTML shape

```html
<section id="columnists" class="columnists">
  <div class="columnists-head">
    <span class="section-kicker">The Columnists</span>
    <span class="section-dek">Three takes on today's game</span>
  </div>
  <div class="columnists-grid" data-shuffle="true">
    <article class="column" data-role="straight_beat">
      <div class="column-byline">
        <span class="column-name">Walt Kieniewicz</span>
        <span class="column-role">The Straight Beat</span>
      </div>
      <div class="column-body"><!-- 300+ words --></div>
    </article>
    <article class="column" data-role="optimist"> ... </article>
    <article class="column" data-role="pessimist"> ... </article>
  </div>
  <script>/* 10-line shuffle script */</script>
</section>
```

## Implementation Units

- [ ] **Unit 1: Merge persona draft into team configs**

**Goal:** Move the 90 approved personas from `docs/brainstorms/2026-04-10-columnist-personas-draft.json` into each of the 30 `teams/{slug}.json` files under a new top-level `columnists` array. One-time migration.

**Requirements:** R4

**Dependencies:** None

**Files:**
- Create: `scripts/merge_columnists.py` (one-time migration script; kept in repo for auditability even though it runs once)
- Modify: `teams/angels.json`, `teams/astros.json`, ... `teams/yankees.json` (all 30)

**Approach:**
- Script reads the draft JSON, iterates each team slug, loads `teams/{slug}.json`, adds a top-level `columnists` array with the three persona objects in a canonical order (straight_beat, optimist, pessimist), and writes the file back with 2-space indent
- Idempotent: if `columnists` already exists, the script leaves it alone unless a `--force` flag is passed. Prevents accidental stomp on hand-edits
- Validates that every team has exactly three personas after the merge; exits non-zero if any team is missing one

**Patterns to follow:**
- Stdlib only, same as the rest of the build pipeline
- JSON read/write via `json.load` and `json.dump(indent=2, ensure_ascii=False)` to preserve existing team config formatting

**Test scenarios:**
- Happy path: run the script clean → all 30 team configs gain a `columnists` array with three personas each, JSON remains valid
- Idempotent re-run: run twice → second run is a no-op, no diff
- Force flag: `--force` on a team that already has personas → rewrites them, logs which team was overwritten
- Missing persona in draft: draft is manually edited to drop one persona → script exits non-zero with the offending team name
- Test expectation: a smoke check — `python3 -c "import json; [json.load(open(f'teams/{s}.json')) for s in ALL_SLUGS]"` passes after the migration

**Verification:**
- Every `teams/*.json` has a top-level `columnists` array with exactly 3 objects
- Each object has keys `name`, `role`, `backstory`, `signature_phrase`, `voice_sample`
- `python3 build.py --team cubs` still builds without error (the new key is just ignored until Unit 3 wires it up)

---

- [ ] **Unit 2: Column generation helper (`generate_column`)**

**Goal:** Add a generation function in `sections/columnists.py` that takes a `briefing` and a `persona` dict and returns a 300+ word column string. Mirrors the existing `generate_lede()` pattern: Ollama first, Anthropic fallback, per-team per-day cache with all three writers in one JSON file.

**Requirements:** R5, R7, R8

**Dependencies:** Unit 1 (team configs must have persona data)

**Files:**
- Create: `sections/columnists.py` (will also hold `render()` in Unit 3 — split into this unit for sequencing clarity)

**Approach:**
- Function signature: `generate_column(briefing, persona, cache) -> str`. Takes the parsed cache dict so all three writers can share reads/writes without three file opens
- Builds the prompt with persona-forward structure: identity block, voice sample, today's context (yesterday's game, current record, key storylines — same context as the existing lede), length instruction ("write 300-500 words, a real column, not a tagline"), guardrails ("no slurs, no personal attacks on real players or their families, no betting advice, no off-field legal commentary"), closing identity reminder
- Tries Ollama (`qwen3:8b-q4_K_M`, temperature 0.8 — higher than the lede's 0.7 because persona voice benefits from slightly more heat, `num_predict` 768 to accommodate longer output)
- On Ollama failure (timeout, empty response, response shorter than 200 chars), falls back to Anthropic Claude Sonnet via `ANTHROPIC_API_KEY` env var, same as `generate_lede()`
- On total failure returns empty string. Caller handles the placeholder UI
- Cache read/write uses `data/columnists-{slug}-{today_iso}.json`. Read the whole file once at the top of `render()`, pass it to each `generate_column` call, write it back once at the end
- Strips any `<think>...</think>` tags from output (qwen3 sometimes leaks thinking)
- Caller is responsible for the persona→cache-key mapping (`straight_beat`, `optimist`, `pessimist`)

**Patterns to follow:**
- `sections/around_league.py :: generate_lede()` — the ~100 LOC template for Ollama + Anthropic fallback + cache + error handling. The new function is essentially a persona-parameterized version of the same thing
- The deferred-import rule: `sections/columnists.py` must not `from build import ...` at module top. If it needs helpers from `build.py`, import them inside function bodies

**Test scenarios:**
- Happy path Ollama: Ollama returns 400-word text → function returns it, cache file gains the writer's entry
- Happy path Anthropic fallback: Ollama connection refused → Anthropic call succeeds → function returns the Claude text, cache file gains the writer's entry
- Cache hit: second call with the same persona and same day → returns cached text, zero network calls
- Both fail: Ollama unreachable, no `ANTHROPIC_API_KEY` set → returns empty string, no cache entry written for that writer
- Empty response: Ollama returns a 40-char response → function rejects it (too short), tries Anthropic
- Think-tag leak: Ollama returns text wrapped in `<think>...</think>some column</think>` → function strips the tag, returns only the column

**Verification:**
- Calling `generate_column` three times in a row for the three Cubs personas produces three distinct strings (or empty strings on failure), and the cache file `data/columnists-cubs-{today}.json` contains three keyed entries
- A second run of the same three calls reads entirely from cache (no subprocess / network activity)

---

- [ ] **Unit 3: Section renderer (`sections/columnists.py :: render`)**

**Goal:** The `render(briefing)` entry point that `build.py` calls. Loads (or creates) the team's cache file, invokes `generate_column` for all three personas, and returns the HTML block.

**Requirements:** R1, R2, R3, R7

**Dependencies:** Unit 2

**Files:**
- Modify: `sections/columnists.py` (adds `render(briefing)`)

**Approach:**
- Reads `briefing.config["columnists"]` — the three persona dicts from Unit 1
- Reads the cache file (if present) into a dict; seeds an empty dict otherwise
- For each persona in canonical order (straight_beat → optimist → pessimist), calls `generate_column(briefing, persona, cache)`. Collects `(persona, column_text)` tuples
- After all three calls, writes the cache dict back to disk
- Builds the HTML: outer `<section id="columnists" class="columnists">`, header block with kicker + dek, grid wrapper `<div class="columnists-grid" data-shuffle="true">`, three `<article class="column" data-role="{role_key}">` with byline + column body
- For any writer with empty `column_text`, renders a placeholder card body: `"<em class='column-off'>{name} is off today.</em>"`
- If all three are empty, still renders the section with three placeholder cards (stable layout, visible debug signal)
- Includes a tiny inline `<script>` at the bottom of the section that shuffles the three `.column` children on `DOMContentLoaded`. ~10 lines of vanilla JS using `Array.from(container.children)` and repeated `appendChild`
- HTML-escapes all persona fields and the generated column text before interpolating (prevent any LLM output from breaking the page)
- Body paragraphs: split column text on double-newlines and wrap each in `<p>`. Preserves paragraph structure the LLM produces

**Patterns to follow:**
- `sections/around_league.py :: render_lede_block()` — minimal function that wraps generated text in a CSS-targetable block
- `sections/headline.py` — the pattern for a section that takes a `briefing` and returns a fully-rendered HTML string

**Test scenarios:**
- Happy path: all three personas generate → returned HTML contains three `<article class="column">` elements, each with a non-empty `<div class="column-body">`
- Partial failure: one persona's column is empty → that card shows the "off today" placeholder, the other two render normally
- Total failure: all three empty → section still renders, all three cards show placeholder, layout is intact
- HTML escape: a persona's name contains `<script>` (shouldn't happen but defense-in-depth) → output is escaped, no script injected
- Paragraph split: LLM returns text with `\n\n` separators → output contains multiple `<p>` tags
- Shuffle script: inspect the rendered HTML → a `<script>` block sits at the bottom of the section and targets `.columnists-grid`
- Test expectation: add a snapshot fixture with stubbed persona text (to avoid hitting Ollama in CI) and verify the HTML shape is stable

**Verification:**
- `sections.columnists.render(briefing)` for the Cubs briefing returns an HTML string starting with `<section id="columnists"`
- The returned HTML has exactly three `<article class="column">` elements
- Written cache file matches the cache-shape spec from the Technical Design section

---

- [ ] **Unit 4: Wire into `build.py`, remove existing lede, add CSS**

**Goal:** Call the new columnists section from `build.py :: page()`, remove the old single-lede call, add the CSS rules for `.columnists` / `.column` to `style.css`, and rebuild all 30 teams.

**Requirements:** R1, R3

**Dependencies:** Unit 3

**Files:**
- Modify: `build.py` (remove `lede_html = sections.around_league.render_lede_block(briefing)`, replace with `columnists_html = sections.columnists.render(briefing)`; update the f-string envelope to use `{columnists_html}`)
- Modify: `build.py` (add `import sections.columnists` at top, alphabetically placed)
- Modify: `style.css` (add `.columnists`, `.columnists-head`, `.columnists-grid`, `.column`, `.column-byline`, `.column-name`, `.column-role`, `.column-body`, `.column-off` rules)
- Modify: `sections/around_league.py` (leave `generate_lede` / `render_lede_block` in place but unused — do not delete. If we revert the columnists feature, the old lede is still callable. Easy cleanup later)
- Rebuild: all 30 `{slug}/index.html` files via `python3 build.py --team <slug>` loop

**Approach:**
- `build.py` change is minimal: one import line, one section call, one f-string swap. The columnists block replaces the old `{lede_html}` position in the page envelope (just below the masthead, above the TOC / nine sections)
- CSS uses `display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px;` on `.columnists-grid` for wide screens, with a `@media (max-width: 900px) { grid-template-columns: 1fr; }` override for narrow. Matches the existing editorial card style: `background: var(--ink-2); border: 1px solid var(--rule); border-top: 2px solid var(--team-primary); padding: 22px 24px; border-radius: 3px;`
- Column body uses Lora serif at 14.5px line-height 1.6 (same as article body elsewhere) and `column-count: 1` — no newspaper multi-column because cards are already narrow
- Byline: name in Playfair italic 18px, role in Oswald uppercase gold 10px letter-spacing 0.2em. Tight, editorial, recognizable at a glance
- Theme-paper overrides: `body.theme-paper .columnists { background: #f3ecd7; }` etc., mirroring existing theme-paper CSS in home.css

**Patterns to follow:**
- `build.py :: page()` — f-string envelope with `{section_html}` placeholders. Just another one slotted in
- `style.css` — existing section card patterns (the nine numbered sections have card treatments that can be mirrored)
- The snapshot re-bless pattern documented in `tests/README.md`

**Test scenarios:**
- Build one team: `python3 build.py --team cubs` → exits 0, produces `cubs/index.html` containing `<section id="columnists">`
- Build all 30: loop over slugs → all 30 build successfully, each page has exactly one `<section id="columnists">` block
- CSS inline: rendered `cubs/index.html` contains `.columnists-grid` style rules (build.py inlines style.css)
- Mobile reflow: visually verify in a narrow-window screenshot that cards stack rather than crush horizontally
- Guest preview unchanged: `/home/` in an incognito window still shows the guest flow without errors (the extraction path for guests isn't hooked up yet — that's Unit 5 — but it shouldn't break)
- Snapshot harness: `python3 tests/snapshot_test.py` — expected to DIFF because the page structure changed. Re-bless the golden fixtures per `tests/README.md`

**Verification:**
- All 30 team pages have a working Columnists section
- The old single-lede block is gone from the rendered output
- Golden snapshots re-blessed and committed
- `deploy.py` pushes the updated pages and CSS changes to Pages

---

- [ ] **Unit 5: `/home` integration (merged view + guest preview)**

**Goal:** Make `/home` aware of the new `#columnists` section — for signed-in users, extract each followed team's columnists and wrap them in a collapsed `<details>`. For guests, render the picked team's columnists unblurred above the three unlocked sections.

**Requirements:** R6, R9

**Dependencies:** Unit 4 (team pages must contain `#columnists`)

**Files:**
- Modify: `home/home.js` (new helper `extractColumnists(doc)` that pulls `#columnists` out of a DOMParsed team page; modify `renderMergedView` to include it per-team wrapped in `<details>`; modify `renderPreview` to insert it above the unlocked-sections loop)
- Modify: `home/home.css` (add `.home-columnists-wrap` details-summary styling, plus any overrides needed so the inlined columnists CSS from the team page renders correctly inside the /home shell)

**Approach:**
- `extractColumnists(doc)` — `doc.querySelector("#columnists")?.cloneNode(true)` and return the node, or null if missing
- In `renderMergedView` per-team loop: after building the team block's section list, check if columnists exists. If so, wrap it in `<details class="home-columnists-wrap">` with a `<summary>` that reads "Columnists: {name1}, {name2}, {name3}" (pulled from the extracted node's `.column-name` children). Prepend the `<details>` to the team block's children, above the numbered sections
- Summary text is useful even when collapsed — it's the "who's writing today for this team" one-liner
- For guests, `renderPreview()` already fetches one team's static page. After extraction, insert the columnists node into the shell ABOVE the existing three unlocked section nodes, NOT wrapped in `<details>` (guests should see it wide open — it's the wedge)
- The inlined shuffle script from Unit 3 needs to run when the nodes are mounted in `/home`. Since we clone from a DOMParsed doc, the inline `<script>` tags do NOT re-execute on append. Workaround: after appending the columnists node, manually reparse and re-run the shuffle by copy-pasting the shuffle logic as a helper in `home.js` and calling it against each inserted `.columnists-grid`
- Density/theme classes on `body` still cascade through the columnists (same as every other section), so no extra work there

**Patterns to follow:**
- `home/home.js :: extractSection(doc, htmlId)` — the model for cloning a static section out of a parsed team page
- `home/home.js :: renderMergedView` — the per-team loop where insertion happens
- `home/home.js :: renderPreview` — the guest flow, already handles one-team extraction

**Test scenarios:**
- Signed-in user with 1 team: /home renders one team block, the columnists `<details>` is collapsed by default, summary shows all 3 writer names
- Signed-in user with 5 teams: /home renders 5 team blocks, each with its own collapsed columnists `<details>`. Opening one does not affect the others
- Signed-in user, click to expand: the three columns inside shuffle order (shuffle helper runs after append)
- Guest preview: /home in incognito, pick Cubs → columnists section appears at the top, above headline/scouting/stretch, unblurred, fully readable
- Guest preview: pick Yankees → columnists updates to the Yankees trio, paywall sections 4-9 still blurred
- Team with missing columnists (legacy snapshot or failed build): `extractColumnists` returns null → /home renders the team block without a columnists wrapper, no JS error
- Summary readable when collapsed: without clicking to expand, the user still sees "Columnists: Walt Kieniewicz, Bee Vittorini, Tony Gedeski"

**Verification:**
- Signed in, following 3 teams → /home shows 3 collapsed columnists blocks with the right writer names in each summary
- Expanding a block shows three shuffled cards with full text
- Guest preview shows the picked team's columnists unblurred above the three unlocked sections
- No console errors, no layout breakage on mobile narrow

---

- [ ] **Unit 6: Tester review and prompt tuning**

**Goal:** After the feature is live, run the daily build, read all 90 columns, and tune the prompt if voices collapse (all three sounding like the same AI doing impressions).

**Requirements:** SC1, SC2, SC3, SC4 (the success criteria from the origin doc)

**Dependencies:** Unit 5

**Files:**
- Modify: `sections/columnists.py :: generate_column` prompt text, iteratively

**Approach:**
- Not code work — content quality work. Read a sample of 5 teams' full columnist output. Ask: (a) can you tell who wrote what without looking at the byline? (b) do all three write about the same thing in suspiciously similar ways? (c) is the Pessimist actually funny-mean or just grumpy-generic? (d) does the Optimist get weird-earnest or stay playful?
- If voice collapse is the issue, the fix is usually one of three prompt tweaks: more voice sample in the prompt (not just the persona block), a negative instruction ("do NOT use the phrase 'silver lining'"), or bumping temperature higher for the Pessimist specifically
- This unit is marked as planned rather than open-ended so it gets done. Shipping without it risks launching with AI slop
- No new files, no new tests. Commits here are small prompt edits and a rebuild-all

**Execution note:** This is a quality pass, not a feature. Budget ~1-2 hours to read real output and iterate. Do this BEFORE inviting testers to look at the columnists feature specifically

**Patterns to follow:**
- None. Judgment call based on reading the output

**Test scenarios:**
- Test expectation: none — this is a content-quality iteration, not a behavioral change

**Verification:**
- A human (JB) reads a sample of 5 teams' full trios and confirms: "yes, these feel distinct" or "no, the Pessimists all sound the same — tune again"

---

## System-Wide Impact

- **Interaction graph:** `build.py` gains one new section module import; `home/home.js` gains one new extraction path (for `#columnists`); `deploy.py` needs no changes (team pages and style.css are already in its push list; `sections/columnists.py` is build-only and doesn't ship to Pages)
- **Error propagation:** single-writer failures are isolated via the "off today" placeholder. Total failures of the columnists section still render an empty-cards shell, never crash the build. The failure path does not throw — it logs and returns empty string
- **State lifecycle risks:** cache file per team per day is additive — old cache files in `data/` do not need purging (they're disposable). The cache shape (JSON with three writer keys) is versionless, but if we ever rename a role, the cache loader needs a migration or a cache-busting filename. Deferred concern for now
- **API surface parity:** the existing `generate_lede` function is NOT deleted, just unused. This keeps a fallback path in case the columnists feature is reverted. After 30 days of stability, it can be removed
- **Integration coverage:** Unit 5's `/home` integration test scenarios exercise the cross-layer path (static page → DOMParser → shell insertion → shuffle script). The signed-in merged view and the guest preview are both separate code paths that each need verification
- **Unchanged invariants:** the nine numbered sections, their rendering, their profile-key → HTML-id map, the `/settings` customization UI, the `followed_players` tracker — none of this is touched. The columnists block lives *above* everything else and is unconditionally present on team pages

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| **Voice collapse** — all three personas sound like the same LLM doing a voice | Per-team character depth in prompts (name, era, backstory, signature phrase, voice sample) should push them apart. Unit 6 is a dedicated read-and-tune pass. If still collapsing, consider higher temperature per persona or different models per persona |
| **Content safety** — Pessimist drifts into personal attacks, betting advice, or off-field commentary | Hard guardrails in every prompt, double-bookended (identity → context → rules → identity reminder). Unit 6 reads the output before inviting testers. Worst case: ship with a small denylist of phrases to reject-and-retry in `generate_column` |
| **Build time** — 90 sequential LLM calls make the daily build 10+ minutes longer | Ollama on Yeezy is fast for 8B models. Realistic estimate is ~5-10 minutes added, acceptable. If it becomes a problem, parallelize with a small thread pool (3 concurrent). Hard to estimate without running it first, so deferred |
| **`/home` visual noise** — a user following 5 teams sees 15 columns at the top | Collapsed `<details>` by default (Unit 5). Summary line tells them who's writing today without forcing them to expand |
| **Maintenance cost of 90 personas** — tuning the Optimist's voice globally requires editing 30 config files | Accepted. 30-file grep/sed isn't hard, and per-team distinctness is the whole point — there's no "global Optimist voice" to tune because every Optimist is supposed to sound different |
| **Ollama quality ceiling** — qwen3:8b may not hold three distinct 300-word voices consistently | Fallback to Anthropic Claude Sonnet exists. If Ollama output is thin, the implementer can raise the rejection threshold (reject Ollama output < 250 chars instead of 200) to force the fallback more aggressively |
| **Shuffle script double-execution on /home** — the inline script from the team page's HTML won't re-run after DOMParser clone | Unit 5 explicitly calls out this edge case and solves it by copy-pasting a shuffle helper into `home.js` that runs after append |
| **Snapshot fixture drift** — the golden HTML fixtures in `tests/` will diff after this change | Expected. Unit 4 includes re-blessing the snapshots as part of verification. Read `tests/README.md` |

## Documentation / Operational Notes

- **Tester announcement** — once Unit 6 is done and voices are tuned, update the tester message (the one drafted in this session) to call out the Columnists feature. It's the most shareable moment of the whole product
- **Persona editability** — if/when JB wants to rewrite a persona, it's a manual edit to `teams/{slug}.json` plus a rebuild of that team. No UI, no migration. Keep it that way for v1
- **Cache invalidation** — if a persona is changed mid-day, delete `data/columnists-{slug}-{today}.json` and rebuild. Document this in `docs/changelog/` after implementation
- **Cost monitoring** — if Anthropic fallback gets hit hard (Ollama down for a day), 90 Claude Sonnet calls per build × daily runs = monitorable cost. Add a log line counting Ollama-vs-Anthropic usage during the build so JB can eyeball it

## Sources & References

- **Origin document:** [docs/brainstorms/2026-04-10-columnist-personas-requirements.md](../brainstorms/2026-04-10-columnist-personas-requirements.md)
- **Persona draft:** [docs/brainstorms/2026-04-10-columnist-personas-draft.json](../brainstorms/2026-04-10-columnist-personas-draft.json)
- **Pattern to follow for generation:** `sections/around_league.py :: generate_lede`
- **Pattern to follow for section module shape:** `sections/headline.py`
- **Team config schema:** `teams/cubs.json` (reference for existing keys)
- **Snapshot re-bless docs:** `tests/README.md`
- **Related prior plan:** [docs/plans/2026-04-10-002-feat-accounts-and-custom-home-plan.md](2026-04-10-002-feat-accounts-and-custom-home-plan.md) — this columnists plan builds on the /home merged-view extraction pattern shipped there
