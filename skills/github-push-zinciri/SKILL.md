---
name: github-push-zinciri
description: Use when bir depoya GitHub push/PR/release düzeni kurulacaksa veya push öncesi sıra soruluyorsa — "push sırası", "pre-commit kur", "gitleaks", "commit kuralı", "release-please", "CI kalite", "dal koruması", "depoyu kusursuz yap", "push zinciri", "başka depoya da kur". Ajanlar (codex/opencode) AfuNöbet üzerinden bir git deposunda iş yapacaksa da.
---

# GitHub Push Zinciri

## Özet
Yerel kancalar ile CI aynı dosyadan (`.pre-commit-config.yaml`) çalışır; push asla doğrudan `main`'e gitmez; sürüm release-please PR'ı ile çıkar. Kanıtlı kalıp: `<kalıp-klasörü>/github-push/` (ilk uygulama AfuDM, 27 Eyl 2026). Örnek alınan depo: astral-sh/uv.

## Push sırası (her değişiklik)
1. Dal aç (`fix/…`, `feat/…`, `chore/…`) — `main`'de çalışma yok.
2. Commit → pre-commit kancaları: biçim, gitleaks, commitizen (Conventional Commits mesajı).
3. `git pull --rebase origin main`
4. Push → pre-push kancası testleri koşar.
5. PR → CI (`kalite.yml`, Windows + Ubuntu) yeşil.
6. Squash merge → release-please sürüm PR'ı açar → onaylanınca tag + CHANGELOG.

## Araç seti (sürüm/SHA'yı kurulum günü `gh api` ile tazele)
| Aşama | Araç |
|---|---|
| Kanca çerçevesi | pre-commit (pre-commit-hooks v6) |
| Sır taraması | gitleaks |
| Commit mesajı | commitizen (commit-msg aşaması) |
| Workflow denetimi | actionlint + zizmor |
| Sürüm | googleapis/release-please-action |
| Sağlık puanı | ossf/scorecard (önce/sonra) |

SHA bulma: `gh api repos/<o>/<r>/releases/latest --jq .tag_name` → `gh api repos/<o>/<r>/commits/<tag> --jq .sha`. Codex/opencode sandbox'ında internet yok: SHA'ları görev dosyasına Claude yazar.

## Kurulum akışı (AfuNöbet ile)
1. Görev dosyası yaz (şablon: `_kalip/github-push/GOREV_BIRLESIK.md`; son satırı `SONUC:` istesin), `afunobet calistir "Read <tam yol> …" --cwd <tam yol> --ajan codex` (denetimde `--ajan opencode`). Global `afunobet tercih` KULLANMA.
2. `calistir` çıktısının ilk satırı job kimliğidir (`is_…`). Bitişi arka planda bu döngüyle bekle, sonra ikinci işi ver:
   ```bash
   J=is_…; cd <AfuNobet-klasörü>
   while python -c "import sqlite3,sys;r=sqlite3.connect('state.db').execute('select status from jobs where job_id=?',(sys.argv[1],)).fetchone();sys.exit(0 if r and r[0]=='RUNNING' else 1)" $J; do sleep 30; done
   tail -c 1200 logs/job_${J}_*.log   # SONUC satırı + hata metni birlikte
   ```
   Başarı yalnız `SONUC: TAMAM …` satırı **ve** `git log main..<dal>` commit gösterirse.
3. Sandbox git commit atamaz → Claude kendi kabuğunda, ajanın worktree'sinde: `git switch -c chore/push-zinciri && git add -A && git commit`.
4. İnternetli kabukta gerçek doğrulama: `python -m pip install pre-commit && python -m pre_commit run --all-files`.
5. Biçim kancalarının depo geneline yaptığı düzeltmeleri `git checkout -- .` ile geri al; ayrı `style:` PR'ı olarak at.
6. Denetim görevi (şablon: `GOREV_DENETIM2.md`) — gerçek pre-commit çıktısını görevin içine yaz.
7. Push + PR + dal koruması + Scorecard: kullanıcıya sor, sonra yap.

## Tuzaklar (hepsi yaşandı)
| Belirti | Gerçek | Çözüm |
|---|---|---|
| Denetim, iş bitmeden başladı | `afunobet calistir` kuyruğa atıp hemen döner | job `status` RUNNING değilken ikinciyi ver |
| Codex'e verilen iş opencode'a düştü | `afunobet tercih` tüm oturumlarda ortak | `--ajan` ile iş başına seç; başka oturum aynı depoda iş veriyorsa önce SendMessage ile işi devral |
| Job COMPLETED ama dal yok | durum ≠ sonuç | log'daki `SONUC:` satırı + `git log main..<dal>` ile doğrula |
| `SONUC: HATA … Git metadata yazma izni yok` | sandbox `.git`'e yazamaz | commit'i Claude atar; görevde "commit yapma" de |
| `main`'de sahipsiz değişiklik | ajan `--worktree-yok` ile ana ağaçta çalıştı | önce WIP dalına commit'le, `main`'i temizle |
| zizmor her commit'i blokluyor | eski workflow'larda yüzlerce bulgu | CI'da `SKIP=zizmor`, eski workflow'ları ayrı PR'da SHA'ya sabitle |
| .bat dosyaları bozuldu riski | mixed-line-ending | `.gitattributes`: `*.bat/*.cmd/*.ps1 eol=crlf` |
| Hata görünmedi | `grep SONUC` hata satırını eledi | log'un son ~1200 karakterini tam oku |
| Yeni `kalite` CI işi eski depoda kırmızı | CI'da `pre-commit run --all-files` eski dosyaların boşluk/satır sonu sorunlarına takılır | CI'da yalnız değişen dosyalar: `fetch-depth: 0` + `shell: bash` + `FROM_REF: ${{ github.event.pull_request.base.sha \|\| github.event.before }}` → `pre-commit run --from-ref "$FROM_REF" --to-ref HEAD`; tüm depo temizliği ayrı `style:` PR'ı |
| Ubuntu işinde `No module named 'winreg'` | uygulama yalnız Windows | test adımına `if: runner.os == 'Windows'`; pre-commit iki sistemde kalsın |
| release-please tüm geçmişi CHANGELOG'a döktü, sürüm yanlış (2.8.0) | etiketler `v2.7.4`, release-please `<paket>-v2.7.4` arıyor | config'e `"include-component-in-tag": false` |
| Sürüm dosyası güncellenmedi | `extra-files` generic güncelleyici işaret ister | satırın sonuna `# x-release-please-version` |
| `GitHub Actions is not permitted to create or approve pull requests` | depo ayarı kapalı | Settings → Actions → "Allow GitHub Actions to create and approve pull requests" (kullanıcı onayıyla) |
| Dosya kancaları her commit'te 2 kez koşuyor | `default_stages` yok → commit-msg aşamasında da koşar | config başına `default_stages: [pre-commit]` |
| style PR'ı Markdown görünümünü bozar | trailing-whitespace iki boşluklu satır kırmasını siler | `args: [--markdown-linebreak-ext=md]`; `git diff -w --ignore-blank-lines --ignore-cr-at-eol` boş olmalı |
| zizmor bilgi notunda bile kırmızı | çıkış kodu her bulguda ≠0 | hook `args: [--min-severity=medium]`; eski workflow'lar temizlenince CI'daki `SKIP=zizmor` kaldır |
| Ajan `workflow_call.secrets` altına `GITHUB_TOKEN` ekledi | ayrılmış ad; zaten otomatik gelir | `secrets: inherit` yerine hiçbir şey geçirme; çağrılan zincirde her işin yetkisi ≤ çağıranın verdiği (yoksa startup_failure) |
| Tüm-depo koşusundan sonra `git add -A` başka dosyaları da aldı | `--all-files` biçim düzeltmelerini çalışma ağacına yazar | tüm-depo koşusunu ayrı worktree'de yap; commit öncesi `git diff --cached --name-only` kapsamını kontrol et |
| `git show origin/main:yol` "ambiguous argument" | Git Bash yol dönüştürmesi | `export MSYS_NO_PATHCONV=1`; Windows git'e `/tmp/...` verme, `C:/...` ver |
| Boşluk PR'ında tek bir UI testi kaldı | zamanlamaya duyarlı test | ilgili dosyalar değişmediyse `gh run rerun <id> --failed` |
| actionlint Windows'ta geçer, Ubuntu'da kırılır | shellcheck yalnız Linux runner'da; bilgi notları (SC2012) hata sayılır | hook `args: [-ignore, 'SC[0-9]+:info:']`; yerelde doğrulamak için `pip install shellcheck-py` |
| Ajan env'e `GITHUB_RUN_NUMBER: ${{ github.run_number }}` yazdı | `GITHUB_` önekli adlar ayrılmış | `RUN_NUMBER` gibi önek siz ad kullan |
| Windows CI işi kırılır | `run: SKIP=zizmor pre-commit …` bash sözdizimi, Windows'ta varsayılan kabuk pwsh | `env: {SKIP: zizmor}` bloğu kullan |
| Kancalar kurulunca sürüm commit'i reddedildi | commitizen `release: vX` kabul etmez | `pre-commit install`'dan ÖNCE sürüm akışını `chore(release): vX` biçimine çevir (AfuDM: afudm-surum-yayinla güncellendi; `Merge …` geçer) |
| Güvenlik bulguları herkese açık oldu | PR açıklaması public depoda | önce `gh repo view --json visibility`; public ise bulgu sayısı/yerini PR'a, commit'e, belgeye yazma |
| Tam test paketi takıldı, iş HATA | UI testi (`ui_startup_test`) başsız ortamda bekliyor | ajan yalnız hızlı çevrimdışı testleri (`scripts/pre_push_test.ps1`) koşsun |
| Mevcut SECURITY.md silindi | ajan "kısa yaz"ı üzerine yazma sandı | var olan belgeye EKLE, üzerine yazma |

## Yeni depoya kopyalama
`_kalip/github-push/` içindeki görev dosyalarında depo yolu, test komutu ve manifest sürümünü (son tag) değiştir; akışı baştan uygula. AfuDM'de özellik dondurması var: yalnız altyapı dosyaları.
