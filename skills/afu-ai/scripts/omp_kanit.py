#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
omp_kanit.py - Bir subagent CLI'ini calistirir ve isi GERCEKTEN o ajanin
yaptigini kanitlayan renkli bir banner basar. Banner'daki model/token/oturum
alanlari ajanin kendi --mode json ciktisindan okunur; elle yazilmaz.

Kullanim:
  python omp_kanit.py "<gorev>" [--cwd DIR] [--timeout SN] [--out DOSYA] [--no-color]
"""
import sys, os, json, time, subprocess, argparse, datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ---- SUBAGENT EKIBI (tek kaynak) -------------------------------------------
EKIP = [
    ("omp",      "gemini-3.8-flash-tiered", "hazir",              "ok"),
    ("opencode", "OpenCode Go",             "hazir",              "ok"),
    ("codex",    "gpt-5.6-terra",           "kota -> 8 Eki 2026", "down"),
]

C = {"yesil": "\033[1;92m", "kirmizi": "\033[1;91m", "gri": "\033[90m",
     "sari": "\033[1;93m", "mavi": "\033[1;96m", "s": "\033[0m"}


def renksiz():
    for k in C:
        C[k] = ""


def gorunur(s):
    """ANSI kodlarini saymadan gercek genislik."""
    out, i = 0, 0
    while i < len(s):
        if s[i] == "\033":
            while i < len(s) and s[i] != "m":
                i += 1
            i += 1
            continue
        out += 1
        i += 1
    return out


def hucre(s, w):
    return s + " " * max(0, w - gorunur(s))


def banner(yapan, meta, session_id, usage, sure, cwd):
    u = usage or {}
    cost = (u.get("cost") or {}).get("total", 0) or 0

    def n(x):
        try:
            return "{:,}".format(int(x)).replace(",", ".")
        except Exception:
            return str(x)

    saglayici = str(meta.get("provider", "?"))
    if saglayici == "google-antigravity":
        para_notu = C["sari"] + "(bedava - Antigravity uyeligi)" + C["s"]
        uyari = None
    else:
        para_notu = C["kirmizi"] + "(UCRETLI!)" + C["s"]
        uyari = ("DIKKAT: beklenen saglayici google-antigravity idi, gelen '%s'. "
                 "omp config.yml bozuk olabilir - en sik sebep: dosya sonunda satir sonu yok." % saglayici)

    w1, w2, w3 = 10, 25, 22
    satirlar = []
    for ad, motor, durum, tip in EKIP:
        if ad == yapan:
            isaret = C["yesil"] + ">>" + C["s"]
            adr = C["yesil"] + hucre(ad, w1) + C["s"]
            motorr = C["yesil"] + hucre(meta.get("model", motor), w2) + C["s"]
            durumr = C["yesil"] + hucre("BU ISI YAPTI", w3) + C["s"]
        elif tip == "down":
            isaret = C["kirmizi"] + "xx" + C["s"]
            adr = C["kirmizi"] + hucre(ad, w1) + C["s"]
            motorr = C["gri"] + hucre(motor, w2) + C["s"]
            durumr = C["kirmizi"] + hucre(durum, w3) + C["s"]
        else:
            isaret = C["gri"] + "--" + C["s"]
            adr = C["gri"] + hucre(ad, w1) + C["s"]
            motorr = C["gri"] + hucre(motor, w2) + C["s"]
            durumr = C["gri"] + hucre(durum, w3) + C["s"]
        satirlar.append("| %s %s| %s| %s|" % (isaret, adr, motorr, durumr))

    ic = 3 + w1 + 2 + w2 + 2 + w3 + 1
    ust = "+" + "=" * ic + "+"
    ara = "+" + "-" * ic + "+"

    L = []
    L.append(C["mavi"] + ust + C["s"])
    L.append("|" + hucre(" " + C["mavi"] + "ISI KIM YAPTI?" + C["s"], ic) + "|")
    L.append(ara)
    L.append("| %s | %s | %s |" % (hucre("Subagent", w1 - 1), hucre("Motor", w2 - 1), hucre("Durum", w3 - 1)))
    L.append(ara)
    L.extend(satirlar)
    L.append(ara)
    for k, v in [
        ("Saglayici", str(meta.get("provider", "?")) + " / " + str(meta.get("api", "?"))),
        ("Oturum ID", str(session_id or "?")),
        ("Token", "giris %s / cikis %s / cache %s / toplam %s" % (
            n(u.get("input", 0)), n(u.get("output", 0)), n(u.get("cacheRead", 0)), n(u.get("total", 0)))),
        ("Maliyet", "$%.4f" % float(cost) + "  " + para_notu),
        ("Sure", "%.1f sn" % sure),
        ("Zaman", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("Dizin", cwd),
    ]:
        L.append("|" + hucre(" %-11s: %s" % (k, v), ic) + "|")
    L.append(C["mavi"] + ust + C["s"])
    if uyari:
        L.append(C["kirmizi"] + "!! " + uyari + C["s"])
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gorev")
    ap.add_argument("--cwd", default=os.getcwd())
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-color", action="store_true")
    a = ap.parse_args()
    if a.no_color or os.environ.get("NO_COLOR"):
        renksiz()

    t0 = time.time()
    try:
        pr = subprocess.run(["omp", "-p", "--mode", "json", "--auto-approve", a.gorev],
                            cwd=a.cwd, capture_output=True, timeout=a.timeout)
    except subprocess.TimeoutExpired:
        print("HATA: omp zaman asimina ugradi (%ss)" % a.timeout)
        return 2
    sure = time.time() - t0
    raw = pr.stdout.decode("utf-8", "replace")

    meta, session_id, cevap = {}, None, ""
    kullanim = {}   # timestamp -> usage  (message_start/end/update tekrarlarini teker)
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("type") == "session":
            session_id = ev.get("id")
        m = ev.get("message")
        if isinstance(m, dict) and m.get("role") == "assistant":
            if m.get("model"):
                meta = m
            if m.get("usage"):
                kullanim[m.get("timestamp")] = m["usage"]
            parts = [c.get("text", "") for c in m.get("content", [])
                     if isinstance(c, dict) and c.get("type") == "text"]
            if parts:
                cevap = "".join(parts)

    if not meta:
        print("HATA: omp'den model metadata gelmedi.\n" + raw[:1200])
        print("STDERR:\n" + pr.stderr.decode("utf-8", "replace")[:800])
        return 1

    toplam = {"input": 0, "output": 0, "cacheRead": 0, "total": 0, "cost": {"total": 0.0}}
    for u in kullanim.values():
        toplam["input"] += int(u.get("input", 0) or 0)
        toplam["output"] += int(u.get("output", 0) or 0)
        toplam["cacheRead"] += int(u.get("cacheRead", 0) or 0)
        toplam["total"] += int(u.get("totalTokens", 0) or 0)
        toplam["cost"]["total"] += float((u.get("cost") or {}).get("total", 0) or 0)

    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(cevap)

    print(cevap)
    print()
    print(banner("omp", meta, session_id, toplam, sure, a.cwd))
    if a.out:
        print("Cevap dosyasi: " + a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
