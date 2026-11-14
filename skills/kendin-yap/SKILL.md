---
name: kendin-yap
description: Kullanıcıya "şunu aç / şuna bas / şu linke git / şunu kopyala / şu komutu çalıştır / yeniden giriş yap" demeden ÖNCE tetikle. Claude'un bilgisayarda kendisi yapabileceği her adımı (tarayıcıda tıklama, Console/panel ayarı, exe açıp deneme, dosya/komut, GitHub) kendisi yapar; kullanıcıya yalnız gerçekten insan gereken adımı (şifre, 2FA, telefonda fiziksel dokunuş, para/geri alınamaz onay) bırakır. Tetikleyiciler — "sen yap", "kendin yap", "benim yapmamı isteme", "tıkla", "bas", "aç", "dene", ve Claude'un yanıtında kullanıcıya adım listesi yazmak üzere olduğu her an.
---

# Kendin yap — kullanıcıya iş bırakma

Kullanıcı (9 Kas 2026): "Senin yapabileceğin işleri bana yaptırıyorsun." Kural: **önce dene, olmazsa devret.**

## Karar sırası (kullanıcıya adım yazmadan önce)
1. Bu adımı bu bilgisayarda bir araçla yapabilir miyim? → Evet ise YAP, sonra kanıtla bildir.
2. Yalnız şu durumlarda kullanıcıya bırak:
   - Şifre / 2FA / SMS kodu / CAPTCHA girmek gerekiyor.
   - Fiziksel cihaz (telefona dokunmak, USB takmak).
   - Para, canlı fatura, silme gibi geri alınamaz işlem (önce sor).
   - Araçla 2 farklı yol denendi, ikisi de başarısız.
3. Bırakırsan: neyi denediğini + neden olmadığını tek satır yaz, kullanıcıya yalnız o tek adımı ver.

## Araç rafı (hangi iş → hangi yol)
| İş | Yol |
|---|---|
| Web paneli (Google Cloud, GitHub ayarı, site paneli) — kullanıcının hesabı gerekir | Kullanıcının **Chrome'u** (oturumlar açık): `Start-Process chrome.exe "<url>&authuser=<e-posta>"` → ekran görüntüsü → tıkla |
| Web — oturum gerekmez / hesapsız erişim yeterli | Playwright MCP (`browser_navigate`, `browser_snapshot`, `browser_click`) |
| Masaüstü uygulamayı açıp deneme | `Start-Process <exe>` → `Get-Process ... Responding` → pencere ekran görüntüsü |
| Ekranda tıklama / yazma | PowerShell: `CopyFromScreen` ile görüntü → Read ile bak → `SetCursorPos` + `mouse_event(2/4)`; yazı için `SendKeys` |
| Kod / commit / PR / release | İşçi terminal (CLAUDE.md "İşçi terminale ver") — kullanıcıya değil |
| GitHub ayarı (Pages, secret, repo) | `gh api` / `gh secret set` / `gh repo edit` |
| Dosya / ayar / servis | Bash / PowerShell |

## Ekranda tıklama kalıbı (Windows)
```powershell
Add-Type -AssemblyName System.Drawing
$bmp=New-Object Drawing.Bitmap 2560,1440; [Drawing.Graphics]::FromImage($bmp).CopyFromScreen(0,0,0,0,$bmp.Size)
(New-Object Drawing.Bitmap $bmp,1280,720).Save("$scratch\ekran.png")   # yarı boyut → koordinatı 2 ile çarp
Add-Type 'using System;using System.Runtime.InteropServices;public class K{[DllImport("user32.dll")]public static extern bool SetCursorPos(int x,int y);[DllImport("user32.dll")]public static extern void mouse_event(int f,int x,int y,int d,int e);}'
[K]::SetCursorPos(X,Y); [K]::mouse_event(2,0,0,0,0); [K]::mouse_event(4,0,0,0,0)
```
- Her tıklamadan sonra yeni ekran görüntüsüyle sonucu kontrol et.
- Kullanıcı oyundayken / tam ekrandayken tarayıcı açma (hafıza: gflow-oyun-odak).

## Örnek (9 Kas, AfuDesk)
- YANLIŞ: "Linki kendi hesabınla aç, Publish app'e bas" → kullanıcıya iş.
- DOĞRU: Chrome'da hesap açık → Claude açtı, Branding'i kontrol etti, eksik linkleri işçiye yazdırdı, yayınlamayı kendisi yapacak.
- DOĞRU: AfuDesk exe'yi açtı, Google girişini Chrome'da kendisi tıklayıp tamamladı, ekran görüntüsüyle "Bilgisayarlarım" kanıtladı.
