import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
import broccoli_rish_shell

class PhysicalBoundaryTests(unittest.TestCase):
    def test_missing_transport_never_executes_raw_rish_or_local_shell(self):
        with patch.object(broccoli_rish_shell, '_transport_class', return_value=None), patch.object(broccoli_rish_shell.subprocess, 'run') as run:
            rc, output = broccoli_rish_shell.shell('id')
        self.assertEqual(rc, 78)
        self.assertIn('RISH_TRANSPORT_MISSING', output)
        run.assert_not_called()

    def test_legacy_shell_entrypoints_delegate_once_with_command_intact(self):
        for relative in ['rish.sh', 'rish_exec.sh', 'rish_run.sh', 'lib/rish_cmd.sh', 'lib/rish_shell.sh', 'lib/adb_rish.sh']:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp)
                (target / 'lib').mkdir()
                source = target / relative
                source.write_text((ROOT / relative).read_text())
                (target / 'lib/rish_run.sh').write_text('#!/bin/bash\nprintf "CANONICAL:%s\\n" "$*"\nexit 23\n')
                env = dict(os.environ, HOME=tmp, BROCCOLI_DIR=tmp)
                result = subprocess.run(['bash', str(source), 'echo "quoted value"; id'], env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 23, result.stderr)
                self.assertEqual(result.stdout, 'CANONICAL:echo "quoted value"; id\n')

if __name__ == '__main__':
    unittest.main()

class PhysicalConsumerTests(unittest.TestCase):
    def test_legacy_python_launcher_uses_canonical_wrapper(self):
        import rish_adb
        result = subprocess.CompletedProcess([], 17, 'proof', 'error')
        with patch.object(rish_adb.subprocess, 'run', return_value=result) as run:
            actual = rish_adb.rish_shell('echo "a b"; id')
        self.assertEqual(actual.returncode, 17)
        self.assertEqual(run.call_args.args[0], ['bash', str(ROOT / 'lib/rish_run.sh'), 'echo "a b"; id'])

    def test_runtime_does_not_fallback_to_host_shell(self):
        from runtime import device
        with patch.object(device, 'run', return_value={'returncode':78, 'ok':False}) as run:
            result = device.privileged('id')
        self.assertFalse(result['ok'])
        self.assertEqual(run.call_args.args[0], ['bash', str(ROOT / 'lib/rish_run.sh'), 'id'])
        self.assertEqual(run.call_count, 1)

class PhysicalSourcePolicyTests(unittest.TestCase):
    def test_current_sources_do_not_embed_raw_rish_launches(self):
        import re
        retired = ('Agent/', 'BroccoliWorkspaceBackup/', 'state/', '~/', '_quarantine/', 'broccoli-core/', 'inbox/', 'tests/')
        bypasses = []
        for name in subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines():
            if not name.endswith(('.py', '.sh')) or name.startswith(retired): continue
            source = (ROOT / name).read_text(errors='replace')
            if re.search(r'\[\s*[\x22\x27]rish[\x22\x27]|\brish\s+-c|\|\s*rish\b', source):
                bypasses.append(name)
        self.assertEqual(bypasses, [], 'Raw physical launch bypasses: ' + ', '.join(bypasses))

class ArchiveRetirementTests(unittest.TestCase):
    def test_archived_python_and_shell_launchers_stop_before_dispatch(self):
        import json
        manifest = __import__('json').loads((ROOT / 'docs/validation/physical-rish-retirement-2026-10-07.json').read_text())
        paths = manifest['retired_archived_launchers']
        for extension, executable in [('.py', sys.executable), ('.sh', 'bash')]:
            path = next(name for name in paths if name.endswith(extension))
            result = subprocess.run([executable, str(ROOT / path)], text=True, capture_output=True, timeout=5)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('RETIRED_PHYSICAL_RISH', result.stderr)
