"""Landing page — Wild Card Race board (both leagues).

Server-side render injected into index.html via __WILDCARD_HTML__. Fetches
standings independently (stdlib urllib) since the landing page has no team
context — same approach as landing_leaders.py. Each league shows its three
wild card spots split from the chase by the Playoff Line: cushion above (+),
deficit below. Every row links to that team's briefing.
"""
import json
import urllib.parse
import urllib.request
from datetime import date
from html import escape

API = "https://statsapi.mlb.com/api/v1"
LOGO_BASE = "https://www.mlbstatic.com/team-logos/team-cap-on-dark/"
LEAGUES = [(103, "American League"), (104, "National League")]


def _fetch(path, **params):
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{API}{path}?{qs}",
                                 headers={"User-Agent": "morning-lineup/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def _maps(teams_dir):
    abbr, slug = {}, {}
    for cfg in sorted(teams_dir.glob("*.json")):
        d = json.loads(cfg.read_text())
        abbr[d["id"]] = d.get("abbreviation", "")
        slug[d["id"]] = cfg.stem
    return abbr, slug


def _fmt_gb(x):
    if x == int(x):
        return str(int(x))
    return f"{x:g}"


def _gb(ahead, behind):
    return ((ahead["wins"] - behind["wins"]) + (behind["losses"] - ahead["losses"])) / 2.0


def _pool_for_league(records, league_id):
    teams = []
    for rec in records:
        if rec["league"]["id"] != league_id:
            continue
        for tr in rec["teamRecords"]:
            try:
                pct = float(tr.get("winningPercentage", "0") or 0)
            except ValueError:
                pct = 0.0
            teams.append({
                "id": tr["team"]["id"],
                "wins": tr.get("wins", 0),
                "losses": tr.get("losses", 0),
                "pct_f": pct,
                "leader": bool(tr.get("divisionLeader")),
                "streak": tr.get("streak", {}).get("streakCode", ""),
            })
    return sorted([t for t in teams if not t["leader"]],
                  key=lambda t: (-t["pct_f"], -t["wins"], t["losses"]))


def _row(t, abbr, slug):
    tid = t["id"]
    href = f'{slug.get(tid, "")}/'
    if t["in_wc"]:
        marker = f'<span class="wcb">WC{t["rank"]}</span>'
        gb = '<span class="wgb pos">+' + _fmt_gb(t["gap"]) + '</span>'
        cls = "wc-row in"
    else:
        marker = f'<span class="wrk">{t["rank"]}</span>'
        gb = '<span class="wgb">' + _fmt_gb(t["gap"]) + '</span>'
        cls = "wc-row"
    s = t["streak"][:1]
    scls = "hot" if s == "W" else ("cold" if s == "L" else "")
    streak = f'<span class="wstk {scls}">{escape(t["streak"])}</span>' if t["streak"] else '<span class="wstk"></span>'
    return (f'<a class="{cls}" href="{escape(href)}">'
            f'{marker}'
            f'<img class="wlg" src="{LOGO_BASE}{tid}.svg" alt="" loading="lazy">'
            f'<span class="wnm">{escape(abbr.get(tid, ""))}</span>'
            f'<span class="wrec">{t["wins"]}-{t["losses"]}</span>'
            f'{gb}{streak}</a>')


def _board(league_id, name, records, abbr, slug):
    pool = _pool_for_league(records, league_id)
    if len(pool) < 4:
        return ""
    cut, first_out = pool[2], pool[3]
    for i, t in enumerate(pool):
        t["rank"] = i + 1
        t["in_wc"] = t["rank"] <= 3
        t["gap"] = _gb(t, first_out) if t["in_wc"] else _gb(cut, t)

    rows = [_row(t, abbr, slug) for t in pool[:3]]
    rows.append('<div class="wc-line"><span>Playoff Line</span></div>')
    chase = [t for t in pool[3:] if t["gap"] <= 6.0][:4]
    if len(chase) < 3:
        chase = pool[3:6]
    rows += [_row(t, abbr, slug) for t in chase]

    return (f'<div class="wc-board">'
            f'<p class="wc-board-label">{escape(name)}</p>'
            f'<div class="wc-list">{"".join(rows)}</div></div>')


def render(teams_dir):
    """Return the full <section> HTML. teams_dir is the Path to morning-lineup/teams."""
    abbr, slug = _maps(teams_dir)
    season = date.today().year
    try:
        stand = _fetch("/standings", leagueId="103,104", season=season,
                       standingsTypes="regularSeason")
    except Exception as e:
        print(f"[landing_wildcard] fetch failed: {e}")
        return ""
    records = stand.get("records", [])
    boards = "".join(_board(lid, name, records, abbr, slug) for lid, name in LEAGUES)
    if not boards.strip():
        return ""
    return (f'<section class="wcrace" id="wcrace" aria-label="Wild Card Race">'
            f'<div class="wcrace-head">'
            f'<span class="num">§</span>'
            f'<h2 class="h">Wild Card Race</h2>'
            f'<span class="tag">The Playoff Line</span>'
            f'</div>'
            f'<div class="wcrace-cols">{boards}</div>'
            f'</section>')
