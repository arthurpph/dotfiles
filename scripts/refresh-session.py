#!/usr/bin/env python3
"""Refresh running components after applying changed dotfiles."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import signal
import subprocess
import sys
import tempfile
import time

CONFIG = runpy.run_path(str(Path(__file__).with_name('install-configs.py')))


def group_for(path):
    parts = path.parts
    if parts[0] == '.config':
        name = parts[1]
        if name == 'hypr':
            return 'portal' if parts[2] == 'xdph.conf' or parts[-1] == 'share-picker.sh' else 'hyprland'
        return name
    return 'files'


def fingerprint(path):
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def snapshot(root, desktop, home):
    groups = {}
    for _, destination, _ in CONFIG['plan'](root, desktop, home):
        relative = destination.relative_to(home)
        group = group_for(relative)
        if desktop in ('kde', 'cosmic') and group not in CONFIG['APPS'] and relative.parts[0] != 'Pictures':
            group = desktop
        groups.setdefault(group, {})[str(relative)] = fingerprint(destination)
    if desktop == 'hyprland':
        # These outputs can change during setup even when repository links do not.
        discord = CONFIG_DESKTOP['discord_location'](home)
        patches = sorted(discord.glob('app-*/resources/app.asar')) if discord else []
        if discord and not patches:
            patches = [discord / 'resources/app.asar']
        groups['discord-runtime'] = {str(p): fingerprint(p) for p in patches}
        settings = home / '.config/Vencord/settings/settings.json'
        groups['discord-runtime']['useQuickCss'] = (
            json.loads(settings.read_text()).get('useQuickCss', False) if settings.is_file() else False)
        firefox = [Path('/usr/lib/firefox/distribution/policies.json')]
        for directory in (home / '.mozilla/native-messaging-hosts', home / '.config/mozilla/native-messaging-hosts'):
            firefox.extend(directory.glob('*pywalfox*.json'))
        groups['firefox-runtime'] = {str(p): fingerprint(p) for p in firefox}
    return groups


CONFIG_DESKTOP = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'environments/hyprland/scripts/setup-desktop.py'))


def read_json(path):
    return json.loads(path.read_text()) if path.is_file() else {}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.refresh-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as output:
            json.dump(data, output, indent=2)
            output.write('\n')
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def run(*arguments):
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=20)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f'{arguments[0]} exited {result.returncode}')
    return result.stdout


def processes(names):
    found = []
    for directory in Path('/proc').glob('[0-9]*'):
        try:
            if directory.stat().st_uid != os.getuid():
                continue
            name = (directory / 'comm').read_text().strip()
            argv = [p.decode() for p in (directory / 'cmdline').read_bytes().split(b'\0') if p]
            if name not in names or not argv or any(p.startswith('--type=') for p in argv):
                continue
            # Only touch applications belonging to this graphical session.
            environment = dict(p.split('=', 1) for p in (directory / 'environ').read_text().split('\0') if '=' in p)
            key = 'WAYLAND_DISPLAY' if os.environ.get('WAYLAND_DISPLAY') else 'DISPLAY'
            if os.environ.get(key) and environment.get(key) != os.environ[key]:
                continue
            found.append((int(directory.name), argv))
        except (OSError, UnicodeError, ValueError):
            continue
    return found


def wait_until(predicate, timeout=12):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() >= deadline:
            raise RuntimeError('Timed out waiting for the old instance to exit; it was not force-killed.')
        time.sleep(0.1)


def restart_application(names, executable, home):
    running = processes(names)
    pending = home / '.local/state/dotfiles' / f'{executable}.restart.json'
    launches = read_json(pending).get('launches', [])
    if not running and not launches:
        return
    launcher = shutil.which(executable)
    if not launcher:
        raise RuntimeError(f'{executable} is not installed')
    if not launches:
        launches = [arguments[1:] for _, arguments in running]
        write_json(pending, {'launches': launches})
    for pid, _ in running:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        wait_until(lambda: not Path(f'/proc/{pid}').exists())
    while launches:
        arguments = launches[0]
        log = home / '.local/state/dotfiles' / f'{executable}.log'
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open('ab') as output:
            child = subprocess.Popen([launcher, *arguments], cwd=home, stdin=subprocess.DEVNULL,
                                     stdout=output, stderr=output, start_new_session=True)
        time.sleep(0.3)
        if child.poll() not in (None, 0):
            raise RuntimeError(f'{executable} failed to start; see {log}')
        launches.pop(0)
        write_json(pending, {'launches': launches})
    pending.unlink(missing_ok=True)


def quickshell_instances(path):
    output = run('qs', 'list', '--path', str(path), '-j').strip()
    # Quickshell prints this human-readable message even with -j when there
    # are no instances. This is the normal state between stop and start.
    if not output or output.startswith('No running instances'):
        return []
    try:
        instances = json.loads(output)
    except json.JSONDecodeError as error:
        raise RuntimeError(f'Unexpected output from qs list: {output[:300]}') from error
    if not isinstance(instances, list) or any(
            not isinstance(instance, dict)
            or not isinstance(instance.get('config_path'), str)
            or not isinstance(instance.get('id'), str) for instance in instances):
        raise RuntimeError('qs list returned an invalid instance list')
    return instances


def quickshell(home):
    path = home / '.config/quickshell/shell.qml'

    def matching():
        return [instance for instance in quickshell_instances(path)
                if Path(instance['config_path']).resolve() == path.resolve()]

    for instance in matching():
        run('qs', 'kill', '--id', instance['id'])
    # --no-duplicate alone can silently skip launch while the old instance exits.
    wait_until(lambda: not matching())
    run('qs', '--path', str(path), '--daemonize', '--no-duplicate')
    wait_until(lambda: bool(matching()))


def refresh_group(group, home, environment):
    hyprland = bool(environment.get('HYPRLAND_INSTANCE_SIGNATURE') and environment.get('WAYLAND_DISPLAY'))
    sway = bool(environment.get('SWAYSOCK') and environment.get('WAYLAND_DISPLAY'))
    graphical = bool(environment.get('WAYLAND_DISPLAY') or environment.get('DISPLAY'))
    if group == 'alacritty':
        (home / '.config/alacritty/alacritty.toml').touch()
    elif group == 'kitty':
        for pid, _ in processes({'kitty'}):
            os.kill(pid, signal.SIGUSR1)
    elif group == 'tmux' and shutil.which('tmux'):
        result = subprocess.run(['tmux', 'list-sessions'], capture_output=True, timeout=5)
        if result.returncode == 0:
            run('tmux', 'source-file', str(home / '.config/tmux/tmux.conf'))
    elif group == 'hyprland' and hyprland:
        run('hyprctl', 'reload')
        errors = run('hyprctl', 'configerrors').strip()
        if errors and errors != 'ok':
            raise RuntimeError(errors)
    elif group == 'quickshell' and hyprland:
        quickshell(home)
    elif group == 'portal' and hyprland:
        service = 'xdg-desktop-portal-hyprland.service'
        status = subprocess.run(['systemctl', '--user', 'is-active', '--quiet', service], timeout=5)
        if status.returncode == 0:
            run('systemctl', '--user', 'restart', service)
    elif group == 'sway' and sway:
        results = json.loads(run('swaymsg', '-t', 'command', 'reload'))
        if not all(result.get('success') for result in results):
            raise RuntimeError(f'Sway reload failed: {results}')
    elif group == 'waybar' and sway:
        for pid, _ in processes({'waybar'}):
            os.kill(pid, signal.SIGUSR2)
    elif group == 'discord-runtime' and graphical:
        restart_application({'Discord', 'discord'}, 'discord', home)
    elif group == 'spicetify' and graphical:
        if hyprland:
            run('bash', str(home / '.config/43pr/bin/spicetify-theme.sh'))
        else:
            restart_application({'spotify', 'Spotify'}, 'spotify', home)
    elif group == 'firefox-runtime' and graphical and processes({'firefox'}):
        # Firefox has no supported external restart command that preserves all
        # open tabs/private windows. Theme updates already use the native host.
        print('Firefox: extension/policy changes require a browser restart; its open windows were preserved.')
    elif group == 'kde' and 'KDE' in environment.get('XDG_CURRENT_DESKTOP', ''):
        if shutil.which('qdbus6'):
            run('qdbus6', 'org.kde.KWin', '/KWin', 'reconfigure')


def state_paths(home, desktop):
    directory = home / '.local/state/dotfiles'
    return directory / f'{desktop}.json', directory / f'{desktop}.pending.json'


def begin(root, desktop, home):
    _, pending = state_paths(home, desktop)
    # Preserve the original baseline if an earlier installation was interrupted.
    if not pending.exists():
        write_json(pending, snapshot(root, desktop, home))


def finish(root, desktop, home, environment=None):
    environment = os.environ if environment is None else environment
    state, pending = state_paths(home, desktop)
    previous = read_json(state)
    before = read_json(pending)
    current = snapshot(root, desktop, home)
    failed = []
    for group in sorted(current.keys() | previous.keys()):
        baseline = previous.get(group)
        if baseline is None and group.endswith('-runtime'):
            baseline = before.get(group, {})
        changed_during_install = before.get(group, {}) != current.get(group, {})
        if baseline == current.get(group) and not changed_during_install:
            continue
        try:
            refresh_group(group, home, environment)
            print(f'Updated configuration: {group}.')
            if group in current:
                previous[group] = current[group]
            else:
                previous.pop(group, None)
            # A failed later action must not repeat already successful restarts.
            write_json(state, previous)
            if group in current:
                before[group] = current[group]
            else:
                before.pop(group, None)
            write_json(pending, before)
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
            print(f'Could not refresh {group}: {error}', file=sys.stderr)
            failed.append(group)
    if failed:
        print('Configuration files are installed. Run the installer again to retry pending refreshes.', file=sys.stderr)
        return 1
    pending.unlink(missing_ok=True)
    print('Automatic refresh complete. Applications without live reload use the configuration on their next launch.')
    return 0


if __name__ == '__main__':
    action, root, desktop = sys.argv[1:]
    if action == 'begin':
        begin(Path(root).resolve(), desktop, Path.home())
    elif action == 'finish':
        sys.exit(finish(Path(root).resolve(), desktop, Path.home()))
    else:
        raise ValueError(f'Unknown action: {action}')
