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

    # Editorial lede
    lede_html = sections.around_league.render_lede_block(briefing)

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
<meta name="theme-color" content="#0d0f14">
<link rel="manifest" href="manifest.json">
<link rel="apple-touch-icon" href="icons/icon-192.png">
<title>The Morning Lineup &mdash; {fmt_date(t)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,600;0,800;0,900;1,700&family=Oswald:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600;700&family=Lora:ital,wght@0,400;0,500;0,600;1,400;1,500&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>

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
    <img src="https://www.mlbstatic.com/team-logos/team-cap-on-dark/{TEAM_ID}.svg" alt="{TEAM_NAME}" class="mast-logo">
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
<script src="live.js"></script>
<script>
window.addEventListener("message",function(e){{if(e.data&&e.data.type==="scorecard-height"){{var f=document.querySelector(".scorecard-frame");if(f)f.style.height=e.data.height+"px"}}}});
document.addEventListener("click",function(e){{var tr=e.target.closest("tr.scorecard-link");if(tr){{var h=tr.getAttribute("data-href");if(h)window.open(h,"_blank")}}}});
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
            "full_name": cfg["full_name"],
            "division_name": cfg["division_name"],
            "colors": cfg["colors"],
        })
    template = (ROOT / "landing.html").read_text(encoding="utf-8")
    html = template.replace("__TEAMS_JSON__", json.dumps(teams))
    out = ROOT / "index.html"
    out.write_text(html, encoding="utf-8")
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
