---
name: seo-indeks-tuzaklari
description: >-
  Use when Google Search Console reports indexing/coverage problems — "blocked by
  robots.txt but indexed", "discovered/crawled not indexed", "page with redirect",
  "alternate page with canonical" — or when a Coverage/Kapsam export needs
  interpreting, or before changing robots.txt / noindex / .htaccess SEO headers.
  Tetikleyiciler — "Search Console", "Coverage raporu", "dizine eklenmedi",
  "indekslenmiyor", "robots.txt", "noindex", "sitemap", "Google sayfayı görmüyor",
  "kapsam sorunu".
---

# SEO İndeks Tuzakları — robots.txt / noindex / sitemap tutarlılığı

## Ne işe yarar
Search Console kapsam uyarılarının **gerçek sebebini** bulur. Bu uyarıların
çoğu içerik sorunu değil, birbiriyle çelişen iki yönerge sorunudur.

## ⛔ En önemli kural: Disallow ≠ noindex
**`Disallow` "dizine ekleme" demek DEĞİL, "bakma" demek.**

Google bir sayfayı çekemezse `noindex`'i de **göremez** — başka sitelerden gelen
linklerle sayfayı yine dizine ekler. Sonuç: *"Robots.txt tarafından engelleniyor
olsa da dizine eklendi."*

| İstediğin | Doğru yol | YANLIŞ |
|---|---|---|
| Dizine girmesin | Taramaya **izin ver** + `noindex` (meta veya `X-Robots-Tag`) | `Disallow` |
| Hiç taranmasın (bant/gizlilik) | `Disallow` (ama dizine girebilir) | — |
| İkisi birden | **Mümkün değil.** noindex'i gördürmek için tarama şart | `Disallow` + `noindex` |

## Ne zaman kullan
- Search Console'dan Coverage/Kapsam raporu geldiğinde
- robots.txt, `noindex` veya `.htaccess` SEO başlığı değiştirmeden **önce**
- "Google sayfamı görmüyor / indekslemiyor" şikayetinde

## Araç
```bash
python ~/.claude/skills/seo-indeks-tuzaklari/scripts/indeks_denetim.py https://site.com \
       --sitemap-ornek 25
```
Kontrol ettiği: Disallow'lu ama 200 dönen uçlar · noindex'li ama engellenmiş
sayfalar · sitemap ölü linkleri · yönlendirme+Disallow çakışması.
**Çıkış kodu 0=temiz, 1=sorun** → push öncesi kapı olarak kullan.

Doğrulandı: düzeltme öncesi robots.txt'te `blog.php`, `api_lib.php`, `/2_turkish/`
sorunlarını yakaladı; düzeltme sonrası TEMİZ verdi.

## Uyarı → gerçek sebep → çözüm

| Search Console uyarısı | Gerçek sebep | Çözüm |
|---|---|---|
| **Engelleniyor olsa da dizine eklendi** | `Disallow` + sayfa 200 dönüyor. Google noindex'i göremiyor | Disallow **kaldır**, `X-Robots-Tag: noindex` ver |
| **Keşfedildi - dizine eklenmedi** | Tarama bütçesi. Google biliyor ama sıraya koymuş | Genelde **hata değil**, bekle. Toplu sayfa eklendiyse normal |
| **Tarandı - dizine eklenmedi** | İçerik zayıf/kopya görülmüş | İçeriği güçlendir, iç link ver |
| **Yönlendirmeli sayfa** | Sitemap'te 301 veren URL var, veya 301 hedefi `Disallow` | Sitemap'i güncelle; yönlendirme yolundaki Disallow'u kaldır |
| **Doğru standart etikete sahip alternatif** | Bilgi mesajı — canonical **doğru** çalışıyor | Dokunma |

## JSON/API uçları için doğru kalıp
```apache
# .htaccess — mod_headers icinde
<FilesMatch "^(blog|api_lib|cark_api|uye_api)\.php$">
  Header always set X-Robots-Tag "noindex, nofollow"
</FilesMatch>
```
robots.txt'te bu uçlar **Disallow OLMAYACAK** — yoksa Google başlığı göremez.
Sadece hiç içerik dönmeyenler (`upload.php` 404, `data/` 403) Disallow kalabilir.

## Tuzaklar (düşüldü — 2026-07-28)

- **Ölü Disallow kuralı:** Olmayan klasöre kural (`/2_turkish/` yokken). 301 ile
  köke gidiyorsa Google yönlendirmeyi izleyemez → "Yönlendirmeli sayfa" uyarısı.
- **Rapor bayat olabilir:** Coverage dışa aktarımı 1-2 gün geriden gelir. Düzeltmeye
  başlamadan **canlıyı kontrol et** — sorun çoktan çözülmüş olabilir (bugün öyleydi).
- **Sitemap sadece bir dosya sanmak:** `sitemap.xml` + `sitemap-blog.xml` ayrı ayrı
  sayılır. Tek dosyaya bakıp "eksik" demek yanlış çıkarım üretir.
- **JS ile veri çeken sayfa:** Ürünleri `urunler.php`'den çeken mağaza sayfasında o
  ucu `Disallow` edersen Googlebot render ederken **boş sayfa** görür. `Allow` şart.
- **Python `urllib.error` import etmemek:** `except urllib.error.HTTPError` sessizce
  AttributeError'a düşer, tüm hatalar "bağlanamadı" görünür.

## Yöntem
1. **Önce canlıyı doğrula.** Rapordaki her uyarıyı `curl -I` ile teyit et.
   Zaten düzelmiş olabilir.
2. **Çelişkiyi bul.** Sayfa 200 mü dönüyor + Disallow'lu mu? Asıl sorun bu.
3. **Tek yönerge bırak.** Ya tarama engeli, ya noindex — ikisi birden değil.
4. **`.htaccess` push'u riskli.** Hatalı satır tüm siteyi 500'e düşürür:
   yedek al → push et → **hemen** ana sayfa + birkaç iç sayfa 200 kontrolü.
5. **Yanlış noindex kontrolü.** Push sonrası normal sayfalarda `X-Robots-Tag`
   **olmadığını** doğrula (`FilesMatch` fazla geniş olabilir).

## Push öncesi (ZORUNLU)
- Yedek: `robots.txt` + `.htaccess`
- **Diff'e bak** — `degismez-kurallar` gereği. Paralel oturum aynı dosyaya
  çalışmış olabilir; beklenmedik değişiklik varsa **kullanıcıya sor**
  (2026-07-28: başka oturumun SEO işi farkında olmadan push'a dahil oldu).
- Push sonrası: `indeks_denetim.py` tekrar çalıştır + site ayakta mı kontrol et

## Raporlarken
- Hangi uyarının **zaten düzelmiş** olduğunu ayır — kullanıcı neyin yeni
  yapıldığını bilmeli
- "Keşfedildi ama taranmadı" için **hata değil** de; tarama bütçesi olduğunu ve
  zamanla düzeleceğini söyle
- Search Console verisi günlerce geriden gelir; "düzeldi" demeden bunu belirt
