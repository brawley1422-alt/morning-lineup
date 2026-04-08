#!/usr/bin/env python3
"""
build.py — generate ~/morning-lineup/index.html with real MLB data
pulled from statsapi.mlb.com. No external deps; stdlib only.
Run: python3 build.py
"""
import json
import urllib.request
import urllib.parse
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
from html import escape
try:
    from zoneinfo import ZoneInfo
    CT = ZoneInfo("America/Chicago")
except (ImportError, KeyError):
    # Minimal container without tzdata — fall back to CDT (UTC-5)
    CT = timezone(timedelta(hours=-5))

CUBS_ID = 112
API = "https://statsapi.mlb.com/api/v1"
OUT = Path(__file__).parent / "index.html"
STYLE_FILE = Path(__file__).parent / "style.css"
HISTORY_FILE = Path(__file__).parent / "history.json"
PROSPECTS_FILE = Path(__file__).parent / "prospects.json"
DATA_DIR = Path(__file__).parent / "data"

# Cubs minor league affiliates (2026)
AFFILIATES = [
    {"id": 451, "name": "Iowa Cubs",          "level": "AAA", "sport_id": 11},
    {"id": 553, "name": "Knoxville Smokies",  "level": "AA",  "sport_id": 12},
    {"id": 550, "name": "South Bend Cubs",    "level": "A+",  "sport_id": 13},
    {"id": 521, "name": "Myrtle Beach Pelicans", "level": "A", "sport_id": 14},
]

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
            if tr["team"]["id"] == CUBS_ID:
                cubs_rec = tr
                break

    # Next 7 days Cubs games → take next 3 (excluding today if already started)
    end = today + timedelta(days=8)
    sched_next = fetch(
        "/schedule",
        sportId=1, teamId=CUBS_ID,
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
        tg_opp_id = tg_away_id if tg_home_id == CUBS_ID else tg_home_id
        tg_is_home = tg_home_id == CUBS_ID

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
            ss_url = fetch("/schedule", sportId=1, teamId=CUBS_ID, season=season,
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
                    cubs_home = gh["team"]["id"] == CUBS_ID
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
            dd = fetch("/schedule", sportId=1, date=day.isoformat(), teamId=CUBS_ID,
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
    roster = fetch(f"/teams/{CUBS_ID}/roster", rosterType="40Man")
    injuries = [p for p in roster.get("roster", [])
                if p.get("status", {}).get("code", "A") != "A"]

    # Hot Cubs bats: last 7 games, min 10 PA, sort by OPS
    cubs_hitters = fetch(
        f"/teams/{CUBS_ID}/roster",
        rosterType="active",
        hydrate=f"person(stats(type=lastXGames,limit=7,season={season},gameType=R))",
    )
    cubs_pitchers = fetch(
        f"/teams/{CUBS_ID}/roster",
        rosterType="active",
        hydrate=f"person(stats(type=lastXGames,limit=7,season={season},gameType=R,group=pitching))",
    )

    # Cubs season stats for team leaders
    cubs_season = fetch(
        f"/teams/{CUBS_ID}/roster",
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
        tx_resp = fetch("/transactions", teamId=CUBS_ID,
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
        tg_is_home = tg_home_id == CUBS_ID
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

def fmt_short_date(d):
    return d.strftime("%a, %b ") + str(d.day)

# ─── section renderers ──────────────────────────────────────────────────────

def render_line_score(game, tmap, game_date=None, yest=None):
    if not game:
        return ('<p class="slang"><em>No completed Cubs game in the last week.</em></p>', "&mdash;")
    away_id = game["teams"]["away"]["team"]["id"]
    home_id = game["teams"]["home"]["team"]["id"]
    away_ab = abbr(tmap, away_id)
    home_ab = abbr(tmap, home_id)
    away_score = game["teams"]["away"].get("score", 0)
    home_score = game["teams"]["home"].get("score", 0)
    cubs_won = (away_id == CUBS_ID and away_score > home_score) or \
               (home_id == CUBS_ID and home_score > away_score)
    innings = list(game["linescore"].get("innings", []))
    max_inn = max(len(innings), 9)
    # pad to 9
    while len(innings) < 9:
        innings.append({"away": {"runs": ""}, "home": {"runs": ""}})
    away_tot = game["linescore"]["teams"]["away"]
    home_tot = game["linescore"]["teams"]["home"]

    def row(label, tid, innings_side, totals):
        cells = ''.join(
            f'<td>{"" if i.get(innings_side, {}).get("runs") in (None,"") else i[innings_side].get("runs",0)}</td>'
            for i in innings
        )
        won_cls = ' class="won"' if ((tid==away_id and away_score>home_score) or (tid==home_id and home_score>away_score)) else ''
        return (f'<tr{won_cls}><td class="team">{escape(label)}</td>{cells}'
                f'<td class="rhe">{totals["runs"]}</td>'
                f'<td class="rhe">{totals["hits"]}</td>'
                f'<td class="rhe">{totals["errors"]}</td></tr>')

    inn_hdrs = ''.join(f'<th>{i+1}</th>' for i in range(len(innings)))
    venue = game.get("venue", {}).get("name", "")
    status = game.get("status", {}).get("detailedState", "Final")
    final_label = "Final"
    if len(innings) > 9:
        final_label = f"Final / {len(innings)}"
    try:
        start_time = fmt_time_ct(game["gameDate"])
    except Exception:
        start_time = ""

    decisions = game.get("decisions", {}) or {}
    wp = decisions.get("winner", {}).get("fullName", "")
    lp = decisions.get("loser", {}).get("fullName", "")
    sv = decisions.get("save", {}).get("fullName", "")

    pitcher_bits = []
    if wp: pitcher_bits.append(f'<span><strong>W</strong><span class="w">{escape(wp)}</span></span>')
    if lp: pitcher_bits.append(f'<span><strong>L</strong><span class="l">{escape(lp)}</span></span>')
    if sv: pitcher_bits.append(f'<span><strong>S</strong><span class="s">{escape(sv)}</span></span>')

    summary_tag = f'W {away_score}-{home_score} at {home_ab}' if (away_id==CUBS_ID and cubs_won) else \
                  f'L {away_score}-{home_score} at {home_ab}' if away_id==CUBS_ID else \
                  f'W {home_score}-{away_score} vs {away_ab}' if cubs_won else \
                  f'L {home_score}-{away_score} vs {away_ab}'

    date_note = ""
    if game_date and yest and game_date != yest:
        date_note = f" &middot; {game_date.strftime('%a %b ')}{game_date.day}"
    html = f"""
    <div class="scoreboard" aria-label="Line score">
      <div class="meta">
        <span>{escape(venue)} &middot; {start_time}{date_note}</span>
        <span class="fin">{final_label}</span>
      </div>
      <table>
        <thead><tr><th></th>{inn_hdrs}<th>R</th><th>H</th><th>E</th></tr></thead>
        <tbody>
          {row(away_ab, away_id, 'away', away_tot)}
          {row(home_ab, home_id, 'home', home_tot)}
        </tbody>
      </table>
      <div class="pitchers">{''.join(pitcher_bits)}</div>
    </div>
    """
    return html, summary_tag

def render_three_stars(boxscore, game, tmap):
    """Pick top Cubs hitter + winning pitcher + runner-up."""
    if not boxscore or not game:
        return '<p class="slang"><em>Three stars unavailable.</em></p>'
    # determine Cubs side
    cubs_side = "away" if game["teams"]["away"]["team"]["id"]==CUBS_ID else "home"
    players = boxscore["teams"][cubs_side]["players"]
    # rank hitters by (H + 2B + 2*3B + 3*HR + RBI + SB) as crude productivity
    hitters = []
    for pid, p in players.items():
        stats = p.get("stats", {}).get("batting", {})
        if not stats or stats.get("atBats", 0) == 0: continue
        h = stats.get("hits", 0); d = stats.get("doubles", 0); t = stats.get("triples", 0)
        hr = stats.get("homeRuns", 0); rbi = stats.get("rbi", 0); sb = stats.get("stolenBases", 0)
        bb = stats.get("baseOnBalls", 0); r = stats.get("runs", 0)
        score = h + d + 2*t + 3*hr + rbi + sb + 0.5*bb + 0.5*r
        hitters.append((score, p, stats))
    hitters.sort(key=lambda x: -x[0])
    # winning/losing pitcher on Cubs side
    pitchers = []
    for pid, p in players.items():
        ps = p.get("stats", {}).get("pitching", {})
        if not ps or ps.get("inningsPitched") in (None, "0.0", 0): continue
        ip = float(ps.get("inningsPitched", "0.0"))
        er = ps.get("earnedRuns", 0); k = ps.get("strikeOuts", 0)
        pitchers.append((ip*2 + k - er*3, p, ps))
    pitchers.sort(key=lambda x: -x[0])

    stars = []
    if pitchers:
        p, ps = pitchers[0][1], pitchers[0][2]
        line = f"{ps.get('inningsPitched')} IP, {ps.get('hits',0)} H, {ps.get('earnedRuns',0)} ER, {ps.get('baseOnBalls',0)} BB, {ps.get('strikeOuts',0)} K"
        stars.append((p['person']['fullName'], line, ""))
    if hitters:
        p, s = hitters[0][1], hitters[0][2]
        line = f"{s.get('hits',0)}-{s.get('atBats',0)}"
        extras = []
        if s.get('doubles',0): extras.append(f"{s['doubles']} 2B")
        if s.get('triples',0): extras.append(f"{s['triples']} 3B")
        if s.get('homeRuns',0): extras.append(f"{s['homeRuns']} HR")
        if s.get('rbi',0): extras.append(f"{s['rbi']} RBI")
        if s.get('stolenBases',0): extras.append(f"{s['stolenBases']} SB")
        if s.get('baseOnBalls',0): extras.append(f"{s['baseOnBalls']} BB")
        line = f"{s.get('hits',0)}-{s.get('atBats',0)}" + ("" if not extras else ", " + ", ".join(extras))
        stars.append((p['person']['fullName'], line, ""))
    if len(hitters) > 1:
        p, s = hitters[1][1], hitters[1][2]
        extras = []
        if s.get('doubles',0): extras.append(f"{s['doubles']} 2B")
        if s.get('homeRuns',0): extras.append(f"{s['homeRuns']} HR")
        if s.get('rbi',0): extras.append(f"{s['rbi']} RBI")
        if s.get('stolenBases',0): extras.append(f"{s['stolenBases']} SB")
        line = f"{s.get('hits',0)}-{s.get('atBats',0)}" + ("" if not extras else ", " + ", ".join(extras))
        stars.append((p['person']['fullName'], line, ""))

    # reorder: best performer first
    # simple heuristic: put hitter #1 first if score > 6, else pitcher first
    if hitters and hitters[0][0] >= 6:
        stars = [stars[1], stars[0], stars[2]] if len(stars)>=3 else stars

    cards = []
    for i, (name, line, note) in enumerate(stars[:3]):
        cards.append(f"""<div class="star">
        <div class="rank">{i+1}</div>
        <div class="name">{escape(name)}</div>
        <div class="line">{escape(line)}</div>
      </div>""")
    return f'<div class="stars">{"".join(cards)}</div>'

def render_key_plays(plays_data, game, tmap):
    if not plays_data or not game:
        return ""
    scoring = plays_data.get("scoringPlays", [])
    all_plays = plays_data.get("allPlays", [])
    if not scoring or not all_plays:
        return ""
    plays_by_idx = {p.get("about", {}).get("atBatIndex"): p for p in all_plays}
    items = []
    for idx in scoring[:6]:
        p = plays_by_idx.get(idx) or (all_plays[idx] if idx < len(all_plays) else None)
        if not p: continue
        about = p.get("about", {})
        inn = about.get("inning")
        half = about.get("halfInning", "")[:1].upper()  # t/b
        inn_str = f"{half}{inn}" if inn else ""
        desc = p.get("result", {}).get("description", "")
        items.append(f'<li><span class="inn">{inn_str}</span><span class="txt">{escape(desc)}</span></li>')
    if not items: return ""
    return f'<h3>Key Plays</h3><ul class="plays">{"".join(items)}</ul>'

def render_nlc_standings(standings_data, tmap):
    recs = []
    for rec in standings_data["records"]:
        if rec["division"]["id"] == 205:
            recs = rec["teamRecords"]
            break
    rows = []
    for tr in recs:
        tid = tr["team"]["id"]
        cls = ' class="cubs"' if tid == CUBS_ID else ''
        name = team_name(tmap, tid)
        l10 = next((s for s in tr["records"]["splitRecords"] if s["type"]=="lastTen"), {})
        l10_str = f'{l10.get("wins",0)}-{l10.get("losses",0)}' if l10 else "–"
        gb = tr.get("gamesBack", "-")
        if gb in ("-", "0.0"): gb = "&mdash;"
        rows.append(f'<tr{cls}><td class="team">{escape(name)}</td>'
                    f'<td class="num">{tr["wins"]}</td><td class="num">{tr["losses"]}</td>'
                    f'<td class="num pct">{tr["winningPercentage"]}</td>'
                    f'<td class="num">{gb}</td><td class="num">{l10_str}</td></tr>')
    return f"""<div class="tblwrap"><table class="data standings">
    <thead><tr><th>Team</th><th style="text-align:right">W</th><th style="text-align:right">L</th>
    <th style="text-align:right">PCT</th><th style="text-align:right">GB</th>
    <th style="text-align:right">L10</th></tr></thead>
    <tbody>{"".join(rows)}</tbody></table></div>"""

def render_injuries(injuries):
    # group by status
    groups = {}
    for p in injuries:
        code = p.get("status",{}).get("code","")
        desc = p.get("status",{}).get("description","")
        groups.setdefault(desc, []).append(p)
    # preferred ordering
    pri = {"Injured 10-Day":1,"Injured 15-Day":2,"Injured 60-Day":3,"Reassigned to Minors":9}
    order = sorted(groups.keys(), key=lambda k: pri.get(k, 5))
    out = []
    for k in order:
        if k == "Reassigned to Minors":  # skip these from injury list
            continue
        players = groups[k]
        if not players: continue
        dds = "".join(f'<dd>{escape(p["position"]["abbreviation"])} <strong>{escape(p["person"]["fullName"])}</strong></dd>'
                      for p in players)
        out.append(f'<dt>{escape(k)}</dt>{dds}')
    if not out:
        return '<p class="slang"><em>Clean bill of health.</em></p>'
    return f'<dl class="transac">{"".join(out)}</dl>'

DOME_VENUES = {12: "Dome", 32: "Retractable Roof", 680: "Retractable Roof",
               2889: "Retractable Roof", 14: "Retractable Roof",
               2394: "Retractable Roof", 19: "Retractable Roof"}

def fetch_pitcher_line(pid):
    """Fetch a pitcher's season stats. Returns formatted string or empty."""
    if not pid: return ""
    try:
        data = fetch(f"/people/{pid}/stats", stats="season", season="2026", group="pitching")
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

def render_next_games(next_games, tmap, today_lineup=None, today_series="", today_opp_info=""):
    cards = []
    for idx, g in enumerate(next_games):
        home_id = g["teams"]["home"]["team"]["id"]
        away_id = g["teams"]["away"]["team"]["id"]
        is_home = home_id == CUBS_ID
        opp_id = away_id if is_home else home_id
        opp_ab = abbr(tmap, opp_id)
        vs = f"vs {opp_ab}" if is_home else f"at {opp_ab}"
        try:
            gd = datetime.strptime(g["gameDate"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            ct = gd.astimezone(CT)
            day_str = ct.strftime("%a, %b ") + str(ct.day)
            time_str = ct.strftime("%-I:%M") + " CT"
        except Exception:
            day_str = g.get("officialDate","")
            time_str = ""
        cubs_side = "home" if is_home else "away"
        opp_side = "away" if is_home else "home"
        cubs_prob = g["teams"][cubs_side].get("probablePitcher", {})
        opp_prob = g["teams"][opp_side].get("probablePitcher", {})
        cubs_p = cubs_prob.get("fullName", "TBD") if cubs_prob else "TBD"
        opp_p = opp_prob.get("fullName", "TBD") if opp_prob else "TBD"

        # Pitcher season stats
        cubs_pid = cubs_prob.get("id") if cubs_prob else None
        opp_pid = opp_prob.get("id") if opp_prob else None
        cubs_line = fetch_pitcher_line(cubs_pid)
        opp_line = fetch_pitcher_line(opp_pid)

        # Broadcasts
        bc = g.get("broadcasts", [])
        tvs = [escape(b["name"]) for b in bc if b.get("type") == "TV" and b.get("language","en") == "en"]
        radios = [escape(b["name"]) for b in bc if b.get("type") in ("AM","FM") and b.get("language","en") == "en"]
        bc_html = ""
        if tvs:
            bc_html += f'<div class="nx-bc"><span class="nx-bc-tag">TV</span> {" &middot; ".join(tvs)}</div>'
        if radios:
            bc_html += f'<div class="nx-bc"><span class="nx-bc-tag">Radio</span> {" &middot; ".join(radios)}</div>'

        # Venue + dome/weather
        venue = g.get("venue", {})
        venue_name = venue.get("name", "")
        vid = venue.get("id")
        dome_label = ""
        if vid in DOME_VENUES:
            dome_label = f'<span class="nx-dome">{DOME_VENUES[vid]}</span>'

        # Weather (only for today's game — first card)
        wx_html = ""
        if idx == 0:
            wx = fetch_weather_for_venue(venue)
            if wx:
                temp, cond, wind_str, wrigley = wx
                wx_html = f'<div class="nx-wx">{temp}°F &middot; {escape(cond)} &middot; {wind_str}'
                if wrigley:
                    wx_html += f' <span class="nx-wrigley">&mdash; {escape(wrigley)}</span>'
                wx_html += '</div>'
            elif vid in DOME_VENUES:
                wx_html = '<div class="nx-wx">72°F &middot; Climate controlled</div>'

        pitcher_html = ""
        if cubs_p != "TBD":
            pitcher_html += f'<div class="nx-pitcher"><span class="nx-side">Cubs</span> {escape(cubs_p)}'
            if cubs_line: pitcher_html += f'<div class="nx-pline">{cubs_line}</div>'
            pitcher_html += '</div>'
        if opp_p != "TBD":
            pitcher_html += f'<div class="nx-pitcher"><span class="nx-side">{escape(opp_ab)}</span> {escape(opp_p)}'
            if opp_line: pitcher_html += f'<div class="nx-pline">{opp_line}</div>'
            pitcher_html += '</div>'

        # Today's game extras (first card only)
        extras_html = ""
        lineup_html = ""
        if idx == 0:
            meta_parts = []
            if today_opp_info:
                meta_parts.append(f'<span class="nx-opp-rec">{escape(opp_ab)}: {escape(today_opp_info)}</span>')
            if today_series:
                meta_parts.append(f'<span class="nx-series">Season series: {escape(today_series)}</span>')
            if meta_parts:
                extras_html = f'<div class="nx-meta">{" &middot; ".join(meta_parts)}</div>'

            if today_lineup:
                cubs_side = "home" if is_home else "away"
                cubs_lu = today_lineup.get(cubs_side, [])
                if cubs_lu:
                    lu_items = "".join(
                        f'<span class="lu-slot"><span class="lu-pos">{escape(p["pos"])}</span> {escape(p["name"].split()[-1])}</span>'
                        for p in cubs_lu
                    )
                    lineup_html = f'<div class="nx-lineup"><span class="nx-lu-label">Lineup</span><div class="lu-slots">{lu_items}</div></div>'

        cards.append(f"""<div class="nx-card{' nx-today' if idx == 0 else ''}">
        <div class="nx-head">
          <div class="nx-day">{day_str} &middot; {vs}</div>
          <div class="nx-time">{time_str}</div>
        </div>
        <div class="nx-venue">{escape(venue_name)} {dome_label}</div>
        {extras_html}
        {pitcher_html}
        {lineup_html}
        {bc_html}
        {wx_html}
      </div>""")
    return f'<div class="next-games">{"".join(cards)}</div>'

def render_hot_cold(hitters_data, pitchers_data):
    # Hitters: sort by OPS, take top 4 & bottom 3 of qualified (>=10 PA)
    def extract_hitters(roster_data):
        out = []
        for p in roster_data.get("roster", []):
            if p.get("position", {}).get("abbreviation") == "P":
                continue
            stats_list = p["person"].get("stats", [])
            if not stats_list or not stats_list[0].get("splits"):
                continue
            st = stats_list[0]["splits"][0]["stat"]
            if st.get("plateAppearances", 0) < 10:
                continue
            out.append({"player": p["person"]["fullName"], "stat": st})
        return out

    qual = extract_hitters(hitters_data)
    def get_ops(s):
        try: return float(s["stat"].get("ops","0") or "0")
        except: return 0.0
    qual.sort(key=get_ops, reverse=True)
    hot = qual[:4]
    cold = list(reversed(qual[-3:])) if len(qual) >= 4 else []

    def hitter_li(s):
        name = s["player"]
        st = s["stat"]
        avg = st.get("avg","."); hr = st.get("homeRuns",0); ops = st.get("ops","-")
        return f'<li><span class="n">{escape(name.split()[-1])}</span><span class="s">{avg} / {hr} HR / {ops} OPS</span></li>'
    hot_html = "".join(hitter_li(s) for s in hot)
    cold_html = "".join(hitter_li(s) for s in cold)

    # Pitchers: hot = best ERA w/ >=2 IP; cold = worst
    def extract_pitchers(roster_data):
        out = []
        for p in roster_data.get("roster", []):
            if p.get("position", {}).get("abbreviation") != "P":
                continue
            stats_list = p["person"].get("stats", [])
            if not stats_list or not stats_list[0].get("splits"):
                continue
            st = stats_list[0]["splits"][0]["stat"]
            if float(st.get("inningsPitched", "0") or 0) < 2:
                continue
            out.append({"player": p["person"]["fullName"], "stat": st})
        return out

    p_qual = extract_pitchers(pitchers_data)
    def era(s):
        try: return float(s["stat"].get("era","99") or 99)
        except: return 99
    p_qual.sort(key=era)
    p_hot = p_qual[:3]
    p_cold = list(reversed(p_qual[-2:])) if len(p_qual) >= 3 else []
    def pitcher_li(s):
        name = s["player"]
        st = s["stat"]
        era_v = st.get("era","-"); k = st.get("strikeOuts",0); ip = st.get("inningsPitched","0")
        return f'<li><span class="n">{escape(name.split()[-1])}</span><span class="s">{ip} IP &middot; {era_v} ERA &middot; {k} K</span></li>'
    phot_html = "".join(pitcher_li(s) for s in p_hot)
    pcold_html = "".join(pitcher_li(s) for s in p_cold)

    return f"""
    <div class="two">
      <div class="tempbox hot"><h4>Hitters Heating Up (L7)</h4><ul>{hot_html or '<li><span class="n">&mdash;</span></li>'}</ul></div>
      <div class="tempbox cold"><h4>In the Icebox (L7)</h4><ul>{cold_html or '<li><span class="n">&mdash;</span></li>'}</ul></div>
    </div>
    <div class="two">
      <div class="tempbox hot"><h4>Arms Dealing (L7)</h4><ul>{phot_html or '<li><span class="n">&mdash;</span></li>'}</ul></div>
      <div class="tempbox cold"><h4>In the Doghouse (L7)</h4><ul>{pcold_html or '<li><span class="n">&mdash;</span></li>'}</ul></div>
    </div>
    """

def render_scoreboard_yest(games_y, tmap):
    rows = []
    for g in games_y:
        if g.get("status",{}).get("abstractGameState") != "Final":
            continue
        away_id = g["teams"]["away"]["team"]["id"]
        home_id = g["teams"]["home"]["team"]["id"]
        aa = abbr(tmap, away_id); ha = abbr(tmap, home_id)
        as_ = g["teams"]["away"].get("score",0)
        hs = g["teams"]["home"].get("score",0)
        winner_ab = aa if as_ > hs else ha
        wp = g.get("decisions",{}).get("winner",{}).get("fullName","").split()[-1] if g.get("decisions") else ""
        pk = g.get("gamePk", "")
        rows.append(f'<tr class="scorecard-link" data-href="scorecard/?game={pk}">'
                    f'<td class="name">{escape(aa)}</td><td class="num">{as_}</td>'
                    f'<td class="name">{escape(ha)}</td><td class="num">{hs}</td>'
                    f'<td class="num w">{escape(winner_ab)}</td><td>{escape(wp)}</td></tr>')
    return f"""<div class="tblwrap"><table class="data">
    <thead><tr><th>Away</th><th></th><th>Home</th><th></th><th>W</th><th>WP</th></tr></thead>
    <tbody>{"".join(rows)}</tbody></table></div>"""

def render_all_divisions(standings_data, tmap):
    # build div → teams map
    by_div = {}
    for rec in standings_data["records"]:
        by_div[rec["division"]["id"]] = rec["teamRecords"]

    def div_table(div_id, name):
        recs = by_div.get(div_id, [])
        rows = []
        for tr in recs:
            tid = tr["team"]["id"]
            cls = ' class="cubs"' if tid == CUBS_ID else ''
            tn = team_name(tmap, tid)
            gb = tr.get("gamesBack","-")
            if gb in ("-","0.0"): gb = "&mdash;"
            rows.append(f'<tr{cls}><td class="team">{escape(tn)}</td>'
                        f'<td class="num">{tr["wins"]}</td><td class="num">{tr["losses"]}</td>'
                        f'<td class="num">{gb}</td></tr>')
        return f"""<h4>{name}</h4><div class="tblwrap"><table class="data standings">
        <thead><tr><th>Team</th><th style="text-align:right">W</th><th style="text-align:right">L</th>
        <th style="text-align:right">GB</th></tr></thead>
        <tbody>{"".join(rows)}</tbody></table></div>"""

    al = "".join(div_table(did, n) for did, n in DIV_ORDER[:3])
    nl = "".join(div_table(did, n) for did, n in DIV_ORDER[3:])
    return f'<div class="two"><div>{al}</div><div>{nl}</div></div>'

def render_leaders(lh, lp, tmap):
    CAT_LABELS = {
        "battingAverage":"AVG","homeRuns":"HR","runsBattedIn":"RBI",
        "stolenBases":"SB","onBasePlusSlugging":"OPS",
        "earnedRunAverage":"ERA","strikeOuts":"K","whip":"WHIP",
        "saves":"SV","wins":"W"
    }
    def rows(data, cats_order):
        lkp = {c["leaderCategory"]: c for c in data.get("leagueLeaders", [])}
        out = []
        for cat in cats_order:
            c = lkp.get(cat)
            if not c or not c.get("leaders"): continue
            L = c["leaders"][0]
            name = L["person"]["fullName"]
            tid = L["team"]["id"]
            ab = abbr(tmap, tid)
            val = L["value"]
            out.append(f'<tr><td>{CAT_LABELS.get(cat,cat)}</td><td class="name">{escape(name)} ({escape(ab)})</td><td class="num">{escape(str(val))}</td></tr>')
        return "".join(out)
    hit = rows(lh, ["battingAverage","homeRuns","runsBattedIn","stolenBases","onBasePlusSlugging"])
    pit = rows(lp, ["earnedRunAverage","strikeOuts","whip","saves","wins"])
    return f"""<div class="two">
    <div><h4>Batting</h4><div class="tblwrap"><table class="data">
    <thead><tr><th>Cat</th><th>Leader</th><th style="text-align:right">#</th></tr></thead>
    <tbody>{hit}</tbody></table></div></div>
    <div><h4>Pitching</h4><div class="tblwrap"><table class="data">
    <thead><tr><th>Cat</th><th>Leader</th><th style="text-align:right">#</th></tr></thead>
    <tbody>{pit}</tbody></table></div></div>
    </div>"""

def render_slate_today(games_t, tmap):
    cards = []
    for g in games_t:
        aid = g["teams"]["away"]["team"]["id"]; hid = g["teams"]["home"]["team"]["id"]
        aa = abbr(tmap, aid); ha = abbr(tmap, hid)
        try:
            gd = datetime.strptime(g["gameDate"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            ct = gd.astimezone(CT)
            time_str = ct.strftime("%-I:%M") + " CT"
        except Exception:
            time_str = ""
        ap = g["teams"]["away"].get("probablePitcher",{}) or {}
        hp = g["teams"]["home"].get("probablePitcher",{}) or {}
        ap_n = ap.get("fullName","TBD").split()[-1] if ap else "TBD"
        hp_n = hp.get("fullName","TBD").split()[-1] if hp else "TBD"
        # Broadcast info
        bc = g.get("broadcasts", [])
        bc_parts = []
        for b in bc:
            if b.get("type") == "TV" and b.get("language","en") == "en":
                bc_parts.append(escape(b.get("name","")))
        bc_str = f'<div class="bc">{" · ".join(bc_parts)}</div>' if bc_parts else ""
        cards.append(f"""<div class="g" data-gpk="{g['gamePk']}">
        <div class="matchup">{aa} @ {ha}</div>
        <div class="time">{time_str}</div>
        <div class="probs">{escape(ap_n)} vs {escape(hp_n)}</div>
        {bc_str}
      </div>""")
    return f'<div class="slate">{"".join(cards)}</div>'

def render_nlc_rivals(games_y, tmap):
    NLC = {112:"Cubs", 158:"Brewers", 138:"Cardinals", 113:"Reds", 134:"Pirates"}
    cards = []
    for g in games_y:
        aid = g["teams"]["away"]["team"]["id"]; hid = g["teams"]["home"]["team"]["id"]
        tid = None
        if aid in NLC and aid != CUBS_ID: tid = aid
        elif hid in NLC and hid != CUBS_ID: tid = hid
        else: continue
        name = NLC[tid]
        is_away = tid == aid
        opp_id = hid if is_away else aid
        opp_ab = abbr(tmap, opp_id)
        my_score = g["teams"]["away" if is_away else "home"].get("score",0)
        opp_score = g["teams"]["home" if is_away else "away"].get("score",0)
        won = my_score > opp_score
        result = f'{"W" if won else "L"} {my_score}-{opp_score} {"at" if is_away else "vs"} {opp_ab}'
        wp = g.get("decisions",{}).get("winner",{}).get("fullName","") if g.get("decisions") else ""
        lp = g.get("decisions",{}).get("loser",{}).get("fullName","") if g.get("decisions") else ""
        blurb = f'WP: {wp}' + (f' · LP: {lp}' if lp else '')
        cards.append(f"""<div class="rival">
        <h4>{escape(name)} <span class="score">{result}</span></h4>
        <p>{escape(blurb)}</p>
      </div>""")
    if not cards:
        cards.append('<div class="rival"><h4>NL Central Rivals</h4><p>All off yesterday.</p></div>')
    return f'<div class="rivals">{"".join(cards)}</div>'

def detect_league_news(games_y, standings_data, tmap):
    """Scan yesterday's games and standings for notable events."""
    items = []
    for g in games_y:
        if g.get("status", {}).get("abstractGameState") != "Final":
            continue
        if "linescore" not in g:
            continue
        away_id = g["teams"]["away"]["team"]["id"]
        home_id = g["teams"]["home"]["team"]["id"]
        away_ab = abbr(tmap, away_id)
        home_ab = abbr(tmap, home_id)
        away_name = team_name(tmap, away_id)
        home_name = team_name(tmap, home_id)
        away_score = g["teams"]["away"].get("score", 0)
        home_score = g["teams"]["home"].get("score", 0)
        innings = g.get("linescore", {}).get("innings", [])
        num_inn = len(innings)
        margin = abs(away_score - home_score)
        total = away_score + home_score
        decisions = g.get("decisions", {}) or {}
        wp = decisions.get("winner", {}).get("fullName", "")
        lp = decisions.get("loser", {}).get("fullName", "")
        wp_last = wp.split()[-1] if wp else ""

        home_won = home_score > away_score
        winner_name = home_name if home_won else away_name
        loser_name = away_name if home_won else home_name
        winner_score = max(away_score, home_score)
        loser_score = min(away_score, home_score)

        is_extras = num_inn > 9

        # Walk-off: home wins and scored in bottom of final inning
        is_walkoff = False
        if home_won and innings:
            last = innings[-1]
            last_home = last.get("home", {}).get("runs")
            if last_home is not None and str(last_home) not in ("", "0"):
                is_walkoff = True

        is_shutout = (away_score == 0 or home_score == 0) and total > 0
        is_blowout = margin >= 8
        is_high_scoring = total >= 15

        if is_walkoff:
            extras_note = f" in {num_inn} innings" if is_extras else ""
            body = f"{escape(home_name)} walked off the {escape(loser_name)}, {winner_score}-{loser_score}{extras_note}."
            if wp_last:
                body += f" {escape(wp_last)} got the win."
            items.append({"type": "walkoff", "priority": 1, "headline": "Walk-Off", "body": body})
        elif is_extras:
            body = f"{escape(winner_name)} outlasted the {escape(loser_name)} in {num_inn} innings, {winner_score}-{loser_score}."
            items.append({"type": "extras", "priority": 2, "headline": f"{num_inn} Innings", "body": body})
        elif is_shutout and is_blowout:
            body = f"{escape(winner_name)} blanked the {escape(loser_name)}, {winner_score}-0."
            if wp_last:
                body += f" {escape(wp_last)} earned the win."
            items.append({"type": "shutout", "priority": 3, "headline": "Shutout", "body": body})
        elif is_shutout:
            body = f"{escape(winner_name)} shut out the {escape(loser_name)}, {winner_score}-0."
            if wp_last:
                body += f" {escape(wp_last)} earned the win."
            items.append({"type": "shutout", "priority": 3, "headline": "Shutout", "body": body})
        elif is_blowout:
            body = f"{escape(winner_name)} routed the {escape(loser_name)}, {winner_score}-{loser_score}."
            items.append({"type": "blowout", "priority": 4, "headline": "Rout", "body": body})
        elif is_high_scoring:
            venue = g.get("venue", {}).get("name", "")
            loc = f" at {escape(venue)}" if venue else ""
            body = f"A slugfest{loc}: {escape(away_ab)} {away_score}, {escape(home_ab)} {home_score} ({total} combined runs)."
            items.append({"type": "high_scoring", "priority": 5, "headline": "Slugfest", "body": body})

    # Streaks from standings (W7+ or L7+)
    for rec in standings_data.get("records", []):
        for tr in rec["teamRecords"]:
            streak = tr.get("streak", {})
            num = streak.get("streakNumber", 0)
            stype = streak.get("streakType", "")
            if num >= 7:
                tid = tr["team"]["id"]
                tname = team_name(tmap, tid)
                if stype == "wins":
                    body = f"The {escape(tname)} have won {num} straight."
                    headline = f"W{num}"
                else:
                    body = f"The {escape(tname)} have dropped {num} in a row."
                    headline = f"L{num}"
                items.append({"type": "streak", "priority": 6, "headline": headline, "body": body})

    items.sort(key=lambda x: x["priority"])
    return items[:6]


def render_league_news_from_items(items):
    """Render pre-computed league news items as blurb cards."""
    if not items:
        return '<p><em class="slang">A quiet night around the league.</em></p>'
    blurbs = []
    for it in items:
        blurbs.append(
            f'<div class="blurb">'
            f'<span class="blurb-tag {escape(it["type"])}">{escape(it["headline"])}</span>'
            f'<p class="blurb-text">{it["body"]}</p>'
            f'</div>'
        )
    return f'<div class="news-wire">{"".join(blurbs)}</div>'


def render_cubs_leaders(cubs_season_data):
    """Render Cubs team leaders table: AVG, OBP, HR, RBI, SB."""
    players = []
    for p in cubs_season_data.get("roster", []):
        if p.get("position", {}).get("abbreviation") == "P":
            continue
        stats_list = p["person"].get("stats", [])
        if not stats_list or not stats_list[0].get("splits"):
            continue
        st = stats_list[0]["splits"][0]["stat"]
        pa = st.get("plateAppearances", 0)
        if pa < 10:
            continue
        players.append({
            "name": p["person"]["fullName"],
            "pos": p.get("position", {}).get("abbreviation", ""),
            "avg": st.get("avg", ".000"),
            "obp": st.get("obp", ".000"),
            "hr": st.get("homeRuns", 0),
            "rbi": st.get("rbi", 0),
            "sb": st.get("stolenBases", 0),
            "pa": pa,
        })

    cats = [
        ("AVG", "avg", lambda x: float(x["avg"] or 0), True),
        ("OBP", "obp", lambda x: float(x["obp"] or 0), True),
        ("HR", "hr", lambda x: x["hr"], False),
        ("RBI", "rbi", lambda x: x["rbi"], False),
        ("SB", "sb", lambda x: x["sb"], False),
    ]
    rows = []
    for label, key, sort_fn, is_pct in cats:
        if not players:
            continue
        leader = max(players, key=sort_fn)
        val = leader[key]
        if is_pct:
            display = val if isinstance(val, str) else f"{val:.3f}"
        else:
            display = str(val)
        name = leader["name"].split()[-1]
        pos = leader["pos"]
        rows.append(
            f'<tr><td>{label}</td>'
            f'<td class="name">{escape(name)} <span style="color:var(--paper-mute);font-size:10px">{escape(pos)}</span></td>'
            f'<td class="num">{escape(display)}</td></tr>'
        )

    if not rows:
        return '<p class="slang"><em>Season stats not yet available.</em></p>'

    return f"""<div class="tblwrap"><table class="data">
    <thead><tr><th>Cat</th><th>Leader</th><th style="text-align:right">#</th></tr></thead>
    <tbody>{"".join(rows)}</tbody></table></div>"""


def render_minors(minors_data, prospects=None):
    """Render minor league affiliate results with prospect tagging."""
    if prospects is None:
        prospects = {}
    cards = []
    for m in minors_data:
        aff = m["aff"]
        g = m["game"]
        box = m["boxscore"]
        if not g or g.get("status", {}).get("abstractGameState") != "Final":
            cards.append(f"""<div class="lvl" data-lvl="{aff['level']}">
        <div class="aff">{escape(aff['name'])}</div>
        <div class="res"><em>No game / not final</em></div>
      </div>""")
            continue

        away_id = g["teams"]["away"]["team"]["id"]
        home_id = g["teams"]["home"]["team"]["id"]
        is_home = home_id == aff["id"]
        away_name = g["teams"]["away"]["team"].get("teamName", "???")
        home_name = g["teams"]["home"]["team"].get("teamName", "???")
        away_score = g["teams"]["away"].get("score", 0)
        home_score = g["teams"]["home"].get("score", 0)
        won = (is_home and home_score > away_score) or (not is_home and away_score > home_score)
        my_score = home_score if is_home else away_score
        opp_score = away_score if is_home else home_score
        opp_name = away_name if is_home else home_name
        wl = "W" if won else "L"
        wl_cls = "w" if won else "l"
        vs_at = "vs" if is_home else "at"

        # Extract top performer from boxscore
        note = ""
        if box:
            our_side = "home" if is_home else "away"
            players = box.get("teams", {}).get(our_side, {}).get("players", {})
            best_hitter = None
            best_score = -1
            best_pitcher = None
            best_p_score = -1
            for pid_key, p in players.items():
                player_id = p.get("person", {}).get("id", 0)
                # Hitter
                bs = p.get("stats", {}).get("batting", {})
                if bs and bs.get("atBats", 0) > 0:
                    h = bs.get("hits", 0)
                    hr = bs.get("homeRuns", 0)
                    rbi = bs.get("rbi", 0)
                    sc = h + 3 * hr + rbi
                    if sc > best_score:
                        best_score = sc
                        best_hitter = (p["person"]["fullName"], bs, player_id)
                # Pitcher
                ps = p.get("stats", {}).get("pitching", {})
                if ps and ps.get("inningsPitched") not in (None, "0.0", 0):
                    ip = float(ps.get("inningsPitched", "0") or 0)
                    k = ps.get("strikeOuts", 0)
                    er = ps.get("earnedRuns", 0)
                    psc = ip * 2 + k - er * 3
                    if psc > best_p_score:
                        best_p_score = psc
                        best_pitcher = (p["person"]["fullName"], ps, player_id)
            def prospect_badge(player_id):
                p = prospects.get(player_id)
                if p:
                    return f' <span class="prospect-tag">#{p["rank"]}</span>'
                return ""

            parts = []
            if best_hitter:
                name, s, pid = best_hitter
                line = f"{s.get('hits',0)}-{s.get('atBats',0)}"
                extras = []
                if s.get("homeRuns", 0): extras.append(f"{s['homeRuns']} HR")
                if s.get("rbi", 0): extras.append(f"{s['rbi']} RBI")
                if extras: line += ", " + ", ".join(extras)
                parts.append(f"<strong>{escape(name.split()[-1])}</strong>{prospect_badge(pid)} {line}")
            if best_pitcher:
                name, s, pid = best_pitcher
                parts.append(f"<strong>{escape(name.split()[-1])}</strong>{prospect_badge(pid)} {s.get('inningsPitched','?')} IP, {s.get('earnedRuns',0)} ER, {s.get('strikeOuts',0)} K")
            note = ". ".join(parts) + "." if parts else ""

        cards.append(f"""<div class="lvl {wl_cls}" data-lvl="{aff['level']}">
        <div class="aff">{escape(aff['name'])}</div>
        <div class="res"><span class="{wl_cls}">{wl} {my_score}&ndash;{opp_score}</span> {vs_at} {escape(opp_name)}</div>
        {f'<div class="note">{note}</div>' if note else ''}
      </div>""")

    if not cards:
        return '<p class="slang"><em>No affiliate games yesterday.</em></p>'

    wins = sum(1 for m in minors_data if m["game"] and m["game"].get("status",{}).get("abstractGameState")=="Final"
               and ((m["game"]["teams"]["home"]["team"]["id"]==m["aff"]["id"] and m["game"]["teams"]["home"].get("score",0)>m["game"]["teams"]["away"].get("score",0))
               or (m["game"]["teams"]["away"]["team"]["id"]==m["aff"]["id"] and m["game"]["teams"]["away"].get("score",0)>m["game"]["teams"]["home"].get("score",0))))
    finals = sum(1 for m in minors_data if m["game"] and m["game"].get("status",{}).get("abstractGameState")=="Final")
    losses = finals - wins
    tag = f"{wins}&ndash;{losses}" if finals > 0 else "No games"

    # Prospect tracker — scan all boxscores for watched prospects
    prospect_rows = []
    if prospects:
        # Build lookup: player_id -> (batting_stats, pitching_stats, aff_name)
        found = {}
        for m in minors_data:
            box = m.get("boxscore")
            g = m.get("game")
            if not box or not g or g.get("status", {}).get("abstractGameState") != "Final":
                continue
            aff = m["aff"]
            is_home = g["teams"]["home"]["team"]["id"] == aff["id"]
            side = "home" if is_home else "away"
            players = box.get("teams", {}).get(side, {}).get("players", {})
            for pid_key, p in players.items():
                player_id = p.get("person", {}).get("id", 0)
                if player_id in prospects:
                    bs = p.get("stats", {}).get("batting", {})
                    ps = p.get("stats", {}).get("pitching", {})
                    has_bat = bs and bs.get("atBats", 0) > 0
                    has_pitch = ps and ps.get("inningsPitched") not in (None, "0.0", 0)
                    if has_bat or has_pitch:
                        found[player_id] = (bs, ps, aff["level"])

        for pid, pr in sorted(prospects.items(), key=lambda x: x[1]["rank"]):
            rank = pr["rank"]
            name = escape(pr["name"])
            pos = escape(pr["position"])
            level = escape(pr["level"])
            if pid in found:
                bs, ps, game_level = found[pid]
                stat_parts = []
                if bs and bs.get("atBats", 0) > 0:
                    line = f'{bs.get("hits",0)}-{bs.get("atBats",0)}'
                    extras = []
                    if bs.get("runs", 0): extras.append(f'{bs["runs"]} R')
                    if bs.get("homeRuns", 0): extras.append(f'{bs["homeRuns"]} HR')
                    if bs.get("rbi", 0): extras.append(f'{bs["rbi"]} RBI')
                    if bs.get("baseOnBalls", 0): extras.append(f'{bs["baseOnBalls"]} BB')
                    if bs.get("strikeOuts", 0): extras.append(f'{bs["strikeOuts"]} K')
                    if extras: line += ", " + ", ".join(extras)
                    stat_parts.append(line)
                if ps and ps.get("inningsPitched") not in (None, "0.0", 0):
                    stat_parts.append(f'{ps.get("inningsPitched","?")} IP, {ps.get("earnedRuns",0)} ER, {ps.get("strikeOuts",0)} K')
                stat_str = " &middot; ".join(stat_parts) if stat_parts else "In lineup, no AB"
                prospect_rows.append(
                    f'<div class="prosp-row played">'
                    f'<span class="prosp-rank">#{rank}</span>'
                    f'<span class="prosp-name">{name}</span>'
                    f'<span class="prosp-pos">{pos}</span>'
                    f'<span class="prosp-lvl">{game_level}</span>'
                    f'<span class="prosp-stat">{stat_str}</span>'
                    f'</div>')
            else:
                prospect_rows.append(
                    f'<div class="prosp-row dnp">'
                    f'<span class="prosp-rank">#{rank}</span>'
                    f'<span class="prosp-name">{name}</span>'
                    f'<span class="prosp-pos">{pos}</span>'
                    f'<span class="prosp-lvl">{level}</span>'
                    f'<span class="prosp-stat">DNP</span>'
                    f'</div>')

    prospect_html = ""
    if prospect_rows:
        prospect_html = f'<h3 class="prosp-header">Prospect Watch</h3><div class="prosp-tracker">{"".join(prospect_rows)}</div>'

    return f'<div class="minors">{"".join(cards)}</div>{prospect_html}', tag


def generate_lede(data):
    """Generate a 3-4 sentence editorial lede via Ollama (or Anthropic API)."""
    lede_cache = DATA_DIR / f"lede-{data['today'].isoformat()}.txt"
    if lede_cache.exists():
        cached = lede_cache.read_text(encoding="utf-8").strip()
        if cached:
            return cached

    # Build summary for the prompt
    parts = []
    cg = data.get("cubs_game")
    if cg:
        away = cg["teams"]["away"]["team"].get("name", "?")
        home = cg["teams"]["home"]["team"].get("name", "?")
        asc = cg["teams"]["away"].get("score", 0)
        hsc = cg["teams"]["home"].get("score", 0)
        parts.append(f"Cubs game: {away} {asc}, {home} {hsc}")
    else:
        parts.append("No Cubs game yesterday.")

    cr = data.get("cubs_rec")
    if cr:
        parts.append(f"Cubs record: {cr['wins']}-{cr['losses']}, {cr.get('gamesBack', '?')} GB in NL Central")

    prompt = f"""Write a 3-4 sentence editorial lede for a Cubs fan newspaper called "The Morning Lineup."
Tone: witty, opinionated, knowledgeable — like a beat writer who bleeds Cubbie blue.
Keep it concise and punchy. No cliches. Reference specific details.
Do NOT use any thinking tags or meta-commentary. Just write the paragraph directly.

Today's context:
{chr(10).join(parts)}

Write ONLY the paragraph, nothing else."""

    # Try Ollama first (chat endpoint)
    try:
        body = json.dumps({
            "model": "qwen3:8b-q4_K_M",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 256}
        }).encode()
        req = urllib.request.Request("http://localhost:11434/api/chat",
                                     data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read())
        text = resp.get("message", {}).get("content", "").strip()
        # Clean up: remove thinking tags if present
        import re
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        if text and len(text) > 50:
            # Cache the lede
            DATA_DIR.mkdir(exist_ok=True)
            lede_cache.write_text(text, encoding="utf-8")
            return text
    except Exception as e:
        print(f"  Ollama lede failed: {e}", flush=True)

    # Try Anthropic API as fallback
    api_key = __import__("os").environ.get("ANTHROPIC_API_KEY")
    if api_key:
        try:
            body = json.dumps({
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 256,
                "messages": [{"role": "user", "content": prompt}],
            }).encode()
            req = urllib.request.Request("https://api.anthropic.com/v1/messages",
                                         data=body, method="POST",
                                         headers={
                                             "Content-Type": "application/json",
                                             "x-api-key": api_key,
                                             "anthropic-version": "2023-06-01",
                                         })
            with urllib.request.urlopen(req, timeout=15) as r:
                resp = json.loads(r.read())
            text = resp["content"][0]["text"].strip()
            if text:
                DATA_DIR.mkdir(exist_ok=True)
                lede_cache.write_text(text, encoding="utf-8")
                return text
        except Exception as e:
            print(f"  Anthropic lede failed: {e}", flush=True)

    return ""

def render_lede(lede_text):
    """Render the editorial lede section."""
    if not lede_text:
        return ""
    return f'<div class="lede">{escape(lede_text)}</div>'

def render_scouting_report(scout_data, next_games, tmap):
    """Render Scouting Report — today's pitching matchup deep dive."""
    if not scout_data:
        return ""
    cubs_sp = scout_data.get("cubs_sp")
    opp_sp = scout_data.get("opp_sp")
    if not cubs_sp and not opp_sp:
        return ""

    def _sp_card(sp, side_label):
        if not sp:
            return f'<div class="sp-card"><div class="sp-side">{side_label}</div><div class="sp-name">TBD</div></div>'
        log_rows = []
        for g in sp.get("log", [])[:3]:
            d = g.get("date", "")
            if len(d) >= 10:
                d = d[5:]  # MM-DD
            log_rows.append(
                f'<tr><td>{d}</td><td class="opp">vs {escape(str(g.get("opp","?")))}</td>'
                f'<td class="num">{g.get("ip","?")}</td><td class="num">{g.get("er","?")}</td>'
                f'<td class="num">{g.get("k","?")}</td><td class="num">{g.get("h","?")}</td>'
                f'<td class="num">{g.get("bb","?")}</td></tr>')
        log_html = ""
        if log_rows:
            log_html = f"""<table class="data sp-log">
            <thead><tr><th>Date</th><th>Opp</th><th style="text-align:right">IP</th><th style="text-align:right">ER</th><th style="text-align:right">K</th><th style="text-align:right">H</th><th style="text-align:right">BB</th></tr></thead>
            <tbody>{"".join(log_rows)}</tbody></table>"""
        return f"""<div class="sp-card">
        <div class="sp-side">{side_label}</div>
        <div class="sp-name">{escape(sp.get("name","TBD"))}</div>
        <div class="sp-season">{sp.get("season","")}</div>
        {f'<h4>Last {len(sp.get("log",[]))} Starts</h4>{log_html}' if log_html else ''}
        </div>"""

    # Game context line
    game_ctx = ""
    if next_games:
        tg = next_games[0]
        home_id = tg["teams"]["home"]["team"]["id"]
        away_id = tg["teams"]["away"]["team"]["id"]
        is_home = home_id == CUBS_ID
        opp_abbr = abbr(tmap, away_id if is_home else home_id)
        venue = tg.get("venue", {}).get("name", "")
        time_str = fmt_time_ct(tg.get("gameDate", ""))
        ha = "vs" if is_home else "at"
        game_ctx = f'<div class="scout-ctx"><span>{ha} {opp_abbr} &middot; {time_str}</span><span>{escape(venue)}</span></div>'

    return f"""{game_ctx}
    <div class="matchup-vs">
        {_sp_card(cubs_sp, "Cubs")}
        <div class="vs-divider">VS</div>
        {_sp_card(opp_sp, abbr(tmap, next_games[0]["teams"]["away" if next_games[0]["teams"]["home"]["team"]["id"] == CUBS_ID else "home"]["team"]["id"]) if next_games else "OPP")}
    </div>"""


def render_stretch(cubs_rec):
    """Render The Stretch — season pulse, run differential, splits."""
    if not cubs_rec:
        return '<p class="slang"><em>Season data not yet available.</em></p>'
    cr = cubs_rec
    w, l = cr["wins"], cr["losses"]
    g = w + l
    pct = cr.get("winningPercentage", ".000")
    gb = cr.get("gamesBack", "-")
    if gb in ("-", "0.0"):
        gb = "&mdash;"
    streak = cr.get("streak", {}).get("streakCode", "")
    rank = cr.get("divisionRank", "?")

    # Run differential
    rs = cr.get("runsScored", 0)
    ra = cr.get("runsAllowed", 0)
    rd = cr.get("runDifferential", rs - ra)
    rd_cls = "w" if rd >= 0 else "l"
    rd_str = f"+{rd}" if rd > 0 else str(rd)

    # Pythagorean W-L
    pyth_pct = (rs ** 2) / (rs ** 2 + ra ** 2) if (rs + ra) > 0 else 0.5
    pyth_w = round(pyth_pct * g)
    pyth_l = g - pyth_w

    # Splits from standings
    splits = {}
    for s in cr.get("records", {}).get("splitRecords", []):
        splits[s["type"]] = s

    def _split_row(label, key):
        s = splits.get(key)
        if not s:
            return ""
        sw, sl = s.get("wins", 0), s.get("losses", 0)
        sp = s.get("pct", ".000")
        return f'<div class="split-row"><span class="split-label">{label}</span><span class="split-val">{sw}-{sl}</span><span class="split-pct">{sp}</span></div>'

    split_rows = [
        _split_row("Home", "home"),
        _split_row("Away", "away"),
        _split_row("vs RHP", "right"),
        _split_row("vs LHP", "left"),
        _split_row("1-Run", "oneRun"),
        _split_row("Extras", "extraInning"),
        _split_row("Day", "day"),
        _split_row("Night", "night"),
        _split_row("Last 10", "lastTen"),
        _split_row("Grass", "grass"),
    ]
    split_rows = [r for r in split_rows if r]

    return f"""<div class="pulse-record">
        <span class="pulse-wl">{w}&ndash;{l}</span>
        <span class="pulse-pct">{pct}</span>
        <span class="pulse-gb">{gb} GB</span>
        <span class="pulse-rank">{rank}{_ordinal(rank)} NL Central</span>
        {f'<span class="pulse-streak">{streak}</span>' if streak else ''}
    </div>
    <div class="pulse-diff">
        <div class="diff-label">Run Differential</div>
        <div class="diff-num {rd_cls}">{rd_str}</div>
        <div class="diff-detail">{rs} RS &middot; {ra} RA &middot; Pythag: {pyth_w}-{pyth_l}</div>
    </div>
    <h3>Splits</h3>
    <div class="splits-grid">{"".join(split_rows)}</div>"""


def render_pressbox(injuries, transactions):
    """Render The Pressbox — recent transactions + injuries."""
    # Sort transactions newest-first
    sorted_tx = sorted(transactions, key=lambda t: t.get("effectiveDate", t.get("date", "")), reverse=True)

    tx_rows = []
    for tx in sorted_tx[:10]:
        d = tx.get("effectiveDate", tx.get("date", ""))
        if len(d) >= 10:
            d = d[5:]  # MM-DD
        tc = tx.get("typeCode", "")
        desc = tx.get("description", "")
        type_map = {
            "DIS": ("IL", "il"), "DTD": ("IL", "il"),
            "ACT": ("Activated", "act"),
            "OPT": ("Optioned", "opt"), "OUT": ("Outrighted", "opt"),
            "RCL": ("Recalled", "rcl"),
            "DFA": ("DFA", "il"), "REL": ("Released", "il"),
            "ASG": ("Assigned", "opt"), "SC": ("Status Change", "act"),
            "SFA": ("Signed", "act"), "SGN": ("Signed", "act"),
            "TR": ("Trade", "il"),
        }
        label, cls = type_map.get(tc, (tx.get("typeDesc", tc)[:12], ""))
        tx_rows.append(
            f'<div class="transac-item">'
            f'<span class="transac-date">{d}</span>'
            f'<span class="transac-badge {cls}">{escape(label)}</span>'
            f'<span class="transac-desc">{escape(desc)}</span>'
            f'</div>')

    tx_html = ""
    if tx_rows:
        tx_html = f'<h3>Recent Transactions</h3><div class="transac-list">{"".join(tx_rows)}</div>'
    else:
        tx_html = '<h3>Recent Transactions</h3><p><em class="slang">No roster moves in the last 7 days.</em></p>'

    inj_html = render_injuries(injuries) if injuries else '<p><em>Clean bill of health.</em></p>'

    return f'{tx_html}<h3>Injured List</h3>{inj_html}'


def render_history(history_items):
    """Render This Day in Cubs History."""
    if not history_items:
        return '<p class="idle-msg">No historical entries for today&rsquo;s date.</p>'
    items = []
    for h in history_items[:5]:
        items.append(f'<li><span class="inn">{h["year"]}</span><span class="txt">{escape(h["text"])}</span></li>')
    return f'<ul class="plays">{"".join(items)}</ul>'


# ─── page assembly ──────────────────────────────────────────────────────────

CSS = STYLE_FILE.read_text(encoding="utf-8")


def page(data):
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
            cubs_record_str += f' &middot; {dr}{suffix} NL Central'

    line_out = render_line_score(data["cubs_game"], data["tmap"], data.get("cubs_game_date"), y)
    if isinstance(line_out, tuple):
        line_score_html, summary_tag = line_out
    else:
        line_score_html, summary_tag = line_out, "No game"

    three_stars = render_three_stars(data["boxscore"], data["cubs_game"], data["tmap"])
    key_plays = render_key_plays(data["plays"], data["cubs_game"], data["tmap"])
    cubs_pk = data["cubs_game"]["gamePk"] if data["cubs_game"] else None
    scorecard_embed = ""
    if cubs_pk:
        scorecard_embed = f'''<details class="scorecard-expand">
      <summary><span class="scorecard-toggle">View Full Scorecard</span></summary>
      <iframe src="scorecard/?game={cubs_pk}&amp;embed=1" class="scorecard-frame" loading="lazy" frameborder="0"></iframe>
    </details>'''
    nlc_stand = render_nlc_standings(data["standings"], data["tmap"])
    next_games_html = render_next_games(data["next_games"], data["tmap"],
                                       data.get("today_lineup"), data.get("today_series", ""),
                                       data.get("today_opp_info", ""))
    hot_cold_html = render_hot_cold(data["cubs_hitters"], data["cubs_pitchers"])
    scoreboard_yest = render_scoreboard_yest(data["games_y"], data["tmap"])
    all_div = render_all_divisions(data["standings"], data["tmap"])
    leaders_html = render_leaders(data["leaders_hit"], data["leaders_pit"], data["tmap"])
    slate_html = render_slate_today(data["games_t"], data["tmap"])
    rivals_html = render_nlc_rivals(data["games_y"], data["tmap"])
    news_items = detect_league_news(data["games_y"], data["standings"], data["tmap"])
    news_count = len(news_items)
    league_news_html = render_league_news_from_items(news_items)

    # Minors
    minors_out = render_minors(data["minors"], data.get("prospects", {}))
    if isinstance(minors_out, tuple):
        minors_html, minors_tag = minors_out
    else:
        minors_html, minors_tag = minors_out, "No games"

    # Cubs team leaders
    cubs_leaders_html = render_cubs_leaders(data["cubs_season"])

    # New sections
    scout_html = render_scouting_report(data.get("scout_data", {}), data["next_games"], data["tmap"])
    stretch_html = render_stretch(data["cubs_rec"])
    pressbox_html = render_pressbox(data["injuries"], data.get("transactions", []))
    history_html = render_history(data["history"])

    # Editorial lede
    lede_text = generate_lede(data)
    lede_html = render_lede(lede_text)

    vol_no = (t - date(t.year, 1, 1)).days + 1
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
  <div class="kicker">
    <span>Vol. {t.year - 2023} &middot; <span class="vol">No. {vol_no:03d}</span></span>
    <span>A Daily Dispatch from the Friendly Confines &amp; Beyond</span>
    <span>Est. 2024</span>
  </div>
  <h1>
    <span class="the">The</span>
    <span class="lineup">Morning <em style="font-style:italic">Lineup</em></span>
  </h1>
  <div class="dek">
    <span class="item"><span class="label">{t.strftime("%a")}</span><span class="val">{t.strftime("%b")} {t.day}, {t.year}</span></span>
    <span class="item"><span class="label">Cubs</span><span class="rec">{cubs_record_str}</span></span>
    <span class="item pill">Data: MLB Stats API</span>
  </div>
</header>
{lede_html}
<div class="wrap">
  <nav class="toc" aria-label="Sections">
    <div class="title">Sections</div>
    <ol>
      <li><a href="#cubs">The Cubs</a></li>
      {'<li><a href="#scout">Scouting Report</a></li>' if scout_html else ''}
      <li><a href="#pulse">The Stretch</a></li>
      <li><a href="#pressbox">The Pressbox</a></li>
      <li><a href="#farm">Down on the Farm</a></li>
      <li><a href="#today">Today&rsquo;s Slate</a></li>
      <li><a href="#nlc">NL Central</a></li>
      <li><a href="#league">Around the League</a></li>
      <li><a href="#history">Cubs History</a></li>
    </ol>
  </nav>

  <main>

  <div id="live-game"></div>

  <section id="cubs" open>
    <summary>
      <span class="num">01</span>
      <span class="h">The Cubs</span>
      <span class="tag">{escape(summary_tag)}</span>
      <span class="chev">&#9656;</span>
    </summary>
    {line_score_html}
    <h3>Three Stars</h3>
    {three_stars}
    {key_plays}
    {scorecard_embed}
    <h3>Cubs Leaders</h3>
    {cubs_leaders_html}
    <h3>Next Games</h3>
    {next_games_html}
    <h3>Form Guide (Last 7 Days)</h3>
    {hot_cold_html}
  </section>

  {f"""<section id="scout" open>
    <summary>
      <span class="num">02</span>
      <span class="h">Scouting Report</span>
      <span class="tag">Today&rsquo;s Matchup</span>
      <span class="chev">&#9656;</span>
    </summary>
    {scout_html}
  </section>""" if scout_html else ''}

  <section id="pulse" open>
    <summary>
      <span class="num">{"03" if scout_html else "02"}</span>
      <span class="h">The Stretch</span>
      <span class="tag">Season Pulse</span>
      <span class="chev">&#9656;</span>
    </summary>
    {stretch_html}
  </section>

  <section id="pressbox" open>
    <summary>
      <span class="num">{"04" if scout_html else "03"}</span>
      <span class="h">The Pressbox</span>
      <span class="tag">Roster &middot; Transactions</span>
      <span class="chev">&#9656;</span>
    </summary>
    {pressbox_html}
  </section>

  <section id="farm" open>
    <summary>
      <span class="num">{"05" if scout_html else "04"}</span>
      <span class="h">Down on the Farm</span>
      <span class="tag">{minors_tag}</span>
      <span class="chev">&#9656;</span>
    </summary>
    {minors_html}
  </section>

  <section id="today" open>
    <summary>
      <span class="num">{"06" if scout_html else "05"}</span>
      <span class="h">Today&rsquo;s Slate</span>
      <span class="tag">{t.strftime("%a %b ")}{t.day}</span>
      <span class="chev">&#9656;</span>
    </summary>
    {slate_html}
  </section>

  <section id="nlc" open>
    <summary>
      <span class="num">{"07" if scout_html else "06"}</span>
      <span class="h">NL Central</span>
      <span class="tag">Rivals &middot; Yesterday</span>
      <span class="chev">&#9656;</span>
    </summary>
    <h3>Standings</h3>
    {nlc_stand}
    <h3>Rivals &middot; Yesterday</h3>
    {rivals_html}
  </section>

  <section id="league" open>
    <summary>
      <span class="num">{"08" if scout_html else "07"}</span>
      <span class="h">Around the League</span>
      <span class="tag">{y.strftime("%b ")}{y.day} &middot; {news_count} Note{"s" if news_count != 1 else ""}</span>
      <span class="chev">&#9656;</span>
    </summary>
    <h3>News Wire</h3>
    {league_news_html}
    <h3>Yesterday&rsquo;s Scoreboard</h3>
    {scoreboard_yest}
    <a href="scorecard/" class="scorecard-btn">Browse All Scorecards &rsaquo;</a>
    <h3>Standings &mdash; All Six Divisions</h3>
    {all_div}
    <h3>League Leaders</h3>
    {leaders_html}
  </section>

  <section id="history" open>
    <summary>
      <span class="num">{"09" if scout_html else "08"}</span>
      <span class="h">This Day in Cubs History</span>
      <span class="tag">{t.strftime("%b ")}{t.day}</span>
      <span class="chev">&#9656;</span>
    </summary>
    {history_html}
  </section>

  </main>
</div>

<footer class="foot">
  <span>The Morning Lineup &middot; <span class="flag">A Friendly Confines Broadsheet</span></span>
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

if __name__ == "__main__":
    print("Fetching MLB data …", flush=True)
    data = load_all()
    save_data_ledger(data)
    print("Rendering page …", flush=True)
    html = page(data)
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT} ({len(html):,} bytes)")
