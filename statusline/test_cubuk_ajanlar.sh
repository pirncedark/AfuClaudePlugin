#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
tmp_home="$(mktemp -d)"
trap 'rm -rf "$tmp_home"' EXIT
export HOME="$tmp_home"
export USERPROFILE="$tmp_home"
mkdir -p "$HOME/.claude"

run_bar() {
  printf '%s\n' '{"model":{"display_name":"Opus 5.5"}}' | bash "$script_dir/statusline-command.sh"
}

out="$(run_bar)"
! printf '%s\n' "$out" | grep -q 'AJANLAR'

export AFUNOBET_DIR="$tmp_home/AfuNobet"
mkdir -p "$AFUNOBET_DIR"
python -c 'import time; time.sleep(60)' &
sleeper_pid=$!
# Git Bash $! MSYS pid verir; cubuk Windows pid ile bakar
sleeper_winpid=$(cat "/proc/$sleeper_pid/winpid" 2>/dev/null || echo "$sleeper_pid")
trap 'kill "$sleeper_pid" 2>/dev/null || true; wait "$sleeper_pid" 2>/dev/null || true; rm -rf "$tmp_home"' EXIT
python - "$AFUNOBET_DIR/state.db" "$sleeper_winpid" <<'PY'
import sqlite3
import sys

db_path, pid = sys.argv[1:]
conn = sqlite3.connect(db_path)
conn.execute("CREATE TABLE shells (pid INTEGER, status TEXT)")
conn.execute("INSERT INTO shells (pid, status) VALUES (?, ?)", (int(pid), "RUNNING"))
conn.execute("INSERT INTO shells (pid, status) VALUES (?, ?)", (2147483647, "RUNNING"))
conn.commit()
conn.close()
PY
out="$(run_bar)"
printf '%s\n' "$out" | grep -q '0 calisiyor · 1 kabuk'
! printf '%s\n' "$out" | grep -q 'Ã‚'
! printf '%s\n' "$out" | grep -q 'Ã‚'
printf '%s\n' "$out" | grep -q 'AJANLAR'
trap - EXIT
kill "$sleeper_pid" 2>/dev/null || true
wait "$sleeper_pid" 2>/dev/null || true
rm -rf "$tmp_home"
unset AFUNOBET_DIR

mkdir -p "$HOME/.claude/afu-ajanlar"
python - "$HOME/.claude/afu-ajanlar" <<'PY'
import json
import os
import sys
import time

folder = sys.argv[1]
now = time.time()
data = [
    {"ajan": "codex", "durum": "CALISIYOR", "guncellendi": now, "bitti": None, "token": 60600},
    {"ajan": "opencode", "durum": "CALISIYOR", "guncellendi": now, "bitti": None, "token": 18200},
]
for index, item in enumerate(data):
    with open(os.path.join(folder, str(index) + ".json"), "w", encoding="utf-8") as handle:
        json.dump(item, handle)
PY
out="$(run_bar)"
printf '%s\n' "$out" | grep -q '2 calisiyor'
printf '%s\n' "$out" | grep -q 'codex, opencode'
printf '%s\n' "$out" | grep -q '78.8k'

python - "$HOME/.claude/afu-ajanlar" <<'PY'
import json
import os
import sys
import time
folder = sys.argv[1]
for name in os.listdir(folder):
    os.unlink(os.path.join(folder, name))
with open(os.path.join(folder, "stale.json"), "w", encoding="utf-8") as handle:
    json.dump({"ajan": "stale", "durum": "CALISIYOR", "guncellendi": time.time() - 60, "bitti": None, "token": 9}, handle)
PY
out="$(run_bar)"

printf '%s\n' '{broken' > "$HOME/.claude/afu-ajanlar/broken.json"
out="$(run_bar)"
printf '%s\n' "$out" | grep -q 'MODEL'

rm -f "$HOME/.claude/afu-ajanlar/stale.json" "$HOME/.claude/afu-ajanlar/broken.json"
python - "$HOME/.claude/afu-ajanlar" <<'PY'
import json
import os
import sys
import time
with open(os.path.join(sys.argv[1], "null.json"), "w", encoding="utf-8") as handle:
    json.dump({"ajan": "nulltoken", "durum": "CALISIYOR", "guncellendi": time.time(), "bitti": None, "token": None}, handle)
PY
out="$(run_bar)"
printf '%s\n' "$out" | grep -q '↓ ?'

python - "$HOME/.claude/afu-ajanlar" <<'PY'
import json
import os
import sys
import time
folder = sys.argv[1]
for name in os.listdir(folder):
    os.unlink(os.path.join(folder, name))
with open(os.path.join(folder, "finished.json"), "w", encoding="utf-8") as handle:
    json.dump({"ajan": "codex", "durum": "TAMAMLANDI", "guncellendi": time.time() - 60, "bitti": time.time() - 60, "token": 12300}, handle)
PY
out="$(run_bar)"
printf '%s\n' "$out" | grep -q '0 calisiyor'
printf '%s\n' "$out" | grep -q '1 bitti'
printf '%s\n' "$out" | grep -q 'codex'
printf '%s\n' "$out" | grep -q '12.3k'

python - "$HOME/.claude/afu-ajanlar" <<'PY'
import json
import os
import sys
import time
folder = sys.argv[1]
for name in os.listdir(folder):
    os.unlink(os.path.join(folder, name))
with open(os.path.join(folder, "old.json"), "w", encoding="utf-8") as handle:
    json.dump({"ajan": "old", "durum": "TAMAMLANDI", "bitti": time.time() - 600, "token": 99}, handle)
PY
out="$(run_bar)"

python - "$HOME/.claude/afu-ajanlar" <<'PY'
import json
import os
import sys
import time
folder = sys.argv[1]
now = time.time()
data = [
    {"ajan": "codex", "durum": "CALISIYOR", "guncellendi": now, "bitti": None, "token": 5000},
    {"ajan": "opencode", "durum": "KOTA", "guncellendi": now - 60, "bitti": now - 60, "token": 2000},
]
for index, item in enumerate(data):
    with open(os.path.join(folder, str(index) + ".json"), "w", encoding="utf-8") as handle:
        json.dump(item, handle)
PY
out="$(run_bar)"
printf '%s\n' "$out" | grep -q '1 calisiyor'
printf '%s\n' "$out" | grep -q '1 bitti (1 sorunlu)'
printf '%s\n' "$out" | grep -q 'codex, opencode'

python - "$script_dir/statusline-command.sh" <<'PY'
import sys
path = sys.argv[1]
with open(path, encoding="utf-8") as handle:
    lines = handle.readlines()
block = lines[11:]
end = next(i for i, line in enumerate(block) if line.rstrip("\n") == "')")
assert "'" not in "".join(block[:end]), "apostrophe found in Python block"
PY

printf '%s\n' 'All ajanlar statusline cases passed.'
