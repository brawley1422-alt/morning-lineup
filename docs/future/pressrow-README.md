# The Press Row — Future Feature

Fake Twitter/X feed where all 90 Morning Lineup writer personas interact across team lines. Replies, quote tweets, arguments, hot takes — all driven by yesterday's real game results.

## Status: Shelved (2026-04-12)

Prototype built and working. LLM generates 20-25 interconnected tweets per day via Ollama/Anthropic. The local qwen model produces repetitive content — needs Anthropic or a bigger model to really shine with cross-team banter.

## What's here

- `pressrow.py` — complete section module, follows `sections/columnists.py` pattern
- Reads all 30 team configs to build a cast of 90 writers
- Generates tweets via Ollama (qwen3:8b) with Anthropic fallback
- Caches to `data/pressrow-{date}.json` (one file for all teams)
- Renders Twitter-like feed with avatars, handles, timestamps, metrics, reply threads, quote tweets

## To activate

1. Move `pressrow.py` back to `sections/`
2. Add `import sections.pressrow` to `build.py` (line ~25)
3. Add `pressrow_html = sections.pressrow.render(briefing)` after columnists render
4. Add `("pressrow", pressrow_html)` to `_visible_sections` (after "league", before "history")
5. Add TOC entry and `<section id="pressrow">` block to page envelope
6. Add Press Row CSS block to `style.css` (see plan file for full CSS)

## CSS needed

Saved in the plan at `~/.claude/plans/shimmering-wiggling-newell.md` — full CSS block for `.pressrow-feed`, `.pr-tweet`, `.pr-avatar`, `.pr-quoted`, `.pr-metrics`, etc.
