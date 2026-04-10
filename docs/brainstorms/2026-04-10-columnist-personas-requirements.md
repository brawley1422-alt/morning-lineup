---
title: Columnist Personas — Editorial Voice for Every Team
status: ready-for-planning
date: 2026-04-10
type: feature
---

# Columnist Personas — Editorial Voice for Every Team

## Problem frame

Morning Lineup currently has a single LLM-generated editorial lede at the top of each team page — one voice, one tone, one paragraph. It reads well enough, but the voice is flat. A die-hard fan doesn't keep coming back for "witty, opinionated, knowledgeable" — they come back because a *specific columnist* says the things they want to hear (or the things that make them angry). A single AI voice can't be that, but three distinct personas per team can.

The goal is to turn the editorial voice into the thing readers return for, not just the stats.

## Who it's for

- **Primary:** die-hard baseball fans who already love their team and want the morning paper to *have a perspective* — not just report
- **Secondary:** fantasy players who want a read on their guys with character
- **Tertiary:** casual fans drawn in by the character/humor even before they care about the team

## What we're building

A **Columnists section** at the top of every team page (and mirrored into `/home` per followed team). It replaces the current single editorial lede with three full-length columns, one from each persona.

**The three personas, team by team:**

1. **The Straight Beat** — facts over feelings. Reads like a veteran beat reporter. Reports what happened, reports what's next, no takes, no jokes, no cheerleading.
2. **The Optimist** — positive humor, everything's a silver lining, even blowout losses contain the seed of a pennant run. Dad-joke energy, unshakable faith.
3. **The Pessimist** — negative humor, doom-scrolls even the wins, finds the bullpen meltdown buried inside a 10-2 victory, convinced the front office is out to ruin his life.

## Key decisions (locked in brainstorm)

- **Placement:** a new "Columnists" section at the top of every team page, replacing the existing single editorial lede
- **Display:** side-by-side cards on wide screens, stacked vertically on narrow screens (the 300+ word length forces this)
- **Order:** randomized on every page render, so readers don't build muscle memory around "I always read the same one first"
- **Scope of voice:** all three columnists write about the same day's context (yesterday's game, current record, biggest storyline), but each is prompted to latch onto what their persona would naturally obsess over. Straight Beat covers the headline; Optimist finds the silver lining even in losses; Pessimist finds the cloud even in wins
- **Per-team personas, not shared:** every one of the 30 teams gets its *own* trio of writers with distinct names, eras, and voices. 90 unique columnists total. The Cubs Optimist is not the Yankees Optimist
- **Character depth:** each persona gets a name, a short backstory (neighborhood, era they started covering the team, how they got the beat), a signature phrase they overuse, and a sample sentence in their voice. All of this feeds into the generation prompt
- **Length:** 300+ words per column, real stories, not quick takes. A pessimist rant might run longer; a straight-beat recap might be tighter. The prompt should encourage room to breathe, not force a specific count
- **All writers, all users:** every user sees all three columnists for every team they follow. No picking favorites. Future: users may be able to hide writers they don't like, but not in v1
- **Content safety:** every persona prompt includes guardrails — no slurs, no personal attacks on real players, no betting advice, no commentary on off-field legal matters. The pessimism is about the *team*, not the humans

## Requirements

- **R1.** Every team page shows a Columnists section at the very top of the page, above all nine existing sections
- **R2.** The Columnists section contains exactly three cards, one per persona, in randomized order
- **R3.** Each card displays the writer's name, role ("The Straight Beat" / "The Optimist" / "The Pessimist"), and their 300+ word column for today
- **R4.** Each of the 30 teams has its own unique trio of writer personas, defined in that team's `teams/{slug}.json` config alongside existing branding
- **R5.** Each persona definition includes: name, role, one-sentence backstory, one signature phrase, one voice-sample sentence — all fed into the generation prompt
- **R6.** The existing single editorial lede (`generate_lede()` in `sections/around_league.py`) is removed from team pages and replaced by the Columnists section
- **R7.** Columns are generated once per team per day using the existing Ollama → Anthropic Claude fallback pipeline (three calls per team per day). Cached to `data/columns-{slug}-{YYYY-MM-DD}.json` with all three writers' text in a single JSON file
- **R8.** On `/home`, each followed team brings its own three columnists, rendered inside that team's block. The section must be collapsible per team (via `<details>`) so a user following five teams isn't buried in 15 columns at the top
- **R9.** If a single writer's generation fails, that writer's card shows a discreet placeholder ("{Name} is off today"). The other two still render
- **R10.** Columns must not contain slurs, personal attacks on real players or their families, betting advice, or off-field legal commentary. Guardrails are baked into every persona prompt
- **R11.** Generation must not break the existing daily build pipeline. If all three writers fail, the build completes without a Columnists section rather than crashing
- **R12.** The columns respect the existing `ml-auth` session model — logged-out guests still see the Columnists section as part of the three unlocked sections in the guest preview (replacing the headline's current position or slotted alongside it — planning to resolve)

## Success criteria

- **SC1.** A returning reader can name at least one columnist they like (or love to hate) from the team they follow most
- **SC2.** Readers regularly scroll past the game recap to read the columns (measurable if analytics are later added; for now, qualitative tester feedback)
- **SC3.** The three personas are distinguishable by voice alone — if you stripped the bylines, a reader could guess which one wrote which
- **SC4.** The columns feel like they were *written*, not *generated*. Tester sentiment is the bar: "this is actually funny" or "this made me mad in a good way"

## Non-goals (v1)

- **NG1.** Users cannot yet hide/mute writers they don't like — that's a later setting
- **NG2.** No cross-team columnist pieces ("The Division Roundup" by someone else) — stays scoped to one team per column
- **NG3.** No reader-visible comments, ratings, or reactions on columns
- **NG4.** No headshots, avatars, or portraits for the writers in v1 — names and roles only
- **NG5.** No writer archives (past columns searchable) — only today's column is shown
- **NG6.** No live/breaking-news updates during the day — one column per writer per day, written at build time

## Open questions for planning

- **Q1.** How does the 90-persona content asset get generated? Options: (a) Claude generates all 90 as a first draft, you review, edit, and commit, or (b) you hand-write a few priority teams (Cubs first) and Claude fills in the rest
- **Q2.** Where do the persona definitions live in `teams/{slug}.json`? Suggested path: extend the existing `branding` block with a new `columnists: [{name, role, backstory, signature_phrase, voice_sample}, ...]` array
- **Q3.** Visual treatment: are the three cards distinguished by background color, border accent, typography, or all three? Planning should pick a visual language that makes the personas recognizable at a glance
- **Q4.** What's the randomization scope — per page load, per session, or per day? Per page load is the freshest; per day keeps the order consistent within a single reader's morning read
- **Q5.** Generation cost: three LLM calls per team per day × 30 teams = 90 calls, mostly on Ollama locally. If Ollama fails and Anthropic is the fallback, Claude Sonnet at 90 calls/day needs an eyeball on the cost. Planning should confirm this is a non-issue
- **Q6.** Guest preview interaction: currently sections 1-3 (headline, scouting, stretch) are unlocked for guests. Does the Columnists section replace one of those in the unlock list, or slot in above all of them as a "always visible" editorial top? Likely the latter — it's the wedge
- **Q7.** Prompt design: how prescriptive should the persona prompts be? Too prescriptive and all three columnists start sounding like the same LLM doing impressions; too loose and they drift toward generic. Planning should sketch the prompt structure

## Dependencies

- Existing `generate_lede()` pipeline in `sections/around_league.py` — Ollama (qwen3:8b) + Anthropic Claude fallback + per-day caching in `data/`
- Per-team config system in `teams/{slug}.json` — already drives `branding.lede_tone`, needs to be extended to hold the three persona definitions
- The daily build (`build.py`) already regenerates per-team pages and has cache awareness for the current lede
- `/home` merged view (`home/home.js`) — must know how to include the Columnists section from each followed team's extracted HTML
- Guest preview logic in `home/home.js` — must decide whether Columnists is always-visible or part of the lock gradient

## Risks and things to watch

- **Voice collapse.** Three personas generated by the same LLM with similar prompts can all end up sounding like the same AI doing impressions. Mitigation: per-team character depth (name, era, backstory, phrase, voice sample) should push the prompts apart enough to get distinct voices. Test early with a few teams before committing
- **Content safety.** Pessimist personas prompted to be negative can drift into territory we don't want (personal attacks, off-field commentary, dark humor that crosses lines). Mitigation: hard guardrails in every prompt, plus tester review before launch
- **Generation time.** Three LLM calls per team × 30 teams is 90 calls per daily build. On Ollama locally this is probably fine; if falling back to Anthropic the build could get slow. Mitigation: generate in parallel per team, fail gracefully if a single call times out
- **Visual noise on `/home`.** A reader following five teams sees 15 cards at the top of their merged view. Without the `<details>` collapsible requirement, this becomes a wall of text. Must be collapsed by default
- **Maintenance cost of 90 personas.** If you want to tune the Optimist's overall voice later, you're editing 30 config files. Mitigation: consider a shared "role defaults" block that persona-specific fields override. Planning decides if worth it
- **LLM quality ceiling.** A local 8B model may not be able to hold three distinct 300-word voices per team consistently. Mitigation: test the quality early, and if needed, lean on the Anthropic fallback for the primary path rather than Ollama

## Notes from the brainstorm

- JB was emphatic that all three writers exist for all users at launch — the picking-a-favorite model was explicitly rejected. Users may eventually be able to hide writers they don't like, but removal is a non-goal for v1
- The combo of "same daily context, different obsessions" was JB's framing when asked whether all three should cover the same thing or each pick their own angle. Planning should respect that hybrid
- JB specifically loved the per-team naming idea despite the content-creation cost — "I like 3 a ton...." This signals that the product is leaning hard into the authored/editorial feel over the generated/automated feel. Planning should protect that instinct
- The 300+ word length is a deliberate escalation. Planning should design the display with that in mind — these are columns, not taglines
