#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
discord_dir="$HOME/.config/discord"
location=$(python3 "$ROOT/setup-desktop.py" discord-location)
if [[ -z "$location" ]]; then
    # Arch's updater package can download the app without launching its GUI.
    mkdir -p "$discord_dir"
    /usr/share/discord/updater_bootstrap --no-zenity "$discord_dir" stable
    location=$(python3 "$ROOT/setup-desktop.py" discord-location)
fi
if [[ -z "$location" ]]; then
    echo 'Discord installation not found after bootstrap.' >&2
    exit 1
fi

if ! python3 "$ROOT/setup-desktop.py" discord-patched "$location"; then
    installer="$HOME/.cache/43pr/VencordInstallerCli-linux"
    mkdir -p "${installer%/*}"
    curl --fail --location --retry 3 \
        https://github.com/Vencord/Installer/releases/latest/download/VencordInstallerCli-linux \
        -o "$installer"
    chmod +x "$installer"
    if [[ -w "$location" ]]; then
        "$installer" --install --location "$location"
    else
        sudo "$installer" --install --location "$location"
    fi
fi
if ! python3 "$ROOT/setup-desktop.py" discord-patched "$location"; then
    echo 'The installer did not apply Vencord to Discord.' >&2
    exit 1
fi
python3 "$ROOT/setup-desktop.py" discord-settings
echo 'Vencord installed and QuickCSS enabled.'
