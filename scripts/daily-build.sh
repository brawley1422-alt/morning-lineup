#!/usr/bin/env bash
# Daily build — games pass only:
#   Builds every team + the landing page (skipping LLM columnists), then
#   deploys. Every team build is bounded by `timeout` so a hung network call
#   can never stall the whole paper.
#
# The columnists section is disabled in build.py (commit 39b6a78a, 2026-04-15,
# pending a rework), so there's no second pass here — it would rebuild and
# redeploy all 30 teams for zero new content. To regenerate columns manually
# once the section is re-enabled, run scripts/columnists-pass.sh directly.
set -euo pipefail

LOG="/home/tooyeezy/personal/morning-lineup/scripts/daily-build.log"
REPO="/home/tooyeezy/personal/morning-lineup"
TEAMS_DIR="$REPO/teams"

exec > >(tee -a "$LOG") 2>&1
echo "=== $(date '+%Y-%m-%d %H:%M:%S %Z') GAMES PASS ==="

cd "$REPO"
source ~/.secrets/morning-lineup.env

# Persistent=true fires this at boot, often before DNS is up — every fetch
# then dies with "name resolution" and the run deploys stale pages. Wait
# (up to 5 min) until MLB's API actually resolves before doing anything.
for i in $(seq 1 60); do
  getent hosts statsapi.mlb.com >/dev/null 2>&1 && break
  echo "Waiting for network... ($i/60)"
  sleep 5
done
if ! getent hosts statsapi.mlb.com >/dev/null 2>&1; then
  echo "FATAL: no network after 5 minutes, aborting (nothing deployed)"
  exit 1
fi

git pull --ff-only origin main 2>/dev/null || true

# --- Pass 1: Games ---------------------------------------------------------
export MORNING_LINEUP_SKIP_COLUMN_GEN=1

FAILED=0
TOTAL=0
for cfg in "$TEAMS_DIR"/*.json; do
  team=$(basename "$cfg" .json)
  TOTAL=$((TOTAL + 1))
  echo "Building $team..."
  timeout 180 python3 build.py --team "$team" \
    || { echo "WARN: $team failed or timed out, continuing"; FAILED=$((FAILED + 1)); }
done

echo "Building landing page..."
timeout 120 python3 build.py --landing \
  || echo "WARN: landing page failed, continuing"

# A couple of flaky teams is fine; a mostly-failed run means something
# systemic (network, API change) — deploying would overwrite good pages
# with nothing new while looking like a success.
if [ "$FAILED" -ge $((TOTAL / 2)) ]; then
  echo "FATAL: $FAILED/$TOTAL teams failed — skipping deploy"
  exit 1
fi

echo "Deploying games pass..."
python3 deploy.py

echo "Verifying cubs page..."
STATUS=$(curl -sI https://brawley1422-alt.github.io/morning-lineup/cubs/ | head -1)
echo "Cubs: $STATUS"

echo "=== GAMES PASS DONE $(date '+%Y-%m-%d %H:%M:%S %Z') ==="
