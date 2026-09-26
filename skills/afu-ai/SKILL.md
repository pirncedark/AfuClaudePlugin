---
name: afu-ai
description: Afu-AI ana dil paketi — Claude (patron) bir görevi alır, "bu işe hangi model uygun?" diye karar verir, uygun CLI subagent'ına (gemini-flash, gemini-pro, codex, opencode) yaptırır, dönen sonucu TEST EDİP doğrular, kullanıcıya tek sonuç verir. Diğer tüm AI'lar subagent gibi çalışır; her biri KENDİ login/kotasından (token tasarrufu). "afu", "afu-ai", "modele yaptır", "subagent'a ver", "orkestra", "kim uygunsa" deyince tetiklenir.
---

# Afu-AI — Çoklu-Model Orkestra (Claude patron + CLI subagent'lar)

## Fikir
Kullanıcı görevi Claude'a (=afu-ai patron) verir. Claude işi kendi yapmak zorunda değil:
işi analiz eder, **en uygun modele** dağıtır (subagent gibi), dönen çıktıyı **test edip
doğrular**, sonra kullanıcıya TEK, doğrulanmış sonuç verir.

Amaç: **token + zaman tasarrufu**. Her subagent KENDİ aboneliği/login'iyle çalışır;
kullanıcının Claude/API cüzdanı gereksiz yanmaz.

## SUBAGENT EKIBI (cagri sozdizimi — hepsi Windows, 19 Eyl 2026'da CANLI dogrulandi)
| Subagent | Motor | Komut | Guclu yani | Durum |
|----------|-------|-------|-----------|-------|
| **gemini-flash** | google-antigravity/gemini-3.8-flash (omp uzerinden) | `omp -p --mode json --model google-antigravity/gemini-3.8-flash "<gorev>"` | Hizli/ucuz: tarama, ozet, ceviri, "nerede geciyor" (~3 sn, ~$0.006) | OK — FLASH_OK dogrulandi |
| **gemini-pro** | google-antigravity/gemini-3.1-pro (omp uzerinden) | `omp -p --mode json --model google-antigravity/gemini-3.1-pro:high "<gorev>"` | Derin inceleme, mimari/plan, ikinci gorus (~4 sn, ~$0.048) | OK — PRO_OK dogrulandi |
| **codex** | ChatGPT (gpt-6-luna, medium, Fast) | `codex exec --skip-git-repo-check "<gorev>"` — review: `codex exec review` | Guclu kod + satir bazli bug avi | OK — v0.155.1, kota ACIK |
| **opencode** | OpenCode Go / Zen | `python ~/.claude/skills/afu-ai/scripts/subajan.py opencode "<gorev>"` | Kod, uzun baglam | Runner ile kullan |

**omp'nin kendisi** subagent degil, yukaridaki iki Gemini'yi tasiyan tasiyicidir
(v18.2.6). Model belirtmezsen `modelRoles.default` = gemini-3.8-flash-tiered calisir.

### opencode neden KAPALI (19 Eyl 2026) — ve ne zaman acilir
- **Ucretsiz kota bitti.** opencode TUI'de gercek mesaj:
  `Free usage exceeded, subscribe to Go [retrying in 14h 4m attempt #1]`
  19 Eyl 12:56'da olculdu -> kota **20 Eyl 2026 ~03:00** civari yenilenir.
- **TUZAK — sahte "takilma":** kota bitince runner OpenCode hatasini loga alamaz; sessizce
  geri-cekilme (backoff) beklemesine girer ve saatlerce bekler. Log 35 baytlik
  basliktan ibaret kalir. 300-400 sn'lik timeout'lar bu beklemenin icine duser ve
  "ajan kilitlendi / model bozuk" gibi gorunur. **Bu bir kilitlenme degil, kota.**
  Teshis icin: runner logunu kontrol et. 35 bayt ve `big-pickle` imzasi varsa
  runner `OPENCODE_KOTA_DOLU` basar ve cikis kodu 3 dondurur.
- **Ucretli modeller:** `Unauthorized ... CreditsError: No payment method` — cuzdana
  odeme yontemi eklenmeden acilmaz (Go aboneligi bunu da cozer).
- `opencode models` ve `opencode auth list` calisiyor -> CLI/ag/kimlik saglam.
- Kota dolu iken "uzun baglam / kod yazma" isleri **codex**'e gider.

### TUZAKLAR (yasanip dogrulandi)
1. **gemini-pro'da dusunme seviyesi ZORUNLU:** `gemini-3.1-pro` seviyesiz cagrilirsa
   omp sessizce takilabilir. Her zaman `:high` (veya `:low`) yaz. Flash'ta serbest.
2. **omp'de `-m` YOK** — model secimi `--model`.
3. **codex trusted-dir disinda `--skip-git-repo-check` ister;** yoksa
   "Not inside a trusted directory" deyip hic calismaz. Ayrica stdin'i bagla (`</dev/null`),
   yoksa "Reading additional input from stdin" ile bekler.
4. **opencode'u BORUYLA cagirma** (`| tail`) — ajani kilitler, log 0/35 bayt kalir.
   Cikti dogrudan dosyaya: `> log 2>&1`.
5. **opencode sessiz kalirsa once KOTA'yi dusun**, kilitlenmeyi degil (yukari bak).
   Bos log + uzun bekleme = `Free usage exceeded`, backoff'ta bekliyor.

### CLI guncelleme ("afu cli update")
- omp: `omp update` (sonra config newline + provider smoke test ZORUNLU)
- TUZAK (19 Eyl 2026 yasandi): `omp update` config.yml'yi YENIDEN YAZAR — yorum satirlarini
  siler, modelRoles'u degistirir ve **son newline'i dusurur**. Guncelleme ONCESI yedekle
  (`cp config.yml config.yml.bak.$(date +%Y%m%d-%H%M%S)`), SONRA newline'i geri koy
  (`printf '
' >> ~/.omp/agent/config.yml`) ve smoke test'i kos.
- npm: `npm install -g opencode-ai@latest @openai/codex@latest`
- TUZAK: Windows'ta npm guncellemesi yarim kalip shim'leri silebilir / codex klasorunde sadece
  node_modules birakabilir (`command not found`, `npm ls` bos surum). Cozum:
  `npm uninstall -g @openai/codex; rm -rf %APPDATA%/npm/node_modules/@openai/codex` + tekrar install.

Ekip bu dordu ile sinirli. (pi = login yok, resmi gemini CLI = Google bireysel tier'i kapatti; Gemini'ye erisim omp uzerinden.)

## ⛔ PENCERE KURALI — ALT-AJANI ASLA ÇIPLAK ÇAĞIRMA (Reyhan, 19 Eyl 2026)

**Yaşanan arıza:** çıplak `codex exec ...` bir kez koştu, conhost sayısı
**61 → 1691** oldu. Her konsol komutu bir `conhost.exe` doğuruyor; ebeveyn süreç
bitince conhost **ÖLMÜYOR**, öksüz kalıp ekranda boş siyah pencere olarak yığılıyor.
Kullanıcının ekranı üst üste pencerelerle doldu, makine kapanacak hale geldi.

### ZORUNLU: sarmalayıcıyı kullan
```bash
python ~/.claude/skills/afu-ai/scripts/subajan.py codex "<gorev>" --cwd "<dizin>" --timeout 600
python ~/.claude/skills/afu-ai/scripts/subajan.py flash "<gorev>" --cwd "<dizin>"
python ~/.claude/skills/afu-ai/scripts/subajan.py pro   "<gorev>" --cwd "<dizin>"
```
### CANLI DURUM + OZET CIKTI (26 Eyl 2026)
- Her kosu `~/.claude/afu-ajanlar/<id>.json` dosyasina yazar: ajan, gorev, cwd, pid, durum, token, eylem, cikis, log, ozet; 2 saniyede bir heartbeat guncellenir.
- stdout yalniz ajanin son mesaji ve tek footer satiridir (ajan, cikis, sure, token, durum, log). Ham log dosyada kalir; tam cikti icin `--ham` kullan.
- codex `--json` ve `-o` ile, opencode `--format json` ile calisir. omp 429 artik opencode kotasi gibi cikis 3 verir.
- Ajanlari `afunobet monitor --canli` agacinda ve status bardaki AJANLAR satirinda izle.
- Codex icin `--sozlesme`, final cevabi tanimli JSON semasina zorlar; JSON tek satir basilir.
- Gecersiz JSON finali oldugu gibi basilir ve footer `sozlesme=gecersiz` ekler.
- Ornek: `python scripts/subajan.py codex "degisikligi tamamla" --sozlesme`
- Codex icin `--worktree`, secenegi dogrudan `codex exec` komutuna aktarir.
- Ornek: `python scripts/subajan.py codex "izole calis" --worktree`
- Avenox yedi civi: “rapor degil sozlesme” — sef ham loglari okumamali.

Sarmalayıcı şunu garanti eder:
1. `CREATE_NO_WINDOW` + `CREATE_NEW_PROCESS_GROUP` → **hiçbir pencere açılmaz**
2. `stdin=DEVNULL` → codex "Reading additional input from stdin" ile beklemez
3. Çıktı doğrudan dosyaya — **boru (`| tail`) YOK** (boru ajanı kilitler)
4. İş bitince **öksüz conhost'ları otomatik temizler**

**Doğrulandı (19 Eyl 2026):** sarmalayıcıyla codex koşusu — conhost 654 → **471**
(azaldı), pencere açılmadı, görev tamamlandı.

### TUZAK: `shell=True` kullanma
`codex` ve `omp` Windows'ta birer `.cmd` shim'i. `shell=False` Popen çıplak adı
bulamaz (`WinError 2`). Çözüm **`shell=True` DEĞİL** — o fazladan bir cmd.exe +
conhost daha doğurur. Çözüm: `shutil.which()` ile tam yolu çöz (sarmalayıcıda
`cozumle()` bunu yapar).

### İKİNCİ KAYNAK: Git Bash'in kendisi (20 Eyl 2026, ölçüldü)

Alt-ajan hiç çalıştırılmasa bile pencereler birikiyordu. Ölçüm: **Bash tool'undan
geçen her komut** bir `cygwin-console-helper.exe` + `conhost.exe` doğuruyor;
komut bitince helper ölüyor, conhost'u **öksüz kalıyor**. Tek oturumda ~6 Bash
çağrısında conhost **26 → 83** oldu (≈7 pencere/çağrı). Sarmalayıcı bunu çözmez —
sorun alt-ajanda değil, kabuğun kendisinde.

**Kurallar:**
1. Çok sayıda kısa Bash çağrısı yapma — işi **tek çağrıda** birleştir
   (`cmd1 && cmd2 && cmd3`, tek heredoc'lu python bloğu). Çağrı sayısı = pencere sayısı.
2. Saf Windows işinde (WMI, süreç, servis, kayıt defteri) **PowerShell tool'unu**
   tercih et — cygwin helper doğurmaz.
3. **Paralel alt-ajan en fazla 3**, hepsi `subajan.py` üzerinden. Her ajan için
   ayrı pencere/terminal açma. (Test penceresi sınırı ayrıca 5'tir.)

### OTOMATİK TEMİZLİK — kurulu (20 Eyl 2026)
`~/.claude/settings.json` içinde **Stop** ve **SubagentStop** kancaları
`conhost_temizle.ps1 -Sessiz`'i `async` + `-WindowStyle Hidden` ile çalıştırır:
her tur sonunda ve her alt-ajan bitişinde öksüz pencereler sessizce süpürülür.
Elle uğraşmak gerekmez; kanca silinirse pencereler tekrar birikir.

### Ekran zaten dolduysa — acil temizlik
```bash
powershell -NoProfile -ExecutionPolicy Bypass -File ~/.claude/skills/afu-ai/scripts/conhost_temizle.ps1
powershell ... -File conhost_temizle.ps1 -KuruCalis    # önce sadece say
powershell ... -File conhost_temizle.ps1 -Esik 40      # 40 altinda hic ugrasma
powershell ... -File conhost_temizle.ps1 -Sessiz       # kanca modu, ciktisiz
```
Betik **iki turlu** çalışır: önce öksüz `cygwin-console-helper`, sonra öksüz
`conhost`. **Yalnızca ebeveyni ÖLÜ** süreci öldürür; açık terminaline / Claude Code
oturumuna dokunmaz. (19 Eyl: 1840 → 545. 20 Eyl: 83 → 60, iki turlu sürümle.)


## KANIT BANNER'I (zorunlu)
omp'yi ciplak cagirma - **sarmalayiciyi kullan**, isi kimin yaptigini kanitli bassin:

```bash
python ~/.claude/skills/afu-ai/scripts/omp_kanit.py "<gorev>" --cwd "<dizin>" --timeout 600
```

Cikti: cevap + renkli tablo (yesil = isi yapan, kirmizi = kapali) + oturum ID,
token, maliyet, sure. Tum alanlar omp'nin kendi `--mode json` ciktisindan okunur,
elle yazilmaz -> uydurulamaz.

**Banner kirmizi `!! DIKKAT` uyarisi basarsa DUR:** omp beklenen saglayiciya degil
Anthropic'e dusmus demektir, yani is UCRETLI calismistir.

### TUZAK: config.yml'nin son satir sonu
`~/.omp/agent/config.yml` dosyasinin sonunda satir sonu (newline) yoksa omp TUM
YAML'i sessizce yok sayar ve varsayilan modele (anthropic/claude-opus-4-8, ucretli)
duser - hicbir hata vermez. `sed -i` bu satir sonunu silebilir. Config'e her
dokunustan sonra dogrula:

```bash
tail -c 1 ~/.omp/agent/config.yml | xxd          # 0a ile bitmeli
cd /tmp && omp -p --mode json "test" | grep -o '"model":"[^"]*"' | head -1
```

> Not: Bir subagent 401/auth hatası verirse → o modeli listeden düş, kullanıcıya "login gerek" de,
> UYDURMA. Çalışan başka subagent'la devam et. (bkz. feedback: uydurma denetimi)

## YÖNLENDİRME (routing) — "bu işe kim uygun?"
- **Hızlı/kısa/ucuz** (özet, çeviri, tek soru, format, tarama) → **gemini-flash**
- **Derin inceleme / mimari / ikinci görüş** → **gemini-pro** (`:high` ŞART)
- **Kod yazma / dosya düzenleme** → **codex** (opencode kapalı)
- **Kod review / bug avı** → **codex exec review**
- **Uzun bağlam / repo geneli** → **gemini-flash** (1M) ile tara, bulguyu **codex**'e yaptır
- **Basit deneme / yedek** → **gemini-flash**
- Emin değilsen: tek bir ajanı gerekcesiyle sec; ikinci ajanı yalnız dogrulama gerektiginde ekle.

## AKIŞ (her görevde)
1. **Analiz:** Görevi tek cümlede tanımla. Küçük mü, kod mu, uzun mu?
2. **Karar:** Yukarıdaki tabloya göre subagent(ları) seç. Neden seçtiğini 1 satır söyle.
3. **Dağıt:** Alt-ajan YALNIZ `subajan.py` ile baslatilir. Runner destegi olmayan ajan CAGRILMAZ.
   Ayni anda EN FAZLA 3 ajan. Ajanlari tek tek ve gerekcesiyle sec. Prompt'u NET yaz
   (subagent senin bağlamını bilmez — gerekli dosya/kuralı prompt'a koy).
4. **TEST ET (zorunlu):** Dönen çıktıyı körlemesine kabul etme.
   - Kod ise: çalıştır / syntax kontrol / testini koştur.
   - Metin ise: göreve uygun mu, eksik/uydurma var mı kontrol et.
   - Yanlışsa: düzelt ve subagent'a **geri iş ver** (loop).
5. **Sonuç:** Kullanıcıya TEK, doğrulanmış sonucu ver. Hangi modelin yaptığını kısaca belirt.

## GOAL-LOOP (isteğe bağlı, /loop ile)
Kullanıcı "loop"/"hedef" derse: hedefe ulaşana kadar
dağıt→test→düzelt→geri ver döngüsü. Her turda ilerlemeyi kısaca raporla.
Sonsuz döngüye karşı: 3 turda ilerleme yoksa dur, kullanıcıya sor.

## KURALLAR
- Önce DEĞİŞMEZ KURALLAR (`degismez-kurallar` skill'i) — subagent'a verdiğin iş de bunlara uymalı.
- Subagent çıktısını DOĞRULAMADAN "oldu" deme (evidence-before-assertions).
- Her subagent kendi login'iyle; kimseye körlemesine API key gömme.
- Auth hatası = o modeli düş + kullanıcıya bildir, uydurma.
- Rapor kısa; ham subagent dökümünü yapıştırma, özetle.
- Riskli/yıkıcı işlerde (dosya silme, canlıya push) önce kullanıcı onayı.
