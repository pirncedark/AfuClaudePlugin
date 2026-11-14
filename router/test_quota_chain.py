import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yonlendir


class QuotaChainTests(unittest.TestCase):
    def setUp(self):
        legacy = patch.dict(yonlendir.os.environ, {"AFU_CODEX_LEGACY": "1"})
        legacy.start()
        self.addCleanup(legacy.stop)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for name, value in {
            'BASE_DIR': self.root, 'WORK_DIR': str(self.root),
            'OFF_FILE': str(self.root / 'KAPALI'),
            'ACTIVE_AGENT_FILE': str(self.root / 'aktif_ajan.txt'),
        }.items():
            p = patch.object(yonlendir, name, value)
            p.start()
            self.addCleanup(p.stop)
        p = patch.dict(os.environ, {'AFU_ROUTER_CHILD': ''})
        p.start()
        self.addCleanup(p.stop)

    def invoke(self, prompt='normal görev', results=None):
        output = io.StringIO()
        with patch.object(yonlendir, 'resolve_executable', side_effect=lambda x: x), patch.object(
            yonlendir.subprocess, 'run', side_effect=results or [subprocess.CompletedProcess([], 0, 'Tamam', '')]
        ) as run:
            code = yonlendir.main(io.StringIO(json.dumps({'prompt': prompt})), output)
        self.assertEqual(code, 0)
        return json.loads(output.getvalue()) if output.getvalue() else None, run

    def test_default_is_claude(self):
        self.assertEqual(yonlendir.get_active_agent(), 'claude')

    def test_normal_runs_claude(self):
        payload, run = self.invoke()
        self.assertIsNone(payload)
        run.assert_not_called()

    def test_only_claude_codex_on_quota(self):
        yonlendir.set_active_agent('codex')
        quota = subprocess.CompletedProcess([], 1, '', 'HTTP 429')
        payload, run = self.invoke(results=[quota, quota])
        self.assertEqual(run.call_count, 2)
        self.assertEqual(yonlendir.get_active_agent(), 'claude')
        self.assertIn('kota', (payload.get('stopReason') or payload.get('hookSpecificOutput', {}).get('additionalContext', '')).lower())

    def test_codex_quota_goes_to_claude(self):
        yonlendir.set_active_agent('codex')
        payload, run = self.invoke(results=[subprocess.CompletedProcess([], 1, '', 'durum=KOTA'), subprocess.CompletedProcess([], 0, 'Gemini tamam', '')])
        self.assertEqual(run.call_count, 2)
        self.assertEqual(yonlendir.get_active_agent(), 'claude')

    def test_codex_chain_quota_with_zero_exit(self):
        yonlendir.set_active_agent('codex')
        payload, run = self.invoke(results=[subprocess.CompletedProcess([], 0, 'ajan=codex durum=KOTA\nZINCIR: BITTI (KOTA, 1 tur)', ''), subprocess.CompletedProcess([], 0, 'Gemini tamam', '')])
        self.assertEqual(run.call_count, 2)
        self.assertIn('Gemini tamam', (payload.get('stopReason') or payload.get('hookSpecificOutput', {}).get('additionalContext', '')))

    def test_exhaustion_blocks_without_loop(self):
        yonlendir.set_active_agent('codex')
        quota = subprocess.CompletedProcess([], 1, '', 'HTTP 429')
        payload, run = self.invoke(results=[quota] * 2)
        self.assertEqual(run.call_count, 2)
        self.assertFalse(payload['continue'])
        self.assertIn('kota', (payload.get('stopReason') or payload.get('hookSpecificOutput', {}).get('additionalContext', '')).lower())

    def test_normal_error_does_not_advance(self):
        yonlendir.set_active_agent('codex')
        payload, run = self.invoke(results=[subprocess.CompletedProcess([], 1, '', 'invalid configuration')])
        self.assertEqual(run.call_count, 1)
        self.assertFalse(payload['continue'])
        self.assertEqual(yonlendir.get_active_agent(), 'codex')

    def test_success_discussing_quota_is_success(self):
        payload, run = self.invoke('gemini: normal görev', results=[subprocess.CompletedProcess([], 0, 'Fixed rate_limit handler', '')])
        self.assertEqual(run.call_count, 1)
        self.assertIn('Fixed rate_limit handler', (payload.get('stopReason') or payload.get('hookSpecificOutput', {}).get('additionalContext', '')))

    def test_claude_json_quota_with_zero_exit(self):
        quota = json.dumps({'type': 'result', 'is_error': True, 'result': "You've hit your limit"})
        with patch.object(yonlendir, 'resolve_executable', return_value='claude'), patch.object(yonlendir.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, quota, '')):
            result = yonlendir.run_claude('test')
        self.assertEqual(result['status'], 'quota')

    def test_claude_json_success(self):
        result = json.dumps({'type': 'result', 'is_error': False, 'result': 'Claude cevap'})
        with patch.object(yonlendir, 'resolve_executable', return_value='claude'), patch.object(yonlendir.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, result, '')):
            response = yonlendir.run_claude('test')
        self.assertEqual(response['output'], 'Claude cevap')

    def test_nested_hook_bypasses(self):
        with patch.dict(os.environ, {'AFU_ROUTER_CHILD': '1'}):
            payload, run = self.invoke()
        self.assertIsNone(payload)
        run.assert_not_called()

    def test_child_environment_has_guard(self):
        _, run = self.invoke('gemini: test')
        self.assertEqual(run.call_args.kwargs['env']['AFU_ROUTER_CHILD'], '1')

    def test_slash_and_empty_bypass(self):
        for text in ('/help', ''):
            payload, run = self.invoke(text)
            self.assertIsNone(payload)
            run.assert_not_called()

    def test_multiline_saved_exactly(self):
        task = 'İlk satır\nİkinci satır'
        self.invoke('gemini: ' + task)
        self.assertEqual(next((self.root / 'isler').glob('*.md')).read_text(encoding='utf-8'), task)

    @unittest.skipUnless(os.name == 'nt', 'Windows npm shim regression')
    def test_real_windows_shim_preserves_arguments(self):
        shim_dir = self.root / 'npm shim with spaces'
        shim_dir.mkdir()
        shim = shim_dir / 'agent.cmd'
        relative_python = os.path.relpath(sys.executable, shim_dir)
        shim.write_text('@ECHO off\n"%dp0%\\' + relative_python + '" %*\n', encoding='utf-8')
        prompt = 'Sen ajan işçisisin.\nDosyayı oku: "C:/My Project/task.md" & %TEMP%'
        result = yonlendir.run_process([str(shim), '-c', 'import sys,json; print(json.dumps(sys.argv[1:]))', prompt])
        self.assertEqual(result['status'], 'ok', result['output'])
        self.assertEqual(json.loads(result['output']), [prompt])


if __name__ == '__main__':
    unittest.main()
