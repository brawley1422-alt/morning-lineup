---
date: 2026-04-12
topic: press-row-v2
source_ideation: docs/ideation/2026-04-12-press-row-pop-ideation.md
---

# Press Row 2.0 — Integrated Brainstorm

## The Vision

Press Row is a fictional MLB beat-writer universe. 90 characters with worldviews, grudges, receipts, and running bits. Each morning, yesterday's real games give them raw material — and an opinionated content pipeline turns that material into a feed that's actually funny, actually continuous, and actually worth coming back to.

The prototype failed because it was *one LLM call that hoped for banter*. Press Row 2.0 treats banter as architecture: pre-compute who's mad at whom, make writers remember their own history, seed each writer with hand-authored obsessions, and run a two-pass editor to kill LLM slop.

**The spine:** state (obsessions, memory, relationships) → pre-computation (beefs, angles, events) → focused per-writer generation → editor rewrite pass → render.

## Shared Infrastructure (the prerequisites)

Before any feature lands, four infrastructure changes need to exist:

### I1. One-writer-at-a-time generation loop
Replace the monolithic "generate 25 tweets" call with `for writer in active_writers: generate_tweet(writer)`. This is NOT one of the 7 ideas — it's the foundation every idea assumes.

**Why:** Focused calls let an 8B model inhabit one character. Bulk calls flatten every persona into the model's averaged voice.

**Cost:** 20-30 sequential LLM calls per build instead of 1. At Ollama local speeds (~3-5s per call), that's 1-3 minutes per build. Acceptable for once-daily static builds.

### I2. Per-writer state directory
New directory: `data/pressrow/writers/{handle}.json`. Stores each writer's memory, predictions, obsessions state, current beef targets, mood. Read at build start, written at build end.

**Structure:**
```json
{
  "handle": "tony_gedeski",
  "last_tweets": [
    {"date": "2026-04-11", "text": "...", "type": "original"},
    {"date": "2026-04-10", "text": "...", "type": "reply"}
  ],
  "predictions": [
    {"date": "2026-04-03", "text": "Ricketts trades Bellinger by July", "resolved": false}
  ],
  "active_beefs": ["jack_durmire"],
  "mood": "bitter",
  "last_signature_use": "2026-04-11"
}
```

### I3. Shared cast config
New file: `data/pressrow/cast.json`. Everything auto-loadable that doesn't live in team JSONs: recurring fans, walk-off ghost identity, shadow personas, current breakdown writer, daily feud arc state.

### I4. LLM call discipline
A single `_llm_call(prompt, max_tokens, model_pref)` helper in `pressrow/llm.py`. Handles Ollama → Anthropic fallback. All 7 features use this — no duplicated retry/timeout logic.

---

## The 7 Features

### Feature 1: The Comedy Editor Pipeline

**The three passes:**

1. **Angles (per writer, cheap local call)** — Ollama prompt: "Given yesterday's game facts + this writer's obsessions, generate 3 possible angles as JSON. stat_angle, narrative_angle, grievance_angle. One sentence each."

2. **Draft (per writer, focused local call)** — Ollama prompt: "You are {writer}. Here are 3 angles. Pick the PETTIEST one — the one your character would choose to be annoying. Write a tweet to that angle. Max 240 chars. Required: name one real player, include one specific number, convey one emotion (petty/smug/doom/cope)."

3. **Edit (per tweet, Sonnet if available, Ollama otherwise)** — "This tweet is 6/10. Rewrite to 9/10. Cut any phrase a ChatGPT assistant would write (no 'buckle up,' 'what a night in baseball,' 'folks,' 'speaking of,' 'meanwhile'). Add one unexpected specific detail. Keep the voice. Return only the rewritten tweet."

**Data model:** Each tweet in the cache gets `draft_text` and `final_text` fields so you can inspect before/after for QA. Add a `premise` field storing the selected angle.

**Per-tweet token cost (Sonnet editor):** ~300 input + 60 output × 3 passes = ~1100 tokens per tweet. 25 tweets × $3/M input + $15/M output = ~$0.12/day. Negligible.

**Failure mode:** If any pass returns junk, fall back to the previous pass's output. If all three fail, drop the tweet.

**Open questions:**
- Should angles be visible to readers as "director's commentary" behind a toggle? Probably no — kills the magic.
- Should the editor pass have a budget limit? (e.g., max 15 tweets get the Sonnet treatment, the rest ship as drafts)

---

### Feature 2: Writer Obsession Config

**The config structure:** Extend `teams/{slug}.json` columnists array:

```json
{
  "name": "Tony Gedeski",
  "role": "The Pessimist",
  "obsessions": [
    {
      "topic": "bullpen usage",
      "angle": "thinks Counsell over-manages by 30%",
      "trigger_phrases": ["bullpen", "reliever", "warmed up"]
    },
    {
      "topic": "Ricketts ownership",
      "angle": "still mad about the 2020 Bryant trade rumor",
      "trigger_phrases": ["ownership", "trade", "budget"]
    },
    {
      "topic": "day baseball",
      "angle": "believes night games at Wrigley are heresy",
      "trigger_phrases": ["lights", "night game", "prime time"]
    }
  ]
}
```

**Injection into prompts:** Every draft prompt includes: "Your obsessions: [topic] — you believe [angle]. At least 50% of your tweets should pivot back to one of your obsessions, whether or not it's directly relevant."

**Shadow personas:** A new `shadow_personas` array in each team JSON. These are 4th personas (total of 30, one per team) who only tweet about one hyper-specific thing:
```json
"shadow_personas": [
  {
    "name": "Bullpen Hawk",
    "handle": "bullpen_hawk",
    "monomaniac_topic": "Cubs bullpen usage patterns",
    "post_probability": 0.3
  }
]
```

Shadow personas tweet ~30% of days, never reply, never quote-tweet. They're the running gag.

**Authoring cost:** 90 writers × 3 obsessions = 270 obsessions. ~5-10 min each to write well. JB = one weekend of writing. Can be done incrementally — start with 1 obsession per writer, expand later.

**Open questions:**
- Should shadow personas be named + visible, or pseudonymous "The Bullpen Hawk"-style? (Pseudonymous is funnier.)
- How heavy-handed should the obsession injection be? Too heavy = caricature. Too light = back to generic. Start at 50% and tune.
- Do obsessions drift over time or stay fixed? (Fixed for v1 — drift is a v2 concern.)

---

### Feature 3: Per-Writer Memory (The Receipt Drawer)

**Memory injection into drafts:** Every draft prompt gets appended: "Your last 3 tweets were: [tweet 1] [tweet 2] [tweet 3]. Do not repeat yourself. You may reference, build on, or contradict your own past take. If you made a prediction that has now resolved, acknowledge it."

**Prediction extraction:** After each day's generation, run a cheap classifier pass (Ollama, single prompt): "Does this tweet contain a prediction about the future? If yes, extract: what is predicted, by when, how we'd know it came true/false. JSON only." Store resolved predictions in the writer's state file with a `resolves_by` date.

**Resolution check:** At build start, check each unresolved prediction against yesterday's real data. If a prediction resolved, mark it `resolved: true` and set `outcome: "hit" | "miss"`.

**The callback mechanic:** During generation, if another writer is building their angle, inject: "RECEIPTS AVAILABLE: @tony_gedeski predicted on April 3rd that Ricketts would trade Bellinger by July. That prediction has now missed (he's still on the roster). You may quote-tweet the original with a dunk or a victory lap."

Not every writer uses the receipt every day. Rare use = high impact.

**Data model:** `data/pressrow/writers/{handle}.json` as shown in I2.

**Open questions:**
- Memory window size — 3 tweets or 5 or everything? (3 for context budget, 5 if Sonnet.)
- How long do predictions live? (30 days default, some predictions are open-ended.)
- Should receipts be quote-tweetable ONLY by rival-team writers, or anyone? (Anyone — it's funnier when your own Optimist teammate dunks on your Pessimist.)

---

### Feature 4: The Beef Engine

**The DAG generation pass (pre-draft):** Before any tweets are written, a planning LLM call builds today's interaction graph. Prompt: "Given these writers [list] and yesterday's game results [digest] and current active beefs [list], generate a JSON array of ~8 interactions. Each interaction is a root tweet + 1-2 replies/quotes. Specify writer IDs, interaction types, and a one-line intent for each."

Example output:
```json
[
  {
    "id": "thread-1",
    "root": {"writer": "tony_gedeski", "intent": "dunk on Cubs bullpen, Ricketts jab"},
    "replies": [
      {"writer": "bee_vittorini", "intent": "naive optimism, defends Hoerner's 2-RBI night"},
      {"writer": "walt_kieniewicz", "intent": "dry stat correction, uses signature phrase"}
    ]
  }
]
```

Then draft generation walks the DAG, generating each tweet with full parent-tweet context. Replies know what they're replying TO in detail, not just an ID.

**Persistent rivalries:** New file `data/pressrow/relationships.json`:
```json
{
  "feuds": [
    {
      "id": "tony-vs-jack",
      "writers": ["tony_gedeski", "jack_durmire"],
      "origin": {"date": "2026-03-15", "event": "Tony called Arizona 'baseball purgatory' in spring training"},
      "running_tally": {"tony_gedeski": 4, "jack_durmire": 3},
      "current_phase": "escalating",
      "last_interaction": "2026-04-10"
    }
  ]
}
```

**The daily feud arc:** One feud per day gets "featured" — guaranteed 2-3 tweet thread advancing the arc, injected into the DAG before other interactions.

**Seeding:** Start with 5-10 hand-authored feuds (Cubs vs. Cardinals, Yankees vs. Red Sox cross-team pessimists, Dodgers optimist vs. Padres pessimist). Let the system generate new ones organically as writers interact.

**Open questions:**
- Cap on active feuds — after how many does it become noise? (10 active max.)
- Do feuds resolve or last forever? (Some resolve in a burst, most fade. Add `status: active | dormant | resolved`.)
- Should readers see the relationships.json as a "Rivalries" sidebar? (Maybe v2. Start subtle.)

---

### Feature 5: Letters to the Editor (Recurring Cast)

**The cast file:** `data/pressrow/recurring_fans.json`:
```json
[
  {
    "name": "Marge from Toledo",
    "team_slug": "tigers",
    "voice": "60s divorcée, three cats, watches every game, unhinged but loving",
    "state": {
      "mood": "reflective",
      "recent_life_events": ["started pottery class"],
      "current_grudge": "Jake Rogers' catching setup"
    },
    "post_probability": 0.6
  },
  {
    "name": "Big Steve, Section 104",
    "team_slug": "phillies",
    "voice": "loud guy at the game, knows every usher by name",
    "state": {
      "mood": "fired up",
      "recent_life_events": ["started Phillies fan club at work"],
      "current_grudge": "anyone who leaves before the 9th"
    },
    "post_probability": 0.5
  }
]
```

**Generation:** For each daily build, 3-5 fans post letters. Prompt per fan: "You are [name], [voice]. Your current state: [state]. Yesterday your team [team] [result]. Write a 100-150 word letter to the editor. Stay in character. Advance your state by +1 beat (one small life update)."

**State advancement:** After generation, a classifier call extracts updated state from each letter: "Did Marge mention a new life event? What is her new mood?" Update the JSON.

**Writer reply hook:** 20% of letters get a writer reply — one of the 90 writers chimes in. ("Tony Gedeski replied: 'Marge, you're the only person in Toledo who still has hope. Bless you.'")

**Render format:** A distinct "Letters" block in the Press Row section, styled like a newspaper letters column (narrower, italic attributions, different typography from the tweets).

**Starting cast size:** 15-20 fans. Seed 3-4 per division.

**Open questions:**
- Do fans interact with each other? (v2 — start with just fans → writers.)
- Can fans make predictions too? (Yes, and they should. Adds to the Receipt Drawer.)
- Age/death/retirement of cast members — does Marge ever leave? (v2 concern. For now, fans are permanent.)

---

### Feature 6: Classifieds

**The prompt:** Daily single call: "Generate 5 newspaper classifieds as JSON. Each with: type (help_wanted | missed_connections | for_sale | personals), team_context, text (max 60 words). Voice: bone-dry, specific, absurd. Leverage yesterday's game results: [digest]. Examples: [3 hand-authored examples]."

**Example output:**
```json
[
  {
    "type": "for_sale",
    "team_context": "rockies",
    "text": "FOR SALE: one (1) Rockies 'Believe' t-shirt, worn once in spring training, tags removed but never again. $5 OBO. Will trade for almost anything."
  },
  {
    "type": "missed_connections",
    "team_context": "yankees",
    "text": "MISSED CONNECTION: You were the reliever who threw 97 in the 7th. I was the fan who believed in you. For three pitches. Call me. xxx-CLOSER"
  },
  {
    "type": "help_wanted",
    "team_context": "marlins",
    "text": "HELP WANTED: Starting rotation. Pay negotiable. Must love Miami weather, bring own bullpen. No experience necessary — clearly."
  }
]
```

**Author attribution:** Each classified is attributed to a writer persona — their voice should show through. "PESSIMIST SEEKS reason to watch after Aug 15" is clearly a pessimist. Match the voice to the obsession when possible.

**Render format:** A newspaper-column block (3 columns, tight type, Oswald or Plex Mono for the headers). Distinct visual rhythm from the tweets.

**Open questions:**
- 5 per day or daily rotation among categories? (5 per day with mixed types.)
- Should classifieds link back to writers (click → see their other posts)? (Nice-to-have. v2.)
- Anyone can "reply" to a missed connection? (v2 — a recurring fan replies next day. Big payoff but complex.)

---

### Feature 7: Scheduled Event Programming

**Two events:**

#### 7a. The Breakdown Arc
A 7-day scheduled event that happens 2-3x per season.

**Trigger logic:** Every build, check `data/pressrow/events.json`. If no breakdown is active and random roll < 1/60, pick a random writer to begin a breakdown. Store `breakdown_arc_day: 1` in their state.

**The 7 days:**
1. Subtle — tweets 10% weirder than normal
2. Slipping — tweets reference "tired" or "off night"
3. Unraveling — personal references, odd hour posts
4. Confessional — long thread about something they've never talked about
5. Quiet day — only posts one cryptic thing
6. "Going on leave" — single tweet announcing a break
7. **No tweets that day (absence is the feature)**
8. **Return** — back to normal, but with ONE change: new signature phrase, new obsession, or retired old grudge

**Prompt per day:** The writer's normal generation includes a breakdown context: "You are in day 3 of a slow public unraveling. Your tweets should feel 30% more unhinged than usual. Reference the grind. Mention something personal you'd normally hide."

**Open questions:**
- Random selection or JB picks? (Random for seasonality, with a JB override file `data/pressrow/override.json`.)
- Readers need a way to track/follow — do we surface it? (No. Discovery is the fun.)
- What if the same writer gets picked twice? (Skip. Log in state.)

#### 7b. The Walk-Off Ghost
A persona that ONLY posts when a game ends in dramatic fashion (walk-off HR, extra innings, no-hitter, blown save).

**Identity:** `data/pressrow/cast.json` has one ghost entry:
```json
{
  "name": "Section 214",
  "handle": "section_214",
  "voice": "cryptic, observational, second-person, never names players directly, always mentions a physical detail of the stadium",
  "triggers": ["walk_off_home_run", "walk_off_hit", "extra_innings", "no_hitter", "blown_save_9th"]
}
```

**Trigger detection:** Rule-based scan of yesterday's box scores. If any trigger fires, generate one ghost post.

**Prompt:** "You are Section 214. Last night [triggering event] happened. Write ONE tweet, max 120 characters. Do not name players. Reference a specific physical detail of the venue (a light, a shadow, a sound, a cup, a vendor). Cryptic. Observational. Second person."

**Example:**
> "The light above section 214 flickered twice. The beer vendor stopped pouring. You already knew."

**Render:** Distinct styling — centered, italic, no avatar, timestamp is the exact game-end time. Rare enough to feel like an event when it appears.

**Open questions:**
- One ghost total, or one per team? (One total. Scarcity is the feature.)
- Should the ghost ever be "discovered"? (No. Mystery forever.)

---

## Dependencies & Build Order

```
Phase 0: Infrastructure (required for everything)
  I1. One-writer-at-a-time loop
  I2. Per-writer state directory
  I3. Shared cast config
  I4. LLM call helper

Phase 1: Quality foundation (makes tweets actually good)
  Feature 1: Comedy Editor Pipeline
  Feature 2: Writer Obsession Config (authoring in parallel)

Phase 2: Continuity & character (makes readers come back)
  Feature 3: Per-Writer Memory
  Feature 4: The Beef Engine (depends on Memory for receipts)

Phase 3: Universe expansion (adds texture)
  Feature 5: Letters to the Editor
  Feature 6: Classifieds

Phase 4: Rare moments (appointment viewing)
  Feature 7: Scheduled Events
```

**Minimum viable relaunch = Phase 0 + Phase 1.** Tweets become funny. Everything else compounds.

**Strong relaunch = Phase 0 + 1 + 2.** Characters feel alive. Readers have reason to return.

**Full feature = all phases.** A fictional universe people check on like a comic strip.

## Token Budget (per daily build)

Assuming Sonnet for editor pass and Ollama for everything else:

| Pass | Calls | Tokens each | Total tokens | Sonnet cost |
|------|-------|-------------|--------------|-------------|
| Beef DAG planning | 1 | 3000 in, 1500 out | 4500 | — (Ollama) |
| Angles pre-compute | 25 | 400 in, 200 out | 15000 | — (Ollama) |
| Draft tweets | 25 | 800 in, 150 out | 23750 | — (Ollama) |
| Editor pass | 25 | 500 in, 150 out | 16250 | ~$0.05 |
| Prediction extract | 25 | 300 in, 100 out | 10000 | — (Ollama) |
| Letters generation | 5 | 600 in, 300 out | 4500 | — (Ollama) |
| Classifieds | 1 | 2000 in, 600 out | 2600 | — (Ollama) |

**Total:** ~$0.05-0.10/day in Sonnet, ~3-5 min of Ollama runtime. Fits the one-build-per-day architecture.

## Key Open Questions for JB

1. **Editor pass: always Sonnet or Ollama-only?** Sonnet is ~$1.50/month and dramatically better. I'd argue always Sonnet for this one pass.

2. **Obsession authoring: do you want to write 270 obsessions yourself, or have the LLM seed drafts you edit?** (I recommend LLM drafts + JB edits. ~1 hour of work instead of a weekend.)

3. **Feud seeding: hand-author the first 10 rivalries or let them emerge?** (Hand-author — it's the B-plot and needs authorial intent.)

4. **Recurring fan names: JB picks names/voices or LLM generates?** (JB picks first 10, LLM suggests rest. These are Marge-from-Toledo beloved characters — they need authorial taste.)

5. **The breakdown arc risk: one writer per season having a meltdown could feel cruel or sad. Keep it funny?** (Think Ron Burgundy, not a real mental health spiral. The breakdown is ALWAYS about something petty — bullpen ERA, the designated hitter, a specific umpire. Never about anything heavy.)

6. **Visibility of the receipts/feuds infrastructure:** Do we surface it (a "Rivalries" sidebar, a "Predictions Tracker") or keep it invisible state that only shows up through tweet content? (Invisible for v1. Adding UI for it is a different conversation.)

7. **Do shadow personas exist on the same feed as main writers, or a separate "Sidebar" block?** (Same feed, but clearly marked — they're *known* bit characters, not hidden.)
