#!/usr/bin/env bash
# Daily build — two phases:
#   Pass 1 (games): fast, skips LLM columnists, must succeed so readers get
#     baseball content on time. Every team build is bounded by `timeout` so
#     a hung network call can never stall the whole paper.
#   Pass 2 (columnists): runs columnists-pass.sh, regenerates AI columns,
#     and redeploys. Allowed to be slow or fail — games are already live.
set -euo pipefail

LOG="/home/tooyeezy/morning-lineup/scripts/daily-build.log"
REPO="/home/tooyeezy/morning-lineup"
TEAMS_DIR="$REPO/teams"

exec > >(tee -a "$LOG") 2>&1
echo "=== $(date '+%Y-%m-%d %H:%M:%S %Z') GAMES PASS ==="

cd "$REPO"
source ~/.secrets/morning-lineup.env

git pull --ff-only origin main 2>/dev/null || true

# --- Pass 1: Games ---------------------------------------------------------
export MORNING_LINEUP_SKIP_COLUMN_GEN=1

for cfg in "$TEAMS_DIR"/*.json; do
  team=$(basename "$cfg" .json)
  echo "Building $team..."
  timeout 180 python3 build.py --team "$team" \
    || echo "WARN: $team failed or timed out, continuing"
done

echo "Building landing page..."
timeout 120 python3 build.py --landing \
  || echo "WARN: landing page failed, continuing"

echo "Deploying games pass..."
python3 deploy.py

echo "Verifying cubs page..."
STATUS=$(curl -sI https://brawley1422-alt.github.io/morning-lineup/cubs/ | head -1)
echo "Cubs: $STATUS"

echo "=== GAMES PASS DONE $(date '+%Y-%m-%d %H:%M:%S %Z') ==="

# --- Pass 2: Columnists ----------------------------------------------------
# Allowed to fail — games are already live. Run in the same shell so logs
# stream into the same file.
bash "$REPO/scripts/columnists-pass.sh" \
  || echo "WARN: columnists pass failed — games pass is already live."

echo "=== ALL PASSES DONE $(date '+%Y-%m-%d %H:%M:%S %Z') ==="
