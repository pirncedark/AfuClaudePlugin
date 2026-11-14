---
name: responsive-denetim
description: Use when a web page breaks/distorts only at certain viewport widths (kart devasa oluyor, sayfa yatay kayıyor, "belli bir boyutta UI bozuluyor", mobil/tablet arası bozulma) VEYA bir CSS/layout değişikliğini canlıya PUSH etmeden önce tüm cihaz genişliklerinde doğrulamak gerektiğinde. Tetikleyiciler: "responsive bozuk", "bir aralıkta bozuluyor", "telefonda/tablette bozuk", "tüm boyutlarda çalışsın", "viewport", "yatay kaydırma", "grid taşıyor".
---

# Responsive Denetim — çoklu-viewport otomatik bozulma tarama

## Ne işe yarar
Bir yerel HTML sayfasını 8-9 viewport genişliğinde headless Chrome ile açar, her biri için **ekran görüntüsü** alır ve **otomatik bozulma tespiti** yapar (yatay taşma + dev-kart çökmesi). "Belli bir aralıkta UI bozuluyor" tarzı bug'ları göz yerine ölçümle yakalar; push öncesi CI-gibi kapı olur (bozuk varsa exit 1).

## Ne zaman kullan
- Kullanıcı "X boyutunda / bir aralıkta sayfa bozuluyor" dediğinde → **önce tara**, bozuk viewport'u kesinleştir, sonra düzelt.
- `magaza.css`/`style.css` veya herhangi bir layout değişikliğini **FTP push etmeden önce** → regresyon kapısı.
- Şüpheli aralık: iki media-query breakpoint'i arası ("bant"), en sık 768–1024px.

## Kullanım
```bash
python ~/.claude/skills/responsive-denetim/scripts/tara.py <yerel_html> \
       --sel ".shop-card" \
       --w 360,414,600,700,768,850,898,1024,1280 \
       --out <scratchpad/klasor>
```
- `--sel`: kart/kutu seçicisi (dev-kart tespiti için). magaza.html → `.shop-card`. Bilmiyorsan atla, sadece yatay taşma bakılır.
- Çıktı: konsolda her viewport `ok`/`BOZUK` + sebep; `rapor.json`; **bozuk viewport'ların `ss_<W>.png`'i** tutulur (Read tool ile incele). Temizler silinir.
- **Çıkış kodu: 0=temiz, 1=bozuk var.** Push script'inden önce çağır.

Rel yollar (css/img) korunsun diye araç, hedef HTML'in **kendi klasöründe** geçici bir kopya üretip siler — sayfayı ayrı yere kopyalama.

## Kök-neden kütüphanesi (bir aralıkta bozulmanın klasik sebepleri)
| Belirti | Kök neden | Çözüm |
|---|---|---|
| Tek kart devasa, sayfa yatay kayar (2 breakpoint arası) | Bir flex-item'in `min-width:auto`'su içeriğe göre şişiyor; `nowrap` yatay şerit taşırıyor | O item'a `min-width:0; max-width:100%`. Koruma zincirini **flex'in başladığı** breakpoint'te ver, mobil breakpoint'te değil — [[magaza_flex_item_tasma_araligi]] |
| `calc(100%/N)` kart genişliği patlıyor | `100%` şişmiş konteynerden hesaplanıyor | Konteyner genişliğini `min-width:0` ile kilitle |
| Sadece bir bantta bozuk | İki `@media` arası hiçbir kural geçerli değil (korumasız bant) | Kuralı doğru aralığa yay; breakpoint boşluğu bırakma |

## Yaygın hatalar
- **Göz kararı "düzeldi" demek.** Ölç. Bozukluk 40px'lik bir bantta olabilir, gözden kaçar.
- **Sadece 375 ve 1440 test etmek.** Bug ARA aralıkta; breakpoint'lerin ±birkaç px'ini ve ortalarını tara (768/850/898 gibi).
- **Canlı URL'yi taramak.** Yerel dosyayı tara (henüz push edilmemiş değişiklik). Push SONRASI canlı teyit ayrı adım.

## Tuzaklar
- Chrome yolu otomatik bulunur; bulunamazsa `CHROME=/yol/chrome.exe` env ver (Edge de olur).
- Google/Meta sitelerine değil — yalnızca kendi yerel dosyalarımıza (otomasyon yasağı bunları kapsamaz).
- Araç salt-okur; hedef dosyayı değiştirmez (geçici kopya üretir + siler).

Doğrulama: bu araç `magaza.html`'in fix'siz halinde 850/898px'i BOZUK (exit 1), fix'li halinde 8 viewport'u TEMİZ (exit 0) olarak doğru işaretledi.
