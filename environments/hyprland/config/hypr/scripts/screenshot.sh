#!/usr/bin/env bash
set -euo pipefail

case "${1:-region}" in
    region) region=$(slurp) || exit 0 ;;
    full)
        output=$(hyprctl -j monitors | jq -er '.[] | select(.focused) | .name')
        ;;
    *) exit 2 ;;
esac

capture=$(mktemp "${XDG_RUNTIME_DIR:-/tmp}/hypr-screenshot-XXXXXX.png")
# Keep the preview available until the OSD has finished fading out.
trap 'sleep 3; rm -f -- "$capture"' EXIT
if [[ "${1:-region}" == region ]]; then
    grim -g "$region" "$capture"
else
    grim -o "$output" "$capture"
fi
wl-copy --type image/png < "$capture"
qs ipc call screenshot notify "$capture" || true
swappy -f "$capture"
