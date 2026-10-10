#!/usr/bin/env python3
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

BEGIN = '/* BEGIN 43PR THEME */'
END = '/* END 43PR THEME */'


def merge_css(existing, rendered):
    block = f'{BEGIN}\n{rendered.rstrip()}\n{END}\n'
    pattern = re.escape(BEGIN) + r'.*?' + re.escape(END) + r'\n?'
    if BEGIN in existing:
        return re.sub(pattern, lambda _: block, existing, flags=re.S)
    return existing + ('\n' if existing and not existing.endswith('\n') else '') + block


def discord():
    root = Path.home() / '.config/Vencord/settings'
    settings = root / 'settings.json'
    if not settings.is_file():
        return
    if not json.loads(settings.read_text()).get('useQuickCss', False):
        print('Discord: enable Use QuickCSS in Vencord settings.', file=sys.stderr)
        return
    path = root / 'quickCss.css'
    existing = path.read_text() if path.exists() else ''
    rendered = (Path.home() / '.cache/43pr/discord.css').read_text()
    updated = merge_css(existing, rendered)
    if updated != existing:
        # Keep the inode so Vencord's file watcher continues receiving changes.
        path.write_text(updated)


def firefox():
    executable = shutil.which('pywalfox')
    local = Path.home() / '.local/share/43pr/pywalfox/bin/pywalfox'
    if executable is None and local.is_file():
        executable = str(local)
    if executable:
        palette = json.loads((Path.home() / '.cache/43pr/palette.json').read_text())
        rgb = [int(palette['bg'][i:i + 2], 16) for i in (1, 3, 5)]
        mode = 'light' if sum(a * b for a, b in zip(rgb, (0.2126, 0.7152, 0.0722))) > 140 else 'dark'
        subprocess.run([executable, mode], check=True, timeout=3)
        subprocess.run([executable, 'update'], check=True, timeout=3)


if __name__ == '__main__':
    {'discord': discord, 'firefox': firefox}[sys.argv[1]]()
