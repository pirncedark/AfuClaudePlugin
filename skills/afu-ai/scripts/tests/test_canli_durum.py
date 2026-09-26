import argparse
import json
import os
import random
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import canli_durum
import subajan


class ParserTests(unittest.TestCase):
    def test_non_dict_json_event_is_skipped(self):
        parser = canli_durum.JSONLParser("codex")
        parser.feed(b"[]\n42\n")
        self.assertEqual(parser.event_count, 0)
        self.assertEqual(parser.actions, [])

    def feed_file(self, parser, name):
        parser.feed((ROOT / "tests" / "ornek" / name).read_bytes())

    def test_codex_sample(self):
        parser = canli_durum.JSONLParser("codex")
        self.feed_file(parser, "codex.jsonl")
        self.assertEqual(parser.token, 44884)
        self.assertTrue(any("komut:" in action and "echo hi" in action for action in parser.actions))
        self.assertEqual(parser.ozet, "OK")

    def test_omp_quota_sample(self):
        parser = canli_durum.JSONLParser("flash")
        self.feed_file(parser, "omp.jsonl")
        self.assertEqual(parser.durum, "KOTA")

    def test_opencode_sample(self):
        parser = canli_durum.JSONLParser("opencode")
        self.feed_file(parser, "opencode.jsonl")
        self.assertEqual(parser.token, 18340)
        self.assertEqual(parser.ozet, "OK")

    def test_codex_incremental_random_chunks(self):
        data = (ROOT / "tests" / "ornek" / "codex.jsonl").read_bytes()
        cuts = sorted(random.Random(45).sample(range(1, len(data)), 2))
        parser = canli_durum.JSONLParser("codex")
        start = 0
        for end in cuts + [len(data)]:
            parser.feed(data[start:end])
            start = end
        self.assertEqual((parser.token, parser.ozet), (44884, "OK"))

    def test_codex_log_contents_do_not_trigger_quota(self):
        parser = canli_durum.JSONLParser("codex")
        data = (ROOT / "tests" / "ornek" / "codex.jsonl").read_bytes()
        extra = json.dumps({"type": "item.completed", "item": {
            "type": "command_execution",
            "aggregated_output": "Free usage exceeded RESOURCE_EXHAUSTED"
        }}).encode()
        parser.feed(data + extra + b"\n")
        raw = data.decode() + extra.decode() + "\n"
        self.assertEqual(parser.durum, None)
        durum, cikis, kota = subajan.runner_outcome("codex", parser, raw, 0)
        self.assertEqual(durum, "BITTI")
        self.assertEqual(cikis, 0)
        self.assertFalse(kota)

    def test_opencode_plain_quota_line_without_events(self):
        parser = canli_durum.JSONLParser("opencode")
        raw = "Free usage exceeded, subscribe to Go\n"
        parser.feed(raw.encode())
        parser.finish()
        durum, cikis, kota = subajan.runner_outcome("opencode", parser, raw, 0)
        self.assertEqual(durum, "KOTA")
        self.assertEqual(cikis, 3)
        self.assertTrue(kota)
        self.assertEqual(parser.event_count, 0)
        self.assertFalse(parser.saw_text_or_step_finish)


class CodexOptionTests(unittest.TestCase):
    def test_contract_schema_and_flags(self):
        with tempfile.TemporaryDirectory() as temp:
            args = argparse.Namespace(sozlesme=True, worktree=True)
            command, schema_path = subajan.komut_kur("codex", "do it", "/tmp/out", args)
            try:
                self.assertIn("--worktree", command)
                self.assertIn("--output-schema", command)
                schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
                self.assertEqual(set(schema["required"]), {"karar", "ozet", "dosyalar", "test", "commit"})
                self.assertFalse(schema["additionalProperties"])
                self.assertEqual(schema["properties"]["karar"]["enum"], ["TAMAM", "KISMEN", "RET"])
            finally:
                Path(schema_path).unlink(missing_ok=True)

    def test_contract_parser_returns_compact_json_and_invalid_marker(self):
        valid = '{"karar":"TAMAM","ozet":"bitti","dosyalar":[],"test":"ok","commit":""}'
        self.assertEqual(subajan.sozlesme_cikti(valid), (valid, None))
        self.assertEqual(subajan.sozlesme_cikti("not json"), ("not json", "gecersiz"))

    def test_non_codex_contract_is_ignored(self):
        args = argparse.Namespace(sozlesme=True, worktree=True)
        command = subajan.komut_kur("flash", "do it", None, args)
        self.assertNotIn("--worktree", command)


class StatusTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows command shim behavior")
    def test_runner_retries_rollout_search_until_live_token_is_written(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            bindir = base / "bin"
            bindir.mkdir()
            program = base / "fake.py"
            program.write_text(
                "import datetime,json,pathlib,sys,time\n"
                "print(json.dumps({'type':'thread.started','thread_id':'abc'}),flush=True)\n"
                "time.sleep(4)\n"
                "home=pathlib.Path(__import__('os').environ['USERPROFILE'])\n"
                "folder=home/'.codex'/'sessions'/datetime.date.today().strftime('%Y/%m/%d')\n"
                "folder.mkdir(parents=True)\n"
                "(folder/'rollout-thread-abc.jsonl').write_text(json.dumps({'type':'event_msg','payload':{'type':'token_count','info':{'total_token_usage':{'total_tokens':123}}}})+'\\n',encoding='utf-8')\n"
                "time.sleep(6)\n",
                encoding="utf-8",
            )
            shim = bindir / "codex.cmd"
            shim.write_text('"%s" "%s" %%*\n' % (sys.executable, program), encoding="utf-8")
            env = os.environ.copy()
            env["PATH"] = str(bindir) + os.pathsep + env["PATH"]
            env["USERPROFILE"] = str(base)
            env["SUBAJAN_STATUS_DIR"] = str(base / "statuses")
            run = subprocess.Popen(
                [sys.executable, str(ROOT / "subajan.py"), "codex", "x", "--timeout", "30"],
                cwd=str(base), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            observed = False
            deadline = time.time() + 20
            while time.time() < deadline and run.poll() is None:
                for path in (base / "statuses").glob("*.json"):
                    status = json.loads(path.read_text(encoding="utf-8"))
                    if status["durum"] == "CALISIYOR" and status["token"] == 123:
                        observed = True
                        break
                if observed:
                    break
                time.sleep(0.1)
            out, err = run.communicate(timeout=35)
            self.assertEqual(run.returncode, 0, err)
            self.assertTrue(observed, out)

    def test_status_round_trip_atomic_and_cleanup(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            status = canli_durum.StatusFile(folder)
            payload = canli_durum.new_status("codex", "birinci cumle. devam", folder, 10.0, 20)
            status.write(payload)
            loaded = json.loads(status.path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            before = status.path.stat().st_mtime_ns
            payload["guncellendi"] = 12.0
            status.write(payload)
            self.assertGreaterEqual(status.path.stat().st_mtime_ns, before)
            self.assertEqual(json.loads(status.path.read_text(encoding="utf-8"))["guncellendi"], 12.0)
            self.assertEqual(list(folder.glob("*.tmp")), [])
            old = folder / "old.json"
            old.write_text(json.dumps({"bitti": time.time() - 90000}), encoding="utf-8")
            fresh = folder / "fresh.json"
            fresh.write_text(json.dumps({"bitti": time.time() - 30}), encoding="utf-8")
            canli_durum.cleanup_statuses(folder, now=time.time())
            self.assertFalse(old.exists())
            self.assertTrue(fresh.exists())


class RunnerTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows command shim behavior")
    def test_fake_codex_updates_status_and_hides_jsonl(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            bindir = base / "bin"
            bindir.mkdir()
            script = base / "emit.py"
            sample = ROOT / "tests" / "ornek" / "codex.jsonl"
            script.write_text(
                "import pathlib,sys,time\n"
                "for line in pathlib.Path(sys.argv[1]).read_text(encoding=\"utf-8\").splitlines():\n"
                " print(line, flush=True); time.sleep(0.3)\n",
                encoding="utf-8",
            )
            shim = bindir / "codex.cmd"
            shim.write_text("\"%s\" \"%s\" \"%s\"\n" % (sys.executable, script, sample), encoding="utf-8")
            env = os.environ.copy()
            env["PATH"] = str(bindir) + os.pathsep + env["PATH"]
            env["SUBAJAN_STATUS_DIR"] = str(base / "statuses")
            run = subprocess.Popen(
                [sys.executable, str(ROOT / "subajan.py"), "codex", "x", "--timeout", "30"],
                cwd=str(base), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            folder = base / "statuses"
            found_running = False
            deadline = time.time() + 10
            while time.time() < deadline and run.poll() is None:
                for path in folder.glob("*.json") if folder.exists() else []:
                    if json.loads(path.read_text(encoding="utf-8"))["durum"] == "CALISIYOR":
                        found_running = True
                if found_running:
                    break
                time.sleep(0.1)
            out, err = run.communicate(timeout=40)
            self.assertEqual(run.returncode, 0, err)
            files = list(folder.glob("*.json"))
            self.assertTrue(found_running)
            self.assertEqual(json.loads(files[0].read_text(encoding="utf-8"))["durum"], "BITTI")
            self.assertIn("OK", out)
            self.assertNotIn("thread.started", out)

    @unittest.skipUnless(os.name == "nt", "Windows command shim behavior")
    def test_final_message_stdout_full_and_status_summary_capped(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            bindir = base / "bin"
            bindir.mkdir()
            program = base / "fake.py"
            message = "x" * 1200
            program.write_text(
                "import json,sys\n"
                "args=sys.argv[1:]\n"
                "out=args[args.index('-o')+1]\n"
                "open(out,'w',encoding='utf-8').write(" + repr(message) + ")\n"
                "print(json.dumps({'type':'thread.started','thread_id':'abc'}),flush=True)\n",
                encoding="utf-8",
            )
            shim = bindir / "codex.cmd"
            shim.write_text('"%s" "%s" %%*\n' % (sys.executable, program), encoding="utf-8")
            env = os.environ.copy()
            env["PATH"] = str(bindir) + os.pathsep + env["PATH"]
            env["SUBAJAN_STATUS_DIR"] = str(base / "statuses")
            run = subprocess.run(
                [sys.executable, str(ROOT / "subajan.py"), "codex", "x"],
                cwd=str(base), env=env, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn(message, run.stdout)
            status_file = next((base / "statuses").glob("*.json"))
            status = json.loads(status_file.read_text(encoding="utf-8"))
            self.assertEqual(len(status["ozet"]), 500)

    @unittest.skipUnless(os.name == "nt", "Windows command shim behavior")
    def test_fake_codex_contract_flags_valid_and_invalid_json(self):
        for message, expected_marker in ((
            '{"karar":"TAMAM","ozet":"ok","dosyalar":[],"test":"pass","commit":""}', None
        ), ("not json", " sozlesme=gecersiz")):
            with self.subTest(message=message), tempfile.TemporaryDirectory() as temp:
                base = Path(temp)
                bindir = base / "bin"
                bindir.mkdir()
                program = base / "fake.py"
                program.write_text(
                    "import json,sys\n"
                    "args=sys.argv[1:]\n"
                    "json.dump(args,open(sys.argv[0]+'.args','w',encoding='utf-8'))\n"
                    "schema=args[args.index('--output-schema')+1]\n"
                    "open(sys.argv[0]+'.schema','w',encoding='utf-8').write(open(schema,encoding='utf-8').read())\n"
                    "out=args[args.index('-o')+1]\n"
                    "open(out,'w',encoding='utf-8').write(" + repr(message) + ")\n"
                    "print(json.dumps({'type':'thread.started','thread_id':'abc'}),flush=True)\n"
                    "print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':" + repr(message) + "}}),flush=True)\n",
                    encoding="utf-8",
                )
                shim = bindir / "codex.cmd"
                shim.write_text('"%s" "%s" %%*\n' % (sys.executable, program), encoding="utf-8")
                env = os.environ.copy()
                env["PATH"] = str(bindir) + os.pathsep + env["PATH"]
                env["SUBAJAN_STATUS_DIR"] = str(base / "statuses")
                run = subprocess.run(
                    [sys.executable, str(ROOT / "subajan.py"), "codex", "x", "--sozlesme", "--worktree"],
                    cwd=str(base), env=env, capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(run.returncode, 0, run.stderr)
                lines = run.stdout.splitlines()
                self.assertEqual(json.loads(lines[0]) if expected_marker is None else lines[0],
                                 json.loads(message) if expected_marker is None else message)
                footer = lines[2]
                self.assertEqual(expected_marker is not None, "sozlesme=gecersiz" in footer)
                status_files = list((base / "statuses").glob("*.json"))
                self.assertEqual(json.loads(status_files[0].read_text(encoding="utf-8"))["ozet"], lines[0])
                args = json.loads(Path(str(program) + ".args").read_text(encoding="utf-8"))
                self.assertIn("--worktree", args)
                schema = json.loads(Path(str(program) + ".schema").read_text(encoding="utf-8"))
                self.assertFalse(schema["additionalProperties"])
                self.assertEqual(schema["properties"]["ozet"]["maxLength"], 300)
                self.assertIn("--output-schema", args)


if __name__ == "__main__":
    unittest.main()
