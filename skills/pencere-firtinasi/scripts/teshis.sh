#!/bin/bash
# Pencere/surec firtinasi teshis betigi.
# PENCERE KURALI: .exe cagrisi YOK — sadece `ps -W` (MSYS yerlesigi) kullanilir.
# Kullanim: bash ~/.claude/skills/pencere-firtinasi/scripts/teshis.sh

PS=$(ps -W 2>/dev/null)

say() { printf '%s' "$PS" | grep -ci "$1"; }
b=$(say 'bash\.exe'); c=$(say 'conhost\.exe'); h=$(say 'cygwin-console-helper')

durum() { # $1=deger $2=alarm-esigi
  if   [ "$1" -gt "$2" ]; then printf 'ALARM'
  elif [ "$1" -gt $(( $2 / 2 )) ]; then printf 'dikkat'
  else printf 'iyi'; fi
}

echo "=== SUREC SAYILARI ==="
printf 'bash.exe                  : %4d   [%s]  (alarm > 40)\n' "$b" "$(durum "$b" 40)"
printf 'conhost.exe               : %4d   [%s]  (alarm > 80)\n' "$c" "$(durum "$c" 80)"
printf 'cygwin-console-helper.exe : %4d   [%s]  (alarm > 20)\n' "$h" "$(durum "$h" 20)"

echo
echo "=== EN COK TEKRAR EDEN KONSOL SURECI (suclu burada) ==="
# ps -W sutunlari: PID PPID PGID WINPID TTY UID STIME COMMAND -> ilk 7'yi at.
# Windows servis gurultusunu (svchost/edge/nvidia) ele: bizi konsol surecleri ilgilendiriyor.
printf '%s' "$PS" \
  | awk 'NR>1{ $1=$2=$3=$4=$5=$6=$7=""; sub(/^ +/,""); if($0!="") print }' \
  | grep -Ei 'bash|conhost|cygwin|cmd\.exe|node|python|codex|opencode|omp' \
  | sort | uniq -c | sort -rn | head -6
echo "  (sol sutun: adet. bash/conhost yuksekse durum cubugu betiklerine bak.)"

echo
echo "=== BASLAMA SAATLERI: kaynak hala uretiyor mu? ==="
echo "(Cogu SON dakikalarda ise kaynak calisiyor -> duzelt."
echo " Cogu ESKI ve yenisi yoksa takili artik -> SKILL.md adim 4 ile temizle.)"
printf '%s' "$PS" | grep -i 'bash\.exe' | awk '{print $7}' | sort | uniq -c | sort -rn | head -6
echo "  (sol sutun: adet, sag sutun: baslama saati)"

echo
echo "=== DURUM CUBUGU BETIK SURESI (asil olcum) ==="
SAHTE_JSON='{"session_id":"teshis","cwd":"'"$HOME"'","model":{"display_name":"Opus"},"cost":{"total_cost_usd":0,"total_duration_ms":0}}'
for betik in "$HOME/.claude/ajan_token.sh" "$HOME/.claude/statusline-command.sh"; do
  [ -f "$betik" ] || continue
  rm -f "$HOME/.claude/.ajan_token.cache"
  bas=$(date +%s%N)
  # statusline-command.sh oturum JSON'unu STDIN'den okur. Bos stdin ile sonsuza
  # kadar bloklar ve SAHTE alarm verir -> asgari gecerli JSON besle.
  ( printf '%s' "$SAHTE_JSON" | CLAUDE_COST=0 CLAUDE_TOKENS=0 CLAUDE_PCT=0 CLAUDE_RESET=0       timeout 60 bash "$betik" >/dev/null 2>&1 )
  son=$(date +%s%N)
  ms=$(( (son - bas) / 1000000 ))
  if [ "$ms" -gt 10000 ]; then d="ALARM"; elif [ "$ms" -gt 3000 ]; then d="dikkat"; else d="iyi"; fi
  printf '%-34s : %5d ms  [%s]  (alarm > 10000)\n' "$(basename "$betik")" "$ms" "$d"
done

echo
echo "=== KILIT DURUMU ==="
for kilit in "$HOME/.claude/.ajan_token.lock"; do
  if [ -d "$kilit" ]; then
    yas=$(( $(date +%s) - $(stat -c%Y "$kilit" 2>/dev/null || echo 0) ))
    printf '%s : VAR, %d sn yasinda' "$(basename "$kilit")" "$yas"
    [ "$yas" -gt 180 ] && printf '  <- BAYAT, sonraki kosu devralacak'
    echo
  else
    printf '%s : yok (bos - normal)\n' "$(basename "$kilit")"
  fi
done

echo
echo "Sonraki adim: ~/.claude/skills/pencere-firtinasi/SKILL.md"
