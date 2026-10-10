#!/usr/bin/env python3
"""Apply shared applications and exactly one desktop profile, with backups."""
import os
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

APPS = ('nvim', 'tmux', 'alacritty')


def plan(root, desktop, home):
    config = home / '.config'
    items = []

    def tree(source, destination, portable=False):
        for src in sorted(source.rglob('*')):
            if src.is_file() and not any(part in {'.git', '__pycache__'} for part in src.relative_to(source).parts):
                content = None
                if src.name == 'xdph.conf' and src.parent.name == 'hypr':
                    content = src.read_text().replace('@SHARE_PICKER@', str(config / 'hypr/scripts/share-picker.sh')).encode()
                if src.name == 'config-xpui.ini' and src.parent.name == 'spicetify':
                    content = src.read_text().replace('/home/arthurpiana/', str(home) + '/').encode()
                if portable:
                    text = src.read_text().replace('/home/arthurpiana/wallpapers/', str(home / 'Pictures/Wallpapers') + '/')
                    text = text.replace('/home/arthurpiana/', str(home) + '/')
                    text = text.replace('~/wallpapers/', '~/Pictures/Wallpapers/')
                    if text != src.read_text():
                        content = text.encode()
                items.append((src, destination / src.relative_to(source), content))

    for name in APPS:
        tree(root / name, config / name)
    for src in sorted((root / 'wallpapers').iterdir()):
        if src.is_file():
            items.append((src, home / 'Pictures/Wallpapers' / src.name, None))
    env = root / 'environments' / desktop
    if desktop == 'hyprland':
        tree(env / 'config', config)
        tree(env / 'apps', config)
        tree(env / 'theme', config)
    elif desktop == 'sway':
        items.append((env / 'config', config / 'sway/config', (env / 'config').read_text().replace('~/wallpapers/', '~/Pictures/Wallpapers/').encode()))
        tree(env / 'waybar', config / 'waybar')
    elif desktop == 'cosmic':
        for directory in sorted(env.glob('com.system76.*')):
            tree(directory, config / 'cosmic' / directory.name, portable=True)
    elif desktop == 'kde':
        destinations = {
            'save/configs/': config,
            'save/app_layouts/': home / '.local/share/kxmlgui5',
            'save/autostart/': config / 'autostart',
            'export/share_folder/': home / '.local/share',
            'export/home_folder/': home,
        }
        with zipfile.ZipFile(env / 'default-config.knsv') as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                for prefix, destination in destinations.items():
                    if member.filename.startswith(prefix):
                        relative = Path(member.filename[len(prefix):])
                        if relative.is_absolute() or '..' in relative.parts:
                            raise ValueError(f'Unsafe profile path: {member.filename}')
                        content = archive.read(member)
                        if b'\0' not in content:
                            content = content.replace(b'/home/arthurpiana/wallpapers/', (str(home / 'Pictures/Wallpapers') + '/').encode())
                            content = content.replace(b'/home/arthurpiana/', (str(home) + '/').encode())
                        items.append((None, destination / relative, content))
                        break
    elif desktop != 'none':
        raise ValueError(f'Unknown desktop: {desktop}')
    return items


def apply_config(root, desktop, home, apply=True):
    items = plan(root, desktop, home)
    backup = None

    def save(path):
        nonlocal backup
        if backup is None:
            directory = home / '.config-backups'
            directory.mkdir(parents=True, exist_ok=True)
            backup = Path(tempfile.mkdtemp(prefix=f'dotfiles-{desktop}-', dir=directory))
        destination = backup / path.relative_to(home)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(destination))

    def ensure_directory(directory):
        if directory == home:
            return
        ensure_directory(directory.parent)
        if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
            save(directory)
        directory.mkdir(exist_ok=True)

    for src, dst, content in items:
        if content is None and not src.is_file():
            raise FileNotFoundError(src)
        # Check parents as well: a directory symlink must be backed up first.
        linked_parent = any(p.is_symlink() for p in dst.parents if p != home and home in p.parents)
        if content is None:
            same = dst.is_symlink() and dst.resolve() == src.resolve()
        else:
            same = dst.is_file() and not dst.is_symlink() and dst.read_bytes() == content
        if same and not linked_parent:
            continue
        print(f'{dst} <- {src or "KDE profile"}')
        if not apply:
            continue
        ensure_directory(dst.parent)
        if os.path.lexists(dst):
            save(dst)
        if content is None:
            dst.symlink_to(src)
        else:
            dst.write_bytes(content)
    if backup:
        print(f'Backup: {backup}')


if __name__ == '__main__':
    apply_config(Path(sys.argv[1]).resolve(), sys.argv[2], Path.home(), sys.argv[3] == '--apply')
