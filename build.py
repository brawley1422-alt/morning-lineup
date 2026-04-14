#!/usr/bin/env python3
"""
build.py — generate a daily MLB briefing page with real data.
Supports any team via --team flag (default: cubs).
Run: python3 build.py --team cubs
"""
import json
import sys
import urllib.request
import urllib.parse
from dataclasses import dataclass, field
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
from html import escape

import sections.around_league
import sections.columnists
import sections.division
import sections.farm
import sections.headline
import sections.history
import sections.pressbox
import sections.scouting
import sections.slate
import sections.stretch
try:
    from zoneinfo import ZoneInfo
    CT = ZoneInfo("America/Chicago")
except (ImportError, KeyError):
    CT = timezone(timedelta(hours=-5))

# ─── team config ────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent

# Build ID stamped into sw.js on every build to force service-worker cache
# rotation. Any change to CACHE name triggers SW activate → old caches deleted.
BUILD_ID = datetime.now(CT).strftime("%Y%m%d%H%M")

def load_team_config(team_slug="cubs"):
    cfg_path = ROOT / "teams" / f"{team_slug}.json"
    if not cfg_path.exists():
        print(f"ERROR: team config not found: {cfg_path}", file=sys.stderr)
        sys.exit(1)
    cfg = json.loads(cfg_path.read_text())
    cfg["slug"] = team_slug
    return cfg

# Parse --team argument
_team_slug = "cubs"
for i, a in enumerate(sys.argv):
    if a == "--team" and i + 1 < len(sys.argv):
        _team_slug = sys.argv[i + 1]

CFG = load_team_config(_team_slug)
TEAM_ID = CFG["id"]
TEAM_NAME = CFG["name"]
AFFILIATES = CFG["affiliates"]
DIV_ID = CFG["division_id"]
DIV_NAME = CFG["division_name"]

API = "https://statsapi.mlb.com/api/v1"
STYLE_FILE = ROOT / "style.css"
HISTORY_FILE = ROOT / "teams" / _team_slug / "history.json"
PROSPECTS_FILE = ROOT / "teams" / _team_slug / "prospects.json"
DATA_DIR = ROOT / "data"
OUT = ROOT / _team_slug / "index.html"

DIV_ORDER = [
    (201, "AL East"), (202, "AL Central"), (200, "AL West"),
    (204, "NL East"), (205, "NL Central"), (203, "NL West"),
]

# ─── fetch helpers ───────────────────────────────────────────────────────────

def fetch(path, **params):
    if params:
        url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    else:
        url = f"{API}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "morning-lineup/0.1"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def teams_map():
    d = fetch("/teams", sportId=1)
    return {t["id"]: t for t in d["teams"]}

def _ordinal(n):
    """Return ordinal suffix for a rank number (1st, 2nd, 3rd, etc.)."""
    try:
        n = int(n)
    except (ValueError, TypeError):
        return ""
    return {1: "st", 2: "nd", 3: "rd"}.get(n if n < 20 else n % 10, "th")

# ─── data gathering ──────────────────────────────────────────────────────────

def load_all():
    today = datetime.now(tz=CT).date()
    yest = today - timedelta(days=1)
    season = today.year
    tmap = teams_map()

    # Full yesterday schedule (all games, hydrated)
    sched_y = fetch(
        "/schedule",
        sportId=1, date=yest.isoformat(),
        hydrate="team,linescore,decisions,probablePitcher,venue",
    )
    games_y = sched_y["dates"][0]["games"] if sched_y.get("dates") else []

    # Today's schedule for slate
    sched_t = fetch(
        "/schedule",
        sportId=1, date=today.isoformat(),
        hydrate="team,probablePitcher,broadcasts",
    )
    games_t = sched_t["dates"][0]["games"] if sched_t.get("dates") else []

    # Standings
    stand = fetch("/standings", leagueId="103,104", season=season, standingsTypes="regularSeason")

    # Cubs record from standings
    cubs_rec = None
    for rec in stand["records"]:
        for tr in rec["teamRecords"]:
            if tr["team"]["id"] == TEAM_ID:
                cubs_rec = tr
                break

    # Next 7 days Cubs games → take next 3 (excluding today if already started)
    end = today + timedelta(days=8)
    sched_next = fetch(
        "/schedule",
        sportId=1, teamId=TEAM_ID,
        startDate=today.isoformat(), endDate=end.isoformat(),
        hydrate="team,probablePitcher,broadcasts,venue",
    )
    next_games = []
    for dd in sched_next.get("dates", []):
        for g in dd["games"]:
            next_games.append(g)
    next_games = next_games[:3]

    # Today's game enhancements: lineup, season series, opponent info
    today_lineup = {"home": [], "away": []}
    today_series = ""
    today_opp_info = ""
    if next_games:
        tg = next_games[0]
        tg_pk = tg["gamePk"]
        tg_home_id = tg["teams"]["home"]["team"]["id"]
        tg_away_id = tg["teams"]["away"]["team"]["id"]
        tg_opp_id = tg_away_id if tg_home_id == TEAM_ID else tg_home_id
        tg_is_home = tg_home_id == TEAM_ID

        # Batting order from live feed
        try:
            feed = json.loads(urllib.request.urlopen(
                urllib.request.Request(
                    f"https://statsapi.mlb.com/api/v1.1/game/{tg_pk}/feed/live",
                    headers={"User-Agent": "morning-lineup/0.1"}),
                timeout=15).read())
            feed_players = feed.get("gameData", {}).get("players", {})
            feed_box = feed.get("liveData", {}).get("boxscore", {})
            for side in ["home", "away"]:
                order = feed_box.get("teams", {}).get(side, {}).get("battingOrder", [])
                for pid in order[:9]:
                    p = feed_players.get(f"ID{pid}", {})
                    today_lineup[side].append({
                        "id": pid,
                        "name": p.get("fullName", "?"),
                        "pos": p.get("primaryPosition", {}).get("abbreviation", "?"),
                    })
        except Exception as e:
            print(f"  warning: lineup fetch failed: {e}", flush=True)

        # Season series: Cubs vs this opponent
        try:
            ss_url = fetch("/schedule", sportId=1, teamId=TEAM_ID, season=season,
                           startDate=f"{season}-03-20", endDate=today.isoformat(),
                           hydrate="team")
            sw, sl = 0, 0
            for dd in ss_url.get("dates", []):
                for g in dd.get("games", []):
                    if g.get("status", {}).get("abstractGameState") != "Final":
                        continue
                    ga, gh = g["teams"]["away"], g["teams"]["home"]
                    if ga["team"]["id"] != tg_opp_id and gh["team"]["id"] != tg_opp_id:
                        continue
                    cubs_home = gh["team"]["id"] == TEAM_ID
                    cs = gh.get("score", 0) if cubs_home else ga.get("score", 0)
                    os_ = ga.get("score", 0) if cubs_home else gh.get("score", 0)
                    if cs > os_:
                        sw += 1
                    else:
                        sl += 1
            if sw + sl > 0:
                today_series = f"{sw}-{sl}"
        except Exception as e:
            print(f"  warning: season series fetch failed: {e}", flush=True)

        # Opponent record from standings
        div_lookup = {did: dname for did, dname in DIV_ORDER}
        try:
            for rec in stand["records"]:
                for tr in rec["teamRecords"]:
                    if tr["team"]["id"] == tg_opp_id:
                        ow, ol = tr["wins"], tr["losses"]
                        rank = tr.get("divisionRank", "?")
                        div_id = rec.get("division", {}).get("id")
                        div_name = div_lookup.get(div_id, "")
                        streak = tr.get("streak", {}).get("streakCode", "")
                        today_opp_info = f"{ow}-{ol}, {rank}{_ordinal(rank)} {div_name}"
                        if streak:
                            today_opp_info += f" ({streak})"
                        break
        except Exception as e:
            print(f"  warning: opponent info failed: {e}", flush=True)

    # Cubs game yesterday → if no Final, walk back up to 7 days
    def find_cubs_final(start_day):
        for back in range(0, 8):
            day = start_day - timedelta(days=back)
            dd = fetch("/schedule", sportId=1, date=day.isoformat(), teamId=TEAM_ID,
                       hydrate="team,linescore,decisions,probablePitcher,venue")
            if not dd.get("dates"): continue
            for g in dd["dates"][0]["games"]:
                if g.get("status",{}).get("abstractGameState") == "Final" and "linescore" in g:
                    return g, day
        return None, None
    cubs_game, cubs_game_date = find_cubs_final(yest)
    boxscore = None
    plays = None
    if cubs_game:
        pk = cubs_game["gamePk"]
        try:
            boxscore = fetch(f"/game/{pk}/boxscore")
        except Exception as e:
            print(f"  warning: boxscore fetch failed: {e}", flush=True)
            boxscore = None
        try:
            # use v1.1 feed for playByPlay scoring plays
            req = urllib.request.Request(
                f"https://statsapi.mlb.com/api/v1.1/game/{pk}/feed/live",
                headers={"User-Agent": "morning-lineup/0.1"})
            with urllib.request.urlopen(req, timeout=15) as r:
                feed = json.loads(r.read())
            plays = feed.get("liveData", {}).get("plays", {})
        except Exception as e:
            print(f"  warning: play-by-play fetch failed: {e}", flush=True)
            plays = None

    # Cubs injuries (40-man, filter D-codes)
    roster = fetch(f"/teams/{TEAM_ID}/roster", rosterType="40Man")
    injuries = [p for p in roster.get("roster", [])
                if p.get("status", {}).get("code", "A") != "A"]

    # Hot Cubs bats: last 7 games, min 10 PA, sort by OPS
    cubs_hitters = fetch(
        f"/teams/{TEAM_ID}/roster",
        rosterType="active",
        hydrate=f"person(stats(type=lastXGames,limit=7,season={season},gameType=R))",
    )
    cubs_pitchers = fetch(
        f"/teams/{TEAM_ID}/roster",
        rosterType="active",
        hydrate=f"person(stats(type=lastXGames,limit=7,season={season},gameType=R,group=pitching))",
    )

    # Cubs season stats for team leaders
    cubs_season = fetch(
        f"/teams/{TEAM_ID}/roster",
        rosterType="active",
        hydrate=f"person(stats(type=season,season={season},gameType=R))",
    )

    # Leaders
    leaders_hit = fetch(
        "/stats/leaders", sportId=1, season=season, limit=1, statGroup="hitting",
        leaderCategories="battingAverage,homeRuns,runsBattedIn,stolenBases,onBasePlusSlugging",
    )
    leaders_pit = fetch(
        "/stats/leaders", sportId=1, season=season, limit=1, statGroup="pitching",
        leaderCategories="earnedRunAverage,strikeOuts,whip,saves,wins",
    )

    # Minor league affiliate results (yesterday)
    minors = []
    for aff in AFFILIATES:
        try:
            ms = fetch("/schedule", sportId=aff["sport_id"], teamId=aff["id"],
                        date=yest.isoformat(), hydrate="team,linescore,decisions")
            mg = ms["dates"][0]["games"][0] if ms.get("dates") and ms["dates"][0].get("games") else None
            box = None
            if mg and mg.get("status", {}).get("abstractGameState") == "Final":
                try:
                    box = fetch(f"/game/{mg['gamePk']}/boxscore")
                except Exception as e:
                    print(f"  warning: {aff['name']} boxscore failed: {e}", flush=True)
            minors.append({"aff": aff, "game": mg, "boxscore": box})
        except Exception as e:
            print(f"  warning: {aff['name']} schedule failed: {e}", flush=True)
            minors.append({"aff": aff, "game": None, "boxscore": None})

    # Prospect watchlist
    prospects = {}
    if PROSPECTS_FILE.exists():
        try:
            pdata = json.loads(PROSPECTS_FILE.read_text())
            prospects = {p["id"]: p for p in pdata}
        except Exception:
            prospects = {}

    # This Day in Cubs History
    history = []
    if HISTORY_FILE.exists():
        try:
            hdata = json.loads(HISTORY_FILE.read_text())
            key = today.strftime("%m-%d")
            history = hdata.get(key, [])
        except Exception:
            history = []

    # Transactions (last 7 days)
    transactions = []
    try:
        tx_start = (today - timedelta(days=7)).isoformat()
        tx_resp = fetch("/transactions", teamId=TEAM_ID,
                        startDate=tx_start, endDate=today.isoformat())
        skip_types = {"SFA"}  # minor league free agent signings
        for tx in tx_resp.get("transactions", []):
            tc = tx.get("typeCode", "")
            desc = tx.get("description", "")
            if tc in skip_types and "minor league" in desc.lower():
                continue
            transactions.append(tx)
    except Exception as e:
        print(f"  warning: transactions fetch failed: {e}", flush=True)

    # Scouting report: pitcher game logs for today's matchup
    scout_data = {}
    if next_games:
        tg = next_games[0]
        tg_home_id = tg["teams"]["home"]["team"]["id"]
        tg_is_home = tg_home_id == TEAM_ID
        cubs_side = "home" if tg_is_home else "away"
        opp_side = "away" if tg_is_home else "home"
        cubs_pp = tg["teams"][cubs_side].get("probablePitcher", {})
        opp_pp = tg["teams"][opp_side].get("probablePitcher", {})

        def _pitcher_scout(pp):
            if not pp or not pp.get("id"):
                return None
            pid = pp["id"]
            info = {"id": pid, "name": pp.get("fullName", "TBD"), "season": "", "log": []}
            # Season line
            info["season"] = fetch_pitcher_line(pid)
            # Game log (last 3 starts)
            try:
                gl = fetch(f"/people/{pid}/stats", stats="gameLog",
                           season=str(season), group="pitching")
                for s in gl.get("stats", []):
                    for sp in s.get("splits", [])[:3]:
                        st = sp.get("stat", {})
                        info["log"].append({
                            "date": sp.get("date", ""),
                            "opp": sp.get("opponent", {}).get("abbreviation",
                                   sp.get("opponent", {}).get("name", "?")),
                            "ip": st.get("inningsPitched", "?"),
                            "er": st.get("earnedRuns", "?"),
                            "k": st.get("strikeOuts", "?"),
                            "h": st.get("hits", "?"),
                            "bb": st.get("baseOnBalls", "?"),
                            "hr": st.get("homeRuns", "?"),
                        })
            except Exception as e:
                print(f"  warning: game log for {pid} failed: {e}", flush=True)
            return info

        cubs_sp = _pitcher_scout(cubs_pp)
        opp_sp = _pitcher_scout(opp_pp)
        if cubs_sp or opp_sp:
            scout_data = {"cubs_sp": cubs_sp, "opp_sp": opp_sp}

    return {
        "today": today, "yest": yest, "season": season,
        "tmap": tmap,
        "games_y": games_y, "games_t": games_t,
        "standings": stand, "cubs_rec": cubs_rec,
        "next_games": next_games,
        "today_lineup": today_lineup, "today_series": today_series,
        "today_opp_info": today_opp_info,
        "cubs_game": cubs_game, "cubs_game_date": cubs_game_date,
        "boxscore": boxscore, "plays": plays,
        "injuries": injuries,
        "cubs_hitters": cubs_hitters, "cubs_pitchers": cubs_pitchers,
        "cubs_season": cubs_season,
        "leaders_hit": leaders_hit, "leaders_pit": leaders_pit,
        "minors": minors, "prospects": prospects, "history": history,
        "transactions": transactions, "scout_data": scout_data,
    }

# ─── briefing dataclass ─────────────────────────────────────────────────────

@dataclass
class TeamBriefing:
    """Per-team build payload passed to section render functions.

    Holds the raw per-team config, the raw load_all() data dict, and a handful
    of direct config aliases that section files read frequently. No computed
    convenience fields — aliases only. Introduced in the sectioned-build
    refactor (see docs/plans/2026-04-10-001-refactor-sectioned-build-plan.md)
    so section files can avoid reaching into build.py module-level globals.
    """
    config: dict
    data: dict
    team_id: int
    team_name: str
    div_id: int
    div_name: str
    affiliates: list = field(default_factory=list)


def build_briefing(team_slug):
    """Construct a TeamBriefing for the given team slug.

    Caveat: load_all() reads TEAM_ID, AFFILIATES, and DIV_ID from module
    globals set at import time from --team. Calling build_briefing with a
    different slug than the one passed via --team will return mismatched data.
    Only safe to call with the same slug that initialized the module globals
    (i.e. the current _team_slug).
    """
    cfg = load_team_config(team_slug)
    data = load_all()
    return TeamBriefing(
        config=cfg,
        data=data,
        team_id=cfg["id"],
        team_name=cfg["name"],
        div_id=cfg["division_id"],
        div_name=cfg["division_name"],
        affiliates=cfg["affiliates"],
    )

# ─── rendering helpers ───────────────────────────────────────────────────────

def abbr(tmap, team_id):
    return tmap.get(team_id, {}).get("abbreviation", "???")

def team_name(tmap, team_id):
    return tmap.get(team_id, {}).get("teamName", "???")

def fmt_time_ct(iso_z):
    """Convert UTC ISO timestamp to Central Time display string."""
    dt = datetime.strptime(iso_z, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    ct = dt.astimezone(CT)
    return ct.strftime("%-I:%M") + " CT"

def fmt_date(d):
    return d.strftime("%a, %b ") + str(d.day) + d.strftime(", %Y")

# ─── section renderers ──────────────────────────────────────────────────────





DOME_VENUES = {12: "Dome", 32: "Retractable Roof", 680: "Retractable Roof",
               2889: "Retractable Roof", 14: "Retractable Roof",
               2394: "Retractable Roof", 19: "Retractable Roof"}

def fetch_pitcher_line(pid):
    """Fetch a pitcher's season stats. Returns formatted string or empty."""
    if not pid: return ""
    if "--fixture" in sys.argv:
        # Deterministic stub for golden snapshot tests — avoids the live MLB
        # season-stats fetch which updates daily as games are played.
        return "0.00 ERA &middot; 0-0 &middot; 0.0 IP &middot; 0 K &middot; 0.00 WHIP"
    try:
        data = fetch(f"/people/{pid}/stats", stats="season", season=str(datetime.now(tz=CT).date().year), group="pitching")
        for s in data.get("stats", []):
            for sp in s.get("splits", []):
                st = sp.get("stat", {})
                era = st.get("era", "-")
                w = st.get("wins", 0)
                l = st.get("losses", 0)
                ip = st.get("inningsPitched", "-")
                k = st.get("strikeOuts", "-")
                whip = st.get("whip", "-")
                return f'{era} ERA &middot; {w}-{l} &middot; {ip} IP &middot; {k} K &middot; {whip} WHIP'
    except Exception:
        pass
    return ""

def fetch_weather_for_venue(venue):
    """Fetch current weather for a venue. Returns (temp, cond, wind_str, wrigley_note) or None."""
    if not venue: return None
    vid = venue.get("id")
    if vid in DOME_VENUES: return None
    if "--fixture" in sys.argv:
        # Deterministic stub for golden snapshot tests — avoids the live
        # open-meteo API call and the MLB venues hydrate fetch above it.
        return (70, "Clear", "5 mph N", "")
    try:
        vdata = fetch(f"/venues/{vid}", hydrate="location")
        v = vdata.get("venues", [{}])[0]
        loc = v.get("location", {})
        coords = loc.get("defaultCoordinates", {})
        lat, lon = coords.get("latitude"), coords.get("longitude")
        if not lat or not lon: return None
        wx_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode,windspeed_10m,winddirection_10m&temperature_unit=fahrenheit&windspeed_unit=mph&timezone=America/Chicago"
        req = urllib.request.Request(wx_url, headers={"User-Agent": "morning-lineup/0.1"})
        with urllib.request.urlopen(req, timeout=10) as r:
            wx = json.loads(r.read())
        c = wx.get("current", {})
        temp = round(c.get("temperature_2m", 0))
        wind_spd = round(c.get("windspeed_10m", 0))
        wind_dir = c.get("winddirection_10m", 0)
        code = c.get("weathercode", 0)
        WMO = {0:"Clear",1:"Mostly Clear",2:"Partly Cloudy",3:"Overcast",
               45:"Foggy",51:"Light Drizzle",61:"Light Rain",63:"Rain",65:"Heavy Rain",
               80:"Showers",95:"Thunderstorm"}
        cond = WMO.get(code, "")
        dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
        compass = dirs[round(wind_dir / 22.5) % 16]
        wind_str = f"{wind_spd} mph {compass}" if wind_spd >= 3 else "Calm"
        # Wrigley wind interpretation
        wrigley_note = ""
        if vid == 17 and wind_spd >= 5:
            cf = (37 + 180) % 360
            diff = wind_dir - cf
            if diff > 180: diff -= 360
            if diff < -180: diff += 360
            ad = abs(diff)
            if ad <= 30: wrigley_note = "Blowing out to center"
            elif ad <= 60: wrigley_note = f"Blowing out to {'right' if diff > 0 else 'left'} field"
            elif ad >= 150: wrigley_note = "Blowing in"
            elif ad >= 120: wrigley_note = f"Blowing in from {'left' if diff > 0 else 'right'} field"
            else: wrigley_note = f"Crosswind {'L→R' if diff > 0 else 'R→L'}"
        return (temp, cond, wind_str, wrigley_note)
    except Exception:
        return None
















# ─── page assembly ──────────────────────────────────────────────────────────

_css_raw = STYLE_FILE.read_text(encoding="utf-8")
# Inject team colors into CSS variables
_colors = CFG["colors"]
_color_overrides = (
    f'--team-primary:{_colors["primary"]};--team-primary-hi:{_colors["primary_hi"]};'
    f'--team-accent:{_colors["accent"]};--team-accent-hi:{_colors["accent_hi"]};'
)
CSS = _css_raw.replace("--team-primary:#0E3386;--team-primary-hi:#2a56c4;", f"--team-primary:{_colors['primary']};--team-primary-hi:{_colors['primary_hi']};")
CSS = CSS.replace("--team-accent:#CC3433;--team-accent-hi:#e8544f;", f"--team-accent:{_colors['accent']};--team-accent-hi:{_colors['accent_hi']};")


# ─── team-cap SVG sprite ───────────────────────────────────────────────
# Fetch every team's team-cap-on-dark SVG once, combine into a single
# inline <svg> block with <symbol id="team-NNN"> entries, and inject at
# the top of <body>. Sections reference via <svg><use href="#team-NNN"/>
# which eliminates N per-page CDN requests and works offline (PWA).

import re as _re_sprite

def _fetch_cap_svg(team_id):
    """Return raw SVG text for a team's cap-on-dark logo, cached to disk."""
    cache_dir = DATA_DIR / ".sprite-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / f"cap-{team_id}.svg"
    if cached.exists():
        return cached.read_text(encoding="utf-8")
    url = f"https://www.mlbstatic.com/team-logos/team-cap-on-dark/{team_id}.svg"
    try:
        import urllib.request as _ur
        req = _ur.Request(url, headers={"User-Agent": "morning-lineup-build/1.0"})
        with _ur.urlopen(req, timeout=10) as r:
            body = r.read().decode("utf-8")
        cached.write_text(body, encoding="utf-8")
        return body
    except Exception as e:
        print(f"  warning: sprite fetch team {team_id} failed: {e}", flush=True)
        return ""


def _build_team_sprite():
    """Scan teams/*.json for team IDs, fetch each cap SVG, build one sprite."""
    teams_dir = ROOT / "teams"
    symbols = []
    seen = set()
    for cfg_file in sorted(teams_dir.glob("*.json")):
        try:
            with open(cfg_file, encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            continue
        tid = cfg.get("id")
        if not tid or tid in seen:
            continue
        seen.add(tid)
        raw = _fetch_cap_svg(tid)
        if not raw:
            continue
        m_vb = _re_sprite.search(r'viewBox="([^"]+)"', raw)
        vb = m_vb.group(1) if m_vb else "0 0 300 300"
        inner = _re_sprite.sub(r"^<svg[^>]*>", "", raw.strip(), count=1)
        inner = _re_sprite.sub(r"</svg>\s*$", "", inner, count=1)
        inner = _re_sprite.sub(r"<title>.*?</title>", "", inner, flags=_re_sprite.DOTALL)
        symbols.append(f'<symbol id="team-{tid}" viewBox="{vb}">{inner.strip()}</symbol>')
    if not symbols:
        return ""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" class="ml-sprite" '
        'aria-hidden="true" style="position:absolute;width:0;height:0;'
        'overflow:hidden">'
        + "".join(symbols)
        + "</svg>"
    )


TEAM_SPRITE = _build_team_sprite()


def page(briefing):
    data = briefing.data
    t = data["today"]; y = data["yest"]
    cr = data["cubs_rec"]
    cubs_record_str = ""
    if cr:
        # find division rank
        dr = cr.get("divisionRank", "")
        gb = cr.get("gamesBack", "-")
        cubs_record_str = f'{cr["wins"]}&ndash;{cr["losses"]}'
        if dr:
            suffix = {"1":"st","2":"nd","3":"rd"}.get(dr, "th")
            cubs_record_str += f' &middot; {dr}{suffix} {DIV_NAME}'

    headline_html, summary_tag = sections.headline.render(briefing)

    division_html = sections.division.render(briefing)
    slate_html = sections.slate.render(briefing)
    around_league_html, news_count = sections.around_league.render(briefing)

    # Minors
    minors_html, minors_tag = sections.farm.render(briefing)

    # New sections
    scout_html = sections.scouting.render(briefing)
    stretch_html = sections.stretch.render(briefing)
    pressbox_html = sections.pressbox.render(briefing)
    history_html = sections.history.render(briefing)

    # Editorial: three columnist personas per team (replaces the old lede)
    lede_html = sections.columnists.render(briefing)

    # Dynamic section numbering — skip sections with empty HTML (e.g. scout
    # on off-days). Each visible section gets the next zero-padded number.
    _visible_sections = [
        ("team", headline_html),
        ("scout", scout_html),
        ("pulse", stretch_html),
        ("pressbox", pressbox_html),
        ("farm", minors_html),
        ("today", slate_html),
        ("div", division_html),
        ("league", around_league_html),
        ("history", history_html),
    ]
    _num = {}
    _n = 1
    for _sid, _html in _visible_sections:
        if _html:
            _num[_sid] = f"{_n:02d}"
            _n += 1

    vol_no = (t - date(t.year, 1, 1)).days + 1
    if "--fixture" in sys.argv:
        # Deterministic timestamp for golden snapshot tests.
        filed = t.strftime("%m/%d/%y") + " 00:00 CT"
    else:
        filed = datetime.now(tz=CT).strftime("%m/%d/%y %H:%M CT")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline' https://esm.sh https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' https://*.supabase.co https://statsapi.mlb.com; frame-src 'self'; base-uri 'self'; form-action 'self'">
<meta name="theme-color" content="#0d0f14">
<link rel="manifest" href="manifest.json">
<link rel="apple-touch-icon" href="icons/icon-192.png">
<title>The Morning Lineup &mdash; {fmt_date(t)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,600;0,800;0,900;1,700&family=Oswald:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600;700&family=Lora:ital,wght@0,400;0,500;0,600;1,400;1,500&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body data-team="{_team_slug}">
{TEAM_SPRITE}

<header class="masthead">
  <div class="nav-btns">
    <a href="../home/" class="home-btn" aria-label="Your Lineup" title="Your Lineup">
      <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor"><path d="M12 22 L2 12 L2 2 L22 2 L22 12 Z"/></svg>
      <span>Your Lineup</span>
    </a>
    <a href="../" class="teams-btn" aria-label="All Teams" title="All Teams">
      <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M3 3h8v8H3zM13 3h8v8h-8zM3 13h8v8H3zM13 13h8v8h-8z"/></svg>
      <span>All Teams</span>
    </a>
  </div>
  <div class="kicker">
    <span>Vol. {t.year - 2023} &middot; <span class="vol">No. {vol_no:03d}</span></span>
    <span>{CFG['branding']['tagline']}</span>
    <span>Est. 2024</span>
  </div>
  <h1>
    <svg class="mast-logo" aria-label="{TEAM_NAME}" role="img" focusable="false"><use href="#team-{TEAM_ID}"/></svg>
    <span class="mast-text"><span class="the">The</span><span class="lineup">Morning <em style="font-style:italic">Lineup</em></span></span>
  </h1>
  <div class="dek">
    <span class="item"><span class="label">{t.strftime("%a")}</span><span class="val">{t.strftime("%b")} {t.day}, {t.year}</span></span>
    <span class="item"><span class="label">{TEAM_NAME}</span><span class="rec">{cubs_record_str}</span></span>
    <span class="item pill">Data: MLB Stats API</span>
  </div>
</header>
{lede_html}
<div class="wrap">
  <nav class="toc" aria-label="Sections">
    <div class="title">Sections</div>
    <ol>
      <li><a href="#team">The {TEAM_NAME}</a></li>
      {'<li><a href="#scout">Scouting Report</a></li>' if scout_html else ''}
      <li><a href="#pulse">The Stretch</a></li>
      <li><a href="#pressbox">The Pressbox</a></li>
      <li><a href="#farm">Down on the Farm</a></li>
      <li><a href="#today">Today&rsquo;s Slate</a></li>
      <li><a href="#div">{DIV_NAME}</a></li>
      <li><a href="#league">Around the League</a></li>
      <li><a href="#history">{TEAM_NAME} History</a></li>
    </ol>
  </nav>

  <main>

  <div id="live-game"></div>

  <section id="team" open>
    <summary>
      <span class="num">{_num.get("team", "")}</span>
      <span class="h">The {TEAM_NAME}</span>
      <span class="tag">{escape(summary_tag)}</span>
      <span class="chev">&#9656;</span>
    </summary>
    {headline_html}
  </section>

  {f"""<section id="scout" open>
    <summary>
      <span class="num">{_num.get("scout", "")}</span>
      <span class="h">Scouting Report</span>
      <span class="tag">Today&rsquo;s Matchup</span>
      <span class="chev">&#9656;</span>
    </summary>
    {scout_html}
  </section>""" if scout_html else ''}

  <section id="pulse" open>
    <summary>
      <span class="num">{_num.get("pulse", "")}</span>
      <span class="h">The Stretch</span>
      <span class="tag">Season Pulse</span>
      <span class="chev">&#9656;</span>
    </summary>
    {stretch_html}
  </section>

  <section id="pressbox" open>
    <summary>
      <span class="num">{_num.get("pressbox", "")}</span>
      <span class="h">The Pressbox</span>
      <span class="tag">Roster &middot; Transactions</span>
      <span class="chev">&#9656;</span>
    </summary>
    {pressbox_html}
  </section>

  <section id="farm" open>
    <summary>
      <span class="num">{_num.get("farm", "")}</span>
      <span class="h">Down on the Farm</span>
      <span class="tag">{minors_tag}</span>
      <span class="chev">&#9656;</span>
    </summary>
    {minors_html}
  </section>

  <section id="today" open>
    <summary>
      <span class="num">{_num.get("today", "")}</span>
      <span class="h">Today&rsquo;s Slate</span>
      <span class="tag">{t.strftime("%a %b ")}{t.day}</span>
      <span class="chev">&#9656;</span>
    </summary>
    {slate_html}
  </section>

  <section id="div" open>
    <summary>
      <span class="num">{_num.get("div", "")}</span>
      <span class="h">{DIV_NAME}</span>
      <span class="tag">Rivals &middot; Yesterday</span>
      <span class="chev">&#9656;</span>
    </summary>
    {division_html}
  </section>

  <section id="league" open>
    <summary>
      <span class="num">{_num.get("league", "")}</span>
      <span class="h">Around the League</span>
      <span class="tag">{y.strftime("%b ")}{y.day} &middot; {news_count} Note{"s" if news_count != 1 else ""}</span>
      <span class="chev">&#9656;</span>
    </summary>
    {around_league_html}
  </section>

  <section id="history" open>
    <summary>
      <span class="num">{_num.get("history", "")}</span>
      <span class="h">This Day in {TEAM_NAME} History</span>
      <span class="tag">{t.strftime("%b ")}{t.day}</span>
      <span class="chev">&#9656;</span>
    </summary>
    {history_html}
  </section>

  </main>
</div>

<footer class="foot">
  <span>The Morning Lineup &middot; <span class="flag">{CFG['branding']['footer_tag']}</span></span>
  <span>Data: MLB Stats API (statsapi.mlb.com)</span>
  <span>Filed {filed}</span>
</footer>

<script>
(function(){{
  var links = document.querySelectorAll('.toc a[href^="#"]');
  var sections = Array.from(links).map(function(a){{return {{link:a, el:document.querySelector(a.getAttribute('href'))}}}});
  function onScroll(){{
    var y = window.scrollY + 120;
    var current = sections[0];
    for (var i=0;i<sections.length;i++){{ if (sections[i].el && sections[i].el.offsetTop <= y) current = sections[i]; }}
    links.forEach(function(l){{l.classList.remove('active')}});
    if (current) current.link.classList.add('active');
  }}
  window.addEventListener('scroll', onScroll, {{passive:true}});
  onScroll();
  links.forEach(function(a){{
    a.addEventListener('click', function(e){{
      var id = a.getAttribute('href').slice(1);
      var el = document.getElementById(id); if (!el) return;
      e.preventDefault();
      var details = el.closest('details');
      if (details && !details.open) details.open = true;
      window.scrollTo({{top: el.offsetTop - 10, behavior: 'smooth'}});
      history.replaceState(null,'','#'+id);
    }});
  }});
}})();
</script>
<script>var TEAM_ID={TEAM_ID};var TEAM_IDLE_MSG="{CFG['branding']['idle_msg']}";</script>
<script src="live.js"></script><script src="reader-state.js" defer></script><script src="player-card.js" defer></script><script src="resolution-pass.js" defer></script>
<script>
window.addEventListener("message",function(e){{if(e.data&&e.data.type==="scorecard-height"){{var f=document.querySelector(".scorecard-frame");if(f)f.style.height=e.data.height+"px"}}}});
document.addEventListener("click",function(e){{var t=e.target;if(t&&t.ownerSVGElement)t=t.ownerSVGElement;var tr=t&&t.closest&&t.closest("tr.scorecard-link");if(tr){{var h=tr.getAttribute("data-href");if(h){{e.preventDefault();location.href=h}}}}}});
if("serviceWorker"in navigator)navigator.serviceWorker.register("sw.js").catch(function(){{}});
</script>

</body>
</html>"""

# ─── main ───────────────────────────────────────────────────────────────────

def _json_default(obj):
    """Serialize date/datetime objects for JSON output."""
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

def save_data_ledger(data):
    """Persist the daily data snapshot as data/YYYY-MM-DD.json."""
    DATA_DIR.mkdir(exist_ok=True)
    day = data["today"].isoformat()
    out = DATA_DIR / f"{day}.json"
    out.write_text(json.dumps(data, default=_json_default, ensure_ascii=False), encoding="utf-8")
    print(f"Saved data ledger → {out.name} ({out.stat().st_size:,} bytes)")


# ─── player cards (Phase 1: Cubs lineup + SP) ───────────────────────────────

def compute_temp_strip(game_log, role="hitter"):
    """Normalize a player's recent-game performance into a 15-element [0..1] array.

    Hitters: rolling OPS per game, clamped to [0, 1.5], rescaled to [0, 1].
    Pitchers: game ERA (lower = hotter), clamped to [0, 9], inverted to [0, 1].
    Missing games pad with None (rendered neutral on the card).

    Pure function. Takes the raw `splits` list from MLB's gameLog endpoint.
    """
    out = []
    splits = list(game_log or [])[:15]
    for sp in splits:
        st = sp.get("stat", {}) if isinstance(sp, dict) else {}
        if role == "hitter":
            try:
                ab = int(st.get("atBats", 0) or 0)
                if ab == 0:
                    out.append(None)
                    continue
                ops_str = st.get("ops", "")
                ops = float(ops_str) if ops_str not in ("", "-", ".---") else 0.0
                ops = max(0.0, min(1.5, ops))
                out.append(round(ops / 1.5, 3))
            except (ValueError, TypeError):
                out.append(None)
        else:  # pitcher
            try:
                ip_str = str(st.get("inningsPitched", "0") or "0")
                ip = float(ip_str) if ip_str not in ("", "-") else 0.0
                if ip <= 0:
                    out.append(None)
                    continue
                er = int(st.get("earnedRuns", 0) or 0)
                era = (er * 9.0) / ip
                era = max(0.0, min(9.0, era))
                out.append(round(1.0 - (era / 9.0), 3))
            except (ValueError, TypeError):
                out.append(None)
    while len(out) < 15:
        out.append(None)
    return out[:15]


def _extract_last_10_games(splits, role):
    """Extract last 10 games for the sparkline. Returns list ordered oldest→newest.
    Each entry: {date, opponent, value}. Hitters: OPS per game. Pitchers: GameScore."""
    out = []
    # MLB gameLog returns splits in reverse chronological order — slice the
    # 10 most recent then flip to oldest→newest for the sparkline left→right.
    for sp in (splits or [])[:10]:
        if not isinstance(sp, dict):
            continue
        st = sp.get("stat", {}) or {}
        date = sp.get("date", "")
        opp = (sp.get("opponent", {}) or {}).get("abbreviation", "?")
        value = None
        if role == "hitter":
            try:
                ab = int(st.get("atBats", 0) or 0)
                if ab > 0:
                    ops_str = st.get("ops", "")
                    if ops_str not in ("", "-", ".---"):
                        value = round(float(ops_str), 3)
            except (ValueError, TypeError):
                pass
        else:  # pitcher
            try:
                ip_str = str(st.get("inningsPitched", "0") or "0")
                ip = float(ip_str) if ip_str not in ("", "-") else 0.0
                if ip > 0:
                    # Bill James GameScore v1: 50 + outs + Ks - hits - 4*ER - 2*UER - BB
                    outs = int(round(ip * 3))
                    h = int(st.get("hits", 0) or 0)
                    er = int(st.get("earnedRuns", 0) or 0)
                    bb = int(st.get("baseOnBalls", 0) or 0)
                    k = int(st.get("strikeOuts", 0) or 0)
                    gs = 50 + outs + k - h - (4 * er) - (2 * bb)
                    value = max(0, min(100, gs))
            except (ValueError, TypeError):
                pass
        out.append({"date": date, "opp": opp, "value": value})
    return list(reversed(out))


def _float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _select_prediction(rec):
    """Pick a contextual daily prediction question for one player record.
    Walks rules in priority order; each rule fires only when its triggers
    match real signal in the record. Falls through to a pid-rotated
    generic pool so even quiet players get varied questions.
    Returns {question_text, resolution_rule, role_tag, context_tag}."""
    role = rec.get("role", "hitter")
    name = rec.get("name", "the player")
    last = rec.get("last_name", "") or name.split()[-1]
    last_10 = rec.get("last_10_games", []) or []
    season = rec.get("season", {}) or {}
    pid = rec.get("id", 0) or 0

    # Hitter rule set
    if role == "hitter":
        avg = _float(season.get("avg"), 0.0)
        ops = _float(season.get("ops"), 0.0)
        hr = _int(season.get("homeRuns"))
        rbi = _int(season.get("rbi"))
        sb = _int(season.get("stolenBases"))
        games = _int(season.get("gamesPlayed"))
        recent = [g["value"] for g in last_10 if g.get("value") is not None]
        last3 = recent[:3]  # last_10 is newest-first
        last3_avg = sum(last3) / len(last3) if last3 else 0.0

        # Rule: HR milestone watch (tight window)
        for milestone in (5, 10, 20, 30, 40, 50):
            if 0 < (milestone - hr) <= 2:
                return {
                    "question_text": f"Will {last} hit HR #{milestone} today?",
                    "resolution_rule": {"stat": "homeRuns", "op": ">=", "value": milestone - hr},
                    "role_tag": "hitter",
                    "context_tag": "milestone-watch",
                }

        # Rule: ice-cold last 3
        if len(last3) >= 2 and last3_avg < 0.450:
            return {
                "question_text": f"Can {last} end the cold snap with a hit?",
                "resolution_rule": {"stat": "hits", "op": ">=", "value": 1},
                "role_tag": "hitter",
                "context_tag": "cold-snap",
            }

        # Rule: red-hot last 3
        if len(last3) >= 2 and last3_avg > 0.900:
            return {
                "question_text": f"Can {last} keep the heater going — multi-hit game?",
                "resolution_rule": {"stat": "hits", "op": ">=", "value": 2},
                "role_tag": "hitter",
                "context_tag": "red-hot",
            }

        # Rule: Mendoza watch (season BA below .200, enough games)
        if games >= 8 and 0 < avg < 0.200:
            return {
                "question_text": f"Will {last} climb back above the Mendoza line?",
                "resolution_rule": {"stat": "hits", "op": ">=", "value": 2},
                "role_tag": "hitter",
                "context_tag": "mendoza",
            }

        # Rule: season-hot (BA above .320)
        if games >= 8 and avg >= 0.320:
            return {
                "question_text": f"Can {last} stay scorching — another multi-hit game?",
                "resolution_rule": {"stat": "hits", "op": ">=", "value": 2},
                "role_tag": "hitter",
                "context_tag": "season-hot",
            }

        # Rule: power threat (HR per game >= 0.15, nibbled threshold for early season)
        if games >= 5 and hr >= 1 and (hr / max(games, 1)) >= 0.15:
            return {
                "question_text": f"Is {last} leaving the yard today?",
                "resolution_rule": {"stat": "homeRuns", "op": ">=", "value": 1},
                "role_tag": "hitter",
                "context_tag": "power-threat",
            }

        # Rule: speed threat (3+ SB already)
        if sb >= 3:
            return {
                "question_text": f"Will {last} swipe another bag today?",
                "resolution_rule": {"stat": "stolenBases", "op": ">=", "value": 1},
                "role_tag": "hitter",
                "context_tag": "speed-threat",
            }

        # Rule: RBI machine (0.8+ RBI per game)
        if games >= 5 and (rbi / max(games, 1)) >= 0.80:
            return {
                "question_text": f"Will {last} drive in a run today?",
                "resolution_rule": {"stat": "rbi", "op": ">=", "value": 1},
                "role_tag": "hitter",
                "context_tag": "rbi-machine",
            }

        # Generic fallback — rotate by pid so different players get different
        # flavors even when no narrative rule fires.
        pool = [
            (f"Will {last} get a hit today?",
             {"stat": "hits", "op": ">=", "value": 1}),
            (f"Will {last} post a multi-hit game?",
             {"stat": "hits", "op": ">=", "value": 2}),
            (f"Will {last} drive in a run today?",
             {"stat": "rbi", "op": ">=", "value": 1}),
            (f"Will {last} go yard today?",
             {"stat": "homeRuns", "op": ">=", "value": 1}),
        ]
        q, rule = pool[pid % len(pool)]
        return {
            "question_text": q,
            "resolution_rule": rule,
            "role_tag": "hitter",
            "context_tag": "generic",
        }

    # Pitcher rule set
    else:
        era = _float(season.get("era"), 99.0)
        whip = _float(season.get("whip"), 9.0)
        so = _int(season.get("strikeOuts"))
        gs = _int(season.get("gamesStarted"))
        gp = _int(season.get("gamesPlayed"))
        wins = _int(season.get("wins"))
        k_per_start = (so / gs) if gs > 0 else 0.0
        recent = [g["value"] for g in last_10 if g.get("value") is not None]
        last3 = recent[:3]
        last3_gs = sum(last3) / len(last3) if last3 else 0.0

        # Rule: K milestone watch
        for milestone in (25, 50, 100, 150, 200, 250):
            if 0 < (milestone - so) <= 5:
                return {
                    "question_text": f"Will {last} reach {milestone} K today?",
                    "resolution_rule": {"stat": "strikeOuts", "op": ">=", "value": milestone - so},
                    "role_tag": "pitcher",
                    "context_tag": "milestone-watch",
                }

        # Rule: dominant form (recent GameScore > 55)
        if len(last3) >= 2 and last3_gs > 55:
            return {
                "question_text": f"Can {last} keep carving — 7+ K today?",
                "resolution_rule": {"stat": "strikeOuts", "op": ">=", "value": 7},
                "role_tag": "pitcher",
                "context_tag": "dominant",
            }

        # Rule: shaky form (recent GameScore < 40)
        if len(last3) >= 2 and last3_gs < 40:
            return {
                "question_text": f"Can {last} bounce back with a quality start?",
                "resolution_rule": {"stat": "qualityStart", "op": "==", "value": True},
                "role_tag": "pitcher",
                "context_tag": "bounce-back",
            }

        # Rule: ace-season (ERA sub-3.00, enough innings)
        if gs >= 3 and 0 < era < 3.00:
            return {
                "question_text": f"Will {last} stay dominant — quality start?",
                "resolution_rule": {"stat": "qualityStart", "op": "==", "value": True},
                "role_tag": "pitcher",
                "context_tag": "ace-season",
            }

        # Rule: K artist (7+ K per start)
        if gs >= 2 and k_per_start >= 7.0:
            return {
                "question_text": f"Is {last} punching out 7+ again today?",
                "resolution_rule": {"stat": "strikeOuts", "op": ">=", "value": 7},
                "role_tag": "pitcher",
                "context_tag": "k-artist",
            }

        # Rule: command guy (WHIP below 1.10)
        if gs >= 2 and 0 < whip < 1.10:
            return {
                "question_text": f"Will {last} paint corners — quality start today?",
                "resolution_rule": {"stat": "qualityStart", "op": "==", "value": True},
                "role_tag": "pitcher",
                "context_tag": "command",
            }

        # Rule: high-ERA watch (struggling — can he get back on track)
        if gs >= 2 and era >= 5.00:
            return {
                "question_text": f"Can {last} turn it around — quality start?",
                "resolution_rule": {"stat": "qualityStart", "op": "==", "value": True},
                "role_tag": "pitcher",
                "context_tag": "struggling",
            }

        # Generic fallback — rotate by pid for variety
        pool = [
            (f"Will {last} record 5+ K today?",
             {"stat": "strikeOuts", "op": ">=", "value": 5}),
            (f"Will {last} deliver a quality start?",
             {"stat": "qualityStart", "op": "==", "value": True}),
            (f"Will {last} punch out 7 today?",
             {"stat": "strikeOuts", "op": ">=", "value": 7}),
        ]
        q, rule = pool[pid % len(pool)]
        return {
            "question_text": q,
            "resolution_rule": rule,
            "role_tag": "pitcher",
            "context_tag": "generic",
        }


def _fetch_next_game_time(team_id):
    """Get the ISO datetime of the team's next scheduled game start, or None.
    Used by Phase 2's prediction lock — picks lock at first pitch."""
    try:
        from datetime import timedelta as _td
        _today = datetime.now(tz=CT).date()
        start = _today.isoformat()
        end = (_today + _td(days=14)).isoformat()
        sched = fetch("/schedule", sportId=1, teamId=team_id,
                      startDate=start, endDate=end)
        for date_block in sched.get("dates", []):
            for game in date_block.get("games", []):
                game_date = game.get("gameDate", "")
                status = (game.get("status", {}) or {}).get("abstractGameState", "")
                if game_date and status in ("Preview", "Live"):
                    return game_date
    except Exception as e:
        print(f"  warning: next game lookup for team {team_id} failed: {e}", flush=True)
    return None


def _fetch_player_record(pid, role, season):
    """Fetch bio + season line + gameLog for one player. Returns None on failure."""
    if not pid:
        return None
    try:
        person = fetch(f"/people/{pid}").get("people", [{}])[0]
    except Exception as e:
        print(f"  warning: player bio {pid} failed: {e}", flush=True)
        return None

    group = "pitching" if role == "pitcher" else "hitting"
    season_stats = {}
    career = []
    try:
        season_data = fetch(
            f"/people/{pid}/stats",
            stats="season",
            season=str(season),
            group=group,
        )
        for s in season_data.get("stats", []):
            for sp in s.get("splits", []):
                season_stats = sp.get("stat", {})
                break
    except Exception as e:
        print(f"  warning: player season {pid} failed: {e}", flush=True)

    try:
        career_data = fetch(
            f"/people/{pid}/stats",
            stats="yearByYear",
            group=group,
        )
        for s in career_data.get("stats", []):
            for sp in s.get("splits", []):
                if sp.get("sport", {}).get("id") != 1:
                    continue
                st = sp.get("stat", {})
                career.append({
                    "year": sp.get("season", ""),
                    "team": sp.get("team", {}).get("abbreviation", ""),
                    "stat": st,
                })
    except Exception as e:
        print(f"  warning: player career {pid} failed: {e}", flush=True)

    temp = []
    last_10 = []
    try:
        gl_data = fetch(
            f"/people/{pid}/stats",
            stats="gameLog",
            season=str(season),
            group=group,
        )
        splits = []
        for s in gl_data.get("stats", []):
            splits = s.get("splits", [])[:15]
            break
        temp = compute_temp_strip(splits, role=role)
        last_10 = _extract_last_10_games(splits, role=role)
    except Exception as e:
        print(f"  warning: player gameLog {pid} failed: {e}", flush=True)
        temp = [None] * 15
        last_10 = []

    pos = person.get("primaryPosition", {}).get("abbreviation", "")
    return {
        "id": pid,
        "name": person.get("fullName", ""),
        "last_name": person.get("lastName", ""),
        "first_name": person.get("firstName", ""),
        "jersey": person.get("primaryNumber", ""),
        "position": pos,
        "role": role,
        "bats": person.get("batSide", {}).get("code", ""),
        "throws": person.get("pitchHand", {}).get("code", ""),
        "height": person.get("height", ""),
        "weight": person.get("weight", 0),
        "birth_date": person.get("birthDate", ""),
        "birth_city": person.get("birthCity", ""),
        "birth_state": person.get("birthStateProvince", ""),
        "birth_country": person.get("birthCountry", ""),
        "age": person.get("currentAge", 0),
        "headshot_url": (
            f"https://img.mlbstatic.com/mlb-photos/image/upload/"
            f"d_people:generic:headshot:67:current.png/w_426,q_100/"
            f"v1/people/{pid}/headshot/67/current"
        ),
        "season": season_stats,
        "career": career,
        "temp_strip": temp,
        "last_10_games": last_10,
        "advanced": {},  # Phase 1.5: Baseball Savant Statcast
        # next_game_time and prediction injected by load_team_players (needs team_id)
        "next_game_time": None,
        "prediction": None,
    }


_PLAYER_CACHE_DIR = None

def _player_cache_path(pid, season, today):
    global _PLAYER_CACHE_DIR
    if _PLAYER_CACHE_DIR is None:
        _PLAYER_CACHE_DIR = DATA_DIR / "cache" / "players"
        _PLAYER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _PLAYER_CACHE_DIR / f"{pid}-{season}-{today.isoformat()}-v2.json"


def _fetch_player_record_cached(pid, role, season, today):
    """Disk-cached wrapper around _fetch_player_record. Cache key = (pid, season, date).
    Cache auto-invalidates daily — a new file per (player, day)."""
    cache_path = _player_cache_path(pid, season, today)
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    rec = _fetch_player_record(pid, role, season)
    if rec:
        try:
            cache_path.write_text(
                json.dumps(rec, default=_json_default, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass
    return rec


def load_team_players(team_id, season, today, max_workers=4):
    """Hydrate the full active roster for a team into a player-card dict.
    Returns {str(pid): record, ...}. Bounded concurrency, daily disk cache."""
    import concurrent.futures
    try:
        roster_data = fetch(f"/teams/{team_id}/roster", rosterType="active")
    except Exception as e:
        print(f"  warning: roster fetch failed for team {team_id}: {e}", flush=True)
        return {}
    roster = roster_data.get("roster", []) or []
    targets = []
    for entry in roster:
        person = entry.get("person", {}) or {}
        pid = person.get("id")
        if not pid:
            continue
        pos_code = (entry.get("position", {}) or {}).get("code", "")
        role = "pitcher" if pos_code == "1" else "hitter"
        targets.append((pid, role))
    if not targets:
        return {}

    players = {}
    def _one(pid, role):
        try:
            return pid, _fetch_player_record_cached(pid, role, season, today)
        except Exception as e:
            print(f"  warning: player {pid} hydrate failed: {e}", flush=True)
            return pid, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(_one, pid, role) for pid, role in targets]
        for f in concurrent.futures.as_completed(futs):
            pid, rec = f.result()
            if rec:
                players[str(pid)] = rec

    # Phase 2: inject next_game_time + prediction once per team (cheap)
    next_game = _fetch_next_game_time(team_id)
    for pid_str, rec in players.items():
        rec["next_game_time"] = next_game
        try:
            rec["prediction"] = _select_prediction(rec)
        except Exception as e:
            print(f"  warning: prediction selection {pid_str} failed: {e}", flush=True)
            rec["prediction"] = None

    return players


def save_player_index():
    """Rebuild the global pid→slug index by scanning every players-*.json.
    Used by the home page binder to look up which team a followed player
    belongs to when the followed_players row is missing mlb_team_abbr."""
    out = {}
    for f in sorted(DATA_DIR.glob("players-*.json")):
        try:
            slug = f.stem.replace("players-", "")
            d = json.loads(f.read_text(encoding="utf-8"))
            for pid in (d.get("players") or {}).keys():
                out[pid] = slug
        except Exception as e:
            print(f"  warning: index scan {f.name} failed: {e}", flush=True)
    payload = {
        "generated_at": datetime.now(tz=CT).isoformat(timespec="seconds"),
        "count": len(out),
        "index": out,
    }
    (DATA_DIR / "player-index.json").write_text(
        json.dumps(payload, default=_json_default, ensure_ascii=False),
        encoding="utf-8",
    )


def save_players(team_slug, players, today):
    """Write per-team player-card JSON to data/players-<slug>.json."""
    DATA_DIR.mkdir(exist_ok=True)
    payload = {
        "generated_at": datetime.now(tz=CT).isoformat(timespec="seconds"),
        "team": team_slug,
        "team_full_name": CFG.get("full_name", ""),
        "team_abbreviation": CFG.get("abbreviation", ""),
        "today": today.isoformat(),
        "players": players,
    }
    out = DATA_DIR / f"players-{team_slug}.json"
    out.write_text(
        json.dumps(payload, default=_json_default, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Saved player cards → {out.name} ({out.stat().st_size:,} bytes, {len(players)} players)")
    return out


def load_player_cards(lineup, sp_pid, season):
    """Pull per-player card data for today's lineup + starting pitcher.

    `lineup` is a list of dicts with at least {"id": pid}. `sp_pid` is the
    integer MLB player ID for the starting pitcher. Returns a dict keyed by
    string player ID, matching the `<player-card pid="...">` attribute.
    """
    players = {}
    for slot in lineup or []:
        pid = slot.get("id")
        if not pid:
            continue
        rec = _fetch_player_record(pid, "hitter", season)
        if rec:
            players[str(pid)] = rec
    if sp_pid:
        rec = _fetch_player_record(sp_pid, "pitcher", season)
        if rec:
            players[str(sp_pid)] = rec
    return players


def save_players_cubs(players, today):
    """Write the player-card JSON alongside the data ledger."""
    DATA_DIR.mkdir(exist_ok=True)
    payload = {
        "generated_at": datetime.now(tz=CT).isoformat(timespec="seconds"),
        "team": "cubs",
        "today": today.isoformat(),
        "players": players,
    }
    out = DATA_DIR / "players-cubs.json"
    out.write_text(
        json.dumps(payload, default=_json_default, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Saved player cards → {out.name} ({out.stat().st_size:,} bytes, {len(players)} players)")
    return out

def load_data_from_fixture(path):
    """Load a frozen load_all() snapshot from JSON and rehydrate date fields.

    Inverse of _json_default: json.loads leaves date keys as ISO strings, but
    downstream renderers (e.g. build.py:1709 `(t - date(t.year, 1, 1)).days`)
    require real `date` objects. Rehydrates `today`, `yest`, and
    `cubs_game_date` when present.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data["today"] = date.fromisoformat(data["today"])
    data["yest"] = date.fromisoformat(data["yest"])
    if data.get("cubs_game_date"):
        data["cubs_game_date"] = date.fromisoformat(data["cubs_game_date"])
    return data

def _argv_value(flag):
    """Return the value following `flag` in sys.argv, or None if absent."""
    if flag in sys.argv:
        i = sys.argv.index(flag)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return None

def build_landing():
    """Generate landing page from all team configs."""
    teams_dir = ROOT / "teams"
    teams = []
    for cfg_file in sorted(teams_dir.glob("*.json")):
        cfg = json.loads(cfg_file.read_text())
        cfg["slug"] = cfg_file.stem
        teams.append({
            "id": cfg["id"],
            "slug": cfg["slug"],
            "name": cfg.get("name", ""),
            "full_name": cfg["full_name"],
            "abbreviation": cfg.get("abbreviation", ""),
            "division_name": cfg["division_name"],
            "colors": cfg["colors"],
        })
    html = (ROOT / "landing.html").read_text(encoding="utf-8")
    out = ROOT / "index.html"
    out.write_text(html, encoding="utf-8")
    (ROOT / "landing-teams.js").write_text(
        "window.__TEAMS = " + json.dumps(teams) + ";\n", encoding="utf-8"
    )
    print(f"Wrote landing page → {out} ({len(html):,} bytes)")

if __name__ == "__main__":
    if "--landing" in sys.argv:
        build_landing()
    elif "--capture-fixture" in sys.argv:
        # Capture the current load_all() output to a JSON fixture and exit.
        # No rendering, no data ledger write. Used by the snapshot test
        # bootstrap to freeze a canonical data snapshot.
        capture_path = _argv_value("--capture-fixture")
        print("Fetching MLB data for fixture capture …", flush=True)
        data = load_all()
        Path(capture_path).parent.mkdir(parents=True, exist_ok=True)
        Path(capture_path).write_text(
            json.dumps(data, default=_json_default, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Captured fixture → {capture_path} ({Path(capture_path).stat().st_size:,} bytes)")
    else:
        fixture_path = _argv_value("--fixture")
        if fixture_path:
            print(f"Loading data from fixture {fixture_path} …", flush=True)
            data = load_data_from_fixture(fixture_path)
            briefing = TeamBriefing(
                config=CFG, data=data,
                team_id=TEAM_ID, team_name=TEAM_NAME,
                div_id=DIV_ID, div_name=DIV_NAME,
                affiliates=AFFILIATES,
            )
        else:
            print("Fetching MLB data …", flush=True)
            briefing = build_briefing(_team_slug)
            save_data_ledger(briefing.data)
            # Phase 2: All-teams player-card pipeline (full active roster).
            try:
                _d2 = briefing.data
                print(f"Fetching player cards for {_team_slug} (active roster) …", flush=True)
                _team_players = load_team_players(TEAM_ID, _d2["season"], _d2["today"])
                save_players(_team_slug, _team_players, _d2["today"])
                save_player_index()
            except Exception as _e2:
                print(f"  warning: team player-card pipeline failed: {_e2}", flush=True)
            # Phase 1 holdover: Cubs-only lineup fallback (feeds today_lineup
            # for headline.py rendering when MLB hasn't posted batting order).
            if _team_slug == "cubs":
                try:
                    _d = briefing.data
                    _tl = _d.get("today_lineup", {}) or {}
                    _ng = _d.get("next_games") or []
                    _cubs_side_lineup = []
                    _sp_pid = None
                    if _ng:
                        _tg = _ng[0]
                        _is_home = _tg["teams"]["home"]["team"]["id"] == TEAM_ID
                        _side = "home" if _is_home else "away"
                        _cubs_side_lineup = _tl.get(_side, []) or []
                        _cubs_pp = _tg["teams"][_side].get("probablePitcher") or {}
                        _sp_pid = _cubs_pp.get("id")
                    # Fallback: if today's lineup hasn't been posted yet, pick the
                    # top 9 hitters from the hydrated roster by games played so the
                    # card experience always has content to show.
                    if not _cubs_side_lineup:
                        _roster = _d.get("cubs_hitters", {}) or {}
                        _candidates = []
                        for _p in _roster.get("roster", []):
                            _pos = _p.get("position", {}).get("abbreviation", "")
                            if _pos == "P":
                                continue
                            _person = _p.get("person", {}) or {}
                            _stats = _person.get("stats", [])
                            _games = 0
                            if _stats and _stats[0].get("splits"):
                                _games = _stats[0]["splits"][0].get("stat", {}).get("gamesPlayed", 0) or 0
                            _candidates.append({
                                "id": _person.get("id"),
                                "name": _person.get("fullName", ""),
                                "pos": _pos,
                                "_games": _games,
                            })
                        _candidates.sort(key=lambda x: -x.get("_games", 0))
                        _cubs_side_lineup = _candidates[:9]
                        print(f"  (using roster fallback — {len(_cubs_side_lineup)} top hitters by games played)", flush=True)
                        # Feed the fallback lineup back into the briefing so
                        # the rendered page's "Lineup" section shows it too.
                        if _ng:
                            _fallback_side = "home" if _is_home else "away"
                            _d["today_lineup"] = _d.get("today_lineup") or {"home": [], "away": []}
                            _d["today_lineup"][_fallback_side] = [
                                {"id": _c["id"], "name": _c["name"], "pos": _c["pos"]}
                                for _c in _cubs_side_lineup
                            ]
                except Exception as _e:
                    print(f"  warning: cubs lineup fallback failed: {_e}", flush=True)
        print("Rendering page …", flush=True)
        html = page(briefing)
        out_dir_override = _argv_value("--out-dir")
        if out_dir_override:
            out_path = Path(out_dir_override) / _team_slug / "index.html"
        else:
            out_path = OUT
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
        print(f"Wrote {out_path} ({len(html):,} bytes)")
        # Copy player-card.js + reader-state.js + resolution-pass.js into
        # the team output dir so the relative script tags resolve on every page.
        try:
            import shutil
            for _asset in ("player-card.js", "reader-state.js", "resolution-pass.js"):
                _src = ROOT / _asset
                if _src.exists():
                    shutil.copyfile(_src, out_path.parent / _asset)
            # sw.js: rewrite cache version to BUILD_ID, stamp root + team copy.
            # Single source of truth — team dirs are regenerated every build so
            # they can't drift from root.
            import re as _re
            _sw_src = ROOT / "sw.js"
            if _sw_src.exists():
                _sw_text = _sw_src.read_text(encoding="utf-8")
                _sw_text = _re.sub(
                    r'lineup-[A-Za-z0-9]+',
                    f'lineup-{BUILD_ID}',
                    _sw_text,
                    count=1,
                )
                _sw_src.write_text(_sw_text, encoding="utf-8")
                (out_path.parent / "sw.js").write_text(_sw_text, encoding="utf-8")
        except Exception as _e3:
            print(f"  warning: phase 2 asset copy failed: {_e3}", flush=True)
