#!/bin/bash
# Ajan token toplayicisi — statusline icin. 30 sn onbellekli (alt bari yavaslatmaz).
#
# PENCERE FIRTINASI DUZELTMESI (20 Eyl 2026):
#   ESKI HALI: her log dosyasi icin ayri sed|grep|tail|tr|grep boru hatti kuruluyordu.
#   ~150 log => kosu basina ~600 surec (= 600 conhost penceresi) ve 47 SANIYE.
#   Statusline 47 sn'den cok daha sik yenilendigi ve onbellek EN SONDA yazildigi icin
#   kopyalar ust uste binip makineyi kilitliyordu. Alt-ajan/opencode calisinca log
#   sayisi artiyor, bu yuzden "supagent gelince cokuyor" diye gorunuyordu.
#   COZUM: (1) tek-ornek kilidi — ikinci kopya hic calismaz, eski onbellegi basar.
#          (2) log taramasi glob basina TEK awk — ~600 surec yerine 3.
ONBELLEK="$HOME/.claude/.ajan_token.cache"

# ============ CLAUDE SATIRI HER CAGRI TAZE (23 Eyl 2026) ============
# Onbellege YALNIZ ajan (GEMINI/CODEX/OPENCODE) satirlari yazilir; CLAUDE satiri
# her cagrida CLAUDE_PCT/CLAUDE_TOKENS/CLAUDE_RESET/CLAUDE_COST ortamindan taze
# uretilir ve ajan satirlarindan ONCE basilir. Bunun icin bar, k, _fmt ve
# kumulatif maliyet dosyanin basina tasindi ki erken cikis yollarinda (onbellek
# hit, kilit geri_cekil) da kullanilabilsin.
# PENCERE KURALI: .exe cagrisi YOK; yalniz printf/awk/cat/sort.

k() { if [ "$1" -ge 1000 ]; then echo "$(( $1 / 1000 ))K"; else echo "$1"; fi; }

bar() {
    # MSYS bash'te ${s:0:n} BAYT keser ve UTF-8 blok karakterini bozar -> dongu ile kur.
    local p=$1 d i o=""
    d=$(( (p + 5) / 10 ))
    (( d < 0 ))  && d=0
    (( d > 10 )) && d=10
    for ((i=0; i<d;  i++)); do o="$o█"; done
    for ((i=d; i<10; i++)); do o="$o░"; done
    printf '%s' "$o"
}

_fmt='\033[%sm%-8s %s\033[0m \033[2;37m%3s%% │ \033[%sm%5s\033[0m\033[2;37m │ ↻ %s\033[0m'

# Claude'un KENDI maliyeti (statusline'dan CLAUDE_COST ile gelir) — ajanlar bedava
# calisirken asil parayi Claude yaktigi icin ayni satirda gorunur.
# KUMULATIF: oturum maliyeti dusse bile toplam geri gitmesin diye kalici sayacta tutulur.
claude_satiri() {
    local CL_TOPLAM_DOSYA="$HOME/.claude/.claude_maliyet_toplam"
    local cl_now cl_onceki cl_toplam cl_tok cl_pct cl_yen cl_bar
    cl_now=$(awk -v c="${CLAUDE_COST:-0}" 'BEGIN{printf "%.4f", (c=="")?0:c}' 2>/dev/null || echo 0)
    cl_onceki=$(cat "$CL_TOPLAM_DOSYA" 2>/dev/null | grep -E '^[0-9.]+$' || echo 0)
    cl_toplam=$(awk -v a="$cl_now" -v b="$cl_onceki" 'BEGIN{printf "%.4f", (a>b)?a:b}')
    [ "$cl_toplam" != "$cl_onceki" ] && echo "$cl_toplam" > "$CL_TOPLAM_DOSYA"
    # Claude satiri da ajanlarla AYNI kalipta: %kota  token  yen. saat  (+ maliyet)
    cl_tok=$(k "$(printf '%s' "${CLAUDE_TOKENS:-0}" | grep -E '^[0-9]+$' || echo 0)")
    if [ -z "${CLAUDE_PCT:-}" ]; then cl_pct="?"; else cl_pct=$(awk -v p="$CLAUDE_PCT" 'BEGIN{printf "%.0f", p}' 2>/dev/null || echo "?"); fi
    cl_yen="${CLAUDE_RESET:-?}"; [ -z "$cl_yen" ] && cl_yen="?"
    cl_bar=$(case "$cl_pct" in ''|*[!0-9]*) bar 0;; *) bar "$cl_pct";; esac)
    printf "$_fmt\n" "38;5;209" "CLAUDE" "$cl_bar" "$cl_pct" "38;5;209" "$cl_tok" "$cl_yen"
}

if [ -f "$ONBELLEK" ]; then
  yas=$(( $(date +%s) - $(stat -c%Y "$ONBELLEK" 2>/dev/null || echo 0) ))
  [ "$yas" -lt 30 ] && { claude_satiri; cat "$ONBELLEK"; exit 0; }
fi

# --- tek-ornek kilidi: ayni anda ikinci kopya ASLA kosmasin ---
KILIT="$HOME/.claude/.ajan_token.lock"

# Kilit baskasindayken cikarken ASLA sessiz cikma: cubuk tamamen kaybolur
# (20 Eyl 2026'da olculdu — onbellek silinmisken es zamanli render bos bar verdi).
# Onbellek varsa onu bas; yoksa kilidin sahibinin onbellegi yazmasini kisa sure
# bekle; yine yoksa en azindan bir yer tutucu bas.
geri_cekil() {
  if [ -f "$ONBELLEK" ]; then claude_satiri; cat "$ONBELLEK"; exit 0; fi
  local i
  for i in 1 2 3 4 5 6 7 8 9 10; do
    sleep 0.5
    [ -f "$ONBELLEK" ] && { claude_satiri; cat "$ONBELLEK"; exit 0; }
  done
  claude_satiri
  printf '\033[2;37m… ajan tokenleri hesaplaniyor\033[0m\n'
  exit 0
}

if ! mkdir "$KILIT" 2>/dev/null; then
  # kilit 180 sn'den eskiyse sahibi olmustur — devral, degilse geri cekil.
  kilit_yas=$(( $(date +%s) - $(stat -c%Y "$KILIT" 2>/dev/null || echo 0) ))
  [ "$kilit_yas" -lt 180 ] && geri_cekil
  rm -rf "$KILIT" 2>/dev/null
  mkdir "$KILIT" 2>/dev/null || geri_cekil
fi
trap 'rm -rf "$KILIT" 2>/dev/null' EXIT

shopt -s nullglob

A="${TEMP:-/tmp}/ajan-kopru"
cx=0; oc=0; gm=0

# Dosya basina SON "totalTokens":N ve "tokens used" altindaki sayiyi tek awk ile cikarir.
# Cikti satirlari: <dosyaadi>\t<totalTokens|0>\t<tokensused|0>
TARA_AWK='
{
  line = $0
  gsub(/\033\[[0-9;]*m/, "", line)
  if (match(line, /"totalTokens":[0-9]+/))
    tt[FILENAME] = substr(line, RSTART + 14, RLENGTH - 14) + 0
  if (bekle[FILENAME]) {
    t = line; gsub(/[ .\r]/, "", t)
    if (t ~ /^[0-9]+$/) tu[FILENAME] = t + 0
    bekle[FILENAME] = 0
  }
  if (line ~ /^tokens used/) bekle[FILENAME] = 1
}
END { for (f in gorulen) printf "%s\t%d\t%d\n", f, tt[f], tu[f] }
{ gorulen[FILENAME] = 1 }
'

# 1) ajan-kopru loglari: "tokens used" sayisi, dosya adina gore codex/opencode
for kayit in $(awk "$TARA_AWK" "$A"/*.log 2>/dev/null | tr -d ' ' | tr '\t' '|'); do
  f="${kayit%%|*}"; rest="${kayit#*|}"; tt="${rest%%|*}"; t="${rest#*|}"
  case "$f" in
    *_gemini_*)   [ "${tt:-0}" -gt 0 ] 2>/dev/null && gm=$((gm + tt)) ;;
    *_codex_*)    [ "${t:-0}"  -gt 0 ] 2>/dev/null && cx=$((cx + t))  ;;
    *_opencode_*) [ "${t:-0}"  -gt 0 ] 2>/dev/null && oc=$((oc + t))  ;;
  esac
done

# 2) scratchpad loglari: totalTokens -> gemini, yoksa "tokens used" -> codex
for kayit in $(awk "$TARA_AWK" "${TEMP:-/tmp}"/claude/*/*/scratchpad/*.log 2>/dev/null | tr -d ' ' | tr '\t' '|'); do
  rest="${kayit#*|}"; tt="${rest%%|*}"; tu="${rest#*|}"
  if [ "${tt:-0}" -gt 0 ] 2>/dev/null; then gm=$((gm + tt))
  elif [ "${tu:-0}" -gt 0 ] 2>/dev/null; then cx=$((cx + tu)); fi
done

# 3) subajan.py loglari: totalTokens, dosya adina gore dagit
for kayit in $(awk "$TARA_AWK" "${TEMP:-/tmp}"/subajan_*.log 2>/dev/null | tr -d ' ' | tr '\t' '|'); do
  f="${kayit%%|*}"; rest="${kayit#*|}"; tt="${rest%%|*}"
  [ "${tt:-0}" -gt 0 ] 2>/dev/null || continue
  case "$f" in
    *_flash_*|*_pro_*) gm=$((gm + tt)) ;;
    *_codex_*)         cx=$((cx + tt)) ;;
    *_opencode_*)      oc=$((oc + tt)) ;;
  esac
done

# OpenCode token kaynagi: SQLite message.data icindeki assistant tokenleri.
# Cache 300 saniye kullanilir; DB okunamazsa onceki dort alan korunur.
OC_DURUM_ONB="$HOME/.claude/.opencode_durum.cache"
OC_TOKEN_DB="$HOME/.local/share/opencode/opencode.db"
oc_db_durum=""
oc_token_yas=999999
[ -f "$OC_DURUM_ONB" ] && oc_token_yas=$(( $(date +%s) - $(stat -c%Y "$OC_DURUM_ONB" 2>/dev/null || echo 0) ))
if [ "${oc_token_yas:-999999}" -gt 300 ]; then
  oc_db_yeni=$(python - "$OC_TOKEN_DB" <<PY 2>/dev/null
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime

db_path = sys.argv[1]
try:
    conn = sqlite3.connect("file:" + db_path + "?mode=ro", uri=True, timeout=2)
    total = 0
    recent = 0
    last_success = 0
    cutoff_ms = (time.time() - 18000) * 1000
    messages = []
    for row in conn.execute("SELECT data FROM message"):
        raw = row[0]
        item = json.loads(raw)
        if item.get("role") != "assistant":
            continue
        tokens = item.get("tokens") or {}
        count = int(tokens.get("input") or 0) + int(tokens.get("output") or 0) + int(tokens.get("reasoning") or 0)
        total += count
        created = (item.get("time") or {}).get("created") or 0
        messages.append((int(created / 1000), count))
        if created >= cutoff_ms:
            recent += count
        if int(tokens.get("output") or 0) > 0:
            completed = (item.get("time") or {}).get("completed") or created
            last_success = max(last_success, int(completed / 1000))
    conn.close()
    last_error = 0
    limit_path = os.path.expanduser("~/.claude/.opencode_limit_tahmin")
    old_limit = 0
    try:
        with open(limit_path, "r", encoding="ascii") as limit_file:
            value = limit_file.read().strip()
            if value.isdigit():
                old_limit = int(value)
    except OSError:
        pass
    log_path = os.path.expanduser("~/.local/share/opencode/log/opencode.log")
    events = []
    try:
        with open(log_path, "rb") as log_file:
            if os.path.exists(limit_path):
                log_file.seek(0, os.SEEK_END)
                size = log_file.tell()
                log_file.seek(max(0, size - 4 * 1024 * 1024))
            tail = log_file.read().decode("utf-8", errors="replace")
        for line in tail.splitlines():
            if "Rate limit exceeded" not in line:
                continue
            match = re.search(r"timestamp=(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z)", line)
            if match:
                stamp = datetime.fromisoformat(match.group(1).replace("Z", "+00:00"))
                event_time = int(stamp.timestamp())
                events.append(event_time)
                last_error = max(last_error, event_time)
    except OSError:
        pass
    events.sort()
    # Tahmini limit = gecmiste KESILMEDEN ulasilmis en yuksek 5 saatlik kullanim.
    # (Eski yontem kesilme anlarindaki kullanimi aliyordu; limit sabit olmadigi icin
    # acik iken ~99 gosterip celisiyordu.) Kayan 5 saat penceresi, tek gecis.
    limit = old_limit
    messages.sort()
    window_sum = 0
    start = 0
    for created, count in messages:
        window_sum += count
        while messages[start][0] < created - 18000:
            window_sum -= messages[start][1]
            start += 1
        if window_sum > limit:
            limit = window_sum
    if limit > 0:
        with open(limit_path, "w", encoding="ascii") as limit_file:
            limit_file.write(str(limit))
    print(f"{total}|{recent}|{last_success}|{last_error}|{limit}")
except Exception:
    sys.exit(1)
PY
)
  case "$oc_db_yeni" in
    *'|'*'|'*'|'*) oc_db_durum="$oc_db_yeni"; printf '%s\n' "$oc_db_durum" > "$OC_DURUM_ONB" ;;
  esac
fi
if [ -z "$oc_db_durum" ]; then oc_db_durum=$(cat "$OC_DURUM_ONB" 2>/dev/null | grep -E '^[0-9]+\|[0-9]+\|[0-9]+\|[0-9]+(\|[0-9]+)?$' || true); fi
if [ -n "$oc_db_durum" ]; then
  IFS='|' read -r oc_db_token oc_5s oc_son_basari oc_son_hata oc_limit <<EOF
$oc_db_durum
EOF
  [ -n "$oc_limit" ] || oc_limit=0
  oc=$oc_db_token
else
  oc=$(cat "$HOME/.claude/.opencode_toplam" 2>/dev/null | grep -E '^[0-9]+$' || echo 0)
  oc_5s="?"; oc_son_basari=0; oc_son_hata=0; oc_limit=0
fi

CX_TOPLAM_DOSYA="$HOME/.claude/.codex_toplam"
cx_onceki=$(cat "$CX_TOPLAM_DOSYA" 2>/dev/null | grep -E '^[0-9]+$' || echo 0)
cx_toplam=$cx_onceki
[ "$cx" -gt "$cx_onceki" ] && { cx_toplam=$cx; echo "$cx" > "$CX_TOPLAM_DOSYA"; }

# gemini/opencode icin de ayni kumulatif koruma: log temizlenirse sayac geri gitmesin
GM_TOPLAM_DOSYA="$HOME/.claude/.gemini_toplam"
gm_onceki=$(cat "$GM_TOPLAM_DOSYA" 2>/dev/null | grep -E '^[0-9]+$' || echo 0)
[ "$gm" -gt "$gm_onceki" ] && echo "$gm" > "$GM_TOPLAM_DOSYA" || gm=$gm_onceki
OC_TOPLAM_DOSYA="$HOME/.claude/.opencode_toplam"
oc_onceki=$(cat "$OC_TOPLAM_DOSYA" 2>/dev/null | grep -E '^[0-9]+$' || echo 0)
[ "$oc" -gt "$oc_onceki" ] && echo "$oc" > "$OC_TOPLAM_DOSYA" || oc=$oc_onceki

# KOTA YUZDELERI — `omp usage` gercek saglayici limitlerini verir (5 saatlik pencere).
# Yavas oldugu icin AYRI ve daha uzun onbellek (5 dk).
# omp'un "resets in" suresini saniyeye cevirir; cozemiyorsa basarisiz olur.
sure_sn() {
  local kalan="$1" sayi birim toplam=0 bulundu=0
  [ -n "$kalan" ] || return 1
  if [[ "$kalan" =~ ^[0-9]+$ ]]; then printf '%s' "$kalan"; return 0; fi
  while [[ "$kalan" =~ ^([0-9]+)([dhms])(.*)$ ]]; do
    sayi="${BASH_REMATCH[1]}"; birim="${BASH_REMATCH[2]}"; kalan="${BASH_REMATCH[3]}"; bulundu=1
    case "$birim" in d) toplam=$((toplam + sayi * 86400));; h) toplam=$((toplam + sayi * 3600));; m) toplam=$((toplam + sayi * 60));; s) toplam=$((toplam + sayi));; esac
  done
  if [ "$bulundu" = 1 ] && [[ "$kalan" =~ ^[0-9]+$ ]]; then
    toplam=$((toplam + kalan)); kalan=""
  fi
  [ "$bulundu" = 1 ] && [ -z "$kalan" ] || return 1
  printf '%s' "$toplam"
}

# Goreli sureyi statusline'daki Claude kota uslubuyla mutlak yenilenme saatine cevirir.
yen_saati() {
  local sn hedef bugun gun hafta saat yas=${2:-0}
  if [[ "$1" =~ ^@([0-9]+)$ ]]; then
    hedef="${BASH_REMATCH[1]}"
  else
    sn=$(sure_sn "$1") || { printf '%s' "$1"; return; }
    sn=$((sn - yas))
    [ "$sn" -lt 0 ] && sn=0
    hedef=$(date -d "+$sn seconds" +%s 2>/dev/null) || { printf '%s' "$1"; return; }
  fi
  bugun=$(date +%F); gun=$(date -d "@$hedef" +%F 2>/dev/null) || { printf '%s' "$1"; return; }
  saat=$(date -d "@$hedef" +%H:%M 2>/dev/null) || { printf '%s' "$1"; return; }
  [ "$gun" = "$bugun" ] && { printf '%s' "$saat"; return; }
  case "$(date -d "@$hedef" +%u 2>/dev/null)" in
    1) hafta=Pzt;; 2) hafta=Sal;; 3) hafta=Car;; 4) hafta=Per;; 5) hafta=Cum;; 6) hafta=Cmt;; 7) hafta=Paz;; *) printf '%s' "$1"; return;;
  esac
  printf '%s %s' "$hafta" "$saat"
}

KOTA_ONB="$HOME/.claude/.ajan_kota.cache"
kota_yas=999999
[ -f "$KOTA_ONB" ] && kota_yas=$(( $(date +%s) - $(stat -c%Y "$KOTA_ONB" 2>/dev/null || echo 0) ))
kota_alan=$(awk -F'|' 'NR==1{print NF}' "$KOTA_ONB" 2>/dev/null)
# sayi kontrolu: sayisal degilse 1 doner (kota/onbellek bozuk demektir)
sayi_mi() { case "$1" in ''|*[!0-9]*) return 1;; *) return 0;; esac; }
if [ "${kota_yas:-999999}" -gt 300 ] || [ "$kota_alan" != "6" ]; then
  timeout 20 omp usage --json </dev/null 2>/dev/null > "$KOTA_ONB.ham" 2>/dev/null
  kota_yeni=$(python - "$KOTA_ONB.ham" <<'PYJSON'
import json
import sys

try:
    with open(sys.argv[1], "r", encoding="utf-8") as source:
        data = json.load(source)
    reports = data.get("reports")
    if not isinstance(reports, list):
        raise ValueError("reports missing")

    def chosen(provider, candidates):
        report = next((r for r in reports if isinstance(r, dict) and r.get("provider") == provider), None)
        if report is None or not isinstance(report.get("limits"), list):
            return "?", "?", "-"
        found = {}
        for item in report["limits"]:
            if not isinstance(item, dict):
                continue
            window = item.get("window") or {}
            amount = item.get("amount") or {}
            if not isinstance(window, dict) or not isinstance(amount, dict):
                continue
            key = (item.get("label"), window.get("id"))
            if key in candidates:
                try:
                    used = int(float(amount["used"]))
                    reset = "@" + str(int(window["resetsAt"]) // 1000)
                    found[key] = (used, reset)
                except (KeyError, TypeError, ValueError, OverflowError):
                    pass
        options = [(found[key][0], priority, found[key][1], tag)
                   for priority, (key, tag) in enumerate(candidates.items()) if key in found]
        if not options:
            return "?", "?", "-"
        # Max pct; priority preserves 5h tie preference.
        pct, priority, reset, tag = max(options, key=lambda option: (option[0], -option[1]))
        return str(pct), reset, tag

    gemp, gsf, gm_src = chosen("google-antigravity", {
        ("Gemini", "5h"): "5H", ("Gemini", "weekly"): "WK"})
    cxp, csf, cx_src = chosen("openai-codex", {
        ("5 hours", "5h"): "5H", ("7 days", "7d"): "7D"})
    print("|".join((cxp, gemp, csf, gsf, cx_src, gm_src)))
except Exception:
    pass
PYJSON
)
  if [ -n "$kota_yeni" ]; then
    IFS='|' read -r CXP GEMP CSF GSF CX_SRC GM_SRC <<EOF
$kota_yeni
EOF
    if { sayi_mi "$CXP" || sayi_mi "$GEMP"; } || [ ! -f "$KOTA_ONB" ]; then
      printf '%s|%s|%s|%s|%s|%s' "${CXP:-?}" "${GEMP:-?}" "${CSF:-?}" "${GSF:-?}" "${CX_SRC:--}" "${GM_SRC:--}" > "$KOTA_ONB"
    fi
  fi
fi
IFS='|' read -r CXP GEMP CSF GSF CX_SRC GM_SRC < "$KOTA_ONB" 2>/dev/null
kota_olcum_yas=$(( $(date +%s) - $(stat -c%Y "$KOTA_ONB" 2>/dev/null || date +%s) ))
calisan=$(ps -W 2>/dev/null | grep -cEi "(codex|opencode|omp)\.exe" || echo 0)   # PENCERE KURALI: powershell.exe YASAK, her cagri conhost penceresi dogurur
oc_retry=$(grep -hEo 'retrying in [0-9]+[dhms]([ ]+[0-9]+[dhms])*' "$A"/*opencode*.log 2>/dev/null | tail -1 | sed 's/^retrying in //; s/ //g')
oc_file="$HOME/.claude/.opencode_yenilenme"
if [ -n "$oc_retry" ]; then
    oc_yen="dolu, yen. $(yen_saati "$oc_retry")"
    oc_p=100; oc_disp="100"
elif [ -f "$oc_file" ]; then
    oc_target=$(tr -dc '0-9' < "$oc_file")
    oc_now=$(date +%s)
    if [ -n "$oc_target" ] && [ "$oc_target" -gt "$oc_now" ]; then
        oc_diff=$((oc_target - oc_now))
        oc_yen="dolu, yen. $(yen_saati "$oc_diff")"
        oc_p=100; oc_disp="100"
    else
        rm -f "$oc_file"
        oc_yen="acik"
        oc_p=0; oc_disp="?"
    fi
elif [ "${oc_son_hata:-0}" -gt "${oc_son_basari:-0}" ] && [ "$(( $(date +%s) - oc_son_hata ))" -lt 18000 ]; then
    oc_yen="dolu, son hata $(date -d "@$oc_son_hata" +%H:%M 2>/dev/null)"
    oc_p=100; oc_disp="100"
else
    # 20 Eyl 2026 DUZELTME: burasi "dolu"/100 yaziyordu. Bu dal, opencode'un dolu
    # olduguna dair HICBIR kanit olmadigi durumdur (ne 'retrying in' logu ne de
    # .opencode_yenilenme dosyasi var). Kanit yoklugu "dolu" demek DEGILDIR; bar
    # kalici olarak "100% | 0 | dolu" gosteriyor ve opencode'a hic is verilmiyordu.
    # Dogru varsayilan: acik.
    oc_yen="acik"
    oc_p=0; oc_disp="?"
fi

if [ "$oc_p" -eq 100 ]; then
    oc_disp="100%"
elif sayi_mi "${oc_5s:-?}" && sayi_mi "${oc_limit:-0}" && [ "$oc_limit" -gt 0 ]; then
    oc_p=$(( (oc_5s * 100 + oc_limit / 2) / oc_limit ))
    [ "$oc_p" -gt 99 ] && oc_p=99
    oc_disp="~$oc_p%"
else
    oc_p=0; oc_disp="?%"
fi

# KOTAYA GORE SIRALA: en cok kotasi KALAN basta (ona is ver).
# opencode kotasi dolu -> 100 sayilir. Bilinmeyen -> 50 (ortada).
# 5 kolona sigsin: 10M ve ustu "18.2M" (6 karakterlik "18244K" hizayi bozuyordu)
say() {
  if [ "$1" -ge 10000000 ]; then echo "$(( $1 / 1000000 )).$(( $1 % 1000000 / 100000 ))M"
  elif [ "$1" -ge 1000 ]; then echo "$(( $1 / 1000 ))K"
  else echo "$1"; fi
}
# EKRAN YUZDESI: olcum yoksa "?" gosterilir (bar tamamen bos, "  ?%"). EKRANA 50 YAZILMAZ.
# SIRALAMA icin ayri sayi anahtari kullanilir: bilinmeyen -> 50 (ortada).
gm_disp="${GEMP:-?}"; gm_sort=50; sayi_mi "$GEMP" && { gm_disp="$GEMP"; gm_sort="$GEMP"; }
cx_disp="${CXP:-?}";  cx_sort=50; sayi_mi "$CXP"  && { cx_disp="$CXP";  cx_sort="$CXP"; }
# oc_disp / oc_p yukarida opencode blogunda belirleniyor (kanit yoksa "?" gorunur)


# ================= YENI TASARIM (20 Eyl 2026) =================
# Her ajan KENDI dil modelinin marka renginde (ANSI 256):
#   GEMINI   -> Google mavi/mor   (38;5;69)
#   CODEX    -> OpenAI yesili     (38;5;41)
#   OPENCODE -> OpenCode amber    (38;5;179)
#   CLAUDE   -> Anthropic turuncu (38;5;209)
# PENCERE KURALI: .exe cagrisi YOK, sadece bash builtin + printf + sort + awk.

bar_goster() {
    # EKRAN BAR: sayi ise gercek pct, sayi degilse ("?") bar tamamen bos kalir
    case "$1" in ''|*[!0-9]*) printf '%s' "$(bar 0)";; *) printf '%s' "$(bar "$1")";; esac
}

# kotaya gore ARTAN sirala (az kullanilan ustte = ona is ver), sonra sira onekini at
cikti_satirlari=$(
    printf "%03d|$_fmt\n" "$gm_sort" "38;5;69"  "GEMINI"   "$(bar_goster "$gm_disp")" "$gm_disp" "38;5;69"  "$(say "$gm")" "$(yen_saati "${GSF:-?}" "$kota_olcum_yas")"
    printf "%03d|$_fmt\n" "$cx_sort" "38;5;41"  "CODEX"    "$(bar_goster "$cx_disp")" "$cx_disp" "38;5;41"  "$(say "$cx")" "$(yen_saati "${CSF:-?}" "$kota_olcum_yas")"
    printf '%03d|\033[%sm%-8s %s\033[0m \033[2;37m%4s │ \033[%sm%5s\033[0m\033[2;37m │ ↻ %s\033[0m\n' "$oc_p" "38;5;179" "OPENCODE" "$(bar "$oc_p")" "$oc_disp" "38;5;179" "$(say "$oc")" "$oc_yen"
)
# kotaya gore ARTAN sirala (az kullanilan ustte = ona is ver), sonra sira onekini at
cikti_satirlari=$(printf '%s\n' "$cikti_satirlari" | sort -n | cut -d'|' -f2-)
# Onbellege YALNIZ ajan satirlari yazilir; CLAUDE satiri her cagri taze uretilir ve once basilir.
printf '%b\n' "$cikti_satirlari" > "$ONBELLEK"
{
    claude_satiri
    printf '%b\n' "$cikti_satirlari"
}
