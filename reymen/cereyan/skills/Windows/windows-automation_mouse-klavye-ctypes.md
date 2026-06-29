---
name: mouse-klavye-ctypes
title: "Hermes Mouse + Klavye Kontrolü (v5)"
description: "Windows'ta fare ve klavye kontrolü — ctypes ile (bağımlılıksız, Win32 API). Hermes'ten uygulama açma, element tıklama, menü gezinme, metin yazma, otonom akış yürütme, ekran görüntüsü alma."
version: 5.0.0
author: marko
license: MIT
platforms: [windows]
audience: user
tags: [mouse, click, keyboard, scroll, sweep, ctypes, win32, automation, windows, element, uia, workflow, screenshot]
related_skills: [tam-sistem-yetkisi, screen-vision-analiz, windows-automation-shortcuts]
---


> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Windows'ta fare ve klavye kontrolü — ctypes ile (bağımlılıksız, Win32 API). Hermes'ten uygulama açma, element tıklama, menü gezinme, metin yazma, otonom akış yürütme, ekran görüntüsü alma. |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Hermes Mouse + Klavye Kontrolü (v5)

## Genel Bakış

`C:\Users\marko\hermesmouse.py` — 900+ satır, 0 dış bağımlılık.
Win32 API + PowerShell UIAutomation + GDI ile tam Windows otomasyonu.

pyautogui veya PowerShell Forms'a ihtiyaç duymaz.

## Komutlar

### Koordinat Bazlı
```bash
python hermesmouse.py pos                              # fare konumu
python hermesmouse.py status                           # ekran + DPI + elevation
python hermesmouse.py move <x> <y>                     # yumuşak hareket
python hermesmouse.py move <x> <y> --fast              # anlık hareket (SendInput)
python hermesmouse.py drag <x1> <y1> <x2> <y2>        # sürükle
python hermesmouse.py click <x> <y>                    # sol tık
python hermesmouse.py rclick <x> <y>                   # sağ tık
python hermesmouse.py dclick <x> <y>                   # çift tık
python hermesmouse.py scroll <delta>                   # kaydırma (+/-)
python hermesmouse.py sweep [cx cy r]                  # daire çiz (demo)
```

### Klavye
```bash
python hermesmouse.py type <metin>                     # Unicode yazı (Türkçe dahil)
python hermesmouse.py key <tus/kombinasyon>            # tuş gönder
# Örnekler:
python hermesmouse.py key enter
python hermesmouse.py key esc
python hermesmouse.py key "ctrl+s"
python hermesmouse.py key "ctrl+shift+esc"
python hermesmouse.py key "alt+f4"
```

### Element (UI Automation) — Detay: references/element-ve-workflow.md
```bash
python hermesmouse.py element "Pencere" list
python hermesmouse.py element "Pencere" "Buton" click
```

### Otonom Akış (Workflow) — Detay: references/element-ve-workflow.md
```bash
python hermesmouse.py run akis.json
python hermesmouse.py run akis.txt
```

### Global Flag'ler
```bash
--verbose     debug log (DPI, elevation, UIA çağrıları)
--timeout N   element bulamazsa N saniye yeniden dene (0 = tek deneme)
```

## Python API
```python
import sys
sys.path.insert(0, r"C:\Users\marko")
import hermesmouse as hm

hm.move(800, 400)          # yumuşak hareket
hm.click(200, 150)         # sol tık
hm.type_text("Merhaba!")   # Unicode yazı
hm.press_key("ctrl+s")     # tuş kombinasyonu
x, y = hm.get_pos()        # fare konumu
```

## Detaylı Başvuru
| Konu | Dosya |
|------|-------|
| Element bulma + Workflow motoru | references/element-ve-workflow.md |
| Çalışma prensipleri + Sınırlamalar | references/calisma-prensipleri.md |
| Test durumu + Yaygın tuzaklar | references/test-ve-tuzaklar.md |

## Test Durumu
109 test, 108 başarılı. Tüm komutlar gerçek Windows'ta test edildi.
