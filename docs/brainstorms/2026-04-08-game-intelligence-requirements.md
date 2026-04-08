---
date: 2026-04-08
topic: game-intelligence
---

# Game Intelligence Layer

## Problem Frame

The Scorecard Book renders play-by-play data faithfully, but a real baseball experience includes more context: where to watch, what the weather's doing, and how the batter has fared against this pitcher before. This adds three data layers — broadcasts, weather, and player stats — as collapsible panels that turn the scorecard from a record of what happened into a richer picture of the game.

## Requirements

**Broadcast Panel**
- R1. Display TV and radio broadcast options in a compact panel in the game header area
- R2. Show home and away broadcasts separately, with station/service name and type (TV, AM, FM)
- R3. Include Spanish-language broadcasts when available
- R4. Also surface broadcast info in Morning Lineup's Cubs game section (today's game and next games)
- R5. Data source: MLB schedule API `hydrate=broadcasts` (already available, no extra API call)

**Weather Panel**
- R6. Display current weather conditions in the game header: temperature, conditions (clear/cloudy/rain), wind speed and direction
- R7. For Wrigley Field: enhanced wind analysis interpreting wind direction relative to the field orientation (e.g., "blowing out to left field", "blowing in from the lake") using the venue's azimuth angle
- R8. For other outdoor venues: basic temperature + conditions + wind speed
- R9. Skip weather display entirely for fully domed venues
- R10. Data source: Open-Meteo API (free, no API key) using venue coordinates from MLB API

**Player Stats Panel**
- R11. Click a player's name in the lineup column to expand a stats panel below their row
- R12. Default view shows essential line: season stats (AVG/OBP/SLG/HR/RBI for hitters; ERA/WHIP/K/IP for pitchers) + career vs today's opposing pitcher + career vs opposing team
- R13. "More" toggle expands to show: monthly splits, last 7 games, home/away splits
- R14. Panel closes when clicking the name again or clicking a different player
- R15. Data fetched on-demand when the panel opens (not pre-loaded for all players)

**Game Finder Cards**
- R16. Show broadcast availability icons on game finder cards (TV/radio indicator)

## Success Criteria

- User can see where to watch/listen before opening a scorecard
- Weather panel shows accurate conditions with Wrigley-specific wind interpretation
- Clicking any player name reveals meaningful matchup context within 1 second
- No extra API calls on initial page load for stats (fetched on-demand per player)
- All three panels feel like natural extensions of the existing dark editorial design

## Scope Boundaries

- **In scope:** Broadcasts, weather, player stats panels, Morning Lineup broadcast integration
- **Out of scope:** Player outlook / editorial content (requires manual writing), expected stats (xBA/xSLG from Baseball Savant — different API), player photos/headshots, weather alerts/rain delay predictions

## Key Decisions

- **Info panels over tooltips:** Gives richer data room to breathe, works on mobile, keeps diamond tooltips focused on play-by-play detail
- **Click player name (not diamond cell):** Keeps diamond click for tooltip toggle on mobile, player panel is a distinct interaction
- **Enhanced Wrigley wind, basic elsewhere:** Wrigley wind is genuinely actionable baseball information; weather at other parks is context, not strategy
- **Essential + expandable stats:** Season line + matchup data by default, monthly/recent/splits behind a toggle. Doesn't overwhelm casual fans, rewards deep dives.
- **On-demand stat fetching:** Avoids loading 18+ player stat bundles upfront. Fetches when the panel opens.

## Outstanding Questions

### Deferred to Planning
- [Affects R7][Needs research] Exact wind direction interpretation formula using Wrigley's azimuth angle (37 degrees) — how to translate compass degrees into "blowing out to left/center/right"
- [Affects R10][Technical] Open-Meteo API endpoint structure and rate limits
- [Affects R12][Technical] Which MLB stat type endpoints to call for each split (vsPlayer, vsTeam, byMonth, lastXGames) and how to batch them efficiently

## Next Steps

-> `/ce:plan` for structured implementation planning, or proceed directly to work
