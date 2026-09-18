# -*- coding: utf-8 -*-
"""Telegram long-poll listener.

Writes every incoming message to telegram_kuyruk/gelen_mesajlar.jsonl the
moment it arrives, so the Claude Code loop can read it from disk instead of
polling the Bot API itself. Photos and documents are downloaded next to it.

Only ONE process may long-poll a given bot. A second one gets 409 Conflict.

Config: MCP_TELEGRAM_TOKEN, from the environment or from a .env file in the
repo root (see .env.example). No credentials live in this file.
"""
import json, os, time
import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KUYRUK = os.environ.get("TELEGRAM_KUYRUK") or os.path.join(BASE, "telegram_kuyruk")
OFFSET_F = os.path.join(KUYRUK, "tg_skill_offset.txt")
GELEN_F = os.path.join(KUYRUK, "gelen_mesajlar.jsonl")
LOG_F = os.path.join(KUYRUK, "tg_dinleyici.log")


def env_token():
    tok = os.environ.get("MCP_TELEGRAM_TOKEN")
    if tok:
        return tok.strip()
    env_path = os.path.join(BASE, ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("MCP_TELEGRAM_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("MCP_TELEGRAM_TOKEN not set (env or .env)")


def log(msg):
    with open(LOG_F, "a", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")


def indir(tok, file_id, hedef_dir, ad):
    """Download a Telegram file into hedef_dir/ad, return the path."""
    fi = requests.get("https://api.telegram.org/bot%s/getFile" % tok,
                      params={"file_id": file_id}, timeout=30).json()
    yol = fi["result"]["file_path"]
    veri = requests.get("https://api.telegram.org/file/bot%s/%s" % (tok, yol),
                        timeout=120).content
    os.makedirs(hedef_dir, exist_ok=True)
    hedef = os.path.join(hedef_dir, ad)
    with open(hedef, "wb") as f:
        f.write(veri)
    return hedef, len(veri)


def main():
    tok = env_token()
    os.makedirs(KUYRUK, exist_ok=True)
    offset = 0
    if os.path.exists(OFFSET_F):
        try:
            offset = int(open(OFFSET_F).read().strip())
        except Exception:
            pass
    log("listener started, offset=%s" % offset)
    while True:
        try:
            r = requests.get(
                "https://api.telegram.org/bot%s/getUpdates" % tok,
                params={"timeout": 50, "offset": offset or None}, timeout=60)
            if r.status_code == 409:
                log("409 CONFLICT - another process is polling the same bot")
                time.sleep(10)
                continue
            data = r.json()
            for u in data.get("result", []):
                offset = u["update_id"] + 1
                with open(OFFSET_F, "w") as f:
                    f.write(str(offset))
                m = u.get("message") or u.get("edited_message") or {}
                kayit = {
                    "update_id": u["update_id"],
                    "chat_id": (m.get("chat") or {}).get("id"),
                    "text": m.get("text") or m.get("caption") or "",
                    "ts": m.get("date"),
                    "durum": "bekliyor",
                }
                if m.get("photo"):
                    try:
                        kayit["resim"], _ = indir(
                            tok, m["photo"][-1]["file_id"],
                            os.path.join(KUYRUK, "gelen_resimler"),
                            "%s.jpg" % u["update_id"])
                    except Exception as e:
                        log("photo download failed: %r" % e)
                # Documents matter as much as photos: a zip/csv/xlsx sent to the
                # bot is silently lost if only photos are handled.
                if m.get("document"):
                    try:
                        d = m["document"]
                        ad = d.get("file_name") or ("%s.bin" % u["update_id"])
                        kayit["dosya"], n = indir(
                            tok, d["file_id"],
                            os.path.join(KUYRUK, "gelen_dosyalar"),
                            "%s_%s" % (u["update_id"], ad))
                        log("document saved: %s (%d bytes)" % (ad, n))
                    except Exception as e:
                        log("document download failed: %r" % e)
                with open(GELEN_F, "a", encoding="utf-8") as f:
                    f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
                log("message received: %s" % kayit["text"][:80])
        except Exception as e:
            log("error: %r" % e)
            time.sleep(10)


if __name__ == "__main__":
    main()
