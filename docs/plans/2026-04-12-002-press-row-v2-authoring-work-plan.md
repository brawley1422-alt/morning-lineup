---
title: "Press Row 2.0 — JB's authoring work (non-engineering)"
type: feat
status: active
date: 2026-04-12
companion: docs/plans/2026-04-12-001-feat-press-row-v2-plan.md
---

# Press Row 2.0 — Your Writing Tasks

Everything in here is **you at a keyboard writing words**, not engineering. No code. Pour coffee, put on music, grind it out.

Total time: **~4 hours of writing**, spread across phases. You can do all of it in a long Saturday morning or break it up over a week.

---

## The Five Tasks At A Glance

| # | Task | File | Time | Phase |
|---|------|------|------|-------|
| 1 | Review + polish 270 obsessions | `pressrow/config/obsessions.json` | ~60 min | Phase 1 (after seed script runs) |
| 2 | Write 30 shadow personas | `pressrow/config/shadow_personas.json` | ~60 min | Phase 1 |
| 3 | Write 15-20 recurring fans | `pressrow/config/recurring_fans.json` | ~60 min | Phase 3 |
| 4 | Seed 10 initial feuds | `pressrow/config/relationships.json` | ~30 min | Phase 2 |
| 5 | Name the Walk-Off Ghost | `pressrow/config/cast.json` | ~15 min | Phase 4 |

**Order matters only for Task 1** — it has to wait until the engineering seed script exists (Phase 1, Unit 5). The other four tasks can be done anytime.

---

## Task 1: Polish 270 Writer Obsessions

**When:** After the engineer runs `python3 -m pressrow seed obsessions` — this creates `pressrow/config/obsessions.draft.json` with LLM-generated candidates.

**What you're doing:** Reading 3 candidate obsessions per writer × 90 writers and keeping the ones that feel right. Editing, replacing, or rejecting the rest. You are NOT writing from scratch — the LLM did the first pass. Your job is taste.

**Time:** ~60 minutes if you move fast. Set a timer. Don't perfect it — "good enough" is good enough.

**Schema** (already created by the seed script, you just edit):

```json
{
  "tony_gedeski": [
    {
      "topic": "bullpen usage",
      "angle": "thinks Counsell over-manages every reliever by 30%",
      "trigger_phrases": ["bullpen", "reliever", "warmed up", "matchup"]
    },
    {
      "topic": "Ricketts ownership",
      "angle": "still mad about the 2020 Bryant trade rumor, brings it up unprompted",
      "trigger_phrases": ["ownership", "trade", "budget", "payroll"]
    },
    {
      "topic": "day baseball",
      "angle": "believes night games at Wrigley are heresy that started the decline",
      "trigger_phrases": ["lights", "night game", "prime time"]
    }
  ],
  "bee_vittorini": [ ... ]
}
```

**What makes a good obsession:**

- **Specific, not vague.** "Hates analytics" is generic. "Thinks every closer should throw 80% sliders and the rest of the league is wrong" is an obsession.
- **Load-bearing.** The writer should pivot to it even when it's not directly relevant. If Tony can't work his obsession into a game recap, the obsession is too narrow.
- **In character.** A Straight Beat writer's obsessions are stat-based grievances. An Optimist's are unironic beliefs in virtues nobody else sees. A Pessimist's are all-caps grudges against ownership/management.
- **Avoid real players by name.** Obsessions should be about *patterns* or *concepts*, not "hates Jon Lester" — players come and go, obsessions stay.

**What to watch for:**

- Repeats across writers — if 5 Pessimists all hate ownership in the same way, differentiate them. One hates the owner personally, one hates the analytics department, one hates the marketing team, etc.
- Too many heavy topics — keep it petty. "Still mad about 2003" is good. "Mourns his father who took him to games" is NOT what this is.
- Straight Beat writers who come out too boring — give them at least one *weird* obsession. Walt Kieniewicz has a thing about infield shifts even though they're banned now. That's funny. "Walt likes fundamentals" is not.

**Editing workflow:**

1. Open `obsessions.draft.json` in your editor.
2. Walk writer by writer. For each, the LLM gave you 3 candidates.
3. Keep 2-3 per writer. Replace any that are weak. Tweak language to match the writer's voice.
4. Save as `obsessions.json` (not `.draft.json`).
5. Done. The engineering side picks it up automatically on the next build.

**If you hate most of the LLM's output:** just rewrite the bad ones from scratch. You know these writers better than the model does. Aim for "good enough to ship," not "publishable."

---

## Task 2: Write 30 Shadow Personas (one per team)

**When:** Phase 1, after the obsessions schema is settled. Can be done in parallel with Task 1.

**What you're doing:** Inventing one pseudonymous lurker persona per team who only tweets about ONE mundane thing, ever. These are the running-gag characters. They're the Bullpen Hawk. The Defensive Shifts Guy. The Grass Length Lunatic. Most days they don't post. When they do, it's an event.

**Time:** ~60 minutes. Faster if you already have ideas.

**File:** `pressrow/config/shadow_personas.json`

**Schema:**

```json
{
  "cubs": {
    "name": "Bullpen Hawk",
    "handle": "bullpen_hawk",
    "monomaniac_topic": "Cubs bullpen usage patterns",
    "voice": "never uses names, refers to relievers by their jersey number and the inning they entered",
    "sample_tweets": [
      "7th inning. #47 for 4 pitches. Hook at 2-1. That's a decision.",
      "Three straight days for #39. Season's long. I'm writing this down."
    ],
    "post_probability": 0.3
  },
  "yankees": {
    "name": "Left Field Cartographer",
    "handle": "lf_cartographer",
    "monomaniac_topic": "Yankees left field defensive positioning",
    "voice": "maps everything in terms of steps from the line",
    "sample_tweets": [
      "14 steps off the line in the 6th. They KNOW where Alonso pulls it. Why."
    ],
    "post_probability": 0.25
  }
}
```

**Required fields:**
- `name` — the persona's pseudonymous handle-name (not a real-sounding person, this is a character)
- `handle` — slug version of the name
- `monomaniac_topic` — ONE thing they tweet about. Narrow.
- `voice` — 1-2 sentences describing how they talk (jersey numbers only, all caps, second-person, etc.)
- `sample_tweets` — 1-2 example tweets so the LLM has something to mimic
- `post_probability` — 0.15-0.35 range. Scarcity is the feature.

**How to brainstorm 30 of these fast:**

Go division by division. For each team, ask yourself: *what's the one tiny, nerdy, specific thing a hardcore fan of this team would be irrationally focused on?*

- **Cubs** — bullpen management (Counsell's an easy target)
- **Yankees** — defensive positioning, or short porch strategy
- **Dodgers** — spin rate obsession
- **Astros** — launch angle in away ballparks
- **Red Sox** — Green Monster carom angles
- **Rockies** — humidor readings and altitude physics
- **Pirates** — prospect call-up timing
- **Rays** — platoon matchups
- **Brewers** — infield shift quirks
- **Mariners** — runners-in-scoring-position analytics
- **Giants** — Oracle Park wind speed charts
- **Padres** — Petco's marine layer effects on fly balls
- **Phillies** — pitch mix against lefties
- **Braves** — batting practice takes
- **Cardinals** — "Cardinals way" fundamentals nitpicks
- **Blue Jays** — batting order decisions
- **Orioles** — prospect rankings
- **White Sox** — ballpark attendance complaints
- **Mets** — spending vs performance ratios
- **Nationals** — rebuild timeline obsessives
- **Guardians** — contact rate
- **Tigers** — rebuild progress tracker
- **Twins** — closer situation
- **Royals** — speed/basestealing
- **Angels** — Ohtani workload
- **Athletics** — stadium drama (obviously)
- **Marlins** — attendance figures
- **D-backs** — humidor differences
- **Rangers** — temperature-vs-offense correlations
- **Reds** — Great American Ballpark dimensions gripes

Don't stress about getting each one perfect. Good names are funnier than precise topics. **"Bullpen Hawk" is better than "Reliever Usage Analyst."**

**Tone anchor:** these are all eccentric-expert characters. Think "the guy at the bar who's been to 300 games this year and has a spreadsheet." Not grumpy, just narrowly obsessed. Sincere within their niche.

---

## Task 3: Write 15-20 Recurring Fans (Letters to the Editor)

**When:** Phase 3, before Unit 8 ships. Can be done anytime.

**What you're doing:** Inventing the small-town cast of fictional fans who write letters to the Press Row editor. These are the Marge-from-Toledo beloved characters. They have names, voices, ongoing life situations. People should ask "what did Marge say today?"

**Time:** ~60 minutes.

**File:** `pressrow/config/recurring_fans.json`

**Schema:**

```json
[
  {
    "name": "Marge from Toledo",
    "team_slug": "tigers",
    "voice": "60s divorcée, three cats, watches every Tigers game, calls the dugout 'the fellas,' writes with affection and zero analysis",
    "starting_state": {
      "mood": "reflective",
      "recent_life_events": ["just started a pottery class at the community center"],
      "current_grudge": "Jake Rogers' catching setup, she can't explain why"
    },
    "post_probability": 0.55
  },
  {
    "name": "Big Steve, Section 104",
    "team_slug": "phillies",
    "voice": "loud, Italian, knows every usher by name, thinks leaving before the 9th is a federal crime",
    "starting_state": {
      "mood": "fired up",
      "recent_life_events": ["started an unofficial Phillies fan club at his HVAC company"],
      "current_grudge": "anyone who leaves early, which is everyone but him"
    },
    "post_probability": 0.5
  },
  {
    "name": "Dale the Conspiracy Guy",
    "team_slug": "athletics",
    "voice": "sees patterns nobody else sees, uses the phrase 'follow the money' unironically, 70% of his letters are about the stadium situation",
    "starting_state": {
      "mood": "agitated",
      "recent_life_events": ["filed a FOIA request with the city of Oakland"],
      "current_grudge": "John Fisher, everything about John Fisher"
    },
    "post_probability": 0.6
  }
]
```

**Required fields:**
- `name` — full character name with a geographic or location tag (From Toledo, Section 104, etc.)
- `team_slug` — which team they root for
- `voice` — 2-3 sentences describing how they talk and what they care about
- `starting_state.mood` — one word (reflective, fired up, agitated, bitter, hopeful)
- `starting_state.recent_life_events` — 1-2 specific life things they're going through (the LLM will advance these day by day)
- `starting_state.current_grudge` — what they're currently mad about (can be baseball or tangentially related)
- `post_probability` — 0.35-0.65. Higher = more prolific.

**What makes a good recurring fan:**

- **They have a LIFE outside baseball.** Marge takes pottery. Big Steve runs a fan club. Dale files FOIA requests. The life stuff is what makes readers care.
- **Baseball is the wrapper, not the point.** Dale's letter about an Athletics game is really about his vendetta against the owner. Marge's letter about a Tigers loss is really about how she misses her son who moved to Denver.
- **Their voice is unmistakable in one sentence.** Marge opens with "Dear Editor, I hope this finds you well." Big Steve opens with "LISTEN." Dale opens with "I'm not saying it's connected, but..."
- **Give them geographic specificity.** "From Toledo" is better than "From Ohio." Section 104 is better than "at the stadium." Specificity sells the character.

**How to come up with 15-20 fast:**

Pick 3-4 fans per division. For each, answer:
1. Are they upbeat, neutral, or unhinged?
2. What's their non-baseball life thing?
3. What's their baseball grudge?
4. How do they talk?

Make at least 2 of them deeply weird. Dale the Conspiracy Guy is an anchor. Every universe needs a Dale.

**Tone guardrails:**
- No real tragedies (no deaths, no illness, no heavy family stuff). Keep it sitcom-warm.
- Grudges can be petty — that's the point.
- Make a couple of them *kinder* than the writers. The writers are cynical pros. The fans should have some warmth.
- Marge calls the players "the fellas." Find little linguistic tics like this for every fan.

**Suggested starter cast to brainstorm around:**
- Marge from Toledo (Tigers) — the classic warm grandma archetype
- Big Steve, Section 104 (Phillies) — loud guy at the game
- Dale the Conspiracy Guy (Athletics) — essential universe anchor
- Pastor Ramón (Marlins) — preaches hope against all evidence
- Barb from the Bar (Twins) — bartender who watches every game on the TV behind the taps
- Little Timmy (Mets) — 11-year-old kid who writes in crayon (conceptually — really an adult writing in that voice)
- The Retired Scout (Dodgers) — uses decades-old scouting language nobody uses anymore
- Donna the Vendor (Red Sox) — sold peanuts at Fenway for 40 years
- Carl from Cleveland (Guardians) — still mad about the name change
- The Anonymous Player's Wife (variable team, switches teams when traded) — recurring running gag
- Phil the Statistician (Rays) — actual real stat nerd, the one counterbalance to Tony-from-Section-104 types

Fill in the rest from there. You don't need all 20 on day one — start with 10, add more as the feature matures.

---

## Task 4: Seed 10 Initial Feuds

**When:** Phase 2, before Unit 7 ships.

**What you're doing:** Writing the opening state of 10 persistent writer rivalries. Each feud has an origin story (what kicked it off), opening tally, and a current phase. The Beef Engine picks one per day to feature.

**Time:** ~30 minutes.

**File:** `pressrow/config/relationships.json`

**Schema:**

```json
{
  "feuds": [
    {
      "id": "tony-vs-jack",
      "writers": ["tony_gedeski", "jack_durmire"],
      "origin": {
        "date": "2026-03-15",
        "event": "Tony called Arizona 'baseball purgatory' in a spring training column. Jack responded by calling the Cubs 'the Marlins with ivy.'"
      },
      "running_tally": { "tony_gedeski": 4, "jack_durmire": 3 },
      "current_phase": "escalating",
      "topic": "whose rebuild is more embarrassing",
      "last_interaction": "2026-04-09"
    },
    {
      "id": "marty-vs-raymond",
      "writers": ["marty_slutskoff", "raymond_tortorelli"],
      "origin": {
        "date": "2026-03-22",
        "event": "Marty (White Sox Straight Beat) wrote that the Yankees pinstripes were 'accounting dressed up as tradition.' Raymond responded by calling Comiskey 'a concrete crime scene.'"
      },
      "running_tally": { "marty_slutskoff": 2, "raymond_tortorelli": 5 },
      "current_phase": "dormant",
      "topic": "legacy vs payroll",
      "last_interaction": "2026-04-05"
    }
  ]
}
```

**Required fields:**
- `id` — kebab-case unique ID (use handles)
- `writers` — the two writer handles
- `origin.date` — when the feud started (can be March for spring training, or any prior date)
- `origin.event` — 1-2 sentence origin story. This is what gets injected into the LLM when the feud is featured.
- `running_tally` — dict with current "wins" for each side (hand-set the opening numbers)
- `current_phase` — one of: `active`, `escalating`, `dormant`, `resolved`
- `topic` — what the feud is really about
- `last_interaction` — date of most recent exchange (set to a past date so the feud picker fires it soon)

**How to pick your 10 feuds:**

Aim for variety across all four quadrants:

**Cross-team rivalries (4-5 feuds):**
- Cubs vs Cardinals Pessimist (the natural rivalry)
- Yankees vs Red Sox Pessimists (classic)
- Dodgers Optimist vs Padres Pessimist
- Mets Pessimist vs Phillies Straight Beat
- White Sox vs Cubs (cross-town)

**Same-team internal beefs (2-3 feuds):**
- Cubs Pessimist vs Cubs Optimist (Tony vs Bee — the internal schism)
- Red Sox Straight Beat vs Red Sox Pessimist (stats vs vibes)
- Mets internal — because of course

**Weird/cross-division beefs (2-3 feuds):**
- Rockies Straight Beat vs Marlins Straight Beat — a running argument about which franchise is more irrelevant, with neither writer actually wanting to win
- Athletics Pessimist vs Rays Pessimist — "whose ownership is worse" 
- A's vs Brewers — competing small-market griefs

**Phase distribution:**
- 2 in `escalating` (active and getting worse)
- 4 in `active` (ongoing, featured sometimes)
- 3 in `dormant` (exists but hasn't fired recently — the engine will reactivate)
- 1 in `resolved` — deliberately set one to "resolved" as a reference state

**Writing the origin events:**

Keep them short and specific. One sentence of action, one sentence of reaction. Example: "Tony called Arizona 'baseball purgatory' in a spring training column. Jack responded by calling the Cubs 'the Marlins with ivy.'" That's enough for the LLM to carry.

Avoid origin events that require complex context. If you find yourself writing a paragraph, you're over-engineering.

---

## Task 5: Name and Voice the Walk-Off Ghost

**When:** Phase 4, before Unit 10 ships. This is the shortest task.

**What you're doing:** Inventing the identity of one cryptic persona who ONLY posts when a game ends dramatically (walk-offs, no-hitters, extra innings 12+, blown saves in the 9th). Never names players. Always cryptic. Always mentions a physical detail of the stadium.

**Time:** ~15 minutes.

**File:** `pressrow/config/cast.json` (add the ghost entry)

**Schema:**

```json
{
  "walkoff_ghost": {
    "name": "Section 214",
    "handle": "section_214",
    "voice": "cryptic, observational, second-person. Never names players or teams directly. Always mentions one specific physical detail of the venue — a light, a shadow, a sound, a vendor, a cup, a railing. Tweets are always ≤120 characters. Never replies, never quote-tweets.",
    "sample_tweets": [
      "The light above section 214 flickered twice. The beer vendor stopped pouring. You already knew.",
      "Concrete was humming at the exits. Nobody left.",
      "A paper cup rolled from row 12 to row 8. The game came with it."
    ]
  }
}
```

**Required fields:**
- `name` — the persona's "name" (really a location code or poetic tag — not a human name)
- `handle` — slug
- `voice` — 2-3 sentences of strict constraints
- `sample_tweets` — 3 examples that nail the voice

**Naming options to consider:**

- `Section 214` — the classic, works anywhere
- `The Upper Deck` — more poetic
- `The Gate C Witness` — more specific, more mysterious
- `The Long Pour` (a bartender-ghost framing)
- `Row F` — short, haunting

Pick one. Don't overthink it. **Scarcity and voice are the feature, not the name.**

**Voice anchors:**

- Second person, always. "You already knew."
- Never names players. "#47 homered" is banned. "The one in center" is fine.
- Always include a physical detail. A light, a beer vendor, a paper cup, a concrete hum, a railing, a jacket on an empty seat.
- Cryptic, not obscure. Readers should feel the weight, not struggle to understand.
- No emotions stated, only observed. Not "the crowd was stunned." Instead: "no one stood up."

**Write 3 sample tweets.** These are the only things the LLM will see to mimic the voice, so they need to nail it. Use the shelved prototype's CSS `.pr-ghost` styling — centered, italic, no avatar.

---

## Working Session Tips

**Put music on.** This is vibe work, not engineering.

**Don't perfect. Ship.** Every task has a "good enough to generate" bar. Hit the bar, commit, move on.

**Batch by task, not by team.** Do ALL the obsessions in one sitting, ALL the fans in another. Don't try to write a Cubs shadow persona + Cubs obsessions + Cubs recurring fan in one session. The mental context switching kills the voice.

**Keep a scratch file.** Not every idea fits where you first put it. If you come up with a great recurring fan while writing obsessions, drop it in a scratch markdown file to use later.

**Read out loud.** The voice test is: does it sound like that character when you say it? If it sounds like ChatGPT, rewrite it.

**Your writers are already cast.** You wrote them months ago and they've been running in the columnists feature. Go read some existing columns in `sections/columnists.py` output before starting Task 1 — your writers already have voices you can tune to.

---

## Handoff Back to Engineering

For each task, the handoff is just "the file exists and is valid JSON." The engineering side picks everything up automatically on the next build.

**Validation checklist after each task:**
- [ ] File saved to the right path
- [ ] Valid JSON (open in an editor with syntax highlighting, or run `python3 -m json.tool pressrow/config/X.json`)
- [ ] Required fields present
- [ ] No obvious typos in handles (they need to match the writer handles exactly — `tony_gedeski` not `Tony_Gedeski`)

When you finish a task, drop a note in the chat: "Task 2 done, 30 shadow personas written" and the next engineering unit can proceed.

---

## Time Budget Reality Check

If the 4-hour estimate slips, here's the minimum-viable-authoring version:

- **Task 1 (obsessions):** Ship with 1 obsession per writer instead of 3. Takes ~20 min. You can expand later.
- **Task 2 (shadow personas):** Ship 15 instead of 30 (just one division's worth at launch, expand later).
- **Task 3 (recurring fans):** Ship 8-10 fans instead of 20. The feature still works.
- **Task 4 (feuds):** Ship 5 instead of 10.
- **Task 5 (ghost):** Cannot be shortened; it's already 15 minutes.

Absolute minimum time to ship: ~90 minutes. Full quality: ~4 hours. Pick your comfort level.
