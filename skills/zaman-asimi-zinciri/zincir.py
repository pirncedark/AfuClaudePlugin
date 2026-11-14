"""Zaman asimi zinciri: bir alt-ajan turu (<=9,5 dk) kesilirse ayni gorevi
"kaldigin yerden devam" notuyla yeni turda yeniden baslatir.

Tek cagri = tek tur (Bash araci 10 dk ile sinirli). Cagiran (codex ajani)
cikti son satirindaki "ZINCIR: DEVAM --tur N" gorurse ayni komutu --tur N ile
tekrar calistirir. Durum ~/.claude/zincir_durum.json dosyasina yazilir;
durum cubugu bu dosyayi okur.

CODEX ICIN YENI DAVRANIS (22 Eki 2026 - GOREV_zincir_oturum_surdur):
  Codex artik AYRIK (detached) baslanir: kendi konsolu yok, gorunmez; ciktisi
  %TEMP%\\zincir_<hash>.log dosyasina akar; PID + log yolu %TEMP%\\zincir_<hash>.json
  durum dosyasinda tutulur (hash = DIZIN+GOREV+ajan, kimlik fonksiyonununkiyle ayni).
  * Tur siniri (570 sn) dolunca surec OLDURULMEZ; "ZINCIR: DEVAM" yazilip cikilir.
  * Sonraki tur durum dosyasini gorurse YENI codex acmaz; ayni PID'e baglanir,
    log'u kaldigi yerden okur ve bitmesini bekler (yine ayni sure siniriyla).
  * Surec bittiyse son yanit/ozet log'dan cikarilir; durum=BITTI (yalniz surec
    gercekten kota hatasiyla bittiyse durum=KOTA).
  * Log 30 dk hic buyumemis ve surec hala ayaktaysa durum=TAKILDI raporlanir
    (yine OLDURULMEZ) - karar kullaniciya sorulur.
  * flash/pro/opencode (gemini/opencode/freebuff) eski davranista KALIR:
    senkron subprocess.run ile calisir, sure dolarsa kapanir.
  * Test diki: ZINCIR_TEST_KOMUT ortam degiskeni subajan.py yerine sahte bir
    surec komutu calistirir (gorev maddesi 6'nin testi icin).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SUBAJAN = Path.home() / ".claude" / "skills" / "afu-ai" / "scripts" / "subajan.py"
DURUM = Path.home() / ".claude" / "zincir_durum.json"
BITMIS_SAKLA_SN = 15 * 60

# --- codex ayrik (detach) modu sabitleri --------------------------------------
TAKILDI_ESIK_SN = 30 * 60    # log bu kadar sure buyumemisse surec takilmistir
ESKI_DURUM_SN = 6 * 3600     # bitmis durum kaydi bu kadar eskiyse yok sayilir
BEKLE_ADIM_SN = 1.0          # surec canliligi bu aralikla yoklanir
LOG_GOSTER_SATIR = 12        # DEVAM mesajinda gosterilecek yeni log satiri

if os.name == "nt":
    # Pencere acmayan + ana konsoldan bagimsiz alt surec (subajan.py ile ayni bayrak).
    BAYRAK = (getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
              | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200))
else:
    BAYRAK = 0


def durum_oku() -> dict:
    try:
        return json.loads(DURUM.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def durum_yaz(kimlik: str, kayit: dict | None) -> None:
    veri = durum_oku()
    simdi = time.time()
    # Bitmis ve eskimis zincirleri at; cubuk yalniz guncel olani gostersin.
    veri = {k: v for k, v in veri.items()
            if v.get("durum") in ("CALISIYOR", "SIRADA")
            or simdi - float(v.get("guncellendi", 0)) < BITMIS_SAKLA_SN}
    if kayit is None:
        veri.pop(kimlik, None)
    else:
        veri[kimlik] = kayit
    gecici = DURUM.with_suffix(".tmp")
    gecici.write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(gecici, DURUM)


# ===================== codex ayrik modu yardimcilari ==========================

def surec_canli(pid: int) -> bool:
    """PID hala calisiyor mu? subajan._surec_canli ile ayni mantik (kopya bagimsiz)."""
    if pid <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    import ctypes
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, pid)          # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    kod = ctypes.c_ulong()
    ok = k.GetExitCodeProcess(h, ctypes.byref(kod))
    k.CloseHandle(h)
    return bool(ok) and kod.value == 259           # STILL_ACTIVE


def durum_yollari(kimlik: str) -> tuple[Path, Path, Path]:
    """(durum json, codex log, subajan stdout) yollari - hepsi %TEMP% icerisinde."""
    kok = Path(tempfile.gettempdir())
    return (kok / ("zincir_%s.json" % kimlik),
            kok / ("zincir_%s.log" % kimlik),
            kok / ("zincir_%s.out" % kimlik))


def kayit_oku(yol: Path) -> dict | None:
    try:
        veri = json.loads(yol.read_text(encoding="utf-8"))
        return veri if isinstance(veri, dict) else None
    except (OSError, ValueError):
        return None


def kayit_yaz(yol: Path, kayit: dict) -> None:
    try:
        gecici = yol.with_suffix(".tmp")
        gecici.write_text(json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(gecici, yol)
    except OSError:
        pass                                  # durum yazimi isin kendisini bozamaz


def dosya_bayt(yol: Path) -> bytes:
    try:
        with open(yol, "rb") as f:
            return f.read()
    except OSError:
        return b""


def dosya_oku(yol: Path) -> str:
    try:
        return yol.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def kota_imzasi(metin: str) -> bool:
    return bool(re.search(r"usage limit|rate limit|quota exceeded|you'?ve hit your usage limit",
                          metin, re.I))


def durum_cikar(metin: str, onceki: str = "") -> str:
    """Bitmis surecin durumu.

    Once subajan footer'indaki "durum=..." (en sonu) esas alinir; footer yoksa
    kota imzasi, basari-sizlik ipuclari ve cikti varligiyla karar verilir.
    Kota yalniz surecin kendisi kota hatasiyla bittiyse soylenir.
    """
    if metin.strip():
        eslesme = re.findall(r"durum=([A-Z_]+)", metin)
        if eslesme and eslesme[-1] in ("BITTI", "HATA", "KOTA", "ZAMAN_ASIMI"):
            return eslesme[-1]
        # Kota hatasi surecin SONUNDA gosterir; icerigin ortasinda gecen "usage limit"
        # ifadesi (ornek kod/yazi) KOTA sayilmaz - kota yalniz gercekten o sekilde
        # biten surece soylenir.
        if kota_imzasi(metin[-1500:]):
            return "KOTA"
        if re.search(r"Ajan baslatilamadi|ZINCIR HATA|Traceback \(most recent call last\)", metin):
            return "HATA"
        return "BITTI"
    # Hic cikti yok: daha once takilmiti diyorduysa onu koru, degilse hata.
    return onceki if onceki == "TAKILDI" else "HATA"


def ozet_cikar(metin: str) -> str:
    """Son yaniti/ozeti log'dan cikar (cok uzunsa ortadan kis)."""
    satirlar = [s for s in metin.splitlines() if s.strip()]
    if not satirlar:
        return "(surec hic cikti uretmedi)"
    if len(satirlar) > 200:
        satirlar = satirlar[:100] + ["... (kesildi) ..."] + satirlar[-100:]
    return "\n".join(satirlar)


def codex_komut(ns: argparse.Namespace, gorev: str, log_yol: Path) -> list[str]:
    test = os.environ.get("ZINCIR_TEST_KOMUT")
    if test:
        # Test diki: sahte surec dogrudan zincir tarafindan baslatilir (subajan yok).
        return shlex.split(test)
    # subajan --timeout 0 = SINIRSIZ: codex 570 sn'de taskkill edilmez, isini bitirir.
    # subajan --log-dosya    = codex JSON akisi sabit log yoluna yazar (buyume takibi).
    return [sys.executable, str(SUBAJAN), "codex", gorev, "--cwd", ns.cwd,
            "--timeout", "0", "--log-dosya", str(log_yol)]


def surec_baslat(ns: argparse.Namespace, gorev: str, kimlik: str) -> dict:
    """Codex'i AYRIK (gorunmez, kendi konsolu yok) baslat; PID + log yolu duruma yaz."""
    kayit_yol, log_yol, out_yol = durum_yollari(kimlik)
    for eski in (log_yol, out_yol):
        try:
            eski.unlink(missing_ok=True)
        except OSError:
            pass
    komut = codex_komut(ns, gorev, log_yol)
    with open(out_yol, "wb") as cikti_dosyasi:
        p = subprocess.Popen(komut, cwd=ns.cwd, stdin=subprocess.DEVNULL,
                             stdout=cikti_dosyasi, stderr=subprocess.STDOUT,
                             creationflags=BAYRAK, close_fds=True, shell=False)
    now = time.time()
    kayit = {"surum": 1, "ajan": ns.ajan, "gorev": ns.gorev[:120], "cwd": ns.cwd,
             "tur": ns.tur, "pid": p.pid, "log": str(log_yol), "out": str(out_yol),
             "komut": " ".join(komut)[:300],
             "basladi": now, "guncellendi": now, "son_buyume": now,
             "okunan": 0, "durum": "CALISIYOR", "ozet": ""}
    kayit_yaz(kayit_yol, kayit)
    return kayit


def sureci_bekle(kayit: dict, kayit_yol: Path, limit_sn: int) -> str:
    """Sureci OLDURMEDEN bekle. Donus: BITTI | SURE_DOLDU | TAKILDI."""
    pid = int(kayit.get("pid") or 0)
    log_yol = Path(kayit["log"])
    out_yol = Path(kayit["out"])
    basla = time.time()
    son_buyume = float(kayit.get("son_buyume") or basla)
    son_boyut = -1
    while True:
        simdi = time.time()
        try:
            mevcut = (log_yol.stat().st_size if log_yol.exists() else 0) \
                + (out_yol.stat().st_size if out_yol.exists() else 0)
        except OSError:
            mevcut = 0
        if mevcut != son_boyut:
            son_boyut, son_buyume = mevcut, simdi
        kayit["son_buyume"] = son_buyume
        kayit["guncellendi"] = simdi
        if not surec_canli(pid):
            kayit_yaz(kayit_yol, kayit)
            return "BITTI"
        if simdi - son_buyume > TAKILDI_ESIK_SN:
            kayit_yaz(kayit_yol, kayit)
            return "TAKILDI"
        if simdi - basla > limit_sn:
            kayit_yaz(kayit_yol, kayit)
            return "SURE_DOLDU"
        time.sleep(BEKLE_ADIM_SN)


def log_yeni_parca(kayit: dict) -> str:
    """Log'u KALDIGI YERDEN oku: son turdan bu yana yazilan yeni satirlar."""
    log_yol = Path(kayit["log"])
    try:
        boyut = log_yol.stat().st_size
    except OSError:
        return ""
    okunan = int(kayit.get("okunan") or 0)
    if boyut <= okunan:
        return ""
    try:
        with open(log_yol, "rb") as f:
            f.seek(okunan)
            veri = f.read()
    except OSError:
        return ""
    kayit["okunan"] = okunan + len(veri)
    satirlar = [s for s in veri.decode("utf-8", "replace").splitlines() if s.strip()]
    if not satirlar:
        return ""
    if len(satirlar) > LOG_GOSTER_SATIR:
        satirlar = ["..."] + satirlar[-LOG_GOSTER_SATIR:]
    return "\n".join(satirlar)


def takildi_mesaj(kayit: dict, bilgi: str) -> str:
    pid = int(kayit.get("pid") or 0)
    sagsn = max(0.0, time.time() - float(kayit.get("son_buyume") or time.time()))
    return ("%s\n"
            "TAKILDI: log %d dakikadir hic buyumuyor (esik %d dk). Surec OLDURULMEDI.\n"
            "SORU (kullaniciya): surec elle kontrol edilsin mi?\n"
            "  - log: %s\n"
            "  - gerekirse PID %s'i sen durdur; is bittigini dusunuyorsan durum dosyasini sil.\n"
            "durum=TAKILDI"
            % (bilgi, int(sagsn // 60), TAKILDI_ESIK_SN // 60, kayit["log"], pid))


def bitti_mesaj(kayit: dict, kayit_yol: Path, bilgi: str) -> str:
    """Surec bitti: son yaniti/ozeti log'dan cikar, durumu raporla."""
    pid = int(kayit.get("pid") or 0)
    out_metin = dosya_oku(Path(kayit["out"]))
    log_metin = dosya_oku(Path(kayit["log"]))
    metin = out_metin if out_metin.strip() else log_metin
    durum = durum_cikar(metin, kayit.get("durum") or "")
    kayit["durum"] = durum
    kayit["bitti"] = time.time()
    kayit["guncellendi"] = time.time()
    kayit["ozet"] = " ".join(metin.split())[:400]
    kayit_yaz(kayit_yol, kayit)
    return ("%s\n%s\n%s\ndurum=%s"
            % (bilgi + " - surec BTTI (yeni surec acilmadi)", ozet_cikar(metin), "", durum))


def codex_akisi(ns: argparse.Namespace, gorev: str, kimlik: str) -> str:
    """Codex turu: durum dosyasina gore baslat / baglan / bekle (asla oldurmez)."""
    kayit_yol, log_yol, out_yol = durum_yollari(kimlik)
    kayit = kayit_oku(kayit_yol)
    yeni_baslatti = False

    if kayit:
        pid = int(kayit.get("pid") or 0)
        bayat = time.time() - float(kayit.get("basladi") or 0) > ESKI_DURUM_SN
        if bayat and not surec_canli(pid):
            kayit = None                        # eski bitmis kayit: yok say, yeniden baslat
    if not kayit:
        kayit = surec_baslat(ns, gorev, kimlik)
        yeni_baslatti = True
        log_yol, out_yol = Path(kayit["log"]), Path(kayit["out"])

    pid = int(kayit.get("pid") or 0)
    bilgi = ("ZINCIR: surec %s pid=%d log=%s out=%s"
             % ("AYRIK BASLATILDI" if yeni_baslatti else "mevcut, AYNI surece baglanildi",
                pid, kayit["log"], kayit["out"]))

    # Daha once TAKILDI raporlandi ve log hala buyumuyorsa: yine oldurme, karar kullaniciya.
    if (kayit.get("durum") == "TAKILDI"
            and surec_canli(pid)
            and time.time() - float(kayit.get("son_buyume") or 0) > TAKILDI_ESIK_SN):
        return takildi_mesaj(kayit, bilgi)
    if kayit.get("durum") == "TAKILDI":
        kayit["durum"] = "CALISIYOR"            # surec toparladi ya da olmuistle normale don

    sonuc = sureci_bekle(kayit, kayit_yol, ns.timeout)

    if sonuc == "BITTI":
        return bitti_mesaj(kayit, kayit_yol, bilgi)
    if sonuc == "TAKILDI":
        kayit["durum"] = "TAKILDI"
        kayit_yaz(kayit_yol, kayit)
        return takildi_mesaj(kayit, bilgi)

    # SURE_DOLDU: surec OLDURULMADAN cik; sonraki tur ayni PID'e baglanacak.
    kayit["durum"] = "CALISIYOR"
    kayit["guncellendi"] = time.time()
    parca = log_yeni_parca(kayit)
    kayit_yaz(kayit_yol, kayit)
    mesaj = ("%s\n"
             "sure siniri %d sn doldu; surec OLDURULMEDI, aynen calisiyor "
             "(son log buyumesi %.0f sn once).\n"
             "Sonraki tur YENI surec acmaz; bu PID'e baglanir, log'u kaldigi yerden okur, "
             "bitmesini bekler." % (bilgi, ns.timeout,
                                    max(0.0, time.time() - float(kayit["son_buyume"]))))
    if parca:
        mesaj += "\nlog'un yeni satirlari:\n" + parca
    return mesaj + "\ndurum=ZAMAN_ASIMI"


def main() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("ajan", choices=["codex", "flash", "pro", "opencode"])
    a.add_argument("gorev")
    a.add_argument("--cwd", default=os.getcwd())
    a.add_argument("--tur", type=int, default=1)
    a.add_argument("--max", type=int, default=5)
    a.add_argument("--timeout", type=int, default=570)
    ns = a.parse_args()

    kimlik = hashlib.sha1(("%s|%s|%s" % (ns.ajan, ns.cwd, ns.gorev)).encode("utf-8")).hexdigest()[:10]
    gorev = ns.gorev.replace("\r", " ").replace("\n", " ")
    if ns.tur > 1:
        gorev = ("[tur %d/%d] DEVAM: onceki tur 10 dk sinirinda kesildi. Once git status ve "
                 "git diff ile yapilani kontrol et, yapilani TEKRARLAMA, kalandan devam et. "
                 "Asil gorev: %s" % (ns.tur, ns.max, gorev))

    kayit = {"ajan": ns.ajan, "gorev": ns.gorev[:120], "cwd": ns.cwd, "tur": ns.tur,
             "max": ns.max, "durum": "CALISIYOR", "basladi": time.time(),
             "guncellendi": time.time()}
    durum_yaz(kimlik, kayit)

    try:
        if ns.ajan == "codex":
            # Ayrik mod: surec zincir'den bagimsiz yasar, tur sinirinda OLDURULMEZ.
            cikti = codex_akisi(ns, gorev, kimlik)
        else:
            # gemini (flash/pro) ve opencode: eski, senkron davranis aynen devam.
            sonuc = subprocess.run(
                [sys.executable, str(SUBAJAN), ns.ajan, gorev, "--cwd", ns.cwd,
                 "--timeout", str(ns.timeout)],
                stdin=subprocess.DEVNULL, capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            cikti = (sonuc.stdout or "") + (sonuc.stderr or "")
    except Exception as exc:  # calistirici hic acilamadi
        cikti = "ZINCIR HATA: %s" % exc

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(cikti.rstrip())

    eslesme = re.findall(r"durum=([A-Z_]+)", cikti)
    son = eslesme[-1] if eslesme else "HATA"
    kayit["guncellendi"] = time.time()
    if son == "ZAMAN_ASIMI" and ns.tur < ns.max:
        kayit["durum"] = "SIRADA"
        durum_yaz(kimlik, kayit)
        print("ZINCIR: DEVAM --tur %d" % (ns.tur + 1))
    elif son == "ZAMAN_ASIMI":
        kayit["durum"] = "LIMIT"
        durum_yaz(kimlik, kayit)
        print("ZINCIR: BITTI (tur siniri %d doldu, is yarim)" % ns.max)
    elif son == "TAKILDI":
        # Surec yasiyor ve oldurulmedi; zincir kullaniciya sorulmak uzeren durur.
        kayit["durum"] = "TAKILDI"
        durum_yaz(kimlik, kayit)
        print("ZINCIR: BITTI (TAKILDI - surec oldurulmedi, kullaniciya soruldu)")
    else:
        kayit["durum"] = son
        durum_yaz(kimlik, kayit)
        print("ZINCIR: BITTI (%s, %d tur)" % (son, ns.tur))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
