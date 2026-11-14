---
name: isaretle-devret
description: Bir bug/hata/kırmızı test/eksik özellik bulunduğunda düzeltmeyi alt ajana (Codex/OpenCode/Gemini) vermeden ÖNCE Claude ilgili dosya satırlarını kendisi bulur, 📍 ile işaretler ve görev dosyasını öyle yazar; ajan aramaz, doğrudan oraya bakar. "bug var", "hata var", "düzelt", "kırmızı test", "çalışmıyor", "codex'e ver", "opencode'a ver", "işaretle", "devret" deyince ve her alt ajan görevinden önce tetikle.
---

# İşaretle → Devret

Kullanıcı kuralı (3 Eki 2026): "Bir bug var. Düzeltmeyi vermeden önce ilgili dosyalardaki satırları işaretliyorum. İşler bu şekilde devredilsin." Claude token'ı az: işi ajan yapar, ama YERİ Claude bulur.

## Adımlar

1. **Belirtiyi yakala (1–2 komut).** Hata çıktısını/kırmızı testi bir kez kendin koş, tam hata satırını al. Ham log okuma; `grep -n`, `tail -3`, `sed -n A,Bp` yeter.
2. **Yeri bul.** `grep -n "<hata metni|fonksiyon|değişken>"` ile dosya + satır. Benzer kopyalar varsa (ör. `app/ui` ↔ `app-ui/windows`, `_yedek`, `_wt/*`) hangisinin DOĞRU olduğunu belirle.
3. **Görev dosyasını yaz** (`<proje>/_gorev/<gün>/.../GOREV_<IS>.md`), şablon aşağıda. Her düzeltme noktası bir 📍 maddesi.
4. **Devret:** `Agent(subagent_type=codex|opencode|gemini)` → tek satır: "Görev dosyası: <tam yol> oku ve uygula (📍 satırlara doğrudan bak)". Çok satırlı görev metnini prompt'a koyma.
5. **Doğrula:** Ajan "geçti" dese de doğrulama komutunu bir kez KENDİN koş. SONUC'taki "gerçek çıktı" ile karşılaştır. Yanlışsa yeni 📍'larla geri ver.

## Görev şablonu

```
# GOREV (<ajan>): <tek cümle iş>
ONAY: Tasarım/kapsam kullanıcı tarafından onaylı; brainstorming/onay adımını ATLA, onay sorma, doğrudan uygula.
ÇALIŞMA DİZİNİ (tam yol): C:\...\<repo veya worktree>
ÖNCE OKU: <varsa CLAUDE.md / ilgili belge, tam yol>
DOKUNMA: <yanlış kopyalar, ~/.claude, başka _wt> · Liste dışı dosya gerekiyorsa dur ve SONUC'ta sor.
YASAK: git restore/checkout --/reset/clean/stash/rebase/amend/push/switch · test silme/atlama · görünür pencere

📍 1) <TAM YOL>:<satır>
   - şu an: `<o satırdaki kod ya da hata metni>`
   - sorun: <neden yanlış>
   - yap: <ne olmalı> (beklenen davranış / onaylı görünüm)
📍 2) ...

DOĞRULA (çıktıyı SONUC'a AYNEN yapıştır): <komutlar, beklenen sonuç>
COMMIT: yalnız değiştirdiğin dosyalar adıyla `git add`; İngilizce mesaj; push YOK
SONUC: <tam yol>\SONUC_<IS>.md — ilk satır "SONUC: TAMAM - ..." / "SONUC: YARIM - neden"
```

## Kurallar

- 📍 maddesinde mutlaka: tam dosya yolu + satır no + o satırdaki metin + yapılacak iş. "İlgili dosyalara bak" gibi belirsiz ifade YASAK.
- Ajana göre: kod yazma/onarım → Codex; test koşma/küçük düzeltme → OpenCode; belge/sayfa → Gemini (dosya yolu şart).
- Ajanlar `~/.claude` ve bazen `.git`e yazamaz: kurulum/commit gerekiyorsa Claude yapar.
- Takılı/yetim süreç kontrolü: yeni tur öncesi `Get-CimInstance Win32_Process | ? CommandLine -match 'codex.js'` (bkz. CLAUDE.md).
- Kullanıcıya kısa rapor: ne bulundu (📍 sayısı), kime verildi, ne zaman doğrulanacak.

## Örnek (3 Eki, durum çubuğu kapısı)

`cubuk_kur.sh` → "KAPI: KALDI (2)". Bulunan: `cubuk_kapi.sh:164 tab: unbound variable`; `tests/test_cubuk_ajanlar.sh` eski çok satırlı AJANLAR'ı bekliyor; `statusline-command.sh:546-547` 5H/7D 178/160 (onaylı 141); `statusline-command.sh:412` OPENCODE "acik" → sahte "0". Dört 📍 ile Codex'e verildi.
