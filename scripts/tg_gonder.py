# -*- coding: utf-8 -*-
"""Send a formatted message (or a photo/video) to Telegram via the Bot API.

The Telegram MCP server's SEND_MESSAGE does not support parse_mode, so
formatted reports have to go through the Bot API directly. This script is that
path. Credentials come from the environment or .env — never from the code.

Usage:
    python scripts/tg_gonder.py "<b>Done</b>"
    python scripts/tg_gonder.py "caption" --photo out/chart.png
    echo "<b>Report</b>" | python scripts/tg_gonder.py -

Telegram HTML supports ONLY: <b> <i> <u> <s> <code> <pre> <a href>
<blockquote> <tg-spoiler>. No <table>, <ul>, <li>, <br>, <h1..h6>, <div>.
Escape bare & < > as &amp; &lt; &gt; or the API returns 400.
Messages over 4096 chars are split.
"""
import argparse, io, json, os, sys, urllib.parse, urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIMIT = 4096


def ayar():
    """Read token + chat id from the environment, falling back to .env."""
    env = {}
    env_path = os.path.join(BASE, ".env")
    if os.path.exists(env_path):
        for line in io.open(env_path, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    tok = os.environ.get("MCP_TELEGRAM_TOKEN") or env.get("MCP_TELEGRAM_TOKEN")
    chat = os.environ.get("MCP_TELEGRAM_CHAT_ID") or env.get("MCP_TELEGRAM_CHAT_ID")
    if not tok or not chat:
        raise SystemExit("MCP_TELEGRAM_TOKEN / MCP_TELEGRAM_CHAT_ID not set "
                         "(see .env.example)")
    return tok, chat


def parcala(metin, limit=LIMIT):
    """Split on line boundaries so tags are not cut in half."""
    if len(metin) <= limit:
        return [metin]
    parcalar, buf = [], ""
    for satir in metin.splitlines(True):
        if len(buf) + len(satir) > limit and buf:
            parcalar.append(buf)
            buf = ""
        buf += satir
    if buf:
        parcalar.append(buf)
    return parcalar


def cagir(tok, metot, alanlar):
    data = urllib.parse.urlencode(alanlar).encode()
    url = "https://api.telegram.org/bot%s/%s" % (tok, metot)
    with urllib.request.urlopen(url, data, timeout=60) as r:
        return json.load(r)


def gonder_dosya(tok, chat, metot, alan, yol, caption):
    """Multipart upload for sendPhoto / sendVideo / sendDocument."""
    sinir = "----afuclaudeplugin"
    govde = io.BytesIO()

    def yaz(s):
        govde.write(s.encode("utf-8") if isinstance(s, str) else s)

    for k, v in (("chat_id", chat), ("caption", caption), ("parse_mode", "HTML")):
        if v is None:
            continue
        yaz("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"
            % (sinir, k, v))
    yaz("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\n"
        "Content-Type: application/octet-stream\r\n\r\n"
        % (sinir, alan, os.path.basename(yol)))
    with open(yol, "rb") as f:
        yaz(f.read())
    yaz("\r\n--%s--\r\n" % sinir)
    req = urllib.request.Request(
        "https://api.telegram.org/bot%s/%s" % (tok, metot), govde.getvalue(),
        {"Content-Type": "multipart/form-data; boundary=%s" % sinir})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("text", help="message text (HTML), or - to read stdin")
    p.add_argument("--photo", help="image file to send")
    p.add_argument("--video", help="video file to send")
    p.add_argument("--document", help="any file to send")
    p.add_argument("--plain", action="store_true", help="send without parse_mode")
    a = p.parse_args()

    tok, chat = ayar()
    metin = sys.stdin.read() if a.text == "-" else a.text

    for metot, alan, yol in (("sendPhoto", "photo", a.photo),
                             ("sendVideo", "video", a.video),
                             ("sendDocument", "document", a.document)):
        if yol:
            sonuc = gonder_dosya(tok, chat, metot, alan, yol, metin[:1024])
            print("ok" if sonuc.get("ok") else json.dumps(sonuc))
            return

    for parca in parcala(metin):
        alanlar = {"chat_id": chat, "text": parca,
                   "disable_web_page_preview": "true"}
        if not a.plain:
            alanlar["parse_mode"] = "HTML"
        sonuc = cagir(tok, "sendMessage", alanlar)
        print("ok" if sonuc.get("ok") else json.dumps(sonuc))


if __name__ == "__main__":
    main()
