#!/usr/bin/env python3
"""
evening.py — Watch for every team's game to go Final, then rebuild that
team's Morning Lineup page. Replaces the old Cubs-only watcher.

Reads teams/*.json to discover the team list, polls the MLB Schedule API
every 5 minutes, and tracks which teams still have games in progress.
When a team's game reaches Final, waits 2 minutes for stats to settle,
then runs `build.py --team <slug>`. Once every tracked team is handled
(or max runtime elapses), runs deploy.py once.

Usage:
  python3 evening.py            # normal mode
  python3 evening.py --dry-run  # log status without rebuilding
  python3 evening.py --team cubs  # single-team watcher (legacy behavior)

Set up as a systemd user timer via ops/morning-lineup-evening.timer.
"""
import json, subprocess, sys, time, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    CT = ZoneInfo("America/Chicago")
except (ImportError, KeyError):
    CT = timezone(timedelta(hours=-5))

API = "https://statsapi.mlb.com/api/v1"
ROOT = Path(__file__).parent
POLL_INTERVAL = 300       # 5 minutes
SETTLE_DELAY = 120        # 2 minutes after Final before rebuilding
MAX_RUNTIME = 6 * 3600    # 6 hours

DRY_RUN = "--dry-run" in sys.argv


def _arg(name):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return None


TEAM_OVERRIDE = _arg("--team")


def load_team_roster():
    """Return list of (slug, team_id) tuples from teams/*.json. When
    --team is supplied, restrict to that single slug."""
    out = []
    teams_dir = ROOT / "teams"
    for cfg_file in sorted(teams_dir.glob("*.json")):
        slug = cfg_file.stem
        if TEAM_OVERRIDE and slug != TEAM_OVERRIDE:
            continue
        try:
            cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
            tid = int(cfg.get("id") or cfg.get("team_id") or 0)
            if tid:
                out.append((slug, tid))
        except Exception as e:
            print(f"  warning: failed to load {cfg_file.name}: {e}", flush=True)
    return out


def fetch(path, **params):
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{API}{path}?{qs}"
    else:
        url = f"{API}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "morning-lineup/0.2"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def get_todays_schedule():
    """One schedule fetch for the entire day — avoids 30 per-team hits.
    Returns list of game dicts."""
    today = datetime.now(tz=CT).date().isoformat()
    sched = fetch("/schedule", sportId=1, date=today)
    games = []
    for d in sched.get("dates", []):
        for g in d.get("games", []):
            games.append(g)
    return games


def games_for_team(all_games, team_id):
    """Filter today's slate to games involving a specific team."""
    out = []
    for g in all_games:
        teams = g.get("teams", {}) or {}
        away_id = (teams.get("away") or {}).get("team", {}).get("id")
        home_id = (teams.get("home") or {}).get("team", {}).get("id")
        if away_id == team_id or home_id == team_id:
            out.append(g)
    return out


def all_final(games):
    if not games:
        return False
    return all(
        g.get("status", {}).get("abstractGameState") == "Final"
        for g in games
    )


def game_status_str(games):
    parts = []
    for g in games:
        state = g.get("status", {}).get("detailedState", "Unknown")
        away = g.get("teams", {}).get("away", {}).get("team", {}).get("abbreviation", "?")
        home = g.get("teams", {}).get("home", {}).get("team", {}).get("abbreviation", "?")
        parts.append(f"{away}@{home}:{state}")
    return ", ".join(parts)


def rebuild_team(slug):
    """Run build.py --team <slug>. Returns True on success."""
    print(f"\n--- REBUILDING {slug} ---", flush=True)
    r = subprocess.run(
        [sys.executable, str(ROOT / "build.py"), "--team", slug],
        cwd=str(ROOT),
    )
    if r.returncode != 0:
        print(f"  build.py --team {slug} failed: exit {r.returncode}", flush=True)
        return False
    return True


def deploy_all():
    """Run deploy.py once at the end of the watcher. Relies on unit 4's
    verify_pages_build to catch silent GH Pages failures."""
    print("\n--- DEPLOYING ---", flush=True)
    r = subprocess.run([sys.executable, str(ROOT / "deploy.py")], cwd=str(ROOT))
    if r.returncode != 0:
        print(f"deploy.py failed: exit {r.returncode}", flush=True)
        return False
    print("--- EVENING EDITION DEPLOYED ---", flush=True)
    return True


def main():
    start = time.time()
    now_str = datetime.now(tz=CT).strftime("%I:%M %p CT")
    print(f"Evening Edition watcher started at {now_str}", flush=True)
    if DRY_RUN:
        print("(dry run — will not rebuild or deploy)", flush=True)
    if TEAM_OVERRIDE:
        print(f"(single-team mode: {TEAM_OVERRIDE})", flush=True)

    teams = load_team_roster()
    if not teams:
        print("No teams to watch. Exiting.", flush=True)
        return
    team_ids = {tid: slug for slug, tid in teams}

    # Initial schedule sweep
    try:
        all_games = get_todays_schedule()
    except Exception as e:
        print(f"  Startup fetch failed: {e} — retrying in {POLL_INTERVAL}s", flush=True)
        time.sleep(POLL_INTERVAL)
        try:
            all_games = get_todays_schedule()
        except Exception as e2:
            print(f"  Retry failed: {e2} — exiting", flush=True)
            return

    # Build initial tracking set: teams with at least one game today
    pending = {}  # slug -> [game dicts]
    for slug, tid in teams:
        g = games_for_team(all_games, tid)
        if g:
            pending[slug] = g
    if not pending:
        print("No team games today. Exiting.", flush=True)
        return

    print(
        f"Tracking {len(pending)} team(s): "
        + ", ".join(sorted(pending.keys())),
        flush=True,
    )

    # Handle any already-Final games up front
    rebuilt = []
    for slug in list(pending.keys()):
        if all_final(pending[slug]):
            print(f"{slug}: already Final — {game_status_str(pending[slug])}", flush=True)
            if not DRY_RUN:
                if rebuild_team(slug):
                    rebuilt.append(slug)
            del pending[slug]

    # Poll loop
    while pending:
        elapsed = time.time() - start
        if elapsed > MAX_RUNTIME:
            print(
                f"Max runtime ({MAX_RUNTIME//3600}h) reached. "
                f"{len(pending)} team(s) still pending: {sorted(pending.keys())}",
                flush=True,
            )
            break

        time.sleep(POLL_INTERVAL)

        try:
            all_games = get_todays_schedule()
        except Exception as e:
            print(f"  Poll error: {e} — retrying", flush=True)
            continue

        now_str = datetime.now(tz=CT).strftime("%I:%M %p")
        just_finalized = []
        for slug in list(pending.keys()):
            tid = next((t for s, t in teams if s == slug), None)
            if tid is None:
                del pending[slug]
                continue
            games = games_for_team(all_games, tid)
            pending[slug] = games
            if all_final(games):
                just_finalized.append(slug)
                print(f"\n{now_str} — FINAL {slug}: {game_status_str(games)}", flush=True)
            else:
                print(f"  {now_str} — {slug}: {game_status_str(games)}", flush=True)

        if just_finalized:
            print(f"Waiting {SETTLE_DELAY}s for stats to settle…", flush=True)
            time.sleep(SETTLE_DELAY)
            for slug in just_finalized:
                if not DRY_RUN:
                    if rebuild_team(slug):
                        rebuilt.append(slug)
                del pending[slug]

    if rebuilt and not DRY_RUN:
        deploy_all()
    else:
        print("Nothing to deploy.", flush=True)


if __name__ == "__main__":
    main()
