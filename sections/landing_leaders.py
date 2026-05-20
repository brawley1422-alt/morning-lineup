"""Landing page — League Leaders section.

Renders top-5 leaders for each of 10 stat categories (5 hitting + 5 pitching)
as compact agate-style lists. Sits below the standings grid on index.html.

Fetches independently from build.py's per-team load_all() because the landing
page has no team context. Uses urllib (stdlib only, no pip deps), same as the
rest of the project.
"""
import json
import urllib.parse
import urllib.request
from datetime import date
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

API = "https://statsapi.mlb.com/api/v1"
LOGO_BASE = "https://www.mlbstatic.com/team-logos/team-cap-on-dark/"
CT = ZoneInfo("America/Chicago")

# (request_key, response_key, label) — API normalizes some keys in the response
# (e.g. "strikeOuts" → "strikeouts", "whip" → "walksAndHitsPerInningPitched"),
# so we match on the response form.
HIT_CATS = [
    ("battingAverage", "battingAverage", "AVG"),
    ("homeRuns", "homeRuns", "HR"),
    ("runsBattedIn", "runsBattedIn", "RBI"),
    ("stolenBases", "stolenBases", "SB"),
    ("onBasePlusSlugging", "onBasePlusSlugging", "OPS"),
]
PIT_CATS = [
    ("earnedRunAverage", "earnedRunAverage", "ERA"),
    ("strikeOuts", "strikeouts", "K"),
    ("whip", "walksAndHitsPerInningPitched", "WHIP"),
    ("saves", "saves", "SV"),
    ("wins", "wins", "W"),
    ("inningsPitched", "inningsPitched", "IP"),
    ("holds", "holds", "HLD"),
]


def _fetch(path, **params):
    qs = urllib.parse.urlencode(params)
    url = f"{API}{path}?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": "morning-lineup/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def _team_abbr_map(teams_dir):
    out = {}
    for cfg in sorted(teams_dir.glob("*.json")):
        d = json.loads(cfg.read_text())
        out[d["id"]] = d.get("abbreviation", "")
    return out


def _short_name(full_name):
    parts = full_name.strip().split()
    if len(parts) < 2:
        return full_name
    return f"{parts[0][0]}. {parts[-1]}"


def _render_cat(label, leaders, abbr_map, slug_map):
    rows = []
    for i, L in enumerate(leaders[:5], start=1):
        tid = L["team"]["id"]
        ab = abbr_map.get(tid, "")
        nm = _short_name(L["person"]["fullName"])
        val = L["value"]
        slug = slug_map.get(tid)
        href = f"{slug}/" if slug else "#"
        rows.append(
            f'<li><span class="rk">{i}</span>'
            f'<img class="lg" src="{LOGO_BASE}{tid}.svg" alt="" loading="lazy">'
            f'<a class="nm" href="{escape(href)}">{escape(nm)}<span class="ab">{escape(ab)}</span></a>'
            f'<span class="v">{escape(str(val))}</span></li>'
        )
    return (
        f'<div class="lcat"><div class="lcat-hd">'
        f'<span class="l">{escape(label)}</span><span>Top 5</span></div>'
        f'<ol>{"".join(rows)}</ol></div>'
    )


def render(teams_dir):
    """Return the full <section> HTML. teams_dir is the Path to morning-lineup/teams."""
    abbr_map = _team_abbr_map(teams_dir)
    slug_map = {}
    for cfg in sorted(teams_dir.glob("*.json")):
        d = json.loads(cfg.read_text())
        slug_map[d["id"]] = cfg.stem

    season = date.today().year
    try:
        hit = _fetch(
            "/stats/leaders", sportId=1, season=season, limit=5, statGroup="hitting",
            leaderCategories=",".join(req for req, _, _ in HIT_CATS),
        )
        pit = _fetch(
            "/stats/leaders", sportId=1, season=season, limit=5, statGroup="pitching",
            leaderCategories=",".join(req for req, _, _ in PIT_CATS),
        )
    except Exception as e:
        print(f"[landing_leaders] fetch failed: {e}")
        return ""

    def _band(label, data, cats):
        lkp = {c["leaderCategory"]: c for c in data.get("leagueLeaders", [])}
        tiles = []
        for _, resp_key, cat_label in cats:
            c = lkp.get(resp_key)
            if not c or not c.get("leaders"):
                continue
            tiles.append(_render_cat(cat_label, c["leaders"], abbr_map, slug_map))
        return (
            f'<div class="leaders-band">'
            f'<p class="leaders-band-label">{label}</p>'
            f'<div class="leaders-row" style="--cols:{len(tiles)}">{"".join(tiles)}</div></div>'
        )

    today_str = date.today().strftime("%a · %b %-d").upper()
    return (
        f'<section class="leaders" id="leaders" aria-label="League Leaders">'
        f'<div class="leaders-head">'
        f'<span class="num">§</span>'
        f'<h2 class="h">League Leaders</h2>'
        f'<span class="tag">Through {today_str}</span>'
        f'</div>'
        f'{_band("At the Plate", hit, HIT_CATS)}'
        f'{_band("On the Mound", pit, PIT_CATS)}'
        f'</section>'
    )
