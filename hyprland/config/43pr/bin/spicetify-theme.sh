#!/usr/bin/env bash
set -euo pipefail
command -v spicetify >/dev/null || exit 0

# First-time installation is handled by setup-spicetify.sh after rendering.
spotify_path=$(spicetify config spotify_path)
[[ -f "$spotify_path/Apps/xpui/spicetify-config.json" ]] || exit 0
[[ "$(spicetify config current_theme)" == text-43pr ]] || exit 0
spicetify refresh --no-restart

if command -v hyprctl >/dev/null && [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
    hyprctl eval 'local window = hl.get_window("class:^(Spotify|spotify)$"); if window then hl.dispatch(hl.dsp.send_shortcut({ mods = "CTRL SHIFT", key = "R", window = window })) end'
fi
