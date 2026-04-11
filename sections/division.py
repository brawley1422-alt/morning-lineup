"""{Division} section — division standings + yesterday's rival results."""
from html import escape


def _team_name(tmap, team_id):
    return tmap.get(team_id, {}).get("teamName", "???")


def _abbr(tmap, team_id):
    return tmap.get(team_id, {}).get("abbreviation", "???")


def _logo(team_id, size="sm"):
    if not team_id:
        return ""
    return (f'<svg class="ml-logo {size}" aria-hidden="true" focusable="false">'
            f'<use href="#team-{team_id}"/></svg>')


def _render_standings(standings_data, tmap, div_id, team_id):
    recs = []
    for rec in standings_data["records"]:
        if rec["division"]["id"] == div_id:
            recs = rec["teamRecords"]
            break
    rows = []
    for tr in recs:
        tid = tr["team"]["id"]
        cls = ' class="my-team"' if tid == team_id else ''
        name = _team_name(tmap, tid)
        l10 = next((s for s in tr["records"]["splitRecords"] if s["type"] == "lastTen"), {})
        l10_str = f'{l10.get("wins",0)}-{l10.get("losses",0)}' if l10 else "–"
        gb = tr.get("gamesBack", "-")
        if gb in ("-", "0.0"): gb = "&mdash;"
        rows.append(f'<tr{cls}><td class="team"><span class="ml-logo-pair">{_logo(tid, "sm")}<span class="ab">{escape(name)}</span></span></td>'
                    f'<td class="num">{tr["wins"]}</td><td class="num">{tr["losses"]}</td>'
                    f'<td class="num pct">{tr["winningPercentage"]}</td>'
                    f'<td class="num">{gb}</td><td class="num">{l10_str}</td></tr>')
    return f"""<div class="tblwrap"><table class="data standings">
    <thead><tr><th>Team</th><th style="text-align:right">W</th><th style="text-align:right">L</th>
    <th style="text-align:right">PCT</th><th style="text-align:right">GB</th>
    <th style="text-align:right">L10</th></tr></thead>
    <tbody>{"".join(rows)}</tbody></table></div>"""


def _render_rivals(games_y, tmap, rivals_cfg, team_id, div_name):
    NLC = {int(k): v for k, v in rivals_cfg.items()}
    cards = []
    for g in games_y:
        aid = g["teams"]["away"]["team"]["id"]; hid = g["teams"]["home"]["team"]["id"]
        tid = None
        if aid in NLC and aid != team_id:
            tid = aid
        elif hid in NLC and hid != team_id:
            tid = hid
        else:
            continue
        name = NLC[tid]
        is_away = tid == aid
        opp_id = hid if is_away else aid
        opp_ab = _abbr(tmap, opp_id)
        my_score = g["teams"]["away" if is_away else "home"].get("score", 0)
        opp_score = g["teams"]["home" if is_away else "away"].get("score", 0)
        won = my_score > opp_score
        opp_logo = _logo(opp_id, "xs")
        vs_prefix = "at" if is_away else "vs"
        result = (f'{"W" if won else "L"} {my_score}-{opp_score} '
                  f'{vs_prefix} {opp_logo}<span class="ab">{opp_ab}</span>')
        wp = g.get("decisions", {}).get("winner", {}).get("fullName", "") if g.get("decisions") else ""
        lp = g.get("decisions", {}).get("loser", {}).get("fullName", "") if g.get("decisions") else ""
        blurb = f'WP: {wp}' + (f' · LP: {lp}' if lp else '')
        cards.append(f"""<div class="rival">
        <h4>{_logo(tid, "sm")} {escape(name)} <span class="score">{result}</span></h4>
        <p>{escape(blurb)}</p>
      </div>""")
    if not cards:
        cards.append(f'<div class="rival"><h4>{div_name} Rivals</h4><p>All off yesterday.</p></div>')
    return f'<div class="rivals">{"".join(cards)}</div>'


def render(briefing):
    data = briefing.data
    standings_html = _render_standings(data["standings"], data["tmap"], briefing.div_id, briefing.team_id)
    rivals_html = _render_rivals(
        data["games_y"], data["tmap"],
        briefing.config["rivals"], briefing.team_id, briefing.div_name,
    )
    return f"""<h3>Standings</h3>
    {standings_html}
    <h3>Rivals &middot; Yesterday</h3>
    {rivals_html}"""
