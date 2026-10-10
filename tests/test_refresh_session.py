import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('refresh_session', ROOT / 'scripts/refresh-session.py')
REFRESH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REFRESH)


class RefreshTests(unittest.TestCase):
    def make_repository(self, directory):
        root = Path(directory) / 'repo'
        home = Path(directory) / 'home'
        home.mkdir()
        for name in ('alacritty', 'tmux', 'nvim', 'wallpapers', 'environments/hyprland/config/quickshell'):
            (root / name).mkdir(parents=True)
        (root / 'alacritty/alacritty.toml').write_text('original terminal config')
        (root / 'environments/hyprland/config/quickshell/shell.qml').write_text('original shell')
        return root, home

    def apply_and_refresh(self, root, home):
        REFRESH.begin(root, 'hyprland', home)
        REFRESH.CONFIG['apply_config'](root, 'hyprland', home)
        return REFRESH.finish(root, 'hyprland', home, {})

    def test_git_pull_changes_are_detected_through_existing_symlinks(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()), \
                patch.object(REFRESH, 'refresh_group') as refresh:
            root, home = self.make_repository(directory)
            self.assertEqual(self.apply_and_refresh(root, home), 0)
            refresh.reset_mock()
            # A pull changes the target before the installer even starts.
            (root / 'environments/hyprland/config/quickshell/shell.qml').write_text('//@ pragma UseQApplication\nnew shell')
            self.assertEqual(self.apply_and_refresh(root, home), 0)
            self.assertEqual([call.args[0] for call in refresh.call_args_list], ['quickshell'])
            refresh.reset_mock()
            self.assertEqual(self.apply_and_refresh(root, home), 0)
            refresh.assert_not_called()

    def test_restoring_local_override_refreshes_even_if_last_installed_content_matches(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()), \
                patch.object(REFRESH, 'refresh_group') as refresh:
            root, home = self.make_repository(directory)
            self.apply_and_refresh(root, home)
            destination = home / '.config/alacritty/alacritty.toml'
            destination.unlink()
            destination.write_text('local override currently loaded by terminal')
            refresh.reset_mock()
            self.assertEqual(self.apply_and_refresh(root, home), 0)
            self.assertEqual([call.args[0] for call in refresh.call_args_list], ['alacritty'])

    def test_failed_refresh_is_retried_without_repeating_successful_actions(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            root, home = self.make_repository(directory)
            calls = []

            def fail_shell(group, *_):
                calls.append(group)
                if group == 'quickshell':
                    raise RuntimeError('temporary startup failure')

            with patch.object(REFRESH, 'refresh_group', side_effect=fail_shell):
                self.assertEqual(self.apply_and_refresh(root, home), 1)
            self.assertIn('alacritty', calls)
            with patch.object(REFRESH, 'refresh_group') as refresh:
                self.assertEqual(self.apply_and_refresh(root, home), 0)
                self.assertEqual([call.args[0] for call in refresh.call_args_list], ['quickshell'])
            self.assertFalse(REFRESH.state_paths(home, 'hyprland')[1].exists())

    def test_interrupted_application_setup_keeps_the_original_runtime_baseline(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()), \
                patch.object(REFRESH, 'refresh_group') as refresh:
            root, home = self.make_repository(directory)
            with patch.object(REFRESH, 'snapshot', return_value={'discord-runtime': {'patch': 'old'}}):
                REFRESH.begin(root, 'hyprland', home)
            with patch.object(REFRESH, 'snapshot', return_value={'discord-runtime': {'patch': 'new'}}):
                REFRESH.begin(root, 'hyprland', home)
                self.assertEqual(REFRESH.finish(root, 'hyprland', home, {}), 0)
            self.assertEqual([call.args[0] for call in refresh.call_args_list], ['discord-runtime'])

    def test_inactive_desktops_do_not_start_or_stop_graphical_components(self):
        with patch.object(REFRESH, 'run') as run, patch.object(REFRESH, 'quickshell') as shell, \
                patch.object(REFRESH, 'restart_application') as restart:
            for group in ('hyprland', 'quickshell', 'portal', 'sway', 'waybar', 'discord-runtime', 'spicetify', 'firefox-runtime', 'kde'):
                REFRESH.refresh_group(group, Path('/nonexistent'), {})
            run.assert_not_called()
            shell.assert_not_called()
            restart.assert_not_called()

    def test_quickshell_restart_waits_and_only_targets_the_managed_configuration(self):
        home = Path('/home/example')
        managed = {'id': 'ours', 'config_path': str(home / '.config/quickshell/shell.qml')}
        other = {'id': 'other', 'config_path': '/elsewhere/shell.qml'}
        replies = iter(([managed, other], [managed, other], [other], [managed, other]))

        def fake_run(*arguments):
            return json.dumps(next(replies)) if arguments[:2] == ('qs', 'list') else ''

        with patch.object(REFRESH, 'run', side_effect=fake_run) as run, patch.object(REFRESH.time, 'sleep'):
            REFRESH.quickshell(home)
        actions = [call.args for call in run.call_args_list if call.args[:2] != ('qs', 'list')]
        self.assertEqual(actions, [('qs', 'kill', '--id', 'ours'),
                                   ('qs', '--path', str(home / '.config/quickshell/shell.qml'), '--daemonize', '--no-duplicate')])

    def test_quickshell_restarts_after_the_cli_returns_a_non_json_empty_list(self):
        home = Path('/home/example')
        path = home / '.config/quickshell/shell.qml'
        managed = {'id': 'ours', 'config_path': str(path)}
        empty = f'No running instances for "{path}"\nUse --all to list all instances.\n'
        replies = iter((json.dumps([managed]), empty, json.dumps([managed])))

        def fake_run(*arguments):
            return next(replies) if arguments[:2] == ('qs', 'list') else ''

        with patch.object(REFRESH, 'run', side_effect=fake_run) as run:
            REFRESH.quickshell(home)
        run.assert_any_call('qs', 'kill', '--id', 'ours')
        run.assert_any_call('qs', '--path', str(path), '--daemonize', '--no-duplicate')

    def test_quickshell_can_start_when_no_instance_exists(self):
        home = Path('/home/example')
        path = home / '.config/quickshell/shell.qml'
        replies = iter(('', 'No running instances.\n', json.dumps([{'id': 'new', 'config_path': str(path)}])))

        def fake_run(*arguments):
            return next(replies) if arguments[:2] == ('qs', 'list') else ''

        with patch.object(REFRESH, 'run', side_effect=fake_run) as run:
            REFRESH.quickshell(home)
        self.assertFalse(any(call.args[:2] == ('qs', 'kill') for call in run.call_args_list))
        run.assert_any_call('qs', '--path', str(path), '--daemonize', '--no-duplicate')

    def test_unexpected_quickshell_output_is_reported_instead_of_ignored(self):
        with patch.object(REFRESH, 'run', return_value='Unexpected CLI failure'):
            with self.assertRaisesRegex(RuntimeError, 'Unexpected output from qs list'):
                REFRESH.quickshell_instances(Path('/home/example/shell.qml'))

    @unittest.skipUnless(shutil.which('qs'), 'Quickshell CLI is not installed')
    def test_actual_quickshell_cli_without_a_running_instance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'shell.qml'
            path.write_text('import Quickshell\nShellRoot {}\n')
            self.assertEqual(REFRESH.quickshell_instances(path), [])

    def test_failed_application_launch_is_retried_even_after_the_old_process_exits(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(REFRESH.shutil, 'which', return_value='/usr/bin/discord'), \
                patch.object(REFRESH.os, 'kill') as kill, patch.object(REFRESH, 'wait_until'), patch.object(REFRESH.time, 'sleep'):
            home = Path(directory)
            with patch.object(REFRESH, 'processes', return_value=[(123, ['Discord', '--start-minimized'])]), \
                    patch.object(REFRESH.subprocess, 'Popen', return_value=SimpleNamespace(poll=lambda: 1)):
                with self.assertRaises(RuntimeError):
                    REFRESH.restart_application({'Discord'}, 'discord', home)
            kill.assert_called_once()
            pending = home / '.local/state/dotfiles/discord.restart.json'
            self.assertTrue(pending.exists())
            with patch.object(REFRESH, 'processes', return_value=[]), \
                    patch.object(REFRESH.subprocess, 'Popen', return_value=SimpleNamespace(poll=lambda: None)) as launch:
                REFRESH.restart_application({'Discord'}, 'discord', home)
            self.assertEqual(launch.call_args.args[0], ['/usr/bin/discord', '--start-minimized'])
            self.assertFalse(pending.exists())


if __name__ == '__main__':
    unittest.main()
