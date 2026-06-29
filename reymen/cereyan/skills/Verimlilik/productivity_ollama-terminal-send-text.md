---
name: ollama-terminal-send-text
title: "Ollama Terminaline Metin Gönderme"
description: "Windows'ta VS Code içindeki Ollama uzantısı sohbet arayüzüne metin yazış ve gönderme adımları."
tags: [ollama, vscode, terminal, send-text, automation]
category: productivity
audience: user
triggers: [ollama metin gönder, ollama sohbet, VS Code ollama, ollama terminal]
---


> **Kategori:** productivity

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Windows'ta VS Code içindeki Ollama uzantısı sohbet arayüzüne metin yazış ve gönderme adımları. |
| **Nerede?** | productivity/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Ollama Terminaline Metin Gönderme

## Ön koşul
- VS Code açık ve Ollama uzantısı yüklü olmalı.
- Ollama sohbet penceresi açık olmalı.

## Adımlar

1. **VS Code'u öne çıkar**
   - PowerShell ile odaklanma komutu:
     ```
     powershell -ExecutionPolicy Bypass -File "C:\Users\marko\AppData\Local\hermes\scripts\vscode_focus_scoped.ps1"
     ```
   - Script `FOCUSED_VSCODE` çıktısı verirse VS Code ön plandadır.

2. **Ollama sohbet arayüzüne odaklan**
   - Sol taraftaki Ollama uzantısı simgesine tıkla (kedi/robot silüeti).
   - Eğer sohbet penceresi kapalıysa "New Chat" butonuna tıkla.

3. **Metni gönder**
   - Aşağıdaki VBS betiğini çalıştır:
     ```
     wscript "C:\Users\marko\AppData\Local\hermes\scripts\send_text_to_ollama.vbs"
     ```
   - Betik, Ollama sohbet alanına metni yazıp Enter'a basar.

4. **Ekran görüntüsü al doğrula**
   - `python C:\Users\marko\AppData\Local\hermes\scripts\screenshot_mss.py`
   - Görselde Ollama sohbetinde mesajın göründüğünü doğrula.

## Kaynaklar
- VS Code Ollama uzantısı
- HERMES otomasyon sistemleri
