---
name: ajan-kopru
description: opencode ve codex'i alt-ajan (team agent) olarak calistirip isi onlara yaptirmak icin kullan. Claude planlar + denetler, ajanlar yazar. "opencode ile yaptir", "codex'e ver", "alt ajan", "team agent", "ajanlara dagit", "codex calistir", "paralel ajan" deyince tetikle. Kilitlenme/ag/kimlik tuzaklarinin cozumu icinde.
---

# Ajan Koprusu — opencode + codex'i alt-ajan olarak calistirma

Claude **planlar, gorev yazar, sonucu DOGRULAR**; kodu/isi opencode ve codex yapar.
Amac: token tasarrufu + is bolumu. Her ajan kendi login'iyle calisir.

## 0. EKIP DURUMU (13 Eki 2026; dagitim = ~/.claude/AFU_PLANLAR.md KOTA DENGESI)
| Ajan | Durum | Not |
|------|-------|-----|
| codex (gpt-6.1-sol, fast off) | **CALISIYOR** | en guvenilir; git/PR/release yetkisi de bunda |
| gemini-3.8-flash (omp) | **CALISIYOR** | hizli/ucuz tarama-ozet; ~0.006-0.026 USD/is |
| pro = Claude Opus 5.5 (Antigravity, omp) | **CALISIYOR** | 13 Eki; Google kotasi; eski gemini-3.1-pro zayif kaldi |
| opencode (space-bunny-free) | **CALISIYOR** | test/derleme; kota dolarsa log 35 bayt kalir (asagi bak) |
| haiku (Claude Haiku 5.5) | **CALISIYOR** | ufak isler; Claude kotasindan yer |

**KOTA DOLDUGUNU NASIL ANLARSIN (opencode):** log **35 bayt** kalir — yalniz
`> build · big-pickle` banner'i, sonrasi BOS, hata mesaji YOK, surec de olur.
TUI'de ayni durum "Free usage exceeded, subscribe to Go [retrying in Xh]" yazar
ama runner ile calisan non-interactive OpenCode bunu log'a YAZMAZ. 35 bayt = kota.
Ayni belirti bayrak/ortam sorunuyla KARISIR; ayirt etmek icin: BASKA bir ajan
(codex) ayni anda calisiyorsa sorun ortamda degil, o ajanin kotasindadir.

**KOTA HALA DOLU MU? 10 saniyede olc** (2026-09-19'da boyle dogrulandi):
```bash
python ~/.claude/skills/afu-ai/scripts/subajan.py opencode "1 + 1 kactir? Sadece sayiyi yaz." --cwd "~" --timeout 20
# log 35 bayt kaldiysa -> hala DOLU. Cevap yazdiysa -> kota ACILMIS.
```
**YENILENME SAATI HICBIR YERDE YOK.** runner ile calisan non-interactive OpenCode
"retrying in Xh" mesajini log'a YAZMAZ; `omp usage` opencode'u LISTELEMEZ.
Elde yalniz TUI'nin bir kez soyledigi goreli sure kalir. Yani alt barda
opencode icin saat gosterilemez — "dolu" yazip yukaridaki yoklamayla
periyodik kontrol etmek DOGRU davranistir. Saat UYDURMA.

## 0b. SKILL DOSYASI YAZARKEN TUZAK (yasandi 2026-09-19)
SKILL.md **slash-komut** olarak cagrildiginda (`/ajan-kopru <arg>`) metindeki
dolar isaretli yer tutucular (dolar+0, dolar+1, dolar+ARGUMENTS)
kullanicinin argumaniyla DEGISTIRILIR. Fiyati "dolar+0.006" seklinde
yazmistim; `/ajan-kopru aktif edelim` denince metinde "~aktif.006" gorundu.
Ayrica Windows yollarinda ters-bolu + a/t gibi
diziler kacis karakteri olarak yenebiliyor (`$env:TEMPjan-kopru` ->
`$env:TEMPjan-kopru`).
KURAL: para birimini "0.006 USD" diye yaz, dolar+rakam KULLANMA;
Windows yollarinda duz bolu (`/`) tercih et veya tirnak icine al.

## 0c. AJAN SIRASI — KULLANICI KARARI (2026-09-19 17:26) ZORUNLU
**opencode -> gemini -> codex.** Is verirken bu siraya uy.
Gerekce: opencode ve gemini kotalari daha SIK/ERKEN yenileniyor; codex'in
kotasi en degerli olan, ONU SAKLA (git/PR/release islerinde `--tam` sart).
- opencode kotasi dolu mu? Once 10 saniyelik yoklama yap (bkz. bolum 0).
  Dolu ise gemini'ye gec. Gemini de dolu/yetersizse codex'e gec.
- `~/.claude/ajan_token.sh` alt barda kotalari SAAT olarak gosterir
  (`codex %12 1330K yen. 20:42`). Is vermeden once ORAYA BAK.
- Bir ajan yanlis secildiyse: surecini oldur (`Stop-Process -Id <pid> -Force`),
  `git status` ile hicbir sey yazmadigini DOGRULA, sonra dogru ajana ayni
  gorev dosyasiyla yeniden ver. Gorev metnini yeniden yazmaya gerek YOK.
  **DIKKAT:** `codex.exe ... app-server` daemon'unu OLDURME — o ayri bir
  surectir ve surekli calisir. Oldurecegin sureci `CreationDate` ve
  komut satirindan AYIRT ET.

## 1. Rol dagilimi (varsayilan)
| Is | Ajan | Neden |
|----|------|-------|
| Kod yazma, coklu dosya duzenleme, refactor | **opencode** (kotasi doluysa **codex**) | uzun baglam, hizli edit — bkz. bolum 0 |
| Kod review / bug avi / "bu dogru mu" | **codex** (salt-okur) | satir bazli kanit cikariyor |
| git push, PR, gh islemleri | **codex --tam** | kimlik deposu erisimi gerekir |
| Surum notu, dokuman | codex veya opencode | ikisi de olur |
| git branch/stash cerrahisi | **Claude kendi yapar** | geri donusu zor, delege etme |

Paralel calistirirken **dosya alanlarini AYIR** (or. biri `.github/`, digeri `docs/`).
Ayni dosyaya iki ajan dokunursa "Files changed on disk between my read and edits" cikar.

## 1b. UCUNCU AJAN: Gemini (omp uzerinden) — CALISIYOR (2026-09-19)
`omp` Antigravity aboneligiyle Gemini'ye baglanir. Kullanim:
```bash
omp -p "<gorev>" --mode json --model google-antigravity/gemini-3.8-flash          # hizli tarama/ozet
omp -p "<gorev>" --mode json --model google-antigravity/gemini-3.1-pro:high       # derin inceleme
```
| Model | Sure (ayni is) | Maliyet | Ne icin |
|-------|----------------|---------|---------|
| gemini-3.8-flash | 3.2 sn | ~0.006 USD | tarama, ozet, i18n, "nerede gecisiyor" |
| gemini-3.1-pro:high | 4.1 sn | ~0.048 USD | mimari/plan incelemesi, ikinci gorus |

**TUZAK — DUSUNME SEVIYESI:** `gemini-3.1-pro` ve `gemini-3-pro` YALNIZ
`low,high` destekler (flash'ta `minimal,low,medium,high` var). Seviye
BELIRTMEDEN cagirirsan omp sessizce TAKILIR — 280 sn'de tek satir cikti yok,
hata da vermez. Pro modellerinde HER ZAMAN `:high` (veya `:low`) yaz.

**TUZAK — SURE SINIRI:** Cok dosya okutan buyuk gorevlerde omp'ye `timeout 600`
YETMEZ. Model dosyalari okur ama cevabi yazamadan kesilir; log'da son satir
`turn_start` kalir ve "model cevap vermedi" gibi GORUNUR (yanlis teshis).
Boyle gorevlerde `timeout 1500` ver; log'da `turn_end` + metin YOKSA once
SURE SINIRINI sorgula, modeli sucla-ma.

**Gorev buyuklugu:** dosya okuyup uzun rapor yazan islerde flash ~78K token /
~0.026 USD harciyor ve dakikalar surebiliyor. Kucuk, net sorular daha verimli.

**TUZAK — BAYRAK:** omp'de `-m` YOK; model secimi `--model`.
**TUZAK — KOTA:** Google bireysel kotasi dolunca 429 "Individual quota reached"
gelir ve 1 sn'de duser (takilma DEGIL). Abonelik yukseltmesi bunu acar.
`omp models` -> saglayici listesi. opencode-zen omp'den KULLANILAMAZ
(403 "free tier can only be used from within OpenCode").

## 2. Calistirma — ZORUNLU sekil
```bash
python ~/.claude/skills/afu-ai/scripts/subajan.py opencode "<gorev>" --cwd "C:/proje"
python ~/.claude/skills/ajan-kopru/scripts/ajan.py codex gorev.txt --cwd "C:/proje" --yaz
python ~/.claude/skills/ajan-kopru/scripts/ajan.py codex gorev.txt --cwd "C:/proje" --tam   # git push / gh
```
Script log yolunu basar; surec arka planda kalir.

### TUZAKLAR (hepsi yasanip dogrulandi, 2026-09-19)
1. **BORU KULLANMA.** Alt-ajan YALNIZ `subajan.py` ile baslatilir. Runner destegi olmayan
   ajan CAGRILMAZ. Cikti DOGRUDAN log dosyasina gider; boru ajani kilitler.
1b. **`DETACHED_PROCESS` KULLANMA — ajani OLDURUR.** (Yasandi 2026-09-19:
   "ajan kabukla birlikte oluyor" diye yanlis teshis koyup Popen'a
   DETACHED_PROCESS eklendi; sonraki IKI ajan da aninda oldu — log 0 bayt,
   surec yok, hata yok. Bayraktan ONCE baslayan ajan calismaya devam ediyordu:
   iste kanit.) Konsolsuz kalan CLI aninda cikiyor. DOGRUSU:
   `CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW` (ajan.py'de boyle).

1c. **AJAN GERCEKTEN CALISIYOR MU — 3 kanit, sirayla bak:**
   ```powershell
   Get-Process | Where-Object { $_.ProcessName -match '^(opencode|codex|omp)$' }
   Get-ChildItem $env:TEMPjan-kopru\*.log | Sort LastWriteTime -Desc |
       Select -First 5 Name, Length, LastWriteTime
   ```
   - Arka plan KABUK listesi ALDATICI: ajan.py cikip gittigi icin ajan orada
     GORUNMEZ. "Sadece 1 sey calisiyor" izlenimi yanlis olabilir.
   - Log **0 bayt + surec yok** = ajan HIC baslamadi (bayrak/ortam sorunu).
   - Log sadece acilis banner'i + surec var = calisiyor, sabret.
   - Yeni bir baslatma sekli denedikten SONRA kucuk bir duman testi kos:
     `ajan.py codex <kisa_gorev> && grep <beklenen> <log>`. Bir turda iki
     ajani birden yeni yontemle baslatma.
1d. **codex GIT DEPOSU OLMAYAN klasorde CALISMAZ** (yasandi 2026-09-19).
   Belirti: log **105 bayt**, icinde `Reading prompt from stdin...` ve
   `Not inside a trusted directory and --skip-git-repo-check was not specified.`
   Surec hemen olur, hicbir sey yapilmaz. `~/.claude`, `~/Downloads` gibi duz
   klasorlerde gorulur. COZUM: `codex exec --skip-git-repo-check ...`
   `ajan.py` bunu artik OTOMATIK ekliyor (hedef klasorde `.git` yoksa).
   **Log boyutu imzalari — ezberle:** 0 bayt = hic baslamadi (bayrak/ortam);
   35 bayt = opencode kotasi dolu; 105 bayt = codex git-deposu reddi.

2. **codex `--full-auto` YOK** (v0.154). Dogrusu `-s workspace-write|read-only|danger-full-access`.
3. **codex `-s workspace-write` AGI KAPATIR.** `git push`/`gh` -> `Failed to connect ... port 443`.
   Ag icin: `-c 'sandbox_workspace_write.network_access=true'` (ajan.py `--ag`).
4. **Ag acik olsa bile kimlik deposu kapali kalir:** `schannel: AcquireCredentialsHandle failed:
   SEC_E_NO_CREDENTIALS`. git push / gh icin **`--tam`** (danger-full-access) sart.
5. **Claude'un kendi Bash'i de agi kapatir.** `gh`/`curl` denemelerinde
   `dangerouslyDisableSandbox: true` gerekir.
6. **omp/afu "cevap vermiyor" derken ACELE ETME** (2026-09-19'da iki kez yanlis
   teshis kondu). Once SIRAYLA elE:
   a) `--model` verilmis mi? (varsayilan model kotali olabilir)
   b) Pro modelinde `:high` var mi? (yoksa sessizce takilir)
   c) `timeout` yeterli mi? (buyuk gorevde 600 sn YETMEZ, 1500 ver)
   d) Log'da 429 "Individual quota reached" var mi? (kota, model sorunu degil)
   Bunlarin hepsi giderilince omp/Gemini SORUNSUZ calisiyor — bkz. 1b.

## 3. Canli izleme (kullanici "ne durumdalar" derse)
```bash
python ~/.claude/skills/ajan-kopru/scripts/kopru.py 15     # opencode DB + codex kaydi
tail -30 <log>                                             # dogrudan log
```
opencode kendi oturumunu SQLite'a yazar: `~/.local/share/opencode/opencode.db`
(`session`, `message`, `part` tablolari; `part.data` JSON — type: text|tool|reasoning).
codex kaydi: `~/.codex/history.jsonl` (+ `~/.codex/sqlite/`).

### TUZAK — MONITOR TASARIMI (yasandi 2026-09-19, ucu birden)
**a) "No output available" = monitor YANLIS kurulmus.** Yalniz ajan BITINCE
yazan bir monitor (surec kayboldu mu diye bakan dongu) ajanlar calisirken
HICBIR SEY basmaz; kullanici panele bakinca bos gorur ve "calisan agent
gozukmuyor" der. DOGRUSU: **duzenli nabiz** + bitis bildirimi birlikte.
Her 90 sn'de TEK satir: her ajan icin `log_boyutu/son_yazma_yasi:durum`.
Boyut buyuyorsa ajan calisiyordur; 2 dk sessizlik = bitti.
Calisan ornek: `$TEMP/ajan_pano.sh` (bu skill ile birlikte saklaniyor).

**b) `tail -F | grep` ajan loglarinda ISE YARAMAZ.** Iki ayri sebeple:
  - codex log'u okudugu DOSYALARIN icerigini de basar. Baska bir skill'in
    SKILL.md'sini okuduysa `^### Step 1 ...` gibi satirlar bildirim olur.
    Yani `^### ` gibi genel kalip ajanin KENDI raporu sanilir — degildir.
  - gemini/omp `--mode json` ile calisir: TUM gorev metni TEK satirda,
    devasa bir JSON olarak log'a duser. `error`, `fatal` gibi kelimeler
    GOREV METNINDE gectigi icin monitor daha ilk saniyede patlar.
  COZUM: icerige degil **dosya boyutu + surec varligina** bak (madde a).

**c) Ayni anda IKI codex varsa surec adiyla bitis tespiti yapma.**
`tasklist | grep codex` ikisi de bitene kadar dolu kalir; ilk ajanin
raporu 5 dakika beklemis olur. Log dosyasi basina AYRI takip yap.

Filtre kullanacaksan **dar** olsun; `error` gibi genel kelime grep gurultusunu
bildirime cevirir. Ise yarayan filtre:
`^← (Edit|Write)|SONUC:|BASARISIZ|Traceback|tokens used|fatal:|https://github.com/.*/pull`

## 4. Gorev metni nasil yazilir (ajan senin baglamini BILMEZ)
Her gorev dosyasinda su 5 blok olsun:
1. **ONCE OKU** — ilgili dosyalar, satir numaralariyla.
2. **KANIT** — hatanin gercek ciktisi/log'u (uydurmasin diye).
3. **YAP** — numarali, tek tek, net istekler.
4. **SINIR/YASAK** — dokunmayacagi dosyalar; `git commit/push/tag YAPMA` (izin vermedikce).
5. **BITINCE** — calistirilacak dogrulama komutu (test, `yaml.safe_load`, syntax kontrol)
   ve istenen rapor bicimi.

## 4b. COMMIT YETKISI TEK AJANDA OLSUN (yasandi, iki kez)
Ayni degisiklik icin iki ajana birden "commit et" deme. Olan:
opencode isi yapip commit etti, ardindan codex ayni dosyalari yeniden
commit'ledi; ikincisi birincinin commit'ini geri alip kendi mesajiyla yazdi
(icerik ayniydi, kayip olmadi — ama tarih kirlendi ve bir tur bosa gitti).
KURAL: kod yazan ajana "commit ATMA, ben/baska ajan yapacak" de; commit+push
TEK bir ajanin gorevi olsun.

TUZAK: commit mesajini PowerShell uzerinden tek tirnakla gecirme — tirnaklar
ikiye katlaniyor ("CI''da", "''core''"). Mesaji dosyaya yazdirip
`git commit -F <dosya>` kullandir.

## 4c. GOREV METNI KALIBI (bugun ise yarayan sekil)
Her gorev dosyasinda su bloklar oldu mu is duzgun cikiyor:
1. **KANIT** — hatanin GERCEK ciktisi (CI log'u, traceback). Ajan uydurmasin.
2. **TESHIS** — kok sebep, DOSYA:SATIR ile. (Ajanin yeniden kesfetmesini bekleme;
   biliyorsan yaz. Bilmiyorsan "teshis et" de.)
3. **YAP** — numarali, tek tek, olculebilir istekler.
4. **SINIR** — es zamanli ajanlar varsa dokunmayacagi dosyalari TEK TEK say:
   "ui/ altina DOKUNMA, tests/video_ui_test.py OLUSTURMA, test.ps1'in SONUNA ekle".
5. **BITINCE** — calistirilacak dogrulama komutu + istenen rapor bicimi.
6. **COMMIT YETKISI** — "commit ATMA" ya da "commit + push ONAYLI" acikca yaz.

## 4c2. "ONAY BEKLEME" MADDESI ZORUNLU (yasandi 2026-09-19)
codex etkilesimsiz (`exec`) calisirken bile plan yapip
"Bu tasarimla uygulamaya gecmemi onayliyor musun?" diye SORUP CIKABILIYOR —
cevap verecek kimse olmadigi icin is SIFIR ciktiyla biter (log'da guzel bir
tasarim taslagi durur, kod YAZILMAMISTIR). Belirti: log dolu, `git status` bos.
Her gorev metnine su blogu KOY:
```
ONAY BEKLEME — ETKILESIMSIZ CALISIYORSUN:
Sana cevap verecek kimse YOK. "Onayliyor musun / devam edeyim mi" diye SORMA;
sorarsan is bosa gider. Plani kendin kur, DOGRUDAN uygula, sonunda raporla.
Karar gereken yerde en makul secenegi SEC ve gerekcesini raporda yaz.
```

## 4d. ES ZAMANLI CALISTIRMA — dosya alanini BOL
Bugun 3 ajan ayni depoda sorunsuz calisti cunku alanlar ayrildi:
- codex#1 -> afuadm.py, core/models.py, video/ytdlp.py, api/server.py
- codex#2 -> ui/, app.py
- codex#3 -> .github/workflows/, docs/RELEASE_NOTES/
- gemini  -> salt-okur (analiz/taslak)
Cakisma belirtisi: "Files changed on disk between my read and edits".
`tests/` ortak alan: her ajana AYRI test dosyasi adi ver.

**DENETCI ile YAZICI ayni dosyalardaysa (yasandi 2026-09-19):**
Denetciye "calisma agacini oku" DEME — commit'lenmis SHA'yi oku dedir:
`git show <sha>` . Boylece yazici ajan ayni dosyalarda calissa bile
denetim raporu tutarli kalir. Gorev metnine su cumleyi koy:
"Degerlendirmeni `git show <sha>` ciktisina dayandir, calisma agacindaki
commit'lenmemis degisikliklere DEGIL."

**DENETIM BULGULARINI HEMEN BASKA AJANA VERME.** Rapor geldiginde yazici
ajan HALA ayni dosyalarda olabilir. Bulgulari biriktir, yazici bitip
commit atilinca TEK gorev dosyasi halinde sirdaki ajana ver. Aksi halde
iki ajan ayni satirlari ezer.

## 4e. AYRI SURUM = AYRI WORKTREE (gercek paralellik)
Ayni depoda iki FARKLI surum uzerinde ayni anda calisilacaksa dosya alani
bolmek yetmez; ayri calisma agaci ac:
```bash
git worktree add -b v1.7-torrent ~/AfuDM-v17 origin/main
```
Ajana `--cwd ~/AfuDM-v17` ver ve gorev metnine "ANA KLASORE
DOKUNMA" yaz. Boylece v1.6 ve v1.7 ayni anda ilerler, testler birbirini
etkilemez. Bitince: `git worktree remove <yol>`.
**TUZAK — WORKTREE'DE COMMIT ATILMIYOR:** worktree'nin `.git`'i bir DOSYADIR ve
ana depoyu gosterir (`gitdir: C:/.../AfuDM/.git/worktrees/<ad>`). codex
`--yaz` (workspace-write) ile calisirken oraya YAZAMAZ; hata:
"commit asamasi ortamin worktree Git metaverisine yazma izni nedeniyle engellendi".
COZUM: worktree gorevlerinde ajana **"COMMIT ATMA"** de, kodu/testi o yazsin,
commit'i Claude (veya `--tam` yetkili ayri bir ajan) atsin.

UYARI: stash yigini worktree'ler ARASINDA ORTAKTIR — ciplak `git stash`
kullandirma; ajana "WIP commit at" dedir.

## 5. Dogrulama — ajan raporuna GUVENME
Ajan "tamamlandi" dese bile Claude:
- `git diff` ile degisikligi KENDI okur,
- testi/dogrulama komutunu KENDI kosar,
- iki ajan paralel calistiysa sozlesmenin kenetlendigini kontrol eder
  (or. biri dosyaya `<!-- PLACEHOLDER -->` koydu, digeri onu dolduruyor mu).
Kanit gormeden "oldu" deme.

## 6. Bilinen faydali kalip: yaz + denetle
```
opencode  -> degisikligi yapar
codex     -> `-s read-only` ile ayni diff'i denetler, DOSYA:SATIR kanitiyla
Claude    -> diff'i okur, testi kosar, kalan kusuru tekrar opencode'a yollar
```

## ⛔ PENCERE SIZINTISI (19 Eyl 2026)
`ajan.py` zaten `CREATE_NO_WINDOW` kullanır — sorun ondan **DEĞİL**. Arıza,
alt-ajanın Bash'ten **çıplak** çağrılmasından çıktı (`codex exec ...`): conhost
61 → 1691 oldu, ekran pencereyle doldu. Kural: alt-ajanı her zaman
`~/.claude/skills/afu-ai/scripts/subajan.py` ile çağır. Temizlik:
`~/.claude/skills/afu-ai/scripts/conhost_temizle.ps1`. Ayrıntı: [afu-ai] skill'i.

**EK (20 Eyl 2026):** ikinci kaynak bulundu — **Bash tool'undan geçen her komut**
bir `cygwin-console-helper` + `conhost` doğuruyor, komut bitince öksüz kalıyor
(≈7 pencere/çağrı; 26 → 83 ölçüldü). Bu yüzden: çok sayıda kısa Bash çağrısı
yapma, işi tek çağrıda birleştir; saf Windows işinde PowerShell tool'unu kullan;
**paralel alt-ajan en fazla 3** ve hepsi `subajan.py` üzerinden. Temizlik artık
`Stop` + `SubagentStop` kancalarıyla **otomatik** (settings.json).
