"""Around the League section — news wire, scoreboard, division standings, league leaders.

Also exports render_lede_block(briefing) for the editorial lede that sits
at the top of the page (outside the main section). generate_lede() tries
Ollama first, then Anthropic API fallback, with a local cache file that
the snapshot test relies on for determinism.
"""
import json
import re
import urllib.request
from html import escape
from pathlib import Path

_DIV_ORDER = [
    (201, "AL East"), (202, "AL Central"), (200, "AL West"),
    (204, "NL East"), (205, "NL Central"), (203, "NL West"),
]


def _abbr(tmap, team_id):
    return tmap.get(team_id, {}).get("abbreviation", "???")


def _logo(team_id, size="sm"):
    if not team_id:
        return ""
    return (f'<svg class="ml-logo {size}" aria-hidden="true" focusable="false">'
            f'<use href="#team-{team_id}"/></svg>')


def _team_name(tmap, team_id):
    return tmap.get(team_id, {}).get("teamName", "???")


def _render_scoreboard_yest(games_y, tmap):
    rows = []
    for g in games_y:
        if g.get("status", {}).get("abstractGameState") != "Final":
            continue
        away_id = g["teams"]["away"]["team"]["id"]
        home_id = g["teams"]["home"]["team"]["id"]
        aa = _abbr(tmap, away_id); ha = _abbr(tmap, home_id)
        as_ = g["teams"]["away"].get("score", 0)
        hs = g["teams"]["home"].get("score", 0)
        winner_ab = aa if as_ > hs else ha
        wp = g.get("decisions", {}).get("winner", {}).get("fullName", "").split()[-1] if g.get("decisions") else ""
        pk = g.get("gamePk", "")
        winner_logo = _logo(away_id if as_ > hs else home_id, "xs")
        rows.append(f'<tr class="scorecard-link" data-href="scorecard/?game={pk}">'
                    f'<td class="name"><span class="ml-logo-pair">{_logo(away_id, "xs")}<span class="ab">{escape(aa)}</span></span></td><td class="num">{as_}</td>'
                    f'<td class="name"><span class="ml-logo-pair">{_logo(home_id, "xs")}<span class="ab">{escape(ha)}</span></span></td><td class="num">{hs}</td>'
                    f'<td class="num w"><span class="ml-logo-pair">{winner_logo}<span class="ab">{escape(winner_ab)}</span></span></td><td>{escape(wp)}</td></tr>')
    return f"""<div class="tblwrap"><table class="data">
    <thead><tr><th>Away</th><th></th><th>Home</th><th></th><th>W</th><th>WP</th></tr></thead>
    <tbody>{"".join(rows)}</tbody></table></div>"""


def _render_all_divisions(standings_data, tmap, team_id):
    by_div = {}
    for rec in standings_data["records"]:
        by_div[rec["division"]["id"]] = rec["teamRecords"]

    def div_table(div_id, name):
        recs = by_div.get(div_id, [])
        rows = []
        for tr in recs:
            tid = tr["team"]["id"]
            cls = ' class="my-team"' if tid == team_id else ''
            tn = _team_name(tmap, tid)
            gb = tr.get("gamesBack", "-")
            if gb in ("-", "0.0"): gb = "&mdash;"
            rows.append(f'<tr{cls}><td class="team"><span class="ml-logo-pair">{_logo(tid, "xs")}<span class="ab">{escape(tn)}</span></span></td>'
                        f'<td class="num">{tr["wins"]}</td><td class="num">{tr["losses"]}</td>'
                        f'<td class="num">{gb}</td></tr>')
        return f"""<h4>{name}</h4><div class="tblwrap"><table class="data standings">
        <thead><tr><th>Team</th><th style="text-align:right">W</th><th style="text-align:right">L</th>
        <th style="text-align:right">GB</th></tr></thead>
        <tbody>{"".join(rows)}</tbody></table></div>"""

    al = "".join(div_table(did, n) for did, n in _DIV_ORDER[:3])
    nl = "".join(div_table(did, n) for did, n in _DIV_ORDER[3:])
    return f'<div class="two"><div>{al}</div><div>{nl}</div></div>'


def _render_leaders(lh, lp, tmap):
    CAT_LABELS = {
        "battingAverage": "AVG", "homeRuns": "HR", "runsBattedIn": "RBI",
        "stolenBases": "SB", "onBasePlusSlugging": "OPS",
        "earnedRunAverage": "ERA", "strikeOuts": "K", "whip": "WHIP",
        "saves": "SV", "wins": "W",
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
            ab = _abbr(tmap, tid)
            val = L["value"]
            out.append(f'<tr><td>{CAT_LABELS.get(cat,cat)}</td><td class="name">{escape(name)} <span class="ml-logo-pair">{_logo(tid, "xs")}<span class="ab">{escape(ab)}</span></span></td><td class="num">{escape(str(val))}</td></tr>')
        return "".join(out)

    hit = rows(lh, ["battingAverage", "homeRuns", "runsBattedIn", "stolenBases", "onBasePlusSlugging"])
    pit = rows(lp, ["earnedRunAverage", "strikeOuts", "whip", "saves", "wins"])
    return f"""<div class="two">
    <div><h4>Batting</h4><div class="tblwrap"><table class="data">
    <thead><tr><th>Cat</th><th>Leader</th><th style="text-align:right">#</th></tr></thead>
    <tbody>{hit}</tbody></table></div></div>
    <div><h4>Pitching</h4><div class="tblwrap"><table class="data">
    <thead><tr><th>Cat</th><th>Leader</th><th style="text-align:right">#</th></tr></thead>
    <tbody>{pit}</tbody></table></div></div>
    </div>"""


def _detect_league_news(games_y, standings_data, tmap):
    items = []
    for g in games_y:
        if g.get("status", {}).get("abstractGameState") != "Final":
            continue
        if "linescore" not in g:
            continue
        away_id = g["teams"]["away"]["team"]["id"]
        home_id = g["teams"]["home"]["team"]["id"]
        away_ab = _abbr(tmap, away_id)
        home_ab = _abbr(tmap, home_id)
        away_name = _team_name(tmap, away_id)
        home_name = _team_name(tmap, home_id)
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

    for rec in standings_data.get("records", []):
        for tr in rec["teamRecords"]:
            streak = tr.get("streak", {})
            num = streak.get("streakNumber", 0)
            stype = streak.get("streakType", "")
            if num >= 7:
                tid = tr["team"]["id"]
                tname = _team_name(tmap, tid)
                if stype == "wins":
                    body = f"The {escape(tname)} have won {num} straight."
                    headline = f"W{num}"
                else:
                    body = f"The {escape(tname)} have dropped {num} in a row."
                    headline = f"L{num}"
                items.append({"type": "streak", "priority": 6, "headline": headline, "body": body})

    items.sort(key=lambda x: x["priority"])
    return items[:6]


def _render_league_news_from_items(items):
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


def _data_dir():
    # Relative to repo root (one level up from sections/).
    return Path(__file__).resolve().parent.parent / "data"


def generate_lede(briefing):
    data = briefing.data
    team_name = briefing.team_name
    div_name = briefing.div_name
    slug = briefing.config["slug"]
    lede_tone = briefing.config["branding"]["lede_tone"]

    data_dir = _data_dir()
    lede_cache = data_dir / f"lede-{slug}-{data['today'].isoformat()}.txt"
    if lede_cache.exists():
        cached = lede_cache.read_text(encoding="utf-8").strip()
        if cached:
            return cached

    parts = []
    cg = data.get("cubs_game")
    if cg:
        away = cg["teams"]["away"]["team"].get("name", "?")
        home = cg["teams"]["home"]["team"].get("name", "?")
        asc = cg["teams"]["away"].get("score", 0)
        hsc = cg["teams"]["home"].get("score", 0)
        parts.append(f"{team_name} game: {away} {asc}, {home} {hsc}")
    else:
        parts.append(f"No {team_name} game yesterday.")

    cr = data.get("cubs_rec")
    if cr:
        parts.append(f"{team_name} record: {cr['wins']}-{cr['losses']}, {cr.get('gamesBack', '?')} GB in {div_name}")

    prompt = f"""Write a 3-4 sentence editorial lede for a {team_name} fan newspaper called "The Morning Lineup."
Tone: witty, opinionated, knowledgeable — {lede_tone}.
Keep it concise and punchy. No cliches. Reference specific details.
Do NOT use any thinking tags or meta-commentary. Just write the paragraph directly.

Today's context:
{chr(10).join(parts)}

Write ONLY the paragraph, nothing else."""

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
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        if text and len(text) > 50:
            data_dir.mkdir(exist_ok=True)
            lede_cache.write_text(text, encoding="utf-8")
            return text
    except Exception as e:
        print(f"  Ollama lede failed: {e}", flush=True)

    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY")
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
                data_dir.mkdir(exist_ok=True)
                lede_cache.write_text(text, encoding="utf-8")
                return text
        except Exception as e:
            print(f"  Anthropic lede failed: {e}", flush=True)

    return ""


def render_lede_block(briefing):
    lede_text = generate_lede(briefing)
    if not lede_text:
        return ""
    return f'<div class="lede">{escape(lede_text)}</div>'


def render(briefing):
    """Return (inner_html, news_count) — the news_count is consumed by the
    page envelope for the section header badge."""
    data = briefing.data
    tmap = data["tmap"]
    team_id = briefing.team_id

    news_items = _detect_league_news(data["games_y"], data["standings"], tmap)
    news_count = len(news_items)
    news_html = _render_league_news_from_items(news_items)
    scoreboard_html = _render_scoreboard_yest(data["games_y"], tmap)
    all_div_html = _render_all_divisions(data["standings"], tmap, team_id)
    leaders_html = _render_leaders(data["leaders_hit"], data["leaders_pit"], tmap)

    inner = f"""<h3>News Wire</h3>
    {news_html}
    <h3>Yesterday&rsquo;s Scoreboard</h3>
    {scoreboard_html}
    <a href="scorecard/" class="scorecard-btn">Browse All Scorecards &rsaquo;</a>
    <h3>Standings &mdash; All Six Divisions</h3>
    {all_div_html}
    <h3>League Leaders</h3>
    {leaders_html}"""
    return inner, news_count
