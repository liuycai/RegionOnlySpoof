#!/usr/bin/python3
"""Exercise installer file operations in a temporary tree, never /Library."""
import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('refresh_setup', Path(__file__).with_name('setup.py'))
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class InstallCases(unittest.TestCase):
    def exercise_install(self, partial_directory, upgrade=False, previous_version='1.0.0'):
        validated_package = setup.package()
        with tempfile.TemporaryDirectory(prefix='refresh-installer-', dir='/private/tmp') as td:
            base = Path(td)
            helper = base / 'helper.py'
            plist = base / 'task.plist'
            state = base / 'state'
            log = base / 'task.log'
            if upgrade:
                helper.write_bytes((setup.ROOT / ('previous/helper-' + previous_version + '.py')).read_bytes())
                plist.write_bytes(validated_package[setup.LABEL + '.plist'])
            if partial_directory:
                state.mkdir(mode=0o755)
            actual_stat = Path.stat
            def root_state_stat(path, *args, **kwargs):
                value = actual_stat(path, *args, **kwargs)
                if path in (state, helper, plist):
                    return types.SimpleNamespace(st_uid=0, st_gid=80, st_mode=value.st_mode)
                return value
            operations = []
            registered = upgrade
            def command(args):
                nonlocal registered
                operations.append(args)
                if args[1] == 'bootstrap':
                    registered = True
                    return subprocess.CompletedProcess(args, 0, '', '')
                if args[1] == 'bootout':
                    registered = False
                    return subprocess.CompletedProcess(args, 0, '', '')
                if registered:
                    return subprocess.CompletedProcess(args, 0, 'state = not running\nruns = 1\nlast exit code = 0\n', '')
                return subprocess.CompletedProcess(args, 113, '', 'Could not find service')
            with mock.patch.object(setup, 'HELPER', helper), mock.patch.object(setup, 'PLIST', plist), \
                 mock.patch.object(setup, 'STATE_DIR', state), mock.patch.object(setup, 'LOG', log), \
                 mock.patch.object(setup, 'package', return_value=validated_package), \
                 mock.patch.object(setup, 'command', side_effect=command), \
                 mock.patch.object(Path, 'stat', root_state_stat), \
                 mock.patch.object(setup.os, 'chown') as chown, \
                 mock.patch.object(setup.os, 'fchown') as fchown, \
                 contextlib.redirect_stdout(io.StringIO()):
                setup.install()
            chown.assert_called_once_with(state, 0, 0)
            self.assertEqual(fchown.call_count, 3)
            self.assertEqual(helper.read_bytes(), (setup.ROOT / 'helper.py').read_bytes())
            self.assertEqual(plist.read_bytes(), (setup.ROOT / (setup.LABEL + '.plist')).read_bytes())
            self.assertTrue(log.exists())
            self.assertEqual(helper.stat().st_mode & 0o777, 0o755)
            self.assertEqual(plist.stat().st_mode & 0o777, 0o644)
            self.assertEqual(sum(op[1] == 'bootstrap' for op in operations), 1)
            self.assertEqual(sum(op[1] == 'bootout' for op in operations), int(upgrade))

    def test_first_install_creates_files_and_registers_job(self):
        self.exercise_install(False)

    def test_retry_after_directory_creation_continues_safely(self):
        self.exercise_install(True)

    def test_known_previous_version_is_replaced_and_reregistered(self):
        self.exercise_install(True, upgrade=True)

    def test_upgrade_from_timeout_fix_is_supported(self):
        self.exercise_install(True, upgrade=True, previous_version='1.0.1')

    def test_upgrade_from_cold_boot_validated_version_is_supported(self):
        self.exercise_install(True, upgrade=True, previous_version='1.1.0')

    def test_unknown_existing_helper_is_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as td:
            path = Path(td) / 'helper.py'
            path.write_bytes(b'not our managed helper')
            with mock.patch.object(setup, 'HELPER', path):
                with self.assertRaises(RuntimeError):
                    setup.check_managed(path, b'new version')


if __name__ == '__main__':
    unittest.main()
