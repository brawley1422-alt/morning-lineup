# Morning Lineup — Launch Day Checklist

A 3-day staggered rollout. Soft launch, then broad, then technical. No
upvote rings, no friends-and-family boosts, no "growth hacks" that
aren't just showing the work.

The core rule across all three days: **content-first framing beats
feature-pitch.** Lead with a specific stat or observation that lives
inside the product. Never lead with "I built a thing." People click
stats. They scroll past tool launches.

---

## Day 1 — r/CHICubs (soft launch)

**Why first:** friendly, small, high signal. The single-team framing
is honest — this was built because JB wanted to read about the Cubs
every morning. If the post belly-flops here, pause and diagnose
framing before touching r/baseball or HN.

**Post format:**

- **Title:** a content-first line referencing a specific Cubs stat
  visible on the page. Example: *"Cubs have the worst April bullpen
  ERA since 2017 — here's the breakdown"*. Title names the stat, not
  the product.
- **Body:** 2–3 sentences of context around the stat. One link at the
  end to the Cubs page: `https://brawley1422-alt.github.io/morning-lineup/cubs/`.
- **Image:** one screenshot of the relevant section on the Cubs page
  (bullpen leaders or Around-the-League splits). Crop to just that
  block; no full-page shot.
- **Flair:** whichever r/CHICubs flair fits "Discussion" best.

**Timing:** weekday morning ET, before a marquee Cubs game that day if
the schedule allows. Morning traffic in a team sub peaks between the
alarm clock and lunch.

**Response window:** check replies every 15–30 minutes for the first
4 hours. Reply to every comment, even the nitpicks. First-hour
engagement drives the sub's own ranking.

**Success signal:** any upvotes + any comments that aren't "cool,
thanks." Not a number target — a temperature check. If the post dies
flat (no comments, zero upvotes), pause Day 2, rewrite framing, try a
different angle at r/CHICubs or another team sub (r/Yankees,
r/mlbtheshow) before cascading a bad framing.

---

## Day 2 — r/baseball + Twitter (broad launch)

### r/baseball

- **Message the mods first.** Send a short modmail with the Day 1
  r/CHICubs post as proof of reception, a one-line description
  ("30-team daily newspaper briefing for every MLB team, free, no
  ads, built solo"), and ask if the post is within the sub's current
  rules. Wait for approval.
- **Verify current Rule 2 wording before posting.** Mods update it.
  This doc's recommendation was written against a 2025-era version —
  check the sidebar on launch day.
- **Title:** same content-first structure as Day 1 but scaled to the
  whole league. Example: *"All 30 teams had bullpen ERA > 4.50 in
  April 2026 — and 5 had ERA > 6.00"*. League-wide stat first.
- **Body:** 2–3 sentences, link to the landing page at the end.
- **Image:** one screenshot of the all-division standings or league
  news wire section, cropped tight.

### Twitter

- **Post 30 minutes after r/baseball**, not before. Staggering gives
  either channel room to breathe if one catches fire first.
- **First tweet: screenshots only, no link.** X's algorithm has
  historically downranked tweets with outbound links in the primary
  post. Check this is still true on launch day before posting.
- **Screenshots:** 2–3 hero captures — landing page, a team briefing,
  and the scorecard. Pull them from `press/screenshots/` — those are
  already 2x retina.
- **Tweet copy:** "30 MLB teams. One daily briefing. Built by one
  person in Python and vanilla JS. No ads, no tracking, no paywall."
- **Reply to own tweet** within 60 seconds with the link:
  `https://brawley1422-alt.github.io/morning-lineup/`. Pin the reply.
- **Response window:** reply to every quote-tweet and mention for the
  first 6 hours. The engagement loop compounds.

---

## Day 3 — Show HN (technical launch)

**Why last:** HN audience rewards technical substance. They want to
see the build, the stack, and the reasoning — not the marketing. By
Day 3, the site has run through two days of real traffic and has
stories to tell.

- **Title:** `Show HN: Morning Lineup – a daily newspaper-style briefing for all 30 MLB teams`
  - Em-dash, not hyphen.
  - No adjectives ("beautiful", "modern"). HN strips those
    psychologically.
  - No emoji. Ever.
- **Day/time:** Tuesday or Wednesday, 8:00–10:00 a.m. ET. Front-page
  odds drop on weekends and after 11 a.m. ET on weekdays.
- **Body (2–3 sentences):** what it is, who it's for, the one
  sentence of technical flavor. Example:

  > Morning Lineup is a daily newspaper-style briefing for all 30
  > MLB teams. Each team's page is rebuilt every morning from the
  > MLB Stats API with a static site generator written in Python's
  > standard library — no frameworks, no tracking, no ads, no
  > paywall. I built it because every other way of reading a box
  > score has gotten worse.

- **First comment (post immediately after submission):** the
  technical transparency layer.
  - Stack: Python stdlib only, vanilla JS, GitHub Pages, Supabase
    for auth.
  - Scope: what the build does and doesn't cover. Be honest about
    limitations (no historical seasons, no advanced stats beyond
    what StatsAPI returns, no playoff race projections yet).
  - Why it exists: one paragraph on the "open the morning paper"
    framing.
  - Link to the GitHub repo for anyone who wants to read the code.
- **Response window:** for the first 90 minutes HN post life is
  measured in single-digit minutes. Refresh the page, reply to every
  comment — even the skeptical ones, especially the skeptical ones.
  Never argue. Acknowledge, answer, move on.

**Do not:**
- Ask friends to upvote. HN voting-ring detection is irreversible
  and will shadow-penalize the account permanently.
- Post and walk away. If the first 30 minutes get zero traction, it
  won't recover.
- Edit the title after submission. Edits reset the ranking clock.

---

## Channels explicitly skipped

| Channel | Why skip |
|---|---|
| **Product Hunt** | Off-genre. PH audience is SaaS/B2B, not sports content. Content sites with no network built up pre-launch consistently belly-flop on PH. |
| **LinkedIn** | Wrong audience. Morning Lineup readers open Reddit and Twitter in the morning, not LinkedIn. |
| **ESPN / MLB subreddit cross-posts** | Lower leverage than r/baseball. Diluted by high-volume news posts. |
| **Email blast to personal network** | Covered by Phase 4 (manual friends-and-family texting). Distinct channel. |

---

## Day-of sanity checks (run the morning you launch)

1. **r/baseball Rule 2** — read the current sidebar, not the doc above.
2. **X algorithm link penalty** — check a couple of recent launches
   and see whether they put the link in-thread or in reply. Match
   the current norm.
3. **OG cards** — paste the landing URL into Facebook Sharing
   Debugger and Twitter Card Validator. Fix anything that doesn't
   render.
4. **Press kit ZIP** — verify
   `https://brawley1422-alt.github.io/morning-lineup/press/morning-lineup-press-kit.zip`
   actually downloads. The Contents API occasionally truncates
   binaries.
5. **Analytics** — open Supabase Events table and watch for the
   first `pageview` within 10 minutes of posting. If none arrive,
   the problem is analytics.js, not reach.

---

## Post-launch debrief (Day 4)

Run the queries in `docs/launch/metrics-dashboard.md` on Day 4
morning and write numbers into a one-page debrief:

- Pageviews per channel (infer by referrer pattern + timestamp)
- Share-button clicks
- Install-prompt accepts
- Day-2 return rate

Decide from those numbers whether Phase 5 (web push + badge)
should ship before or after shipping the email digest question.
