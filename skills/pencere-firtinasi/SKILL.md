---
name: pencere-firtinasi
description: Windows'ta boş siyah terminal/konsol pencereleri birikip PC'yi kilitlediğinde teşhis + kalıcı düzeltme. "pencereler açılıyor", "boş terminal birikiyor", "conhost patladı", "PC çöküyor", "supagent gelince donuyor", "opencode iş verince kilitleniyor", "süreç fırtınası", "durum çubuğu doğru mu", "çubuk yanlış gösteriyor", "yenilenme saati kaymış" deyince tetikle. ÖNCE ölç, sonra düzelt — pencereyi doğuran şey genelde alt-ajan DEĞİL, durum çubuğudur.
allowed-tools: Bash, PowerShell, Read, Edit, Write, Glob, Grep
---

# Pencere / süreç fırtınası — teşhis ve düzeltme

## Altın kural

**Suçluyu tahmin etme, ölç.** Bu arıza üç kez yaşandı ve HER SEFERİNDE ilk şüpheli
(alt-ajanlar, codex, opencode, MCP) yanlış çıktı. Gerçek kaynak iki kez **durum çubuğuydu**.
Alt-ajanlar sadece *tetikleyici*: bıraktıkları log dosyaları durum çubuğu betiğini
yavaşlatıyor, yavaşlayan betik üst üste biniyor.

Windows'ta her konsol süreci bir `conhost.exe` (= ekranda boş siyah pencere) doğurur.
Git Bash'ten çalışan her komut ayrıca bir `cygwin-console-helper.exe` doğurur.
Durum çubuğu saniyeler içinde defalarca çalıştığı için **oradaki her fazladan süreç
katlanarak birikir**.

## 1. Ölç (her zaman ilk adım)

```bash
bash ~/.claude/skills/pencere-firtinasi/scripts/teshis.sh
```

Betik şunları basar: süreç sayıları, en çok süreç doğuran komut satırı, yaş dağılımı ve
durum çubuğu betiklerinin gerçek süresi.

Eşikler:

| Ölçüm | Sağlıklı | Alarm |
|---|---|---|
| `bash.exe` | < 15 | > 40 |
| `conhost.exe` | < 30 | > 80 |
| `cygwin-console-helper.exe` | < 5 | > 20 |
| `ajan_token.sh` süresi | < 3 sn | > 10 sn |

## 2. Kaynağı bul

**Yaş dağılımına bak — bu tek başına davayı çözer:**

- Süreçlerin çoğu **yeni** (< 60 sn) ve sayı artıyor → kaynak HÂLÂ üretiyor, komut satırına bak.
- Süreçlerin çoğu **eski** (> 100 sn) ve yeni doğan yok → kaynak durmuş, bunlar **takılı artık**.
  Düzeltme değil temizlik gerekir (bkz. adım 4).

**Komut satırı gruplamasına bak:** `teshis.sh` en çok tekrar eden konsol sürecini verir.
Ama `ps -W` yalnızca **çalıştırılabilir yolunu** basar, argümanları basmaz — `bash.exe` yüksekse
hangi *betiğin* suçlu olduğunu görmek için tam komut satırı lazım:

```powershell
Get-CimInstance Win32_Process -Filter "Name='bash.exe'" |
  ForEach-Object { $_.CommandLine.Substring(0,[Math]::Min(60,$_.CommandLine.Length)) } |
  Group-Object | Sort-Object Count -Descending | Select-Object Count,Name -First 5
```

Neredeyse her zaman `ajan_token.sh` veya `statusline-command.sh` çıkar.
(Bu PowerShell çağrısı bir conhost doğurur — teşhis için kabul, döngüye sokma.)

## 3. Düzelt — iki kalıp

Durum çubuğundan çağrılan her betik bu iki kurala uymak ZORUNDA.

### Kalıp A — dosya başına süreç doğuran döngü YASAK

```bash
# YANLIS: 148 log × 5 süreç = 740 pencere, 47 saniye
for f in "$A"/*.log; do
  t=$(sed 's/\x1b\[[0-9;]*m//g' "$f" | grep -A1 "^tokens used" | tail -1 | tr -d ' .')
done

# DOGRU: glob başına TEK awk = 1 süreç, 1 saniye
awk "$TARA_AWK" "$A"/*.log 2>/dev/null
```

Çalışan `TARA_AWK` örneği `~/.claude/ajan_token.sh` içinde — dosya başına son
`"totalTokens":N` ve `tokens used` değerini tek geçişte çıkarır. Yeni bir tarayıcı
yazman gerekirse oradan kopyala.

### Kalıp B — tek-örnek kilidi (önbellek TEK BAŞINA YETMEZ)

Bu en kritik ders. Betikte 30 sn önbellek VARDI ve yine de çöktü: önbellek betiğin
**en sonunda** yazılıyordu, betik 47 sn sürüyordu, dolayısıyla hiçbir koşu bitmeden
yenisi başlıyor ve önbellek asla devreye girmiyordu.

```bash
ONBELLEK="$HOME/.claude/.X.cache"
KILIT="$HOME/.claude/.X.lock"
if ! mkdir "$KILIT" 2>/dev/null; then
  kilit_yas=$(( $(date +%s) - $(stat -c%Y "$KILIT" 2>/dev/null || echo 0) ))
  if [ "$kilit_yas" -lt 180 ]; then
    [ -f "$ONBELLEK" ] && cat "$ONBELLEK"     # eski veriyi bas, yığılma
    exit 0
  fi
  rm -rf "$KILIT" 2>/dev/null                  # bayat kilidi devral
  mkdir "$KILIT" 2>/dev/null || { [ -f "$ONBELLEK" ] && cat "$ONBELLEK"; exit 0; }
fi
trap 'rm -rf "$KILIT" 2>/dev/null' EXIT
```

`trap ... EXIT` şart — yoksa betik çöktüğünde kilit kalır ve çubuk 180 sn donar.

### Kalıp C — `.exe` çağrısı YASAK

`powershell.exe`, `tasklist`, `wmic`, `cmd.exe` → her çağrı bir conhost. Windows süreç
bilgisi lazımsa `ps -W` kullan (MSYS yerleşiği, pencere açmaz, ~0.15 sn).

## 4. Birikmiş artıkları temizle

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "~\.claude\skills\afu-ai\scripts\conhost_temizle.ps1"
```

**Bu betiğin kör noktası:** yalnızca **ebeveyni ölmüş** süreçleri öldürür. Ebeveyni
(Claude Code) hâlâ canlı olan takılı `bash.exe`'lere dokunmaz — 20 Eyl'de sayıyı
düşürmek yerine arttırmış görünmesinin sebebi buydu. Takılı olanları elle avla:

```powershell
$stuck = Get-CimInstance Win32_Process -Filter "Name='bash.exe'" |
  Where-Object { $_.CommandLine -like '*ajan_token.sh*' -and
                 ((Get-Date)-$_.CreationDate).TotalSeconds -gt 90 }
$stuck | ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -EA Stop } catch {} }
```

90 sn eşiği önemli: sağlıklı bir koşu 3 sn sürer, 90 sn'yi geçen kesinlikle takılmıştır.
Bunlar ölünce bağımlı süreçlerin çoğu kendiliğinden çıkar.

## 5. Doğrula (atlanmaz)

```bash
time bash ~/.claude/ajan_token.sh >/dev/null    # < 3 sn olmali
rm -f ~/.claude/.ajan_token.cache
for i in 1 2 3 4 5; do bash ~/.claude/ajan_token.sh >/dev/null 2>&1 & done; time wait
# 5 esamanli kosu tek kosu kadar surmeli (kilit calisiyor demektir)
```

Sonra **45 sn bekle** ve tekrar say — sayı artmıyorsa düzeltme tuttu.
Değişiklikten önce mutlaka yedek al: `cp ~/.claude/ajan_token.sh ~/.claude/ajan_token.sh.yedek-$(date +%Y%m%d-%H%M%S)`

## Yapma

- **Durum çubuğunu KAPATMA.** Kalıcı karar: çubuk kapatılmayacak, düzeltilecek.
  Geçmişte başka oturumlar `statusline-command.sh` başına `exit 0` mührü koydu — bu
  çözüm değil, semptom gizleme. Bkz. `[[statusline-surec-firtinasi]]`.
- **Test penceresi açma.** Her iş headless/konsol içinde — yeni pencere sorunu büyütür.
  Bkz. `[[test-penceresi-siniri]]`.
- `statusline-command.sh` içindeki python bloğuna apostrof yazma — alt bar ölür.
  Bkz. `[[statusline-apostrof-tuzagi]]`.
- Suçu alt-ajanlara atıp `ajan-kopru`/`afu-ai` betiklerini kurcalama; onlarda zaten
  `subajan.py` sarmalayıcısı var. Önce ÖLÇ.

## Geçmiş vakalar

| Tarih | Belirti | Gerçek kök | Düzeltme |
|---|---|---|---|
| 19 Eyl 2026 | conhost 61 → 1691 | çıplak `codex exec`, her komut conhost | `subajan.py` sarmalayıcı + temizleyici |
| 20 Eyl 02:00 | 190 bash + 398 öksüz konsol | `ajan_token.sh` içinde `powershell.exe` | `ps -W` ile değiştirildi (Kalıp C) |
| 20 Eyl 03:35 | 99 bash / 85 conhost, "supagent gelince çöküyor" | dosya başına boru hattı: 148 log × 5 süreç, 47 sn, önbellek sonda yazılıyor | tek-örnek kilidi + tek awk (Kalıp A+B) → 3.0 sn, 6/15/0 |

Üçünün ortak dersi: **kaynak durum çubuğuydu, alt-ajanlar sadece yükü büyüttü.**

## Teşhis betiğinin kendi tuzağı

`statusline-command.sh` oturum JSON'unu **stdin'den** okur. Boş stdin ile elle çalıştırırsan
sonsuza kadar bloklar ve "90 sn ALARM" gibi **sahte** bir sonuç verirsin (20 Eyl'de tam olarak
bu oldu). `teshis.sh` bu yüzden asgari bir JSON besliyor — betiği elle ölçeceksen sen de besle:

```bash
printf '%s' '{"session_id":"t","cwd":"'"$HOME"'","model":{"display_name":"Opus"}}' \
  | timeout 60 bash ~/.claude/statusline-command.sh >/dev/null
```

Ders: bir betiğin yavaş olduğunu iddia etmeden önce **onu gerçek koşullarında** ölç.

## Kilidin kendi tuzağı — sessiz çıkış (20 Eyl 2026, ölçüldü)

Kalıp B'yi uygularken kolay bir hata var: kilit başkasındayken `cat "$ONBELLEK"; exit 0`
yazmak. **Önbellek henüz yoksa** (ilk koşu, ya da önbellek silinmişse) bu satır hiçbir şey
basmaz ve **çubuk tamamen kaybolur** — ki bu yasak (bkz. "Yapma").

Doğrusu: asla sessiz çıkma. Önbellek yoksa kilit sahibinin onu yazmasını kısa süre bekle,
o da olmazsa en azından bir yer tutucu bas:

```bash
geri_cekil() {
  if [ -f "$ONBELLEK" ]; then cat "$ONBELLEK"; exit 0; fi
  local i
  for i in 1 2 3 4 5 6 7 8 9 10; do
    sleep 0.5
    [ -f "$ONBELLEK" ] && { cat "$ONBELLEK"; exit 0; }
  done
  printf '\033[2;37m… ajan tokenleri hesaplaniyor\033[0m\n'
  exit 0
}
```

Test: `rm -f önbellek; mkdir kilit; bash betik` → çıktı **boş olmamalı**.
Ve `rm -f önbellek; 5 eşzamanlı koşu` → beşi de tam çıktı vermeli.

## Alt-ajan "takıldı" mı, kotası mı dolu?

Pencere sorunu araştırırken sık karışır. opencode/codex **sessizce takılı** görünüyorsa
önce kotayı düşün — kilitlenme değildir:

- `subajan.py` çıkış kodu **3** = `OPENCODE_KOTA_DOLU`.
- opencode kotası dolunca yalnızca banner satırını basar (`> build · <oturum>`), cevap yok.
- Bu durumda `~/.claude/.opencode_yenilenme` dosyasına yenilenme epoch'u yazılır; durum
  çubuğu bu dosyayı okuyup `dolu, yen. <saat>` gösterir. Dosya yoksa **açık** demektir.
- Runner ana süreci öldürse bile `opencode.exe` **çocuk süreç sağ kalabilir** — takılı
  kalanları yaşına bakıp ayrıca öldür, yoksa conhost tutmaya devam eder.

**Eşik/imza kontrolü yazarken:** bayt uzunluğuna güvenme. `wc -c` ham CRLF sayar, Python
`read_text()` satır sonlarını çevirip 3 bayt eksiltir — 20 Eyl'de kota dedektörü tam bu
yüzden (35 vs 32) hiç ateşlememişti. Uzunluk yerine **anlamsal** imza kullan.

## Token sayaçları yanlış gösteriyorsa (20 Eyl 2026, ölçülüp düzeltildi)

Durum çubuğundaki ajan token sayıları `~/.claude/ajan_token.sh` tarafından
üretilir. Üç ayrı hata yaşandı; üçü de aynı gün ölçülerek bulundu.

### Hata 1 — bir ajan hiç sayılmıyor

`ajan-kopru` logları taranırken `case` yalnızca bilinen ajanları eşliyordu:

```bash
case "$f" in
  *_codex_*)    cx=$((cx + t)) ;;
  *_opencode_*) oc=$((oc + t)) ;;
esac                      # <-- *_gemini_* dalı YOK: 24 log sayım dışı kaldı
```

`ajan.py gemini ...` ile açılan loglar `$TEMP/ajan-kopru/*_gemini_*.log`
altına düşer ve tamamen atlanıyordu (gösterilen 522K, gerçeği 938K).
**Yeni bir ajan türü eklediğinde bu `case`'e dal eklemeyi unutma.**

Ajanların token alanı FARKLIDIR, karıştırma:
- gemini/omp → JSON içinde `"totalTokens":N` (`tt` alanı)
- codex → `tokens used` satırının ALTINDAKİ sayı (`tu` alanı), **kümülatiftir**

### Hata 2 — toplama yapma, SON değeri al

`tt[FILENAME] += ...` yazmak cazip ama YANLIŞTIR. gemini `--mode json`
aynı JSON gövdesini akış boyunca tekrar tekrar basar; her tekrar ayrı
harcama sayılır ve toplam ~256 kat şişer (938K yerine **240.713K** görüldü).
Doğrusu dosya başına **son** `totalTokens` değeridir:

```awk
if (match(line, /"totalTokens":[0-9]+/))
  tt[FILENAME] = substr(line, RSTART + 14, RLENGTH - 14) + 0   # = , += DEĞİL
```

codex'in `tokens used` değeri zaten kümülatif olduğu için orada da son değer
doğrudur. İki alanın semantiği farklı ama sonuç aynı: **son değer**.

### Hata 3 — zehirlenen yüksek-su-işareti dosyası

Sayaç log temizliğinde düşmesin diye kalıcı bir maksimum tutulur:

```bash
GM_TOPLAM_DOSYA="$HOME/.claude/.gemini_toplam"
[ "$gm" -gt "$gm_onceki" ] && echo "$gm" > "$GM_TOPLAM_DOSYA" || gm=$gm_onceki
```

Bu yüzden **hatalı bir koşum kalıcı hasar bırakır**: 240M bir kez yazıldıktan
sonra betiği düzeltmek YETMEZ, dosya her koşuda şişmiş değeri geri yükler.
Betiği düzelttikten sonra dosyayı MUTLAKA sıfırla:

```bash
rm -f ~/.claude/.gemini_toplam ~/.claude/.ajan_token.cache
```

Aynı kalıp `.claude_maliyet_toplam` için de geçerlidir.

### Doğrulama — bağımsız ölçümle karşılaştır

Betiğin kendi çıktısına güvenme; ikinci bir yoldan say ve iki sayı tutmalı:

```bash
awk '{ line=$0; gsub(/\033\[[0-9;]*m/,"",line)
       if (match(line, /"totalTokens":[0-9]+/))
         tt[FILENAME]=substr(line,RSTART+14,RLENGTH-14)+0 }
     END { for (f in tt) s+=tt[f]; printf "toplam %d\n", s }' \
  "$TEMP"/ajan-kopru/*gemini*.log
```

Blokları ayrı ayrı topla (ajan-kopru + scratchpad + subajan) ve durum
çubuğundaki sayıyla eşleştir. 20 Eyl'de: 622069 + 235114 + 81432 = 938615 →
çubukta `938K`. **Tutmuyorsa hangi bloğun eksik/fazla olduğunu bul.**

### Elle çalıştırınca CLAUDE ve Bağlam satırları 0 görünür — bu ARIZA DEĞİL

`CLAUDE` satırı statusline'a stdin ile gelen oturum JSON'undaki maliyet
alanlarından beslenir. Betiği elle asgari JSON ile çalıştırırsan bu alanlar
yoktur ve satır `0% │ 0 │ ↻ ?` görünür. Gerçek oturumda doludur.
Buna bakıp "sayaç bozuldu" deme; önce gerçek koşulda gör.
Gerçek girdi her render'da `~/.claude/.statusline_son_girdi.json` dosyasına
yazılır; elle test için `cat ~/.claude/.statusline_son_girdi.json | bash ~/.claude/statusline-command.sh`
kullan — CLAUDE/Bağlam/5H/7D satırları gerçek değerlerle gelir.

## "Çubuk doğru mu?" — satır satır doğruluk denetimi (23 Eyl 2026)

"Çalışıyor mu" iki ayrı soru: (1) çiziliyor ve pencere doğurmuyor mu,
(2) gösterdiği her sayı gerçek kaynağıyla tutuyor mu. İkisini de ölç:

| Satır | Kaynağı | Karşılaştır |
|---|---|---|
| MODEL / CLAUDE / Bağlam / 5H / 7D | stdin JSON (`rate_limits`, `context_window`, `cost`) | `.statusline_son_girdi.json` içindeki `resets_at` epoch'unu `datetime.fromtimestamp()` ile çevir, çubuktaki saatle eşleştir |
| NOBET | AfuNobet `state.db` + `get_best_provider()` | `jobs` tablosunda `status != COMPLETED` job var mı; yoksa router seçimi görünmeli. Supervisor portu 50505 kapalıysa satırda `supervisor kapali` yazar |
| CODEX / GEMINI yüzde + ↻ | `omp usage --json` → `.ajan_kota.cache.ham` (5 dk önbellek) | `amount.used` ve `window.resetsAt` (epoch ms) ile birebir |
| OPENCODE ~% / dolu | `opencode.db` + `~/.local/share/opencode/log/opencode.log` → `.opencode_durum.cache` (`toplam|son5s|son_basari|son_hata|L`, 5 dk) | Aşağıda "Hata 5" |

### Hata 4 — yenilenme saati çizim anına göre kayıyordu (23 Eyl 2026, düzeltildi)

`omp usage` göreli süre verir (`resets in 3h8m`). `yen_saati` bu süreyi **çizim
anındaki** saate ekliyordu; kota önbelleği 300 sn'ye kadar yaşlı olabildiği için
CODEX/GEMINI ↻ saati 5 dk'ya kadar ileri kayıyordu (17:20 yerine 17:21…17:25).
Düzeltme (`ajan_token.sh`): `yen_saati "<süre>" "<ölçüm yaşı>"` — ikinci argüman
süreden düşülür; yaş = `now - mtime($KOTA_ONB)`. OpenCode dalı yaş vermez (dosyası
zaten mutlak epoch). Test: `yen_saati 3h8m 300` = `date -d '+3 hours 3 minutes' +%H:%M`.
Göreli süreyi önbellekten okuyan HER yerde aynı kural: ölçüm anını baz al.
**Kesin çözüm (23 Eyl 2026, aynı gün):** metin çıktısı yerine `omp usage --json` okunuyor
(`reports[].limits[].window.resetsAt` = epoch ms, `amount.used` = yüzde). Tek python ile
ayrıştırılıp önbelleğe `@<epoch>` yazılıyor: `66|86|@1790173238|@1790415233|5H|WK`.
`yen_saati "@epoch"` doğrudan o anı gösterir; haftalık GEMINI artık dakikasıyla sabit
(eski `2d22h` yuvarlaması her ölçümde 12:12 → 12:28 kaydırıyordu). Göreli süre yolu yalnız
OpenCode ve eski önbellek için duruyor. Test: 3 taze ölçüm → ↻ saatleri aynı kalmalı ve
`date -d @<epoch>` ile birebir tutmalı.

### Hata 5 — OPENCODE yüzdesi hiç ölçülmüyordu (23 Eyl 2026, düzeltildi)

Hiçbir sürümde gerçek ölçüm yoktu: sırayla sabit `100`, `50`, `0`, sonra `?` basıldı.
Kullanıcı `0%`yı ölçüm sandı. `omp usage` OpenCode göstermez; ücretsiz big-pickle
limiti sabit değil (geçmişte 5 saatte 411K ve 738K tokende kesildi, 815K de açık kaldı).
Şimdiki kurulum (`ajan_token.sh`, 300 sn önbellekli TEK python bloğu):
- **Dolu kanıtı:** OpenCode kendi logu `opencode.log` → son `Rate limit exceeded` zamanı
  son başarılı cevaptan (DB, `tokens.output>0`) yeniyse ve <5 sa ise `dolu, son hata HH:MM`.
  Eski `retrying in` ve `.opencode_yenilenme` dalları önceliklidir.
- **Tahmini yüzde `~p%`:** L = geçmişte KESİLMEDEN ulaşılmış en yüksek kayan 5 saatlik token
  (input+output+reasoning; 23 Eyl ölçümü 3,6M). `~/.claude/.opencode_limit_tahmin` dosyasında saklanır, yalnız büyür.
  p = son5s/L, en çok 99; dolu kanıtı varsa 100.
  **YAPMA:** L'yi kesilme anlarındaki kullanımdan alma. Önceki denemede (738K) şu an 815K'da hâlâ açıkken
  `~99% … acik` çelişkisi çıktı, kullanıcı çok kızdı. Limit sabit değil; kesilmeler 0 kullanımda bile olmuş.
- Test: `echo $(( $(date +%s)+3600 )) > ~/.claude/.opencode_yenilenme` → `100% … dolu`; dosyayı sil → `~p%`.

### Hata 6 — `omp usage` boş dönünce iyi değerler 5 dk siliniyordu (23 Eyl 2026)

Alt-ajan çalışırken `omp usage` ara sıra boş döner; betik `?|?|?|?` yazıp CODEX/GEMINI'yi
5 dk `?%` gösteriyordu. Artık iki yüzde de sayı değilse `.ajan_kota.cache` EZİLMEZ
(eski dosya + mtime kalır, sonraki koşu yeniden dener; ↻ saati mtime'a göre doğru kalır).

### Tuzak — alt-ajan UTF-8 kutu karakterlerini bozabiliyor

Codex `│` `↻` karakterlerini `â”‚` `â†»` (UTF-8 baytları cp1252 okunup tekrar yazılmış) olarak
dosyaya yazdı; çubuk bozuk göründü. Her alt-ajan düzenlemesinden sonra:
`grep -c $'Ã¢' ~/.claude/ajan_token.sh` → **0** olmalı. Onarım: python ile
`ch.encode("utf-8").decode("cp1252").encode("utf-8")` baytlarını `ch` ile değiştir.
Alt-ajanın "grep 0 döndü" demesine güvenme — kendisi yanlış dizgeyi arayabiliyor.
