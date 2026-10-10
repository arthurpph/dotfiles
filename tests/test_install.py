import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
DESKTOP = runpy.run_path(str(ROOT / 'environments/hyprland/scripts/setup-desktop.py'))
POLICY = runpy.run_path(str(ROOT / 'environments/hyprland/scripts/setup-firefox-policy.py'))
CONFIG = runpy.run_path(str(ROOT / 'scripts/install-configs.py'))
MIGRATION = runpy.run_path(str(ROOT / 'scripts/migrate-links.py'))


class InstallerTests(unittest.TestCase):
    def test_fresh_home_and_repeated_config_application(self):
        for desktop in ('hyprland', 'sway', 'cosmic', 'kde', 'none'):
            with self.subTest(desktop=desktop), tempfile.TemporaryDirectory() as directory:
                home = Path(directory)
                with contextlib.redirect_stdout(io.StringIO()):
                    CONFIG['apply_config'](ROOT, desktop, home)
                self.assertEqual((home / '.config/alacritty/alacritty.toml').resolve(), ROOT / 'alacritty/alacritty.toml')
                self.assertTrue((home / '.config/nvim/init.lua').is_file())
                self.assertTrue((home / '.config/tmux/tmux.conf').is_file())
                wallpapers = list((ROOT / 'wallpapers').iterdir())
                self.assertEqual({p.name for p in (home / 'Pictures/Wallpapers').iterdir()}, {p.name for p in wallpapers})
                for wallpaper in wallpapers:
                    self.assertEqual((home / 'Pictures/Wallpapers' / wallpaper.name).resolve(), wallpaper)
                self.assertEqual((home / '.config/hypr').exists(), desktop == 'hyprland')
                self.assertEqual((home / '.config/sway').exists(), desktop == 'sway')
                self.assertEqual((home / '.config/cosmic').exists(), desktop == 'cosmic')
                self.assertEqual((home / '.config/kwinrc').exists(), desktop == 'kde')
                targets = home / '.config/43pr/targets.toml'
                self.assertEqual(targets.exists(), desktop == 'hyprland')
                self.assertEqual((home / '.config/spicetify').exists(), desktop == 'hyprland')
                self.assertEqual((home / '.config/matugen').exists(), desktop == 'hyprland')
                if desktop == 'hyprland':
                    self.assertIn('[hyprlock]', targets.read_text())
                if desktop == 'cosmic':
                    background = home / '.config/cosmic/com.system76.CosmicBackground/v1/all'
                    self.assertIn(str(home / 'Pictures/Wallpapers'), background.read_text())
                    self.assertNotIn('/home/arthurpiana/', background.read_text())
                if desktop == 'sway':
                    self.assertIn('~/Pictures/Wallpapers/', (home / '.config/sway/config').read_text())
                with contextlib.redirect_stdout(io.StringIO()):
                    CONFIG['apply_config'](ROOT, desktop, home)
                self.assertFalse((home / '.config-backups').exists())

    def test_existing_alacritty_directory_link_is_backed_up(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            other = home / 'other-config'
            other.mkdir()
            original = other / 'alacritty.toml'
            original.write_text('original config')
            (home / '.config').mkdir()
            (home / '.config/alacritty').symlink_to(other)
            with contextlib.redirect_stdout(io.StringIO()):
                CONFIG['apply_config'](ROOT, 'none', home)
            self.assertEqual(original.read_text(), 'original config')
            self.assertEqual(len(list((home / '.config-backups').glob('dotfiles-*/.config/alacritty'))), 1)

    def test_existing_links_follow_reorganized_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / '.config'
            config.mkdir()
            links = {
                config / 'hypr': ROOT / 'hyprland/config/hypr',
                config / 'kitty': ROOT / 'hyprland/config/kitty',
                config / 'targets.toml': ROOT / 'hyprland/config/43pr/targets.toml',
            }
            for link, source in links.items():
                link.symlink_to(source)
            with contextlib.redirect_stdout(io.StringIO()):
                MIGRATION['migrate'](ROOT, home)
            self.assertEqual((config / 'hypr').resolve(), ROOT / 'environments/hyprland/config/hypr')
            self.assertEqual((config / 'kitty').resolve(), ROOT / 'environments/hyprland/apps/kitty')
            self.assertEqual((config / 'targets.toml').resolve(), ROOT / 'environments/hyprland/theme/43pr/targets.toml')

    def test_preview_does_not_create_files(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            with contextlib.redirect_stdout(io.StringIO()):
                CONFIG['apply_config'](ROOT, 'kde', home, apply=False)
            self.assertEqual(list(home.iterdir()), [])

    def test_selecting_sway_preserves_existing_hyprland_config(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            hypr = home / '.config/hypr'
            hypr.mkdir(parents=True)
            path = hypr / 'hyprland.lua'
            path.write_text('existing Hyprland config')
            with contextlib.redirect_stdout(io.StringIO()):
                CONFIG['apply_config'](ROOT, 'sway', home)
            self.assertEqual(path.read_text(), 'existing Hyprland config')

    def test_main_script_runs_with_sh_and_interactive_selection(self):
        result = subprocess.run(['/bin/sh', str(ROOT / 'install.sh'), '--dry-run'], input='cosmic\n', check=True, capture_output=True, text=True)
        self.assertIn('Choose a desktop:', result.stdout)
        self.assertIn('/.config/cosmic/', result.stdout)
        self.assertIn('Preview complete; no files were changed.', result.stdout)
        invalid = subprocess.run(['/bin/sh', str(ROOT / 'install.sh'), 'invalid'], capture_output=True, text=True)
        self.assertEqual(invalid.returncode, 2)

    def test_downloaded_script_passes_desktop_and_mode_to_backend(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / 'calls'
            for name in ('git', 'bash'):
                stub = root / name
                stub.write_text(f'#!/bin/sh\nprintf "%s\\n" "{name} $*" >> "$CHECK_LOG"\n')
                stub.chmod(0o755)
            environment = dict(os.environ, PATH=str(root) + ':' + os.environ['PATH'], CHECK_LOG=str(log))
            result = subprocess.run(['/bin/sh', '-c', (ROOT / 'install.sh').read_text(), '--', 'sway', '--dry-run'], env=environment, capture_output=True, text=True, check=True)
            if log.exists():
                calls = log.read_text()
                self.assertIn('sway --dry-run', calls)
                self.assertNotIn('git ', calls)
            else:
                self.assertIn('Would clone', result.stdout)

    def test_vencord_settings_preserve_plugins_and_css(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            root = home / '.config/Vencord/settings'
            root.mkdir(parents=True)
            path = root / 'settings.json'
            path.write_text(json.dumps({'useQuickCss': False, 'plugins': {'Example': {'enabled': True}}}))
            css = root / 'quickCss.css'
            css.write_text('/* personal CSS */')
            DESKTOP['discord_settings'](home)
            result = json.loads(path.read_text())
            self.assertTrue(result['useQuickCss'])
            self.assertEqual(result['plugins'], {'Example': {'enabled': True}})
            self.assertEqual(css.read_text(), '/* personal CSS */')
            DESKTOP['discord_settings'](home)
            self.assertEqual(len(list((home / '.config-backups').iterdir())), 1)

    def test_firefox_policy_preserves_existing_extensions_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'distribution/policies.json'
            path.parent.mkdir()
            original = {'policies': {'DisableTelemetry': True, 'ExtensionSettings': {'example': {'installation_mode': 'allowed'}}}}
            path.write_text(json.dumps(original))
            POLICY['install_policy'](path)
            result = json.loads(path.read_text())
            self.assertTrue(result['policies']['DisableTelemetry'])
            extensions = result['policies']['ExtensionSettings']
            self.assertEqual(extensions['example'], original['policies']['ExtensionSettings']['example'])
            self.assertEqual(extensions['pywalfox@frewacom.org']['installation_mode'], 'normal_installed')
            POLICY['install_policy'](path)
            self.assertEqual(len(list(path.parent.glob('hyprland-policy-backup-*'))), 1)

    def test_other_desktops_do_not_setup_hyprland_theme_apps(self):
        for desktop in ('sway', 'cosmic', 'kde', 'none'):
            with self.subTest(desktop=desktop), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                log = root / 'calls'
                for name in ('git', 'bash', 'python3', 'sudo'):
                    stub = root / name
                    stub.write_text(f'#!/bin/bash\nprintf "%s\\n" "{name} $*" >> "$CHECK_LOG"\n')
                    stub.chmod(0o755)
                environment = dict(os.environ, PATH=str(root), CHECK_LOG=str(log))
                subprocess.run(['/bin/bash', str(ROOT / 'scripts/install.sh'), str(ROOT), desktop, '--apply'], env=environment, check=True, capture_output=True, text=True)
                calls = log.read_text()
                self.assertIn(f'{ROOT}/scripts/install-configs.py {ROOT} {desktop} --apply', calls)
                self.assertNotIn('setup-', calls)
                self.assertNotIn('theme.py', calls)
                self.assertNotIn('sudo ', calls)

    def test_default_install_orders_packages_and_application_setups(self):
        for helper_installed in (False, True):
            with self.subTest(helper_installed=helper_installed), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                binaries = root / 'bin'
                binaries.mkdir()
                log = root / 'calls'
                for name in ('dirname', 'sed', 'mktemp', 'cat', 'sort'):
                    (binaries / name).symlink_to(shutil.which(name))
                for name in ('sudo', 'bash', 'python3', 'git', 'makepkg', 'pacman'):
                    extra = ''
                    if name == 'python3':
                        extra = 'if [[ "$1" == - ]]; then /usr/bin/cat >/dev/null; fi\n'
                    elif name == 'git':
                        extra = 'if [[ "$1" == clone ]]; then /usr/bin/mkdir -p "$3"; fi\n'
                    elif name == 'makepkg':
                        extra = '/usr/bin/cp "$MOCK_YAY_SOURCE" "$MOCK_BIN/yay"\n'
                    stub = binaries / name
                    stub.write_text(f'#!/bin/bash\nprintf "%s\\n" "{name} $*" >> "$CHECK_LOG"\n' + extra)
                    stub.chmod(0o755)
                helper = root / 'yay-source'
                helper.write_text('#!/bin/bash\nprintf "%s\\n" "yay $*" >> "$CHECK_LOG"\n')
                helper.chmod(0o755)
                if helper_installed:
                    shutil.copy2(helper, binaries / 'yay')
                environment = dict(os.environ, PATH=str(binaries), TMPDIR=str(root), CHECK_LOG=str(log), MOCK_BIN=str(binaries), MOCK_YAY_SOURCE=str(helper))
                subprocess.run(['/bin/bash', str(ROOT / 'scripts/install.sh'), str(ROOT), 'hyprland', '--install'], env=environment, check=True, capture_output=True, text=True)
                calls = log.read_text().splitlines()
                self.assertTrue(calls[0].startswith('sudo pacman -Syu --needed'))
                aur = next(i for i, line in enumerate(calls) if line.startswith('yay -S --needed'))
                config = next(i for i, line in enumerate(calls) if line.startswith(f'python3 {ROOT}/scripts/install-configs.py '))
                vencord = calls.index(f'bash {ROOT}/environments/hyprland/scripts/setup-vencord.sh')
                pywalfox = calls.index(f'bash {ROOT}/environments/hyprland/scripts/setup-pywalfox.sh')
                policy = calls.index(f'sudo python3 {ROOT}/environments/hyprland/scripts/setup-firefox-policy.py')
                spotify = calls.index(f'bash {ROOT}/environments/hyprland/scripts/setup-spicetify.sh')
                self.assertLess(aur, config)
                self.assertLess(config, vencord)
                self.assertLess(vencord, pywalfox)
                self.assertLess(pywalfox, policy)
                self.assertLess(policy, spotify)
                if not helper_installed:
                    self.assertTrue(any(line.startswith('git clone https://aur.archlinux.org/yay-bin.git') for line in calls))


if __name__ == '__main__':
    unittest.main()
