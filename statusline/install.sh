#!/usr/bin/env bash
# Afu Claude Statusline installer (macOS / Linux / Windows Git Bash)
set -euo pipefail
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dest="$HOME/.claude"
settings="$dest/settings.json"
command -v python >/dev/null 2>&1 || command -v python3 >/dev/null 2>&1 || { echo "Python 3 gerekli / Python 3 required"; exit 1; }
PY="$(command -v python3 || command -v python)"
mkdir -p "$dest"
for f in statusline-command.sh subagent_statusline.py; do
  [[ -f "$dest/$f" ]] && cp "$dest/$f" "$dest/$f.bak-$(date +%Y%m%d-%H%M%S)"
  cp "$dir/$f" "$dest/$f"
done
printf '#!/usr/bin/env bash\nexec %s "$HOME/.claude/subagent_statusline.py"\n' "$(basename "$PY")" > "$dest/subagent-statusline.sh"
"$PY" - "$settings" <<'PYEOF'
import json, os, sys
p = sys.argv[1]
try:
    with open(p, encoding="utf-8") as f: s = json.load(f)
except (OSError, ValueError): s = {}
s["statusLine"] = {"type": "command", "command": "bash ~/.claude/statusline-command.sh"}
s["subagentStatusLine"] = {"type": "command", "command": "bash ~/.claude/subagent-statusline.sh"}
with open(p, "w", encoding="utf-8") as f: json.dump(s, f, indent=2, ensure_ascii=False)
print("settings.json guncellendi / updated:", p)
PYEOF
echo "Tamam / Done. Claude Code'u yeniden baslat / Restart Claude Code."
