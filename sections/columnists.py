"""Columnists section — three persona-driven columns at the top of every
team page. Replaces the old single editorial lede.

Each team's `teams/{slug}.json` config carries a `columnists` array with
three persona dicts (name, role, backstory, signature_phrase, voice_sample).
For each persona we generate a ~300-500 word column using Ollama. If
MORNING_LINEUP_SKIP_COLUMN_GEN is set in the environment (pass 1 of the
daily build), generation is skipped entirely and columns render as
"off today" placeholders — pass 2 fills them in afterwards.

All three writers for a given team share a single cache file at
data/columnists-{slug}-{YYYY-MM-DD}.json with shape:
    {
      "straight_beat": {"name": "...", "column": "..."},
      "optimist":      {"name": "...", "column": "..."},
      "pessimist":     {"name": "...", "column": "..."}
    }
An empty "column" string means generation failed for that writer; the
UI shows a "{Name} is off today." placeholder card so the layout stays
stable and the failure is visible.
"""
import json
import os
import re
import urllib.request
from html import escape
from pathlib import Path


ROLE_KEYS = ("straight_beat", "optimist", "pessimist")

# Minimum acceptable column length in characters. Shorter outputs are
# treated as generation failures (model hiccup, empty response, etc).
MIN_COLUMN_CHARS = 250


def _data_dir():
    return Path(__file__).resolve().parent.parent / "data"


def _role_key(persona):
    """Map a persona's role label back to a canonical key."""
    label = (persona.get("role") or "").lower()
    if "straight" in label:
        return "straight_beat"
    if "optimist" in label:
        return "optimist"
    if "pessimist" in label:
        return "pessimist"
    # Defensive fallback: slugify the role
    return re.sub(r"[^a-z0-9_]+", "_", label).strip("_")


def _load_cache(slug, today_iso):
    cache_path = _data_dir() / f"columnists-{slug}-{today_iso}.json"
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache(slug, today_iso, cache):
    data_dir = _data_dir()
    data_dir.mkdir(exist_ok=True)
    cache_path = data_dir / f"columnists-{slug}-{today_iso}.json"
    cache_path.write_text(
        json.dumps(cache, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _build_day_context(briefing):
    """Short plain-text summary of the day's facts, shared across all
    three writers. Intentionally sparse — the point is to give each
    persona the same raw material and let their voice shape it."""
    data = briefing.data
    team_name = briefing.team_name
    div_name = briefing.div_name

    parts = []
    cg = data.get("cubs_game")  # key is legacy "cubs_*" across the codebase
    if cg:
        away = cg["teams"]["away"]["team"].get("name", "?")
        home = cg["teams"]["home"]["team"].get("name", "?")
        asc = cg["teams"]["away"].get("score", 0)
        hsc = cg["teams"]["home"].get("score", 0)
        parts.append(f"Yesterday's {team_name} game: {away} {asc}, {home} {hsc}")
    else:
        parts.append(f"No {team_name} game yesterday.")

    cr = data.get("cubs_rec")
    if cr:
        parts.append(
            f"{team_name} record: {cr['wins']}-{cr['losses']}, "
            f"{cr.get('gamesBack', '?')} GB in {div_name}"
        )

    return "\n".join(parts)


def _build_prompt(briefing, persona, day_context):
    name = persona["name"]
    role = persona["role"]
    backstory = persona["backstory"]
    phrase = persona["signature_phrase"]
    sample = persona["voice_sample"]
    team_name = briefing.team_name

    return f"""You are {name}, a columnist for "The Morning Lineup," a daily newspaper about the {team_name}.

YOUR IDENTITY
Name: {name}
Role: {role}
Backstory: {backstory}
A phrase you overuse: "{phrase}"
A sentence in your voice: "{sample}"

TODAY'S FACTS
{day_context}

YOUR TASK
Write your column for today, 300 to 500 words, in your voice. Real column, not a tagline. Go long if your persona would. Pick the angle your persona would naturally obsess over — don't feel obligated to cover the obvious headline if your persona would be fixated on something else. Use your signature phrase at most once, only if it lands naturally. Paragraphs allowed; use double line breaks between them.

RULES (non-negotiable)
- No slurs. No personal attacks on real players or their families.
- No betting advice, no gambling references framed as advice.
- No commentary on off-field legal matters, arrests, or personal lives.
- The negativity (for the Pessimist) or optimism (for the Optimist) is about the team, the front office, and the game — NOT about humans as humans.
- Do not break the fourth wall. You are {name}, not an AI. Do not say you are writing a column or refer to the exercise.
- Do not include your byline, a title, or a headline. Write ONLY the column text.

YOUR VOICE, ONE MORE TIME: {role}. {name}. "{phrase}"

Begin."""


def _strip_thinking(text):
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _try_ollama(prompt):
    try:
        body = json.dumps({
            "model": "qwen3:8b-q4_K_M",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.8, "num_predict": 768},
        }).encode()
        req = urllib.request.Request(
            "http://localhost:11434/api/chat",
            data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.loads(r.read())
        text = _strip_thinking(resp.get("message", {}).get("content", "").strip())
        if text and len(text) >= MIN_COLUMN_CHARS:
            return text
    except Exception as e:
        print(f"  Ollama column failed: {e}", flush=True)
    return ""


def generate_column(briefing, persona, cache):
    """Return the column text for a given persona, using the shared cache
    dict. Tries Ollama, returns '' on failure. Mutates `cache` in place so
    the caller can save the whole file once.

    Respects MORNING_LINEUP_SKIP_COLUMN_GEN — when set, only the cache is
    consulted and no Ollama calls are made. Used by pass 1 of daily-build
    so the games-pass deploys fast without touching the LLM."""
    role_key = _role_key(persona)
    cached = cache.get(role_key, {})
    if cached.get("column"):
        return cached["column"]

    if os.environ.get("MORNING_LINEUP_SKIP_COLUMN_GEN"):
        cache[role_key] = {"name": persona["name"], "column": ""}
        return ""

    day_context = _build_day_context(briefing)
    prompt = _build_prompt(briefing, persona, day_context)

    print(f"  generating column for {persona['name']} ({role_key})...", flush=True)
    text = _try_ollama(prompt)
    if text:
        print(f"    ✓ got {len(text)} chars", flush=True)
    else:
        print(f"    ✗ Ollama failed for {persona['name']}", flush=True)

    cache[role_key] = {
        "name": persona["name"],
        "column": text,  # may be empty
    }
    return text


def _render_column_card(persona, column_text):
    name = escape(persona["name"])
    role = escape(persona["role"])
    role_key = _role_key(persona)

    if column_text:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", column_text) if p.strip()]
        body_html = "".join(f"<p>{escape(p)}</p>" for p in paragraphs)
    else:
        body_html = (
            f"<p class=\"column-off\"><em>{name} is off today.</em></p>"
        )

    return (
        f'<details class="column" data-role="{escape(role_key)}">'
        f'<summary class="column-byline">'
        f'<span class="column-name">{name}</span>'
        f'<span class="column-role">{role}</span>'
        f'<span class="column-toggle" aria-hidden="true">Read</span>'
        f'</summary>'
        f'<div class="column-body">{body_html}</div>'
        f'</details>'
    )


_SHUFFLE_SCRIPT = """
(function(){
  var grid = document.currentScript && document.currentScript.previousElementSibling;
  if (!grid || !grid.classList || !grid.classList.contains('columnists-grid')) return;
  var kids = Array.prototype.slice.call(grid.children);
  for (var i = kids.length - 1; i > 0; i--) {
    var j = Math.floor(Math.random() * (i + 1));
    var tmp = kids[i]; kids[i] = kids[j]; kids[j] = tmp;
  }
  kids.forEach(function(k){ grid.appendChild(k); });
})();
""".strip()


def render(briefing):
    """Build the Columnists section HTML block for a team. Called from
    build.py, slotted in above the numbered sections."""
    personas = briefing.config.get("columnists") or []
    if len(personas) < 3:
        return ""  # no personas configured — omit section entirely

    slug = briefing.config["slug"] if "slug" in briefing.config else None
    # slug fallback: build.py uses different keys in older code; try a couple
    if not slug:
        slug = briefing.config.get("id_slug") or briefing.config.get("abbreviation", "unknown").lower()
    today_iso = briefing.data["today"].isoformat()

    cache = _load_cache(slug, today_iso)

    cards = []
    for persona in personas:
        text = generate_column(briefing, persona, cache)
        cards.append(_render_column_card(persona, text))

    _save_cache(slug, today_iso, cache)

    return (
        f'<section id="columnists" class="columnists">'
        f'<div class="columnists-head">'
        f'<span class="section-kicker">The Columnists</span>'
        f'<span class="section-dek">Three takes on today</span>'
        f'</div>'
        f'<div class="columnists-grid" data-shuffle="true">'
        f'{"".join(cards)}'
        f'</div>'
        f'<script>{_SHUFFLE_SCRIPT}</script>'
        f'</section>'
    )
