# Orkestrasyon rehberi — kurduktan sonra nasıl çalıştırılır

Bu rehber `isci-terminal` + `afu-ai` + `telegram-mod` üçlüsünü kuran birinin ilk günü içindir.

## 1. Kurulum kontrolü (5 dk)
```bash
git clone https://github.com/pirncedark/AfuClaudePlugin.git
cd AfuClaudePlugin
cp .env.example .env            # Telegram kullanacaksan doldur, yoksa boş bırak
```
Skill'leri bağla (README'deki `ln -s` / `New-Item -SymbolicLink` komutları), ardından üç yardımcıyı kur ve giriş yap:

| Araç | Kontrol | Not |
|---|---|---|
| Codex | `codex --version` | ChatGPT hesabıyla giriş |
| OpenCode | `opencode --version` | Ücretsiz kotası günlük yenilenir |
| Gemini (omp) | `omp --version` | Google hesabıyla giriş |

Hepsi şart değil: sadece Codex bile yeter. `afu-ai` kurulu olanı kullanır.

## 2. İki terminal aç
1. **Koordinatör:** projenin klasöründe `claude` başlat. Modeli Opus seç (`/model`).
2. **İşçi:** ikinci pencerede aynı klasörde `claude` başlat, hemen `/rename işçi` yaz.
3. Koordinatörde: *"ListAgents ile işçiyi bul, tüm sorularını bana SendMessage ile göndermesini söyle."*

## 3. İlk iş
Koordinatöre normal konuş: *"README'ye kurulum bölümü ekle."* Koordinatör:
1. Görev dosyasını yazar (`_gorev/<tarih>/...md`).
2. İşçiye `SendMessage` ile yollar; işçi Codex ile yazar.
3. İşçi soru sorarsa koordinatör cevaplar (sen karışmazsın).
4. Bitince koordinatör logu ve `git log` / `git status` çıktısını doğrular.
5. Eksikse **bir kez** geri yollar; yine olmazsa kendisi yapar.
6. Commit + push görmeden "bitti" demez.

## 4. Telefonla yönetim (isteğe bağlı)
1. `.env` içine bot token'ı ve chat id'ni yaz (BotFather, userinfobot).
2. `pythonw scripts/tg_dinleyici.py` ile dinleyiciyi başlat.
3. Claude'a `afk` yaz → her yanıt Telegram'a düşer, sorular numaralı gelir (`1 / 2`), tek rakamla cevap verirsin.
4. 60 sn cevap vermezsen önerilen seçenek uygulanır, ne yapıldığı tek satır bildirilir. Silme/para/canlı işlerde uygulanmaz, bekler.
5. `afk kapat` → Telegram'a bir şey gitmez.

## 5. Kota dengesi (kısa)
- Ufak iş (özet, tarama, tek satır) → Gemini flash / OpenCode.
- Normal iş (kod, test) → Codex.
- Kritik iş (canlı site, ödeme, güvenlik) → Codex yazar, ikinci bir model inceler.
- Hepsi aynı anda tükenmesin: kullanımı en düşük olana ver, Claude'u en sona sakla.

## 6. Sık sorunlar
| Belirti | Çözüm |
|---|---|
| Koordinatör işçiyi bulamıyor | İşçi oturumunda `/rename işçi`; `ListAgents` çıktısında adı gör |
| Codex yanıt vermeden kesiliyor | Zaman aşımı: aynı oturumu sürdür, yeni tur açma (eski süreç arkada yaşar; `Get-CimInstance Win32_Process \| ? CommandLine -match 'codex'` ile bak) |
| Telegram cevabı gelmiyor | Dinleyici çalışıyor mu? Aynı bota birden fazla süreç `getUpdates` çekiyorsa cevaplar yutulur: tek dinleyici bırak |
| İşçi "yaptım" diyor ama push yok | Normal: koordinatör `git log origin/<dal>` bakar, geri gönderir |
| İşçi yıkıcı git komutu çalıştırdı | Her görevde yasak satırı olduğundan emin ol (skill'deki "Her görevde yazılacak şartlar") |

## 7. Güvenlik
- `.env`, token, şifre asla commit edilmez (`.gitignore` kapsar).
- `bypass_ayar.py ac` yalnız güvendiğin makinede ve depoda.
- Canlı sunucuya yükleme ve `main`'e merge her zaman senin onayınla.

## 8. Gemini kullananlar için
- `afu-ai` Gemini'yi `omp` üzerinden çağırır: flash = hızlı tarama/özet, pro = derin inceleme. Kurulum: `omp` kur, Google hesabıyla giriş yap, `omp --version` ile doğrula.
- Sadece Gemini'n varsa Codex'siz de çalışır: `skills/afu-ai/SKILL.md` içindeki tabloda Codex satırını kullanma, kod işlerini de Gemini'ye ver.
- Gemini kotası bitince OpenCode ya da Codex'e düş; `zaman-asimi-zinciri` skill'i kesilen işi aynı oturumdan devam ettirir.

## 9. Durum çubuğu paneli
Çubuk ayrı depoda: [afu-claude-statusline](https://github.com/pirncedark/afu-claude-statusline) (kota çubukları, bağlam, alt ajan paneli). Kurulum o deponun README'sinde. `afu-ai` canlı ajan durumunu `~/.claude/afu-ajanlar/` altına yazar, çubuk oradan okur.

## 10. Skill listesi
| Skill | Ne işe yarar |
|---|---|
| `isci-terminal` | Koordinatör + işçi terminal düzeni |
| `afu-ai` | Görevi Gemini/Codex/OpenCode'dan uygun olana yaptırır, doğrular |
| `ajan-kopru` | opencode ve codex'i alt ajan olarak çalıştırma, tuzakların çözümü |
| `zaman-asimi-zinciri` | Zaman aşımına uğrayan işi kaldığı yerden sürdürür |
| `isaretle-devret` | Hata yerini 📍 ile işaretleyip ajana devretme |
| `kendin-yap` | Araçla yapılabilen adımı kullanıcıya bırakma |
| `ana-terminal-koordinatoru` | Bilgisayarı kapatmadan önce açık işleri toplayıp push eder |
| `github-push-zinciri` | Depoya push/PR/release düzeni kurma |
| `telegram-mod` | Telefondan iki yönlü yönetim (AFK) |
| `kesif` | İşe başlamadan önce hazır repo/çözüm araştırma |
| `crawl4ai-tara` | Siteyi ücretsiz tarayıp markdown'a çevirme |
| `pencere-firtinasi` | Windows'ta boş terminal pencereleri birikmesini teşhis |
| `responsive-denetim`, `site-hiz-olcum`, `seo-indeks-tuzaklari` | Web sitesi kontrolleri |

## 11. Arkadaşa gönderilecek mesaj
> Claude Code + Codex/Gemini orkestrasyon kiti: https://github.com/pirncedark/AfuClaudePlugin
> 1) Klonla, `install.ps1` (Windows) ya da `./install.sh` çalıştır. 2) `docs/ORKESTRASYON.md` dosyasını sırayla oku: iki terminal aç, birini `/rename işçi` yap. 3) Gemini için `omp` kur ve giriş yap. 4) Durum çubuğu için `afu-claude-statusline` deposunu kur. Telegram ve `.env` isteğe bağlı; kendi token'ını yaz, benimkini isteme.
