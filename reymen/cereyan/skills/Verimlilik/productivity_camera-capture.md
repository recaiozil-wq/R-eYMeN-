
> **Kategori:** productivity

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Productivity_Camera Capture |
| **Nerede?** | productivity/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: camera-capture
description: Gerçek kamera fotoğrafı çekme, yeniden çekim, ekran görüntüsü alma, canlı kamera akışı ve Telegram'a gönderme.
title: "Camera Capture"

audience: user
tags: [camera, productivity, tools]
category: productivity---

# Kamera Fotoğraf Çekme

## Amaç
Bilgisayar başında olmadığımızda bile kameradan gerçek fotoğraf almak.
Ayrıca ekran görüntüsü yeniden çekip paylaşmak için kullanılır.

## Kayıt ve Yenileme Adımları

1. Kayıt yönergelerini güncelle.
2. Obsidian notunu güncelle.

## Yöntemler

### 1. Gerçek kamera fotoğrafı çekme
- Kod: `C:\Users\marko\AppData\Local\hermes\scripts\camera_real.py`
- Python: `C:\Users\marko\AppData\Local\Python\PythonCore-3.14-64\python.exe`
- Çıktı: `C:\Users\marko\Desktop\camera_real.jpg`
- Komut:
  ```
  cmd.exe /c "C:\Users\marko\AppData\Local\Python\PythonCore-3.14-64\python.exe" "C:\Users\marko\AppData\Local\hermes\scripts\camera_real.py"
  ```
- Doğrulama:
  ```
  ls -l "C:/Users/marko/Desktop/camera_real.jpg"
  ```
- Telegram gönderimi:
  ```
  send_message ile MEDIA:C:\Users\marko\Desktop\camera_real.jpg
  ```

### 2. Yeniden çekme (refresh)
Yeni fotoğraf dosyası aynı yolda yeniden yazılır. Kullanıcıya yeni çekim yapıldığı sinyalini ver ve dosyayı gönder.

### 3. Ekran görüntüsü — güvenilir yöntem
- Kod: `C:\Users\marko\AppData\Local\hermes\scripts\screenshot_mss.py`
- Python: `C:\Users\marko\AppData\Local\Python\PythonCore-3.14-64\python.exe`
- Çıktı: `C:\Users\marko\Desktop\screenshot.png`
- Komut:
  ```
  cmd.exe /c "C:\Users\marko\AppData\Local\Python\PythonCore-3.14-64\python.exe" "C:\Users\marko\AppData\Local\hermes\scripts\screenshot_mss.py"
  ```
- Doğrulama:
  ```
  ls -l "C:/Users/marko/Desktop/screenshot.png"
  ```
- Telegram gönderimi:
  ```
  send_message ile MEDIA:C:\Users\marko\Desktop\screenshot.png
  ```

### 4. Canlı kamera akışı
- Kod: `C:\Users\marko\AppData\Local\hermes\scripts\camera_stream.py`
- Arka planda başlatma:
  ```
  terminal(background=true, command="C:\Users\marko\AppData\Local\Python\PythonCore-3.14-64\python.exe C:\Users\marko\AppData\Local\hermes\scripts\camera_stream.py")
  ```
- Akış adresi: `http://localhost:8080/`

## Kullanıcı tercihi / kural
Kullanıcı, ekran görüntüsü veya kamera çekimi istediğinde bekleme, tekrar onay sorma veya zaten çalışan bir betiği tekrar yazma. Varolan skill’i kontrol et, önce mevcut yöntemi çalıştır, sorun olursa tekrar dene.

## Kaynaklar
- Fotoğraf betiği: `C:\Users\marko\AppData\Local\hermes\scripts\camera_real.py`
- Ekran görüntüsü betiği: `C:\Users\marko\AppData\Local\hermes\scripts\screenshot_mss.py`
- Canlı akış betiği: `C:\Users\marko\AppData\Local\hermes\scripts\camera_stream.py`
- Obsidian notu: `Hermes\Skills\productivity\camera-capture.md`
