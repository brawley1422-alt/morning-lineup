---
title: "feat: Launch & distribution — every option for getting Morning Lineup in front of more people"
type: feat
status: active
date: 2026-04-15
revised: 2026-04-15
---

# Launch & Distribution — every option on the table

> **Revision note (2026-04-15, same day):** Track A and Track E shipped
> in two commits. This document has been updated to mark those units
> complete, capture what we learned from shipping, and re-sequence the
> remaining work. The original 5-track structure is preserved; the
> "Phased Delivery" and "Path Forward" sections now reflect the
> post-shipping reality.

## Shipped Log

| Date       | Commit    | Track    | Summary                                              |
|------------|-----------|----------|------------------------------------------------------|
| 2026-04-15 | `22a59e0` | A1-A5    | OG/Twitter meta tags on every page, robots.txt, sitemap.xml, 30 per-team OG card PNGs, fixed Cubs-centric manifest copy, canonical URLs, per-page titles + descriptions for SEO |
| 2026-04-15 | `3636d04` | E1, E2   | `analytics.js` client + Supabase `events` table (schema in `docs/supabase/events.sql`, applied manually by JB in the Supabase SQL Editor) + `docs/launch/metrics-dashboard.md` with daily-fill-in log and copy-pasteable queries |
| 2026-04-15 | `b2d8fda` | D1, D2, D5 | Share button in every team masthead (Web Share API + clipboard fallback + toast), smart install prompt gated on visits≥3 + non-standalone + not-dismissed, first-visit onboarding overlay on landing (pick team → install → "come back tomorrow"). All wired to analytics events: `share_click`, `install_shown`/`accepted`/`dismissed`, `onboard_*` |

**Verified live:**
- Team page OG tags render correctly (anyone sharing a link to a team page now gets a rich preview card).
- `/robots.txt` and `/sitemap.xml` served from GH Pages root.
- 30 per-team OG card PNGs committed under `icons/og-{slug}.png` + `icons/og-default.png`.
- Analytics smoke-test row inserted via REST API with HTTP 201. Every pageview on the live site now writes a row to Supabase `events`.
- Share button, install prompt, and welcome overlay all served at 200 across root + per-team paths.

## What we learned by shipping

- **The measurement layer changes the posture of every subsequent unit.** Before Track E, we were guessing what would move the needle. Now every unit can be measured against concrete metrics (pageviews, sessions, top team, referrer). This argues for shipping small cheap units and *looking at the data* before committing to larger ones.
- **OG card generation was much easier than expected.** Headless Chromium + a single HTML template + team-config-driven substitution rendered 30 production-ready cards in ~30 seconds. Future OG-adjacent work (press-kit screenshots, social promo graphics, email header images) can reuse the same pipeline.
- **Track B (friends & family invite flow) is lower ROI than it looked on paper.** The manual alternative — JB texts 10 friends the URL — is effectively free and captures the same outcome for the same sample size. A formal invite system, a welcome overlay, and a magic-link share button is a week of work that replaces a task JB can do in one evening. **Recommendation below: skip most of Track B and fold its one valuable piece (welcome onboarding for any cold visitor) into Track D.**
- **Track D1 (share button) is higher ROI than any single B unit.** One button, one script, every visitor gets the power to share with one tap. It's the thing that makes the OG cards we just shipped actually get used.
- **No content has been pushed externally yet.** All the work so far is infrastructure. Zero launch signal has left the repo. Until JB posts somewhere, analytics will show only his own visits and this session's smoke tests.

## Research Deepening Pass (2026-04-15, post-Phase-2)

After shipping Phases 1 and 2, four research threads were run in parallel
to strengthen the remaining Phase 3–5 unit specs. Findings below are
integrated into the revised unit definitions; this section summarizes the
highest-signal decisions the research produced.

### Launch playbook findings

- **r/baseball gates self-promo.** Posts look like product pitches get removed without mod pre-approval. The reliable entry is a **soft launch in a friendly team subreddit first** (r/CHICubs is the natural choice given JB's affinity), then message r/baseball mods with that team-sub post as proof the community likes it.
- **Frame every external post as content, not build.** Lead with today's screenshot and a concrete observation ("The Cubs have the worst bullpen ERA in April since 2017 — here's the chart"). The site is the source in the body. "I built this" goes in the first comment, not the title.
- **Skip Product Hunt.** For an off-genre content site with no pre-built network, PH ROI is marginal. The platform has drifted toward AI tools and SaaS. Time is better spent on team subs + Twitter replies to beat writers.
- **Stagger the launch over 3 days, not simultaneously.** Day 1: team subreddit soft launch. Day 2: r/baseball (mod-approved) + Twitter. Day 3: Show HN. 24-hour gaps. Simultaneous posting means you can't respond to engagement on all channels.
- **Show HN title format:** `Show HN: Morning Lineup – a daily newspaper-style briefing for all 30 MLB teams`. Tue/Wed/Thu 8–10am ET. First comment immediately with stack + what's automated + what's next. Never ask friends to upvote — HN voting-ring detection is fatal.
- **Twitter:** screenshots in the first tweet, link in the first reply, pin the reply. Link-in-first-tweet is algorithmically downweighted.
- **Correction to prior plan draft:** `r/reddevils` is Manchester United, not a baseball sub. Correct Giants sub is `r/SFGiants`.

### Email deliverability findings (affects D3)

- **Provider: Resend.** Free tier (3,000/mo, 100/day), no credit card, cleanest Supabase DX, first-class Supabase ecosystem integration.
- **Sending from a provider default domain (`onboarding@resend.dev`) is not viable for real lists.** Deliverability to Gmail primary inbox is poor — emails land in Promotions at best, Spam at worst. Gmail SMTP + app password has a 500/day cap and burns fast.
- **Recommendation: buy a cheap owned domain** (`morninglineup.email` at Cloudflare Registrar, ~$10/yr). Resend's dashboard wizard auto-generates SPF + DKIM + DMARC records and verifies on Cloudflare DNS in under 5 minutes.
- **Supabase scheduler:** There is no built-in cron UI for Edge Functions. The canonical 2026 pattern is `pg_cron` extension (Dashboard → Database → Extensions) calling `net.http_post` (from `pg_net`) to invoke the Edge Function URL with the service-role key. DST gotcha: compute the target hour inside the function from `America/Chicago` rather than hard-coding a UTC cron.
- **Idempotency via `email_sends` table** with unique constraint on `(user_id, send_date)` — insert before sending so retries don't duplicate.
- **Compliance minimums:** `List-Unsubscribe` one-click header (Resend adds it automatically when you pass the header), CAN-SPAM physical address in footer, short `/privacy` page on GH Pages.
- **Double opt-in is now the majority default** for deliverability. Gmail's 2024 sender rules punish low-engagement lists hard; single opt-in risks burning sender reputation on day one.
- **Contrarian finding (press-kit agent):** Consider skipping email v1 entirely. For a free daily content site, the home-screen install is the retention mechanism; email is a second surface to maintain (compose, send, unsubscribe, SPF/DKIM/DMARC, compliance) for a marginal retention lift at the current audience size. Revisit at 500 DAU when there's a newsy reason to send beyond "new edition live."

### Web push findings (affects D4)

- **iOS PWA push works since 16.4, but is install-gated.** Reachable audience is roughly 10–15× smaller than Android Chrome because the user must install to home screen *first*. Android Chrome (FCM-backed) remains the most reliable delivery path.
- **EU blackout:** iOS 17.4+ DMA changes removed standalone PWA mode in the EU. Push and badges don't work there. Non-issue for an MLB audience.
- **Use `negrel/webpush` or `draphy/pushforge`** — Deno-native VAPID libraries that work inside Supabase Edge Functions. The classic Node `web-push` npm package is awkward in the Edge runtime. **Don't use it.**
- **Safari payload cap ~256 bytes** for title+body combined. No custom images (only the PWA app icon renders). Keep copy tight: `"Cubs 5, Brewers 3 — Final. Tap for recap."`
- **Pre-prompt is mandatory.** Never call `pushManager.subscribe()` on first visit — Chrome has actively deranked sites that do. Use a custom HTML button ("Get final score alerts for the Cubs") that triggers the native prompt only on click. Well-prompted content sites hit 15–20% accept vs ~6% site-wide average.
- **410 Gone = delete the row immediately.** Also listen for `pushsubscriptionchange` in `sw.js` and re-POST the new subscription.
- **Permission-free fallback: `navigator.setAppBadge()` with local polling.** Costs nothing, works for users who decline push, and gives a passive re-engagement surface (badge only updates when the PWA is opened, but that's still a nudge). **Ship this as a Day-1 companion to web push**, not as an alternative.
- **Build-vs-buy:** negrel/webpush + Supabase Edge Function is ~200 lines total. OneSignal's free tier has a 10k-per-send cap and adds SDK bloat. For a static site with one event trigger (game Final), self-hosting via VAPID is cleaner than any managed service.

### Press kit + landing conversion findings (affects C1, C2)

- **Single dominant CTA beats menu.** Every high-converting newsletter/content landing page in recent teardowns (beehiiv, Morning Brew, Sherwood News) has one CTA above the fold, removed top nav from the hero, and a product preview thumbnail as social proof.
- **For Morning Lineup, the team-picker grid IS the CTA** — don't dilute it with an email field in the same stripe. Email capture is a Phase-5 decision, not a launch-day one.
- **Contextual CTA variant:** first visit = "Pick your team", repeat visit (via `localStorage.ml_visits`) = "Welcome back — add to home screen". The install chip is a *secondary* element, not the primary action.
- **Install button copy:** "Read it every morning" converts better than generic "Install". Place it **in-content after one scroll**, not in the header. Header-mounted install buttons get <1% tap-through vs 4–6% for in-content placement.
- **Trust signals without users:** name the founder, state the cadence, show the stack. "Edited by JB Rawley. Rebuilt every morning at 6 a.m. CT. 30 teams. No ads, no tracking." This replaces testimonials you don't have. Founder photo fits `/press/`, not the hero.
- **Press kit conventions (2026):**
  - Naming: **`/press/`** (not `/about/` or `/media-kit/`) — matches the editorial theme and is what reporters search for.
  - Sections (in order): Fact Sheet, Descriptions (one-liner / 50w / 150w), Screenshots, Logos, Founder, Quotes, Contact.
  - Downloadable ZIP: `/press/morning-lineup-press-kit.zip` — logos (PNG + SVG, dark + light), 2–3 hero screenshots at 2x retina, founder headshot, fact sheet + boilerplate as plain text. One gold "Download press kit" button at the top of the page.
  - **Fact sheet is the most-copied section** per Prezly's 2025 guide. Lead with it.
  - **One pre-written quote** attributed to JB so a writer can drop it in without emailing.
  - **Three description lengths (one-liner, 50w, 150w)** so reporters can paste whichever fits.
- **Explicitly do NOT build for launch:** fake "As seen in" logo row, email capture form, modal popups, testimonial carousel, header-mounted install button, Notion-hosted press kit (keep the HTML page as the front door; Notion is hidden).

### Research caveat

Two of the four agents ran without web search access and noted this
explicitly. Their recommendations are synthesis from 2024–2025 platform
norms, which are generally stable but not guaranteed to hold on
launch day. JB should sanity-check:

1. r/baseball's current Rule 2 wording before posting
2. Resend's free tier numbers and Gmail/Yahoo bulk sender thresholds (both moving targets)

A 15-minute pre-flight check each is worth it before pressing publish.

## Overview

Morning Lineup is a complete, polished daily-briefing product for all 30 MLB
teams. The pages are technically public and the infrastructure is solid
(cron rebuild, deploy verification, service worker, PWA, team picker,
per-team branding, live polling, fold design). What's missing is every
mechanism that turns a working product into a *discoverable* one.

This plan enumerates **every launch and distribution option** on the
table, groups them into five tracks, and proposes a sequenced rollout.
JB asked for the full landscape — not a single track — so the plan is
deliberately broad. Each track is independently shippable; some are
cheap, some are meaningful lifts. Pick any combination.

## Problem Frame

**The actual gap is discovery, not access.** A quick audit of the repo
reveals the real shape of the problem:

| Surface | State |
|---|---|
| Team page auth | Not gated — `auth/session.js` only guards `home/`, `settings/`, binder features. Anyone with a URL can read all 30 briefings. |
| Social share previews | Zero `og:*` or `twitter:*` meta tags on any team page or the landing page. Links shared on iMessage/Twitter/Slack produce a naked URL with no image, title, or description. |
| SEO | No `robots.txt`, no `sitemap.xml`, no canonical URLs, no per-page `<meta name="description">`. Google has no map of the site. |
| PWA install prompt | Manifest exists (installable) but nothing nudges visitors to add to home screen. |
| Shareable artifacts | No "share this team" / "share this player card" / "share this scorecard" buttons anywhere. |
| Landing page conversion | `landing.html` exists with live standings, but no CTA, no waitlist, no "tell a friend", no install prompt. |
| Signup onboarding | `auth/index.html` exists but there's no path from landing → signup → personalized home for a first-time visitor. |
| Manifest copy | Still says "A daily dispatch from the Friendly Confines & beyond" — Cubs-centric; wrong for 29 other teams. |

**The blocker is that no existing person has a reason to forward a link
AND the link they'd forward renders as a dead text string.** Fix the
shareability floor and every other growth mechanism stops leaking.

## Requirements Trace

- R1. A link to a team page, when pasted into iMessage / Twitter / Slack / Facebook, renders a rich preview card with team colors, today's game, and a compelling title.
- R2. The site is crawlable and indexed by Google — a search for "cubs daily briefing" or "morning lineup mlb" surfaces our pages.
- R3. There is a clear, one-click path to install the PWA to home screen on mobile, without being nagged.
- R4. There is a clear, one-click path to share the current page — team, player card, scorecard — to any destination.
- R5. There is a public launch artifact (landing pitch, waitlist or first-visit CTA) that converts a cold visitor into either an installed app or an account.
- R6. There is a post-visit loop — email, push, or scheduled reminder — that brings the visitor back tomorrow.
- R7. There is a measurable way to know whether any of this is working (page views, installs, shares, signups).

## Scope Boundaries

**In scope:**
- Shareability, SEO, social preview, install prompts, landing conversion, onboarding UX
- Growth-loop features that are mechanical (share buttons, OG images, invite links)
- Distribution plan (channels, messaging, posting cadence)
- Lightweight analytics/telemetry so we can tell if it worked

**Out of scope:**
- Paid advertising, Google Ads, influencer deals — we're not spending money
- Rewriting the auth system (Supabase stays)
- Native iOS/Android apps — PWA is the mobile strategy
- Server-side infrastructure beyond what GitHub Pages already provides
- Content changes to the briefings themselves (that's a separate backlog)
- A full rebuild of the landing page UX — we'll enhance what's there

## Context & Research

### Relevant Code and Patterns

- `build.py` — team-page renderer. Page envelope is one big f-string at `page()` ~line 1310. All meta tags live in the `<head>` block. Team config drives per-team strings; any new OG tag becomes a one-line addition per team. No per-team build step needed beyond the existing rebuild.
- `landing.html` — standalone landing renderer (loaded via `build.py --landing`). Has `__TEAMS_JSON__` replacement token; a similar `__SHARE_*__` pattern would work for OG tags.
- `auth/session.js` — Supabase wrapper with `requireAuth`, `getProfile`, `onAuthChange`. Used only by `home/`, `settings/`, and binder features. Team pages remain unauthenticated.
- `home/home.js` — "Your Lineup" home screen. Good anchor for any first-time onboarding flow (hasProfile? → show welcome; !hasProfile? → show pick-your-team CTA).
- `teams/{slug}.json` — per-team config (colors, division, branding, affiliates). Already contains everything needed to generate team-specific OG text and share strings.
- `manifest.json` — PWA manifest. Currently has Cubs-centric description. Per-team manifests would require build.py generating one manifest.json per team dir.
- `sections/headline.py` — The Team section renderer. Knows the team's next games and last result — the right place to compute a "today's hook" string for OG title.
- `sw.js` — service worker with offline cache. Already in place.
- `deploy.py` — Contents API + per-team `{slug}/index.html` push + Pages Build verification. Any new static asset (robots.txt, sitemap.xml, social card PNGs) should be added to `STATIC_ASSETS` at lines 183–199.
- `build.py` line 2335 — the per-team asset copy loop (`player-card.js`, `reader-state.js`, `resolution-pass.js`, `tz.js`). New per-team scripts follow this pattern.

### Institutional Learnings

- `docs/solutions/` was not surveyed for this plan, but prior memory confirms: **when changing shared assets, rebuild all 30 teams** (see `feedback_rebuild_all_teams`). Any of the five tracks that touch `build.py` or `style.css` will need the full 30-team rebuild + redeploy.
- Evening auto-rebuild still runs for Cubs only. Any feature that depends on evening-refreshed OG text (e.g. "Cubs won 8–3, read the morning-after briefing") only lands on Cubs until evening is extended.
- GitHub Pages builds can flap when many commits land within seconds (seen 2026-04-13 and 2026-04-15). The deploy verifier in `deploy.py` catches this. Any launch that involves multiple rapid pushes should account for 30–60s of Pages settling time per push.
- The landing page already pulls live standings and scores from MLB Stats API client-side. That's an asset for conversion — a first-time visitor sees a live product immediately, not a static teaser.

### External References

- Open Graph protocol spec: `https://ogp.me/`
- Twitter Card reference: `https://developer.twitter.com/en/docs/twitter-for-websites/cards/overview/markup`
- Web App Manifest for per-page install prompts: `https://developer.mozilla.org/en-US/docs/Web/Manifest`
- `beforeinstallprompt` event for conditional install CTAs: `https://web.dev/articles/customize-install`
- Reddit r/baseball post etiquette: self-promotion must be sparing; content-first posts (e.g. "I built a daily briefing for every MLB team") tend to land better than feature pitches.

## Key Technical Decisions

- **Static OG image generation happens at build time, not request time.** GitHub Pages has no server-side render path. We have two options: (1) pre-generate a PNG per team per day using headless Chromium driven by a new `build.py --og-card <team>` mode, then commit to the repo; (2) commit *one* static OG image per team (colors + logo + "Today's Edition") that never changes. Decision: **start with option 2** (static per-team PNG) because the build-time headless render adds 30+ seconds per team and a failure mode for the morning cron. Upgrade to option 1 later if share-click data shows it's worth the complexity.
- **Use `<link rel="canonical">` on every team page pointing to the clean GH Pages URL.** Prevents duplicate-content penalties if the site ever gets mirrored.
- **Do not generate a per-team manifest.** One manifest at the root with team-agnostic copy is simpler and still makes the PWA installable per team page. The home-screen icon will be the Morning Lineup logo, not the team logo — acceptable for v1.
- **Analytics: Plausible or Umami, not Google Analytics.** Privacy-respecting, lightweight, no cookie banner needed in EU. Fits the editorial brand. One script tag, no configuration.
- **Social sharing: Web Share API first, fallback to copy-link.** `navigator.share()` is supported on mobile Safari and Chrome Android, which is where most shares happen. Desktop gets a "copy link" button with a brief toast confirmation.
- **Invite flow uses Supabase magic links, not unique per-recipient URLs.** We already have Supabase; building a new invite-token system is overkill for a friends-and-family beta.
- **The launch moment happens AFTER the shareability floor is in place.** Posting on Reddit before OG cards work means every share looks broken.

## Open Questions

### Resolved During Planning

- **Are team pages currently gated by auth?** No — `requireAuth` is only imported by `home/home.js`, `settings/settings.js`, and binder code. Team pages are publicly accessible.
- **Does GH Pages support server-side OG image generation?** No. Static pre-generation at build time is the only option.
- **Is there an existing analytics pipeline?** None visible in the repo. Clean slate.
- **Does the landing page convert anonymous visitors?** It shows live data but has no CTA, waitlist, or signup prompt. Conversion surface is zero today.

### Deferred to Implementation

- Exact copy for the landing-page CTA — "Install" vs "Subscribe" vs "Pick your team" — should be A/B'd once analytics exist.
- Whether to send the first post-visit push notification via Web Push (needs VAPID keys + backend) or via email (needs Supabase Edge Function + SendGrid or Resend). Web Push is simpler but has worse deliverability; email is more effort but higher trust. Defer until Phase 3.
- The right cadence for the morning email digest — 7am local time requires user TZ from the profile, which isn't collected today.
- Whether to include the scorecard or just a single game result in the email body.
- Which subreddits/communities to post to beyond r/baseball — defer to the launch-day checklist.

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

**The five tracks, arranged by dependency:**

```
                 ┌──────────────────────────────────┐
                 │   TRACK A — Shareability Floor   │
                 │   OG/Twitter tags, SEO, icons    │
                 │   robots, sitemap, meta descr    │
                 └────────────────┬─────────────────┘
                                  │
               ┌──────────────────┼──────────────────┐
               │                  │                  │
               ▼                  ▼                  ▼
     ┌─────────────────┐ ┌─────────────────┐ ┌──────────────────┐
     │ TRACK B — F&F   │ │ TRACK C — Public│ │ TRACK D — Growth │
     │ Invite Flow     │ │ Launch Moment   │ │ Loop Features    │
     │ magic-link      │ │ landing CTA,    │ │ share buttons,   │
     │ invites,        │ │ Reddit/Twitter/ │ │ install prompt,  │
     │ onboarding,     │ │ PH, press-kit   │ │ email digest,    │
     │ welcome screen  │ │ page            │ │ web push         │
     └─────────────────┘ └─────────────────┘ └──────────────────┘
               │                  │                  │
               └──────────────────┼──────────────────┘
                                  ▼
                 ┌──────────────────────────────────┐
                 │   TRACK E — Measurement          │
                 │   Plausible/Umami, share count,  │
                 │   signup count, return rate      │
                 └──────────────────────────────────┘
```

**Tracks B, C, D are peer alternatives** — any one of them is shippable without the other two. Track A is a prerequisite for all of them (otherwise every share they generate is broken). Track E is the "did it work?" layer and should ship alongside whichever track you pick first.

**The recommended sequence** — my take, not prescriptive:
1. **Week 1 — Track A + Track E** (foundation). Ship the shareability floor and turn on analytics. Cheap, compounding, unblocks everything.
2. **Week 2 — Track B** (friends & family). Hand to 20-50 people via invite links. Get real feedback. Tune the onboarding before the public sees it.
3. **Week 3 — Track C** (public launch). Post to r/baseball, r/{team} subreddits, Twitter, Product Hunt. Leverage the beta learnings.
4. **Ongoing — Track D** (growth loops). Ship one loop per week based on what the data says is leaky.

## Implementation Units

### Track A — Shareability Floor (foundation)

- [x] **Unit A1: Open Graph and Twitter Card meta tags on every team page**

**Goal:** Every team page, the landing page, and the home page emit complete `og:*` and `twitter:*` meta tags so that any link shared anywhere produces a rich preview card.

**Requirements:** R1

**Dependencies:** None

**Files:**
- Modify: `build.py` (page envelope `<head>` block ~line 1310–1325; add OG/Twitter meta after existing `<meta>` tags)
- Modify: `landing.html` (static `<head>` additions)
- Modify: `home/index.html`
- Modify: `auth/index.html`
- Create: `icons/og-default.png` (1200×630, Morning Lineup masthead + team-agnostic)
- Create: `icons/og-{slug}.png` × 30 (per-team 1200×630 — team colors, logo, "Today's Edition" in Playfair)
- Test: `tests/test_og_tags.py` (parse rendered HTML, assert required tags present for 5 sample teams)

**Approach:**
- Each team page gets: `og:title` = "The {Team} · Morning Lineup · {Date}", `og:description` = "Last night's game, today's matchup, and every angle that matters.", `og:image` = absolute URL to the team's static OG card, `og:type=article`, `og:url` = canonical, `twitter:card=summary_large_image`, `twitter:creator` (optional), plus `<meta name="description">` and `<link rel="canonical">`.
- OG images are pre-rendered *once* and committed to `icons/og-{slug}.png`. Generation script can be a one-shot Python helper using PIL that draws masthead + team-colored background; not a build-time dependency.
- Do NOT include today's date in the OG image — makes it stale on old share clicks. Keep the date in the `og:title` text only.

**Technical design:** *(directional, not implementation spec)*

```html
<!-- Added to every team page <head> -->
<meta property="og:type" content="article">
<meta property="og:site_name" content="The Morning Lineup">
<meta property="og:title" content="The {Team} · Morning Lineup · {Date}">
<meta property="og:description" content="{lede_one_liner}">
<meta property="og:url" content="https://brawley1422-alt.github.io/morning-lineup/{slug}/">
<meta property="og:image" content="https://brawley1422-alt.github.io/morning-lineup/icons/og-{slug}.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="The {Team} · Morning Lineup">
<meta name="twitter:description" content="{lede_one_liner}">
<meta name="twitter:image" content="https://brawley1422-alt.github.io/morning-lineup/icons/og-{slug}.png">
<meta name="description" content="{lede_one_liner}">
<link rel="canonical" href="https://brawley1422-alt.github.io/morning-lineup/{slug}/">
```

**Patterns to follow:**
- Existing meta tag block in `build.py` page envelope (search for `<meta name="viewport">`).
- Existing per-team config access: `CFG['id']`, `CFG['branding']`, `TEAM_NAME`.

**Test scenarios:**
- Happy path: Rebuild cubs page. Parse HTML, assert 9 required meta tags exist with non-empty content. `og:image` matches `icons/og-cubs.png`.
- Happy path: Same for yankees, dodgers, red-sox, guardians — verify per-team substitution works across all 30.
- Happy path: Paste the cubs URL into a real OG debugger (facebook.com/tools/debug or cards-dev.twitter.com/validator) as a manual smoke test after deploy.
- Edge case: A team with a long name ("Arizona Diamondbacks") should not overflow `og:title`.
- Edge case: The landing page gets its own OG set with a team-agnostic image.

**Verification:**
- Every team page in the repo contains the required `og:*` and `twitter:*` tags after rebuild.
- Sharing the cubs URL on iMessage shows a rich card with team colors, logo, and the Morning Lineup masthead.

---

- [x] **Unit A2: robots.txt, sitemap.xml, and canonical URLs**

**Goal:** Google can crawl and index every team page. A sitemap makes discovery fast; canonical URLs prevent duplicate-content issues.

**Requirements:** R2

**Dependencies:** None (can run in parallel with A1)

**Files:**
- Create: `robots.txt` (at repo root)
- Create: `sitemap.xml` (at repo root — generated by build.py)
- Modify: `build.py` (add `generate_sitemap()` function, call from main when `--sitemap` flag is passed or at the end of any build run)
- Modify: `deploy.py` (add `robots.txt` and `sitemap.xml` to `STATIC_ASSETS` at lines 183–199)
- Test: `tests/test_sitemap.py`

**Approach:**
- `robots.txt` is static — allow all, point to sitemap. One file, never regenerated.
- `sitemap.xml` is generated nightly by the morning cron: 30 team URLs + landing + home + auth, each with `<lastmod>` set to today's date and `<changefreq>daily</changefreq>`.
- Add `<link rel="canonical">` to every team page in the build envelope.

**Patterns to follow:**
- `deploy.py` `STATIC_ASSETS` list at line 183.
- `build.py` landing-page build path for the sitemap generator.

**Test scenarios:**
- Happy path: Run sitemap generator, assert all 30 teams + landing URLs present, valid XML, correct `<loc>` format.
- Happy path: `robots.txt` referenced in Google Search Console after deploy (manual verification).
- Edge case: Missing team config should not crash the sitemap generator.

**Verification:**
- `https://brawley1422-alt.github.io/morning-lineup/sitemap.xml` returns 200 with 30+ URLs.
- `robots.txt` served at root, references the sitemap.

---

- [x] **Unit A3: Per-page meta descriptions and page titles**

**Goal:** Every page has a unique, compelling `<title>` and `<meta name="description">` tuned for search snippets.

**Requirements:** R2

**Dependencies:** Unit A1 (shares the description generation)

**Files:**
- Modify: `build.py` (change `<title>` to include team name + "Daily Briefing" + date; add meta description)
- Test: Add assertions to `tests/test_og_tags.py`

**Approach:**
- Title format: `The {Team} Daily Briefing — Morning Lineup, {Date}`
- Description: 1-line lede from the headline section, trimmed to 155 chars.
- If no lede, fall back to "Last night's game, today's matchup, leaders, and the full slate."

**Patterns to follow:** Existing `<title>` in `build.py`.

**Test scenarios:**
- Happy path: Cubs page title contains "The Cubs Daily Briefing" and today's date.
- Happy path: Description is under 160 chars for all 30 teams.
- Edge case: Lede missing → fallback description used.

**Verification:** All 30 team pages have distinct, search-friendly titles and descriptions.

---

- [x] **Unit A4: Per-team OG images (one-shot generation)**

**Goal:** Commit 30 static 1200×630 PNGs to `icons/og-{slug}.png`, one per team, styled to match the newspaper masthead with team colors.

**Requirements:** R1

**Dependencies:** None (independent, but A1 references these files)

**Files:**
- Create: `scripts/generate_og_cards.py` (one-shot Python script using Pillow or headless Chromium)
- Create: `icons/og-{slug}.png` × 30
- Create: `icons/og-default.png` (landing page fallback)

**Approach:**
- Use headless Chromium with a small HTML template that takes team config as query params and renders a 1200×630 card: masthead ("The Morning Lineup"), team logo, team colors as background, "Today's Edition" stamp.
- Script runs once locally, outputs 30 PNGs, commit them.
- No build-time integration — these are static assets.

**Patterns to follow:**
- Existing headless Chromium usage from design mockups (`/tmp/fold-design/*.html` → PDF pipeline).
- `teams/*.json` config schema.

**Test scenarios:**
- Visual QA only: Eyeball all 30 cards after generation. No automated tests for image output.

**Verification:** 30 files exist under `icons/`, each is 1200×630, each uses the correct team primary/accent colors.

---

- [x] **Unit A5: Fix Cubs-centric manifest copy**

**Goal:** `manifest.json` description is team-agnostic so the PWA install copy makes sense across all 30 teams.

**Requirements:** R3

**Dependencies:** None

**Files:**
- Modify: `manifest.json` (single-line description change)

**Approach:**
- Change description from "A daily dispatch from the Friendly Confines & beyond" to "A daily briefing for every MLB team — last night's game, today's matchup, and every angle that matters."

**Test scenarios:** *Test expectation: none — copy change.*

**Verification:** Installed PWA shows the new description in home-screen app info.

---

### Track B — Friends & Family Invite Flow

- [ ] **Unit B1: Invite link landing and onboarding**

**Goal:** A single shareable link (`?invite=1` query flag) that lands a first-time visitor on a tailored welcome screen — "Pick your team, install to home screen, sign up for the daily nudge" — instead of the raw landing page.

**Requirements:** R3, R5

**Dependencies:** Track A complete (otherwise the shared invite link has no preview card)

**Files:**
- Modify: `landing.html` (detect `?invite=1`, show welcome overlay)
- Modify: `landing.html` CSS block (welcome overlay styles)
- Create: `home/welcome.js` (first-visit detection, overlay toggling)

**Approach:**
- First visit sets `localStorage.ml_onboarded = true`. Subsequent visits skip the overlay.
- Welcome overlay has 3 steps: (1) Pick your team (click a team card → sets `localStorage.ml_team = slug`), (2) "Install as app" button that triggers `beforeinstallprompt` if available, (3) "Get it in your email" optional signup.
- Skippable at every step. Sticky on the top of the landing page, not a modal.

**Patterns to follow:**
- `home/home.js` profile-check pattern for first-time detection.

**Test scenarios:**
- Happy path: First visit with `?invite=1` shows overlay.
- Happy path: Pick a team → redirect to `/{slug}/`, overlay dismissed, team stored.
- Happy path: Skip install → overlay advances to email step.
- Edge case: Return visit (localStorage set) → no overlay even with `?invite=1`.

**Verification:** Cold visit with `?invite=1` produces a clean onboarding flow; return visit goes straight to the landing page.

---

- [ ] **Unit B2: Supabase magic-link invite button in settings**

**Goal:** From the settings page, an authenticated user can generate a pre-filled invite message ("Here's my Morning Lineup — pick your team") with a tracked URL that marks the recipient as a B-flow onboarding visitor.

**Requirements:** R5

**Dependencies:** B1

**Files:**
- Modify: `settings/index.html` (add invite section)
- Modify: `settings/settings.js` (invite link generation, Web Share API with copy fallback)

**Approach:**
- Generate URL: `https://brawley1422-alt.github.io/morning-lineup/?invite=1&from={user_hash}`.
- Click "Share invite" → `navigator.share({title, text, url})` on mobile, fallback to copy-to-clipboard + toast on desktop.
- `from=` is purely for counting; no auth on the receiving end.

**Patterns to follow:** `auth/session.js` profile hash access.

**Test scenarios:**
- Happy path: Click invite button, share sheet opens on mobile.
- Happy path: Click invite button, link copied + toast shown on desktop.
- Edge case: Not logged in → button hidden.

**Verification:** A real user can generate and share an invite link from settings.

---

### Track C — Public Launch Moment

- [ ] **Unit C1: Landing page conversion CTA (research-revised)**

**Goal:** The landing page has a single dominant above-the-fold CTA that routes cold visitors straight into the product. The team-picker grid **is** the CTA — not one of three options competing with email capture.

**Requirements:** R5

**Dependencies:** Track A complete. Phase 2 already shipped `welcome-overlay.js` which handles the first-visit onboarding flow. C1 handles every subsequent visit and anyone who skipped the overlay.

**Files:**
- Modify: `landing.html` (CTA stripe markup + CSS + contextual-variant JS)

**Approach (revised per research):**
- **Single full-bleed stripe**, not a three-button row. Runs under the masthead, above the live standings. One headline, one action.
- **Primary action is the existing team-picker grid** — a single dominant CTA converts better than a menu of options. Do NOT add an email field in this stripe. (Email capture is a Phase-5 decision.)
- **Contextual headline via `localStorage.ml_visits`:**
  - Visit 1 (overlay already dismissed): `Pick your team. Read it every morning.`
  - Visit 2+: `Welcome back. Add Morning Lineup to your home screen.`
  - Standalone PWA display mode: hide the stripe entirely (user already installed).
- **Secondary chip under the headline:** `Read it every morning → Add to home screen`. Feature-detect `beforeinstallprompt`; fall back to iOS Safari share-sheet instructions on iOS; hide entirely on desktop Safari.
- **Trust line in the masthead dek, byline style:** `Edited by JB Rawley. Rebuilt every morning at 6 a.m. CT. 30 teams. No ads, no tracking.` Replaces testimonials we don't have. Shipping this line is a 10-minute change and can land independently of the rest of C1.
- Analytics events: `landing_cta_clicked` with `{variant: "first|return"}`, reuse existing `install_*` events from D2.

**Explicitly not shipped in C1:**
- Email capture field (deferred to Phase 5, possibly skipped entirely)
- Modal popups
- Testimonial row
- Fake "As seen in" logo bar

**Test scenarios:**
- Happy path: First visit after overlay dismissal → stripe shows "Pick your team" headline, team grid is the primary target.
- Happy path: Return visit (`ml_visits >= 2`) → stripe headline swaps to "Welcome back".
- Happy path: Installed PWA (`display-mode: standalone`) → stripe hidden, user goes straight to home/.
- Edge case: Safari desktop → install chip hidden (no API + no iOS instructions apply).
- Edge case: iOS Safari → install chip shows share-sheet instructions instead of a clickable button.

**Verification:** Cold landing visit produces a clear "pick your team" signal above the fold. Analytics `landing_cta_clicked` events arrive in Supabase within seconds of click.

---

- [ ] **Unit C2: Press kit page (research-revised)**

**Goal:** A `/press/` page that gives beat writers, bloggers, and sports-Twitter curators everything they need to cover Morning Lineup without emailing for assets. Ships with a one-click ZIP download of the full kit.

**Requirements:** R5

**Dependencies:** Track A complete

**Files:**
- Create: `press/index.html` (newspaper-template styling, matches the rest of the site)
- Create: `press/press.css` (minimal — reuses `../style.css` where possible)
- Create: `press/screenshots/landing.png`, `press/screenshots/cubs.png`, `press/screenshots/scorecard.png` (2x retina)
- Create: `press/logos/logo-dark.svg`, `press/logos/logo-light.svg`, `press/logos/logo-mark.png`
- Create: `press/founder-jb.jpg` (editorial B&W headshot — JB to provide)
- Create: `press/morning-lineup-press-kit.zip` (bundles the above + `fact-sheet.txt` + `boilerplate.txt`)
- Modify: `deploy.py` (add `press/` tree to STATIC_ASSETS deploy loop)
- Modify: `build.py` footer to link `/press/`

**Approach (revised per research):**
- **Naming:** `/press/`, not `/about/` or `/media-kit/`. Matches the editorial theme and is what reporters search for.
- **Template:** full newspaper aesthetic — Playfair masthead reading "PRESS ROOM", dark ink on cream, gold rule. Reuse the existing `style.css` variables.
- **Sections in order** (from the 2025 Prezly/Zapier/Acorn Games research synthesis — fact sheet is the most-copied section, lead with it):
  1. **Download press kit** (big gold button at the top, "Download press kit (ZIP, ~4 MB)")
  2. **Fact sheet** — launched 2026, built by JB Rawley in Grand Rapids, MI, 30 team pages rebuilt every morning, static HTML + Python, zero ads, zero tracking
  3. **Three description lengths** so reporters can paste whichever fits their word count:
     - *One-liner:* `Morning Lineup is a daily newspaper-style briefing for all 30 MLB teams, rebuilt every morning.`
     - *50-word:* add stack, cadence, solo-founder angle
     - *150-word:* add the "why" (built because existing MLB apps bury the box score under ten tabs of ads)
  4. **Screenshots** — 2–3 hero captures at 2x retina: landing page, a team page, the scorecard view
  5. **Logos** — PNG + SVG, dark + light variants
  6. **Founder** — JB headshot + 2-sentence bio
  7. **Pre-written quote** attributed to JB so a writer can drop it in without emailing: *"I wanted the feeling of opening the morning paper and seeing my team's box score on the second page. Morning Lineup is that page, for all 30 teams, every day."*
  8. **Press contact** — one email (not a form), a 24-hour response promise, and optional Bluesky/X handle
- **ZIP contents:** `logo-dark.svg`, `logo-light.svg`, `logo-mark.png@2x`, `screenshot-landing.png@2x`, `screenshot-cubs.png@2x`, `founder-jb.jpg`, `fact-sheet.txt`, `boilerplate.txt`. Generate via a one-shot `scripts/build_press_kit.sh`.
- **Footer link on every page** so reporters can find it via "site:brawley1422-alt.github.io/morning-lineup press kit".

**Explicitly NOT included:**
- Notion-hosted kit (keep HTML as the front door)
- Testimonials or fake "As seen in"
- Mailing list form in the contact section
- Modal popups for image previews

**Test scenarios:** *Test expectation: none — static content page. Manual QA: verify all 8 sections render, ZIP downloads cleanly, founder photo is editorial B&W, quote attribution is correct.*

**Verification:** `/press/` serves 200. `/press/morning-lineup-press-kit.zip` downloads and extracts cleanly. Footer link appears on every team page.

---

- [ ] **Unit C3: Launch-day distribution checklist (research-revised)**

**Goal:** A committed markdown doc listing every channel, exact copy, and the order to post them in, so launch week is mechanical. Revised per research to stagger over 3 days, skip Product Hunt, and use content-first framing.

**Requirements:** R5

**Dependencies:** C1, C2

**Files:**
- Create: `docs/launch/2026-04-XX-launch-day-checklist.md`

**Approach (revised per research):**

**Day 1 — Soft launch in one team sub (low stakes, learn framing).**
- **Channel:** `r/CHICubs` (JB's natural affinity — he'll respond best to engagement, and team subs are more tolerant of fan-made stuff than r/baseball).
- **Title:** Content-first observation, not "I built this." Example: `The Cubs have the worst April bullpen ERA since 2017 — I pulled the data into a page-one chart` or similar. Lead with a concrete fact about today.
- **Body:** A screenshot of the Cubs page showing the specific stat the title referenced. 2 sentences of context. Link to `https://brawley1422-alt.github.io/morning-lineup/cubs/`. "I built this" goes in a follow-up comment if asked, not in the body.
- **Time:** Weekday morning ET, before first pitch of a marquee Cubs game.
- **Purpose:** Learn what framing resonates. If this post lands well, use it as proof when messaging r/baseball mods on Day 2.

**Day 2 — r/baseball (mod-approved) + Twitter.**
- **r/baseball:** Message mods first with the Day 1 team-sub post as proof the community likes it. Ask for flair and permission. Wait for approval. Post with the same content-first title format.
- **Twitter:** Screenshots in the first tweet (2–3 hero captures of different teams' pages), link in the first reply, pin the reply. Do NOT put the link in the first tweet — algorithmic deranking. Include one line about the why: `30 MLB teams. One daily briefing. Built by one person in Python + vanilla JS.`
- **Time:** Twitter post 30 minutes after r/baseball lands to avoid simultaneous self-promotion signals.

**Day 3 — Show HN.**
- **Title:** `Show HN: Morning Lineup – a daily newspaper-style briefing for all 30 MLB teams`. Em-dash + factual descriptor. No adjectives like "beautiful" or "modern". No emojis.
- **Body:** 2–3 sentences max. Detail goes in the first comment.
- **First comment:** Immediate, must cover — why JB built it, the stack (static site generator, GitHub Pages, Supabase for auth, zero framework), what's automated vs manual, what's next. HN rewards transparency about scope and limitations.
- **Time:** Tuesday or Wednesday, 8–10am ET.
- **NEVER ask friends to upvote.** HN voting-ring detection is aggressive and penalties are often irreversible. Organic only.

**Skipped channels and why:**
- **Product Hunt:** Off-genre for content sites, no pre-built network, platform drifted to AI tools and SaaS. Time is better spent elsewhere.
- **LinkedIn:** Wrong audience for MLB content.
- **ESPN Fan Feedback / MLB Reddit:** Lower-leverage than targeted team subs + r/baseball.

**Optional follow-up channels (post-launch week):**
- Team-specific subs for 3–5 teams JB has a natural in on (r/NYYankees, r/Braves, r/Dodgers are known to be more tolerant; r/SFGiants is stricter).
- r/sabermetrics if the site adds a data-viz angle worth sharing.
- Beat writer Twitter replies when they tweet a stat and Morning Lineup visualizes it.

**Rules of the road:**
- Content-first framing always beats feature-pitch on every platform.
- 24-hour gaps between channels, not 30 minutes.
- Respond to every comment in the first 6 hours. Cold engagement kills posts.
- If one channel flops, pause and diagnose before hitting the next. Don't cascade a bad framing.

**Two-week follow-up post:** "Morning Lineup, two weeks later — what I learned and changed." Repost to Twitter and optionally Show HN (HN allows substantive reposts).

**Day-of sanity checks:**
- Verify r/baseball Rule 2 wording (it moves).
- Test the OG card in Facebook Sharing Debugger + Twitter Card Validator.
- Confirm analytics events flow end-to-end.
- Stage a dry-run post in a throwaway sub first.

**Test scenarios:** *Test expectation: none — document.*

**Verification:** On launch day, follow the checklist top-to-bottom without improvising. Watch `docs/launch/metrics-dashboard.md` fill in with real data for the first time.

---

### Track D — Growth Loop Features

- [x] **Unit D1: Share button on every team page**

**Goal:** A small "Share this team" button in the page masthead that opens the Web Share sheet on mobile, copies the URL on desktop.

**Requirements:** R4

**Dependencies:** Track A complete

**Files:**
- Modify: `build.py` (add share button to the masthead block ~line 1330)
- Modify: `style.css` (button styles)
- Create: `share.js` (per-team copy, event delegation, toast confirmation)
- Modify: `build.py` per-team asset copy loop (line 2335) to include `share.js`

**Approach:**
- Button lives in `.nav-btns` next to "All Teams" and "Your Lineup".
- On click: `navigator.share({title: document.title, url: location.href})` if supported, else `navigator.clipboard.writeText(location.href)` + toast "Link copied".
- Track shares via a simple fire-and-forget `fetch` to an analytics endpoint.

**Test scenarios:**
- Happy path: Mobile click opens share sheet with pre-filled URL.
- Happy path: Desktop click copies URL, shows toast.
- Edge case: Clipboard API unavailable → show fallback modal with the URL selected.

**Verification:** Button works across mobile Safari, Chrome Android, desktop Chrome/Safari/Firefox.

---

- [x] **Unit D2: Smart install prompt**

**Goal:** A dismissible, non-nagging install banner that appears on the 3rd visit (not before), only on mobile, only if not installed.

**Requirements:** R3

**Dependencies:** None (orthogonal to other tracks)

**Files:**
- Create: `install-prompt.js`
- Modify: `build.py` script loading line (add `install-prompt.js`)
- Modify: `build.py` asset copy loop

**Approach:**
- Track visit count in `localStorage.ml_visits`.
- Show banner when `ml_visits >= 3` AND `!matchMedia('(display-mode: standalone)').matches` AND `!localStorage.ml_install_dismissed`.
- Banner sits below the page masthead, collapsible. One action button, one dismiss.
- If the `beforeinstallprompt` event fires, wire it up. Otherwise show iOS-specific "Tap Share → Add to Home Screen" instructions on iOS Safari.

**Test scenarios:**
- Happy path: Visit 1 → no banner. Visit 3 → banner.
- Happy path: Click install → native prompt or iOS instructions.
- Happy path: Dismiss → banner never reappears.
- Edge case: Already installed → banner suppressed regardless of visit count.

**Verification:** Banner appears exactly when expected across iOS Safari, Chrome Android, and desktop.

---

- [ ] **Unit D3: Daily email digest (research-revised — likely deferred)**

> **Strong contrarian signal from research:** Consider skipping email v1 entirely. For a free daily content site, the home-screen install (already shipped in D2+D5) is the retention mechanism. Email is a second surface to maintain — compose, send, unsubscribe handling, SPF/DKIM/DMARC, compliance — for a marginal retention lift at the current audience size. **Revisit this unit once analytics show >500 DAU AND install-prompt acceptance is below target AND there's a newsy reason to send beyond "new edition live."** If those conditions don't hold by week 3 post-launch, drop this unit entirely.

**If it still makes sense to ship:**

**Goal:** Opted-in users receive a 7am CT email with their team's briefing link and yesterday's one-line summary.

**Requirements:** R6

**Dependencies:**
- One-time JB action: buy a cheap domain at Cloudflare Registrar (~$10/yr, e.g. `morninglineup.email` or `.app`)
- Resend account (free, no credit card)
- Supabase: enable `pg_cron` and `pg_net` extensions in Dashboard → Database → Extensions
- New secrets in Supabase: `RESEND_API_KEY`, `SEND_FROM_ADDRESS`

**Files:**
- Create: `supabase/functions/daily-digest/index.ts` (Deno Edge Function)
- Create: `docs/supabase/email-digest.sql` (schema + cron + pg_net setup, idempotent like events.sql)
- Create: `docs/ops/email-digest-setup.md` (runbook for domain DNS records + secrets + cron schedule)
- Modify: Supabase schema — add `email_digest_enabled boolean default false`, `email_verified boolean default false` to `profiles`; create `email_sends` table with unique constraint `(user_id, send_date)`
- Modify: `settings/settings.js` + `settings/index.html` to add an opt-in toggle with double-confirmation
- Create: `privacy/index.html` (short privacy page for CAN-SPAM compliance)

**Approach (revised per research):**
- **Provider: Resend.** Free tier, no credit card, cleanest Supabase DX, first-class Supabase ecosystem integration.
- **Sending domain: owned domain, not `resend.dev`.** Buy `morninglineup.email` at Cloudflare Registrar (~$10/yr). Resend's dashboard wizard auto-generates SPF + DKIM + DMARC records for Cloudflare DNS; verify in <5 min. Start DMARC at `p=none` for monitoring.
- **Double opt-in** (Gmail's 2024 sender rules punish low-engagement lists hard; single opt-in risks burning sender reputation on day one). User clicks "Enable digest" → receives confirmation email → clicks link → `email_verified = true`.
- **Scheduler: `pg_cron` + `pg_net`.** Supabase has no built-in cron UI for Edge Functions. Canonical pattern: `select cron.schedule('ml-daily-digest', '0 12 * * *', $$ select net.http_post('https://...functions.supabase.co/daily-digest', headers := '{"Authorization": "Bearer ..."}'::jsonb) $$);` — DST gotcha: 12 UTC is 7am CT during CDT but 6am CST. Compute the target hour inside the function from `America/Chicago` timezone rather than hard-coding the cron.
- **Idempotency:** Before each send, `insert into email_sends (user_id, send_date) values (...);` with a unique constraint. Duplicate insert = skip. Survives at-least-once cron semantics and function retries.
- **Rate limiting:** Resend free tier allows 2 req/sec. Send in batches of 2 with a 500ms pause, or use `Promise.all` in pairs. For <1000 users this completes in <10 min, well under the Edge Function 400s wall-clock limit.
- **Compliance (CAN-SPAM + Gmail sender rules):**
  - `List-Unsubscribe` one-click header (Resend auto-adds when you pass the header)
  - Unsubscribe link in footer → Supabase RPC that flips `email_digest_enabled = false`
  - Physical mailing address in footer (JB's or a PO box)
  - `/privacy` page explaining what's stored, linked from the email footer
- **Email body:** Plain-text with one link per team. Format: `The {team} · Morning Lineup · Apr 16` + 1-line yesterday-game summary + link to `https://brawley1422-alt.github.io/morning-lineup/{slug}/`. HTML version optional for v1.
- **Warm-up:** <50 person list = invisible, no special ramp needed. For 500+, follow a 50 → 100 → 200 → 500 curve over 5–7 days.
- **Observability:** Log every send into an `email_runs` table from inside the function (user_id, status, error). `pg_cron` jobs succeed even if the function errors — without this table, silent failures are invisible.

**Test scenarios:**
- Happy path: User enables digest in settings → receives confirmation email → clicks link → `email_verified = true` → receives next morning's digest.
- Happy path: User disables digest → no further sends on subsequent mornings.
- Edge case: Duplicate cron fire (at-least-once) → second run inserts into `email_sends`, unique constraint fires, no duplicate email.
- Edge case: Resend API returns 4xx → logged to `email_runs`, function continues with next user.
- Edge case: User signs up between the cron fire and the function query → included if opted-in and verified at query time.
- Integration: `pg_cron` → `pg_net` → Edge Function → Resend API → real inbox at 7am CT end-to-end.

**Verification:** End-to-end with a test account on JB's own email — subscribe, verify, receive the next morning's digest, click through to the team page, analytics fires the `digest_click` event. Then check Resend dashboard for delivery status, spam folder sanity check, and `email_runs` table for zero errors.

---

- [ ] **Unit D4: Web Push notifications on game Final (research-revised)**

**Goal:** Users who grant push permission receive a notification within 2 minutes of their team's game going Final: "Cubs 5, Brewers 3 — Final. Tap for recap."

**Requirements:** R6

**Dependencies:**
- Phase 2 complete (installed PWA via D2's prompt)
- `evening.py` already runs the game-final watcher
- One-time: generate VAPID keys (`npx web-push generate-vapid-keys` or Deno equivalent)
- Supabase secrets: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`

**Files:**
- Create: `push-register.js` (client: pre-prompt button + `pushManager.subscribe()` + POST to `push_subscriptions` table)
- Modify: `sw.js` (add `push` event handler + `notificationclick` handler + `pushsubscriptionchange` handler)
- Create: `supabase/functions/game-final-push/index.ts` (Deno Edge Function using `negrel/webpush`)
- Create: `docs/supabase/push-subscriptions.sql` (schema: endpoint, p256dh, auth, user_id, team_id, created_at)
- Create: `docs/ops/web-push-setup.md` (VAPID generation + secrets + testing runbook)
- Modify: `evening.py` to POST to the Edge Function on game Final (fire-and-forget)
- Modify: `settings/settings.js` + `settings/index.html` to add a "Push notifications" toggle
- Optional: Create: `badge-poller.js` — the `setAppBadge()` fallback described below

**Approach (revised per research):**
- **Library: `negrel/webpush`** (Deno-native, RFC 8291/8292 compliant, works in Supabase Edge Functions). Alternative: `draphy/pushforge`. **Do NOT use the classic Node `web-push` npm package** — it's awkward in the Edge runtime.
- **Pre-prompt is mandatory.** Never call `pushManager.subscribe()` on first visit; Chrome has actively deranked sites that do. Flow:
  1. User lands on a team page with permission `default`
  2. After some engagement (scroll, multi-section click), a custom HTML chip appears: "Get final score alerts for the {Team}"
  3. Clicking the chip calls `pushManager.subscribe()` → browser native permission prompt
  4. Accept → POST subscription payload to Supabase → chip shows "You're subscribed"
  5. Decline → remember dismissal in localStorage; never prompt again (clicking Block is permanent anyway)
- **Payload: tight** to fit Safari's ~256-byte cap on title+body. Template: `"Cubs 5, Brewers 3 — Final. Tap for recap."` No custom images — iOS renders only the PWA app icon; engineering a per-team image pipeline for Chrome-only isn't worth the complexity.
- **Delivery pattern:**
  - `evening.py` detects game Final (existing logic)
  - POST to `https://...supabase.co/functions/game-final-push` with `{team_id, w_score, l_score, w_team, l_team}` + service-role header
  - Edge Function queries `push_subscriptions` for that team_id, loops via `Promise.allSettled` in chunks of 50, sends via `negrel/webpush` with the VAPID keys
  - On 410 Gone or 404: delete the row immediately
  - On success: log to `push_runs` table
- **Subscription lifecycle:**
  - `sw.js` listens for `pushsubscriptionchange` (fires when the browser rotates the endpoint) and re-POSTs the new payload
  - Edge Function handles 410/404 by deleting stale rows
  - Cleanup job optional: nightly delete for rows unseen in 30 days
- **Tap behavior:** `sw.js` `notificationclick` handler calls `clients.openWindow('/morning-lineup/{team_slug}/')`. Works from fully closed state on both Chrome and Safari.

**Permission-free companion — Unit D6: badge polling fallback**

Ship this **alongside** D4, not as an alternative:

- [ ] **Unit D6: Local badge-poll for unseen game Finals**
- **Files:** `badge-poller.js`, modify `build.py` script loading, modify `build.py` asset copy loop
- **Approach:** When the PWA loads (or on `visibilitychange` → visible), fetch `history.json` or a lightweight `latest-finals.json`, compare against `localStorage.ml_last_seen_finals`, and call `navigator.setAppBadge(unseenCount)`. Zero permission theater, zero server cost. Passive re-engagement — badge only updates when the user opens the PWA, but that's still a nudge that "something happened."
- **Why ship both:** Web push is the real-time nudge for users who opted in. Badge polling is the opt-out-proof retention surface for users who declined push. They complement each other.

**Test scenarios:**
- Happy path: Grant push permission via pre-prompt → subscription row written to Supabase → receive notification on next game Final → tap → team page loads.
- Happy path: Decline push → pre-prompt dismissed → no further ask.
- Happy path: Install PWA → badge polling kicks in on next visit → `navigator.setAppBadge` shows unseen count.
- Edge case: Subscription expires (410 from push service) → Edge Function deletes row on next send attempt.
- Edge case: iOS Safari not installed (no home-screen install) → pre-prompt hidden; D6 badge fallback is no-op on non-installed Safari.
- Edge case: EU user (iOS 17.4+ standalone PWA removed) → push + badge both hidden via feature detection.
- Integration: `evening.py` game-final → Edge Function → push delivery → notification rendered → `notificationclick` → team page.

**Verification:** Real device testing — Chrome Android (primary), iOS 16.4+ Safari installed as home-screen PWA (secondary). Subscribe, trigger a fake final via a test Edge Function endpoint, confirm notification within 2 min. Then install PWA, let a real game finish, confirm badge count updates on next PWA open.

---

### Track E — Measurement

- [x] **Unit E1: Plausible or Umami analytics**

**Goal:** Every page emits anonymous page views and custom events (share click, install click, email signup) to a privacy-respecting analytics endpoint.

**Requirements:** R7

**Dependencies:** None — ship alongside Track A

**Files:**
- Modify: `build.py` page envelope (add analytics script tag)
- Modify: `landing.html`
- Modify: `home/index.html`
- Modify: `settings/index.html`
- Modify: `share.js`, `install-prompt.js` (fire custom events)

**Approach:**
- **Plausible** (recommended): Self-host or use Plausible Cloud free tier. One script tag, one line of setup.
- **Umami** (alternative): Open-source, self-hostable on a small VPS.
- Track: page views, share clicks per team, install prompts dismissed vs accepted, email signups.

**Patterns to follow:** N/A — new surface.

**Test scenarios:**
- Happy path: Load cubs page → page view event fires.
- Happy path: Click share button → share event fires with team slug.
- Edge case: Analytics blocked by an ad blocker → site still works.

**Verification:** Plausible dashboard shows page views and events within 30 seconds of interaction.

---

- [x] **Unit E2: Launch metrics dashboard page**

**Goal:** A committed markdown in `docs/launch/` that the operator reviews daily during launch week with the numbers that matter.

**Requirements:** R7

**Dependencies:** E1

**Files:**
- Create: `docs/launch/metrics-dashboard.md`

**Approach:**
- Manual review doc, not automated. Columns: date, page views, unique visitors, top team, shares, installs, signups, retained-next-day.
- Operator fills it in every morning from the Plausible dashboard.
- Purpose: forces a daily check-in during launch week so we actually look at the numbers.

**Test scenarios:** *Test expectation: none — document.*

**Verification:** Dashboard exists and is filled in for at least 7 days post-launch.

---

## System-Wide Impact

- **Interaction graph:** Track A touches `build.py`'s page envelope (every team page regenerates), `landing.html` (single standalone render), `home/` and `auth/` static files, `deploy.py` STATIC_ASSETS list, and the 30 per-team output dirs. Track D adds new client scripts that need the same per-team copy pattern as `tz.js`/`sections.js`.
- **Error propagation:** New meta tags and static files cannot fail at runtime — they're text. The `generate_og_cards.py` script is one-shot and offline, no runtime risk. Email digest and web push have real failure modes (provider down, rate limits) and need retry + dead-letter handling at the Supabase Edge Function layer.
- **State lifecycle risks:** First-visit detection in `welcome.js` / `install-prompt.js` uses `localStorage`. Cleared storage = re-onboarding, not a bug. Push subscription state lives in the service worker; stale subscriptions are the main risk and should be cleaned on 410 responses.
- **API surface parity:** All 30 teams must get OG tags at once or social sharing breaks for any team missing them. Snapshot tests in `tests/snapshot_test.py` will catch accidental per-team drift.
- **Integration coverage:** Track C (launch day) has integration dependencies on real Plausible/Supabase/email providers that can't be fully mocked. Smoke-test each channel with a single real event before launch day.
- **Unchanged invariants:** Existing auth, team-page content, build pipeline, evening watcher, TZ localization, fold design, collapsible sections, and snapshot fixtures are all untouched. None of the launch tracks modify existing briefing logic.

## Risks & Dependencies

| Risk | Mitigation |
|---|---|
| Track A ships but OG tags are wrong — shares look broken on launch day | Use facebook.com/tools/debug and cards-dev.twitter.com/validator on 5 sample team URLs before any external promotion |
| Pre-rendered OG images look stale because they don't include today's game | Accept for v1; upgrade to build-time regeneration only if share-click data justifies the complexity |
| Posting to r/baseball without reading sub rules → instant ban | Read the subreddit's self-promo policy, frame the post as content-first ("I built this for myself"), don't link-farm |
| Product Hunt launch flops because we have no existing network there | Treat it as a secondary channel; don't build the launch around it |
| Email digest ships but deliverability is bad (spam folder) | Use a reputable provider (Resend or SendGrid), set up SPF/DKIM, start with small volume and warm up the sending reputation |
| Web Push permissions spook users if asked too early | Only prompt after 5+ visits AND from a visible settings toggle, never on first load |
| Analytics script slows the page | Use an async defer tag, no render blocking. Plausible script is ~1KB |
| Per-team OG image generation requires 30 manual QA passes | Build the script so regeneration is one command; accept 30 minutes of visual review once |
| PWA install prompt nags iOS users (Safari has no API) | Detect iOS Safari and show a static "Tap Share → Add to Home Screen" message instead of a button |
| Cubs-only evening rebuild means post-game OG content only updates for Cubs | Out of scope for this plan — tracked separately. Non-blocking for launch |

## Success Metrics

- **Shareability:** 100% of team pages render rich OG previews in the Facebook/Twitter validators (binary check).
- **SEO:** Site appears in Google Search Console with 30+ indexed pages within 14 days of launch.
- **Conversion:** Cold landing visits that click into a team page ≥ 40% (measured via Plausible).
- **Install:** Mobile visitors who accept the install prompt ≥ 10% of those who see it.
- **Retention:** Next-day return rate for installed users ≥ 30%.
- **Growth:** Share events per week, tracked by team, non-zero and rising.

## Phased Delivery — Original Plan

### Phase 1 — Foundation ✅ SHIPPED 2026-04-15
- Units A1, A2, A3, A4, A5, E1, E2

Everything was static, no backend changes, fully testable locally. Outcome: shareable links work, Google can find the site, analytics are flowing.

### ~~Phase 2 — Friends & Family Beta~~ (superseded — see Path Forward below)

### ~~Phase 3 — Public Launch~~ (still valid, re-sequenced below)

### ~~Phase 4 — Growth Loops~~ (re-sequenced — D1/D2 moved earlier)

### ~~Phase 5 — Measurement Discipline~~ (subsumed by E2, ships continuously)

---

## Path Forward — Revised Sequence (2026-04-15, post-Phase-1)

Ship order has been re-thought now that Track A and Track E are live.
The original plan treated Tracks B and D as peers; the shipped learning
is that Track B's invite-flow unit economics don't justify its code
footprint for an audience of 20–50 people. Track D1 (share button) is
the one high-leverage unit that makes every already-shipped OG card
actually get used. The revised sequence puts the cheap high-leverage
work first and defers anything requiring Supabase schema changes until
there's data to justify it.

### Phase 2 — Cheap High-Leverage (~4–6 hours)

Goal: **every visitor can share the page they're looking at with one
tap, and every return visitor gets gently nudged to install the PWA.**
Both directly tracked via analytics already wired up.

Order of operations:

- [x] **Unit D1** — Share button on every team page. Cheap (one button, one script, one CSS block), big leverage (multiplies every visitor's sharing ability), directly measurable via `share_click` events. Single most important remaining unit.
- [x] **Unit D2** — Smart install prompt (3rd-visit gate, dismissible, platform-aware). The PWA is already set up; we're just adding the CTA. Measurable via `install_shown` / `install_accepted` / `install_dismissed` events.
- [x] **Unit D5** (new — salvaged from killed B1) — First-visit onboarding overlay on the landing page. Skippable "Pick your team / Install / Come back tomorrow" overlay fired on any first visit. Shares CSS with D2.

Why this order: D1 is the floor. D2 compounds over time. D5 is a
one-time conversion booster for cold visits. All three can ship in one
commit and be measured against baseline analytics within 24 hours of
the public launch.

### Phase 3 — Public Launch (~1 day of prep + launch day)

Once D1/D2/D5 are shipped and verified with a few warm visits, Phase 3
is the actual launch moment.

- [ ] **Unit C1** — Landing page conversion CTA stripe. Ships before C2/C3 because every external post will drive visits to the landing page.
- [ ] **Unit C2** — Press kit page at `/press/`. Something to link from Reddit / Twitter / Product Hunt posts.
- [ ] **Unit C3** — Launch-day distribution checklist. A committed markdown with exact copy and posting order for each channel.
- [ ] **Launch-day execution** — Follow the checklist. Post to r/baseball, 3–5 team subreddits, Twitter, Hacker News, Product Hunt. Watch `docs/launch/metrics-dashboard.md` filling in every morning.

### Phase 4 — Friends & Family (Manual)

- [ ] **Manual F&F outreach** — JB texts the URL to 10–30 people over the course of launch week. No special invite flow, no magic link, no `?invite=1` welcome overlay tied to a query param — those add code for nothing. Plain URLs share cleanly now that OG cards work, and D5 will give any first-time visitor the right onboarding whether they came from a text or from a Reddit post.

This phase was originally Track B. The only valuable piece from B1
(first-visit onboarding overlay) has been moved to Unit D5 above, and
B2 (magic-link invite button) has been dropped entirely — manual
texting is strictly better at this scale.

### Phase 5 — Growth Loops (Ongoing, data-driven — research-revised)

Only ship these after Phase 3 has delivered real analytics showing
where the funnel is leaking. Research pass 2026-04-15 adjusted the
priority order and added Unit D6.

- [ ] **Unit D4 + D6** — Web Push notifications on game Final **plus** permission-free `setAppBadge` local polling companion. Ship together. Realistic subscribed audience is 10–15× smaller than Android-Chrome-only estimates suggest (iOS is install-gated); the badge polling fallback catches users who decline push. Research suggests this is a cleaner v1 than the email digest — the trigger event is already detected in `evening.py`, the subscribe button can be scoped per team, and the whole thing is ~200 lines with `negrel/webpush`. **Priority: first in Phase 5.**
- [ ] **Unit D3** — Daily email digest. **Likely deferred or dropped.** Contrarian research signal: for a free daily content site with home-screen install, email is a second surface to maintain for marginal retention lift. Only ship if analytics at week 3 post-launch show install-accept rate <10% AND next-day return <30% AND there's a newsy reason to send beyond "new edition live." Otherwise drop entirely. Prerequisites if it does ship: buy a cheap domain (~$10/yr), enable `pg_cron` + `pg_net`, Resend account, double opt-in flow.
- [ ] **Plus any new unit the data suggests** — e.g. a "most-shared team this week" module, a leaderboard of reader-picked outcomes, etc. Plan those as they become obvious from the metrics, not in advance.

### Deprecated Units

- **Unit B1** — Invite link landing and onboarding. Superseded by Unit D5 (first-visit overlay for any cold visit, not just invite links).
- **Unit B2** — Supabase magic-link invite button. Dropped. Manual texting is strictly simpler at this audience size.

---

## New Unit — D5: First-Visit Onboarding Overlay

- [x] **Unit D5: First-visit overlay on the landing page**

**Goal:** A skippable, dismiss-once welcome overlay that appears on the landing page for any first-time visitor. Three steps: (1) Pick your team, (2) Install to home screen (if supported), (3) "Come back tomorrow" — plain bookmark reminder, no email required for v1. Persistent dismissal via `localStorage`.

**Requirements:** R3, R5

**Dependencies:** Phase 1 (already shipped)

**Files:**
- Modify: `landing.html` (overlay markup + CSS)
- Create: `welcome-overlay.js` (first-visit detection, step navigation, install prompt wiring, dismissal persistence)
- Modify: `deploy.py` STATIC_ASSETS (add `welcome-overlay.js`)

**Approach:**
- First visit sets `localStorage.ml_onboarded = true` on dismissal.
- Overlay is CSS-driven, sticky above the landing page hero.
- Step 1: grid of team cards — click to set `localStorage.ml_team = slug` and advance.
- Step 2: if `beforeinstallprompt` event has fired, show an "Install" button; else show iOS Safari instructions.
- Step 3: single text — "Come back tomorrow. Every morning by 7 AM CT." + a "Got it" button that dismisses the overlay.
- Analytics: fire `onboard_shown`, `onboard_team_picked` (with `team_slug`), `onboard_install_accepted`, `onboard_dismissed` events via `window.mlTrack`.

**Patterns to follow:**
- Existing `home/home.js` profile-check pattern for first-visit detection.
- Existing `sections.js` IIFE + localStorage pattern.
- Existing `window.mlTrack` API from `analytics.js`.

**Test scenarios:**
- Happy path: First visit with empty localStorage → overlay appears on landing.
- Happy path: Pick team → overlay advances to step 2, `localStorage.ml_team` set, `onboard_team_picked` event fires.
- Happy path: Dismiss → overlay disappears, `ml_onboarded = true`, next visit skips overlay.
- Edge case: Return visit → no overlay regardless of `ml_onboarded` state.
- Edge case: iOS Safari → step 2 shows manual instructions instead of a button.
- Edge case: Already-installed PWA (`display-mode: standalone`) → skip step 2 entirely.

**Verification:** Cold first visit (incognito window) shows the overlay; second visit goes straight to the landing page.

## Alternative Approaches Considered

- **Paid ads (Twitter/Meta/Google):** Rejected — we said no budget. Also, paid traffic to a content site with no retention loop burns money.
- **Build a Twitter bot that auto-posts every game recap:** Rejected for v1 — real engagement risk (Twitter suspends bots), and it competes with the core "hand to friends" play. Could revisit after launch.
- **Submit to MLB as a partner integration:** Very high ceiling, very low probability — requires MLB BAM legal approval. Out of scope.
- **Rebuild the site as a Next.js app on Vercel for SSR OG images:** Massive scope creep. Static pre-rendering is good enough until data proves otherwise.
- **Pay for a Substack newsletter and cross-post:** Rejected — splits audience, steals from the main site's retention.
- **Redesign the home page as a "feed" of team cards:** Out of scope for launch. Current landing + home flow is good enough; the gap is discovery, not UX.

## Documentation / Operational Notes

- **Secrets:** If Track D3 or D4 ships, new secrets live at `~/.secrets/morning-lineup.env` alongside the existing GitHub PAT. Email provider key and VAPID keys should be added to a separate file with documented env var names.
- **Cron:** The morning build already runs. Sitemap generation piggybacks on that — one more function call in the build loop.
- **Deploy:** Every track that touches `build.py` or per-team assets requires a full 30-team rebuild + deploy. Budget 90 seconds for Pages build settling after each push.
- **Rollback:** All Phase 1 changes are reversible in a single `git revert` — meta tags and static files only. Phases 2–4 touch Supabase schema; any schema change should be additive with defaults so rollback is safe.
- **Privacy:** Plausible/Umami don't use cookies → no GDPR banner required. If the email digest ships, add a standard unsubscribe link and a simple privacy page explaining what's stored.

## Sources & References

- **Origin document:** None — this plan was written from the feature request directly after a quick repo audit.
- Related code: `build.py` (page envelope), `landing.html`, `auth/session.js`, `deploy.py` STATIC_ASSETS, `teams/*.json`
- Related prior work: `docs/plans/2026-04-14-003-refactor-stats-pipeline-hardening-plan.md` (completed), the recent fold-design + TZ localization work
- External docs: Open Graph protocol (`https://ogp.me/`), Twitter Cards, Web Share API, `beforeinstallprompt`, Plausible analytics
