
> **Kategori:** system

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Windows System Automation_Windows Camera Capture |
| **Nerede?** | system/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: windows-camera-capture
description: Windows'ta USB/built-in webcam'dan video çekme, doğrulama ve Telegram'a gönderme. opencv-python-headless hatası, çözünürlük/fps ayarı, kare sayısı doğrulama ve Telegram Bot API gönderimi için.
title: "Windows Camera Capture"

audience: user
tags: [automation, camera, system, windows]
category: windows-system-automation---

# Windows Kamera Video Çekme

Windows'ta webcam'den 10 sn video alıp doğrulayıp Telegram'a gönder. Headless OpenCV tuzağı ve Telegram MEDIA etiket engeli için düzeltmeler içerir.

## Paket

- YANLIŞ: `opencv-python-headless` (GUI/A/V çekemez)
- DOĞRU: `opcv-python`
- Kurulum:
  ```powershell
  pip uninstall opencv-python-headless -y
  pip install opencv-python
  ```

## Kamera Açma (Windows DSHOW)

```python
import cv2
for idx in [0, 1, 2]:
    cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
    print('IDX', idx, 'OPENED', cap.isOpened())
    cap.release()
```

- `CAP_DSHOW` olmazsa `DirectShow` backend hatası alınır.
- Genellikle index 0 çalışır.

## Kayıt

```python
import cv2, time
out = r"C:\Users\marko\Desktop\kamera_test.mp4"
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
assert cap.isOpened(), "Kamera acilamadi"
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
writer = cv2.VideoWriter(out, cv2.VideoWriter_fourcc(*"mp4v"), 20.0, (w, h))
frames = 0
start = time.time()
while time.time() - start < 10:
    ret, frame = cap.read()
    if not ret:
        print("FRAME_READ_FAILED"); break
    writer.write(frame)
    frames += 1
cap.release(); writer.release()
print(f"RECORDED frames={frames}")
```

## Doğrulama (BOŞ DOSYA ÜRETME)

```python
import pathlib
p = pathlib.Path(out)
size = p.stat().st_size if p.exists() else 0
print(f"size={size} bytes")
# 0 byte ise "kayıt boş" de, başka index/uygulama(kullanım) sorunu var demektir.
```

## Telegram'a Gönder (MEDIA etiketi engeli)

`send_message` MEDIA etiketi bazen video iletmeyi reddeder. Alternatif:

```python
import requests, pathlib, re
env = pathlib.Path(r"C:\Users\marko\AppData\Local\hermes\.env")
token = None
for line in env.read_text().splitlines():
    if line.startswith("TELEGRAM_TOKEN="):
        token = line.split("=", 1)[1].strip(); break
assert token, "TELEGRAM_TOKEN_NOT_FOUND"
url = f"https://api.telegram.org/bot{token}/sendVideo"
with open(out, "rb") as f:
    files = {"video": (pathlib.Path(out).name, f, "video/mp4")}
    data = {"chat_id": "6328823909"}
    r = requests.post(url, data=data, files=files, timeout=60)
print("STATUS", r.status_code, "BODY", r.text)
```

## Arıza Giderme

- `FRAME_READ_FAILED` / 0 byte: Kamera başka uygulama tarafından kullanılıyor (Teams/Zoom/tarayıcı). Kullanıcı kapatmalı.
- `OPENED False` tüm indexlerde: Sürücü veya Windows kamera izni kapalı (Ayarlar > Gizlilik > Kamera).
- Telegram 400: Yanlış token/chat_id veya dosya bozuk.

## Kullanıcı Tercihi

- Ham çıktı beğenir. Ara açıklama/özet yapma.
- Her adımın gerçek çıktısını göster, "tamamlandı" deme, data ver.

## Referanslar

- `scripts/cam_capture_10s.py`: Basit 10 sn kayıt iskeleti
- `scripts/send_telegram_video.py`: .env’den token okuyan Telegram video gönderici
