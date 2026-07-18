"""Wild Card Race — the team's league playoff picture, drawn around the cut line.

Computes entirely from data["standings"] (regularSeason type already carries
league.id, divisionLeader, wins/losses/pct/streak, and the L10 split record).
No extra API calls. The signature element is the Playoff Line: division leaders
are set aside, the remaining pool is ranked, the top three hold wild cards, and
a bold divider marks the cut — cushion shown above (+), deficit below.
"""
from html import escape

AL, NL = 103, 104
LEAGUE_NAME = {AL: "American League", NL: "National League"}
LEAGUE_ABBR = {AL: "AL", NL: "NL"}


def _logo(team_id, size="sm"):
    if not team_id:
        return ""
    return (f'<svg class="ml-logo {size}" aria-hidden="true" focusable="false">'
            f'<use href="#team-{team_id}"/></svg>')


def _fmt_gb(x):
    """Half-game aware: 0 -> '0', 2.0 -> '2', 2.5 -> '2.5'."""
    if x == int(x):
        return str(int(x))
    return f"{x:g}"


def _gb_between(ahead, behind):
    """Standard games-back: average of the win gap and the loss gap."""
    return ((ahead["wins"] - behind["wins"]) + (behind["losses"] - ahead["losses"])) / 2.0


def _l10(tr):
    for s in tr.get("records", {}).get("splitRecords", []):
        if s.get("type") == "lastTen":
            return f'{s.get("wins", 0)}-{s.get("losses", 0)}'
    return "–"


def _ordinal(n):
    return {1: "st", 2: "nd", 3: "rd"}.get(n, "th")


def render(briefing):
    data = briefing.data
    stand = data.get("standings")
    tmap = data["tmap"]
    team_id = briefing.team_id

    if not stand or not stand.get("records"):
        return '<p class="slang"><em>Standings not yet available.</em></p>'

    # Which league is this team in?
    my_league = None
    for rec in stand["records"]:
        for tr in rec["teamRecords"]:
            if tr["team"]["id"] == team_id:
                my_league = rec["league"]["id"]
                break
        if my_league:
            break
    if my_league not in (AL, NL):
        return '<p class="slang"><em>Wild card race unavailable.</em></p>'

    # Normalize every team in this league. Division leaders are set aside — they
    # hold a berth via the division and don't compete for a wild card.
    league_teams, div_leaders = [], []
    for rec in stand["records"]:
        if rec["league"]["id"] != my_league:
            continue
        for tr in rec["teamRecords"]:
            try:
                pct_f = float(tr.get("winningPercentage", "0") or 0)
            except ValueError:
                pct_f = 0.0
            t = {
                "id": tr["team"]["id"],
                "wins": tr.get("wins", 0),
                "losses": tr.get("losses", 0),
                "pct": tr.get("winningPercentage", ".000"),
                "pct_f": pct_f,
                "div_leader": bool(tr.get("divisionLeader")),
                "streak": tr.get("streak", {}).get("streakCode", ""),
                "l10": _l10(tr),
                "magic": tr.get("magicNumber", "-"),
                "wc_elim": str(tr.get("wildCardEliminationNumber", "-")),
            }
            league_teams.append(t)
            if t["div_leader"]:
                div_leaders.append(t)

    pool = sorted(
        [t for t in league_teams if not t["div_leader"]],
        key=lambda t: (-t["pct_f"], -t["wins"], t["losses"]),
    )
    if len(pool) < 4:
        return '<p class="slang"><em>Wild card race not yet meaningful.</em></p>'

    cut = pool[2]        # third / final wild card
    first_out = pool[3]  # first team on the outside
    for i, t in enumerate(pool):
        rank = i + 1
        t["rank"] = rank
        if rank <= 3:
            t["in_wc"] = True
            t["gap"] = _gb_between(t, first_out)          # games clear of the line
            t["wcgb_disp"] = "+" + _fmt_gb(t["gap"])
        else:
            t["in_wc"] = False
            t["gap"] = _gb_between(cut, t)                # games back of the line
            t["wcgb_disp"] = _fmt_gb(t["gap"])

    me = next((t for t in pool if t["id"] == team_id), None)
    me_leader = next((t for t in div_leaders if t["id"] == team_id), None)

    # -- Status hero: this team's own footing in the race --
    eyebrow = f"{LEAGUE_ABBR[my_league]} Wild Card"
    if me_leader is not None:
        # Division cushion = games up on second place in that division.
        div_teams = []
        for rec in stand["records"]:
            if rec["division"]["id"] == briefing.div_id:
                div_teams = sorted(
                    rec["teamRecords"],
                    key=lambda x: (-float(x.get("winningPercentage", "0") or 0), -x["wins"]),
                )
                break
        cls = "is-div"
        status = f"Leading the {briefing.div_name}"
        if len(div_teams) >= 2:
            lead = _gb_between(div_teams[0], div_teams[1])
            detail = ("Tied atop the division" if lead == 0
                      else f"{_fmt_gb(lead)} game{'s' if lead != 1 else ''} up on second")
        else:
            detail = "Atop the division"
        try:
            m = int(me_leader["magic"])
            if 0 < m <= 99:
                detail += f" &middot; Magic number {m}"
        except (ValueError, TypeError):
            pass
    elif me is not None and me["wc_elim"] in ("E", "0"):
        cls = "is-out"
        status = "Eliminated"
        detail = "Out of the playoff race"
    elif me is not None and me["in_wc"]:
        cls = "is-in"
        status = f"{me['rank']}{_ordinal(me['rank'])} Wild Card"
        detail = ("Tied at the cut line" if me["gap"] == 0
                  else f"{_fmt_gb(me['gap'])} game{'s' if me['gap'] != 1 else ''} clear of the line")
    elif me is not None:
        cls = "is-hunt"
        status = "In the Hunt" if me["gap"] <= 6 else "On the Outside"
        detail = (f"{_fmt_gb(me['gap'])} game{'s' if me['gap'] != 1 else ''} "
                  f"back of the final wild card")
    else:
        cls = "is-hunt"
        status = f"{LEAGUE_NAME[my_league]} Race"
        detail = "Three spots, everyone chasing"

    hero = (f'<div class="wc-hero {cls}">'
            f'<span class="wc-eyebrow">{eyebrow}</span>'
            f'<span class="wc-status">{status}</span>'
            f'<span class="wc-detail">{detail}</span>'
            f'</div>')

    # -- The table: three spots, the Playoff Line, then the chase --
    def _row(t):
        tid = t["id"]
        name = tmap.get(tid, {}).get("teamName", "???")
        classes = []
        if tid == team_id:
            classes.append("my-team")
        if t["in_wc"]:
            classes.append("wc-in")
        cls_attr = f' class="{" ".join(classes)}"' if classes else ""
        marker = (f'<span class="wc-badge">WC{t["rank"]}</span>' if t["in_wc"]
                  else f'<span class="wc-rank">{t["rank"]}</span>')
        gap_cls = " pos" if t["in_wc"] else ""
        strk_cls = ""
        if t["streak"][:1] == "W":
            strk_cls = " w"
        elif t["streak"][:1] == "L":
            strk_cls = " l"
        return (f"<tr{cls_attr}>"
                f'<td class="team"><span class="ml-logo-pair">{marker}{_logo(tid)}'
                f'<span class="ab">{escape(name)}</span></span></td>'
                f'<td class="num">{t["wins"]}</td>'
                f'<td class="num">{t["losses"]}</td>'
                f'<td class="num pct">{t["pct"]}</td>'
                f'<td class="num wcgb{gap_cls}">{t["wcgb_disp"]}</td>'
                f'<td class="num">{t["l10"]}</td>'
                f'<td class="num strk{strk_cls}">{t["streak"] or "&ndash;"}</td></tr>')

    line_row = ('<tr class="wc-line" aria-hidden="true">'
                '<td colspan="7"><span>Playoff Line</span></td></tr>')

    rows = [_row(t) for t in pool[:3]]
    rows.append(line_row)

    chase_all = pool[3:]
    chase = [t for t in chase_all if t["gap"] <= 8.0]
    if len(chase) < 3:
        chase = chase_all[:3]
    chase = chase[:6]
    rows += [_row(t) for t in chase]

    # Always keep the reader's own team on the page, even out of the shown chase.
    if me is not None and not me["in_wc"] and me not in chase:
        rows.append('<tr class="wc-gap" aria-hidden="true"><td colspan="7">&hellip;</td></tr>')
        rows.append(_row(me))

    table = (f'<div class="tblwrap"><table class="data standings wc-table">'
             f'<thead><tr><th>Team</th><th class="r">W</th><th class="r">L</th>'
             f'<th class="r">PCT</th><th class="r">WCGB</th><th class="r">L10</th>'
             f'<th class="r">STRK</th></tr></thead>'
             f'<tbody>{"".join(rows)}</tbody></table></div>')

    dl_bits = "".join(
        f'<span class="dl">{_logo(t["id"], "xs")}'
        f'<span class="ab">{escape(tmap.get(t["id"], {}).get("abbreviation", "?"))}</span></span>'
        for t in sorted(div_leaders, key=lambda x: (-x["pct_f"], -x["wins"]))
    )
    context = (f'<p class="wc-context"><span class="lbl">In via the division</span>'
               f'<span class="dl-list">{dl_bits}</span></p>') if dl_bits else ""

    return f'{hero}\n<h3>{LEAGUE_NAME[my_league]} Wild Card</h3>\n{table}\n{context}'
