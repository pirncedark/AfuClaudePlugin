---
name: isci-terminal
description: Koordinatör (Claude Opus) + işçi terminal düzeni — verilen her işi ayrı bir "işçi" Claude Code oturumuna SendMessage ile gönderir, işçi kodu Codex ile yazar (gerekirse Gemini/OpenCode'u kullanır), koordinatör işçinin sorularını cevaplar, bitince sonucu doğrular, eksikse BİR kez geri gönderir, yine olmazsa kendisi yapar; commit + push olmadan iş bitmiş sayılmaz. "işçiye ver", "işçi terminal", "koordinatör", "codex'e yaptır", "orkestra", "işi dağıt" deyince tetiklenir.
---

# İşçi Terminal — Koordinatör + İşçi düzeni

## Roller
| Rol | Kim | Ne yapar |
|---|---|---|
| **Koordinatör** | Ana Claude Code oturumu (Opus 5.5) | Görevi yazar, işçiye yollar, sorularını cevaplar, sonucu doğrular. Kodu kendisi yazmaz. |
| **İşçi** | Ayrı bir Claude Code oturumu, adı `işçi` (ya da `iş`) | Kodu Codex ile yazar; test/tarama için Gemini veya OpenCode'u çağırır; commit + push yapar. |
| **Yardımcılar** | Codex, Gemini, OpenCode CLI'ları | `afu-ai` skill'i ile çağrılır (bkz. `skills/afu-ai`). |

Amaç: koordinatörün (pahalı) kotasını korumak. Koordinatör planlar ve doğrular; yazma işi
işçi + Codex'te kalır.

## Gerekenler
- İki Claude Code oturumu açık: biri koordinatör, biri **adı `işçi`** olan (`/rename işçi`).
- Koordinatörde `ListAgents` ve `SendMessage` araçları kullanılabilir olmalı.
- `codex`, (isteğe bağlı) `omp`/Gemini ve `opencode` kurulu ve giriş yapılmış (bkz. `afu-ai`).
- Depo GitHub'a push edebilmeli (`gh auth status`).

## Akış
1. **İşçiyi bul:** `ListAgents` → adı `işçi` olan satırı seç. Bulamazsan kullanıcıya sor, tahmin etme. (Kendi alt ajanını `Agent` ile AÇMA; iş işçi oturumuna gider.)
2. **Görevi dosyaya yaz:** `_gorev/<YYYY-MM-DD>/<is-adi>.md` — amaç, ÇALIŞACAĞI DOSYALAR (tam yol), ilgili satır/fonksiyon, "bu listenin dışına yazma", başarı ölçütü, doğrulama komutu.
3. **Tek satırla gönder:** `SendMessage` → `Görev: <dosya yolu>. Bitince kontrol logunu yaz ve bana SendMessage ile haber ver.`
4. **Şartları görevde yaz** (aşağıdaki "Her görevde" listesi).
5. **İşçinin sorularını cevapla** (aşağıda).
6. **Bitince doğrula** (aşağıda). Eksikse geri gönder.
7. **Push olmadan bitmedi:** commit hash + `git status` temiz + commit `origin/<dal>` içinde. Uygulamaysa release/tag.

## İşçinin sorularına cevap verme
İşçi kullanıcıya değil **koordinatöre** sorar (`SendMessage`). Koordinatör:
- Cevabı konuşma bağlamından, görev dosyasından ve depodan bulur; kısa ve net cevaplar.
- Yalnız şu kararlar kullanıcıya gider: **silme, para/ödeme, canlı (production) değişiklik, geri alınamaz işlem**.
- Telegram AFK modu açıksa kullanıcının sorusu telefona düşer (bkz. aşağıdaki bölüm); cevap gelince işçiye aynen iletilir.
- Cevap veremiyorsa "bilmiyorum" der ve kullanıcıya sorar; uydurmaz.

İşçi ilk açıldığında koordinatör ona bir kez yazar: *"Tüm sorularını bana SendMessage ile gönder, kullanıcıya sorma."*

## Doğrulama ve geri gönderme döngüsü
Koordinatör işçinin "tamam" demesine güvenmez:
1. Kontrol logunu okur (komut + **ham çıktı** + hash/link).
2. Bir kez kendisi ucuz bir doğrulama koşar (`git log`, `gh pr view`, test çıkış kodu, dosya var mı).
3. **Eksik / yanlışsa → işçiye BİR kez geri gönderir:** neyin eksik olduğunu somut yazar ("test X kırmızı, log satırı Y").
4. **İkinci denemede de olmazsa → koordinatör kendisi yapar** (ya da kullanıcıya durumu söyler). Sonsuz döngü yok.
5. Sayaç: görev dosyasının sonuna `deneme: 1/2` yaz.

## Her görevde yazılacak şartlar
- ÇALIŞACAĞIN DOSYALAR: tam yollar. Liste dışına yazma; gerekirse dur ve sor.
- Yıkıcı git YASAK: `git restore`, `checkout --`, `reset`, `clean`, `stash`, `rebase`, `amend`, `push --force`.
- Bitince: kontrol logu + koordinatöre `SendMessage`.
- Bitince projenin `GUNLUK.md` dosyasına tek satır: `YYYY-MM-DD · ne yapıldı · sonuç`.
- Commit + push dal üzerine zorunlu; `main`'e merge ve canlıya yükleme yalnız kullanıcı isterse.

## Paralel iş
İşçi meşgulken yeni görevi "bitince başla" diye sıraya koyma. Görevde şunu yaz: *"Beklemeden ayrı bir Codex süreciyle şimdi başlat."* Aynı dosyaya dokunan işlerde çakışma kontrolü iste. Aynı anda en fazla ~6 yardımcı süreç.

## İş sınıfı → kim yapar
| Sınıf | Örnek | Yapan |
|---|---|---|
| Ufak | tek satır düzeltme, özet, tarama | Gemini flash / OpenCode (koordinatör devretmeden kendisi de yapabilir) |
| Normal | kod yazma, test | Codex (işçi) |
| Kritik | canlı site, ödeme/fatura, güvenlik, mimari | Codex yazar + bağımsız ikinci inceleme (`agent-skills:code-reviewer` veya Gemini pro) |

Kural: görevi devretmek işin kendisinden çok token yakıyorsa (3 satırlık iş için uzun görev dosyası) koordinatör kendisi yapar.

## Telegram AFK modu ile birlikte
`skills/telegram-mod` açıkken ("afk" / "telegram mod"):
- Koordinatörün her yanıtı Telegram'a gider; kullanıcı telefondan yazınca mesaj koordinatöre ulaşır.
- İşçinin kullanıcıya gitmesi gereken sorusu koordinatör üzerinden Telegram'a numaralı seçenekle atılır (`1 = ... / 2 = ...`), kullanıcı tek rakamla cevaplar, koordinatör işçiye iletir.
- **60 sn kuralı:** cevap gelmezse önerilen seçenek uygulanır ve karar + geri alma yolu tek satır bildirilir. Silme/para/canlı işlerde uygulanmaz, beklenir.
- `afk kapat` deyince mod kapanır; kapalıyken Telegram'a hiçbir şey gitmez.
