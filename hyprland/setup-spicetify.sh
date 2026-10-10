#!/usr/bin/env bash
set -euo pipefail

if ! command -v spicetify >/dev/null; then
    echo 'Spicetify is not installed. Run hyprland/install.sh --packages before --apply.' >&2
    exit 1
fi

spotify_path=""
for candidate in \
    "$HOME/.local/share/spotify-launcher/install/usr/share/spotify" \
    /opt/spotify \
    "$HOME/.local/share/flatpak/app/com.spotify.Client/x86_64/stable/active/files/extra/share/spotify" \
    /var/lib/flatpak/app/com.spotify.Client/x86_64/stable/active/files/extra/share/spotify; do
    if [[ -d "$candidate/Apps" ]]; then
        spotify_path="$candidate"
        break
    fi
done
if [[ -z "$spotify_path" ]]; then
    spotify-launcher --no-exec
    spotify_path="$HOME/.local/share/spotify-launcher/install/usr/share/spotify"
    [[ -d "$spotify_path/Apps" ]] || exit 1
fi

prefs_path="$HOME/.config/spotify/prefs"
if [[ "$spotify_path" == *flatpak* ]]; then
    prefs_path="$HOME/.var/app/com.spotify.Client/config/spotify/prefs"
fi
if [[ ! -f "$prefs_path" ]]; then
    version=$("$spotify_path/spotify" --version | sed -n 's/^Spotify version \([^,]*\),.*/\1/p')
    [[ -n "$version" ]] || { echo 'Could not determine the Spotify version.' >&2; exit 1; }
    mkdir -p "${prefs_path%/*}"
    printf 'app.last-launched-version="%s"\n' "$version" > "$prefs_path"
fi

if [[ ! -f "$HOME/.config/spicetify/Themes/text-43pr/color.ini" || ! -f "$HOME/.config/spicetify/Themes/text-43pr/user.css" ]]; then
    python3 "$HOME/.config/43pr/bin/theme.py" apply
fi
spicetify config spotify_path "$spotify_path" prefs_path "$prefs_path" current_theme text-43pr color_scheme 43PR
if [[ -f "$spotify_path/Apps/xpui/spicetify-config.json" ]]; then
    spicetify apply --no-restart
else
    spicetify backup apply --no-restart
fi
bash "$HOME/.config/43pr/bin/spicetify-theme.sh"
echo 'Spicetify applied with the desktop palette.'
