#!/usr/bin/env bash
# AjanCRM StatusLine — bağlam kota çubuğu + harcanan dolar
# jq yerine Python kullanır (jq bu sistemde kurulu değil)

input=$(cat)
# Son girdiyi sakla: alanlar (model, effort) kanitla dogrulansin diye
printf "%s" "$input" > "$HOME/.claude/.statusline_son_girdi.json" 2>/dev/null

# Tüm alanları tek Python çağrısıyla çek (tab ile ayrılmış)
# Her alan ayrı satırda — boş alanlar korunur (ardışık tab yutma sorunu yok)
parsed=$(printf '%s' "$input" | python -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    d = {}
cw = d.get("context_window", {}) or {}
cost = d.get("cost", {}) or {}
rl = d.get("rate_limits", {}) or {}
five = (rl.get("five_hour") or {})
seven = (rl.get("seven_day") or {})
model = (d.get("model") or {}).get("display_name", "Claude")

# Effort: once stdin JSON, yoksa settings.json varsayilani
effort = d.get("effort") or (d.get("output_config") or {}).get("effort") or ""
if not effort:
    try:
        import os
        sp = os.path.expanduser("~/.claude/settings.json")
        with open(sp, encoding="utf-8") as f:
            effort = json.load(f).get("effortLevel", "")
    except Exception:
        effort = ""
# dict gelirse (level=low sozlugu gibi) sadece seviye metnini al
if isinstance(effort, dict):
    effort = effort.get("level") or effort.get("effort") or ""
effort = str(effort)

# fast_mode: bool -> on/off, yoksa bos
fm = d.get("fast_mode")
fm = "on" if fm is True else ("off" if fm is False else "")

def bstr(v):
    if isinstance(v, bool):
        return "on" if v else "off"
    if isinstance(v, (int, float)):
        return "on" if v else "off"
    if isinstance(v, str):
        s = v.lower()
        if s in ("on", "enabled", "true", "compact", "auto", "high"):
            return "on"
        if s in ("off", "disabled", "false", "none"):
            return "off"
    return ""

# thinking: bool ise on/off; dict ise type/enabled degerinden uret, yoksa bos
th = d.get("thinking")
if isinstance(th, dict):
    tv = th.get("enabled")
    if tv is None:
        tv = th.get("type", "")
    tm = bstr(tv)
elif isinstance(th, bool):
    tm = "on" if th else "off"
else:
    tm = ""

def num(v):
    return "" if v is None else v

def yerel_saat(ts):
    # resets_at: ISO string veya epoch -> yerel "HH:MM" (7g icin "GunAd HH:MM")
    if not ts:
        return ""
    from datetime import datetime
    try:
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts)
        else:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone()
        gunler = ["Pzt", "Sal", "Car", "Per", "Cum", "Cmt", "Paz"]
        saat = dt.strftime("%H:%M")
        if (dt.date() - datetime.now().astimezone().date()).days > 0:
            return gunler[dt.weekday()] + " " + saat
        return saat
    except Exception:
        return ""

nobet = ""
try:
    import os, socket
    depo = os.environ.get("AFUNOBET_DIR") or os.path.join(os.path.expanduser("~"), "Desktop", "afuproject", "AfuNobet")
    if os.path.isdir(depo):
        sys.path.insert(0, depo)
        from afu.supervisor.router import get_best_provider
        from afunobet import nobet_satiri
        router = get_best_provider()
        from afu.supervisor.state import get_db
        conn = get_db()
        try:
            job = conn.execute("SELECT job_id, provider FROM jobs WHERE status NOT IN (?, ?) ORDER BY updated_at DESC LIMIT 1", ("done", "COMPLETED")).fetchone()
        finally:
            conn.close()
        satir = nobet_satiri(job["provider"] if job else router)
        parcalar = str(satir).split(None, 1)
        if len(parcalar) > 1:
            nobet = parcalar[1].replace("\r", " ").replace("\n", " ").strip()
        if job and nobet:
            nobet += " \u2502 job " + str(job["job_id"])
        try:
            with socket.create_connection(("127.0.0.1", 50505), timeout=0.15):
                pass
        except Exception:
            if nobet:
                nobet += " \u2502 supervisor kapali"
except Exception:
    nobet = ""

ajanlar = ""
kabuk_sayisi = 0
try:
    import os, sqlite3
    from pathlib import Path
    depo = os.environ.get("AFUNOBET_DIR") or os.path.join(os.path.expanduser("~"), "Desktop", "afuproject", "AfuNobet")
    db_path = os.path.join(depo, "state.db")
    conn = sqlite3.connect("file:" + db_path.replace("\\", "/") + "?mode=ro", uri=True, timeout=0.2)
    shell_rows = conn.execute("SELECT pid FROM shells WHERE status = ?", ("RUNNING",)).fetchall()
    conn.close()
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        kernel32.WaitForSingleObject.restype = ctypes.c_uint32
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.restype = ctypes.c_int
        for (pid,) in shell_rows:
            handle = kernel32.OpenProcess(0x00100000 | 0x1000, 0, int(pid))
            if handle:
                try:
                    if kernel32.WaitForSingleObject(handle, 0) == 0x102:
                        kabuk_sayisi += 1
                finally:
                    kernel32.CloseHandle(handle)
    else:
        for (pid,) in shell_rows:
            try:
                os.kill(int(pid), 0)
                kabuk_sayisi += 1
            except PermissionError:
                kabuk_sayisi += 1
            except (ProcessLookupError, ValueError, TypeError):
                pass
except Exception:
    pass
try:
    import glob, time
    ajan_dir = os.path.join(os.path.expanduser("~"), ".claude", "afu-ajanlar")
    calisan_ajan_names = []
    biten_ajan_names = []
    seen_calisan_names = set()
    seen_biten_names = set()
    ajan_tokens = []
    ajan_sayisi = 0
    biten_sayisi = 0
    sorunlu_sayisi = 0
    now = time.time()
    for ajan_file in glob.glob(os.path.join(ajan_dir, "*.json")):
        try:
            with open(ajan_file, encoding="utf-8") as handle:
                ajan_data = json.load(handle)
            durum = ajan_data.get("durum")
            bitti = ajan_data.get("bitti")
            if durum == "CALISIYOR" and bitti is None:
                updated = ajan_data.get("guncellendi")
                if not isinstance(updated, (int, float)) or now - updated > 15:
                    continue
                ajan_sayisi += 1
                ajan_grubu = "calisan"
            elif isinstance(bitti, (int, float)) and not isinstance(bitti, bool) and now - bitti <= 300:
                biten_sayisi += 1
                ajan_grubu = "biten"
                if durum in ("KOTA", "HATA", "ZAMAN_ASIMI"):
                    sorunlu_sayisi += 1
            else:
                continue
            ajan_name = ajan_data.get("ajan")
            if ajan_name is not None:
                ajan_name = str(ajan_name)
                if ajan_grubu == "calisan" and ajan_name not in seen_calisan_names:
                    seen_calisan_names.add(ajan_name)
                    calisan_ajan_names.append(ajan_name)
                elif ajan_grubu == "biten" and ajan_name not in seen_biten_names:
                    seen_biten_names.add(ajan_name)
                    biten_ajan_names.append(ajan_name)
            token = ajan_data.get("token")
            if isinstance(token, int) and not isinstance(token, bool):
                ajan_tokens.append(token)
        except Exception:
            continue
    if ajan_sayisi or biten_sayisi:
        if ajan_tokens:
            total_tokens = sum(ajan_tokens)
            if total_tokens < 1000:
                token_text = str(total_tokens)
            elif total_tokens < 1000000:
                token_text = "%.1fk" % (total_tokens / 1000.0)
            else:
                token_text = "%.1fM" % (total_tokens / 1000000.0)
            token_part = "\u2193 " + token_text
        else:
            token_part = "\u2193 ?"
        durum_part = str(ajan_sayisi) + " calisiyor"
        if biten_sayisi:
            biten_part = str(biten_sayisi) + " bitti"
            if sorunlu_sayisi:
                biten_part += " (" + str(sorunlu_sayisi) + " sorunlu)"
            durum_part += " \u00b7 " + biten_part
        ajanlar = durum_part
        ajan_names = list(calisan_ajan_names)
        seen_ajan_names = set(ajan_names)
        for ajan_name in biten_ajan_names:
            if ajan_name not in seen_ajan_names:
                seen_ajan_names.add(ajan_name)
                ajan_names.append(ajan_name)
        if ajan_names:
            ajanlar += " \u00b7 " + ", ".join(ajan_names)
        ajanlar += " \u00b7 " + token_part
except Exception:
    ajanlar = ""

if kabuk_sayisi > 0:
    if not ajanlar:
        ajanlar = "0 calisiyor"
    ajanlar += " · " + str(kabuk_sayisi) + " kabuk"

fields = [
    num(cw.get("used_percentage")),
    num(cw.get("remaining_percentage")),
    num(cost.get("total_cost_usd")),
    num(five.get("used_percentage")),
    num(seven.get("used_percentage")),
    model,
    effort,
    yerel_saat(five.get("resets_at")),
    yerel_saat(seven.get("resets_at")),
    # Claude kendi token harcamasi (giris + cikis) — alt satirdaki claude rozeti icin
    num((cw.get("total_input_tokens") or 0) + (cw.get("total_output_tokens") or 0)),
    num(fm),
    num(tm),
    nobet,
    ajanlar,
]
# Token basi maliyet: bu oturumda GERCEKLESEN $ / 1M token (liste fiyati degil).
# MODEL satirinda yuzde kolonuna (4 kolon) sigacak kisa bicim.
def m_kisa(x):
    if x < 10:
        return "$%.1f" % x
    if x < 1000:
        return "$%.0f" % x
    return "$%.0fK" % (x / 1000)
try:
    _tok = (cw.get("total_input_tokens") or 0) + (cw.get("total_output_tokens") or 0)
    _usd = float(cost.get("total_cost_usd") or 0)
    fields.append(m_kisa(_usd * 1e6 / _tok) if _tok > 0 else "")
except Exception:
    fields.append("")
# Windows CRLF tuzagi: \r ile bas degil, salt \n ile bayt yaz
sys.stdout.buffer.write(("\n".join(str(x) for x in fields)).encode("utf-8"))
')

# Satır satır oku (mapfile ile, boş satırlar dahil)
mapfile -t _f <<< "$parsed"
used_pct="${_f[0]}"
remaining_pct="${_f[1]}"
cost_usd="${_f[2]}"
five_pct="${_f[3]}"
week_pct="${_f[4]}"
model="${_f[5]}"
effort="${_f[6]}"
five_reset="${_f[7]}"
week_reset="${_f[8]}"
claude_tokens="${_f[9]}"
fast_mode="${_f[10]}"
thinking="${_f[11]}"
nobet="${_f[12]}"
ajanlar="${_f[13]}"
model_mtok="${_f[14]}"

# --- İlerleme çubuğu ---
progress_bar() {
  local pct="${1:-0}"
  local width=20
  local filled
  filled=$(awk -v p="$pct" -v w="$width" 'BEGIN{n=int(p*w/100); if(n>w)n=w; if(n<0)n=0; print n}')
  local empty=$((width - filled))
  local bar="" i
  for ((i=0; i<filled; i++)); do bar="${bar}█"; done
  for ((i=0; i<empty; i++)); do bar="${bar}░"; done
  printf '%s' "$bar"
}

reset="\033[0m"

# --- Bağlam çubuğu ---
if [ -n "$used_pct" ]; then
  bar=$(progress_bar "$used_pct")
  used_int=$(awk -v p="$used_pct" 'BEGIN{printf "%.0f", p}')
  rem_int=$(awk -v p="${remaining_pct:-0}" 'BEGIN{printf "%.0f", p}')

  if [ "$used_int" -ge 80 ]; then
    color="\033[1;31m"   # kırmızı
  elif [ "$used_int" -ge 60 ]; then
    color="\033[1;33m"   # sarı
  else
    color="\033[1;32m"   # yeşil
  fi
  ctx_line=$(printf "%bBaglam [%s] %d%% kullanildi - %d%% kaldi%b" "$color" "$bar" "$used_int" "$rem_int" "$reset")
else
  ctx_line=""
fi

# --- 5 saatlik kota çubuğu ---
rate_line=""
if [ -n "$five_pct" ]; then
  five_int=$(awk -v p="$five_pct" 'BEGIN{printf "%.0f", p}')
  rate_bar=$(progress_bar "$five_pct")
  if [ "$five_int" -ge 80 ]; then
    rcolor="\033[1;31m"
  elif [ "$five_int" -ge 60 ]; then
    rcolor="\033[1;33m"
  else
    rcolor="\033[1;36m"
  fi
  rate_line=$(printf "%b5s-kota [%s] %d%%%b" "$rcolor" "$rate_bar" "$five_int" "$reset")
  if [ -n "$five_reset" ]; then
    rate_line="${rate_line}$(printf " %b(yenilenme %s)%b" "\033[2;37m" "$five_reset" "\033[0m")"
  fi
fi

# --- 7 günlük kota ---
if [ -n "$week_pct" ]; then
  week_int=$(awk -v p="$week_pct" 'BEGIN{printf "%.0f", p}')
  rate_line="${rate_line}$(printf " %b| 7g-kota %d%%%b" "\033[1;35m" "$week_int" "\033[0m")"
  if [ -n "$week_reset" ]; then
    rate_line="${rate_line}$(printf " %b(yenilenme %s)%b" "\033[2;37m" "$week_reset" "\033[0m")"
  fi
fi

# --- Effort seviyesi (2. satira eklenir, sadece "Effort: <seviye>") ---
if [ -n "$effort" ]; then
  case "$effort" in
    low)    ecolor="\033[1;32m" ;;
    medium) ecolor="\033[1;36m" ;;
    high)   ecolor="\033[1;33m" ;;
    xhigh|max) ecolor="\033[1;31m" ;;
    *)      ecolor="\033[2;37m" ;;
  esac
  rate_line="${rate_line}$(printf " %b| Effort: %s%b" "$ecolor" "$effort" "\033[0m")"
fi

# --- Dolar (gerçek total_cost_usd) ---
if [ -n "$cost_usd" ]; then
  cost_fmt=$(awk -v c="$cost_usd" 'BEGIN{printf "%.4f", c}')
else
  cost_fmt="0.0000"
fi
dollar_line=$(printf " %b| \$%s harcandi%b" "\033[1;33m" "$cost_fmt" "\033[0m")

# --- MODEL + NOBET satirlari: ajan satirlariyla AYNI kolonlar (23 Eyl 2026) ---
# Ajan satiri: ad(8) + bosluk + bar(10) + bosluk + yuzde(4) = 24 kolon, sonra " │ " + token(5) + " │ ".
# Burada: ad(8) + bosluk + model(10, bar yerine) + bosluk + $/1M token(4, yuzde yerine)
#         + " │ " + effort(5, saga yasli) + " │ " + kalan.
# $/1M: MODEL = bu oturumda gerceklesen (maliyet / token); NOBET = $0 (abonelik, token basi ucret yok).
# Boylece iki │ cizgisi alttaki satirlarla ayni kolona duser. medium 6 harf -> "med".
# Model adi renkleri cubukta BASKA HICBIR YERDE kullanilmayan tonlar:
#   MODEL (Claude modeli) -> mor 141, NOBET modeli -> parlak beyaz 255.
effort_kisa() { case "$1" in medium) printf 'med';; *) printf '%s' "${1:0:5}";; esac; }
effort_renk() {
  case "$1" in
    low)    printf '\033[1;32m' ;;
    medium) printf '\033[1;36m' ;;
    high)   printf '\033[1;33m' ;;
    xhigh|max) printf '\033[1;31m' ;;
    *)      printf '\033[2;37m' ;;
  esac
}
hizali_satir() {
  # $1 ad rengi, $2 ad, $3 model, $4 effort, $5 kalan metin, $6 model rengi, $7 $/1M token
  printf '%b%-8s\033[0m %b%-10s\033[0m \033[2;37m%4s │ \033[0m%b%5s\033[0m\033[2;37m │ %s\033[0m' \
    "$1" "$2" "$6" "${3:0:10}" "${7:0:4}" "$(effort_renk "$4")" "$(effort_kisa "$4")" "$5"
}

mdl_kalan=""
[ -n "$fast_mode" ] && mdl_kalan="fast $fast_mode"
[ -n "$thinking" ] && mdl_kalan="${mdl_kalan:+$mdl_kalan · }thinking $thinking"
printf '%b\n' "$(hizali_satir '\033[38;5;209m' "MODEL" "${model:-Claude}" "$effort" "$mdl_kalan" '\033[1;38;5;141m' "$model_mtok")"

if [ -n "$nobet" ]; then
  # nobet: "CODEX → gpt-6-luna │ effort medium │ fast on[ │ job X][ │ supervisor kapali]"
  nobet_bas="${nobet%% │ *}"
  nobet_provider="${nobet_bas%% *}"
  nobet_model="${nobet_bas##* }"
  [ "${#nobet_model}" -gt 10 ] && nobet_model="${nobet_model%%:*}"   # 10 kolona sigmazsa :high gibi eki at
  nobet_geri="${nobet#"$nobet_bas"}"; nobet_geri="${nobet_geri# │ }"
  nobet_effort=""
  case "$nobet_geri" in
    "effort "*) nobet_effort="${nobet_geri%% │ *}"; nobet_effort="${nobet_effort#effort }"
                nobet_geri="${nobet_geri#"effort $nobet_effort"}"; nobet_geri="${nobet_geri# │ }" ;;
  esac
  nobet_kalan="$nobet_provider${nobet_geri:+ · ${nobet_geri// │ / · }}"
  case "$nobet_provider" in
    CODEX)    ncolor="\033[38;5;41m" ;;
    GEMINI)   ncolor="\033[38;5;69m" ;;
    OPENCODE) ncolor="\033[38;5;179m" ;;
    CLAUDE)   ncolor="\033[38;5;209m" ;;
    *)        ncolor="\033[2;37m" ;;
  esac
  printf '%b\n' "$(hizali_satir "$ncolor" "NOBET" "$nobet_model" "$nobet_effort" "$nobet_kalan" '\033[1;38;5;255m' '$0')"
fi

if [ -n "$ajanlar" ]; then
  printf '%b\n' "$(printf '%b%-8s\033[0m %b%s\033[0m' '\033[38;5;41m' 'AJANLAR' '\033[2;37m' "$ajanlar")"
fi

# 3. satir — alt ajanlarin (codex / gemini / opencode) token harcamasi
# Claude'un kendi maliyeti de ayni satirda gorunsun diye disari aktarilir
if [ -x "$HOME/.claude/ajan_token.sh" ]; then
  CLAUDE_COST="$cost_usd" CLAUDE_TOKENS="$claude_tokens" CLAUDE_PCT="$five_pct" CLAUDE_RESET="$five_reset" bash "$HOME/.claude/ajan_token.sh" 2>/dev/null
fi


# --- Ozet satiri (20 Eyl 2026 tasarimi): Baglam + 5H + 7D tek satirda ---
# Renk: Claude'a ait bilgi -> Anthropic turuncusu (38;5;209)
bar5() {
    # MSYS bash'te ${s:0:n} BAYT keser -> UTF-8 bloklari donguyle kur.
    local p=$1 d i o=""
    d=$(( (p + 5) / 10 ))
    (( d < 0 )) && d=0
    (( d > 10 )) && d=10
    for ((i=0; i<d; i++)); do o="$o█"; done
    for ((i=d; i<10; i++)); do o="$o░"; done
    printf '%s' "$o"
}

cost_kisa=$(awk -v c="${cost_usd:-0}" 'BEGIN{printf "%.2f", c}')
# Hizalama: $ sabit solda, sayi 5 kolona saga yasli, alan 8 kolon -> "│ $ 2.14  │ 5H"
cost_alan=$(printf '%-7s' "\$$(printf '%5s' "$cost_kisa")")

# Ajan satirlariyla AYNI kolon duzeni:
#   %-9s ad  |  bar(10 kolon) %3d%%  |  %5s  |  son alan
# "Bağlam" 6 gorunur karakter / 7 bayt -> %-9s bayt dolgusu 8 gorunur kolon verir.
ozet=$(printf '\033[38;5;77m%-9s %s\033[0m \033[2;37m%3d%% │ \033[38;5;77m%5s\033[0m\033[2;37m │ %s\033[0m' \
    "Bağlam" "$(bar5 "${used_int:-0}")" "${used_int:-0}" "${rem_int:-0}%" "$cost_alan")

# --- 5H (sari) + 7D (pembe) mini cubuklar, ayni satirda ---
barN() {
    local p=$1 w=$2 d i o=""
    d=$(( (p * w + 50) / 100 ))
    (( d < 0 )) && d=0
    (( d > w )) && d=$w
    for ((i=0; i<d; i++)); do o="$o█"; done
    for ((i=d; i<w; i++)); do o="$o░"; done
    printf '%s' "$o"
}
f_int=$(awk -v p="${five_pct:-0}" 'BEGIN{printf "%.0f", (p=="")?0:p}')
w_int=$(awk -v p="${week_pct:-0}" 'BEGIN{printf "%.0f", (p=="")?0:p}')
ozet="${ozet}$(printf '\033[2;37m │ \033[1;38;5;220m5H\033[0m \033[38;5;220m%s\033[0m \033[2;37m%3d%% ↻ %s\033[0m' \
    "$(barN "$f_int" 5)" "$f_int" "${five_reset:-?}")"
ozet="${ozet}$(printf '\033[2;37m │ \033[1;38;5;212m7D\033[0m \033[38;5;212m%s\033[0m \033[2;37m%3d%% ↻ %s\033[0m' \
    "$(barN "$w_int" 5)" "$w_int" "${week_reset:-?}")"

printf '%b\n' "$ozet"
