#!/usr/bin/env python3
"""Populate teams/{slug}/prospects.json for all 30 MLB teams.

Phase 1: Scrape MLB Pipeline prospect rankings (official ranks + player IDs)
Phase 2: Crawl minor league affiliate rosters for current level assignments
Phase 3: Merge and write JSON files

Source: mlb.com/milb/prospects/{team} embeds an Apollo GraphQL cache with
the full Top 30 ranked prospects including MLB Stats API player IDs.

Usage:
    python3 scripts/populate_prospects.py                  # all teams (skip existing)
    python3 scripts/populate_prospects.py --team yankees   # single team
    python3 scripts/populate_prospects.py --force-all      # regenerate all 30
    python3 scripts/populate_prospects.py --from-cache     # skip Phase 1+2
"""

import json
import re
import sys
import time
import html as htmlmod
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEAMS_DIR = ROOT / "teams"
API = "https://statsapi.mlb.com/api/v1"
CACHE_FILE = ROOT / "scripts" / "prospects_cache.json"

# Our slug → MLB Pipeline URL slug (only where they differ)
MLB_URL_SLUGS = {
    "blue-jays": "bluejays",
    "red-sox": "redsox",
    "white-sox": "whitesox",
}


# ─── helpers ────────────────────────────────────────────────────────────────

def fetch_json(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "morning-lineup/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def fetch_html(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def fetch_api(path, **params):
    if params:
        url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    else:
        url = f"{API}{path}"
    return fetch_json(url)


def load_team_slugs():
    return [f.stem for f in sorted(TEAMS_DIR.glob("*.json"))]


def load_team_config(slug):
    return json.loads((TEAMS_DIR / f"{slug}.json").read_text())


# ─── Phase 1: MLB Pipeline Rankings ────────────────────────────────────────

def scrape_pipeline_rankings(slugs):
    """Scrape mlb.com/milb/prospects/{team} for official Pipeline Top 30."""
    print("\n=== Phase 1: MLB Pipeline Rankings ===\n")
    rankings = {}

    for i, slug in enumerate(slugs):
        url_slug = MLB_URL_SLUGS.get(slug, slug)
        url = f"https://www.mlb.com/milb/prospects/{url_slug}"

        try:
            html = fetch_html(url)
            decoded = htmlmod.unescape(html)

            # Find the rankings section by the selection slug
            sel_key = f"sel-pr-2026-{url_slug}"
            idx = decoded.find(sel_key)
            if idx < 0:
                print(f"  [{i+1}/{len(slugs)}] {slug} — no rankings found in page")
                rankings[slug] = []
                continue

            chunk = decoded[idx:idx+200000]

            # Split on RankedPlayerEntity to isolate each entry
            entries = chunk.split("RankedPlayerEntity")
            prospects = []
            for entry in entries[1:]:
                rank_m = re.search(r'"rank":(\d+)', entry)
                pid_m = re.search(r'"Person:(\d+)"', entry)
                pos_m = re.search(r'"position":"([^"]+)"', entry)
                if rank_m and pid_m and pos_m:
                    prospects.append({
                        "id": int(pid_m.group(1)),
                        "rank": int(rank_m.group(1)),
                        "position": pos_m.group(1),
                    })

            # Batch resolve names via MLB API
            if prospects:
                ids_str = ",".join(str(p["id"]) for p in prospects)
                pdata = fetch_api(f"/people", personIds=ids_str)
                names = {p["id"]: p["fullName"] for p in pdata.get("people", [])}
                pos_api = {p["id"]: p.get("primaryPosition", {}).get("abbreviation", "?")
                           for p in pdata.get("people", [])}
                for p in prospects:
                    p["name"] = names.get(p["id"], f"Unknown ({p['id']})")
                    # Use API position if Pipeline position is generic
                    if p["position"] in ("INF", "OF", "UTIL", "SS/2B"):
                        p["position"] = pos_api.get(p["id"], p["position"])

            rankings[slug] = prospects
            print(f"  [{i+1}/{len(slugs)}] {slug} — {len(prospects)} prospects")

        except Exception as e:
            print(f"  [{i+1}/{len(slugs)}] {slug} — FAILED: {e}")
            rankings[slug] = []

        time.sleep(0.8)

    return rankings


# ─── Phase 2: Roster Crawl for Level Assignment ────────────────────────────

def crawl_rosters(slugs):
    """Fetch minor league rosters to determine each prospect's current level."""
    print("\n=== Phase 2: Roster Crawl (for levels) ===\n")
    # Returns {player_id: level} across all affiliates
    level_map = {}

    level_order = {"AAA": 0, "AA": 1, "A+": 2, "A": 3}

    for i, slug in enumerate(slugs):
        cfg = load_team_config(slug)
        affiliates = cfg.get("affiliates", [])
        team_count = 0

        for aff in affiliates:
            try:
                data = fetch_api(f"/teams/{aff['id']}/roster", rosterType="fullSeason")
                for entry in data.get("roster", []):
                    pid = entry.get("person", {}).get("id")
                    level = aff["level"]
                    # Keep highest level if player appears on multiple rosters
                    if pid not in level_map or level_order.get(level, 9) < level_order.get(level_map[pid], 9):
                        level_map[pid] = level
                        team_count += 1
                time.sleep(0.3)
            except Exception as e:
                print(f"  [{i+1}/{len(slugs)}] {slug} — {aff['level']} FAILED: {e}")
                time.sleep(0.3)

        print(f"  [{i+1}/{len(slugs)}] {slug} — {len(affiliates)} affiliates")

    print(f"\n  Total: {len(level_map)} players mapped to levels")
    return level_map


# ─── Phase 3: Merge & Write ────────────────────────────────────────────────

def merge_and_write(slugs, rankings, level_map, force_all=False, max_per_team=15):
    """Combine rankings with level data and write prospects.json files."""
    print("\n=== Phase 3: Merge & Write ===\n")
    total_written = 0

    for slug in slugs:
        prospects_file = TEAMS_DIR / slug / "prospects.json"

        # Skip existing non-empty files unless forced
        if not force_all and prospects_file.exists():
            content = prospects_file.read_text().strip()
            if content and content != "[]" and len(content) > 2:
                print(f"  {slug}: SKIPPED (already populated)")
                continue

        ranked = rankings.get(slug, [])
        if not ranked:
            print(f"  {slug}: NO RANKINGS — writing empty []")
            prospects_file.write_text("[]\n")
            continue

        # Build output, capping at max_per_team
        output = []
        no_level = []
        for p in sorted(ranked, key=lambda x: x["rank"]):
            if len(output) >= max_per_team:
                break
            level = level_map.get(p["id"])
            if not level:
                no_level.append(p["name"])
                continue  # Skip players not on any minor league roster (likely MLB)
            output.append({
                "id": p["id"],
                "name": p["name"],
                "position": p["position"],
                "rank": p["rank"],
                "level": level,
            })

        prospects_file.parent.mkdir(parents=True, exist_ok=True)
        prospects_file.write_text(json.dumps(output, indent=2) + "\n")
        total_written += 1

        skip_str = f" (MLB/no roster: {', '.join(no_level)})" if no_level else ""
        print(f"  {slug}: {len(output)} prospects{skip_str}")

    print(f"\nDone. Wrote {total_written} files.")


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    force_all = "--force-all" in args
    from_cache = "--from-cache" in args
    single_team = None
    if "--team" in args:
        idx = args.index("--team")
        if idx + 1 < len(args):
            single_team = args[idx + 1]

    all_slugs = load_team_slugs()

    if single_team:
        if single_team not in all_slugs:
            print(f"Unknown team slug: {single_team}")
            print(f"Available: {', '.join(all_slugs)}")
            sys.exit(1)
        slugs = [single_team]
    else:
        slugs = all_slugs

    if from_cache and CACHE_FILE.exists():
        print("Loading from cache...")
        cache = json.loads(CACHE_FILE.read_text())
        rankings = cache["rankings"]
        level_map = {int(k): v for k, v in cache["level_map"].items()}
    else:
        rankings = scrape_pipeline_rankings(slugs)
        level_map = crawl_rosters(slugs)

        # Cache
        cache = {
            "rankings": rankings,
            "level_map": {str(k): v for k, v in level_map.items()},
        }
        CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False))
        print(f"\nCached to {CACHE_FILE}")

    merge_and_write(slugs, rankings, level_map, force_all=force_all)


if __name__ == "__main__":
    main()
