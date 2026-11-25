#!/usr/bin/env bash
# Run only on session start, not on configuration reload.
set -u
for app in alacritty discord firefox; do
    if command -v "$app" >/dev/null && ! pgrep -x "$app" >/dev/null; then
        "$app" &
    fi
done

wallpaper=$(python3 - <<'PY'
import json
from pathlib import Path
home = Path.home()
state = home / '.local/state/43pr/state.json'
try:
    saved = json.loads(state.read_text()).get('wallpaper', '')
except (OSError, ValueError):
    saved = ''
path = Path(saved) if saved else home / 'Pictures/Wallpapers/WallPaper 13.png'
if not path.is_file():
    path = home / 'Pictures/Wallpapers/WallPaper 13.png'
print(path)
PY
)
if [[ -f "$wallpaper" ]] && command -v awww >/dev/null; then
    for attempt in {1..15}; do
        if awww query >/dev/null 2>&1; then
            awww img "$wallpaper" --resize crop
            break
        fi
        sleep 0.2
    done
fi

if command -v gpu-screen-recorder >/dev/null; then
    bash "$HOME/.config/hypr/scripts/replay.sh" start &
fi
