---
name: mobile-expo-dev
description: React Native + Expo mobil geliştirme döngüsü — kurulum, arayüz, test, hata düzeltme ve yayın öncesi kontrol.
title: "Mobile Expo Dev"
platforms: [windows, macos, linux]

audience: contributor
tags: [coding, development, mobile]
category: software-development---

# Mobile Expo Dev (Hermes Skill)

Bu proje için oturumdan oturuma sürekli uygulanacak mobil geliştirme rehberi.

## Kullanım Zorunluluğu

- Expo/React Native geliştirme, test ve yayınlama işlerinde bu skill’i öncelikle yükle.
- Eğer farklı bir mobil framework/araç kullanılacaksa, önce bu skill’i dikkate al.

---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | React Native + Expo mobil geliştirme döngüsü — kurulum, arayüz, test, hata düzeltme ve yayın öncesi kontrol. |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

## 1. Proje Yapısı

- Proje adı: **VerToGo** (içinde deneme-metni kullanma; final ismiyle publish edilecek)
- Ana klasör: `C:\Users\marko\OneDrive\Desktop\hermes_v7`
- Proje dışı ana dizine build ve ara klasörler bırakma; proje içinde tut.

### Kurallar

- Proje, **her zaman bir üst dizinden** başlatılır.
- Kökde kişisel dosyalar (`Notlar`, `NOTES`, `MEMORY` vb.) bulunur; bunları silmeya veya taşıma.
- Expo CLI: `npx expo start`, `--clear` veya `-c` tercih edilebilir ancak dikkatli kullanılsın.
- Versiyon yönetimi: `git` varsa her önemli adımdan sonra commit.
- Express/Node sunucu gerektiren özellikler için backend klasörü yoksa, proje içinde basit bir mock servis geliştir.

---

## 2. Temel Geliştirme Kuralları

- Tasarım: ferah, sade, nesnelli/renkli bir tema. Favori: açık tema, buton turuncu, arka plan beyaz/bej.
- Kullanıcı deneyimi: fazla şekilli/süslü elementlerden kaçın.
- Reusable yapı: aynı component’leri tekrar tekrar eklemek yerine ortak klasörlere koy.
- Yorum/feedback kullan: AI’ya prompt’u yazarken pratik ve tek tek çözümünü iste.

---

## 3. Test ve Hata Ayıklama Akışı

1. Expo CLI hata verdiğinde önce `expo start -c` (cache temizle).
2. `npx expo start` ve terminalden iOS/Android seçimi (`i`, `a`).
3. Simülatörde görünmüyorsa: `npx expo start --clear` + yeniden başlat.
4. Emülatör hata verirse: önce `-c`, sonra emülatörü kapatıp aç.
5. Görsel bug varsa print screenshot + AI’ya prompt.
6. Hata çözüldüğünde yeniden `npx expo start` (çoklu reload önleme).

---

## 4. Yayın Öncesi Kontrol Listesi (Apple App Store)

- Üyelik/hesap sil butonu: Uygulama içinde.
- Privacy Policy + Terms of Use (gizlilik politikası ve kullanım şartları).
- İzinler: galeri, kamera, konum, rehber vb. açıklamaları App Store Connect’te doldur.
- Lisans, telif hakkı, içerik sağlayıcısı; hangi api/veri kullanılıyorsa yaz.
- Başlık, alt başlık, anahtar kelimeler, desteklenen diller.
- Ödeme/abonelik + reklam entegrasyonu alt yapısı hazır mı?
- TestFlight ile önce kendi testlerini yap.

---

## 5. Yayın Öncesi Kontrol Listesi (Google Play)

- Üstteki “Apple App Store” listesini aynen uygula; sadece Xcode/TestFlight yerine Android Studio/Google Play Console’da yap.
- İzinler (AndroidManifest.xml) ile uygulama içi izin talep akışı eşleşsin.
- Ödeme/abonelik sistemini Google Play entegrasyonuyla doğrula.

---

## 6. Pazar Yolu

- İlk yayın uygulama tek seferde onay almak için şu yöntem önerilir:
  - Gerekli Store formunu tek seferde eksiksiz doldur; sonra “Send to Review”.
  - Gerekli alanlar: başlık, alt başlık, etiketler, açıklama, gizlilik politikası, kullanım şartları, izin açıklamaları.
- Deneme sürümü (trial) ekle; App Store / Play Store’da ürün/abonelikleri önce oluştur.
- Hâlâ red alırsan; 30 gün geçmeden yeniden dene. Ret sebebi açık değilse: “Test aşamasında, ileriki sürümde tam işlevsellik sunulacak.” gibi kısa net cevap ver.
- “App Store’a gönder” adımını her zaman kullan; doğrulamadan önce formu tekrar kontrol et.

## 7. Auto-Yayınlama ve AI Destekli Form Doldurma

- Bazı AI araçları App Store Connect formlarını otomatik doldurabilir; bunu kullanmak tek seferde onay alma şansını artırır.
- Ancak AI ile “vibe coding” sonrası mutlaka kontrol et:
  - TestFlight’ta güvenlik açıkları, anahtar sızıntısı, veri karışıklığı gibi hatalar görülebilir.
  - Yayınlamadan önce tek tek çöz; güvenlik/veri sorunu kalmamalı.
- Auto-fill sonrası da form bir kez manuel kontrol edilmeli.

## 8. Yayın Sonrası ve Pazarlama

- Yayınlandıktan sonra ilk 1-2 hafta kritik: kullanıcı deneyimi, app kalitesi, indirme/retention oranları marka yerini belirler.
- Organik indirme: Store’un ilk boost’unu kullan; kullanıcı kalitesi düşerse ileride görünürlük azalır.
- Pazarlama kanalları: TikTok, Instagram, LinkedIn, Twitter/X, YouTube; içerik üretimi çok etkili.
- Takip edilecek metrikler: indirme, aktif kullanıcı, abonelik dönüşüm oranı, AI servis maliyeti, reklam geliri.
- Sonraki sürümde maliyet/indirme/gelir detaylarını paylaş; buna göre projeye devam et veya durdur kararı ver.
- Red sebebi açık değilse: “Bu uygulama şu anda sadece test aşamasındadır, ilerleyen sürümde tam işlevsellik sunulacaktır.” gibi bir cevap ver.
- Tekrar red alındığında video içindeki deneyimi kullan: yayıncıya kısa, net mesaj yaz.

---

## 8. UI/UX Test

- iOS ve Android’de aynı anda test et.
- Kullanıcı yolu: login → ana sayfa → harita → AI butonu → öneri listeleme → detay görünümü.
- Test edilecekler: UI elementlerin tıklanabilirliği, hata mesajı kullanıcı dostu mu, navigation çalışıyor mu.
- Hatalı durumda: uygulamayı kapat/tekrar aç, `npx expo start`’ı yeniden çalıştır.

---

## 9. Monetizasyon Planı

1. Reklam: **AdMob** entegrasyonu (banner, interstitial, rewarded).
   - `npx expo prebuild --clean` native dosyalar oluşturulduktan sonra eklenmeli.
   - Test ID'leriyle geliştirme; canlıya alırken production ID'leri değiştir.
2. Abonelik: **RevenueCat** tercih edilsin (tek kod, iki platform).
   - App Store / Play Store'da ürün/abonelikleri önce oluştur; sonra kodda entegre et.
3. İlk model: **Free + Pro** yeterli; Plus katmanı kullanıcıyı karıştırma.
   - Deneme süresi: 7 gün trial şart; eklemezsen dönüşüm düşer.
   - Ödül reklamı: reklam izleyerek kredi/kısıtlı özellik aç.
4. Fiyatlandırma:
   - Aylık ~$1.99–$2.00, yıllık ~$17.99 hedefle.
   - Düşük bütçeli pazarlarda TR için 99–100 TL bandı uygun.
5. Dashboard/UI:
   - Premium butonu ana sayfada veya profile'de görülebilir olsun.
   - Rewarded ad için "kredi kazan" ekranı ayrı olsun.

---

## 10. Karmaşık Konu ve Bağımlılık Yönetimi

- Node.js versiyonu: projeye uygun LTS sürümü kullan.
- npm paketleri çakışırsa `package.json` önce temizlenip tekrar kurulur.
- Firebase/Supabase anahtarları `.env` dosyasında olmalı; uygulama içinde hiçbir yere sabit koduyla gömme.
- Backend servisler için `requirements.txt` ya da `pyproject.toml` kullan.

---

## 11. Büyük UI Değişikliği Öncesi

- Değişiklik öncesi `git stash` ya da commit yap.
- Değişiklikten sonra derin bir test döngüsü yap; snapshot/screenshot al.

---

## 12. Kayıtlı Öğrenme Notları

- **Reusable yapı çok önemli.** Tekrar kullanılabilir component’ler uzun vadede 5x azaltıyor refactor maliyetini.
- **İlk yayın öncelikle kendi kullanıcının beğenisini al.** İlk 14 gün içinde roller/izinler ve hata mesajlarını kullanıcı dostu hâle getir.
- **AI ile vibe coding yapmak hızlı ama güvenlik testi şart.** Özellikle giriş/üyelik verilerini asla hardcode etme.
- **Emülatör hatalarında önce soft reset sonra hard reset.** Gerçek cihaz/cloud build (Expo Go) ile test et.
- **App Store Connect formunu tek seferde doğru doldur.** Eksik/hatalı alan red nedenidir.

---

## 13. Komut Kısayolları

```bash
# Proje köküne git ve başlat
cd C:\Users\marko\OneDrive\Desktop\hermes_v7
npx expo start --clear
# İOS/Android açmak için tuş: i / a
```

---

## 14. Oturum Başı Yapılacaklar

1. Her session açılışında `npx expo --version` ve `node --version` kontrol et.
2. Önceki session’da kalmış cache/build dosyaları varsa temizle.
3. Eğer herhangi bir hata mesajı varsa önce bu skill’in 3. maddesini uygula.

---

_Eğer bu skill’in eksik bir bölümü varsa, ilgili sorunu gördüğünde hemen skill’i patch’le; her hatadan sonra öğrenilen her şeyi 12. maddede kaydet._

---

## 15. Admob + RevenueCat Referans

- Önce `npx expo prebuild --clean` çalıştır.
- AdMob: Test ID’leriyle geliştirme, sonra production ID’leri değiştir.
- RevenueCat: Store tarafı ürünleri önce oluştur, sonra entegre et.
- İlk model: **Free + Pro**; Plus katmanı kullanıcıyı karıştırma.
- 7 gün trial ekle; ödüllü reklam ile kredi/kısıtlı özellik aç.
- Normalleştirilmiş fiyat bandı: aylık ~$1.99–$2.00, yıllık ~$17.99.
