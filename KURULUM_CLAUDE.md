# Claude için kurulum talimatı / Install instructions for Claude

> **Kullanıcıya:** Bu dosyanın içeriğini ya da bu dosyanın linkini Claude Code'una (veya Codex'ine) yapıştır ve "bunu kur" de.
> **To the AI agent reading this:** you are installing the AfuClaudePlugin kit on the user's machine. Follow the steps in order, run the verification command after each step, report results in plain language, and stop at any step marked 🙋 (a human must act). Do not edit anything outside the paths named here. Do not run destructive git commands. Do not ask the user for tokens/passwords; tell them where to put their own.

Repo: https://github.com/pirncedark/AfuClaudePlugin (public, MIT-style personal kit)

## 0. Önce sor (tek mesajda)
1. İşletim sistemi: Windows mu, Mac/Linux mu? (PowerShell ya da bash seçimi)
2. Hangi araçlar kurulu/giriş yapılı: Codex, Gemini (`omp`), OpenCode? (hepsi şart değil, biri yeter)
3. Telegram'dan yönetmek ister mi? (isteğe bağlı)
4. Durum çubuğu paneli ister mi?

## 1. Ön koşullar — doğrula
```bash
git --version && python --version && claude --version
```
Eksik olan varsa kullanıcıya hangisinin eksik olduğunu söyle ve kurulumunu öner; kendi başına sistem geneli program kurma, önce sor.
İsteğe bağlı: `codex --version`, `omp --version`, `opencode --version`.

## 2. Repoyu indir
Kullanıcının proje klasörlerinin dışında, bir "araçlar" klasörü seç (ör. `~/afu-kit`):
```bash
git clone https://github.com/pirncedark/AfuClaudePlugin.git ~/afu-kit/AfuClaudePlugin
cd ~/afu-kit/AfuClaudePlugin
```

## 3. Skill'leri kur (Claude Code + Codex birlikte)
- Windows: `.\install.ps1`  (yalnız biri için: `-Target claude` ya da `-Target codex`)
- Mac/Linux: `./install.sh`  (`./install.sh claude` ya da `./install.sh codex`)

Doğrula (15 skill görmelisin):
```bash
ls ~/.claude/skills | head -20      # Claude Code
ls ~/.agents/skills | head -20      # Codex
```
Mevcut aynı adlı skill'lerin üzerine yazıldığını kullanıcıya söyle (betik kopyayı yeniler).

## 4. Yardımcı modeller (kullanıcının sahip olduğu kadar)
- **Codex:** `codex --version`; giriş yoksa 🙋 kullanıcı `codex login` yapar (tarayıcıda hesabıyla).
- **Gemini:** `omp` kur, 🙋 Google hesabıyla giriş, sonra `omp --version`.
- **OpenCode:** `opencode --version`; 🙋 giriş gerekirse kullanıcı yapar.
Hiçbiri yoksa sadece Claude ile de çalışır; orkestrasyon yardımcı model olmadan eksik kalır, bunu kullanıcıya söyle.

## 5. Orkestrasyon (koordinatör + işçi)
Skill'ler kuruldu; kullanım için iki Claude Code oturumu gerekir:
1. 🙋 Kullanıcı ikinci bir terminal açıp proje klasöründe `claude` başlatır ve `/rename işçi` yazar.
2. Bu (birinci) oturum koordinatördür. Koordinatör `isci-terminal` skill'ini okuyup uygular: `ListAgents` ile `işçi` oturumunu bulur, görevleri `SendMessage` ile gönderir.
3. Koordinatör işçiye ilk mesajı yazar: "Tüm sorularını bana SendMessage ile gönder."
Doğrula: `ListAgents` çıktısında `işçi` satırı görünmeli. Görünmüyorsa kullanıcıdan adı kontrol etmesini iste.
Ayrıntı: `docs/ORKESTRASYON.md` ve `skills/isci-terminal/SKILL.md`.

## 6. Durum çubuğu (kullanıcı istediyse)
Gereken: Python 3 + bash (Windows'ta Git Bash).
```bash
bash statusline/install.sh        # Windows PowerShell: .\statusline\install.ps1
```
Betik mevcut dosyaları yedekler ve `~/.claude/settings.json` içinde yalnız `statusLine` ve `subagentStatusLine` anahtarlarını yazar. Doğrula: `grep statusLine ~/.claude/settings.json`. 🙋 Çubuğun görünmesi için Claude Code yeniden başlatılmalı. Geri almak: o iki anahtarı sil.

## 7. Telegram (kullanıcı istediyse; yoksa atla)
1. 🙋 Kullanıcı `@BotFather`'dan bot oluşturur, token'ı; `@userinfobot`'tan chat id'sini alır. **Sen token'ı isteme, yazma; kullanıcı kendi `.env` dosyasına yazar.**
2. `cp .env.example .env` (Windows: `Copy-Item .env.example .env`), sonra 🙋 kullanıcı `MCP_TELEGRAM_TOKEN` ve `MCP_TELEGRAM_CHAT_ID` değerlerini doldurur.
3. `pip install requests`
4. Kullanım: `skills/telegram-mod/SKILL.md`. Tek dinleyici çalışmalı (`scripts/tg_dinleyici.py`).

## 8. Bitirme kontrolü — kullanıcıya şunu raporla
- [ ] Skill'ler kuruldu (sayı: 15)
- [ ] Hangi yardımcı modeller çalışıyor (codex / gemini / opencode)
- [ ] `işçi` oturumu `ListAgents`'te görünüyor mu
- [ ] Durum çubuğu kuruldu mu (yeniden başlatma gerekli)
- [ ] Telegram kuruldu mu / atlandı mı
Hata olursa ham hata çıktısını kısa bir özetle birlikte göster; tahminle "oldu" deme.

## Güvenlik
- `.env`, token, şifre asla commit edilmez ve sohbete yazdırılmaz.
- `scripts/bypass_ayar.py ac` izin sormayı kapatır: kullanıcı açıkça isterse ve yalnız güvendiği makinede.
- Canlı sunucuya yükleme ve `main`'e merge her zaman kullanıcı onayıyla.
