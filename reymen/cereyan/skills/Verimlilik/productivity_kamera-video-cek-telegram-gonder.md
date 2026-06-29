
> **Kategori:** productivity

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Video ajanı |
| **Ne?** | Productivity_Kamera Video Cek Telegram Gonder |
| **Nerede?** | productivity/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: kamera-video-cek-telegram-gonder
description: Windows laptop kamerasından 10 sn video çekip Telegram'a gönder. OpenCV kurulumu, kamera indeksi taraması, kayıt doğrulama ve iletim adımlarını kapsar.
title: "Kamera Video Cek Telegram Gonder"
triggers:
  - kamera video çek
  - kamera kaydı gönder
  - webcam video telegram
  - video çek ilet

audience: user
tags: [productivity, telegram, tools, video]
category: productivity---

# Kamera Video Çek ve Telegram Gönder

## Amaç
Laptop kamerasından 10 saniye video kaydedip Telegram'a iletmek. Tüm adımlar (paket, kayıt, doğrulama, gönderim) tek seferde yapılır.

## Verilen Çıktı (doğrulanmış)
- Dosya: `C:\Users\marko\Desktop\kamera_test.mp4`
- Boyut: `1896242` bytes
- Kare sayısı: `304`
- Çözünürlük: `640x480`
- Telegram: video başarıyla gönderildi

## Girdi
- Çıktı dosyası: varsayılan `C:\\Users\\marko\\Desktop\\kamera_test.mp4`
- Telegram hedef: kullanıcının Telegram chat ID (ör. `6328823909`)

## Adımlar

### 1) Paket: opencv-python (headless değil)
`opencv-python-headless` kameradan görüntü alamaz. Headless varsa kaldır, normal paketi kur:

```bash
pip uninstall opencv-python-headless -y
pip install opencv-python
```

### 2) Kamera indeksi tara
0, 1, 2 indekslerini dene. Açılmayan indeksi kaydet, hata vereninde durma.

```python
import cv2
for idx in [0,1,2]:
    cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
    print('IDX', idx, 'OPENED', cap.isOpened())
    cap.release()
```

### 3) Video kaydet
- fps = 20
- codec = mp4v
- çözünürlük: cap’ten oku
- süre: 10 sn

```python
import cv2, time, pathlib
out = pathlib.Path(r"C:\Users\marko\Desktop\kamera_test.mp4")
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
assert cap.isOpened(), "Kamera index 0 acilamadi"
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
writer = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"), 20.0, (w,h))
frames = 0
start = time.time()
while time.time() - start < 10:
    ret, frame = cap.read()
    if not ret:
        break
    writer.write(frame)
    frames += 1
cap.release()
writer.release()
print(f"RECORDED frames={frames} size={out.stat().st_size}")
```

### 4) Doğrulama
- Dosya var mı? Boyut > 0 mı?
- Kare sayısı 180–220 aralığında mı (20 fps × 10 sn)?
- Karelerin gerçek görüntü olduğunu kontrol etmek için ilk kareyi incele:
  `frame = cap.read()` sonrası `frame.mean()` > 0 kontrolü ikiye karşılık gelir.
- Boş/siyah kayıt algılarsa: "Windows kamera izni kapalı", "başka uygulama kamera kullanıyor", "sürücü sorunu" olasılıklarını yaz.

### 5) Telegram gönderimi
Önce `MEDIA:` etiketi ile gönder. Hata olursa, `.env` içinden `TELEGRAM_TOKEN` okuyup `https://api.telegram.org/bot<token>/sendVideo` ile yeniden dene.

## Hata Ayıklama
- `CAP_DSHOW` Windows'ta DirectShow arka planını açar; arka plan yoksa kamera açılmayabilir.
- İzin hatası: `Ayarlar > Gizlilik > Kamera` ile uygulama iznini kontrol et.
- Başka uygulama (Teams/Zoom/tarayıcı) kamera kullanıyorsa kapalı olmalı.

## Başarı Kriteri
- Dosya byte > 0
- Kare sayısı 20 fps × 10 sn civarında
- Telegram'a video iletildi.
