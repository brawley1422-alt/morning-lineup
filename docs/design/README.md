# Design prototypes

Self-contained HTML mockups produced during editorial design sessions. These are the source-of-truth designs that shipped work was built from, plus deferred work still waiting to ship.

Every file here is a single-file HTML artifact with inline CSS — no external dependencies beyond Google Fonts. Open any one of them directly in a browser to see the design as originally sketched.

## Index

| File | Origin | Status | Shipped to |
|---|---|---|---|
| `2026-04-10-auth-redesign.html` | 2026-04-10 editorial session | ✅ Shipped | `auth/index.html` + `auth/auth.css` (commit `9ff98b2`) |
| `2026-04-10-auth-signup-variant.html` | 2026-04-10 editorial session | ✅ Shipped (pattern only) | The signup-mode styling was folded into the main auth page's `auth.js`-driven mode toggle in commit `9ff98b2`. This variant stays as reference. |
| `2026-04-10-reset-redesign.html` | 2026-04-10 editorial session | ✅ Shipped | `auth/reset.html` (commit `9ff98b2`) |
| `2026-04-10-404-redesign.html` | 2026-04-10 editorial session | ✅ Shipped | `404.html` at repo root (commit `9ff98b2`) |
| `2026-04-10-team-briefing-polish.html` | 2026-04-10 editorial session | ✅ Shipped | `sections/headline.py` + `style.css` headline block (commit `56ea6f2`). Note: the TOC bar shown in this prototype is deferred to Unit 2 of the Phase 3 plan. |
| `2026-04-10-scorecard-finder-redesign.html` | 2026-04-10 editorial session | ⚠️ Partially shipped | Only the masthead polish shipped to `scorecard/index.html` + `scorecard/styles.css` in commit `d7807ab`. The game-picker card grid (the "no game selected" landing state) is deferred to Unit 5 of the Phase 3 plan. |
| `2026-04-10-landing-authed-redesign.html` | 2026-04-10 editorial session | 🟡 Pending | Deferred to Unit 4 of the Phase 3 plan. Greeting bar + Your Team hero + team grid with live-game glows. |
| `2026-04-10-home-wedge-alternate.html` | 2026-04-10 editorial session | ❌ Not shipping | The current live `/home/` page has a functional guest preview flow with sample columnist content. This alternate is a regression in information density — more marketing splash, less useful preview. Kept here as design-direction reference, intentionally not shipping. |

## Related docs

- **Phase 3 plan** (follow-up work from this session): `docs/plans/2026-04-10-004-feat-editorial-polish-phase-3-plan.md`
- **Shipped commits from this session**: `9ff98b2` (auth + reset + 404), `b89b849` (columnist accordion), `d7807ab` (scorecard masthead), `6b0199f` (columnist editorial redesign), `56ea6f2` (headline editorial polish)

## Conventions for future sessions

- Name new prototypes `YYYY-MM-DD-<descriptive-slug>.html`.
- Every prototype should be self-contained HTML with inline CSS so it's openable standalone without a build step.
- When a prototype ships, update this README's table with the commit hash and the target file path(s).
- When a prototype is explicitly NOT shipping, document why in the table so a future reader doesn't wonder why it was forgotten.
