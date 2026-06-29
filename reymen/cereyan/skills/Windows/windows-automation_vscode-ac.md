---
name: vscode-ac
title: "VS Code Aç / Odakla"
description: "VS Code'u öne getir (zaten açıksa) veya aç (kapalıysa). Ekran görüntüsü al ve Telegram'a gönder."
tags: [vscode, focus, open, vs-code]
category: windows-automation
audience: user
triggers: [vs code ac, vscode ac, vscode aç, visual studio code]
related_skills: [open_vscode_claude_terminal, claude-agent-terminal-send-text]
---


> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | VS Code'u öne getir (zaten açıksa) veya aç (kapalıysa). Ekran görüntüsü al ve Telegram'a gönder. |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# VS Code Aç / Odakla

## Amaç
VS Code'u öne getir. Zaten açık değilse yeni başlat.

## Adımlar

### 1. VS Code'u öne getir
```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\marko\AppData\Local\hermes\scripts\vscode_focus_scoped.ps1"
```

**Beklenen çıktı:** `FOCUSED_VSCODE` (hatalar yok sayılır)
**Bilinen hata:** `[FocusWin]::IsIconic($h)` hatası PowerShell sürümü kaynaklıdır — yok say, `FOCUSED_VSCODE` görünüyorsa çalışmıştır.

### 2. Ekran görüntüsü al (doğrulama)
```powershell
powershell -ExecutionPolicy Bypass -Command "& 'C:\Users\marko\AppData\Local\Python\PythonCore-3.14-64\python.exe' 'C:\Users\marko\AppData\Local\hermes\scripts\screenshot_v2.py'"
```
Çıktı: `C:\Users\marko\AppData\Local\hermes\scripts\screen.png`

### 3. Doğrula ve bildir
- Model vision destekliyorsa → `vision_analyze` ile kontrol et
- Model vision desteklemiyorsa → ekran görüntüsünü Telegram'a gönder:
  ```
  MEDIA:C:\Users\marko\AppData\Local\hermes\scripts\screen.png
  ```
- Kullanıcıya "VS Code açıldı ✅" olarak bildir.

## Bilinen Durum
- 2026-06-03: "Aynen açıldı" — kullanıcı teyit etti ✅
