---
name: takili-kalma
description: Karmaşık görevlerde takılı kalmayı önleyen otomatik kural seti. Ekran okuyarak aktif konuyu tespit eder, Tor/web'de araştırma yapar, çözüm bulamazsa Telegram kurtarma sinyali gönderir.
title: "Takili Kalma"
category: self-improvement
audience: user
tags: [agents, ai, automation]


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Karmaşık görevlerde takılı kalmayı önleyen otomatik kural seti. Ekran okuyarak aktif konuyu tespit eder, Tor/web'de araştırma yapar, çözüm bulamazsa Telegram kurtarma sinyali gönderir. |
| **Nerede** | `autonomous-ai-agents\autonomous-ai-agents_takili-kalma.md` |
| **Ne Zaman** | Ilgili gorev gerektiginde |
| **Neden** | Autonomous Ai Agents Takili Kalma islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Karmaşık görevlerde takılı kalmayı önleyen otomatik kural seti. Ekran okuyarak aktif konuyu tespit eder, Tor/web'de araştırma yapar, çözüm bulamazsa Telegram kurtarma sinyali gönderir. |
| **Nerede?** | autonomous-ai-agents/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: Otonom ajan gelistiricisi
Ne: Karmaşık görevlerde takılı kalmayı önleyen otomatik kural seti. Ekran okuyarak aktif konuyu tespit eder, Tor/web'de araştırma yapar, çözüm bulamazsa Telegram kurtarma sinyali gönderir.
Nerede: `autonomous-ai-agents\autonomous-ai-agents_takili-kalma.md`
Ne Zaman: Ilgili gorev gerektiginde
Neden: Autonomous Ai Agents Takili Kalma islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# TAKILI KALMA KURALI

Her karmaşık görevde (3+ adım) bu kuralları uygula:

## 1. Adım Tekrarı Kontrolü
- Aynı adımı 2 kez tekrarlarsan **DUR** ve farklı bir yöntem dene.
- Tekrar eden adımı tespit ettiğinde "Bu adım daha önce denendi, alternatif yönteme geçiyorum" de ve rotayı değiştir.

## 2. Todo Döngüsü Koruması
- "Preparing todo" veya benzeri planlama döngüsüne girersen **HEMEN DUR**.
- Görevi daha küçük parçalara böl (maksimum 1-2 işlem içeren mini-adımlar).
- Planlamak yerine doğrudan ilk küçük adımı uygulamaya başla.

## 3. İlerleme Kilidi
- 3 denemede ilerleme yoksa modeli değiştir:
  ```
  /model deepseek-v4-pro
  ```
- Model değişimini kullanıcıya bildir ve yeni modelle devam et.
- Aynı modelle 3 başarısız deneme = model değiştirme zorunluluğu.

## 4. Uygulama Sırası
1. Görev karmaşıksa (3+ adım) bu kuralları yükle.
2. Her adımda ilerleme kaydedip kaydetmediğini kontrol et.
3. Kural tetiklenirse hemen durumu raporla ve alternatife geç.

## 5. Aktif Konuyu Tespit Et (Takılı Değilse Bile)
- Kullanıcı "araştırma yap", "şu konuda çalış" gibi bir talimat verdiğinde ama **takildi.txt yoksa** (Hermes takılı değilse):
  1. **Önce ekran görüntüsü al** — PowerShell ile screenshot çek:
     ```
     powershell.exe -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; $bmp = New-Object System.Drawing.Bitmap([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width, [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height); $g = [System.Drawing.Graphics]::FromImage($bmp); $g.CopyFromScreen((New-Object System.Drawing.Point(0,0)), (New-Object System.Drawing.Point(0,0)), $bmp.Size); $bmp.Save('C:\Users\marko\Desktop\screen_debug.png', [System.Drawing.Imaging.ImageFormat]::Png); $g.Dispose(); $bmp.Dispose(); Write-Output 'OK'"
     ```
  2. **Görseli JPEG'e çevir** (PIL ile, RGBA'dan RGB'ye dönüştür):
     ```python
     from PIL import Image
     img = Image.open('screen_debug.png')
     if img.mode == 'RGBA': img = img.convert('RGB')
     img = img.resize((1280, 720), Image.LANCZOS)
     img.save('screen_small.jpg', 'JPEG', quality=60)
     ```
  3. **vision_analyze ile oku** — ekranda ne görünüyor, hangi uygulamalar açık, Hermes'in terminalinde ne yazıyor, hata var mı?
  4. **NOT:** DeepSeek gibi vision desteklemeyen modellerde fallback görsel işleme otomatik çalışır — vision_analyze yine de dene, model desteklemezse hata döner, o zaman alternatif yöntem dene.
  5. **Ekran yorumundan aktif konuyu çıkar** — hangi cihaz/hedef üzerinde çalışılıyor, hangi araç kullanılıyor, blokaj ne?
  6. **Blokajı çöz veya araştırmaya başla** — tespit edilen konuda ilerle.
  7. **Kullanıcıya raporla:** "Hermes şu an \<konu\> üzerinde çalışıyor, blokaj \<sorun\>, çözüm için \<adım\> yapıyorum"
- Eğer Hermes takılı değilse ve aktif konu tespit edilemezse kullanıcıya sor: "Hermes'in hangi konuda araştırma yapmasını istiyorsun?"

## 6. Önce Kendin Araştır (Tor + Web Search) [ESKİ 5]
- Yukarıdaki tüm yöntemler başarısız olursa (adım tekrarı + todo döngüsü + model değişimi + aktif konu tespiti çözmedi) **HEMEN** kendi araştırmanı başlat:
  1. **Önce web_search dene** (varsa normal web araması — provider'da firecrawl veya benzeri varsa)
  2. **web_search çalışmazsa veya yoksa Tor ile dene:**
     ```
     python C:\\Users\\marko\\hermestor.py search "sorunun anahtar kelimeleri"
     ```
  3. **NOT: DuckDuckGo (hermestor.py search) bazen "Sonuc bulunamadi" döndürür** — Tor çıkış IP'si bloke olmuş olabilir. Bu durumda alternatif yöntemler dene:
     - `python C:\\Users\\marko\\hermestor.py proxy "https://www.google.com/search?q=sorgu"` (Google Tor üzerinden)
     - `python C:\\Users\\marko\\hermestor.py start` ile Tor'u yeniden başlat (yeni devre)
     - Detaylı alternatifler: tor-browser-arama skill'inin `references/duckduckgo-fallback.md` dosyasına bak
  4. **Hâlâ çözüm yoksa** farklı anahtar kelimelerle tekrar dene (max 3 farklı sorgu)
  5. **Hepsi başarısız olursa** Telegram Kurtarma Sinyali'ne geç

## 7. Background Task Delegation (Async Çalışma)
- Kullanıcı bir görev verdiğinde **HEMEN arkaya at**, bitene kadar bekleme.
- **Script/komut işiyse:** terminal(background=true, notify_on_complete=true) ile çalıştır.
- **AI/analiz işiyse:** delegate_task veya cronjob(action='run') ile arkada işlet.
- Kullanıcıya hemen "Tamam, arkada çalışıyor, bitince haber veririm" cevabını ver.
- Kullanıcı başka soru yazmaya devam edebilir, iş bitince bildirim düşer.
- **ASLA** kullanıcıyı iş bitene kadar bekletme — synchronous çalışma şikayet sebebidir.
- **Batch test isiysa (50+ dosya):** checkpoint sistemi kullan. `checkpoint-onay-sinirlari` skill'ine bak. Her N batch'te bir JSON checkpoint kaydedilir, process restart'ında 0'dan değil checkpoint'ten devam edilir. Onay gerektiren aksiyonlar: process restart, checkpoint silme. Otonom: checkpoint kaydetme/okuma, shim oluşturma, hata analizi.

## 8. Telegram Kurtarma Sinyali
- Tüm kendi araştırma yöntemleri başarısız olursa **HEMEN** şu dosyayı oluştur:
  ```
  C:\\Users\\marko\\takildi.txt
  ```
  İçine şu formatı yaz:
  ```
  SORUN: <kısa hata/ne yapmaya çalıştığın>
  ADIM: <takıldığın adım>
  DENENEN: <denenen çözümler>
  ANAHTAR_KELIMELER: <Tor'da denenen sorgular>
  ```
- Dosyayı oluşturduktan sonra bekle — Telegram'daki Hermes gelip sorunu okuyacak, daha derin Tor'da araştırma yapacak ve çözümü bildirecek.
- Çözüm gelince dosya otomatik silinecek ve kaldığın yerden devam edebileceksin.
- **ÖNEMLİ:** Bu sinyal DOSYA BAZLI çalışır — process sinyali, HTTP veya socket değil. Dosyayı yazmak için `write_file` veya PowerShell `Out-File` kullan.
- Detaylı akış şeması ve kısıtlar için `references/kurtarma-akisi.md` dosyasına bak.

## 9. Cokus Raporu (Alternatif Kurtarma)

Telegram sinyali yerine veya ek olarak, yapılandırılmış crash raporu da üretilebilir. Özellikle hata geçmişi ve denenen ajanların kaydı önemliyse:

```python
from cokus_raporlayici import cokus_raporu_uret
rapor = cokus_raporu_uret(
    gorev="gorev tanimi",
    deneme_sayisi=5,
    hata_gecmisi=hata_listesi,
    denenen_ajanlar=ajan_listesi
)
# Rapor .ReYMeN/cokus_raporlari/ klasorune kaydedilir
```

Detay: `otonom-cozum-dongusu` skill'indeki "Cokus Raporlayici" bolumu ve `references/yapilandirilmis-gorev-formati.md`.

## Pitfalls
- Küçük görevlerde (1-2 adım) bu kuralı uygulama, gereksiz yere yavaşlatır.
- Kullanıcı "dur" veya "stop" derse tüm kontrolleri bırak, hemen dur.
- Model değiştirmeden önce kullanıcıya sorma — otomatik yap.
- Sinyal dosyasını sadece GERÇEKTEN takıldığında oluştur, her küçük hatada değil.