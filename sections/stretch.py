"""The Stretch section — season pulse, run differential, Pythagorean W-L, splits."""


def _ordinal(n):
    try:
        n = int(n)
    except (ValueError, TypeError):
        return ""
    return {1: "st", 2: "nd", 3: "rd"}.get(n if n < 20 else n % 10, "th")


def render(briefing):
    cubs_rec = briefing.data["cubs_rec"]
    div_name = briefing.div_name
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
        <span class="pulse-rank">{rank}{_ordinal(rank)} {div_name}</span>
        {f'<span class="pulse-streak">{streak}</span>' if streak else ''}
    </div>
    <div class="pulse-diff">
        <div class="diff-label">Run Differential</div>
        <div class="diff-num {rd_cls}">{rd_str}</div>
        <div class="diff-detail">{rs} RS &middot; {ra} RA &middot; Pythag: {pyth_w}-{pyth_l}</div>
    </div>
    <h3>Splits</h3>
    <div class="splits-grid">{"".join(split_rows)}</div>"""
