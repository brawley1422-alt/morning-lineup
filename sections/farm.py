"""Down on the Farm section — minor league affiliate results + prospect tracker.

Returns a tuple (html, tag) because the page envelope needs the W-L tag
for the section header badge.
"""
from html import escape


def _fmt_tonight(today_game, aff_id):
    """Render a compact tonight-game line: 'vs/at OPP · 7:05 CT' or
    'off day'. Returns an HTML fragment."""
    if not today_game:
        return '<div class="lvl-tonight"><em>off day</em></div>'
    try:
        from datetime import datetime
        try:
            from zoneinfo import ZoneInfo
            ct = ZoneInfo("America/Chicago")
        except Exception:
            ct = None
        home_id = today_game["teams"]["home"]["team"]["id"]
        is_home = home_id == aff_id
        opp_side = "away" if is_home else "home"
        opp_name = today_game["teams"][opp_side]["team"].get("teamName", "???")
        vs_at = "vs" if is_home else "at"
        iso = today_game.get("gameDate", "")
        time_s = ""
        if iso:
            try:
                d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
                if ct:
                    d = d.astimezone(ct)
                h = d.hour % 12 or 12
                ampm = "PM" if d.hour >= 12 else "AM"
                time_s = f"{h}:{d.minute:02d} {ampm} CT"
            except Exception:
                time_s = ""
        state = today_game.get("status", {}).get("abstractGameState", "")
        if state == "Final":
            away = today_game["teams"]["away"].get("score", 0)
            home = today_game["teams"]["home"].get("score", 0)
            my = home if is_home else away
            opp = away if is_home else home
            res = "W" if my > opp else "L"
            return (
                f'<div class="lvl-tonight"><span class="lvl-lbl">today</span> '
                f'{res} {my}&ndash;{opp} {vs_at} {escape(opp_name)}</div>'
            )
        return (
            f'<div class="lvl-tonight"><span class="lvl-lbl">tonight</span> '
            f'{vs_at} {escape(opp_name)}'
            + (f' &middot; {time_s}' if time_s else "")
            + '</div>'
        )
    except Exception:
        return ""


def _fmt_standings(standings):
    if not standings:
        return ""
    w = standings.get("wins", 0)
    l = standings.get("losses", 0)
    rank = standings.get("rank")
    rank_s = f" &middot; {rank}" + _ordinal_suffix(rank) if rank else ""
    return f'<div class="lvl-standings">{w}&ndash;{l}{rank_s}</div>'


def _ordinal_suffix(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    if 10 <= n % 100 <= 20:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def render(briefing):
    minors_data = briefing.data["minors"]
    prospects = briefing.data.get("prospects", {}) or {}

    cards = []
    for m in minors_data:
        aff = m["aff"]
        g = m["game"]
        box = m["boxscore"]
        today_game = m.get("today_game")
        standings = m.get("standings")
        tonight_html = _fmt_tonight(today_game, aff["id"])
        standings_html = _fmt_standings(standings)
        if not g or g.get("status", {}).get("abstractGameState") != "Final":
            cards.append(f"""<div class="lvl" data-lvl="{aff['level']}">
        <div class="aff">{escape(aff['name'])}</div>
        <div class="res"><em>No game / not final</em></div>
        {tonight_html}
        {standings_html}
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
                bs = p.get("stats", {}).get("batting", {})
                if bs and bs.get("atBats", 0) > 0:
                    h = bs.get("hits", 0)
                    hr = bs.get("homeRuns", 0)
                    rbi = bs.get("rbi", 0)
                    sc = h + 3 * hr + rbi
                    if sc > best_score:
                        best_score = sc
                        best_hitter = (p["person"]["fullName"], bs, player_id)
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
        {tonight_html}
        {standings_html}
      </div>""")

    if not cards:
        return '<p class="slang"><em>No affiliate games yesterday.</em></p>', "No games"

    wins = sum(1 for m in minors_data if m["game"] and m["game"].get("status", {}).get("abstractGameState") == "Final"
               and ((m["game"]["teams"]["home"]["team"]["id"] == m["aff"]["id"] and m["game"]["teams"]["home"].get("score", 0) > m["game"]["teams"]["away"].get("score", 0))
                    or (m["game"]["teams"]["away"]["team"]["id"] == m["aff"]["id"] and m["game"]["teams"]["away"].get("score", 0) > m["game"]["teams"]["home"].get("score", 0))))
    finals = sum(1 for m in minors_data if m["game"] and m["game"].get("status", {}).get("abstractGameState") == "Final")
    losses = finals - wins
    tag = f"{wins}&ndash;{losses}" if finals > 0 else "No games"

    prospect_rows = []
    if prospects:
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

        def lvl_class(level):
            return {"AAA": "aaa", "AA": "aa", "A+": "aplus", "A": "a"}.get(level, "")

        played_rows = []
        dnp_rows = []
        for pid, pr in sorted(prospects.items(), key=lambda x: x[1]["rank"]):
            rank = pr["rank"]
            name = escape(pr["name"])
            pos = escape(pr["position"])
            level = escape(pr["level"])
            if pid in found:
                bs, ps, game_level = found[pid]
                stat_parts = []
                is_hot = False
                if bs and bs.get("atBats", 0) > 0:
                    h, ab = bs.get("hits", 0), bs.get("atBats", 0)
                    line = f'{h}-{ab}'
                    extras = []
                    if bs.get("runs", 0): extras.append(f'{bs["runs"]} R')
                    if bs.get("homeRuns", 0): extras.append(f'{bs["homeRuns"]} HR')
                    if bs.get("rbi", 0): extras.append(f'{bs["rbi"]} RBI')
                    if bs.get("baseOnBalls", 0): extras.append(f'{bs["baseOnBalls"]} BB')
                    if bs.get("strikeOuts", 0): extras.append(f'{bs["strikeOuts"]} K')
                    if extras: line += ", " + ", ".join(extras)
                    stat_parts.append(line)
                    if bs.get("homeRuns", 0) or (h >= 3 and ab >= 3):
                        is_hot = True
                if ps and ps.get("inningsPitched") not in (None, "0.0", 0):
                    ip = ps.get("inningsPitched", "?")
                    er = ps.get("earnedRuns", 0)
                    k = ps.get("strikeOuts", 0)
                    stat_parts.append(f'{ip} IP, {er} ER, {k} K')
                    try:
                        ip_f = float(str(ip).replace(".", "")) if "." not in str(ip) else float(ip)
                        if ip_f >= 5.0 and er <= 1 and k >= 5:
                            is_hot = True
                    except (ValueError, TypeError):
                        pass
                stat_str = " &middot; ".join(stat_parts) if stat_parts else "In lineup, no AB"
                hot_cls = " hot" if is_hot else ""
                played_rows.append(
                    f'<div class="prosp-row played{hot_cls}">'
                    f'<span class="prosp-rank">#{rank}</span>'
                    f'<span class="prosp-name">{name}</span>'
                    f'<span class="prosp-pos">{pos}</span>'
                    f'<span class="prosp-lvl {lvl_class(game_level)}">{game_level}</span>'
                    f'<span class="prosp-stat">{stat_str}</span>'
                    f'</div>')
            else:
                dnp_rows.append(
                    f'<div class="prosp-row dnp">'
                    f'<span class="prosp-rank">#{rank}</span>'
                    f'<span class="prosp-name">{name}</span>'
                    f'<span class="prosp-pos">{pos}</span>'
                    f'<span class="prosp-lvl {lvl_class(level)}">{level}</span>'
                    f'<span class="prosp-stat">DNP</span>'
                    f'</div>')
        prospect_rows = played_rows
        if played_rows and dnp_rows:
            prospect_rows.append('<div class="prosp-divider"></div>')
        prospect_rows.extend(dnp_rows)

    prospect_html = ""
    if prospect_rows:
        col_hdr = '<div class="prosp-cols"><span>#</span><span>Name</span><span>Pos</span><span>Lvl</span><span>Line</span></div>'
        prospect_html = f'<h3 class="prosp-header">Prospect Watch</h3><div class="prosp-tracker">{col_hdr}{"".join(prospect_rows)}</div>'

    return f'<div class="minors">{"".join(cards)}</div>{prospect_html}', tag
