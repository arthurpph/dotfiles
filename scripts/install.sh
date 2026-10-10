#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
ROOT="$1"
DESKTOP="$2"
MODE="$3"

if [[ "$MODE" == --install || "$MODE" == --packages ]]; then
    command -v pacman >/dev/null || { echo 'Package installation requires Arch Linux.' >&2; exit 1; }
    package_lists=("$ROOT/scripts/packages.txt")
    aur_lists=("$ROOT/scripts/packages-aur.txt")
    if [[ "$DESKTOP" != none ]]; then
        package_lists+=("$ROOT/environments/$DESKTOP/packages.txt")
        aur_lists+=("$ROOT/environments/$DESKTOP/packages-aur.txt")
    fi
    mapfile -t packages < <(sed '/^[[:space:]]*#/d; /^[[:space:]]*$/d' "${package_lists[@]}" | sort -u)
    mapfile -t aur_packages < <(sed '/^[[:space:]]*#/d; /^[[:space:]]*$/d' "${aur_lists[@]}" | sort -u)
    sudo pacman -Syu --needed "${packages[@]}"
    if (( ${#aur_packages[@]} )); then
        if command -v yay >/dev/null; then aur_helper=yay
        elif command -v paru >/dev/null; then aur_helper=paru
        else
            build_dir=$(mktemp -d)
            git clone https://aur.archlinux.org/yay-bin.git "$build_dir/yay-bin"
            (cd "$build_dir/yay-bin" && makepkg -si --needed)
            aur_helper=yay
        fi
        "$aur_helper" -S --needed "${aur_packages[@]}"
    fi
    [[ "$MODE" != --packages ]] || exit 0
    MODE=--apply
fi

if [[ "$MODE" != --dry-run ]]; then
    git -C "$ROOT" submodule update --init --recursive
    python3 "$ROOT/scripts/refresh-session.py" begin "$ROOT" "$DESKTOP"
fi
python3 "$ROOT/scripts/install-configs.py" "$ROOT" "$DESKTOP" "$MODE"
if [[ "$MODE" == --dry-run ]]; then
    echo 'Preview complete; no files were changed.'
    exit 0
fi

if [[ "$DESKTOP" == hyprland ]]; then
    bash "$ROOT/environments/hyprland/scripts/setup-vencord.sh"
    bash "$ROOT/environments/hyprland/scripts/setup-pywalfox.sh"
    sudo python3 "$ROOT/environments/hyprland/scripts/setup-firefox-policy.py"
    if [[ -f "$HOME/.cache/43pr/palette.json" ]]; then
        python3 "$HOME/.config/43pr/bin/theme.py" apply
    else
        python3 "$HOME/.config/43pr/bin/theme.py" preset dracula
    fi
    bash "$ROOT/environments/hyprland/scripts/setup-spicetify.sh"
fi
python3 "$ROOT/scripts/refresh-session.py" finish "$ROOT" "$DESKTOP"
echo "Installation complete. Shared applications and $DESKTOP configurations are ready."
