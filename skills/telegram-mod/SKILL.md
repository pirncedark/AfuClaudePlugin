---
name: telegram-mod
description: '"telegram mod" / "teleg aktif" / "telegram aktif et" deyince cift yonlu Telegram loop kur: gelen mesajlari dinleyiciden oku, isleri yurut, sonucu Telegram uzerinden raporla. BUTUN sorular Telegram''dan sorulur, cevap Telegram''dan alinir. Kullanici bu ifadeleri yazinca tetikle.'
---

# Telegram Mod — Cift Yonlu Loop

Tetik: "telegram mod", "teleg aktif", "telegram aktif et".

Amac: bilgisayar basinda olmadan, telefondan is yurutmek. Claude Code arka planda
doner; sorularini Telegram'a sorar, cevabini Telegram'dan alir.

## Kurulum
1. `@BotFather`'dan bot al, token'i `.env` icine `MCP_TELEGRAM_TOKEN` olarak yaz.
2. Kendi chat id'ni `@userinfobot`'tan al, `MCP_TELEGRAM_CHAT_ID` olarak yaz.
3. `pip install requests`
4. Bu repoyu skills dizinine bagla (bkz. README).

## ⛔ TEMEL KURAL — Telegram tek kanal
- **Butun sorular Telegram'dan sorulur.** Terminalde soru sorup bekleme — soruyu
  Telegram'a gonder, cevabi `gelen_mesajlar.jsonl`'den oku.
- **Butun cevaplar/raporlar Telegram'a gider.** Terminal ciktisi sadece ozet.
- Onay/teyit isteyen her is (canliya push, silme, toplu islem) → teyidi Telegram'dan
  iste, gelen cevaba gore ilerle.
- Soru sorarken **numarali secenek** ver ("1/2/3 yaz") — telefondan cevap kolay olsun.
- Cevap gelene kadar loop'u kapatma; sessiz turda rapor GONDERME (spam yok).

## ~2 dk loop — her turda HEM alim HEM gonderim

### 1. ALIM — surekli dinleyici + dosyadan oku
`scripts/tg_dinleyici.py` arka planda SUREKLI calisir (long-poll, mesaji ANINDA
yakalar):
- Calisiyor mu: `telegram_kuyruk/tg_dinleyici.log` son satiri taze mi? Degilse baslat:
  `pythonw scripts/tg_dinleyici.py &`
- Her turda mesajlari DOSYADAN oku: `telegram_kuyruk/gelen_mesajlar.jsonl` icinde
  `"durum": "bekliyor"` satirlar = yeni mesaj. Isleyince satiri
  `"durum": "tamamlandi"` yap (dosyayi yeniden yaz).
- Bekleyen yoksa sessiz tur (Telegram'a rapor GONDERME, spam yapma).
- ⛔ **Ayni botu iki surec dinlemez.** Ikinci surec `409 Conflict` alir ve mesaj
  calinir. Dinleyici acikken baska bir poll script'i CALISTIRMA.
- Gonderilen foto → `telegram_kuyruk/gelen_resimler/`, dosya (zip/csv/xlsx) →
  `telegram_kuyruk/gelen_dosyalar/`.

### 2. YURUT
Isleri sirayla yap. **AUTO-MOD: terminalde soru sorma** (sifre dahil; `.env`'den
oku). Gercekten karar gerekiyorsa soruyu **Telegram'a** gonder ve cevabi bekle
(loop devam eder, her turda kuyruga bak).

### 3. GONDERIM — HTML formatli
Telegram MCP sunucusunun `SEND_MESSAGE` araci **parse_mode DESTEKLEMEZ** (duz metin
gider, etiketler goze gorunur). Bicimli rapor icin Bot API'yi dogrudan kullan:

```bash
python scripts/tg_gonder.py "<b>Is bitti</b>
• 3 dosya guncellendi
• testler gecti"

python scripts/tg_gonder.py "yeni gorsel" --photo cikti/banner.png
```

**Telegram HTML'de SADECE sunlar calisir:** `<b> <i> <u> <s> <code> <pre>
<a href> <blockquote> <tg-spoiler>`.
⛔ `<table> <ul> <li> <br> <h1..h6> <div>` YOK — tablo yerine `•` satirlari,
baslik yerine `<b>`, satir sonu yerine gercek yeni satir kullan.
⛔ Metindeki serbest `&`, `<`, `>` karakterlerini kacir (`&amp; &lt; &gt;`) yoksa
400 doner. 4096 karakteri asan mesaji script kendisi parcalar.

Duz/kisa mesajda MCP `SEND_MESSAGE` yeterli.

### 4. LOOP
`ScheduleWakeup` ~120 sn, `prompt: /telegram-mod`. "dur/stop"a kadar devam.
**Sessiz turda da loop'u kapatma**, sadece tarayip devam et.

## Kurallar
- Dis push (canli sunucu) oncesi teyidi Telegram'dan iste, terminalde bekleme.
- Rapor formati: ━ ayrac + baslik + numarali emoji maddeler (kalici).
- Token'i asla mesaja, log'a veya commit'e yazma — sadece `.env`.
- Uretilen her basarili gorsel/video aninda `--photo` / `--video` ile gonder.
