---
date: 2026-04-08
topic: live-scoring
---

# Live Game Scoring

## Problem Frame

The Scorecard Book currently only renders completed games. During a live game, users have no way to watch the scorecard fill in as plays happen — the most satisfying version of the experience. This adds real-time polling so in-progress games render and update live.

## Requirements

**Live Polling**
- R1. When viewing an in-progress game, poll the MLB live feed every 20 seconds for new play data
- R2. Stop polling when the game reaches Final status
- R3. Pause polling when the browser tab is hidden (Visibility API); resume on tab focus
- R4. Bypass the API cache during live polling so fresh data is always fetched

**Scorecard Updates**
- R5. New completed at-bats appear as diamond cells in-place without re-rendering the entire grid
- R6. The line score header updates with current inning scores as they change
- R7. Pitching decisions (W/L/S) appear in the header once the game is Final

**Live Situation Bar**
- R8. Display a compact situation bar showing: current batter, current pitcher, count (B-S-O), and baserunners (diamond SVG)
- R9. The situation bar is visible only during in-progress games; hidden once Final
- R10. Situation bar updates on each poll with current at-bat data

**Game Finder**
- R11. In-progress games are clickable in the game finder with a LIVE badge
- R12. Preview/Scheduled games remain non-clickable

**Visual Indicators**
- R13. A pulsing LIVE indicator visible while the game is in progress (reuse Morning Lineup's pulse animation)
- R14. When the game goes Final, replace the LIVE indicator with a FINAL badge and stop polling

## Success Criteria

- User can open a live game from the finder and watch diamond cells appear as at-bats complete
- Situation bar shows accurate current batter/pitcher/count/runners between plays
- Polling stops cleanly when the game ends or the tab is hidden
- No visible flicker or full-page re-renders during updates

## Scope Boundaries

- **In scope:** Live polling, in-place diamond updates, situation bar, live finder cards
- **Out of scope:** Pitch-by-pitch animation, sound/notifications, live embed in Morning Lineup (the Morning Lineup embed still shows yesterday's final game only)

## Key Decisions

- **Reuse live.js patterns:** 20s poll interval, Visibility API pause, adaptive idle — proven approach already in production on Morning Lineup
- **In-place updates over full re-render:** Compare new parsed model against current state, only insert/update changed diamond cells. More code but dramatically better UX.
- **Situation bar:** Compact, same aesthetic as Morning Lineup's live widget situation display

## Next Steps

-> `/ce:plan` for structured implementation planning
