#!/usr/bin/env python3
"""Control Claude Code's bypass permissions settings in settings.json.
Create a backup before changing settings and preserve all unrelated values.
WARNING: Bypass mode skips permission prompts for every tool; enable it only
on a machine you trust.
"""
import argparse
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("ac", "kapat", "durum"))
    parser.add_argument(
        "--settings", type=Path,
        default=Path.home() / ".claude" / "settings.json",
        help="settings.json path (default: ~/.claude/settings.json)",
    )
    args = parser.parse_args()
    path = args.settings

    if not path.exists():
        if args.action != "ac":
            print("Ayar dosyası yok.")
            return 0
        settings = {}
    else:
        try:
            with path.open("r", encoding="utf-8") as f:
                settings = json.load(f)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            print("Ayar dosyası okunamadı veya bozuk JSON: %s" % exc,
                  file=sys.stderr)
            return 1
        if not isinstance(settings, dict):
            print("Ayar dosyası bozuk: JSON kökü nesne değil.", file=sys.stderr)
            return 1

    if args.action == "durum":
        permissions = settings.get("permissions", {})
        if not isinstance(permissions, dict):
            permissions = {}
        print("permissions.defaultMode: %s" % permissions.get("defaultMode", "(yok)"))
        print("skipDangerousModePermissionPrompt: %s" %
              settings.get("skipDangerousModePermissionPrompt", "(yok)"))
        return 0

    if path.exists():
        backup = path.with_name("settings.json.bak")
        try:
            backup.write_bytes(path.read_bytes())
        except OSError as exc:
            print("Yedek alınamadı: %s" % exc, file=sys.stderr)
            return 1

    permissions = settings.get("permissions")
    if not isinstance(permissions, dict):
        permissions = {}
        settings["permissions"] = permissions

    if args.action == "ac":
        permissions["defaultMode"] = "bypassPermissions"
        settings["skipDangerousModePermissionPrompt"] = True
        print("Bypass izin modu açıldı.")
    else:
        permissions["defaultMode"] = "default"
        settings.pop("skipDangerousModePermissionPrompt", None)
        print("Bypass izin modu kapatıldı.")

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except OSError as exc:
        print("Ayar dosyası yazılamadı: %s" % exc, file=sys.stderr)
        return 1
    print("Yeni Claude Code oturumunda geçerli olur.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
