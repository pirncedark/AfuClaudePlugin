---
name: site-hiz-olcum
description: >-
  Use when a site is slow to respond to clicks/typing or a Core Web Vitals metric
  is bad (INP, LCP, CLS) — from Clarity/Search Console/PageSpeed reports or user
  complaints. Also before/after any performance change, to prove the fix actually
  worked. Tetikleyiciler — "INP yüksek", "site yavaş", "tıklayınca geç tepki
  veriyor", "Core Web Vitals", "Clarity performans", "sayfa donuyor", "hızlandır",
  "performans raporu geldi".
---

# Site Hız Ölçüm — tahminle değil ÖLÇÜMLE performans

## Ne işe yarar
Yavaşlığın **gerçek kaynağını** bulur ve düzeltmenin işe yarayıp yaramadığını
sayıyla kanıtlar. Web performansında sezgi sürekli yanılır: en "ağır görünen"
kod çoğu zaman suçlu değildir.

## ⛔ Bu skill'in tek kuralı
**Tek ölçüme bakıp karar verme.** Web performans ölçümü gürültülüdür; tek sayı
seni yanlış yere götürür. Her iddia için: tekrarlı + almaşık ölçüm, medyan.

## Ne zaman kullan
- Clarity/Search Console/PageSpeed'den kötü metrik geldiğinde
- "Tıklayınca geç tepki veriyor / donuyor" şikayetinde
- Bir performans düzeltmesi push etmeden ÖNCE ve SONRA (kanıt için)
- **Kullanma:** görsel/layout bozukluğu → `responsive-denetim`

## Araç
```bash
python ~/.claude/skills/site-hiz-olcum/scripts/inp_olc.py <url> \
       --js "renderProducts()" --tekrar 10 \
       --karsilastir ".kategori-satir{content-visibility:visible !important}"
```
- `--js` → bir fonksiyonun blok süresi (almaşık, medyan, ısınma dahil)
- `--tik ".secici"` → tarayıcının **gerçek INP** ölçümü (PerformanceObserver)
- `--karsilastir "<css>"` → özelliği geçici KAPATIR, kazancı % olarak verir
- Çıktı: medyan/min/maks + mobil tahmini (4x/6x) + eşik yorumu

## Eşikler
| Metrik | İyi | Orta | Kötü |
|---|---|---|---|
| INP | <200ms | 200-500 | >500 |
| LCP | <2.5s | 2.5-4 | >4 |
| CLS | <0.1 | 0.1-0.25 | >0.25 |

## Ölçüm tuzakları (hepsine düşüldü — 2026-07-28)

| Tuzak | Ne olur | Çözüm |
|---|---|---|
| **Soğuk başlangıç** | İlk çağrı derleme+ilk layout taşır. `openDetail` 61.8ms ölçüldü, ısınmış hali 2ms | Isınma turu at, sonra ölç |
| **Sıra yanlılığı** | A,A,A→B,B,B ölçümünde ilk çalışan avantajlı/dezavantajlı çıkar. Fragment önce "-23%" sonra "+14%" verdi | **Almaşık** ölç: A,B,A,B... |
| **Laboratuvar ≠ saha** | Masaüstünde 56ms "iyi" görünür, mobilde 4-6x = 224-336ms | Mobil çarpanı uygula, trafiğin mobil oranına bak |
| **Tek ölçüm** | Canlıda arka arkaya 56ms ve 104ms ölçülebilir | En az 6-12 tekrar + medyan |
| **`networkidle` beklemek** | Analytics sürekli istek atar, ASLA gerçekleşmez → 60sn timeout | `domcontentloaded` + sabit bekleme |
| **CSP `unsafe-eval`** | `eval`/`new Function` bloklanır (bu sitede kapalı) | Fonksiyonu `window[ad]()` ile çağır |
| **Sentetik olay** | `dispatchEvent` ile INP ölçülmez, `interactionId` gelmez | Gerçek `page.click()` kullan |

## Yöntem
1. **Kaynağı ölç, tahmin etme.** Kaç öğe çiziliyor? Kaç DOM düğümü?
   Canlı veriyle yerel kod farklı olabilir (burada: kodda 28 ürün, canlıda **158**).
2. **Tetikleyici zinciri çıkar.** Hangi olay hangi fonksiyonu çağırıyor?
   `onkeyup`'a bağlı ağır render = her tuşta tam yeniden çizim.
3. **Tek hipotez, tek değişiklik, ölç.** Aynı anda 3 şey değiştirirsen hangisinin
   işe yaradığını bilemezsin.
4. **Hipotez çürürse GERİ AL.** Ölçüm kazanç göstermiyorsa "dursun zararı yok"
   deme — ya kaldır ya da yorumuna "kazanç ölçülmedi" yaz. Yanlış iddia bırakma.
5. **CLS'i de kontrol et.** INP düzeltirken layout kaydırma yaratmak kolaydır.
   `content-visibility` eklediysen `contain-intrinsic-size`'ı **gerçek yüksekliğe**
   ayarla (ölç, tahmin etme).

## Sık çıkan kök nedenler
- **Debounce'suz arama** (`onkeyup`/`oninput` → ağır render): her tuş tam render.
  Çözüm: 150ms debounce + buton/Enter için beklemesiz sürüm.
- **Ekran dışı içerik layout'a giriyor:** `content-visibility: auto` +
  `contain-intrinsic-size` (ölçülen yükseklik). Burada %47-64 kazanç verdi.
- **Render + smooth scroll aynı blokta:** `scrollIntoView`'ı
  `requestAnimationFrame`'e al.
- **İşe yaramayan "optimizasyon":** DocumentFragment modern Chrome'da kazanç
  vermedi (12 tekrar, %-9). Ölçmeden ekleme.

## Push öncesi (ZORUNLU)
1. CSS/layout değiştiyse → `responsive-denetim` skill'i (çoklu viewport kapısı)
2. **Yedek al + diff'e bak** — `degismez-kurallar` gereği. Paralel oturum aynı
   dosyaya çalışmış olabilir; beklenmedik değişiklik varsa **kullanıcıya sor**
   (2026-07-28'de tam bu oldu: push'a başka oturumun SEO işi de dahil oldu).
3. Cache-bust: `?v=<tarih-konu>` — hem CSS hem JS
4. Push sonrası **canlıdan doğrula**: kodun orada olması yetmez, çalıştığını ölç

## Raporlarken
- Ölçümü **öncesi/sonrası** ver, tek sayı değil
- Laboratuvar ölçümü olduğunu söyle; Clarity/CrUX gerçek kullanıcı verisi
  **24-48 saatte** güncellenir — "düzeldi" demeden önce bunu belirt
- Çürüyen hipotezini de raporla (neyi denedin, neden bıraktın)
