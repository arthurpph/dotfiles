#!/usr/bin/env bash
set -euo pipefail

stylesheet="${XDG_CACHE_HOME:-$HOME/.cache}/43pr/share-picker.qss"
args=(-style Fusion)
if [[ -f "$stylesheet" ]]; then
    args+=(-stylesheet "$stylesheet")
fi
exec /usr/bin/hyprland-share-picker "${args[@]}" "$@"
