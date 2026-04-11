"""The {Team} headline section.

Combines six sub-renders: line score, three stars, key plays, scorecard
embed, team leaders, next games, form guide. Returns (html, summary_tag)
because the page envelope uses summary_tag for the section header badge.

fetch_pitcher_line and fetch_weather_for_venue are pulled in via a deferred
import inside render() — see plan Decision 13. The deferred import is
safe because build.py is fully loaded by the time this render runs, and
the fresh `build` module (distinct from __main__) is loaded once and
cached.
"""
from datetime import datetime, timezone
from html import escape

try:
    from zoneinfo import ZoneInfo
    _CT = ZoneInfo("America/Chicago")
except (ImportError, KeyError):
    from datetime import timedelta
    _CT = timezone(timedelta(hours=-5))


def _abbr(tmap, team_id):
    return tmap.get(team_id, {}).get("abbreviation", "???")


def _fmt_time_ct(iso_z):
    dt = datetime.strptime(iso_z, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    ct = dt.astimezone(_CT)
    return ct.strftime("%-I:%M") + " CT"


def _render_line_score(game, tmap, team_id, team_name, game_date=None, yest=None):
    if not game:
        return (f'<p class="slang"><em>No completed {team_name} game in the last week.</em></p>', "&mdash;")
    away_id = game["teams"]["away"]["team"]["id"]
    home_id = game["teams"]["home"]["team"]["id"]
    away_ab = _abbr(tmap, away_id)
    home_ab = _abbr(tmap, home_id)
    away_full = game["teams"]["away"]["team"].get("name", away_ab)
    home_full = game["teams"]["home"]["team"].get("name", home_ab)
    # Shorten "Chicago Cubs" → "Chicago" etc. for the linescore row label.
    away_label = away_full.rsplit(" ", 1)[0] if " " in away_full else away_full
    home_label = home_full.rsplit(" ", 1)[0] if " " in home_full else home_full
    away_score = game["teams"]["away"].get("score", 0)
    home_score = game["teams"]["home"].get("score", 0)
    cubs_won = (away_id == team_id and away_score > home_score) or \
               (home_id == team_id and home_score > away_score)
    innings = list(game["linescore"].get("innings", []))
    max_inn = max(len(innings), 9)
    while len(innings) < 9:
        innings.append({"away": {"runs": ""}, "home": {"runs": ""}})
    away_tot = game["linescore"]["teams"]["away"]
    home_tot = game["linescore"]["teams"]["home"]

    def row(label, tid, innings_side, totals):
        cells = ''.join(
            f'<td>{"—" if i.get(innings_side, {}).get("runs") in (None,"") else i[innings_side].get("runs",0)}</td>'
            for i in innings
        )
        is_winner = (tid == away_id and away_score > home_score) or (tid == home_id and home_score > away_score)
        row_cls = ' class="win-row"' if is_winner else ''
        rhe_cls = ' class="rhe-total gold"' if is_winner else ' class="rhe-total"'
        return (f'<tr{row_cls}><td>{escape(label)}</td>{cells}'
                f'<td{rhe_cls}>{totals["runs"]}</td>'
                f'<td{rhe_cls}>{totals["hits"]}</td>'
                f'<td{rhe_cls}>{totals["errors"]}</td></tr>')

    inn_hdrs = ''.join(f'<th>{i+1}</th>' for i in range(len(innings)))
    venue = game.get("venue", {}).get("name", "")
    status = game.get("status", {}).get("detailedState", "Final")
    final_label = "Final"
    if len(innings) > 9:
        final_label = f"Final / {len(innings)}"
    try:
        start_time = _fmt_time_ct(game["gameDate"])
    except Exception:
        start_time = ""

    decisions = game.get("decisions", {}) or {}
    wp = decisions.get("winner", {}).get("fullName", "")
    lp = decisions.get("loser", {}).get("fullName", "")
    sv = decisions.get("save", {}).get("fullName", "")

    wp_bits = []
    if wp: wp_bits.append(f'<span><span class="lbl">WP</span>{escape(wp)}</span>')
    if lp: wp_bits.append(f'<span><span class="lbl">LP</span>{escape(lp)}</span>')
    if sv: wp_bits.append(f'<span><span class="lbl">SV</span>{escape(sv)}</span>')
    wp_line_html = f'<div class="wp-line">{"".join(wp_bits)}</div>' if wp_bits else ""

    # Result badge — W/L in persona colors, score, inning count.
    if cubs_won:
        team_score = away_score if away_id == team_id else home_score
        opp_score = home_score if away_id == team_id else away_score
        result_badge = f'<span class="result win">W {team_score}&ndash;{opp_score}</span>'
    else:
        team_score = away_score if away_id == team_id else home_score
        opp_score = home_score if away_id == team_id else away_score
        result_badge = f'<span class="result loss">L {team_score}&ndash;{opp_score}</span>'

    summary_tag = f'W {away_score}-{home_score} at {home_ab}' if (away_id == team_id and cubs_won) else \
                  f'L {away_score}-{home_score} at {home_ab}' if away_id == team_id else \
                  f'W {home_score}-{away_score} vs {away_ab}' if cubs_won else \
                  f'L {home_score}-{away_score} vs {away_ab}'

    date_note = ""
    if game_date and yest and game_date != yest:
        date_note = f" &middot; {game_date.strftime('%a %b ')}{game_date.day}"
    html = f"""
    <div class="game-result" aria-label="Line score">
      <div class="game-status">
        <span>{escape(venue)} &middot; {start_time}{date_note} &middot; {final_label}</span>
        {result_badge}
      </div>
      <table class="linescore">
        <thead><tr><th></th>{inn_hdrs}<th class="rhe">R</th><th class="rhe">H</th><th class="rhe">E</th></tr></thead>
        <tbody>
          {row(away_label, away_id, 'away', away_tot)}
          {row(home_label, home_id, 'home', home_tot)}
        </tbody>
      </table>
      {wp_line_html}
    </div>
    """
    return html, summary_tag


def _render_three_stars(boxscore, game, tmap, team_id):
    if not boxscore or not game:
        return '<div class="three-stars"><div class="stars-head"><h3 class="h">Three Stars</h3><span class="tag">&#9733; &#9733; &#9733;</span></div><p class="slang"><em>Three stars unavailable.</em></p></div>'
    cubs_side = "away" if game["teams"]["away"]["team"]["id"] == team_id else "home"
    players = boxscore["teams"][cubs_side]["players"]
    hitters = []
    for pid, p in players.items():
        stats = p.get("stats", {}).get("batting", {})
        if not stats or stats.get("atBats", 0) == 0: continue
        h = stats.get("hits", 0); d = stats.get("doubles", 0); t = stats.get("triples", 0)
        hr = stats.get("homeRuns", 0); rbi = stats.get("rbi", 0); sb = stats.get("stolenBases", 0)
        bb = stats.get("baseOnBalls", 0); r = stats.get("runs", 0)
        score = h + d + 2 * t + 3 * hr + rbi + sb + 0.5 * bb + 0.5 * r
        hitters.append((score, p, stats))
    hitters.sort(key=lambda x: -x[0])
    pitchers = []
    for pid, p in players.items():
        ps = p.get("stats", {}).get("pitching", {})
        if not ps or ps.get("inningsPitched") in (None, "0.0", 0): continue
        ip = float(ps.get("inningsPitched", "0.0"))
        er = ps.get("earnedRuns", 0); k = ps.get("strikeOuts", 0)
        pitchers.append((ip * 2 + k - er * 3, p, ps))
    pitchers.sort(key=lambda x: -x[0])

    def _pos(player_dict):
        return (player_dict.get("position") or {}).get("abbreviation", "")

    stars = []
    if pitchers:
        p, ps = pitchers[0][1], pitchers[0][2]
        line = f"{ps.get('inningsPitched')} IP &middot; {ps.get('hits',0)} H &middot; {ps.get('earnedRuns',0)} ER &middot; {ps.get('strikeOuts',0)} K"
        stars.append((p['person']['fullName'], line, _pos(p) or "P", p['person'].get('id')))
    if hitters:
        p, s = hitters[0][1], hitters[0][2]
        extras = []
        if s.get('doubles', 0): extras.append(f"{s['doubles']} 2B")
        if s.get('triples', 0): extras.append(f"{s['triples']} 3B")
        if s.get('homeRuns', 0): extras.append(f"{s['homeRuns']} HR")
        if s.get('rbi', 0): extras.append(f"{s['rbi']} RBI")
        if s.get('stolenBases', 0): extras.append(f"{s['stolenBases']} SB")
        if s.get('baseOnBalls', 0): extras.append(f"{s['baseOnBalls']} BB")
        line = f"{s.get('hits',0)}-for-{s.get('atBats',0)}" + ("" if not extras else " &middot; " + " &middot; ".join(extras))
        stars.append((p['person']['fullName'], line, _pos(p), p['person'].get('id')))
    if len(hitters) > 1:
        p, s = hitters[1][1], hitters[1][2]
        extras = []
        if s.get('doubles', 0): extras.append(f"{s['doubles']} 2B")
        if s.get('homeRuns', 0): extras.append(f"{s['homeRuns']} HR")
        if s.get('rbi', 0): extras.append(f"{s['rbi']} RBI")
        if s.get('stolenBases', 0): extras.append(f"{s['stolenBases']} SB")
        line = f"{s.get('hits',0)}-for-{s.get('atBats',0)}" + ("" if not extras else " &middot; " + " &middot; ".join(extras))
        stars.append((p['person']['fullName'], line, _pos(p), p['person'].get('id')))

    if hitters and hitters[0][0] >= 6:
        stars = [stars[1], stars[0], stars[2]] if len(stars) >= 3 else stars

    cards = []
    for i, (name, line, pos_badge, pid) in enumerate(stars[:3]):
        badge_html = f'<div class="star-badge">{escape(pos_badge)}</div>' if pos_badge else ''
        name_html = (
            f'<player-card pid="{pid}">{escape(name)}</player-card>' if pid else escape(name)
        )
        cards.append(f"""<div class="star">
        <div class="star-rank">{i+1}</div>
        <div class="star-body">
          <div class="star-name">{name_html}</div>
          <div class="star-stat">{line}</div>
        </div>
        {badge_html}
      </div>""")
    return f"""<div class="three-stars">
      <div class="stars-head">
        <h3 class="h">Three Stars</h3>
        <span class="tag">&#9733; &#9733; &#9733;</span>
      </div>
      {"".join(cards)}
    </div>"""


def _render_key_plays(plays_data, game, tmap):
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
        half = about.get("halfInning", "")[:1].upper()
        inn_str = f"{half}{inn}" if inn else ""
        desc = p.get("result", {}).get("description", "")
        items.append(f'<li><span class="inn">{inn_str}</span><span class="txt">{escape(desc)}</span></li>')
    if not items: return ""
    return f'<h3>Key Plays</h3><ul class="plays">{"".join(items)}</ul>'


def _render_next_games(next_games, tmap, team_id, team_name, today_lineup, today_series, today_opp_info):
    from build import fetch_pitcher_line, fetch_weather_for_venue, DOME_VENUES

    cards = []
    for idx, g in enumerate(next_games):
        home_id = g["teams"]["home"]["team"]["id"]
        away_id = g["teams"]["away"]["team"]["id"]
        is_home = home_id == team_id
        opp_id = away_id if is_home else home_id
        opp_ab = _abbr(tmap, opp_id)
        vs = f"vs {opp_ab}" if is_home else f"at {opp_ab}"
        try:
            gd = datetime.strptime(g["gameDate"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            ct = gd.astimezone(_CT)
            day_str = ct.strftime("%a, %b ") + str(ct.day)
            time_str = ct.strftime("%-I:%M") + " CT"
        except Exception:
            day_str = g.get("officialDate", "")
            time_str = ""
        cubs_side = "home" if is_home else "away"
        opp_side = "away" if is_home else "home"
        cubs_prob = g["teams"][cubs_side].get("probablePitcher", {})
        opp_prob = g["teams"][opp_side].get("probablePitcher", {})
        cubs_p = cubs_prob.get("fullName", "TBD") if cubs_prob else "TBD"
        opp_p = opp_prob.get("fullName", "TBD") if opp_prob else "TBD"

        cubs_pid = cubs_prob.get("id") if cubs_prob else None
        opp_pid = opp_prob.get("id") if opp_prob else None
        cubs_line = fetch_pitcher_line(cubs_pid)
        opp_line = fetch_pitcher_line(opp_pid)

        bc = g.get("broadcasts", [])
        tvs = [escape(b["name"]) for b in bc if b.get("type") == "TV" and b.get("language", "en") == "en"]
        radios = [escape(b["name"]) for b in bc if b.get("type") in ("AM", "FM") and b.get("language", "en") == "en"]
        bc_html = ""
        if tvs:
            bc_html += f'<div class="nx-bc"><span class="nx-bc-tag">TV</span> {" &middot; ".join(tvs)}</div>'
        if radios:
            bc_html += f'<div class="nx-bc"><span class="nx-bc-tag">Radio</span> {" &middot; ".join(radios)}</div>'

        venue = g.get("venue", {})
        venue_name = venue.get("name", "")
        vid = venue.get("id")
        dome_label = ""
        if vid in DOME_VENUES:
            dome_label = f'<span class="nx-dome">{DOME_VENUES[vid]}</span>'

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

        def _pitcher_name_html(name, pid):
            safe = escape(name)
            if pid:
                return f'<player-card pid="{pid}">{safe}</player-card>'
            return safe

        pitcher_html = ""
        if cubs_p != "TBD":
            pitcher_html += f'<div class="nx-pitcher"><span class="nx-side">{team_name}</span> {_pitcher_name_html(cubs_p, cubs_pid)}'
            if cubs_line: pitcher_html += f'<div class="nx-pline">{cubs_line}</div>'
            pitcher_html += '</div>'
        if opp_p != "TBD":
            pitcher_html += f'<div class="nx-pitcher"><span class="nx-side">{escape(opp_ab)}</span> {escape(opp_p)}'
            if opp_line: pitcher_html += f'<div class="nx-pline">{opp_line}</div>'
            pitcher_html += '</div>'

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
                    def _lu_slot(p):
                        last = escape(p["name"].split()[-1])
                        pid = p.get("id")
                        name_html = (
                            f'<player-card pid="{pid}">{last}</player-card>'
                            if pid else last
                        )
                        return (
                            f'<span class="lu-slot">'
                            f'<span class="lu-pos">{escape(p["pos"])}</span> '
                            f'{name_html}</span>'
                        )
                    lu_items = "".join(_lu_slot(p) for p in cubs_lu)
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


def _render_hot_cold(hitters_data, pitchers_data):
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
            out.append({"player": p["person"]["fullName"], "stat": st, "pid": p["person"].get("id")})
        return out

    qual = extract_hitters(hitters_data)

    def get_ops(s):
        try:
            return float(s["stat"].get("ops", "0") or "0")
        except:
            return 0.0

    qual.sort(key=get_ops, reverse=True)
    hot = qual[:4]
    cold = list(reversed(qual[-3:])) if len(qual) >= 4 else []

    def hitter_li(s):
        name = s["player"]
        st = s["stat"]
        pid = s.get("pid")
        avg = st.get("avg", "."); hr = st.get("homeRuns", 0); ops = st.get("ops", "-")
        last = escape(name.split()[-1])
        name_html = f'<player-card pid="{pid}">{last}</player-card>' if pid else last
        return f'<li><span class="n">{name_html}</span><span class="s">{avg} / {hr} HR / {ops} OPS</span></li>'

    hot_html = "".join(hitter_li(s) for s in hot)
    cold_html = "".join(hitter_li(s) for s in cold)

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
            out.append({"player": p["person"]["fullName"], "stat": st, "pid": p["person"].get("id")})
        return out

    p_qual = extract_pitchers(pitchers_data)

    def era(s):
        try:
            return float(s["stat"].get("era", "99") or 99)
        except:
            return 99

    p_qual.sort(key=era)
    p_hot = p_qual[:3]
    p_cold = list(reversed(p_qual[-2:])) if len(p_qual) >= 3 else []

    def pitcher_li(s):
        name = s["player"]
        st = s["stat"]
        pid = s.get("pid")
        era_v = st.get("era", "-"); k = st.get("strikeOuts", 0); ip = st.get("inningsPitched", "0")
        last = escape(name.split()[-1])
        name_html = f'<player-card pid="{pid}">{last}</player-card>' if pid else last
        return f'<li><span class="n">{name_html}</span><span class="s">{ip} IP &middot; {era_v} ERA &middot; {k} K</span></li>'

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


def _render_cubs_leaders(cubs_season_data):
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
            "pid": p["person"].get("id"),
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
        pid = leader.get("pid")
        name_html = (
            f'<player-card pid="{pid}">{escape(name)}</player-card>' if pid else escape(name)
        )
        rows.append(
            f'<tr><td>{label}</td>'
            f'<td class="name">{name_html} <span style="color:var(--paper-mute);font-size:10px">{escape(pos)}</span></td>'
            f'<td class="num">{escape(display)}</td></tr>'
        )

    if not rows:
        return '<p class="slang"><em>Season stats not yet available.</em></p>'

    return f"""<div class="tblwrap"><table class="data">
    <thead><tr><th>Cat</th><th>Leader</th><th style="text-align:right">#</th></tr></thead>
    <tbody>{"".join(rows)}</tbody></table></div>"""


def render(briefing):
    data = briefing.data
    team_id = briefing.team_id
    team_name = briefing.team_name

    line_score_html, summary_tag = _render_line_score(
        data["cubs_game"], data["tmap"], team_id, team_name,
        data.get("cubs_game_date"), data["yest"],
    )
    three_stars = _render_three_stars(data["boxscore"], data["cubs_game"], data["tmap"], team_id)
    key_plays = _render_key_plays(data["plays"], data["cubs_game"], data["tmap"])

    cubs_pk = data["cubs_game"]["gamePk"] if data["cubs_game"] else None
    scorecard_embed = ""
    if cubs_pk:
        scorecard_embed = f'''<details class="scorecard-expand">
      <summary><span class="scorecard-toggle">View Full Scorecard</span></summary>
      <iframe src="scorecard/?game={cubs_pk}&amp;embed=1" class="scorecard-frame" loading="lazy" frameborder="0"></iframe>
    </details>'''

    cubs_leaders_html = _render_cubs_leaders(data["cubs_season"])
    next_games_html = _render_next_games(
        data["next_games"], data["tmap"], team_id, team_name,
        data.get("today_lineup"), data.get("today_series", ""), data.get("today_opp_info", ""),
    )
    hot_cold_html = _render_hot_cold(data["cubs_hitters"], data["cubs_pitchers"])

    inner = f"""<div class="hero-grid">
      {line_score_html}
      {three_stars}
    </div>
    {key_plays}
    {scorecard_embed}
    <h3>{team_name} Leaders</h3>
    {cubs_leaders_html}
    <h3>Next Games</h3>
    {next_games_html}
    <h3>Form Guide (Last 7 Days)</h3>
    {hot_cold_html}"""
    return inner, summary_tag
