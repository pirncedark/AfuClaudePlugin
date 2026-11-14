# -*- coding: utf-8 -*-
"""ajan.py — opencode / codex'i DOGRU bayraklarla, kilitlenmeden baslatir.

Kullanim:
  python ajan.py opencode <gorev_dosyasi> [--cwd DIZIN]
  python ajan.py codex    <gorev_dosyasi> [--cwd DIZIN] [--yaz] [--ag] [--tam]

  --yaz : codex dosya yazabilsin (-s workspace-write). Yoksa salt-okur.
  --ag  : codex agi kullanabilsin (pip/curl vb.)  -> network_access=true
  --tam : codex tam erisim (-s danger-full-access). git push / gh icin SART:
          workspace-write kumandasi Windows kimlik deposuna erisemez
          (schannel SEC_E_NO_CREDENTIALS).
  --hizli: codex fast (priority tier, 2 kat kota). Varsayilan fast OFF
          (AfuNobet karari 23 Eyl: kota verimi). Global config.toml a dokunmaz.

Cikti: log dosyasinin yolu stdout'a basilir. Surec arka planda KALIR.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# bul() bir node shimi cozdugunde "node.exe<AYRAC>betik.js" dondurur.
NODE_AYRAC = "\x00"


def komut(ad):
    """bul() sonucunu Popen listesine cevirir. Node shimi ise [node, js]."""
    y = bul(ad)
    return y.split(NODE_AYRAC) if NODE_AYRAC in y else [y]


def bul(ad: str) -> str:
    """Windows'ta opencode/codex birer .cmd sarmalayicidir; Popen ciplak adi
    bulamaz (WinError 2). Tam yolu cozeriz.

    PENCERE FIRTINASI (20 Eyl 2026): .cmd/.bat shim calistirildiginda Windows
    bir cmd.exe + conhost penceresi dogurur; CREATE_NO_WINDOW bunu TAM
    engellemez ve ekran pencereyle dolar (conhost 26 -> 101 olculdu).
    COZUM: ONCE .exe aranir, shim en son care olarak kullanilir.
    subajan.py de ayni sirayi uygular."""
    for ek in (".exe", ".com"):
        yol = shutil.which(ad + ek)
        if yol:
            return yol
    yol = shutil.which(ad)
    if yol and os.path.splitext(yol)[1].lower() in (".exe", ".com"):
        return yol
    # npm shim (.cmd) bulundu. Shim CALISTIRMA - icindeki gercek .exe yolunu
    # cikar. Ornek satir:  "%dp0%\node_modules\opencode-ai\bin\opencode.exe" %*
    # Boylece cmd.exe hic devreye girmez, conhost penceresi DOGMAZ.
    for ek in (".cmd", ".bat"):
        shim = shutil.which(ad + ek)
        if not shim:
            continue
        try:
            metin = Path(shim).read_text(encoding="utf-8", errors="replace")
        except OSError:
            metin = ""
        dp0 = str(Path(shim).parent)
        for parca in re.findall(r'"([^"]+\.exe)"', metin):
            hedef = parca.replace("%dp0%", dp0).replace("%~dp0", dp0)
            hedef = os.path.normpath(hedef)
            if os.path.isfile(hedef) and os.path.basename(hedef).lower() != "node.exe":
                return hedef
        # node shim (ornek: codex.cmd -> node.exe + .../bin/codex.js).
        # node.exe'yi DOGRUDAN cagirmak icin js yolunu dondururuz; cagiran
        # taraf bunu [node, js] listesine cevirir.
        for parca in re.findall(r'"([^"]+\.js)"', metin):
            hedef = parca.replace("%dp0%", dp0).replace("%~dp0", dp0)
            hedef = os.path.normpath(hedef)
            if os.path.isfile(hedef):
                dugum = shutil.which("node") or shutil.which("node.exe")
                if dugum:
                    return NODE_AYRAC.join((dugum, hedef))
        return shim  # gercek hedef cikmadi; son care shim
    for ek in (".ps1",):
        y = shutil.which(ad + ek)
        if y:
            return y
    if yol:
        return yol
    raise SystemExit(f"HATA: '{ad}' PATH'te bulunamadi")


def log_dizini() -> Path:
    d = Path(os.environ.get("TEMP", "/tmp")) / "ajan-kopru"
    d.mkdir(parents=True, exist_ok=True)
    return d


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("ajan", choices=["opencode", "codex", "gemini"])
    p.add_argument("gorev", help="gorev metnini iceren dosya")
    p.add_argument("--cwd", default=os.getcwd())
    p.add_argument("--yaz", action="store_true")
    p.add_argument("--ag", action="store_true")
    p.add_argument("--tam", action="store_true")
    p.add_argument("--hizli", action="store_true")
    p.add_argument("--etiket", default="")
    p.add_argument("--pro", action="store_true",
                   help="gemini: 3.1-pro:high kullan (varsayilan 3.8-flash)")
    a = p.parse_args()

    gorev = Path(a.gorev)
    if not gorev.exists():
        print(f"HATA: gorev dosyasi yok: {gorev}", file=sys.stderr)
        return 2
    metin = gorev.read_text(encoding="utf-8")
    if not metin.strip():
        print(f"HATA: gorev dosyasi bos: {gorev}", file=sys.stderr)
        return 2

    etiket = a.etiket or gorev.stem
    log = log_dizini() / f"{etiket}_{a.ajan}_{time.strftime('%H%M%S')}.log"

    # TUZAK: cok satirli metni argv ile gecirince Windows .cmd sarmalayicisi
    # ILK SATIRDAN sonrasini yutuyor. Prompt'u STDIN'den veriyoruz.
    if a.ajan == "gemini":
        # TUZAK: pro modelleri YALNIZ low/high destekler; seviye yazilmazsa takilir.
        model = ("google-antigravity/gemini-3.1-pro:high" if a.pro
                 else "google-antigravity/gemini-3.8-flash")
        cmd = komut("omp") + ["-p", metin, "--mode", "json", "--model", model]
    elif a.ajan == "opencode":
        cmd = komut("opencode") + ["run"]
    else:
        cmd = komut("codex") + ["exec"]
        cmd += ["-c", "service_tier=\"priority\"" if a.hizli else "service_tier=\"default\""]
        if a.tam:
            cmd += ["-s", "danger-full-access"]
        else:
            cmd += ["-s", "workspace-write" if a.yaz else "read-only"]
            if a.ag:
                cmd += ["-c", "sandbox_workspace_write.network_access=true"]
        # TUZAK 16: codex git deposu OLMAYAN klasorde calismayi REDDEDER
        # ("Not inside a trusted directory and --skip-git-repo-check was not
        # specified." -> log 105 bayt kalir, is HIC baslamaz). ~/.claude gibi
        # duz klasorlerde bu bayrak SART.
        gitd = os.path.join(a.cwd, ".git")
        if not (os.path.isdir(gitd) or os.path.isfile(gitd)):
            cmd += ["--skip-git-repo-check"]
        cmd += ["-C", a.cwd]

    # TUZAK 1: cikti BORUYA baglanirsa (| tail) ajan kilitlenir -> dogrudan dosyaya.
    # TUZAK 2: Windows'ta cocuk surec, onu baslatan kabuk kapaninca BIRLIKTE OLUR.
    #   Uzun gorevler sessizce yarida kesilir (log'da yalniz acilis banner'i kalir).
    #   DETACHED_PROCESS + CREATE_NEW_PROCESS_GROUP ile ajani kabuktan KOPAR.
    bayraklar = 0
    if os.name == "nt":
        # DIKKAT: DETACHED_PROCESS KULLANMA — ajan konsolsuz kalinca ANINDA olur
        # (log 0 bayt, surec yok). Yalniz yeni surec grubu + penceresiz calistir.
        bayraklar = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200) |                     getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    with open(log, "wb") as f:
        if a.ajan == "gemini":
            girdi = subprocess.DEVNULL          # prompt zaten argv'de
            subprocess.Popen(cmd, cwd=a.cwd, stdout=f, stderr=subprocess.STDOUT,
                             stdin=girdi, creationflags=bayraklar, close_fds=True)
        else:
            with open(gorev, "rb") as g:        # prompt STDIN'den (cok satirli)
                subprocess.Popen(cmd, cwd=a.cwd, stdout=f, stderr=subprocess.STDOUT,
                                 stdin=g, creationflags=bayraklar, close_fds=True)
    print(str(log))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
