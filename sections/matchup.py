"""Matchup Read section — tonight's lineup × opposing starter's arsenal.

Joins the opposing starter's pitch mix against each hitter's per-pitch
Savant performance (xwOBA, whiff%) to produce a letter grade and a
per-hitter vulnerability tag. Bottom line is a "exploit: SL (2), FS (1)"
money line counting lineup vulnerabilities weighted by pitcher usage.

Conditional: renders empty when any precondition fails (no game, no
Savant arsenal for the opposing starter, empty lineup).

See docs/plans/2026-04-14-002-feat-matchup-read-plan.md
"""
from html import escape

# 2025 MLB league-average xwOBA across qualifying pitch types — used as
# the fallback when a batter has no row for a pitch the pitcher throws,
# or when the pitch type (FS, SV) isn't in the Savant batter CSV.
LEAGUE_AVG_XWOBA = 0.310

# Letter-grade bands match the Form Guide tier thresholds in
# sections/headline.py so tier colors stay consistent across sections.
_A_MIN = 0.360
_B_MIN = 0.320
_C_MIN = 0.290

# PA thresholds for 1–4 confidence dots.
_DOT_BANDS = ((150, 4), (100, 3), (75, 2), (50, 1))


def _dots(pa):
    if pa is None:
        return 0
    try:
        n = float(pa)
    except (ValueError, TypeError):
        return 0
    for threshold, dots in _DOT_BANDS:
        if n >= threshold:
            return dots
    return 0


def _letter_grade(x):
    if x is None:
        return "—"
    if x >= _A_MIN:
        return "A"
    if x >= _B_MIN:
        return "B"
    if x >= _C_MIN:
        return "C"
    return "D"


def _tier_class(grade):
    return {
        "A": "t-elite",
        "B": "t-solid",
        "C": "t-rough",
        "D": "t-rough",
    }.get(grade, "")


def _expected_xwoba(pitcher_arsenal, batter_arsenal_map):
    """Σ (usage[pt] × batter_xwOBA_vs[pt]) with league-avg fallback.

    Safety net: any unaccounted usage slice (pitcher_arsenal summing to
    less than 100% — common in early April when secondary pitches haven't
    cleared Savant's min-pitches threshold) falls back to league-average
    xwOBA. Clamps at 0 when arsenals round to >100%.
    """
    total = 0.0
    accounted = 0.0
    for pt in pitcher_arsenal or []:
        usage = pt.get("usage")
        if usage is None:
            continue
        accounted += usage
        code = pt.get("pitch")
        row = (batter_arsenal_map or {}).get(code) if code else None
        if row and row.get("xwoba") is not None:
            x = row["xwoba"]
        else:
            x = LEAGUE_AVG_XWOBA
        total += (usage / 100.0) * x
    missing = max(0.0, 100.0 - accounted)
    total += (missing / 100.0) * LEAGUE_AVG_XWOBA
    return total


def _vuln_tag(pitcher_arsenal, batter_arsenal_map):
    """Return the single strongest per-pitch story for this matchup, or
    None when there isn't one. Story = worst/best weighted gap from
    league average. Returns {pitch, kind ('vuln'|'safe'), dots, name}."""
    if not batter_arsenal_map:
        return None
    best = None
    best_abs = 0.0
    for pt in pitcher_arsenal or []:
        usage = pt.get("usage")
        code = pt.get("pitch")
        if usage is None or not code:
            continue
        row = batter_arsenal_map.get(code)
        if not row or row.get("xwoba") is None:
            continue
        gap = row["xwoba"] - LEAGUE_AVG_XWOBA
        weighted = (usage / 100.0) * gap
        if abs(weighted) > best_abs:
            best_abs = abs(weighted)
            best = {
                "pitch": code,
                "name": pt.get("name", code),
                "kind": "vuln" if weighted < 0 else "safe",
                "dots": _dots(row.get("pa")),
            }
    # Threshold: require at least a meaningful weighted gap to show a tag
    if best is None or best_abs < 0.010:
        return None
    return best


def _team_grade(expected_xwobas):
    vals = [x for x in expected_xwobas if isinstance(x, (int, float))]
    if not vals:
        return "—"
    mean = sum(vals) / len(vals)
    return _letter_grade(mean)


def _exploit_counts(tags, pitcher_arsenal):
    """Count vuln tags by pitch, order by pitcher usage desc so the
    headline pitch is the one the pitcher actually leans on."""
    counts = {}
    for tag in tags:
        if not tag or tag.get("kind") != "vuln":
            continue
        code = tag.get("pitch")
        counts[code] = counts.get(code, 0) + 1
    if not counts:
        return []
    usage_by_code = {
        pt.get("pitch"): (pt.get("usage") or 0.0)
        for pt in pitcher_arsenal or []
    }
    return sorted(
        counts.items(),
        key=lambda kv: usage_by_code.get(kv[0], 0.0),
        reverse=True,
    )


def _dots_html(n, kind):
    """Render n filled dots plus (4-n) hollow dots using Unicode."""
    if not n:
        return ""
    filled = "●" * n
    hollow = "○" * (4 - n)
    cls = "d-vuln" if kind == "vuln" else "d-safe"
    return f'<span class="mr-dots {cls}">{filled}{hollow}</span>'


def _render_lineup_row(slot, hitter, exp, grade, tag):
    name = escape(hitter.get("name", ""))
    pos = escape(hitter.get("pos", ""))
    grade_cls = _tier_class(grade)
    if exp is None:
        tag_html = '<span class="mr-nodata">—</span>'
        grade_html = '<span class="mr-grade">—</span>'
    else:
        if tag:
            kind = tag["kind"]
            code = escape(tag["pitch"])
            dots = _dots_html(tag["dots"], kind)
            tag_html = (
                f'<span class="mr-tag mr-{kind}">{kind}: '
                f'<b>{code}</b> {dots}</span>'
            )
        else:
            tag_html = '<span class="mr-tag mr-none">—</span>'
        grade_html = f'<span class="mr-grade {grade_cls}">{grade}</span>'
    return (
        f'<tr class="mr-row">'
        f'<td class="mr-slot">{slot}</td>'
        f'<td class="mr-name">{name}</td>'
        f'<td class="mr-pos">{pos}</td>'
        f'<td class="mr-read">{tag_html}</td>'
        f'<td class="mr-gcell">{grade_html}</td>'
        f'</tr>'
    )


def _render_arsenal_strip(arsenal):
    """Compact arsenal strip — top 5 pitches, same shape as the fuller
    scouting pitch-card grid but scaled down."""
    top = [p for p in arsenal if p.get("pitch")][:5]
    if not top:
        return ""
    cards = []
    for p in top:
        usage = p.get("usage")
        velo = p.get("velo")
        code = escape(p.get("pitch", ""))
        full = escape(p.get("name") or p.get("pitch", ""))
        velo_s = f"{velo:.1f}" if isinstance(velo, (int, float)) else "&mdash;"
        usage_s = f"{usage:.0f}%" if isinstance(usage, (int, float)) else "&mdash;"
        cards.append(
            f'<div class="mr-pc" title="{full}">'
            f'<div class="mr-pc-code">{code}</div>'
            f'<div class="mr-pc-velo">{velo_s}</div>'
            f'<div class="mr-pc-usage">{usage_s}</div>'
            f'</div>'
        )
    return f'<div class="mr-arsenal">{"".join(cards)}</div>'


def render(briefing):
    data = briefing.data
    next_games = data.get("next_games") or []
    savant = data.get("savant") or {}
    scout_data = data.get("scout_data") or {}
    today_lineup = data.get("today_lineup") or {}

    if not next_games or not savant or not scout_data:
        return ""

    opp_sp = scout_data.get("opp_sp") or {}
    opp_sp_id = opp_sp.get("id")
    if not opp_sp_id:
        return ""

    arsenal_map = savant.get("arsenal") or {}
    pitcher_arsenal = arsenal_map.get(str(opp_sp_id))
    if not pitcher_arsenal:
        return ""

    # Pick own lineup side from next_games[0] vs briefing.team_id —
    # same is_home check sections/scouting.py uses at line 135.
    tg = next_games[0]
    home_id = tg.get("teams", {}).get("home", {}).get("team", {}).get("id")
    is_home = home_id == briefing.team_id
    own_side = "home" if is_home else "away"
    own_lineup = today_lineup.get(own_side) or []
    if not own_lineup:
        return ""

    batter_arsenal_all = savant.get("batter_arsenal") or {}
    opp_sp_name = escape(opp_sp.get("name", "TBD"))

    rows = []
    tags = []
    expected_list = []
    for slot, hitter in enumerate(own_lineup[:9], start=1):
        pid = hitter.get("id")
        batter_arsenal = batter_arsenal_all.get(str(pid)) if pid else None
        if not batter_arsenal:
            exp = None
            grade = "—"
            tag = None
        else:
            exp = _expected_xwoba(pitcher_arsenal, batter_arsenal)
            grade = _letter_grade(exp)
            tag = _vuln_tag(pitcher_arsenal, batter_arsenal)
            expected_list.append(exp)
            tags.append(tag)
        rows.append(_render_lineup_row(slot, hitter, exp, grade, tag))

    team_letter = _team_grade(expected_list)
    team_cls = _tier_class(team_letter)
    exploit = _exploit_counts(tags, pitcher_arsenal)
    if exploit:
        exploit_html = (
            "exploit: "
            + ", ".join(f'<b>{escape(code)}</b> ({n})' for code, n in exploit)
        )
    else:
        exploit_html = '<span class="mr-muted">no obvious exploits</span>'

    arsenal_html = _render_arsenal_strip(pitcher_arsenal)

    return f"""<div class="matchup-read">
      <div class="mr-head">
        <span class="mr-sp">{opp_sp_name}</span>
        <span class="mr-sub">tonight's arsenal × {escape(briefing.team_name)} lineup</span>
      </div>
      {arsenal_html}
      <table class="mr-lineup">
        <tbody>{"".join(rows)}</tbody>
      </table>
      <div class="mr-foot">
        <span class="mr-team">TEAM <b class="{team_cls}">{team_letter}</b></span>
        <span class="mr-exp">{exploit_html}</span>
      </div>
    </div>"""
