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
DESKTOP = runpy.run_path(str(ROOT / 'setup-desktop.py'))
POLICY = runpy.run_path(str(ROOT / 'setup-firefox-policy.py'))


class InstallerTests(unittest.TestCase):
    def test_fresh_home_and_repeated_config_application(self):
        script = (ROOT / 'install.sh').read_text().split("<<'PY'\n", 1)[1].split('\nPY\n', 1)[0]
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            argv = ['installer', str(ROOT), '--apply']
            with patch.object(Path, 'home', return_value=home), patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()):
                exec(compile(script, str(ROOT / 'install.sh'), 'exec'), {})
            self.assertEqual((home / '.config/alacritty/alacritty.toml').resolve(), ROOT.parent / 'alacritty/alacritty.toml')
            self.assertTrue((home / 'Pictures/Wallpapers/WallPaper 13.png').is_file())
            wallpapers = list((ROOT / 'assets/wallpapers').iterdir())
            self.assertEqual({p.name for p in (home / 'Pictures/Wallpapers').iterdir()}, {p.name for p in wallpapers})
            for wallpaper in wallpapers:
                self.assertEqual((home / 'Pictures/Wallpapers' / wallpaper.name).resolve(), wallpaper)
            self.assertTrue((home / '.config/43pr/bin/pywalfox-host.sh').is_file())
            with patch.object(Path, 'home', return_value=home), patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()):
                exec(compile(script, str(ROOT / 'install.sh'), 'exec'), {})
            self.assertFalse((home / '.config-backups').exists())

    def test_existing_alacritty_directory_link_is_backed_up(self):
        script = (ROOT / 'install.sh').read_text().split("<<'PY'\n", 1)[1].split('\nPY\n', 1)[0]
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            other = home / 'other-config'
            other.mkdir()
            original = other / 'alacritty.toml'
            original.write_text('original config')
            (home / '.config').mkdir()
            (home / '.config/alacritty').symlink_to(other)
            with patch.object(Path, 'home', return_value=home), patch.object(sys, 'argv', ['installer', str(ROOT), '--apply']), contextlib.redirect_stdout(io.StringIO()):
                exec(compile(script, str(ROOT / 'install.sh'), 'exec'), {})
            self.assertEqual(original.read_text(), 'original config')
            self.assertEqual(len(list((home / '.config-backups').glob('hyprland-*/.config/alacritty'))), 1)

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

    def test_default_install_orders_packages_and_application_setups(self):
        for helper_installed in (False, True):
            with self.subTest(helper_installed=helper_installed), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                binaries = root / 'bin'
                binaries.mkdir()
                log = root / 'calls'
                for name in ('dirname', 'sed', 'mktemp', 'cat'):
                    (binaries / name).symlink_to(shutil.which(name))
                for name in ('sudo', 'bash', 'python3', 'git', 'makepkg'):
                    extra = ''
                    if name == 'python3':
                        extra = 'if [[ "$1" == - ]]; then /usr/bin/cat >/dev/null; fi\n'
                    elif name == 'git':
                        extra = '/usr/bin/mkdir -p "$3"\n'
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
                subprocess.run(['/bin/bash', str(ROOT / 'install.sh')], env=environment, check=True, capture_output=True, text=True)
                calls = log.read_text().splitlines()
                self.assertTrue(calls[0].startswith('sudo pacman -Syu --needed'))
                aur = next(i for i, line in enumerate(calls) if line.startswith('yay -S --needed'))
                config = next(i for i, line in enumerate(calls) if line.startswith('python3 - '))
                vencord = calls.index(f'bash {ROOT}/setup-vencord.sh')
                pywalfox = calls.index(f'bash {ROOT}/setup-pywalfox.sh')
                policy = calls.index(f'sudo python3 {ROOT}/setup-firefox-policy.py')
                spotify = calls.index(f'bash {ROOT}/setup-spicetify.sh')
                self.assertLess(aur, config)
                self.assertLess(config, vencord)
                self.assertLess(vencord, pywalfox)
                self.assertLess(pywalfox, policy)
                self.assertLess(policy, spotify)
                if not helper_installed:
                    self.assertTrue(any(line.startswith('git clone https://aur.archlinux.org/yay-bin.git') for line in calls))


if __name__ == '__main__':
    unittest.main()
