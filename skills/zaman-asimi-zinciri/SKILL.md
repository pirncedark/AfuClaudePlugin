---
name: zaman-asimi-zinciri
description: Codex (ve diger alt-ajanlar) 10 dk sinirinda ZAMAN_ASIMI verince isi kaybetmeden yeni turda "kaldigin yerden devam" ile yeniden cagirir; en fazla 5 tur. codex ajani cagrildiginda OTOMATIK devrededir. "zaman asimi", "codex kesildi", "yarim kaldi devam", "10 dk sinir", "tur zinciri" deyince de tetikle.
---

# Zaman aşımı zinciri

## Neden
Bash aracı tek çağrıda en fazla 10 dk bekler; `subajan.py` bu yüzden `--timeout 570` ile koşar.
Büyük iş 9,5 dk'ya sığmazsa `durum=ZAMAN_ASIMI` döner ve iş yarım kalır.

## Nasıl çalışır (otomatik)
`~/.claude/agents/codex.md` artık `subajan.py` yerine `zincir.py`'yi çağırır:

```
python "~/.claude/skills/zaman-asimi-zinciri/zincir.py" codex "<GOREV>" --cwd "<DIZIN>" --tur 1
```

- Tur bitince çıktının son satırı:
  - `ZINCIR: DEVAM --tur N` → ajan AYNI komutu `--tur N` ile hemen tekrar çalıştırır (her tur ≤10 dk).
  - `ZINCIR: BITTI (...)` → dur, tüm turların çıktısını döndür.
- 2. turdan itibaren görevin başına eklenir: `[tur N/5] DEVAM: git status/diff ile yapılanı kontrol et, tekrarlama, kalandan devam et`.
- En fazla 5 tur (~50 dk). Dolarsa `ZINCIR: BITTI (tur siniri 5 doldu, is yarim)`.
- **`ZINCIR: BITTI (KOTA, ...)` iş bitti DEMEK DEĞİL (19 Eki kullanıcı kuralı).** Claude: çalışan Codex'i durdurmaz. `git diff` + testle yapılanı kontrol edip korur. Logdaki "try again at" saati +2 dk'ya CronCreate ile devam turu kurar. Kota bitti bilinse bile yeni işte önce dener, reddederse yenilenmeyi bekler. Ayrıntı: `~/.claude/AFU_PLANLAR.md` "Codex KOTA = iş bitti DEĞİL".

## Durum çubuğu
Durum `~/.claude/zincir_durum.json` içinde tutulur:
`{ "<id>": {ajan, gorev, cwd, tur, max, durum: CALISIYOR|SIRADA|BITTI|HATA|LIMIT, basladi, guncellendi} }`
Bitmiş kayıtlar 15 dk sonra silinir. Durum çubuğu bu dosyayı okuyup `⏱ codex tur 2/5` gibi gösterir
(yalnız dosya okur; çubuktan .exe çağrılmaz).
Tur öneki `[tur N/5]` görev metninde de olduğundan, `afu-ajanlar` canlı durum satırında da görünür.

## Elle kullanım (başka ajan)
`zincir.py flash|pro|opencode "<GOREV>" --cwd "<DIZIN>" --tur 1` — aynı kurallar.

## Tuzaklar
- Görev TEK SATIR olmalı (çok satır → ilk satır gider). Uzun görev dosyaya yazılır, tek satırla okutulur.
- Devam turu yeni codex oturumudur; bağlam çalışma ağacındaki değişikliklerden gelir. Bu yüzden görev dosyası "yapılanı kontrol et" demeli.
- Tur öneki `git diff` ister: git deposu olmayan dizinde codex yine çalışır, yalnız kontrol adımı boş geçer.
