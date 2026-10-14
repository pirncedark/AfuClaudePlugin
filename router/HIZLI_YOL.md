# Hızlı yönlendirici
Claude terminalinde mevcut UserPromptSubmit/StopFailure hook düzeni korunur.
Codex doğrudan CLI ile başlar: Luna, low reasoning, workspace-write. Mevcut giriş kullanılır.
İki aracı Python süreci, görev dosyasını modelle tekrar okutma ve alt ajan temizlik zinciri hızlı yolda kaldırılmıştır.
Her mesaj yine yeni CLI sürecidir. Canlı token akışı veya kalıcı süreç vaat edilmez.
Başarılı Codex sonucu hook stopReason olarak gösterilir: Claude ikinci kez çalışmaz; arayüz Operation stopped by hook başlığını gösterebilir.
Kota devri yalnız Claude ve Codex arasında; aynı görevde başarısız Claude tekrar denenmez.
AFU_CODEX_LEGACY=1 eski zaman aşımı zincirine döner. AFU_CODEX_MODEL model seçimini değiştirir.
Doğrudan yol zaman aşımında otomatik tekrar yapmaz; görev ve ham çıktı isler klasöründedir.
Yedek: yonlendir.before-fast.py. Test: python -m unittest discover -q (34 test).
Canlı kısa test: HIZ_TEST_OK, toplam 9.92 saniye. Bu bir denemedir, garanti değildir.
