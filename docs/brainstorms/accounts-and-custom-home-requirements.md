# Morning Lineup — Accounts & Customizable Home Page (v1)

**Date:** 2026-04-10
**Status:** Requirements — ready for planning
**Brainstorm type:** Deep (strategic product direction + feature scope)

## Context

Morning Lineup today is a 30-team static MLB briefing site published to GitHub Pages. It runs on a cron, costs ~$0/mo, and has no accounts, email list, analytics, or monetization. This brainstorm explored whether Morning Lineup has a real business case and what the first product move toward that should be.

**Decisions reached during brainstorming:**

- **D1 — Primary audience:** Die-hard baseball fans, with fantasy players as a welcome secondary. The product's soul stays editorial/narrative, not spreadsheet. [HIGH confidence]
- **D2 — Positioning wedge:** "The morning paper baseball deserves." Competes on *feel* and *daily ritual*, not info completeness. Closest analogs are newsletter empires (Morning Brew, The Hustle) — none exist in sports. [HIGH confidence]
- **D3 — Ambition ceiling:** Tier 2 (self-sustaining, $1-10k/mo, 10-50k engaged readers) with Tier 1 as the safety net. Tier 3+ stays optional, not planned. [HIGH confidence]
- **D4 — First product move:** Accounts + customizable home page. Chosen over email-first because customization is the actual product differentiator and sets up email, scorecards, and monetization to work *better* later. [MEDIUM-HIGH confidence]
- **D5 — Customization scope:** Full (teams + sections + layout order + theme + scorecard profile integration). [User decision — MEDIUM confidence on v1 scope, may trim during planning]
- **D6 — Architecture:** Supabase for auth + profile data. Client-side rendering on top of existing per-team JSON ledgers. No server, no backend rewrite, preserves $0 infra. [HIGH confidence]

## Requirements

### Auth & identity

- **R1** — User can create an account with email/password and optionally Google OAuth, via Supabase Auth.
- **R2** — User can log in, log out, and reset password. Session persists across visits via Supabase client.
- **R3** — User profile is stored in a Supabase `profiles` table linked to `auth.users`, containing: display name, followed teams (1+), section visibility map, section order, display density, theme preference, created_at, updated_at.

### Customizable home page

- **R4** — New route `/home` renders a personalized daily briefing for the logged-in user. Route is client-side rendered — no changes to `build.py` output for the 30 static team pages.
- **R5** — User can follow 1 or more teams. If following multiple teams, `/home` displays a **merged briefing** combining each followed team's data for the day (one masthead, sections grouped or interleaved — exact layout to be resolved in planning).
- **R6** — User can toggle visibility of each section (headline, scouting, stretch, pressbox, farm, slate, division, around-the-league, history).
- **R7** — User can reorder sections via drag-to-reorder. Order persists in profile.
- **R8** — User can choose display density: **compact** (fewer details, higher density) or **full** (current per-team page behavior).
- **R9** — User can choose theme: at minimum paper (cream) and dark (current scorecard palette). Extends existing CSS variable system.
- **R10** — Logged-out visitors to `/home` see a signup prompt + preview (not a redirect — preview earns signups).

### Scorecard Book integration

- **R11** — Scorecard Book persists completed scorecards to the user's profile when logged in. Existing localStorage fallback remains for logged-out users.
- **R12** — Profile page includes a "My Scorecards" section listing saved games, sortable by date, with links to reopen each one.

### Settings & account management

- **R13** — Settings page (`/settings` or `/profile`) lets users edit followed teams, section visibility, section order, display density, theme, and display name.
- **R14** — User can delete their account and all associated data (Supabase row delete + scorecard data removal).

### Brand & design

- **R15** — All new UI (signup, login, home, settings, profile) matches Morning Lineup's editorial newspaper aesthetic. No generic dashboard look. Reuses existing CSS variables, fonts (Playfair Display, Oswald, Lora, IBM Plex Mono), and color system.
- **R16** — Existing 30 per-team static pages are unchanged. Zero regressions to the current experience for logged-out readers.

## Success Criteria

- **SC1** — A first-time user can sign up, pick 1+ teams, and see their personalized home page within 60 seconds of landing on the signup flow. [HIGH priority]
- **SC2** — Preferences (teams, sections, order, density, theme) persist across devices via Supabase. [HIGH priority]
- **SC3** — `/home` initial render < 2 seconds on desktop broadband. Client-side merge of prebuilt JSON should comfortably meet this. [MEDIUM priority]
- **SC4** — Zero regressions: all 30 existing team pages render identically (byte-identical via the snapshot test harness in `tests/`). [HIGH priority]
- **SC5** — Scorecard saves persist per user across sessions and devices. [MEDIUM priority]
- **SC6** — Adoption signal: 100 signed-up accounts within 30 days of launch. [MEDIUM priority — distribution-dependent]
- **SC7** — Validation signal: >40% of signed-up users follow 2+ teams. Confirms the multi-team wedge is real. [MEDIUM priority]
- **SC8** — Engagement signal: logged-in users return at least 3 days of the first 7 post-signup. [MEDIUM priority]

## Scope Boundaries

### In scope for v1

- Supabase auth (email/password + Google OAuth)
- `profiles` table with followed teams, section visibility, order, density, theme
- `/home` client-rendered route with multi-team merge
- Section visibility + drag-to-reorder
- Display density toggle
- Theme toggle (paper/dark)
- Scorecard Book → profile save/load
- Settings page
- Profile page with saved scorecards list
- Signup/login UI in editorial aesthetic
- Account deletion

### Explicitly out of scope for v1 (deferred, not cancelled)

- **Email delivery** — daily newsletter email. Next after accounts land. [HIGH confidence it's next]
- **Push notifications** — browser/PWA push for game starts, big moments.
- **Social features** — comments, follows, sharing, public profiles, leaderboards.
- **Paid tier / premium features** — monetization waits until usage is validated.
- **Sponsor slots** — monetization layer two, after paid tier question is answered.
- **Prediction games / pick'em** — scope creep, different audience.
- **User-contributed content** — custom history entries, game notes, journal.
- **Team-branded premium pages** — licensing/partnerships, far future.
- **Analytics dashboard for JB** — useful but separable; can be added with Plausible or Umami later.
- **Native mobile apps** — PWA is sufficient for v1.
- **SEO for `/home`** — it's logged-in and per-user, not indexable content.
- **Multi-sport expansion** — MLB only. Other leagues are a post-validation question.

### Non-goals (things v1 is deliberately *not* trying to be)

- Not replacing the static per-team pages. They remain the public front door and SEO surface.
- Not adding a backend server. Supabase client + static hosting only.
- Not monetizing in v1. The goal is validated usage, not revenue.
- Not a full CMS or editorial tool.
- Not a community platform.

## Open questions for planning

- **Q1** — Email provider for Supabase auth emails: Supabase default, Resend, or SMTP via existing provider?
- **Q2** — Supabase project region: `us-east-1` default, or closer to Chicago?
- **Q3** — URL structure: `/home` path, subdomain, or treat `brawley1422-alt.github.io/morning-lineup/home/` acceptably?
- **Q4** — Scorecard data migration: current localStorage format → Supabase schema. Lossless migration path?
- **Q5** — Multi-team merge UX: grouped by team (team A's sections, then team B's), interleaved by section type (all headlines together, all farms together), or user-configurable?
- **Q6** — Logged-out `/home` preview content: generic sample, or rotating "try it with the Cubs" style teaser?
- **Q7** — Rate limiting / abuse: does Supabase free tier cover projected signup volume, or do we need throttling?
- **Q8** — Does the brainstorm-decided "Full" scope need to be trimmed during planning if the timeline exceeds ~5-6 weeks, and if so, which requirements are droppable? (R7 drag-to-reorder and R9 theme are the two most easily deferred.) [MEDIUM confidence on trim order]

## What comes after v1

Rough sequence if v1 validates the thesis (SC6 + SC7 + SC8 all hit):

1. **Email delivery** — daily per-team-set email. Biggest Tier 2 growth lever. [HIGH confidence]
2. **Distribution push** — Reddit, team bloggers, Twitter presence, SEO. [HIGH confidence]
3. **Sponsor slots + media kit** — first monetization layer once readership exists. [MEDIUM confidence on sequencing]
4. **Paid tier** — scorecard-centric (save unlimited games, season books, print-on-demand). [MEDIUM confidence]

Re-brainstorm the sequence above once v1 is live and early usage data exists. This v1 doc does not commit to the post-v1 roadmap.
