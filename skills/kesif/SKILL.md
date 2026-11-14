---
name: kesif
description: İşe BAŞLAMADAN ÖNCE internetten en iyi repo/agent/kütüphane/yöntemi tarayan ön-keşif birimi. Yeni bir özellik, araç, entegrasyon, otomasyon veya "X yapalım / X kuralım / X ekleyelim" gibi bir işe girmeden önce tetiklenir. Amaç: tekerleği yeniden icat etmeden, işin EN GELİŞMİŞ ve en fonksiyonlu halini kurmak. "keşif", "araştır", "en iyisi nasıl", "hazır çözüm var mı", "repo bul" deyince de çağrılır.
---

# Keşif Birimi — İşten Önce Ön-Araştırma

## Amaç
Herhangi bir yeni işe (özellik, araç, entegrasyon, otomasyon, altyapı) girmeden ÖNCE:
"Bu işi zaten en iyi kim yapmış? Hangi repo, hangi agent, hangi kütüphane, hangi yöntem
en gelişmiş ve en fonksiyonlu sonucu verir?" sorusunu cevaplar.

Böylece sıfırdan yazmak yerine olgun çözümlerin üstüne inşa ederiz.

## NE ZAMAN TETİKLENİR
- Kullanıcı yeni bir şey kurmak/eklemek/yapmak istediğinde ("X yapalım", "X kuralım", "X ekleyelim")
- Bilinmeyen/yeni bir teknoloji, entegrasyon veya API söz konusuysa
- "En iyisi nasıl olur", "hazır çözüm var mı", "araştır" dendiğinde

## NE ZAMAN ATLANIR
- Küçük, rutin, iyi bilinen bakım işleri (bir metni değiştir, bir bug'ı düzelt, deploy et)
- Kullanıcı "araştırma, direkt yap" dediğinde
- Proje içi DEĞİŞMEZ KURALLAR zaten yöntemi belirlemişse (önce `degismez-kurallar` skill'ine bak)

## ADIMLAR

### 1. İşi tek cümlede tanımla
Ne yapılacağını net yaz. Anahtar kelimeleri çıkar (İngilizce + Türkçe).

### 2. Kendi hafızanı tara (İLK — internetten önce)
- `MEMORY.md` içinde bu işe benzer bir kayıt / çözüm / tuzak var mı?
- Kurulu 40+ skill ve subagent'lar arasında bu işi zaten yapan var mı? (yukarıdaki liste)
- Varsa: tekerleği yeniden icat etme, mevcut çözümü kullan/genişlet ve burada dur.

### 3. İnternet taraması (WebSearch + WebFetch)
**Güncel nabız için `last30days` skill'ini kullan** (kurulu): son 30 günde Reddit/X/HN/
YouTube'da bu konu hakkında gerçek insanlar ne diyor, hangi araç yükselişte — özellikle
"hangi kütüphane/araç seçilmeli" kararlarında topluluk sinyali verir. Reddit/HN/GitHub
sıfır yapılandırmayla çalışır.

Paralel olarak şunları ara:
- **En iyi repolar:** `<konu> best library github`, `<konu> github stars`, `awesome <konu>`
- **Hazır agentler/MCP:** `<konu> AI agent`, `<konu> mcp server`, `<konu> claude skill`
- **Güncel yöntem:** `<konu> best practices 2026`, resmi dokümantasyon
- GitHub için gerekirse `gh search repos "<konu>" --sort=stars --limit 10`

Her aday için not al: yıldız sayısı, son commit tarihi (aktif mi?), lisans, ne işe yaradığı.

### 4. Karşılaştır ve ele
- Terk edilmiş (2+ yıl commit yok) veya lisansı uygun olmayanları ele.
- En fazla 2-3 güçlü adayı bırak.
- Her biri için: artılar, eksiler, projeye uyumu (Windows/PHP/Python/Phaser stack).

### 5. RAPOR + ÖNERİ
Kısa bir özet sun (uzun döküm değil):

```
🔍 KEŞİF: <iş>
─────────────────────────
En iyi 3 yaklaşım:
1. <ad> — ⭐<yıldız>, son: <tarih> — <tek satır>
2. ...
3. ...

TAVSİYEM: <hangisi ve neden — 1-2 cümle>
Uygulama planı: <3-5 madde>
```

Uzun/kaynaklı versiyonu istenirse `outputs/kesif_<konu>_<tarih>.md` altına yaz.

### 6. Onay al, sonra işe başla
"Bununla ilerleyeyim mi?" diye kısaca sor. Onay gelince asıl işe (gerekirse ilgili
diğer skill/agent'la) başla. Kullanıcı zaten "otomatik ilerle" demişse tavsiyeni uygula.

## KURALLAR
- Önce hafıza/mevcut skiller, sonra internet. Var olanı tekrar yazma.
- Terk edilmiş repoyu önerme; aktiflik ve lisans şart.
- Rapor KISA olsun; ham arama dökümünü yapıştırma.
- Güvenlik: rastgele repoyu körlemesine `pip install`/`npm install` etme — önce değerlendir.
- Proje DEĞİŞMEZ KURALLARINI ihlal eden bir çözümü önerme.
