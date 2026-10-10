#!/usr/bin/env python3
import json
import shutil
import sys
import tempfile
from pathlib import Path


def discord_location(home):
    local = home / '.config/discord'
    if any(local.glob('app-*/resources/app.asar')):
        return local
    for candidate in (Path('/opt/discord'), Path('/usr/share/discord')):
        if (candidate / 'resources/app.asar').is_file():
            return candidate
    return None


def discord_patched(location):
    resources = sorted(location.glob('app-*/resources'))
    if not resources:
        resources = [location / 'resources']
    resources = [p for p in resources if (p / 'app.asar').is_file()]
    if not resources:
        return False
    latest = max(resources)
    return ((latest / '_app.asar').is_file()
            and 'Vencord' in (latest / 'app.asar').read_bytes().decode(errors='ignore'))


def discord_settings(home):
    path = home / '.config/Vencord/settings/settings.json'
    existing = path.read_text() if path.exists() else '{}'
    settings = json.loads(existing)
    settings['useQuickCss'] = True
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not json.loads(existing).get('useQuickCss', False):
        backup_dir = home / '.config-backups'
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = Path(tempfile.mkdtemp(prefix='hyprland-vencord-', dir=backup_dir))
        shutil.copy2(path, backup / 'settings.json')
    if json.loads(existing) != settings:
        path.write_text(json.dumps(settings, indent=4) + '\n')
    css = path.parent / 'quickCss.css'
    css.touch(exist_ok=True)


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'discord-location':
        print(discord_location(Path.home()) or '')
    elif action == 'discord-patched':
        sys.exit(0 if discord_patched(Path(sys.argv[2])) else 1)
    elif action == 'discord-settings':
        discord_settings(Path.home())
    else:
        raise ValueError(action)
