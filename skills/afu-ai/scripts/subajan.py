# -*- coding: utf-8 -*-
"""Penceresiz subagent calistirici (afu-ai).

NEDEN VAR (19 Eyl 2026, Reyhan bildirdi):
  Ciplak `codex exec ...` / `omp ...` cagrilari Windows ortaminda her konsol komutu icin
  bir conhost.exe dogurur. Ebeveyn bitince conhost OLMEZ - oksuz kalir, ekranda
  bos siyah pencere olarak birikir. Tek bir codex kosusu conhost sayisini
  61 -> 1691 yapti; makine kilitlendi, pencereler ust uste yigildi.

NE YAPAR:
  1. Alt-ajani CREATE_NO_WINDOW + CREATE_NEW_PROCESS_GROUP ile calistirir
     (hicbir pencere acilmaz).
  2. stdin DEVNULL kaynagina baglanir (codex "Reading additional input from stdin" ile
     beklemesin).
  3. Cikti dogrudan dosyaya gider - BORU (| tail) YOK (boru ajani kilitler).
  4. Is bitince oksuz conhost sureclerini otomatik temizler.

KULLANIM:
  python subajan.py codex "<gorev>" [--cwd DIZIN] [--timeout 600]
  python subajan.py flash "<gorev>" [--cwd DIZIN]
  python subajan.py pro   "<gorev>" [--cwd DIZIN]
  python subajan.py opencode "<gorev>" [--cwd DIZIN]
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from canli_durum import JSONLParser, StatusFile, cleanup_statuses, new_status

KOK = Path(__file__).resolve().parent
TEMIZLEYICI = KOK / "conhost_temizle.ps1"

# Windows ortaminda pencere acmayan bayraklar. DETACHED_PROCESS KULLANMA:
# ajan konsolsuz kalinca aninda olur (log 0 bayt).
if os.name == "nt":
    BAYRAK = (getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
              | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200))
else:
    BAYRAK = 0


def cozumle(ad: str, exe_once: bool = False) -> str:
    """Windows ortaminda codex/omp birer .cmd shim dosyasidir. shell=False Popen ciplak adi
    BULAMAZ (WinError 2). Tam yolu burada cozeriz - shell=True kullanmayiz,
    cunku shell=True fazladan bir cmd.exe + conhost daha dogurur."""
    if exe_once and os.name == "nt":
        yol = shutil.which(ad + ".exe")
        if yol:
            return yol
    yol = shutil.which(ad)
    if not yol:
        raise SystemExit("%s bulunamadi (PATH icinde yok) - login/kurulum gerek" % ad)
    return yol


def contrat_schema() -> dict:
    return {
        "type": "object",
        "required": ["karar", "ozet", "dosyalar", "test", "commit"],
        "additionalProperties": False,
        "properties": {
            "karar": {"type": "string", "enum": ["TAMAM", "KISMEN", "RET"]},
            "ozet": {"type": "string", "description": "En fazla 300 karakter", "maxLength": 300},
            "dosyalar": {"type": "array", "items": {"type": "string"}},
            "test": {"type": "string"},
            "commit": {"type": "string"},
        },
    }


def sozlesme_cikti(value: str) -> tuple[str, str | None]:
    try:
        decoded = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value, "gecersiz"
    return json.dumps(decoded, ensure_ascii=False, separators=(",", ":")), None


def find_rollout(sessions: Path, thread_id: str,
                 today: datetime.date | None = None) -> Path | None:
    current = today or datetime.date.today()
    for day in (current, current - datetime.timedelta(days=1)):
        folder = sessions / day.strftime("%Y/%m/%d")
        matches = list(folder.glob("rollout-*-%s.jsonl" % thread_id))
        if matches:
            return matches[0]
    return None


def retry_rollout_find(sessions: Path, thread_id: str, last_search: float,
                       now: float) -> tuple[Path | None, float]:
    if now - last_search < 3:
        return None, last_search
    return find_rollout(sessions, thread_id), now


def komut_kur(ajan: str, gorev: str, last_message: str | None = None,
              options: argparse.Namespace | None = None) -> list[str] | tuple[list[str], str]:
    if ajan == "codex":
        # --skip-git-repo-check: guvenilir dizin disinda sart, yoksa hic calismaz.
        # --sandbox workspace-write: varsayilan read-only, kod yazamaz (23 Eyl 2026).
        command = [cozumle("codex"), "exec", "--json", "--skip-git-repo-check",
                   "--sandbox", "workspace-write"]
        if options and options.worktree:
            command.append("--worktree")
        schema_path = None
        if options and options.sozlesme:
            fd, schema_path = tempfile.mkstemp(prefix="subajan_schema_", suffix=".json")
            with os.fdopen(fd, "w", encoding="utf-8") as schema_file:
                json.dump(contrat_schema(), schema_file, ensure_ascii=False, separators=(",", ":"))
            command.extend(["--output-schema", schema_path])
        command.extend(["-o", last_message or "", gorev])
        return (command, schema_path) if schema_path else command
    if ajan == "flash":
        return [cozumle("omp"), "-p", "--mode", "json",
                "--model", "google-antigravity/gemini-3.8-flash", gorev]
    if ajan == "pro":
        # :high ZORUNLU - seviyesiz cagrilirsa omp sessizce takilir.
        return [cozumle("omp"), "-p", "--mode", "json",
                "--model", "google-antigravity/gemini-3.1-pro:high", gorev]
    if ajan == "opencode":
        # Once dogrudan .exe aranir. Shim gerekirse shell=False ile calisir.
        return [cozumle("opencode", exe_once=True), "run", "--format", "json", gorev]
    raise SystemExit("bilinmeyen ajan: %s (codex|flash|pro|opencode)" % ajan)


def opencode_kota_dolu(metin: str) -> bool:
    """Non interactive OpenCode kota imzasini belirle.

    ESKI HALI (bozuktu): `len(metin.encode()) == 35 and "big-pickle" in metin`.
    35 rakami `wc -c` ile HAM dosyadan olculmustu; buraya gelen metin ise
    read_text() ile okundugu icin CRLF -> LF cevrilmis ve 32 bayta dusuyordu.
    Dedektor hicbir zaman ateslemedi (20 Eyl 2026 tarihinde olculdu) - bu yuzden kota
    dolulugu hic raporlanmadi ve durum cubugu kanitsiz kaldi.

    YENI: bayt uzunluguna ve oturum adina ("big-pickle") guvenme. Anlam sudur:
    opencode SADECE banner satirini bastiysa (">" ile baslayan tek satir) gercek
    bir cevap uretmemistir = kota dolu / is yapilamadi.
    """
    sade = re.sub(r"\x1b\[[0-9;]*m", "", metin).strip()
    if not sade:
        return False                                  # bos cikti = baska ariza
    satirlar = [s for s in sade.splitlines() if s.strip()]
    return len(satirlar) == 1 and satirlar[0].lstrip().startswith(">")


def kota_tespit(ajan: str, parser: JSONLParser, cikti: str) -> bool:
    if parser.durum == "KOTA":
        return True
    if ajan != "opencode":
        return False
    return ((parser.plain_opencode_quota and not parser.saw_text_or_step_finish) or
            opencode_kota_dolu(cikti))


def runner_exit_code(kota_dolu: bool, kod: int) -> int:
    if kota_dolu:
        return 3
    return 0 if kod == 0 else 1


def runner_outcome(ajan: str, parser: JSONLParser, cikti: str, kod: int,
                   timed_out: bool = False) -> tuple[str, int, bool]:
    kota_dolu = kota_tespit(ajan, parser, cikti)
    if timed_out:
        durum = "ZAMAN_ASIMI"
    elif kota_dolu:
        durum = "KOTA"
    else:
        durum = "BITTI" if kod == 0 else "HATA"
    return durum, runner_exit_code(kota_dolu, kod), kota_dolu


# Durum cubugu (ajan_token.sh) bu dosyayi okur: icinde opencode kotasinin
# yenilenecegi epoch saniye yazar. 20 Eyl 2026 tarihine kadar dedektor bulgusunu
# HICBIR yere yazmiyordu; cubugun okuyacagi kanit olmadigi icin OPENCODE satiri
# sabit "dolu/100%" gosteriyor ve opencode icin hic is verilmiyordu.
OPENCODE_KOTA_DOSYASI = Path.home() / ".claude" / ".opencode_yenilenme"
# opencode gercek yenilenme suresini bildirmiyor; cubuktaki diger saglayicilarla
# ayni 5 saatlik pencere varsayilir. Log icinde "retrying in ..." varsa ajan_token.sh
# zaten onu tercih eder (daha kesin kaynak).
OPENCODE_KOTA_PENCERESI_SN = 5 * 3600


def opencode_kota_isaretle(dolu: bool) -> None:
    """Kota durumunu durum cubugunun okuyabilecegi dosyaya yaz/sil."""
    try:
        if dolu:
            OPENCODE_KOTA_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
            hedef = int(time.time()) + OPENCODE_KOTA_PENCERESI_SN
            OPENCODE_KOTA_DOSYASI.write_text(str(hedef), encoding="utf-8")
        elif OPENCODE_KOTA_DOSYASI.exists():
            OPENCODE_KOTA_DOSYASI.unlink()      # basarili kosu = kota geri geldi
    except OSError:
        pass                                     # isaret sirf gosterim; isi bozma


def temizle() -> str:
    if os.name != "nt" or not TEMIZLEYICI.exists():
        return ""
    try:
        s = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", str(TEMIZLEYICI)],
            capture_output=True, text=True, timeout=180, creationflags=BAYRAK)
        return s.stdout.strip()
    except Exception as hata:            # temizlik basarisiz olsa da is bitti
        return "temizlik atlandi: %s" % hata


def main() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("ajan", choices=["codex", "flash", "pro", "opencode"])
    a.add_argument("gorev")
    a.add_argument("--cwd", default=os.getcwd())
    a.add_argument("--timeout", type=int, default=600)
    a.add_argument("--ham", action="store_true")
    a.add_argument("--sozlesme", action="store_true")
    a.add_argument("--worktree", action="store_true")
    ns = a.parse_args()

    log = Path(tempfile.gettempdir()) / ("subajan_%s_%d.log" % (ns.ajan, int(time.time())))
    basla = time.time()
    status_dir = Path(os.environ.get("SUBAJAN_STATUS_DIR", str(Path.home() / ".claude" / "afu-ajanlar")))
    cleanup_statuses(status_dir)
    parser = JSONLParser(ns.ajan)
    last_message = None
    if ns.ajan == "codex":
        fd, name = tempfile.mkstemp(prefix="subajan_ozet_", suffix=".txt")
        os.close(fd)
        last_message = name
    status = None
    kod = -1
    timed_out = False
    rollout_path = None
    last_rollout_search = 0.0
    rollout_offset = 0
    log_offset = 0
    schema_path = None
    contract_status = None
    final_message = None
    try:
        with open(log, "wb") as f:
            command_result = komut_kur(ns.ajan, ns.gorev, last_message, ns)
            if isinstance(command_result, tuple):
                command, schema_path = command_result
            else:
                command = command_result
            if ns.sozlesme and ns.ajan != "codex":
                print("UYARI: --sozlesme yalniz codex icin desteklenir; yok sayildi")
            p = subprocess.Popen(command, cwd=ns.cwd,
                                 stdout=f, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL,
                                 creationflags=BAYRAK, close_fds=True, shell=False)
            payload = new_status(ns.ajan, ns.gorev, ns.cwd, basla, p.pid)
            payload["log"] = str(log)
            status = StatusFile(status_dir, payload["id"])
            status.write(payload)
            deadline = basla + ns.timeout
            while True:
                kalan = deadline - time.time()
                if kalan <= 0:
                    p.kill()
                    p.wait()
                    timed_out = True
                    kod = -1
                else:
                    try:
                        kod = p.wait(timeout=min(2.0, kalan))
                    except subprocess.TimeoutExpired:
                        kod = None
                f.flush()
                with open(log, "rb") as reader:
                    reader.seek(log_offset)
                    new_bytes = reader.read()
                    log_offset += len(new_bytes)
                parser.feed(new_bytes)
                now = time.monotonic()
                if parser.thread_id and rollout_path is None:
                    sessions = Path.home() / ".codex" / "sessions"
                    rollout_path, last_rollout_search = retry_rollout_find(
                        sessions, parser.thread_id, last_rollout_search, now)
                if rollout_path is not None:
                    try:
                        with open(rollout_path, "rb") as reader:
                            reader.seek(rollout_offset)
                            token_bytes = reader.read()
                            rollout_offset += len(token_bytes)
                        parser.live_token_count(token_bytes)
                    except OSError:
                        pass
                payload["guncellendi"] = time.time()
                payload["eylem"] = parser.eylem
                payload["token"] = parser.token
                payload["ozet"] = parser.ozet[:500]
                status.write(payload)
                if kod is not None:
                    parser.finish()
                    break
            cikti = log.read_text(encoding="utf-8", errors="replace")
            durum, _, kota_dolu = runner_outcome(ns.ajan, parser, cikti, kod, timed_out)
            if ns.ajan == "codex" and last_message:
                try:
                    candidate = Path(last_message).read_text(encoding="utf-8", errors="replace").strip()
                    if candidate:
                        final_message = candidate if ns.sozlesme else " ".join(candidate.split())
                        parser.ozet = final_message
                except OSError:
                    pass
            if ns.ajan == "codex" and ns.sozlesme:
                parser.ozet, contract_status = sozlesme_cikti(parser.ozet)
            payload.update({"durum": durum, "bitti": time.time(), "guncellendi": time.time(),
                            "cikis": kod, "token": parser.token, "eylem": parser.eylem,
                            "ozet": parser.ozet if ns.ajan == "codex" and ns.sozlesme else parser.ozet[:500]})
            status.write(payload)
    except OSError as hata:
        print("Ajan baslatilamadi: %s" % hata)
        kod = 1
        cikti = ""
        kota_dolu = False
        durum = "HATA"
    finally:
        if last_message:
            try:
                os.unlink(last_message)
            except OSError:
                pass
        if schema_path:
            try:
                os.unlink(schema_path)
            except OSError:
                pass
    sure = time.time() - basla
    if ns.ajan == "opencode":
        # Durum cubugu kanita baksin diye bulguyu dosyaya yaz (dolu) / sil (acik).
        opencode_kota_isaretle(kota_dolu)

    if ns.ajan == "codex" and ns.sozlesme:
        print(final_message if final_message is not None else parser.ozet)
    elif ns.ajan == "codex" and final_message is not None:
        print(final_message)
    elif ns.ham:
        print(cikti)
    elif parser.event_count:
        print(parser.ozet)
    else:
        print("\n".join(cikti.splitlines()[-20:]))
    print("-" * 60)
    footer = "ajan=%s cikis=%s sure=%.1fs token=%s durum=%s log=%s" % (
        ns.ajan, kod, sure, parser.token if parser.token is not None else "?", durum, log)
    if ns.ajan == "codex" and ns.sozlesme and contract_status:
        footer += " sozlesme=" + contract_status
    print(footer)
    ozet = temizle()
    if ozet:
        print("[conhost temizligi]")
        print(ozet)
    # opencode/omp sessizligi = KOTA olabilir, kilitlenme degil.
    return runner_exit_code(kota_dolu, kod)


if __name__ == "__main__":
    sys.exit(main())
