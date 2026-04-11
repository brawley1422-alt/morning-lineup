# Morning Lineup — Design Audit
**Date:** 2026-04-11
**Reviewer:** frontend-design pass on 21 screenshots + `style.css` / `home/home.css`
**Viewports:** 1280x900 desktop, 390x844 mobile

---

## 1. Aesthetic Health Check

The dark-newspaper vision is landing on the **team pages** and **scorecard standalone**. It is not landing yet on the **landing page** and **home binder**, which still read like generic dark dashboards with a serif title pasted on top. The team pages are the strongest surface by a wide margin — they look like something a fan would actually screenshot and share. Everything else is trailing.

| Surface | Score | One-line verdict |
|---|---|---|
| Landing (team picker) | **5/10** | Masthead is pretty, but the body below it falls off a cliff into generic-dark-UI land. "This is just a taste" panel is the weakest thing on the site. |
| Cubs top fold | **8/10** | Masthead + TOC + linescore is genuinely the vision. Looks like a real paper. |
| Cubs full scroll | **7/10** | Strong top, but density drifts, section spacing gets lazy lower down, and gold accents get sprinkled too evenly — no hierarchy of importance. |
| Scorecard standalone | **8/10** | Best-branded surface on the whole site. The "Seat in the Press Box" tagline does more work than anything in the home binder. |
| Player card (front) | **7/10** | Cream card on dark ground is a real moment. Back isn't shown — can't rate. |
| Mobile team page | **6/10** | Readable and survives the shrink, but the top fold wastes 60% of the first viewport on masthead chrome before you see a single stat. |
| Mobile home binder | **n/a** | Stuck in loading state — noted, not scored. |
| Team variants (Cubs/Yanks/Dodgers) | **4/10** | Team colors barely touch anything. This is the biggest aesthetic miss — three teams, one feel. |

Overall site score: **6.5/10.** The vision is real and the good parts are really good. The rest is undercooked and the team-variant problem is the thing that will make a hardcore fan shrug.

---

## 2. Per-Surface Findings

### Landing page (team picker)
**Working:**
- Masthead lockup ("YOUR Lineup") is confident, the gold underline + cream double-rule reads editorially.
- Top metadata strip ("READER GUEST / FOLLOWING / PROVEN / SETTINGS") has the right cond-uppercase rhythm.

**Broken:**
- The "this is just a taste" preview box is the single weakest element on the site. It's a rounded-rect marketing panel parachuted into a newspaper — wrong vocabulary entirely. It looks like a Mailchimp modal.
- "The Columnists" as an H2 with no per-column visual differentiation reads like a placeholder list. These should be three bylines with headshots or at least oversized drop-caps — right now they are an unread TODO list.
- Below the fold it just... stops. The full-page scroll shows a huge vertical dead zone of "The Cubs / Scouting Report / The Stretch..." section headings stacked with nothing in them. This is a preview that is selling nothing because every section is empty. Either populate shadow previews or compress these into a single "what you're missing" editorial block.

**Mediocre:**
- "CREATE A FREE ACCOUNT" button uses a generic gold fill that echoes nothing else on the page. Looks like Bootstrap.
- Division/team switcher dropdown has no newspaper personality — it's a default `<select>`.

### Cubs team page — top fold
**Working:**
- Full masthead ("THE Morning Lineup") with Cubs bug on the left is *the* design moment. Keep this pattern forever.
- The dek strip ("APR 11 2026 / VOL X NO Y / 8:10 CENTRAL / VIA MLB STATS API") nails the "real newspaper" affordance. This is the best piece of UI on the site.
- TOC sidebar with `decimal-leading-zero` numerals is excellent — it's doing aesthetic AND navigational work.
- Columnists list with "A DAILY DISPATCH FROM THE TRUSTY TYPISTS & VICARS" kicker is a lovely touch.

**Broken:**
- The "PIT 0 — 0 CHC" linescore at the top fold is enormous AND empty — no runs, no pitchers, no highlight. On a day with data this sings; on a day without it screams "nothing happened." Needs an empty-state treatment that doesn't occupy the same footprint as a populated one.

**Mediocre:**
- The three columnists rows all use identical styling. Would benefit from letting the first row breathe larger (a "lead column" treatment) — newspapers never give three stories equal weight.

### Cubs page — full scroll (sections 1-9)
**Working:**
- Section `summary` headers with dashed gold numeral box + gradient rule across the top (`background-image:linear-gradient(90deg, paper, gold, paper)`) is distinctive and consistent. This is the load-bearing visual identity across sections.
- `.tempbox.hot` and `.tempbox.cold` with accent-colored top borders are a rare place where color actually means something.

**Broken:**
- **Density is flat.** Every section uses roughly the same row-height and the same gold highlight frequency. A newspaper has a pyramid: big lede, dense middle, scannable tail. Here, "Around the League" has the same visual weight as "The Stretch." Nothing is prioritized.
- **Gold fatigue.** Every stat column, every link, every header rule, every button, every `td.num`, every `.slate-inn`, every `dt` uses `--gold` or `--gold-dim`. When everything is the accent, nothing is the accent. Count the gold hits on a full-page scroll — easily 80+.
- Section spacing between consecutive sections is too uniform (`section{margin:18px 0 22px}`). Newspapers use heavier rules between "beats" — the break from "Down on the Farm" into "Today's Slate" should feel like turning a page, not like the next `<details>`.
- The "WANT THE WHOLE PAPER?" CTA at the bottom is a naked centered button on black. It deserves either a full-width cream footer panel or an editorial "SUBSCRIBE" masthead echo.

**Mediocre:**
- Tables (`table.data`, `table.standings`) are technically correct but visually anonymous — same type size, same row height, same dashed-bottom. Giving the leader's row a heavier paper-cream bar would cost nothing and read enormously.

### Scorecard book (standalone)
**Working:**
- "Members Desk — Digital Scorer's Book" kicker + "A Seat in the Press Box — Pencil & Paper For Every Game" dek is the best voice anywhere on the site. This is the editorial confidence the rest of the site should aspire to.
- The three stat badges (LIVE NOW / FINAL / UPCOMING) in cream numerals on dark ground are perfectly calibrated.

**Broken:**
- Below the fold, the today's-slate grid is visually identical to the landing preview grid — the branding moment evaporates after the first scroll.

**Mediocre:**
- The filter controls (date picker, team filter) are default form controls wearing a dark skin. They don't match the masthead's voice.

### Player card (front)
**Working:**
- Cream card on dark ground is a real visual event. The headshot-over-team-color-bar + monospace stat line below is the right vocabulary — it reads like a 1980s Topps card.

**Broken:**
- Desktop screenshot shows a lot of dead dark space around the card. At 1280px a single card floating in a void feels like a modal, not a trading card. The surrounding page should dim behind it and add some printed-paper texture, or the card should be flanked by "PREV / NEXT" arrows so it feels like a binder page, not a lightbox.
- No visible back-of-card state in the audit set — can't rate the flip.

**Mediocre:**
- The "2" in the top-right of the card is presumably jersey number but sits without a label — a tiny "NO." above it would clarify instantly and add Topps-era honesty.

### Mobile team page
**Working:**
- Masthead holds up under 390px — the cond-uppercase kicker still reads, the serif italic still feels alive.
- TOC collapses into a horizontal pill strip (the `@media (max-width:900px)` rule) — correct move.

**Broken:**
- The first 480px of the mobile viewport is entirely masthead + kicker + dek + TOC pills. On a phone that's almost the whole fold with no content. The `h1` clamp of `9vw` is too aggressive at mobile — `clamp(44px, 9vw, 108px)` hits ~35px at 390px, which is fine, but the surrounding padding is too generous for the viewport.
- Columnists list items look unstyled on mobile — no avatar, no hierarchy, just three rows of similar-weight text.

**Mediocre:**
- The horizontal TOC pill strip wraps to two rows on Cubs, which feels like scope creep rather than design.

### Mobile home binder (blocked state)
Both `12-home-fullpage-desktop.png` and `31-home-fullpage-mobile.png` show "Loading your lineup..." with a huge dark empty column below. Noted, scoped out. The only observation worth making: the **loading state itself is a design decision and it's bad.** A blank 8000px-tall black column with a single italic line is not a newspaper loading — it should be a skeleton of the columnists, a fake dek strip, and maybe a rotating "POLISHING THE PRESS..." kicker. Right now it looks broken, not loading.

### Team variants (Cubs vs Yankees vs Dodgers)
**This is the biggest miss.** All three team pages feel 90% identical.

- Looking at `02-cubs-top-desktop.png`, `03-yankees-top-desktop.png`, `04-dodgers-top-desktop.png` side by side, the only delta is: (a) the tiny team bug in the top-left of the masthead, (b) the thin left-border on `.game-result` (`border-left:4px solid var(--team-primary)`), and (c) the `.my-team` row in standings.
- `--team-primary` and `--team-accent` are declared in `style.css:5-6` and then used in a dozen places but almost all of them are 4px borders or subtle background tints. You cannot tell a Yankees page from a Dodgers page from across the room.
- A Dodgers fan should feel "LA" when they load their page — right now they feel "dark editorial with a blue dot." Cubs should feel IVY-tinged, Yankees should feel PINSTRIPE-tinged. None of that is happening.

**Fix direction:** team primary should flood a hero background band behind the masthead (5-8% tint), the section-rule gradient (`section > summary` background-image) should swap gold for team-accent on lede sections, and the `.toc` `border-top` should be team-primary not gold-dim.

---

## 3. Cross-Cutting Issues

### Typography drift
- The four-font stack (Playfair / Oswald / Lora / IBM Plex Mono) is doing the right work in the masthead and section headers, but **Lora is barely visible** on body copy. Most `section h3` and `section h4` use `--cond` (Oswald). Plays list `.txt` uses unqualified `font-size:14px` with no family — it's falling back to system-serif, not Lora.
- Italic Playfair is used in TWO places that compete: masthead `h1` and every `section > summary .h`. The section headers should probably shift to Oswald Black or upright Playfair to give the masthead exclusivity on italic. Right now the masthead's identity is diluted every time you scroll past a section header.

### Spacing inconsistency
- `section{margin:18px 0 22px}` uses 18/22 asymmetrical gutters — fine in isolation, but `.masthead{padding:14px 20px 10px}` uses 14/10, `.toc{padding:16px 14px 14px}` uses 16/14/14, `.game-result{padding:18px 20px 16px}` uses 18/20/16. There is no 4px/8px rhythm — every component picked its own padding in isolation. Establish a scale (`--s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:24px; --s6:40px`) and refactor. This alone would tighten the feel enormously.

### Color accent overuse
- `--gold` appears as: link color, button border, section numeral, section hover h-color, stars rank color, linescore .rhe, .wp-line lbl color, td.num color, standings pct color, plays .inn color, tempbox .s color, nx-time color, nx-dome bg, live-badge accent, slate-inn color, transac dt...
- That's a dozen roles for one color. Gold should mean ONE thing (e.g., "editorial chrome: rules, numerals, masthead kicker") and team-accent should take over the data-emphasis role (winners, leaders, RHE totals).

### Motion
- The only motion on the page is the `live-badge .dot` pulse and a `summary:hover` color shift. A newspaper can still have motion — think of the "developing story" chyron, or a 1-row ticker across the top. The site feels paused. A single marquee or rotating "BREAKING" strip above the masthead would sell the "morning edition" metaphor harder than any static polish.

### Repetitive patterns
- Every section body opens with one or two `section h3` mini-headers, then a table, then maybe a tempbox. By section 6 the reader has memorized the rhythm. Newspapers vary form per beat: sidebar, quote pull, photo, box score. The site currently has one template applied nine times.

### Density problems
- The Cubs full-scroll is ~6000px tall with no editorial pacing. Newspapers use visible page breaks. Introduce a full-width cream horizontal rule with a section kicker ("EDITION CONTINUES — PAGE C") at the 3000px mark to create the sense of "turning the page."

### Mobile responsiveness
- Font clamps are aggressive but container padding isn't — body sections still carry desktop-scale `padding:18px 20px` on 390px viewports, eating 10% of horizontal real estate.
- Tables (standings, leaders, transactions) haven't been considered on mobile at all — they horizontally scroll or crunch, and neither is handled. Need a mobile variant that stacks (card-per-row) or elides columns.

---

## 4. Prioritized Change Plan

### P0 — Embarrassing, fix today

**P0-1. Team variants must actually differ.** Inject a 6% team-primary tint behind the masthead band and swap the `section > summary` background gradient from `paper → gold → paper` to `paper → team-accent → paper`. *Why it matters: right now a Yankees fan and a Dodgers fan are looking at the same site with a different logo. That's the first thing they'll screenshot-share, and it won't say anything about their team.*
- Files: `style.css` (lines 30, 55)
- Effort: **1hr**

**P0-2. Kill the rounded "this is just a taste" panel on landing.** Replace with an editorial block: cream-on-dark pull quote ("You're reading the Guest Edition. Sign in for your team's front page.") with the columnists strip continuing directly below. *Why it matters: this one panel is the strongest "AI slop" signal on the entire site — it breaks the newspaper metaphor in exactly the place a new visitor first lands.*
- Files: `landing.html`, `home/home.css` or inline landing CSS
- Effort: **1hr**

**P0-3. Fix the home-binder loading state.** Replace "Loading your lineup..." black void with a skeleton echo of the columnists strip + a rotating kicker ("POLISHING THE PRESS..." / "INKING THE PLATES..." / "WAITING ON THE WIRE..."). *Why it matters: the current loading state looks like a 500 error, not a loading state. JB's testers will bounce.*
- Files: `home/home.css`, `home/index.html` (wherever the loading markup lives)
- Effort: **half day**

### P1 — Costs the site a point, fix this week

**P1-1. Establish a spacing scale and refactor.** Add `--s1..--s6` variables to `:root`, then replace hardcoded paddings in `.masthead`, `.toc`, `.game-result`, `.three-stars`, `.nx-card`, `section > summary`. *Why it matters: the "almost right" feeling across the site is 80% spacing drift. A two-hour refactor removes the biggest AI-slop tell.*
- Files: `style.css` (global)
- Effort: **half day**

**P1-2. Break the gold monoculture.** Decide gold = "editorial chrome only" (numerals, rules, masthead kicker). Reassign stat-emphasis roles to `--team-accent-hi`: `table.data td.num`, `table.standings td.pct`, `.linescore th.rhe`, `.linescore .rhe-total.gold`, `.plays .inn`. *Why it matters: this simultaneously (a) reduces gold fatigue and (b) makes team colors earn their keep on every page.*
- Files: `style.css` (lines 82, 88, 117, 125, 128)
- Effort: **1hr**

**P1-3. Varied section templates.** Pick three sections and give them non-default layouts: (a) "This Day in History" should be a pulled-quote column with an oversized drop-cap date, (b) "The Pressbox" should be a two-column `column-count:2` body like a newspaper column, (c) "Around the League" should have a ticker strip at the top. *Why it matters: nine sections with identical rhythm is the #1 reason the full scroll feels monotonous.*
- Files: `style.css`, `sections/history.py`, `sections/pressbox.py`, `sections/around_league.py`
- Effort: **full day**

**P1-4. Fix the mobile top fold.** Drop masthead h1 clamp minimum from 44px to 36px on `<480px`, compress TOC to horizontal scroll (not wrap), reduce section-body horizontal padding from 20px to 14px. *Why it matters: mobile readers don't see any content before they've already scrolled once. That's the kill-shot for a daily-briefing format.*
- Files: `style.css` (lines 33, 52, ~body sections)
- Effort: **1hr**

**P1-5. Empty-state for the linescore.** When the game is pre-game or no-game, the hero should show the masthead's dek-style matchup card instead of a 0-0 linescore. *Why it matters: on off-days the current design implies "game happened, nobody scored" which is the worst possible signal on a baseball briefing.*
- Files: `sections/headline.py`, `style.css`
- Effort: **half day**

### P2 — Visible polish, fix this month

**P2-1. Section-break "page turn" rule.** Add a full-width cream horizontal rule with a `PAGE B — CONTINUES` kicker between sections 3/4 and 6/7.
- Files: `style.css`, `build.py` (section envelope)
- Effort: **1hr**

**P2-2. Columnists rows — lead-column treatment.** First columnist gets double-height and a drop-cap of the first initial; rows 2 and 3 stay compact.
- Files: `style.css`, whatever renders the columnists strip
- Effort: **1hr**

**P2-3. Mobile table cards.** Wrap `table.standings` and `table.data` in a mobile-only "stack view" where each row becomes a card.
- Files: `style.css` only (via `@media`), possibly markup
- Effort: **half day**

**P2-4. Kill button fallback styling.** All buttons currently inherit a generic gold-fill. Give `.cta` a letterpress treatment: cream serif italic on dark, with a cream double-underline.
- Files: `style.css`
- Effort: **15min**

**P2-5. Scorecard embed consistency.** The scorecard iframe on the team page loses the scorecard standalone's voice ("A seat in the press box"). Embed the kicker above the iframe.
- Files: `sections/headline.py` or scorecard embed markup
- Effort: **15min**

### P3 — Nice to have

**P3-1.** Typographic ligatures on masthead (`font-feature-settings:"liga","dlig"`). 15min.
**P3-2.** Subtle paper-grain SVG noise overlay on `.game-result` and `.three-stars` at 3% opacity. 15min.
**P3-3.** Player card back design (not in audit set, so presumed unstarted). Half day.
**P3-4.** "As of 8:12 AM CT" live freshness stamp on the masthead dek. 1hr.
**P3-5.** Favicon rework — use the gold numeral box motif. 15min.

---

## 5. Bold Moves Worth Considering

These aren't polish — these are the directional bets that separate "good vibe-coded static site" from "thing a fan blog would embed."

### Bet 1 — Commit to the "dateline" fiction all the way down
Right now the masthead is the only part of the site that commits to the newspaper metaphor. The bold move is to extend the fiction into every section header: every section `summary` gets a fake byline ("BY THE WIRE DESK — 8:02 AM CT"), every stat block gets a "SOURCE: MLB STATS API" footer in 9px mono, and every section gets a fake edition number. None of this is data — it's editorial chrome. Cost: ~2hrs of CSS + Python string work. Payoff: the site stops feeling like "a static site that uses serif fonts" and starts feeling like "a paper." This is the single change that would make a fan blog care.

### Bet 2 — The columnists are real, and they rotate
Right now "The Columnists" is three invented names in an italic row. The bold move: each columnist writes ONE section. "Walt Kleniewicz" owns the Pressbox. "Tony Gedecki" owns the Stretch. "Beatrice 'Bee' Vittorini" owns Around the League. Each section gets a small byline card at the top with an italic "BY WALT KLENIEWICZ" + kicker. The lede voice of each section changes subtly per "author" (a single Python string swap in each section renderer). The reader starts to remember them. Cost: 1 day. Payoff: the site has personality, which every other static briefing site lacks.

### Bet 3 — The binder IS the paper — physically
The home binder loading-screen shows how exposed this surface is. The bold move: lean into a literal bound-book metaphor. The "My Players" section becomes a cream card-binder (already in `50-my-players-binder-real.png`), but the WHOLE home page adopts a "page of a leather scorebook" frame — a thin outer border with stitched-edge SVG, a ribbon bookmark hanging from the top-right, and page-flip arrows between today/yesterday. This ties the Scorecard Book standalone design language (which is already the strongest on the site) into the home experience. Cost: 1 day CSS + ~50 lines of inline SVG. Payoff: home has a visual identity that is not "dashboard." This is the missing leg of the stool: currently you have "the paper" (team page) and "the scorebook" (scorecard standalone) but no home identity. This makes home the binder that holds them both.

---

## Appendix — Observations that didn't fit above

- `.masthead h1 .lineup` uses `background-clip:text` for a cream-to-paper-dim gradient. Lovely touch, keep it. Consider adding `text-shadow:0 2px 0 rgba(0,0,0,.4)` — it's already there, good.
- `--team-primary-hi` and `--team-accent-hi` exist but are only used in 4 places. Underutilized.
- The `section > summary` gradient-rule is the site's best decorative idea and should be emulated in more places (e.g., `.masthead` bottom border could use it instead of a flat double-rule).
- The scorecard's `.the-stretch`-style dek is the best voice on the site — take anything from `scorecard/styles.css` that can be lifted into the main stylesheet.
- "Loading your lineup..." appears on desktop at the same size it appears on mobile. That's wrong — desktop has room for a real skeleton.
- `ul.plays .txt` has no font-family declared, so it falls back. Add `font-family:var(--serif-body, var(--cond))` or commit to Lora for body copy. It's declared nowhere I can find.
