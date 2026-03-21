#!/bin/bash
# March Madness local sync — runs every 5 min via LaunchAgent
REPO="/tmp/march-madness-tracker"
LOG="$REPO/sync.log"
PYTHON="/Volumes/Samsung990Pro/caches/local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3"

GAME_DATES="2026-03-21 2026-03-22 2026-03-27 2026-03-28 2026-03-29 2026-03-30 2026-04-04 2026-04-06"
TODAY=$(date +%Y-%m-%d)
HOUR=$(date +%H)
MINUTE=$(date +%M)
NOW_MIN=$((HOUR * 60 + MINUTE))

# 9:10 AM = 550 min, 8:00 PM = 1200 min
IN_WINDOW=false
for d in $GAME_DATES; do
  if [ "$TODAY" = "$d" ] && [ "$NOW_MIN" -ge 550 ] && [ "$NOW_MIN" -le 1200 ]; then
    IN_WINDOW=true; break
  fi
done

if [ "$IN_WINDOW" = "false" ]; then
  echo "$(date): Outside game window" >> "$LOG"; exit 0
fi

cd "$REPO" || exit 1
git pull --rebase --quiet 2>/dev/null

echo "$(date): Syncing..." >> "$LOG"
PYTHONPATH="$REPO" "$PYTHON" -m scoring sync >> "$LOG" 2>&1

git add data/
if ! git diff --cached --quiet; then
  ROUND=$("$PYTHON" -c "import json; print(json.load(open('data/leaderboard.json'))['current_round'])")
  git commit -m "chore: local sync $ROUND — $(date +'%Y-%m-%d %H:%M')" --quiet
  git pull --rebase --quiet 2>/dev/null
  git push --quiet 2>> "$LOG"
  echo "$(date): Pushed" >> "$LOG"
else
  echo "$(date): No changes" >> "$LOG"
fi
