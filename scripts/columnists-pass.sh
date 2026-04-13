#!/usr/bin/env bash
# Pass 2 of the daily build — regenerate AI columnist sections for every
# team and redeploy. Runs after the main games pass. Safe to invoke
# manually anytime; uses the date-keyed cache so it won't duplicate work
# if columns have already been generated for today.
set -euo pipefail

LOG="/home/tooyeezy/morning-lineup/scripts/daily-build.log"
REPO="/home/tooyeezy/morning-lineup"
TEAMS_DIR="$REPO/teams"

exec > >(tee -a "$LOG") 2>&1
echo "=== COLUMNISTS PASS $(date '+%Y-%m-%d %H:%M:%S %Z') ==="

cd "$REPO"
source ~/.secrets/morning-lineup.env

# Bail early if Ollama isn't reachable — nothing else will work.
if ! curl -sf --max-time 5 http://localhost:11434/api/tags > /dev/null; then
  echo "Ollama not responding at localhost:11434 — skipping columnists pass."
  echo "=== COLUMNISTS PASS ABORTED $(date '+%Y-%m-%d %H:%M:%S %Z') ==="
  exit 0
fi

unset MORNING_LINEUP_SKIP_COLUMN_GEN

for cfg in "$TEAMS_DIR"/*.json; do
  team=$(basename "$cfg" .json)
  echo "Columnists for $team..."
  timeout 420 python3 build.py --team "$team" \
    || echo "WARN: $team columnist build failed or timed out, continuing"
done

echo "Deploying columnists pass..."
python3 deploy.py

echo "=== COLUMNISTS PASS DONE $(date '+%Y-%m-%d %H:%M:%S %Z') ==="
