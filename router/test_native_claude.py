import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import yonlendir


class NativeClaudeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for name, value in {'BASE_DIR': self.root, 'WORK_DIR': str(self.root),
                            'ACTIVE_AGENT_FILE': str(self.root / 'aktif.txt'),
                            'OFF_FILE': str(self.root / 'KAPALI')}.items():
            p = patch.object(yonlendir, name, value)
            p.start()
            self.addCleanup(p.stop)
        p = patch.dict(yonlendir.RUNNERS, {'claude': Mock(return_value={'status': 'ok', 'output': 'Claude mock', 'returncode': 0})})
        p.start()
        self.addCleanup(p.stop)

    def invoke(self, **fields):
        payload = {'session_id': 'session-a', 'cwd': str(self.root), **fields}
        stream = io.StringIO()
        self.assertEqual(yonlendir.main(io.StringIO(json.dumps(payload)), stream), 0)
        return stream.getvalue()

    def test_greeting_passes_to_native_without_output_or_worker(self):
        with patch.object(yonlendir.subprocess, 'run') as run:
            output = self.invoke(hook_event_name='UserPromptSubmit', prompt='mrb')
        self.assertEqual(output, '')
        run.assert_not_called()

    def test_quota_failure_dispatches_saved_task_once(self):
        self.invoke(hook_event_name='UserPromptSubmit', prompt='aynı görev\nikinci satır')
        with patch.dict(yonlendir.RUNNERS, {'codex': lambda task: {'status': 'ok', 'output': 'Codex tamam', 'returncode': 0}}), patch.object(yonlendir, 'run_claude') as claude:
            result = self.invoke(hook_event_name='StopFailure', error='rate_limit')
            duplicate = self.invoke(hook_event_name='StopFailure', error='rate_limit')
        self.assertIn('Codex tamam', json.loads(result)['systemMessage'])
        self.assertEqual(duplicate, '')
        self.assertEqual(yonlendir.get_active_agent(), 'codex')
        claude.assert_not_called()

    def test_non_quota_failure_does_not_dispatch(self):
        self.invoke(hook_event_name='UserPromptSubmit', prompt='mrb')
        with patch.object(yonlendir.subprocess, 'run') as run:
            output = self.invoke(hook_event_name='StopFailure', error='authentication_failed')
        self.assertEqual(output, '')
        run.assert_not_called()

    def test_failure_from_other_session_cannot_reuse_task(self):
        self.invoke(hook_event_name='UserPromptSubmit', prompt='görev a')
        with patch.object(yonlendir.subprocess, 'run') as run:
            output = self.invoke(hook_event_name='StopFailure', error='rate_limit', session_id='session-b')
        self.assertEqual(output, '')
        run.assert_not_called()

    def test_same_task_and_cwd_reach_fallback(self):
        task = 'Görev\nikinci satır'
        self.invoke(hook_event_name='UserPromptSubmit', prompt=task)
        received = []
        def runner(prompt):
            received.append((prompt, yonlendir.WORK_DIR))
            return {'status': 'ok', 'output': 'Tamam', 'returncode': 0}
        with patch.dict(yonlendir.RUNNERS, {'codex': runner}):
            self.invoke(hook_event_name='StopFailure', error='rate_limit')
        self.assertEqual(received, [(task, str(self.root))])


if __name__ == '__main__':
    unittest.main()
