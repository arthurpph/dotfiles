#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:---install}"
if [[ "$EUID" == 0 ]]; then
    echo 'Run this script as your regular user; it invokes sudo when needed.' >&2
    exit 1
fi

install_packages() {
    # Full upgrade prevents partial upgrades on Arch. Keep pacman's prompts.
    mapfile -t packages < <(sed '/^[[:space:]]*#/d; /^[[:space:]]*$/d' "$ROOT/packages.txt")
    mapfile -t aur_packages < <(sed '/^[[:space:]]*#/d; /^[[:space:]]*$/d' "$ROOT/packages-aur.txt")
    sudo pacman -Syu --needed "${packages[@]}"
    if command -v yay >/dev/null; then
        aur_helper=yay
    elif command -v paru >/dev/null; then
        aur_helper=paru
    else
        build_dir=$(mktemp -d)
        git clone https://aur.archlinux.org/yay-bin.git "$build_dir/yay-bin"
        (cd "$build_dir/yay-bin" && makepkg -si --needed)
        aur_helper=yay
    fi
    "$aur_helper" -S --needed "${aur_packages[@]}"
}

case "$MODE" in
    --install) install_packages; MODE=--apply ;;
    --packages) install_packages; exit 0 ;;
    --dry-run|--apply) ;;
    *) echo "Usage: $0 [--install|--dry-run|--packages|--apply]" >&2; exit 2 ;;
esac

python3 - "$ROOT" "$MODE" <<'PY'
import os
import shutil
import sys
import tempfile
from pathlib import Path

root = Path(sys.argv[1])
source = root / 'config'
apply = sys.argv[2] == '--apply'
home = Path.home()
config = home / '.config'
backup = None

def save(path):
    global backup
    if backup is None:
        root = home / '.config-backups'
        root.mkdir(parents=True, exist_ok=True)
        backup = Path(tempfile.mkdtemp(prefix='hyprland-', dir=root))
    target = backup / path.relative_to(home)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(target))

# A config directory may itself be a symlink to another dotfiles checkout.
# Back it up before creating directories, so writes never follow that link.
directories = [config] + [config / p.relative_to(source) for p in sorted(source.rglob('*')) if p.is_dir()]
directories += [config / 'alacritty', home / 'Pictures', home / 'Pictures/Wallpapers']
for directory in directories:
    if apply:
        if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
            save(directory)
        directory.mkdir(parents=True, exist_ok=True)

links = [(src, config / src.relative_to(source)) for src in sorted(source.rglob('*')) if src.is_file()]
links.append((root.parent / 'alacritty/alacritty.toml', config / 'alacritty/alacritty.toml'))
links.extend((src, home / 'Pictures/Wallpapers' / src.name) for src in sorted((root / 'assets/wallpapers').glob('*.png')))
for src, dst in links:
    if not src.is_file():
        raise FileNotFoundError(src)
    if dst.is_symlink() and dst.resolve() == src.resolve():
        continue
    print(f'{dst} -> {src}')
    if apply:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if os.path.lexists(dst):
            save(dst)
        dst.symlink_to(src)

if backup:
    print(f'Backup: {backup}')
if apply:
    (home / 'Pictures' / 'Wallpapers').mkdir(parents=True, exist_ok=True)
PY

if [[ "$MODE" == --apply ]]; then
    bash "$ROOT/setup-vencord.sh"
    bash "$ROOT/setup-pywalfox.sh"
    sudo python3 "$ROOT/setup-firefox-policy.py"
    if [[ -f "$HOME/.cache/43pr/palette.json" ]]; then
        python3 "$HOME/.config/43pr/bin/theme.py" apply
    else
        python3 "$HOME/.config/43pr/bin/theme.py" preset dracula
    fi
    bash "$ROOT/setup-spicetify.sh"
    echo 'Installation complete. Log into Hyprland; applications will be configured when opened.'
else
    echo 'Preview complete; no files were changed.'
fi
