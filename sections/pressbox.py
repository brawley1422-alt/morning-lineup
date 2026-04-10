"""The Pressbox section — recent transactions + injured list."""
from html import escape


def _render_injuries(injuries):
    groups = {}
    for p in injuries:
        code = p.get("status", {}).get("code", "")
        desc = p.get("status", {}).get("description", "")
        groups.setdefault(desc, []).append(p)
    pri = {"Injured 10-Day": 1, "Injured 15-Day": 2, "Injured 60-Day": 3, "Reassigned to Minors": 9}
    order = sorted(groups.keys(), key=lambda k: pri.get(k, 5))
    out = []
    for k in order:
        if k == "Reassigned to Minors":
            continue
        players = groups[k]
        if not players:
            continue
        dds = "".join(f'<dd>{escape(p["position"]["abbreviation"])} <strong>{escape(p["person"]["fullName"])}</strong></dd>'
                      for p in players)
        out.append(f'<dt>{escape(k)}</dt>{dds}')
    if not out:
        return '<p class="slang"><em>Clean bill of health.</em></p>'
    return f'<dl class="transac">{"".join(out)}</dl>'


def render(briefing):
    injuries = briefing.data["injuries"]
    transactions = briefing.data.get("transactions", [])

    sorted_tx = sorted(transactions, key=lambda t: t.get("effectiveDate", t.get("date", "")), reverse=True)

    tx_rows = []
    for tx in sorted_tx[:10]:
        d = tx.get("effectiveDate", tx.get("date", ""))
        if len(d) >= 10:
            d = d[5:]  # MM-DD
        tc = tx.get("typeCode", "")
        desc = tx.get("description", "")
        type_map = {
            "DIS": ("IL", "il"), "DTD": ("IL", "il"),
            "ACT": ("Activated", "act"),
            "OPT": ("Optioned", "opt"), "OUT": ("Outrighted", "opt"),
            "RCL": ("Recalled", "rcl"),
            "DFA": ("DFA", "il"), "REL": ("Released", "il"),
            "ASG": ("Assigned", "opt"), "SC": ("Status Change", "act"),
            "SFA": ("Signed", "act"), "SGN": ("Signed", "act"),
            "TR": ("Trade", "il"),
        }
        label, cls = type_map.get(tc, (tx.get("typeDesc", tc)[:12], ""))
        tx_rows.append(
            f'<div class="transac-item">'
            f'<span class="transac-date">{d}</span>'
            f'<span class="transac-badge {cls}">{escape(label)}</span>'
            f'<span class="transac-desc">{escape(desc)}</span>'
            f'</div>')

    if tx_rows:
        tx_html = f'<h3>Recent Transactions</h3><div class="transac-list">{"".join(tx_rows)}</div>'
    else:
        tx_html = '<h3>Recent Transactions</h3><p><em class="slang">No roster moves in the last 7 days.</em></p>'

    inj_html = _render_injuries(injuries) if injuries else '<p><em>Clean bill of health.</em></p>'

    return f'<div class="two"><div>{tx_html}</div><div><h3>Injured List</h3>{inj_html}</div></div>'
