"""Scouting Report section — today's pitching matchup deep dive.

Conditional: renders empty when scout_data is missing (off-days).
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


def _logo(team_id, size="sm"):
    if not team_id:
        return ""
    return (f'<svg class="ml-logo {size}" aria-hidden="true" focusable="false">'
            f'<use href="#team-{team_id}"/></svg>')


def _fmt_time_ct(iso_z):
    dt = datetime.strptime(iso_z, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    ct = dt.astimezone(_CT)
    return ct.strftime("%-I:%M") + " CT"


def _render_arsenal(arsenal):
    """Render a compact pitch-mix table from the top 4 pitches by usage.
    Returns empty string when arsenal is missing or empty."""
    if not arsenal:
        return ""
    top = [p for p in arsenal if p.get("pitch")][:4]
    if not top:
        return ""
    rows = []
    for p in top:
        usage = p.get("usage")
        velo = p.get("velo")
        spin = p.get("spin")
        whiff = p.get("whiff")
        usage_s = f"{usage:.0f}%" if isinstance(usage, (int, float)) else "&mdash;"
        velo_s = f"{velo:.1f}" if isinstance(velo, (int, float)) else "&mdash;"
        spin_s = f"{int(round(spin))}" if isinstance(spin, (int, float)) else "&mdash;"
        whiff_s = f"{whiff:.0f}%" if isinstance(whiff, (int, float)) else "&mdash;"
        name = escape(p.get("name") or p.get("pitch", ""))
        rows.append(
            f'<tr><td class="pitch-name">{name}</td>'
            f'<td class="num">{usage_s}</td>'
            f'<td class="num">{velo_s}</td>'
            f'<td class="num">{spin_s}</td>'
            f'<td class="num">{whiff_s}</td></tr>'
        )
    return f"""<h4>Arsenal</h4>
    <table class="data sp-arsenal">
      <thead><tr><th>Pitch</th><th style="text-align:right">Usage</th><th style="text-align:right">Velo</th><th style="text-align:right">Spin</th><th style="text-align:right">Whf</th></tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table>"""


def render(briefing):
    scout_data = briefing.data.get("scout_data", {})
    next_games = briefing.data["next_games"]
    tmap = briefing.data["tmap"]
    team_id = briefing.team_id
    team_name = briefing.team_name
    savant = briefing.data.get("savant") or {}
    arsenal_map = savant.get("arsenal") or {}

    if not scout_data:
        return ""
    cubs_sp = scout_data.get("cubs_sp")
    opp_sp = scout_data.get("opp_sp")
    if not cubs_sp and not opp_sp:
        return ""

    def _sp_card(sp, side_label, is_own=False, side_team_id=None):
        side_logo = _logo(side_team_id, "md") if side_team_id else ""
        side_html = f'<div class="sp-side">{side_logo}<span class="sp-side-ab">{side_label}</span></div>'
        if not sp:
            return f'<div class="sp-card">{side_html}<div class="sp-name">TBD</div></div>'
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
        sp_name = escape(sp.get("name", "TBD"))
        sp_pid = sp.get("id")
        sp_name_html = (
            f'<player-card pid="{sp_pid}">{sp_name}</player-card>'
            if is_own and sp_pid else sp_name
        )
        arsenal_html = _render_arsenal(arsenal_map.get(str(sp_pid), [])) if sp_pid else ""
        return f"""<div class="sp-card">
        {side_html}
        <div class="sp-name">{sp_name_html}</div>
        <div class="sp-season">{sp.get("season","")}</div>
        {f'<h4>Last {len(sp.get("log",[]))} Starts</h4>{log_html}' if log_html else ''}
        {arsenal_html}
        </div>"""

    # Game context line
    game_ctx = ""
    opp_team_id = None
    if next_games:
        tg = next_games[0]
        home_id = tg["teams"]["home"]["team"]["id"]
        away_id = tg["teams"]["away"]["team"]["id"]
        is_home = home_id == team_id
        opp_team_id = away_id if is_home else home_id
        opp_abbr = _abbr(tmap, opp_team_id)
        venue = tg.get("venue", {}).get("name", "")
        time_str = _fmt_time_ct(tg.get("gameDate", ""))
        ha = "vs" if is_home else "at"
        game_ctx = (f'<div class="scout-ctx">'
                    f'<span>{ha} {_logo(opp_team_id, "sm")}<span class="ab">{opp_abbr}</span> &middot; {time_str}</span>'
                    f'<span>{escape(venue)}</span></div>')

    opp_label = _abbr(tmap, opp_team_id) if opp_team_id else "OPP"
    return f"""{game_ctx}
    <div class="matchup-vs">
        {_sp_card(cubs_sp, team_name, is_own=True, side_team_id=team_id)}
        <div class="vs-divider">VS</div>
        {_sp_card(opp_sp, opp_label, side_team_id=opp_team_id)}
    </div>"""
