---
name: afu-ai
description: CLI köprüsü — Claude (patron) bir görevi alır, "bu işe hangi model uygun?" diye karar verir, uygun CLI subagent'ına (omp/Gemini, opencode, codex) yaptırır, dönen sonucu TEST EDİP doğrular, kullanıcıya tek sonuç verir. Her subagent KENDİ login/kotasından çalışır (token tasarrufu). "afu", "afu-ai", "modele yaptır", "subagent'a ver", "orkestra", "kim uygunsa" deyince tetiklenir.
---

# Afu-AI — CLI Köprüsü (Claude patron + CLI subagent'lar)

## Fikir
Kullanıcı görevi Claude'a verir. Claude işi kendi yapmak zorunda değil: işi analiz
eder, **en uygun CLI modeline** dağıtır (subagent gibi), dönen çıktıyı **test edip
doğrular**, sonra kullanıcıya TEK, doğrulanmış sonuç verir.

Amaç: **token + zaman tasarrufu**. Her subagent KENDİ aboneliği/login'iyle çalışır;
tek bir cüzdan gereksiz yanmaz. Hiçbir API anahtarı bu repoda tutulmaz — her CLI
kendi oturumunu kullanır.

## SUBAGENT EKİBİ (çağrı sözdizimi — Windows'ta doğrulandı)
| Subagent | Motor | Komut | Güçlü yanı |
|----------|-------|-------|-----------|
| **omp**  | Gemini (antigravity, 1M bağlam) | `omp -p "<görev>" --auto-approve` | Hızlı, tarama/özet |
| **opencode** | OpenCode (Go) | `opencode run "<görev>"` | Kod, uzun bağlam |
| **codex** | ChatGPT / Codex CLI | `codex exec "<görev>"` — review: `codex exec review` | Güçlü kod + review |

Her biri ayrıca kurulur ve **kendi hesabıyla login olur**; bu repo sadece köprüyü
(yönlendirme + kanıt + doğrulama) tanımlar.

### CLI güncelleme ("afu cli update")
- omp: `omp update` (sonra config newline + provider smoke test ZORUNLU)
- npm: `npm install -g opencode-ai@latest @openai/codex@latest`
- TUZAK: Windows'ta npm güncellemesi yarım kalıp shim'leri silebilir (`command not
  found`, `npm ls` boş sürüm). Çözüm: paketi `npm uninstall -g` + global
  `node_modules` altındaki klasörü sil + tekrar kur.

## KANIT BANNER'I (zorunlu)
omp'yi çıplak çağırma — **sarmalayıcıyı kullan**, işi kimin yaptığını kanıtlı bassın:

```bash
python skills/afu-ai/scripts/omp_kanit.py "<görev>" --cwd "<dizin>" --timeout 600
```

Çıktı: cevap + renkli tablo (yeşil = işi yapan, kırmızı = kapalı) + oturum ID,
token, maliyet, süre. Tüm alanlar omp'nin kendi `--mode json` çıktısından okunur,
elle yazılmaz → uydurulamaz.

**Banner kırmızı `!! DIKKAT` uyarısı basarsa DUR:** omp beklenen sağlayıcıya değil
ücretli bir modele düşmüş demektir, yani iş ÜCRETLİ çalışmıştır.

### TUZAK: config.yml'nin son satır sonu
`~/.omp/agent/config.yml` dosyasının sonunda satır sonu (newline) yoksa omp TÜM
YAML'i sessizce yok sayar ve varsayılan (ücretli) modele düşer — hiçbir hata
vermez. `sed -i` bu satır sonunu silebilir. Config'e her dokunuştan sonra doğrula:

```bash
tail -c 1 ~/.omp/agent/config.yml | xxd          # 0a ile bitmeli
cd /tmp && omp -p --mode json "test" | grep -o '"model":"[^"]*"' | head -1
```

> Bir subagent 401/auth hatası verirse → o modeli listeden düş, kullanıcıya "login
> gerek" de, UYDURMA. Çalışan başka subagent'la devam et.

## YÖNLENDİRME (routing) — "bu işe kim uygun?"
- **Hızlı/kısa/ucuz** (özet, çeviri, tek soru, format) → **omp**
- **Kod yazma / dosya düzenleme** → **opencode** veya **codex**
- **Kod review / bug avı** → **codex exec review** (yoksa opencode)
- **Uzun bağlam / repo geneli** → **opencode**
- Emin değilsen: aynı işi 2 modele ver, sonuçları karşılaştır (konsey modu).

## AKIŞ (her görevde)
1. **Analiz:** Görevi tek cümlede tanımla. Küçük mü, kod mu, uzun mu?
2. **Karar:** Yukarıdaki tabloya göre subagent(ları) seç. Neden seçtiğini 1 satır söyle.
3. **Dağıt:** Subagent'ı `Bash` ile çağır. Karmaşık/uzun görevleri `run_in_background` ile ver.
   Prompt'u NET yaz (subagent senin bağlamını bilmez — gerekli dosya/kuralı prompt'a koy).
4. **TEST ET (zorunlu):** Dönen çıktıyı körlemesine kabul etme.
   - Kod ise: çalıştır / syntax kontrol / testini koştur.
   - Metin ise: göreve uygun mu, eksik/uydurma var mı kontrol et.
   - Yanlışsa: düzelt ve subagent'a **geri iş ver** (loop).
5. **Sonuç:** Kullanıcıya TEK, doğrulanmış sonucu ver. Hangi modelin yaptığını kısaca belirt.

## GOAL-LOOP (isteğe bağlı, /loop ile)
Kullanıcı "loop"/"hedef" derse: hedefe ulaşana kadar dağıt→test→düzelt→geri ver
döngüsü. Her turda ilerlemeyi kısaca raporla. Sonsuz döngüye karşı: 3 turda
ilerleme yoksa dur, kullanıcıya sor.

## KURALLAR
- Subagent çıktısını DOĞRULAMADAN "oldu" deme (evidence-before-assertions).
- Her subagent kendi login'iyle; kimseye körlemesine API key gömme.
- Auth hatası = o modeli düş + kullanıcıya bildir, uydurma.
- Rapor kısa; ham subagent dökümünü yapıştırma, özetle.
- Riskli/yıkıcı işlerde (dosya silme, canlıya push) önce kullanıcı onayı.
