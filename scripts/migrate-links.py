#!/usr/bin/env python3
"""Update existing repository links after reorganizing the dotfiles."""
import os
from pathlib import Path
import sys


def migrated_source(source, root):
    source = Path(source)
    try:
        relative = source.relative_to(root)
    except ValueError:
        return None
    parts = relative.parts
    profile = root / 'environments/hyprland'
    if parts and parts[0] in ('43pr', 'matugen'):
        return profile / 'theme' / relative
    if parts and parts[0] in ('btop', 'cava', 'fastfetch', 'kitty', 'spicetify', 'swappy', 'xed', 'neofetch', 'mimeapps.list'):
        return profile / 'apps' / relative
    if relative == Path('environments/hyprland/targets.toml'):
        return profile / 'theme/43pr/targets.toml'
    if parts[:2] == ('hyprland', 'config') and len(parts) > 2:
        subtree = Path(*parts[2:])
        if parts[2] == '43pr' and subtree == Path('43pr/targets.toml'):
            return profile / 'theme/43pr/targets.toml'
        for directory in ('apps', 'theme'):
            destination = profile / directory / subtree
            if destination.exists():
                return destination
        return root / 'environments/hyprland/config' / subtree
    if parts[:3] == ('hyprland', 'assets', 'wallpapers'):
        return root / 'wallpapers' / Path(*parts[3:])
    if parts and parts[0] in ('sway', 'kde', 'cosmic'):
        return root / 'environments' / relative
    if parts and parts[0] == 'waybar':
        return root / 'environments/sway' / relative
    return None


def migrate(root, home):
    for directory in (home / '.config', home / 'Pictures/Wallpapers'):
        for parent, directories, files in os.walk(directory, followlinks=False):
            for name in directories + files:
                link = Path(parent) / name
                if not link.is_symlink():
                    continue
                raw = Path(os.readlink(link))
                source = Path(os.path.abspath(raw if raw.is_absolute() else link.parent / raw))
                new = migrated_source(source, root)
                if new is None or not new.exists():
                    continue
                temporary = link.with_name(link.name + '.dotfiles-migration')
                temporary.symlink_to(new)
                os.replace(temporary, link)
                print(f'Updated: {link} -> {new}')


if __name__ == '__main__':
    migrate(Path(sys.argv[1]).resolve(), Path.home())
