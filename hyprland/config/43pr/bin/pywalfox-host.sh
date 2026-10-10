#!/usr/bin/env bash
set -euo pipefail

pywalfox_bin="$HOME/.local/share/43pr/pywalfox/bin/pywalfox"
if [[ ! -x "$pywalfox_bin" ]]; then
    pywalfox_bin=$(command -v pywalfox)
fi

# Fetch the palette after the extension connects, including on its first launch.
(
    for attempt in {1..20}; do
        if [[ -S "${TMPDIR:-/tmp}/pywalfox_socket_$UID" ]]; then
            sleep 1
            python3 "$HOME/.config/43pr/bin/theme-apps.py" firefox
            exit
        fi
        sleep 0.5
    done
) >/dev/null 2>&1 &
exec "$pywalfox_bin" "$@"
