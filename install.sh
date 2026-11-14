#!/usr/bin/env bash
# Usage: ./install.sh [claude|codex|both]   (default: both)
# Copies every skill in skills/ into ~/.claude/skills and/or ~/.agents/skills (Codex).
set -e
T="${1:-both}"; HERE="$(cd "$(dirname "$0")" && pwd)"
put() { mkdir -p "$1"; for d in "$HERE"/skills/*/; do rm -rf "$1/$(basename "$d")"; cp -r "$d" "$1/"; echo "ok  $1/$(basename "$d")"; done; }
[ "$T" != codex ]  && put "$HOME/.claude/skills"
[ "$T" != claude ] && put "$HOME/.agents/skills"
echo "Done. Next: copy .env.example to .env (Telegram only) and read docs/ORKESTRASYON.md"
