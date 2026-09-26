from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path


MAX_ACTION = 80


def one_line(value: str, limit: int) -> str:
    return " ".join(str(value).split())[:limit]


def first_sentence(task: str) -> str:
    line = one_line(task, 10000)
    match = re.search(r"[.!?](?:\s|$)", line)
    return line[:match.end()].strip()[:80] if match else line[:80]


def new_status(agent: str, task: str, cwd: str | Path, started: float, pid: int) -> dict:
    ident = "%s_%d_%d" % (agent, int(started), os.getpid())
    return {
        "surum": 1,
        "id": ident,
        "ajan": agent,
        "gorev": first_sentence(task),
        "cwd": str(cwd),
        "pid": pid,
        "runner_pid": os.getpid(),
        "basladi": started,
        "guncellendi": started,
        "bitti": None,
        "durum": "CALISIYOR",
        "token": None,
        "eylem": "basliyor",
        "cikis": None,
        "log": "",
        "ozet": "",
    }


class StatusFile:
    def __init__(self, folder: str | Path, ident: str | None = None):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.path = self.folder / ((ident or "status") + ".json")

    def write(self, payload: dict) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_name(self.path.name + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        os.replace(temp, self.path)


def cleanup_statuses(folder: str | Path, now: float | None = None) -> None:
    root = Path(folder)
    if not root.exists():
        return
    cutoff = (time.time() if now is None else now) - 24 * 3600
    for path in root.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("bitti") is not None and float(payload["bitti"]) < cutoff:
                path.unlink()
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue


class JSONLParser:
    def __init__(self, agent: str):
        self.agent = agent
        self.buffer = b""
        self.live_buffer = b""
        self.actions: list[str] = []
        self.eylem = "basliyor"
        self.ozet = ""
        self.token: int | None = None
        self.durum: str | None = None
        self.event_count = 0
        self.thread_id: str | None = None
        self.saw_text_or_step_finish = False
        self.plain_opencode_quota = False

    def feed(self, data: bytes) -> None:
        self.buffer += data
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            self._line(line)

    def finish(self) -> None:
        if self.buffer:
            self._line(self.buffer)
            self.buffer = b""

    def _line(self, line: bytes) -> None:
        try:
            event = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            if self.agent == "opencode" and b"Free usage exceeded" in line:
                self.plain_opencode_quota = True
            return
        self.event_count += 1
        if self.agent == "codex":
            self._codex(event)
        elif self.agent in ("flash", "pro"):
            self._omp(event)
        elif self.agent == "opencode":
            self._opencode(event)

    def _action(self, value: str) -> None:
        self.eylem = one_line(value, MAX_ACTION)
        self.actions.append(self.eylem)

    def _codex(self, event: dict) -> None:
        kind = event.get("type")
        if kind in ("turn.failed", "error"):
            message = event.get("message") or event.get("error") or ""
            if isinstance(message, dict):
                message = message.get("message", "")
            if re.search(r"usage limit|429|quota", str(message), flags=re.I):
                self.durum = "KOTA"
        if kind == "thread.started":
            self.thread_id = event.get("thread_id")
        elif kind == "item.started":
            item = event.get("item") or {}
            item_type = item.get("type")
            if item_type == "command_execution":
                command = str(item.get("command", ""))
                command = re.sub(r"^.*?powershell(?:\.exe)?[\" ]*\s+-Command\s+", "", command, flags=re.I)
                command = command.strip().strip("\"").strip(chr(39))
                self._action("komut: " + one_line(command, 60))
            elif item_type == "file_change":
                path = item.get("path")
                self._action("dosya duzenliyor" + ((": " + str(path)) if path else ""))
            elif item_type == "reasoning":
                self._action("dusunuyor")
            elif item_type == "agent_message":
                self._action("yaziyor")
                if item.get("text"):
                    self.ozet = one_line(item["text"], 500)
            elif item_type == "mcp_tool_call":
                tool = item.get("tool") or item.get("name")
                if tool:
                    self._action("arac: " + str(tool))
            elif item_type == "web_search":
                self._action("web aramasi")
        elif kind == "item.completed":
            item = event.get("item") or {}
            if item.get("type") == "agent_message" and item.get("text"):
                self.ozet = one_line(item["text"], 500)
        elif kind == "mcp_tool_call":
            tool = event.get("tool") or event.get("name") or (event.get("item") or {}).get("name")
            if tool:
                self._action("arac: " + str(tool))
        elif kind == "web_search":
            self._action("web aramasi")
        elif kind == "turn.completed":
            usage = event.get("usage") or {}
            if "input_tokens" in usage and "output_tokens" in usage:
                self.token = int(usage["input_tokens"]) + int(usage["output_tokens"])

    def _omp(self, event: dict) -> None:
        kind = str(event.get("type", ""))
        message = event.get("message") or {}
        if "tool" in kind.lower():
            name = event.get("name") or (event.get("part") or {}).get("name")
            if name:
                self._action("arac: " + str(name))
        if kind == "message_start" and message.get("role") == "assistant":
            self._action("dusunuyor")
        if message.get("errorStatus") == 429 or "RESOURCE_EXHAUSTED" in str(message.get("errorMessage", "")):
            self.durum = "KOTA"
        if kind == "message_end" and message.get("role") == "assistant":
            usage = message.get("usage") or {}
            if "totalTokens" in usage:
                self.token = (self.token or 0) + int(usage["totalTokens"])
            texts = [part.get("text", "") for part in message.get("content", []) if part.get("type") == "text"]
            candidate = "".join(texts)
            if candidate:
                self.ozet = one_line(candidate, 500)
                self._action("yaziyor")

    def _opencode(self, event: dict) -> None:
        kind = event.get("type")
        part = event.get("part") or {}
        if kind in ("text", "step_finish"):
            self.saw_text_or_step_finish = True
        if kind == "text" and part.get("text"):
            self.ozet = one_line(part["text"], 500)
            self._action("yaziyor")
        elif kind == "step_finish":
            total = (part.get("tokens") or {}).get("total")
            if total is not None:
                self.token = (self.token or 0) + int(total)
        elif kind == "tool_use" or "tool" in str(part.get("type", "")).lower():
            tool = part.get("tool") or part.get("name")
            if tool:
                self._action("arac: " + str(tool))

    def live_token_count(self, lines: bytes) -> None:
        last = None
        self.live_buffer += lines
        complete = self.live_buffer.split(b"\n")
        self.live_buffer = complete.pop()
        for raw in complete:
            try:
                event = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if event.get("type") == "token_count":
                last = ((event.get("info") or {}).get("total_token_usage") or {}).get("total_tokens")
        if last is not None:
            self.token = int(last)
