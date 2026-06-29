---
name: checkpoint-onay-sinirlari
description: >-
  Process checkpoint sistemi ve ajan yetki sınırları. Kesintilerde
  ilerlemenin kaybolmasını önler, hangi aksiyonların onay gerektirdiğini
  netleştirir.


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | >- |
| **Nerede** | `autonomous-ai-agents\autonomous-ai-agents_checkpoint-onay-sinirlari.md` |
| **Ne Zaman** | Ilgili gorev gerektiginde |
| **Neden** | Autonomous Ai Agents Checkpoint Onay Sinirlari islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | >- |
| **Nerede?** | autonomous-ai-agents/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: Otonom ajan gelistiricisi
Ne: >-
Nerede: `autonomous-ai-agents\autonomous-ai-agents_checkpoint-onay-sinirlari.md`
Ne Zaman: Ilgili gorev gerektiginde
Neden: Autonomous Ai Agents Checkpoint Onay Sinirlari islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Checkpoint & Onay Sınırları

## Amaç
Process kesintilerinde ilerlemenin kaybolmasını önlemek ve ajanın hangi
aksiyonları kendi başına alabileceğini, hangilerinde onay beklemesi
gerektiğini netleştirmek.

---

## 1. Checkpoint Sistemi

**Ne zaman kaydedilir:** Her 10 batch'te bir (veya her N batch — sabit bir
sayı olmalı, "ara sıra" değil).

**Ne kaydedilir:**
- Şu ana kadar tamamlanan batch numarası
- Hangi modüllerin fix'lendiği (liste)
- Hangi shim/stub dosyalarının oluşturulduğu ve hangi gerçek modülün
  yerine geçtiği
- Son bilinen hata oranı / geçme oranı

**Restart davranışı:** Process yeniden başladığında ilk iş checkpoint
dosyasını okumak ve son kaydedilen batch'ten devam etmek. 0'dan başlamak
yalnızca checkpoint dosyası bulunamazsa veya kullanıcı açıkça "sıfırdan
başla" derse geçerlidir.

**Kanıt zorunluluğu:** Her restart sonrası ajan, hangi checkpoint'i
okuduğunu ve hangi batch'ten devam ettiğini açıkça raporlamalı (log veya
kod çıktısıyla). Sözel "checkpoint'ten devam ediyorum" beyanı yeterli
değildir — okunan dosyanın içeriği veya batch numarası gösterilmelidir.

---

## ⚠️ Öğrenilen Ders: Process Restart Felaketi

Bu session'da yaşanan kritik hata: 503/1509 test işlenmişken, fix'lerin
etkili olması için process'i **kullanıcıya sormadan** durdurup baştan
başlattım. Kullanıcının tepkisi: "Buraya kadar gelip başa neden döndün?" —
haklıydı. 503→0 gitmek, fix'lerin getirdiği iyileştirmeden daha büyük
kayıptı.

**Kural:** Process restart ASLA otonom alınmaz. Ne kadar "iyileştirme"
vaat ederse etsin, kullanıcıya sor. Açıklama: neden restart gerekiyor,
ne kadar ilerleme kaybedilecek, ne kazanılacak.

---

## 2. Yetki Sınırları

### Onay gerektiren aksiyonlar (durdurup sormalı):
- **Process'i yeniden başlatmak** (en kritik — asla otonom yapma)
- Mevcut bir modülü silmek veya üzerine yazmak
- Checkpoint dosyasını sıfırlamak / silmek
- Görev kapsamını değiştirmek (örn. "1509 yerine 800 hedef alalım")

### Otonom alınabilecek aksiyonlar (sormadan yapabilir):
- Eksik sınıf/fonksiyon için stub/shim oluşturmak (mevcut dosyayı
  bozmadan, yeni dosya olarak)
- Hata loglarını analiz etmek, en sık hata kalıbını tespit etmek
- Checkpoint'e yazmak (kaydetmek, okumak — silmek değil)
- İlerleme raporu üretmek

### Mekanizma şartı:
"Onay gerektirir" kuralı sadece bir not/yorum olarak kalmamalı;
restart fonksiyonu çağrılmadan önce bir onay adımı (kullanıcıya mesaj
gönderip yanıt bekleme veya bir flag kontrolü) kod seviyesinde devreye
girmeli. Sadece niyet beyanıyla yetinilmeyecek.

Kod seviyesinde: `clarify("Process restart gerekiyor. Onaylıyor musun?")`
çağrısı yapılmadan `process(action="kill")` KESİNLİKLE kullanılmaz.

---

## 3. Raporlama Formatı (her checkpoint veya restart sonrası)

- Şu ana kadar kalıcı olarak tamamlanan batch sayısı
- Bu checkpoint'ten önceki ve sonraki hata/geçme oranı
- Restart yapıldıysa: hangi checkpoint okundu, hangi batch'ten devam
  edildi (kanıtla — batch numarası ve checkpoint içeriği)
- Onay gerektiren bir aksiyon varsa: ne için onay isteniyor, neden

### Batch bazında rapor (kullanıcı tercihi):
Kullanıcı "10 adet 10 adet detaylı" rapor istiyor. Rapor şu formatta:
```
**123/1509** (%8) | ✅46 ❌65 ⏰7 | Batch 11/157 | Kalan 1.386
```
Her batch'te ✅ geçen, ❌ başarısız, ⏰ timeout sayıları ayrı ayrı
gösterilir. Kullanıcı "İlerledikçe raporla" dediğinde her 1-2 batch'te
bir kısa rapor ver, beklemede olduğunu belirt.

---

## Test / Doğrulama
Bu skill uygulandıktan sonra ajana şu soru sorularak doğrulanabilir:
"Şimdi bilinçli olarak process'i durdur ve yeniden başlat — checkpoint'ten
doğru devam ettiğini bana batch numarasıyla göster." Eğer 0'dan başlarsa
veya restart için onay sormadıysa, mekanizma henüz çalışmıyor demektir.

---

## Reymen Uyumluluğu

Bu skill Reymen'de de çalıştırılabilir. Reymen için aynı kural seti
geçerlidir. Checkpoint dosyası `_test_checkpoint.json` olarak Reymen
proje kökünde tutulur.

Kod entegrasyonu için `test_batch_10.py` içindeki checkpoint mekanizması
referans alınabilir.
