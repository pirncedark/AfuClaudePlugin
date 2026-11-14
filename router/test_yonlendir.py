import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import yonlendir


class HookTests(unittest.TestCase):
    def setUp(self):
        legacy = patch.dict(yonlendir.os.environ, {"AFU_CODEX_LEGACY": "1"})
        legacy.start()
        self.addCleanup(legacy.stop)
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.off = self.root / "KAPALI"
        self.active = self.root / "aktif_ajan.txt"

        self.old_off = yonlendir.OFF_FILE
        self.old_active = yonlendir.ACTIVE_AGENT_FILE
        yonlendir.OFF_FILE = str(self.off)
        yonlendir.ACTIVE_AGENT_FILE = str(self.active)

        self.addCleanup(setattr, yonlendir, "OFF_FILE", self.old_off)
        self.addCleanup(setattr, yonlendir, "ACTIVE_AGENT_FILE", self.old_active)

    def invoke(self, prompt="Merhaba", results=None):
        output = io.StringIO()
        with patch.object(yonlendir, "resolve_executable", side_effect=lambda x: x), patch.object(yonlendir, "BASE_DIR", self.root), patch.object(
            yonlendir, "WORK_DIR", str(self.root)
        ), patch.object(
            yonlendir.subprocess,
            "run",
            side_effect=results or [
                subprocess.CompletedProcess([], 0, "Cevap\nZINCIR: BITTI\n", "")
            ],
        ) as run:
            code = yonlendir.main(
                io.StringIO(json.dumps({"prompt": prompt}, ensure_ascii=False)),
                output,
            )
        self.assertEqual(code, 0)
        return output.getvalue(), run

    def test_default_agent_is_claude(self):
        self.assertEqual(yonlendir.get_active_agent(), "claude")

    def test_normal_prompt_uses_claude_by_default(self):
        output, run = self.invoke("login hatasını düzelt")
        self.assertEqual(output, "")
        run.assert_not_called()

    def test_manual_switch_to_claude_persists(self):
        output, run = self.invoke("ajan claude")
        payload = json.loads(output)
        self.assertFalse(payload["continue"])
        self.assertIn("claude", payload["stopReason"])
        run.assert_not_called()
        self.assertEqual(self.active.read_text(encoding="utf-8"), "claude")

        output2, run2 = self.invoke("normal görev")
        self.assertEqual(output2, "")
        run2.assert_not_called()

    def test_manual_switch_to_gemini_persists(self):
        output, run = self.invoke("ajan gemini")
        payload = json.loads(output)
        self.assertFalse(payload["continue"])
        self.assertIn("gemini", payload["stopReason"])
        run.assert_not_called()
        self.assertEqual(yonlendir.get_active_agent(), "gemini")

    def test_manual_switch_to_opencode_persists(self):
        output, run = self.invoke("ajan opencode")
        payload = json.loads(output)
        self.assertFalse(payload["continue"])
        self.assertIn("opencode", payload["stopReason"])
        run.assert_not_called()
        self.assertEqual(yonlendir.get_active_agent(), "opencode")

    def test_manual_switch_back_to_codex_persists(self):
        yonlendir.set_active_agent("claude")
        output, run = self.invoke("ajan codex")
        payload = json.loads(output)
        self.assertFalse(payload["continue"])
        self.assertIn("codex", payload["stopReason"])
        run.assert_not_called()
        self.assertEqual(yonlendir.get_active_agent(), "codex")

    def test_agent_status(self):
        yonlendir.set_active_agent("gemini")
        output, run = self.invoke("ajan")
        payload = json.loads(output)
        self.assertFalse(payload["continue"])
        self.assertIn("Aktif ajan: gemini", payload["stopReason"])
        run.assert_not_called()

    def test_codex_quota_auto_switches_to_claude(self):
        yonlendir.set_active_agent("codex")
        output, run = self.invoke(
            "normal görev",
            results=[
                subprocess.CompletedProcess(
                    [], 1, "", "ajan=codex durum=KOTA\nZINCIR: BITTI (KOTA, 1 tur)"
                ),
                subprocess.CompletedProcess([], 0, "Gemini cevap", ""),
            ],
        )
        self.assertEqual(run.call_count, 2)
        self.assertIn("Gemini cevap", (json.loads(output).get("stopReason") or json.loads(output).get("hookSpecificOutput", {}).get("additionalContext", "")))
        self.assertEqual(yonlendir.get_active_agent(), "claude")

    def test_one_shot_gemini_does_not_change_active_agent(self):
        self.assertEqual(yonlendir.get_active_agent(), "claude")
        output = io.StringIO()
        with patch.object(yonlendir, "BASE_DIR", self.root), patch.object(
            yonlendir, "WORK_DIR", str(self.root)
        ), patch.object(
            yonlendir, "resolve_executable", return_value="gemini"
        ), patch.object(
            yonlendir.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 0, "Gemini cevap", ""),
        ):
            code = yonlendir.main(
                io.StringIO(json.dumps({"prompt": "gemini: repoyu incele"})),
                output,
            )
        self.assertEqual(code, 0)
        self.assertEqual(yonlendir.get_active_agent(), "claude")

    def test_one_shot_claude_does_not_change_active_agent(self):
        output, run = self.invoke("claude: bunu sen yap")
        self.assertEqual(output, "")
        run.assert_not_called()
        self.assertEqual(yonlendir.get_active_agent(), "claude")


if __name__ == "__main__":
    unittest.main()
