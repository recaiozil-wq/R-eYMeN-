
> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Windows Automation_Ollama Baslat Ekran Goster |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: ollama-baslat-ekran-goster
description: Belirtilen Ollama exe yolunu başlatıp hemen ekran görüntüsü al.
title: "Ollama Baslat Ekran Goster"
triggers:
  - ollama exe başlat
  - ollama uygulamasını aç ve ekran görüntüsü al
  - ollama ekran kontrolü

audience: user
tags: [automation, windows]
category: windows-automation---

# Ollama Başlat ve Ekran Göster

## Kullanım

`ollama_baslat_ve_goruntule()` fonksiyonunu çağırarak çalıştır.

## Kurallar

1. Bu skill Windows'ta çalışır.
2. Başlatılacak yol: `C:\Users\marko\AppData\Local\Programs\Ollama\ollama app.exe`
3. Eğer önceden çalışan bir Ollama instance'ı varsa, mevcut pencereyi öne getir ve sadece ekran görüntüsü al.
4. Ekran görüntüsü çözünürlüğü: önce tam ekran dene; Windows ekran görüntüsü API başarısız olursa `pyautogui` ile düşük çözünürlükte fallback al.
5. Ekran kaydı varsayılan olarak masaüstüne: `C:\Users\marko\Desktop\ekran_gorselleri\ollama_ekran_<timestamp>.png`

## Çalıştırma Adımları

- `ollama app.exe`'yi çalıştır.
- Kısa bir gecikme sonrası ekran görüntüsü al.
- Sonucu şu formatta bildir:
  - "Çalıştı"
  - "Ekran kaydı: <yol>"
  - "Durum: OK / HATA"
