# AFU Router — Claude → Codex → Gemini → OpenCode

Başlangıçta aktif ajan: **Claude**.

Kota/rate-limit hatasında aynı görev sırayla **Claude → Codex → Gemini → OpenCode**
ajanlarına geçer. Başarılı ajan sonraki normal mesajlarda da kullanılır.
Son ajandan başa dönülmez. Kota yenilendiğinde `ajan claude` ile başa dönülür.

Kalıcı geçiş:
- `ajan codex`
- `ajan claude`
- `ajan gemini`
- `ajan opencode`

Aktif ajanı gör:
- `ajan`

Tek görevlik seçim:
- `codex: görev`
- `claude: görev`
- `gemini: görev`
- `opencode: görev`

Örnek: Claude kotası doluysa Codex dener; onun da kotası doluysa Gemini,
sonra OpenCode dener. Dördü de kota hatası verirse görev `isler` içinde korunur
ve kullanıcıya bildirilir. Kurulum hatası/zaman aşımı gibi başka hatalarda
otomatik ajan değiştirilmez; hata ve görev dosyası gösterilir.

Claude, çalışan eski kopyadaki gibi ana oturumda normal yanıt verir.
`UserPromptSubmit` normal Claude mesajını durdurmaz ve ayrı Claude işçisi
başlatmaz. Son mesaj oturum kimliğiyle `oturumlar` klasöründe saklanır.
Claude'un `StopFailure` olayı `rate_limit` bildirdiğinde aynı mesaj Codex'e
devredilir; gerekirse Gemini ve OpenCode ile devam edilir. Aynı hata olayı
birden fazla gelirse aynı görev tekrar başlatılmaz. Oturumlar birbirine karışmaz.
Claude ayarında aynı script için `StopFailure` hook'u da bulunmalıdır.

Çocuk süreçlerde `AFU_ROUTER_CHILD=1` yeniden yönlendirmeyi önler.
Diğer hook'lar korunur. Slash komutları ve KAPALI anahtarı yönlendiriciyi atlar.
Ajanlar kurulu ve oturumları açık olmalıdır.

Test: `python -m unittest discover -v` (gerçek API çağrısı yapmaz).

Windows'ta npm `.cmd` başlatıcıları gerçek `.exe`/Node girişine çözülür;
görev metni komut kabuğundan geçirilmez. Boşluklar, tırnaklar ve satır
sonları korunur. Özel bir başlatıcı kullanılıyorsa gerçek program yolunu ver.

Normal Claude sohbetinde `Operation stopped by hook` başlığı oluşmaz.
Codex/Gemini/OpenCode elle seçilmişse sonuç hook çıktısı olarak gösterilebilir.
Kota devrinde yanıt ayrıca `isler` klasörüne kaydedilir ve hook bildirimiyle sunulur.

Aktif ajan bilgisi `_codex_yonlendir/aktif_ajan.txt` dosyasında tutulur.
Dosya yoksa varsayılan Claude'dur. Tek görevlik seçim aktif ajanı başarıda
değiştirmez; kota nedeniyle geçiş olursa aktif ajan sıradakine alınır.

## Kurulum

`~/.claude/settings.json` içinde `UserPromptSubmit` ve `StopFailure` hook'larına:

```json
{ "type": "command", "command": "python \"<bu klasör>/router/yonlendir.py\"" }
```

Yollar `AFU_WORK_DIR`, `AFU_SUBAJAN_SCRIPT`, `AFU_CODEX_CHAIN` ortam değişkenleriyle değiştirilebilir.
Gemini, `skills/afu-ai/scripts/subajan.py` üzerinden (omp / Antigravity) çalışır.
