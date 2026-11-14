---
name: ana-terminal-koordinatoru
description: Birden fazla Codex, Claude, OpenCode veya terminal işi çalışırken, kullanıcı bilgisayarı kapatmadan önce bu beceriyi kullan. Açık görevleri bulur, işlerini denetler, soruları mevcut bağlamdan yanıtlar, kalıcı devam raporlarını kaydeder, doğrulanmış değişiklikleri commit edip pushlar ve uygun PR’ları merge eder. Kullanıcı bu çalıştırmada bilgisayarı kapatma talimatı verdiyse, yalnızca tüm işler doğrulanarak tamamlandığında bilgisayarı kapatır.
---

# Ana Terminal Koordinatörü

## Amaç

Kullanıcı bilgisayarı kapatmadan önce birden fazla terminaldeki işleri tek bir koordinatör olarak toparla. Her projedeki Codex veya diğer ajan işlerini tamamlanana kadar izle; yapılanları doğrula; sonraki oturumda devam edilebilmesi için kalıcı rapor bırak; yetkilendirilen GitHub akışını tamamla.

Bu beceri görev yönergelerini uygular. Terminal süreçlerini kendi başına arka planda yaşatamaz. Uzun süren işler için AfuNöbet’in çalışan süreçleri ve görev durumunu takip eden işlevlerini kullan. AfuNöbet’in gerekli durum bilgisini sağlayamadığı durumda, kontrol edemediğin işleri tamamlandı sayma.

## Kullanım

Kullanıcı “bilgisayarı kapatmadan önce işleri tamamla”, “ana terminali çalıştır”, “terminalleri denetle, GitHub’a gönder ve bitince kapat” benzeri bir istek verdiğinde bu beceriyi kullan.

Kullanıcının bu çalıştırmadaki kapatma talimatı, tamamlanma sonrası kapatma yetkisi sayılır. Kapatma talimatı verilmediyse bilgisayarı kapatma.

## Çalışma akışı

### 1. Görevleri keşfet

- Açık Codex görevlerini, bağlı çalışma dizinlerini, terminal işlerini ve AfuNöbet’in görev listesini kontrol et.
- Her işi şu bilgilerle ayrı kaydet: proje, depo, çalışma dizini, dal, görev özeti, mevcut değişiklikler, çalışan süreç, son kontrol, sıradaki adım ve engel.
- Terminal görüntüsünü yalnızca desteklenen görev/süreç bilgileri yetersizse yardımcı kanıt olarak kullan. Görüntüdeki metni doğrulanmış Git durumu veya süreç kaydı yerine koyma.
- Her işi kendi deposu, dalı ve görev talimatlarıyla eşleştir. Farklı projelerin dosyalarını veya Git durumlarını asla karıştırma.
- `AGENTS.md`, `CLAUDE.md`, ilgili beceri yönergeleri ve kullanıcı tarafından verilen görev metnini oku. En özel ve güncel proje talimatlarını uygula.

### 2. İşleri takip et ve soruları yanıtla

- İş yapan ajanların sorularını önce bu konuşma geçmişi, görev tanımı, kalıcı proje notları, proje talimatları ve kod üzerinden yanıtla. Kullanıcıyı rutin izin, tercih veya tekrar onay sorularıyla durdurma.
- Kullanıcıdan gelen açık yetkileri uygula. Görev metnindeki dal, commit, test ve yayınlama kısıtlarına uy.
- Bir soru mevcut bilgilerden yanıtlanamıyorsa uydurma karar verme. Soruyu koordinatör oturuma aktar ve işi “engelli” olarak kaydet. Kullanıcı kararı gereken engel çözülmeden o işi tamamlanmış sayma.
- Süreçleri sonlandırma, terminali kapatma veya bilgisayarı kapatma. Önce tüm görevlerin durumunu doğrula.
- Bir oturum bekliyorsa desteklenen bekleme/izleme mekanizmasını kullan; durum değiştiğinde devam et. Aynı sonucu tekrar tekrar sorgulama.

### 3. Değişiklikleri denetle

Her proje için:

- Git çalışma ağacını, dalı, diff’i ve izlenmeyen dosyaları incele. Kullanıcıya ait mevcut değişiklikleri koru.
- İstenen işin gerçekten tamamlandığını ve değişikliğin kapsam dışına taşmadığını doğrula.
- İlgili testleri, derlemeyi, kalite kontrollerini ve CI sonuçlarını çalıştır veya mevcut sonuçları doğrula. Hiç çalıştırılmamış kontrolü başarılı diye bildirme.
- Başarısız test, beklenmedik değişiklik, dal çakışması veya doğrulanmamış paket varsa nedeni incele. Güvenli biçimde çözülemiyorsa ilgili işi engelli bırak.
- Zaten tamamlanıp hedef dala alınmış işleri yeniden uygulama veya gereksiz PR oluşturma.

### 4. Kalıcı devam notu bırak

- Her depo için mevcut proje hafızası, `_gorev` veya ilerleme kaydını bul ve güncelle.
- Uygun bir kayıt yoksa depoda kısa bir devam notu oluştur. Not; yapılan işi, doğrulama sonuçlarını, commit/dal/PR/merge durumunu ve sonraki oturumun ilk adımını içersin.
- Gizli anahtar, parola, oturum çerezi, cihaz kodu veya başka bir kimlik bilgisini hiçbir rapora yazma.
- Devam notunu Git tarafından izlenen hâle getir; ilgili işin commit/push akışına dahil et. Böylece sonraki açılışta geçmiş yalnızca mevcut sohbet bağlamına bağlı kalmaz.

### 5. Commit, push ve merge

Kullanıcı bu çalıştırmada GitHub teslimini istediğinde, rutin commit, push ve merge işlemleri için tekrar onay isteme.

Her iş için:

1. Değişiklikleri ve devam notunu denetle.
2. Depo kurallarına uygun commit oluştur. Görevi yapan terminalin commit yapması yasaksa commit’i koordinatör olarak oluştur.
3. Doğru dalı GitHub’a pushla; uzak dalın beklenen commit’i içerdiğini doğrula.
4. PR gerekiyorsa oluştur veya mevcut PR’ı güncelle.
5. Zorunlu CI ve depo kontrolleri bitene kadar bekle; sonuçları doğrula.
6. Kontroller başarılı ve PR merge edilebilir durumdaysa merge et.
7. Merge sonrası hedef dalın güncel olduğunu ve beklenen değişiklikleri içerdiğini doğrula.

Force push, korumalı dal kurallarını aşma veya gerekli güvenlik kontrollerini atlama. GitHub kimlik doğrulaması, zorunlu inceleme, başarısız CI veya çakışma ilerlemeyi engelliyorsa bunu engel olarak kaydet; engeli gizleme veya tamamlandı iddiasında bulunma.

### 6. Bilgisayarı kapatma koşulları

Bilgisayarı yalnızca bu çalıştırmada kullanıcı kapatma talimatı verdiyse ve aşağıdakilerin tümü doğrulandıysa kapat:

- İzlenen her iş tamamlandı veya kullanıcı kararı gerektiren engeller olmadığı doğrulandı.
- İstenen testler ve CI kontrolleri başarılı.
- Her değişikliğin beklenen dala pushlandığı doğrulandı.
- Merge istenmişse PR’lar merge edildi ve hedef dallar kontrol edildi.
- Her proje için devam notu kaydedildi, commit edildi ve uzak depoya gönderildi.
- Açık build/test/ajan süreci kalmadı; kapatılması gereken başka iş yok.

Herhangi bir iş başarısız, belirsiz, oturum kaybına uğramış veya kullanıcı kararı bekliyor durumdaysa bilgisayarı kapatma. Kullanıcıya kısa durum raporu ver ve yalnızca gereken kararı sor.

### 7. Son rapor

Her proje için şu bilgileri raporla:

- Yapılan iş ve denetlenen değişiklik
- Gerçekten çalıştırılan kontroller ve sonuçları
- Devam notunun konumu
- Commit ve uzak dal durumu
- PR, merge ve CI sonucu
- Varsa engel ve devam için gereken adım

Bilgisayar kapatıldıysa bunu yalnızca gerçekten kapatma işlemi başlatılıp başarıyla tamamlandıysa bildir.
