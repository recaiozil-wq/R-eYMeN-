---
name: openai-screenshot
title: "Openai Screenshot"
tags: [ai, productivity, screen]
description: "OS-level screenshot and capture tooling for desktop, window, and region captures. Camera hardware capture is delegated to `camera-capture`."
version: 1.2.0
author: marko
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [screenshot, desktop, capture, windows, keyboard shortcut]
audience: user
related_skills: [windows-system-automation, obsidian, gorsel-onaylama]
---


> **Kategori:** productivity

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | OS-level screenshot and capture tooling for desktop, window, and region captures. Camera hardware capture is delegated to `camera-capture`. |
| **Nerede?** | productivity/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Screenshot Capture

## Yöntem Seçimi (Kullanıcı tercihine göre)

- **Win + Shift + S** → En işlevsel yöntem. Ekranın bir kısmını, belirli bir pencereyi veya tüm ekranı seçip doğrudan panoya kopyalamanıza (veya dosyaya kaydetmenize) olanak tanır.
- **Print Screen (PrtScn)** → Tüm ekranın görüntüsü panoya kopyalanır.
- **Win + Print Screen** → Tüm ekranın görüntüsünü otomatik olarak "Resimler > Ekran Görüntüleri" klasörüne dosya olarak kaydeder.
- **Alt + Print Screen** → Sadece aktif olan (o an üzerinde çalıştığınız) pencerenin görüntüsünü panoya alır.

## Kullanım

1. Kullanıcı ekran görüntüsü istediğinde yukarıdaki yöntemlerden uygun olanı tetikle.
2. En hızlı ve kontrol edilebilir yöntem **Win + Shift + S**’tir.
3. Görüntü alındıktan sonra panodaki içeriği `C:\Users\marko\Desktop\screenshot.png` olarak kaydet.
4. Dosya var mı? Boyutunu kontrol et.
5. Görseli gondermek/göstermek için ekteki medya akışını kullan.

## Gerçek Kamera Çekimi (Donanım)

Kullanıcı **ekran görüntüsü değil** gerçek kamera fotoğrafı istiyorsa, sistem PowerShell/WinRT yolları denemek, sonra OpenCV yolu üzerinden çekim yapmak daha güvenilir.

**Onaylı komut zinciri:**
1. Kamera uygulamasını aç: `cmd.exe /c start microsoft.windows.camera:`
2. Space tuşuyla UI çekimi denemek **kullanıcı odaklı değilse kaçın**.
3. Doğrudan kamera çekimi: `"C:\Users\marko\AppData\Local\Python\PythonCore-3.14-64\python.exe" "C:\Users\marko\AppData\Local\hermes\scripts\camera_real.py"`
4. Çıktı: `C:\Users\marko\Desktop\camera_real.jpg`

**Bilinen sınırlar:**
- PowerShell 5.1 ile WinRT `MediaCapture` tipi genellikle bulunamaz.
- Python 3.14 için `pip install winrt` dağıtımı olmayabilir / import hata verebilir.
- OpenCV yüklü ise gerçek kamera çekimi daha güvenilir sonuç verir.

### Pitfall: stdout ekran kayması

**ÇÖZÜLDÜ**: OpenCV ile kamera çekiminde `cap.read()` boolean döner, False durumunda `OK_READ` mesajı akışa bulaşmadan önce yazılıyor ve bozuluyor.

`camera_real.py` sonucunu aşağıya yaz. Dosya gönderme için `MEDIA:` prefix kullan.
