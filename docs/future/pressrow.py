"""The Press Row — fake Twitter/X social feed where all 90 Morning Lineup
writer personas interact across team lines.

Generates a shared feed of ~20 interconnected tweets (originals, replies,
quote tweets) from writers across all 30 teams, reacting to yesterday's
real game results. Cached once per day in data/pressrow-{YYYY-MM-DD}.json
so only the first team build triggers LLM generation.
"""
import json
import os
import re
import urllib.request
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _data_dir():
    return ROOT / "data"


def _teams_dir():
    return ROOT / "teams"


# ─── helpers ────────────────────────────────────────────────────────────────


def _make_handle(name):
    """'Tony Gedeski' → 'tony_gedeski'"""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _make_initials(name):
    """'Beatrice Bee Vittorini' → 'BV' (first + last)"""
    parts = re.sub(r"['\"]", "", name).split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return parts[0][0].upper() if parts else "?"


def _role_key(role_label):
    label = role_label.lower()
    if "straight" in label:
        return "straight_beat"
    if "optimist" in label:
        return "optimist"
    if "pessimist" in label:
        return "pessimist"
    return re.sub(r"[^a-z0-9_]+", "_", label).strip("_")


# ─── load all 30 teams' columnists ─────────────────────────────────────────


def _load_all_columnists():
    """Read every teams/*.json and return a list of dicts with writer +
    team metadata. Also returns a slug→colors map for avatar tinting."""
    writers = []
    team_colors = {}
    for cfg_path in sorted(_teams_dir().glob("*.json")):
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        slug = cfg_path.stem
        abbr = cfg.get("abbreviation", slug.upper()[:3])
        team_name = cfg.get("name", slug.title())
        team_id = cfg.get("id", 0)
        colors = cfg.get("colors", {})
        team_colors[slug] = colors

        for persona in cfg.get("columnists", []):
            role = _role_key(persona.get("role", ""))
            writers.append({
                "name": persona["name"],
                "handle": _make_handle(persona["name"]),
                "team_slug": slug,
                "team_name": team_name,
                "team_abbr": abbr,
                "team_id": team_id,
                "role": role,
                "initials": _make_initials(persona["name"]),
                "signature_phrase": persona.get("signature_phrase", ""),
                "color": colors.get("accent", "#888") if role == "pessimist"
                    else colors.get("primary", "#888") if role == "straight_beat"
                    else "#c9a24a",  # gold for optimist
            })
    return writers, team_colors


# ─── game digest ────────────────────────────────────────────────────────────


def _build_game_digest(briefing):
    """Format yesterday's full schedule into plain text for the LLM."""
    games = briefing.data.get("games_y", [])
    if not games:
        return "No MLB games were played yesterday (off-day across the league)."

    lines = []
    for g in games:
        status = g.get("status", {}).get("abstractGameState", "")
        if status != "Final":
            continue
        away_name = g["teams"]["away"]["team"].get("name", "?")
        home_name = g["teams"]["home"]["team"].get("name", "?")
        away_sc = g["teams"]["away"].get("score", 0)
        home_sc = g["teams"]["home"].get("score", 0)
        winner = away_name if away_sc > home_sc else home_name
        lines.append(f"- {away_name} {away_sc}, {home_name} {home_sc} (W: {winner})")

    if not lines:
        return "No final results from yesterday's games yet."
    return "\n".join(lines)


# ─── cast list ──────────────────────────────────────────────────────────────


def _build_cast_list(writers):
    lines = []
    for w in writers:
        lines.append(
            f"- {w['name']} (@{w['handle']}) {w['team_abbr']}, "
            f"{w['role'].replace('_',' ').title()}: \"{w['signature_phrase']}\""
        )
    return "\n".join(lines)


# ─── LLM prompt ─────────────────────────────────────────────────────────────


def _build_prompt(game_digest, cast_list):
    return f"""You are generating a fake Twitter/X social media feed for "The Press Row," a feature of The Morning Lineup, a daily MLB newspaper.

YESTERDAY'S GAME RESULTS:
{game_digest}

AVAILABLE WRITERS — pick 10-15 whose teams had notable games:
{cast_list}

Generate a JSON array of 18-25 tweets. Each tweet object must have:
- "id": sequential string "pr-001", "pr-002", etc.
- "author_name": exact name from the cast list above
- "type": one of "original", "reply", "quote"
- "text": the tweet text (max 280 characters, like real Twitter)
- "reply_to": id string of parent tweet (null if original or quote)
- "quote_of": id string of quoted tweet (null if original or reply)
- "timestamp": fake evening timestamp like "10:34 PM" or "11:12 PM"
- "metrics": {{"replies": N, "retweets": N, "likes": N}}

REQUIREMENTS:
- Beat writers (Straight Beat) are factual, dry, stat-driven. Short declarative sentences.
- Optimists find silver linings, see hope, are upbeat and charming.
- Pessimists doom-post, complain about management, predict collapse.
- Include INTERACTIONS: replies that argue, quote tweets that dunk or agree.
- Spicy takes get high engagement (100-500 likes). Factual posts get moderate (20-80).
- Pessimists and optimists from rival teams should argue with each other.
- At least 3 reply threads (an original tweet + 1-2 replies to it).
- At least 3 quote tweets referencing earlier tweets by id.
- Reference REAL scores and results from above. Use actual player names if known.
- Writers should use their signature phrases sparingly (at most once per writer).
- No slurs, no personal attacks on real players or families, no betting references.
- Writers never break character or reference being AI.
- Timestamps should progress chronologically from ~9:30 PM to ~12:15 AM.

Return ONLY the raw JSON array. No markdown fences, no commentary."""


# ─── LLM generation ─────────────────────────────────────────────────────────


def _strip_thinking(text):
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _try_ollama(prompt):
    try:
        body = json.dumps({
            "model": "qwen3:8b-q4_K_M",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.85, "num_predict": 4096},
        }).encode()
        req = urllib.request.Request(
            "http://localhost:11434/api/chat",
            data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=180) as r:
            resp = json.loads(r.read())
        text = _strip_thinking(resp.get("message", {}).get("content", "").strip())
        if text and len(text) >= 200:
            return text
    except Exception as e:
        print(f"  [pressrow] Ollama failed: {e}", flush=True)
    return ""


def _try_anthropic(prompt):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return ""
    try:
        body = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body, method="POST",
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read())
        text = resp["content"][0]["text"].strip()
        if text and len(text) >= 200:
            return text
    except Exception as e:
        print(f"  [pressrow] Anthropic failed: {e}", flush=True)
    return ""


# ─── parse & validate ───────────────────────────────────────────────────────


def _normalize_timestamp(raw):
    """Convert various timestamp formats to simple '10:34 PM' style."""
    # Already in the right format?
    if re.match(r"\d{1,2}:\d{2}\s*[AaPp][Mm]", raw):
        return raw.strip()
    # ISO format: 2023-10-05T21:30:00Z → 9:30 PM
    m = re.match(r"\d{4}-\d{2}-\d{2}T(\d{2}):(\d{2})", raw)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        suffix = "AM" if h < 12 else "PM"
        h12 = h % 12
        if h12 == 0:
            h12 = 12
        return f"{h12}:{mi:02d} {suffix}"
    return raw


def _extract_json(raw):
    """Try to extract a JSON array from raw LLM output, handling markdown
    fences and wrapper objects."""
    raw = raw.strip()
    # strip markdown fences
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if m:
        raw = m.group(1).strip()
    # try direct parse
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
        # some models wrap in {"tweets": [...]}
        if isinstance(parsed, dict):
            for key in ("tweets", "data", "feed", "results"):
                if isinstance(parsed.get(key), list):
                    return parsed[key]
        return []
    except json.JSONDecodeError:
        return []


def _parse_and_validate(raw_text, writers_by_name):
    """Parse LLM JSON output into validated tweet list."""
    tweets = _extract_json(raw_text)
    if not tweets:
        return []

    valid = []
    valid_ids = set()

    for i, tw in enumerate(tweets):
        if not isinstance(tw, dict):
            continue
        new_id = f"pr-{i+1:03d}"

        author_name = tw.get("author_name", "")
        writer = writers_by_name.get(author_name)
        if not writer:
            # try fuzzy match on last name
            for name, w in writers_by_name.items():
                if name.split()[-1].lower() == author_name.split()[-1].lower():
                    writer = w
                    break
        if not writer:
            continue  # skip tweets from unknown writers

        text = str(tw.get("text", ""))[:280]
        if not text:
            continue

        metrics = tw.get("metrics", {})
        if not isinstance(metrics, dict):
            metrics = {}

        # Infer type from fields if LLM didn't set it correctly
        raw_reply = tw.get("reply_to")
        raw_quote = tw.get("quote_of")
        tweet_type = tw.get("type", "original")
        if tweet_type not in ("original", "reply", "quote"):
            tweet_type = "original"
        # Override type based on actual references
        if raw_reply and not raw_quote:
            tweet_type = "reply"
        elif raw_quote and not raw_reply:
            tweet_type = "quote"

        # Normalize timestamp — handle ISO format from some models
        raw_ts = str(tw.get("timestamp", "10:00 PM"))
        ts = _normalize_timestamp(raw_ts)

        valid_tweet = {
            "id": new_id,
            "old_id": tw.get("id", ""),  # for remapping references
            "author": {
                "name": writer["name"],
                "handle": writer["handle"],
                "team_slug": writer["team_slug"],
                "team_name": writer["team_name"],
                "team_abbr": writer["team_abbr"],
                "team_id": writer["team_id"],
                "role": writer["role"],
                "initials": writer["initials"],
                "color": writer["color"],
            },
            "type": tweet_type,
            "text": text,
            "reply_to": raw_reply,
            "quote_of": raw_quote,
            "timestamp": ts,
            "metrics": {
                "replies": int(metrics.get("replies", 0)),
                "retweets": int(metrics.get("retweets", 0)),
                "likes": int(metrics.get("likes", 0)),
            },
        }
        valid.append(valid_tweet)
        valid_ids.add(new_id)

    # Build old_id → new_id map for remapping references
    id_map = {}
    for tw in valid:
        if tw["old_id"]:
            id_map[tw["old_id"]] = tw["id"]

    # Remap and validate references
    for tw in valid:
        if tw["reply_to"]:
            tw["reply_to"] = id_map.get(tw["reply_to"])
            if tw["reply_to"] not in valid_ids:
                tw["reply_to"] = None
                tw["type"] = "original"
        if tw["quote_of"]:
            tw["quote_of"] = id_map.get(tw["quote_of"])
            if tw["quote_of"] not in valid_ids:
                tw["quote_of"] = None
                tw["type"] = "original"
        del tw["old_id"]

    return valid


# ─── cache ──────────────────────────────────────────────────────────────────


def _load_cache(today_iso):
    cache_path = _data_dir() / f"pressrow-{today_iso}.json"
    if cache_path.exists():
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("tweets"):
                return data
        except Exception:
            pass
    return None


def _save_cache(today_iso, data):
    data_dir = _data_dir()
    data_dir.mkdir(exist_ok=True)
    cache_path = data_dir / f"pressrow-{today_iso}.json"
    cache_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ─── generate feed ──────────────────────────────────────────────────────────


def generate_feed(briefing):
    """Generate or load cached Press Row feed. Returns list of tweet dicts."""
    today_iso = briefing.data["today"].isoformat()

    cached = _load_cache(today_iso)
    if cached:
        print("  [pressrow] using cached feed", flush=True)
        return cached["tweets"]

    writers, _ = _load_all_columnists()
    writers_by_name = {w["name"]: w for w in writers}

    game_digest = _build_game_digest(briefing)
    cast_list = _build_cast_list(writers)
    prompt = _build_prompt(game_digest, cast_list)

    print("  [pressrow] generating feed...", flush=True)
    raw = _try_ollama(prompt)
    if not raw:
        print("    Ollama failed, trying Anthropic...", flush=True)
        raw = _try_anthropic(prompt)

    if not raw:
        print("    ✗ both providers failed for Press Row", flush=True)
        return []

    tweets = _parse_and_validate(raw, writers_by_name)
    if not tweets:
        print(f"    ✗ failed to parse tweet JSON (raw len={len(raw)}, first 200: {raw[:200]})", flush=True)
        return []

    print(f"    ✓ got {len(tweets)} tweets", flush=True)
    _save_cache(today_iso, {"generated": today_iso, "tweets": tweets})
    return tweets


# ─── render HTML ────────────────────────────────────────────────────────────


_REPLY_SVG = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>'
_RT_SVG = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>'
_HEART_SVG = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>'


def _render_quoted(tweet, tweets_by_id):
    """Render an embedded quote tweet."""
    quoted = tweets_by_id.get(tweet.get("quote_of"))
    if not quoted:
        return ""
    a = quoted["author"]
    return (
        f'<div class="pr-quoted">'
        f'<div class="pr-meta">'
        f'<span class="pr-name">{escape(a["name"])}</span>'
        f'<span class="pr-handle">@{escape(a["handle"])}</span>'
        f'<span class="pr-team">{escape(a["team_abbr"])}</span>'
        f'</div>'
        f'<div class="pr-text">{escape(quoted["text"])}</div>'
        f'</div>'
    )


def _render_tweet(tweet, tweets_by_id, home_slug):
    """Render a single tweet article."""
    a = tweet["author"]
    is_home = a["team_slug"] == home_slug
    is_reply = tweet["type"] == "reply" and tweet.get("reply_to")

    classes = ["pr-tweet"]
    if is_home:
        classes.append("pr-home")
    if is_reply:
        classes.append("pr-reply")

    # Reply-to context line
    reply_ctx = ""
    if is_reply:
        parent = tweets_by_id.get(tweet["reply_to"])
        if parent:
            reply_ctx = (
                f'<div class="pr-replying">'
                f'Replying to <span class="pr-handle">@{escape(parent["author"]["handle"])}</span>'
                f'</div>'
            )

    # Quote tweet embed
    quote_html = ""
    if tweet["type"] == "quote" and tweet.get("quote_of"):
        quote_html = _render_quoted(tweet, tweets_by_id)

    m = tweet["metrics"]

    return (
        f'<article class="{" ".join(classes)}" data-id="{escape(tweet["id"])}" '
        f'data-role="{escape(a["role"])}" data-team="{escape(a["team_slug"])}">'
        f'<div class="pr-avatar" style="background:{a["color"]}">{escape(a["initials"])}</div>'
        f'<div class="pr-body">'
        f'{reply_ctx}'
        f'<div class="pr-meta">'
        f'<span class="pr-name">{escape(a["name"])}</span>'
        f'<span class="pr-handle">@{escape(a["handle"])}</span>'
        f'<span class="pr-team">{escape(a["team_abbr"])}</span>'
        f'<span class="pr-dot">&middot;</span>'
        f'<span class="pr-time">{escape(tweet["timestamp"])}</span>'
        f'</div>'
        f'<div class="pr-text">{escape(tweet["text"])}</div>'
        f'{quote_html}'
        f'<div class="pr-metrics">'
        f'<span class="pr-metric">{_REPLY_SVG} {m["replies"]}</span>'
        f'<span class="pr-metric pr-rt">{_RT_SVG} {m["retweets"]}</span>'
        f'<span class="pr-metric pr-like">{_HEART_SVG} {m["likes"]}</span>'
        f'</div>'
        f'</div>'
        f'</article>'
    )


def render(briefing):
    """Entry point — returns inner HTML for the Press Row section, or ''."""
    tweets = generate_feed(briefing)
    if not tweets:
        return ""

    home_slug = briefing.config.get("slug", "")
    if not home_slug:
        home_slug = briefing.config.get("id_slug") or briefing.config.get(
            "abbreviation", "unknown").lower()

    tweets_by_id = {tw["id"]: tw for tw in tweets}

    cards = []
    for tw in tweets:
        cards.append(_render_tweet(tw, tweets_by_id, home_slug))

    return (
        f'<div class="pressrow-feed">'
        f'{"".join(cards)}'
        f'</div>'
    )
