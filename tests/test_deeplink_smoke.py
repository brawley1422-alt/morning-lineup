#!/usr/bin/env python3
"""Smoke test: every team's /<slug>/#p/<pid> deeplink has all pieces in place.

For each team, verifies:
  - data/players-<slug>.json exists with at least one player
  - <slug>/index.html exists, references player-card.js, has data-team="<slug>"
  - <slug>/player-card.js exists (per-team copy of the component)
  - The picked pid is present in the JSON

The component runtime itself is proven by the Cubs MVP — this test catches
distribution and gating regressions: missing JSON, missing script tag, missing
per-team copy, wrong data-team attribute.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"


def check_team(slug):
    json_path = DATA / f"players-{slug}.json"
    if not json_path.exists():
        return False, f"missing {json_path.name}"
    payload = json.loads(json_path.read_text())
    players = payload.get("players", {})
    if not players:
        return False, "empty players dict"
    pid = next(iter(players.keys()))

    page = ROOT / slug / "index.html"
    if not page.exists():
        return False, f"missing {slug}/index.html"
    html = page.read_text(encoding="utf-8")
    if 'src="player-card.js"' not in html:
        return False, "missing player-card.js script tag"
    if f'data-team="{slug}"' not in html:
        return False, "missing data-team body attribute"

    pc_js = ROOT / slug / "player-card.js"
    if not pc_js.exists():
        return False, "missing per-team player-card.js"

    pname = players[pid].get("name", "?")
    return True, f"#p/{pid} ({pname})"


def main():
    fails = []
    total = 0
    for json_file in sorted(DATA.glob("players-*.json")):
        slug = json_file.stem.replace("players-", "")
        ok, msg = check_team(slug)
        total += 1
        marker = "OK  " if ok else "FAIL"
        print(f"{marker} {slug:12s} — {msg}")
        if not ok:
            fails.append(f"{slug}: {msg}")
    print(f"\n{total - len(fails)}/{total} deeplink smoke checks passed")
    if fails:
        sys.exit(1)


if __name__ == "__main__":
    main()
