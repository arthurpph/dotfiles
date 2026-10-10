#!/usr/bin/env bash
set -euo pipefail

pywalfox_bin=""
if command -v pywalfox >/dev/null; then
    pywalfox_bin=$(command -v pywalfox)
elif [[ -x "$HOME/.local/share/43pr/pywalfox/bin/pywalfox" ]]; then
    pywalfox_bin="$HOME/.local/share/43pr/pywalfox/bin/pywalfox"
elif [[ "${1:---install}" == --register ]]; then
    echo 'Firefox: run environments/hyprland/scripts/setup-pywalfox.sh to install the native host.'
    exit 0
else
    pywalfox_env="$HOME/.local/share/43pr/pywalfox"
    python3 -m venv "$pywalfox_env"
    "$pywalfox_env/bin/python" -m pip install 'pywalfox==2.9.0'
    pywalfox_bin="$pywalfox_env/bin/pywalfox"
fi

host="$HOME/.config/43pr/bin/pywalfox-host.sh"
"$pywalfox_bin" install --executable "$host"
"$pywalfox_bin" install --executable "$host" \
    --manifest-path "$HOME/.config/mozilla/native-messaging-hosts" \
    --profile-path "$HOME/.config/mozilla/firefox"
echo 'Pywalfox installed and registered; the extension receives the palette on startup.'
