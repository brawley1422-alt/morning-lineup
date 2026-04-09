#!/usr/bin/env python3
"""
evening.py — Watch for the Cubs game to go Final, then rebuild the Morning Lineup.

Polls the MLB Schedule API every 5 minutes. When the Cubs game reaches
Final status, waits 2 minutes for stats to settle, then runs build.py
followed by deploy.py.

Usage:
  python3 evening.py           # normal mode
  python3 evening.py --dry-run # check status without rebuilding

Set up as a cron or systemd timer to start at ~6 PM CT daily.
Exits after triggering a rebuild or if no Cubs game is scheduled.
"""
import json, subprocess, sys, time, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    CT = ZoneInfo("America/Chicago")
except (ImportError, KeyError):
    CT = timezone(timedelta(hours=-5))

CUBS_ID = 112
API = "https://statsapi.mlb.com/api/v1"
ROOT = Path(__file__).parent
POLL_INTERVAL = 300  # 5 minutes
SETTLE_DELAY = 120   # 2 minutes after Final before rebuilding
MAX_RUNTIME = 6 * 3600  # 6 hours max (exit by midnight if started at 6 PM)

DRY_RUN = "--dry-run" in sys.argv

def fetch(path, **params):
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{API}{path}?{qs}"
    else:
        url = f"{API}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "morning-lineup/0.1"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def get_cubs_game_today():
    """Find today's Cubs game(s). Returns list of game dicts."""
    today = datetime.now(tz=CT).date().isoformat()
    sched = fetch("/schedule", sportId=1, teamId=CUBS_ID, date=today)
    games = []
    for d in sched.get("dates", []):
        for g in d.get("games", []):
            games.append(g)
    return games

def all_final(games):
    """Check if all games in the list are Final."""
    if not games:
        return False
    return all(
        g.get("status", {}).get("abstractGameState") == "Final"
        for g in games
    )

def any_live(games):
    """Check if any game is currently Live."""
    return any(
        g.get("status", {}).get("abstractGameState") == "Live"
        for g in games
    )

def game_status_str(games):
    """Human-readable status of all games."""
    parts = []
    for g in games:
        state = g.get("status", {}).get("detailedState", "Unknown")
        away = g.get("teams", {}).get("away", {}).get("team", {}).get("abbreviation", "?")
        home = g.get("teams", {}).get("home", {}).get("team", {}).get("abbreviation", "?")
        parts.append(f"{away}@{home}: {state}")
    return ", ".join(parts)

def rebuild():
    """Run build.py then deploy.py."""
    print("\n--- REBUILDING ---", flush=True)
    r1 = subprocess.run([sys.executable, str(ROOT / "build.py")], cwd=str(ROOT))
    if r1.returncode != 0:
        print(f"build.py failed with exit code {r1.returncode}", flush=True)
        return False
    r2 = subprocess.run([sys.executable, str(ROOT / "deploy.py")], cwd=str(ROOT))
    if r2.returncode != 0:
        print(f"deploy.py failed with exit code {r2.returncode}", flush=True)
        return False
    print("--- EVENING EDITION DEPLOYED ---", flush=True)
    return True

def main():
    start = time.time()
    now_str = datetime.now(tz=CT).strftime("%I:%M %p CT")
    print(f"Evening Edition watcher started at {now_str}", flush=True)
    if DRY_RUN:
        print("(dry run — will not rebuild)", flush=True)

    # Check if Cubs have a game today
    try:
        games = get_cubs_game_today()
    except Exception as e:
        print(f"  Startup fetch failed: {e} — retrying in {POLL_INTERVAL}s", flush=True)
        time.sleep(POLL_INTERVAL)
        try:
            games = get_cubs_game_today()
        except Exception as e2:
            print(f"  Retry failed: {e2} — exiting", flush=True)
            return
    if not games:
        print("No Cubs game today. Exiting.", flush=True)
        return

    print(f"Found {len(games)} game(s): {game_status_str(games)}", flush=True)

    # If already Final, trigger immediately
    if all_final(games):
        print("Game(s) already Final.", flush=True)
        if DRY_RUN:
            print("Would rebuild now.", flush=True)
        else:
            rebuild()
        return

    # Poll loop
    while True:
        elapsed = time.time() - start
        if elapsed > MAX_RUNTIME:
            print(f"Max runtime ({MAX_RUNTIME//3600}h) reached. Exiting.", flush=True)
            return

        time.sleep(POLL_INTERVAL)

        try:
            games = get_cubs_game_today()
        except Exception as e:
            print(f"  Poll error: {e} — retrying", flush=True)
            continue

        now_str = datetime.now(tz=CT).strftime("%I:%M %p")
        status = game_status_str(games)

        if all_final(games):
            print(f"\n{now_str} — FINAL: {status}", flush=True)
            print(f"Waiting {SETTLE_DELAY}s for stats to settle...", flush=True)
            time.sleep(SETTLE_DELAY)

            if DRY_RUN:
                print("Would rebuild now.", flush=True)
            else:
                rebuild()
            return
        else:
            print(f"  {now_str} — {status}", flush=True)

if __name__ == "__main__":
    main()
