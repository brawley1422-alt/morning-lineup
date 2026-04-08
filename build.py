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
HISTORY_FILE = Path(__file__).parent / "history.json"

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
        hydrate="team,probablePitcher",
    )
    next_games = []
    for dd in sched_next.get("dates", []):
        for g in dd["games"]:
            next_games.append(g)
    next_games = next_games[:3]

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

    # This Day in Cubs History
    history = []
    if HISTORY_FILE.exists():
        try:
            hdata = json.loads(HISTORY_FILE.read_text())
            key = today.strftime("%m-%d")
            history = hdata.get(key, [])
        except Exception:
            history = []

    return {
        "today": today, "yest": yest, "season": season,
        "tmap": tmap,
        "games_y": games_y, "games_t": games_t,
        "standings": stand, "cubs_rec": cubs_rec,
        "next_games": next_games,
        "cubs_game": cubs_game, "cubs_game_date": cubs_game_date,
        "boxscore": boxscore, "plays": plays,
        "injuries": injuries,
        "cubs_hitters": cubs_hitters, "cubs_pitchers": cubs_pitchers,
        "cubs_season": cubs_season,
        "leaders_hit": leaders_hit, "leaders_pit": leaders_pit,
        "minors": minors, "history": history,
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

def render_next_games(next_games, tmap):
    cards = []
    for g in next_games:
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
        vs_line = f"{cubs_p.split()[-1] if cubs_p!='TBD' else 'TBD'} vs {opp_p.split()[-1] if opp_p!='TBD' else 'TBD'}"
        cards.append(f"""<div class="g">
        <div class="day">{day_str} &middot; {vs}</div>
        <div class="vs">{escape(vs_line)}</div>
        <div class="prob">{escape(cubs_p)} &middot; {escape(opp_p)}</div>
        <div class="time">{time_str}</div>
      </div>""")
    return f'<div class="upcoming">{"".join(cards)}</div>'

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


def render_minors(minors_data):
    """Render minor league affiliate results."""
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
            for pid, p in players.items():
                # Hitter
                bs = p.get("stats", {}).get("batting", {})
                if bs and bs.get("atBats", 0) > 0:
                    h = bs.get("hits", 0)
                    hr = bs.get("homeRuns", 0)
                    rbi = bs.get("rbi", 0)
                    sc = h + 3 * hr + rbi
                    if sc > best_score:
                        best_score = sc
                        best_hitter = (p["person"]["fullName"], bs)
                # Pitcher
                ps = p.get("stats", {}).get("pitching", {})
                if ps and ps.get("inningsPitched") not in (None, "0.0", 0):
                    ip = float(ps.get("inningsPitched", "0") or 0)
                    k = ps.get("strikeOuts", 0)
                    er = ps.get("earnedRuns", 0)
                    psc = ip * 2 + k - er * 3
                    if psc > best_p_score:
                        best_p_score = psc
                        best_pitcher = (p["person"]["fullName"], ps)
            parts = []
            if best_hitter:
                name, s = best_hitter
                line = f"{s.get('hits',0)}-{s.get('atBats',0)}"
                extras = []
                if s.get("homeRuns", 0): extras.append(f"{s['homeRuns']} HR")
                if s.get("rbi", 0): extras.append(f"{s['rbi']} RBI")
                if extras: line += ", " + ", ".join(extras)
                parts.append(f"<strong>{escape(name.split()[-1])}</strong> {line}")
            if best_pitcher:
                name, s = best_pitcher
                parts.append(f"<strong>{escape(name.split()[-1])}</strong> {s.get('inningsPitched','?')} IP, {s.get('earnedRuns',0)} ER, {s.get('strikeOuts',0)} K")
            note = ". ".join(parts) + "." if parts else ""

        cards.append(f"""<div class="lvl" data-lvl="{aff['level']}">
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

    return f'<div class="minors">{"".join(cards)}</div>', tag


def render_history(history_items):
    """Render This Day in Cubs History."""
    if not history_items:
        return ""
    items = []
    for h in history_items[:3]:
        items.append(f'<li><span class="inn">{h["year"]}</span><span class="txt">{escape(h["text"])}</span></li>')
    return f'<h3>This Day in Cubs History</h3><ul class="plays">{"".join(items)}</ul>'


# ─── page assembly ──────────────────────────────────────────────────────────

CSS = r"""
:root{
  --ink:#0d0f14;--ink-2:#141823;--ink-3:#1c2230;
  --paper:#ece4d0;--paper-dim:#c9bfa6;--paper-mute:#8b836d;
  --rule:#2a3142;--rule-hi:#3a4360;
  --cubs-blue:#0E3386;--cubs-blue-hi:#2a56c4;
  --cubs-red:#CC3433;--cubs-red-hi:#e8544f;
  --gold:#c9a24a;--gold-dim:#8a6f32;
  --win:#6ea86a;--loss:#c0554f;
  --serif:"Playfair Display",Georgia,serif;
  --body:"Lora","Source Serif Pro",Georgia,serif;
  --cond:"Oswald","Bebas Neue",Impact,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
  --maxw:1180px;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--ink);color:var(--paper)}
body{font-family:var(--body);font-size:16px;line-height:1.55;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;
  background:radial-gradient(1200px 600px at 10% -10%,rgba(14,51,134,.22),transparent 60%),radial-gradient(900px 500px at 110% 10%,rgba(204,52,51,.12),transparent 55%),linear-gradient(180deg,#0a0c12 0%,#0d0f14 40%,#0b0d12 100%);
  background-attachment:fixed;position:relative;overflow-x:hidden;}
body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:1;opacity:.06;mix-blend-mode:overlay;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0.6 0'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>");}
a{color:var(--gold);text-decoration:none;border-bottom:1px dotted var(--gold-dim)}
a:hover{color:var(--paper);border-bottom-color:var(--paper)}
a:focus-visible,summary:focus-visible{outline:2px solid var(--gold);outline-offset:3px;border-radius:2px}
.masthead{position:relative;z-index:2;border-bottom:6px double var(--paper);padding:28px 20px 18px;max-width:var(--maxw);margin:0 auto;}
.masthead .kicker{display:flex;justify-content:space-between;align-items:baseline;font-family:var(--cond);letter-spacing:.22em;text-transform:uppercase;font-size:11px;color:var(--paper-mute);border-bottom:1px solid var(--rule);padding-bottom:8px;margin-bottom:14px;}
.masthead .kicker .vol{color:var(--gold)}
.masthead h1{font-family:var(--serif);font-weight:900;font-style:italic;font-size:clamp(44px,9vw,108px);line-height:.9;margin:0;letter-spacing:-.01em;text-shadow:0 2px 0 rgba(0,0,0,.4);}
.masthead h1 .the{display:block;font-size:.28em;font-style:normal;font-weight:600;letter-spacing:.4em;color:var(--gold);margin-bottom:4px;text-transform:uppercase;}
.masthead h1 .lineup{background:linear-gradient(180deg,var(--paper) 0%,var(--paper-dim) 100%);-webkit-background-clip:text;background-clip:text;color:transparent;}
.masthead .dek{display:flex;flex-wrap:wrap;gap:14px 26px;align-items:center;margin-top:14px;padding-top:12px;border-top:1px solid var(--rule);font-family:var(--cond);text-transform:uppercase;letter-spacing:.14em;font-size:12px;}
.masthead .dek .item{display:flex;gap:8px;align-items:center}
.masthead .dek .label{color:var(--paper-mute)}
.masthead .dek .val{color:var(--paper)}
.masthead .dek .rec{color:var(--gold);font-weight:600}
.masthead .dek .pill{display:inline-block;padding:3px 8px;border:1px solid var(--rule-hi);border-radius:2px;background:rgba(14,51,134,.25);}
.wrap{position:relative;z-index:2;max-width:var(--maxw);margin:0 auto;padding:0 20px 80px;display:grid;grid-template-columns:220px 1fr;gap:36px;}
@media (max-width:900px){.wrap{grid-template-columns:1fr;gap:0;padding:0 16px 60px}}
.toc{position:sticky;top:14px;align-self:start;padding-top:24px}
.toc .title{font-family:var(--cond);text-transform:uppercase;letter-spacing:.2em;font-size:11px;color:var(--paper-mute);border-bottom:1px solid var(--rule);padding-bottom:8px;margin-bottom:10px;}
.toc ol{list-style:none;padding:0;margin:0;counter-reset:toc}
.toc li{counter-increment:toc;border-bottom:1px dashed var(--rule);padding:7px 0}
.toc li::before{content:counter(toc,decimal-leading-zero);font-family:var(--mono);font-size:10px;color:var(--gold-dim);margin-right:10px;}
.toc a{color:var(--paper-dim);border:none;font-family:var(--cond);text-transform:uppercase;letter-spacing:.08em;font-size:13px;}
.toc a:hover,.toc a.active{color:var(--cubs-red-hi)}
@media (max-width:900px){.toc{position:static;padding:14px 0 8px;margin-bottom:8px;border-bottom:1px solid var(--rule)}.toc ol{display:flex;flex-wrap:wrap;gap:4px 6px}.toc li{border:none;padding:0}.toc li::before{display:none}.toc a{display:inline-block;padding:6px 10px;border:1px solid var(--rule);background:var(--ink-2);border-radius:2px;font-size:11px;}}
main{min-width:0}
section{margin:28px 0 36px;scroll-margin-top:10px}
section > summary,section > .sechead{list-style:none;cursor:pointer;display:flex;align-items:baseline;gap:14px;border-top:4px solid var(--paper);border-bottom:1px solid var(--rule);padding:12px 0 10px;margin-bottom:18px;font-family:var(--cond);text-transform:uppercase;}
section > summary::-webkit-details-marker{display:none}
section > summary .num{font-family:var(--mono);font-size:11px;color:var(--gold);letter-spacing:.1em;border:1px solid var(--gold-dim);padding:2px 6px;border-radius:2px;}
section > summary .h{font-size:clamp(22px,4vw,34px);font-weight:700;letter-spacing:.04em;color:var(--paper);flex:1;line-height:1;}
section > summary .tag{font-size:11px;letter-spacing:.22em;color:var(--paper-mute);}
section > summary .chev{font-family:var(--mono);font-size:18px;color:var(--gold);transition:transform .2s;}
section[open] > summary .chev{transform:rotate(90deg)}
section h3{font-family:var(--cond);text-transform:uppercase;letter-spacing:.12em;font-size:13px;color:var(--cubs-red-hi);margin:22px 0 10px;border-bottom:1px dotted var(--rule-hi);padding-bottom:6px;}
section h4{font-family:var(--cond);text-transform:uppercase;letter-spacing:.1em;font-size:12px;color:var(--gold);margin:16px 0 8px;}
p{margin:0 0 12px}
em.slang{font-style:italic;color:var(--paper-dim)}
.scoreboard{background:linear-gradient(180deg,#0a1528 0%,#08101e 100%);border:1px solid var(--cubs-blue);border-radius:3px;padding:18px 18px 14px;box-shadow:inset 0 0 0 1px rgba(255,255,255,.03),0 10px 30px -10px rgba(14,51,134,.5);position:relative;overflow:hidden;}
.scoreboard::before{content:"";position:absolute;inset:0;pointer-events:none;background:repeating-linear-gradient(90deg,transparent 0 22px,rgba(255,255,255,.018) 22px 23px);}
.scoreboard .meta{display:flex;justify-content:space-between;align-items:center;font-family:var(--cond);text-transform:uppercase;letter-spacing:.14em;font-size:11px;color:var(--paper-mute);margin-bottom:10px;}
.scoreboard .meta .fin{color:var(--gold);border:1px solid var(--gold-dim);padding:2px 8px;border-radius:2px;font-weight:600;}
.scoreboard table{width:100%;border-collapse:collapse;font-family:var(--mono)}
.scoreboard th,.scoreboard td{padding:7px 6px;text-align:center;font-size:13px;border-bottom:1px solid rgba(255,255,255,.06);}
.scoreboard th{font-weight:500;color:var(--paper-mute);font-size:10px;letter-spacing:.1em;}
.scoreboard td.team{text-align:left;font-family:var(--cond);font-size:16px;letter-spacing:.08em;text-transform:uppercase;color:var(--paper);font-weight:600;padding-left:10px;width:80px;}
.scoreboard td.rhe{font-weight:700;color:var(--gold);font-size:15px}
.scoreboard tr.won td.team{color:var(--cubs-red-hi)}
.scoreboard tr.won td.rhe{color:var(--paper)}
.scoreboard .pitchers{display:flex;flex-wrap:wrap;gap:18px;margin-top:12px;padding-top:10px;border-top:1px dashed var(--rule-hi);font-size:13px;}
.scoreboard .pitchers span strong{font-family:var(--cond);text-transform:uppercase;letter-spacing:.1em;font-size:10px;color:var(--paper-mute);margin-right:6px;}
.scoreboard .pitchers .w{color:var(--win)}
.scoreboard .pitchers .l{color:var(--loss)}
.scoreboard .pitchers .s{color:var(--gold)}
.stars{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:14px 0;}
@media (max-width:640px){.stars{grid-template-columns:1fr}}
.star{background:var(--ink-2);border:1px solid var(--rule);padding:12px 14px;border-radius:2px;position:relative;border-left:3px solid var(--gold);}
.star .rank{font-family:var(--serif);font-style:italic;font-weight:900;font-size:42px;color:var(--gold);line-height:1;position:absolute;top:8px;right:14px;opacity:.25;}
.star .name{font-family:var(--cond);text-transform:uppercase;letter-spacing:.06em;font-size:16px;font-weight:600;color:var(--paper);}
.star .line{font-family:var(--mono);font-size:12px;color:var(--paper-dim);margin-top:4px}
.star .note{font-size:13px;color:var(--paper-dim);margin-top:6px;font-style:italic}
.tblwrap{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:10px 0 14px}
table.data{width:100%;border-collapse:collapse;font-family:var(--mono);font-size:12.5px;min-width:480px;}
table.data th{text-align:left;font-weight:500;color:var(--paper-mute);font-size:10px;letter-spacing:.12em;text-transform:uppercase;border-bottom:1px solid var(--rule-hi);padding:8px 10px 6px;background:rgba(255,255,255,.015);position:sticky;top:0;}
table.data td{padding:7px 10px;border-bottom:1px solid var(--rule);color:var(--paper-dim);}
table.data td.name{color:var(--paper);font-family:var(--cond);letter-spacing:.04em;font-size:14px;text-transform:uppercase}
table.data td.num{text-align:right;color:var(--gold)}
table.data tr:hover td{background:rgba(201,162,74,.04)}
table.data td.w{color:var(--win)}
table.data td.l{color:var(--loss)}
table.standings td.team{color:var(--paper);font-family:var(--cond);font-size:14px;text-transform:uppercase;letter-spacing:.04em}
table.standings tr.cubs td{background:rgba(14,51,134,.18)}
table.standings tr.cubs td.team{color:var(--cubs-red-hi)}
table.standings td.pct{font-family:var(--mono);color:var(--gold)}
ul.plays{list-style:none;padding:0;margin:8px 0}
ul.plays li{display:grid;grid-template-columns:48px 1fr;gap:12px;padding:10px 0;border-bottom:1px dashed var(--rule);}
ul.plays .inn{font-family:var(--cond);font-weight:700;letter-spacing:.06em;color:var(--gold);font-size:13px;text-transform:uppercase;border-right:2px solid var(--gold-dim);padding-right:12px;text-align:right;}
ul.plays .txt{font-size:14px;color:var(--paper-dim)}
ul.plays .txt strong{color:var(--paper);font-weight:500}
.two{display:grid;grid-template-columns:1fr 1fr;gap:22px}
@media (max-width:720px){.two{grid-template-columns:1fr;gap:0}}
.tempbox{border:1px solid var(--rule);padding:12px 14px;border-radius:2px;background:var(--ink-2)}
.tempbox.hot{border-top:3px solid var(--cubs-red)}
.tempbox.cold{border-top:3px solid #4a7fc4}
.tempbox h4{margin-top:0}
.tempbox ul{list-style:none;padding:0;margin:0}
.tempbox li{display:flex;justify-content:space-between;gap:10px;padding:6px 0;border-bottom:1px dotted var(--rule);font-size:13px;}
.tempbox li:last-child{border-bottom:none}
.tempbox .n{font-family:var(--cond);text-transform:uppercase;letter-spacing:.04em;color:var(--paper)}
.tempbox .s{font-family:var(--mono);font-size:11px;color:var(--gold)}
.upcoming{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:12px 0}
@media (max-width:640px){.upcoming{grid-template-columns:1fr}}
.upcoming .g{background:var(--ink-2);border:1px solid var(--rule);padding:10px 12px;border-radius:2px;border-left:3px solid var(--cubs-blue-hi);}
.upcoming .day{font-family:var(--cond);text-transform:uppercase;letter-spacing:.14em;font-size:10px;color:var(--paper-mute)}
.upcoming .vs{font-family:var(--cond);text-transform:uppercase;font-size:15px;color:var(--paper);margin:2px 0;letter-spacing:.06em}
.upcoming .prob{font-family:var(--mono);font-size:11px;color:var(--paper-dim)}
.upcoming .time{font-family:var(--mono);font-size:11px;color:var(--gold);margin-top:4px}
dl.transac{margin:8px 0;font-size:13px}
dl.transac dt{font-family:var(--cond);text-transform:uppercase;letter-spacing:.08em;font-size:11px;color:var(--cubs-red-hi);margin-top:10px;}
dl.transac dd{margin:3px 0 0;color:var(--paper-dim)}
.minors{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px}
@media (max-width:720px){.minors{grid-template-columns:repeat(2,1fr)}}
@media (max-width:420px){.minors{grid-template-columns:1fr}}
.minors .lvl{background:var(--ink-2);border:1px solid var(--rule);padding:10px 12px;border-radius:2px;position:relative;}
.minors .lvl::after{content:attr(data-lvl);position:absolute;top:6px;right:8px;font-family:var(--mono);font-size:9px;color:var(--gold-dim);letter-spacing:.1em;}
.minors .aff{font-family:var(--cond);text-transform:uppercase;font-size:14px;color:var(--paper);letter-spacing:.06em}
.minors .res{font-family:var(--mono);font-size:12px;margin-top:4px}
.minors .res .w{color:var(--win)}
.minors .res .l{color:var(--loss)}
.minors .note{font-size:11.5px;color:var(--paper-dim);margin-top:6px;line-height:1.4}
.rivals{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
@media (max-width:640px){.rivals{grid-template-columns:1fr}}
.rival{background:var(--ink-2);border:1px solid var(--rule);padding:12px 14px;border-radius:2px;border-left:3px solid var(--gold-dim);}
.rival h4{margin:0 0 4px;color:var(--paper)}
.rival .score{font-family:var(--mono);font-size:12px;color:var(--gold)}
.rival p{font-size:13px;margin:6px 0 0;color:var(--paper-dim)}
.news-wire{display:flex;flex-direction:column;gap:10px;margin:12px 0 18px}
.blurb{background:var(--ink-2);border:1px solid var(--rule);border-left:3px solid var(--cubs-red);
  padding:10px 14px;border-radius:2px;display:flex;gap:12px;align-items:baseline;}
.blurb-tag{font-family:var(--cond);text-transform:uppercase;letter-spacing:.12em;font-size:10px;
  color:var(--cubs-red-hi);border:1px solid var(--cubs-red);padding:2px 8px;border-radius:2px;
  white-space:nowrap;font-weight:600;flex-shrink:0;}
.blurb-tag.extras,.blurb-tag.streak{color:var(--gold);border-color:var(--gold-dim)}
.blurb-tag.shutout{color:var(--paper-mute);border-color:var(--rule-hi)}
.blurb-tag.blowout{color:var(--cubs-red-hi);border-color:var(--cubs-red)}
.blurb-tag.high_scoring{color:var(--gold);border-color:var(--gold-dim)}
.blurb-text{font-size:14px;color:var(--paper-dim);margin:0}
@media (max-width:640px){.blurb{flex-direction:column;gap:6px}}
.slate{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
@media (max-width:640px){.slate{grid-template-columns:1fr}}
.slate .g{background:var(--ink-2);border:1px solid var(--rule);padding:10px 12px;border-radius:2px;display:grid;grid-template-columns:1fr auto;gap:4px 10px;align-items:center;}
.slate .matchup{font-family:var(--cond);text-transform:uppercase;font-size:13px;color:var(--paper);letter-spacing:.04em}
.slate .time{font-family:var(--mono);font-size:11px;color:var(--gold);text-align:right}
.slate .probs{font-family:var(--mono);font-size:10.5px;color:var(--paper-mute);grid-column:1/-1}
.slate .bc{font-family:var(--mono);font-size:9.5px;color:var(--paper-mute);grid-column:1/-1;opacity:.7}
footer.foot{max-width:var(--maxw);margin:40px auto 0;padding:20px;border-top:6px double var(--paper);position:relative;z-index:2;font-family:var(--cond);text-transform:uppercase;letter-spacing:.18em;font-size:10px;color:var(--paper-mute);display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;}
footer.foot .flag{color:var(--gold)}
#live-game{margin:0 0 28px}
.live-widget{background:linear-gradient(180deg,#0a1528,#08101e);border:2px solid var(--cubs-blue);border-radius:3px;padding:20px 24px;box-shadow:inset 0 0 0 1px rgba(255,255,255,.03),0 10px 30px -10px rgba(14,51,134,.5);position:relative;overflow:hidden}
.live-widget::before{content:"";position:absolute;inset:0;pointer-events:none;background:repeating-linear-gradient(90deg,transparent 0 22px,rgba(255,255,255,.018) 22px 23px)}
.live-badge{display:inline-flex;align-items:center;gap:6px;font-family:var(--cond);text-transform:uppercase;letter-spacing:.2em;font-size:11px;color:var(--cubs-red-hi);margin-bottom:12px}
.live-badge .dot{width:8px;height:8px;background:var(--cubs-red);border-radius:50%;animation:pulse 1.5s ease-in-out infinite}
.live-badge .flag{color:var(--gold);font-size:13px}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.live-widget .score-row{display:flex;justify-content:center;align-items:center;gap:18px;font-family:var(--cond);font-size:clamp(28px,6vw,48px);font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin:8px 0 14px}
.live-widget .team-abbr{min-width:2.6em;text-align:center}
.live-widget .runs{color:var(--gold);font-family:var(--mono)}
.live-widget .score-sep{color:var(--paper-mute);font-size:.5em}
.live-widget .situation{display:flex;flex-wrap:wrap;gap:10px 20px;align-items:center;justify-content:center;font-family:var(--mono);font-size:12px;color:var(--paper-dim);padding:10px 0;border-top:1px dashed var(--rule-hi);margin:10px 0 0}
.live-widget .count{display:flex;gap:10px;align-items:center}
.live-widget .count-label{color:var(--paper-mute);font-size:10px;margin-right:2px}
.live-widget .count-val{color:var(--gold);font-weight:600}
.live-widget .diamond{display:block}
.live-widget .live-matchup{text-align:center;font-family:var(--body);font-size:13px;color:var(--paper-dim);margin-top:10px}
.live-widget .live-matchup strong{color:var(--paper);font-weight:500}
.live-widget .last-play{text-align:center;font-size:13px;color:var(--paper-mute);font-style:italic;margin-top:8px;padding-top:8px;border-top:1px dotted var(--rule)}
.live-widget.final .live-badge{color:var(--paper-mute)}
.live-widget.preview .live-badge{color:var(--gold)}
.live-widget.preview .score-row{font-size:clamp(20px,4vw,32px)}
.live-widget.idle{border-color:var(--rule);opacity:.7}
.idle-msg{font-family:var(--cond);text-transform:uppercase;letter-spacing:.14em;font-size:12px;color:var(--paper-mute);text-align:center;padding:10px 0}
.g-live{border-color:var(--cubs-blue) !important;box-shadow:0 0 8px rgba(14,51,134,.3)}
.g-live .time{font-size:13px}
.slate-live{color:var(--gold);font-family:var(--mono);font-weight:700}
.slate-inn{color:var(--cubs-red-hi);font-family:var(--cond);text-transform:uppercase;letter-spacing:.1em;font-size:10px}
.g-final .time{font-size:13px}
.slate-final{color:var(--paper-dim);font-family:var(--mono);font-weight:600}
.scorecard-expand{margin:16px 0}
.scorecard-expand summary{cursor:pointer;list-style:none;display:inline-block}
.scorecard-expand summary::-webkit-details-marker{display:none}
.scorecard-toggle{font-family:var(--cond);font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--gold);border:1px solid var(--gold-dim);padding:5px 14px;border-radius:3px;transition:background .15s,color .15s}
.scorecard-expand[open] .scorecard-toggle{background:var(--gold-dim);color:var(--ink)}
.scorecard-expand summary:hover .scorecard-toggle{background:var(--gold-dim);color:var(--ink)}
.scorecard-frame{width:100%;min-height:600px;border:none;margin-top:12px;border-radius:3px}
tr.scorecard-link{cursor:pointer;transition:background .12s}
tr.scorecard-link:hover{background:rgba(201,162,74,.1)}
tr.scorecard-link:hover td{color:var(--gold) !important}
.scorecard-btn{display:inline-flex;align-items:center;gap:6px;font-family:var(--cond);font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--gold);border:1px solid var(--gold-dim);padding:6px 16px;border-radius:3px;text-decoration:none;transition:background .15s,color .15s;margin:12px 0}
.scorecard-btn:hover{background:var(--gold-dim);color:var(--ink)}
"""

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
    injuries_html = render_injuries(data["injuries"])
    next_games_html = render_next_games(data["next_games"], data["tmap"])
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
    minors_out = render_minors(data["minors"])
    if isinstance(minors_out, tuple):
        minors_html, minors_tag = minors_out
    else:
        minors_html, minors_tag = minors_out, "No games"

    # Cubs team leaders
    cubs_leaders_html = render_cubs_leaders(data["cubs_season"])

    # History
    history_html = render_history(data["history"])

    vol_no = (t - date(t.year, 1, 1)).days + 1
    filed = datetime.now(tz=CT).strftime("%m/%d/%y %H:%M CT")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0d0f14">
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

<div class="wrap">
  <nav class="toc" aria-label="Sections">
    <div class="title">Sections</div>
    <ol>
      <li><a href="#cubs">The Cubs</a></li>
      <li><a href="#today">Today&rsquo;s Slate</a></li>
      <li><a href="#farm">Down on the Farm</a></li>
      <li><a href="#nlc">NL Central</a></li>
      <li><a href="#league">Around the League</a></li>
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
    <div class="two">
      <div>
        <h3>Cubs Leaders</h3>
        {cubs_leaders_html}
      </div>
      <div>
        <h3>Injuries &amp; Roster</h3>
        {injuries_html}
      </div>
    </div>
    <h3>Next Games</h3>
    {next_games_html}
    <h3>Form Guide (Last 7 Days)</h3>
    {hot_cold_html}
  </section>

  <section id="today" open>
    <summary>
      <span class="num">02</span>
      <span class="h">Today&rsquo;s Slate</span>
      <span class="tag">{t.strftime("%a %b ")}{t.day}</span>
      <span class="chev">&#9656;</span>
    </summary>
    {slate_html}
  </section>

  <section id="farm" open>
    <summary>
      <span class="num">03</span>
      <span class="h">Down on the Farm</span>
      <span class="tag">{minors_tag}</span>
      <span class="chev">&#9656;</span>
    </summary>
    {minors_html}
  </section>

  <section id="nlc" open>
    <summary>
      <span class="num">04</span>
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
      <span class="num">05</span>
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

  {f'<section id="history" open><summary><span class="num">06</span><span class="h">This Day in Cubs History</span><span class="chev">&#9656;</span></summary>{history_html}</section>' if history_html else ''}

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
</script>

</body>
</html>"""

# ─── main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Fetching MLB data …", flush=True)
    data = load_all()
    print("Rendering page …", flush=True)
    html = page(data)
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT} ({len(html):,} bytes)")
