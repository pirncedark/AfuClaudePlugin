#!/bin/bash
# Ajan panosu: her 90 sn'de tek satirlik ilerleme + bitis bildirimi.
A="${TEMP:-/tmp}/ajan-kopru"
LOGS="codex_review_codex_165915.log:DENETIM-3+4
codex_maestro_codex_170326.log:DENETIM-maestro
codex_statusline_codex_170629.log:ALTBAR
gemini_dilim5_gemini_165918.log:DILIM5-gemini"
declare -A bitti
tur=0
while :; do
  tur=$((tur+1))
  kalan=0; rapor=""
  while IFS=: read -r dosya ad; do
    [ -z "$dosya" ] && continue
    f="$A/$dosya"
    [ -f "$f" ] || { rapor="$rapor  $ad:log-yok"; continue; }
    boy=$(stat -c%s "$f" 2>/dev/null || echo 0)
    yas=$(( $(date +%s) - $(stat -c%Y "$f" 2>/dev/null || date +%s) ))
    if [ "$yas" -gt 120 ] && [ "$boy" -gt 0 ] && [ -z "${bitti[$ad]}" ]; then
      bitti[$ad]=1
      echo "BITTI -> $ad  (${boy} bayt, 2 dk sessiz)  log: $dosya"
    fi
    [ -z "${bitti[$ad]}" ] && kalan=$((kalan+1))
    durum="calisiyor"; [ -n "${bitti[$ad]}" ] && durum="BITTI"
    rapor="$rapor  $ad=${boy}b/${yas}s:$durum"
  done <<< "$LOGS"
  echo "[tur $tur] $rapor"
  [ "$kalan" -eq 0 ] && { echo "TUM AJANLAR BITTI"; break; }
  sleep 1200
done
