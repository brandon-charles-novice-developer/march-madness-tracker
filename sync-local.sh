#!/bin/bash
# March Madness local sync — runs every 5 min via LaunchAgent
REPO="/Users/barracuda/Development/projects/march-madness-tracker"
LOG="$REPO/sync.log"

# Resolve Python — try uv-managed first, fall back to system
PYTHON="/Volumes/Samsung990Pro/caches/local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3"
if [ ! -x "$PYTHON" ]; then
  PYTHON="$(command -v python3)"
fi
if [ -z "$PYTHON" ] || [ ! -x "$PYTHON" ]; then
  echo "$(date): ERROR — python3 not found" >> "$LOG"
  exit 1
fi

# Game window: 9:10 AM - 11:00 PM on game days
GAME_DATES="2026-03-21 2026-03-22 2026-03-27 2026-03-28 2026-03-29 2026-03-30 2026-04-04 2026-04-06"
TODAY=$(date +%Y-%m-%d)
HOUR=$(date +%H)
MINUTE=$(date +%M)
NOW_MIN=$((HOUR * 60 + MINUTE))

IN_WINDOW=false
for d in $GAME_DATES; do
  if [ "$TODAY" = "$d" ] && [ "$NOW_MIN" -ge 550 ] && [ "$NOW_MIN" -le 1380 ]; then
    IN_WINDOW=true; break
  fi
done

if [ "$IN_WINDOW" = "false" ]; then
  echo "$(date): Outside game window" >> "$LOG"; exit 0
fi

# Log rotation
if [ -f "$LOG" ] && [ "$(wc -l < "$LOG")" -gt 500 ]; then
  tail -300 "$LOG" > "${LOG}.tmp" && mv "${LOG}.tmp" "$LOG"
fi

cd "$REPO" || exit 1
git pull --rebase --quiet 2>/dev/null

echo "$(date): Syncing..." >> "$LOG"
PYTHONPATH="$REPO" "$PYTHON" -m scoring sync >> "$LOG" 2>&1
SYNC_EXIT=$?
if [ "$SYNC_EXIT" -ne 0 ]; then
  echo "$(date): ERROR — sync failed (exit $SYNC_EXIT)" >> "$LOG"
  exit 1
fi

git add data/
if ! git diff --cached --quiet; then
  LEADERBOARD="$REPO/data/leaderboard.json"
  if [ ! -f "$LEADERBOARD" ]; then
    echo "$(date): ERROR — leaderboard.json not found" >> "$LOG"
    exit 1
  fi
  ROUND=$("$PYTHON" -c "
import json
with open('$LEADERBOARD') as f:
    data = json.load(f)
allowed = ['R64', 'R32', 'S16', 'E8', 'F4', 'Championship']
r = data.get('current_round', 'unknown')
print(r if r in allowed else 'unknown')
")
  git commit -m "chore: local sync ${ROUND} — $(date +'%Y-%m-%d %H:%M')" --quiet
  git pull --rebase --quiet 2>/dev/null
  if ! git push --quiet 2>> "$LOG"; then
    echo "$(date): ERROR — git push failed" >> "$LOG"
    exit 1
  fi
  echo "$(date): Pushed ($ROUND)" >> "$LOG"
else
  echo "$(date): No changes" >> "$LOG"
fi
