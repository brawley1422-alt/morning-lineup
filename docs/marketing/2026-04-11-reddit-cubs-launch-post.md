# r/CHICubs launch post — draft

**Status:** draft, pre-post
**Created:** 2026-04-11
**Target sub:** r/CHICubs (primary), r/baseball (cross-post), r/SideProject, r/InternetIsBeautiful, Hacker News (Show HN)
**Best time to post:** Saturday morning off-day, 8–9am CT
**Author voice:** JB — freight broker, vibe coder, Cubs fan

---

## Title options

1. *I vibe-coded a daily Cubs briefing site while learning AI — looking for feedback*
2. *Freight broker, no coding background — built a Cubs daily briefing site as a way to learn AI*
3. *I made a thing: a newspaper-style daily Cubs briefing. Feedback welcome.*

---

## Body

Hey r/CHICubs —

Quick confession before anything else: **I'm not a developer.** I'm a freight broker in the logistics world and this whole thing started as an excuse to learn how to use AI tools. I describe what I want, Claude builds it, I tweak, I break things, we fix them. That's it. "Vibe coding."

It's called **Morning Lineup** and it's a daily MLB briefing site with a page for every team. Nothing about it is original — everything pulls from the public MLB Stats API, and you can find every individual piece on other sites. What I was after was *one place* that reads like a morning newspaper for your team: lineup, matchup, form, history, standings, news, all on one page, every day, free, no login, no ads.

Live here: **https://brawley1422-alt.github.io/morning-lineup/** → pick Cubs (or any team).

It started as a personal project to read with my coffee. Then I added another team. Then another. Then my buddy asked about the Yankees. Now it's all 30, with stuff I never planned to build, because once you're vibe-coding it's hard to stop.

**I'd love honest feedback.** I can make changes fast — usually same day if it's something small. If something looks broken, reads wrong, or you wish it had a feature, tell me. I'm especially curious what Cubs fans think because I'm one too and this is the page I open every morning.

---

**What's on it (the obvious stuff):**
- Yesterday's game with line score, three stars, and key plays
- Today's matchup with a full scouting report on both starters + recent game logs
- Team leaders, next three games, hot/cold form guide
- Transactions and injured list side-by-side
- Minor league affiliate results + a prospect tracker
- Today's full slate across MLB with live scores
- Division standings + rival results
- Around the League news wire (walk-offs, extras, shutouts, streaks)
- All-division standings + league leaders
- "This Day in Cubs History" (I'm still filling out the database — corrections welcome)

**What's on it (the stuff you won't notice at first):**
- **A full scorecard book embedded in the page** — old-school scorer's notation, pitch-by-pitch, strike zone overlay, SVG diamond with actual baserunning paths. Dark/paper theme toggle. You can open any past game from the scoreboard and score it yourself or watch the scorecard auto-fill.
- **Topps-style flip cards for every player on the 26-man roster.** Click any name in the lineup or scouting report and a card pops up — front has portrait and team-colored banner, flip it for splits, hot/cold strip, and a last-10-games sparkline (OPS for hitters, GameScore for pitchers).
- **A "My Players" section** on the home page where you can follow any player from any team. Browsing the Yankees page? Star Judge, and he shows up on your home dashboard tomorrow alongside Happ and Crow-Armstrong.
- **Daily contextual predictions** on cards for players you follow. The app picks an editorial question for each guy based on their recent form — "Will Bregman climb back above the Mendoza line?", "Will Happ hit HR #5 today?", "Can Imanaga keep carving — 7+ K?". You pick YES or NO before first pitch. Picks lock when the game starts. Next time you open the site, they've quietly resolved while you were gone and your record ticks up in the binder header.
- **Daily editorial lede** at the top of every team page written by a local LLM I have running on my desktop, with an Anthropic API fallback. It's not always great. It's sometimes great.
- **Per-venue weather forecast** on game days (Open-Meteo API).
- **Works offline as a PWA** — add to home screen on mobile and it acts like an app.
- **Adaptive live polling** — when a game's in progress the scores refresh every 20 seconds, otherwise every 5 minutes so it doesn't hammer the API.
- **Team-colored styling for all 30 teams** — primary/accent colors, rival callouts, affiliate minors branding.
- **Deeplinks to any player card** — the URL `/cubs/#p/663538` opens PCA's card. Share it with a buddy.
- **Keyboard-friendly, mobile-first, no tracking, no cookies, no ads.** Ever.

Tech, for anyone curious: Python for the static site generator (MLB Stats API + a local Ollama model for the lede), vanilla JS on the frontend (no React, no framework), GitHub Pages for hosting. Total cost: $0 and a lot of sleep.

If you actually look at it, thank you. If you find a bug or have an idea, even better. This started as a toy and I'm genuinely surprised it turned into something I use every day. Happy to make whatever changes help it be more useful.

Go Cubs.

---

## Pre-post checklist

- [ ] Smoke-test 3 random historical scorecards work end-to-end (past reputation-killer if broken)
- [ ] Confirm `#p/PID` deeplink works on mobile Safari + mobile Chrome
- [ ] Spot-check 3 teams besides Cubs (Yankees, Dodgers, Royals) render cleanly
- [ ] Check the landing page (`/morning-lineup/`) loads fast on a cold cache
- [ ] Verify PWA install prompt behaves (or at least doesn't break)
- [ ] Draft 1–2 canned replies to the most likely bug reports
- [ ] Draft a "here's what I'm working on next" reply for feature requests

## Cross-post variants to draft later

- **r/baseball** — same story, reframe around "built this for all 30 teams" instead of Cubs-specific
- **r/SideProject** — lean into the AI/vibe-coding origin story more, mention Claude by name
- **r/InternetIsBeautiful** — lead with the newspaper aesthetic, less on the stats
- **Hacker News (Show HN)** — technical angle: "Show HN: Daily MLB briefings for 30 teams, built by a non-developer using Claude"
