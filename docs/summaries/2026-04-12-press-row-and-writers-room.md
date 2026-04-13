---
date: 2026-04-12
topic: Press Row 2.0 + Writer's Room
---

# What we built today

## The arc in one paragraph

Started with a throwaway idea — "what if the Morning Lineup writers had a fake Twitter feed where they all argued with each other?" — built a first-draft prototype the same afternoon, shelved it because the local qwen model produced boring tweets, then spent the rest of the day turning it into a real plan. By the end of the session we had three planning documents covering the full feature, a fully-built local tool to eliminate the authoring friction, and a clear sense of what's still missing.

## Press Row 2.0 — the feature itself

A fictional MLB beat-writer universe layered on top of Morning Lineup. 90 writer personas (3 per team × 30 teams) interact with each other every day via a fake Twitter-style feed, reacting to real game results with hot takes, reply threads, quote tweets, and running arcs. The first prototype failed because one monolithic LLM call just hoped for banter. The 2.0 design treats banter as architecture.

**Three planning docs landed:**

1. **`docs/ideation/2026-04-12-press-row-pop-ideation.md`** — 30 candidate ideas across three frames (character/lore, format innovation, LLM craft), filtered down to 7 survivors via adversarial review. The 7: Comedy Editor Pipeline, Writer Obsession Config, Per-Writer Memory / Receipt Drawer, The Beef Engine, Letters to the Editor, Classifieds, Scheduled Event Programming.

2. **`docs/brainstorms/2026-04-12-press-row-v2-brainstorm.md`** — all 7 survivors integrated into a single coherent Press Row 2.0 system, with shared infrastructure, token budgets, build order, and open questions.

3. **`docs/plans/2026-04-12-001-feat-press-row-v2-plan.md`** — the master implementation plan. 10 implementation units across 4 phases, ~10-14 days of engineering. Architecture decision: Press Row runs as a separate Python subpackage at `pressrow/` that writes `data/pressrow-{date}.json`, consumed by a thin renderer in `sections/pressrow.py`. ML builds stay fast; Press Row can regenerate independently; graceful degradation at every layer.

**Also landed: the authoring companion plan.** `docs/plans/2026-04-12-002-press-row-v2-authoring-work-plan.md` — the 5 writing tasks JB needs to complete before Press Row 2.0 can ship. 270 obsessions, 30 shadow personas, 15-20 recurring fans, 10 seeded feuds, 1 Walk-Off Ghost. Estimated ~4 hours of writing if done in plain JSON editors.

## The Writer's Room — the tool we built to avoid those 4 hours

Halfway through the day we realized: editing 5 JSON files for 4 hours is a terrible workflow for a creative task. So we ideated again, designed a hybrid Chat + Swipe + Card tool, planned it, and built it end-to-end in the same session.

**Plan:** `docs/plans/2026-04-12-003-feat-press-row-writers-room-plan.md` — 7 units across 4 phases, ~3.5 days estimated.

**Shipped:** the full tool, all 7 units, verified end-to-end.

### Architecture

- **Subpackage**: `pressrow_writer/` at the repo root, separate from `pressrow/` (which doesn't exist yet) and `sections/` (ML runtime)
- **Stack**: Python stdlib only + vanilla JS. No pip deps, no framework, no build step. Matches Morning Lineup discipline.
- **Entry point**: `python3 -m pressrow_writer serve` launches a local HTTP server on `localhost:8787`, opens the browser
- **Aesthetic**: same CSS variables and fonts as Morning Lineup (dark ink, cream paper, gold accents, Playfair / Oswald / Lora / Plex Mono)
- **State discipline**: all progress derived from `pressrow/config/*.json` files — single source of truth, no separate database, no localStorage for canonical data
- **LLM helper**: ported from `sections/columnists.py:142-191` pattern, Anthropic-first with Ollama fallback
- **Atomic writes**: every commit uses temp-file-then-rename so crashes can't corrupt config files

### Three modes, different shapes, different interfaces

- **Chat mode** — task selector (Shadow Personas / Recurring Fans / Feuds) with scrollable conversation and inline committable JSON cards. Production prompts with Morning Lineup tone guardrails for all three tasks. Claude pitches one candidate at a time, you Accept / Discard / Edit, commits write atomically. Verified with a live Ollama conversation that produced a real Pirates persona.
- **Swipe mode** — full-screen card stack for the 270-obsession grind. Reads from a pre-generated batch file at `pressrow_writer/state/batch_obsessions.json`. Three actions: Reject (←), Accept (→), Anchor (space). **The Anchor flow is the highlight** — when you love one obsession, hitting Anchor commits it, calls Sonnet to generate 2 more in the same voice/cadence, and commits all 3. Tested end-to-end with Tony Gedeski and the variants came back with "Ricketts gonna Ricketts" — perfect voice transfer.
- **Card mode** — full-screen ritual editor for the Walk-Off Ghost. Form for name/voice, an oracle panel that calls a low-temperature LLM for one cryptic fragment at a time (second-person, no player names, physical venue detail required). You Keep / Dismiss / Whisper Again until you have 3-5 samples, then "Seal the Ghost" commits to `cast.json`. The oracle whispered *"You saw the paper cup in the seat tremble as the bat's crack split the night's hum"* on first try — nailed the constraints.

### The batch obsession generator (the Swipe feeder)

Separate CLI subcommand: `python3 -m pressrow_writer batch`. Loops through all 90 writers sequentially, calls Sonnet once per writer for 9 candidate obsessions, writes to `pressrow_writer/state/batch_obsessions.json`. Smoke-tested with `--limit 2 --ollama` producing 18 well-formed candidates. Estimated ~$0.30 total cost for a full 90-writer run against Sonnet, ~15-25 minutes of runtime. This is the overnight step before a Swipe session.

### Progress header + celebration

Sticky top-of-page task chips showing `T1 0/90 · T2 0/30 · T3 0/15 · T4 0/10 · T5 ⚪`. Click a chip to jump to its mode. Every commit refreshes the count. When all five tasks hit their targets, a celebration overlay fades in.

## Where it stands right now

**Verified end-to-end:**
- Server starts, all 90 writers load, all API endpoints respond
- Chat mode — real Ollama conversation produced a committable Pirates persona, Accept wrote atomically, progress header updated
- Swipe mode — full flow with accept/reject/anchor against a fake batch, Anchor produced 2 voice-matched variants via Sonnet
- Card mode — oracle generates proper cryptic fragments, ghost commit writes to `cast.json`, T5 flips to complete

**Verified but untuned:**
- Chat prompts are production-shape but never subjectively graded for content quality
- Batch generator works but my 2-writer smoke test showed qwen has a bullpen-heavy bias — variety needs tuning
- Anthropic path only tested for Anchor variants, not Chat or Oracle

**Missing but acknowledged:**
- No `pressrow_writer/README.md`
- No automated tests
- No real multi-hour usage session
- No mobile/touch testing on Swipe
- No edit-as-card path for existing committed entries
- Replace-confirmation modal for anchor-over-existing is silent

Full retrospective on what we lost to single-session pacing is in the conversation history.

## File inventory

```
morning-lineup/
├── docs/
│   ├── future/
│   │   ├── pressrow.py                             (shelved v1 prototype)
│   │   └── pressrow-README.md
│   ├── ideation/
│   │   └── 2026-04-12-press-row-pop-ideation.md
│   ├── brainstorms/
│   │   └── 2026-04-12-press-row-v2-brainstorm.md
│   └── plans/
│       ├── 2026-04-12-001-feat-press-row-v2-plan.md
│       ├── 2026-04-12-002-press-row-v2-authoring-work-plan.md
│       └── 2026-04-12-003-feat-press-row-writers-room-plan.md
└── pressrow_writer/
    ├── __init__.py
    ├── __main__.py              (CLI: serve / batch)
    ├── server.py                (stdlib HTTP server + routing)
    ├── routes.py                (all API handlers)
    ├── llm.py                   (Anthropic → Ollama fallback)
    ├── config_io.py             (atomic writes, loaders)
    ├── progress.py              (task completion derivation)
    ├── writers.py               (loads 90 writers from teams/*.json)
    ├── util.py                  (handle/initials/json helpers)
    ├── batch_obsessions.py      (overnight seed script)
    ├── prompts/
    │   ├── __init__.py
    │   ├── chat_shadow_personas.py
    │   ├── chat_recurring_fans.py
    │   ├── chat_feuds.py
    │   ├── batch_obsessions.py
    │   ├── anchor_variants.py
    │   └── card_ghost.py
    ├── state/                   (runtime state dir)
    └── static/
        ├── index.html           (single-page shell)
        ├── styles.css           (Morning Lineup palette)
        ├── app.js               (mode switching, progress, celebration)
        ├── chat.js              (chat conversations)
        ├── swipe.js             (card stack + anchor)
        └── card.js              (ghost conjuring booth)
```

## How to actually use this

```bash
# One-time: pre-generate obsession candidates (overnight, ~15-25 min, ~$0.30)
export ANTHROPIC_API_KEY=...
python3 -m pressrow_writer batch

# Main session: launch the tool and grind
python3 -m pressrow_writer serve
# → opens localhost:8787
# → work through Chat (T2, T3, T4), Swipe (T1), Card (T5)
# → all commits write directly to pressrow/config/*.json
# → celebration fires when 5/5 tasks complete
```

---

## Next up: the Research Agents

The Writer's Room solves the authoring friction, but it doesn't solve the *content intelligence* gap. Right now the Swipe mode's batch generator seeds candidates from the writer's persona + a voice sample and nothing else. Sonnet writes obsessions in a vacuum. That's why the test batch skewed bullpen-heavy for everyone — the model has no real fuel.

The next piece is a fleet of per-team research agents — one per MLB team, recreated from the same template — that continuously monitor each club's actual happenings. What Reddit (`r/CHICubs`, `r/NYYankees`, `r/LetsGoPeay`, etc.) is grinding on right now. What the local beat reporters are writing. What the trade rumor mill is saying. What yesterday's game actually meant to the fan base — not just the box score but the mood.

Each agent digests this into a small JSON brief per team per day: *current controversies, trending grievances, lineup debates, fan mood, hot-button topics, recent incidents*. The brief becomes fuel for every downstream system in the Press Row universe.

### How it plugs into what we built today

- **Swipe mode's batch generator becomes dramatically better.** Instead of `batch_obsessions.py` calling Sonnet with just the writer's persona, it includes the team's current research brief. Tony Gedeski's obsession candidates stop being generic bullpen complaints and start being *"the way Counsell yanked Leiter on Tuesday"* or *"Jed Hoyer's silence on the trade deadline rumors this week"*. The candidates get specific in a way that makes curation feel like you're reacting to reality, not synthetic content.

- **Chat mode gets smarter too.** When JB pitches a shadow persona for the Padres in Chat, Claude's response could be informed by "Padres fans are currently arguing about X." The persona suggestions become timely, not generic.

- **Press Row 2.0 runtime is the biggest beneficiary.** The brainstorm's Comedy Editor Pipeline, Beef Engine, and Writer Memory systems all hunger for specificity. A per-team research brief is exactly the raw material those systems need — it's the "what just happened in the world" input that keeps writers in character AND makes their takes feel connected to reality.

### The architectural shape

Research agents should sit in a new subpackage — `research/` or similar — each running as an async scheduled job that writes to `data/research/{team_slug}-{date}.json`. Same architecture pattern we already committed to: each agent is a separate process writing to a JSON artifact that downstream systems read. The Writer's Room's batch generator, Press Row's runtime pipeline, and any future feature can all consume the same brief without coupling.

Each agent's job:
1. Scrape its team's Reddit (hot posts, top comments from last 24h)
2. Pull recent news from a small whitelist of beat-writer sources
3. Monitor the team's official transactions + injury feeds
4. Synthesize into a structured brief: `{controversies, trending_topics, fan_mood, recent_incidents, lineup_debates, trade_rumors}`
5. Write `data/research/{team_slug}-{date}.json` atomically

And because it's one template recreated 30 times, the effort to support a new team is zero — you just run the factory.

### Where it fits in the build order

The research agents are a *prerequisite improvement* for the Writer's Room Swipe mode and for Press Row 2.0 Phase 1 (Comedy Editor Pipeline). They don't block the Writer's Room from being usable today — you can still grind through obsessions with the current generic-batch output. But the research agents would turn the Writer's Room from "edit LLM drafts" into "curate drafts that feel like they were written by someone who actually watches this team" — which is a completely different quality floor.

**Open question worth deciding before building:** do research agents feed the Writer's Room first (so JB's authoring session benefits from them), or Press Row 2.0 first (so the daily runtime feed benefits)? Probably both, since the brief artifact is the same, but build-order matters for validation.

---

## What to do next

1. **Actually use the Writer's Room for 20 minutes.** That's the single biggest feedback loop we skipped today.
2. **Decide on research agents.** Plan + ideate them as a separate unit, then build the per-team template.
3. **Iterate on Chat / batch prompts** based on the feedback from #1.
4. **Write `pressrow_writer/README.md`** so the tool is legible if you come back to it in weeks.
5. **Start Press Row 2.0 Phase 0** once the Writer's Room has produced real config data.
