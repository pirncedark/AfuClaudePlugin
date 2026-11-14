---
name: crawl4ai-tara
description: 'Web sayfasını/siteyi yerel Crawl4AI ile ücretsiz tarayıp markdown’a çevirir. Tetikleyiciler: "siteyi tara", "sayfayı çek", "web scraping", "crawl", "şu linki oku", "rakip site incele". WebFetch yetmediğinde ya da JS ile açılan sayfalarda kullan.'
---

# Crawl4AI ile tara

1. PowerShell'de önce ortamı ayarla, ardından URL'yi tara:
```powershell
$env:PLAYWRIGHT_BROWSERS_PATH='F:\afu_buyuk\crawl4ai\browsers'
$env:CRAWL4_AI_BASE_DIRECTORY='F:\afu_buyuk\crawl4ai'
& 'F:\afu_buyuk\crawl4ai\venv\Scripts\crwl.exe' <URL> -o markdown
```
`<URL>` yerine gerçek adresi yaz.
Çıktı uzunsa klasörü önce oluştur, kısa bir dosya adı seç ve çıktıyı kaydet:
```powershell
New-Item -ItemType Directory -Force -Path 'F:\afu_buyuk\crawl4ai\cikti' | Out-Null
& 'F:\afu_buyuk\crawl4ai\venv\Scripts\crwl.exe' <URL> -o markdown > F:\afu_buyuk\crawl4ai\cikti\<kisa-ad>.md
```
Kaydedilen dosyanın yalnız ilgili kısmını oku.

2. Ayrıntılı seçenekler için önce yardım komutunu çalıştır; uydurma bayrak kullanma:
```powershell
& 'F:\afu_buyuk\crawl4ai\venv\Scripts\crwl.exe' --help
```

3. Kurallar:
- Her şey F: üzerinde kalır; C: üzerine kurulum veya indirme yapma.
- Ücretli servis (Apify vb.) önerme.
- Giriş gerektiren veya izinsiz siteleri tarama; robots ve site kurallarına uy.
- Tek sayfa için bu yeter; çok sayfalı derin tarama gerekirse kullanıcıya sor.

4. Hata olursa aşağıdaki komutu çalıştır ve çıktısını kullanıcıya göster:
```powershell
& 'F:\afu_buyuk\crawl4ai\venv\Scripts\crawl4ai-doctor.exe'
```
