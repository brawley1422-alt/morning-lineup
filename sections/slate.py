"""Today's Slate section — full MLB schedule with probable pitchers + broadcasts."""
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


def render(briefing):
    games_t = briefing.data["games_t"]
    tmap = briefing.data["tmap"]

    cards = []
    for g in games_t:
        aid = g["teams"]["away"]["team"]["id"]; hid = g["teams"]["home"]["team"]["id"]
        aa = _abbr(tmap, aid); ha = _abbr(tmap, hid)
        try:
            gd = datetime.strptime(g["gameDate"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            ct = gd.astimezone(_CT)
            time_str = ct.strftime("%-I:%M") + " CT"
        except Exception:
            time_str = ""
        ap = g["teams"]["away"].get("probablePitcher", {}) or {}
        hp = g["teams"]["home"].get("probablePitcher", {}) or {}
        ap_n = ap.get("fullName", "TBD").split()[-1] if ap else "TBD"
        hp_n = hp.get("fullName", "TBD").split()[-1] if hp else "TBD"
        bc = g.get("broadcasts", [])
        bc_parts = []
        for b in bc:
            if b.get("type") == "TV" and b.get("language", "en") == "en":
                bc_parts.append(escape(b.get("name", "")))
        bc_str = f'<div class="bc">{" · ".join(bc_parts)}</div>' if bc_parts else ""
        cards.append(f"""<div class="g" data-gpk="{g['gamePk']}">
        <div class="matchup">{aa} @ {ha}</div>
        <div class="time">{time_str}</div>
        <div class="probs">{escape(ap_n)} vs {escape(hp_n)}</div>
        {bc_str}
      </div>""")
    return f'<div class="slate">{"".join(cards)}</div>'
