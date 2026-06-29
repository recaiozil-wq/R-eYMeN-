---
title: "Emülatör Klavye Navigasyonu"
name: "emulator-klavye-navigasyonu"
description: "Android emülatörüne fare tıklaması ile odaklanıp klavye kısayollarıyla gezinme yöntemi"
category: windows-automation
audience: user
tags: [automation, tor, windows]
author: Hermes
version: 1.0
---


> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Android emülatörüne fare tıklaması ile odaklanıp klavye kısayollarıyla gezinme yöntemi |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Emülatör Klavye Navigasyonu

Emülatör üzerinde UI otomasyonu yaparken ADB `input tap X Y` koordinatları yerine, önce pencereye tıkla/odaklan, sonra klavye kısayollarıyla ilerle.

## Neden Bu Yöntem?

- Koordinat hesaplamaya gerek yok
- Ekran çözünürlüğü değişse bile çalışır
- Daha hızlı ve güvenilir

## Adımlar

### 1. Pencereyi Aktif Et (Odakla)

```bash
python C:\Users\marko\hermesmouse.py click X Y
```

Veya emülatör içinde bir öğeye tıkla:
```bash
/c/Users/marko/AppData/Local/Android/Sdk/platform-tools/adb.exe shell input tap X Y
```

### 2. Klavye Kısayolları ile Navigasyon

| Tuş | İşlev |
|-----|-------|
| `Tab` | Sonraki öğeye git (buton, alan) |
| `Shift + Tab` | Önceki öğeye git |
| `Enter` | Seçili öğeyi onayla/tıkla |
| `Space` | Onay kutusunu işaretle |
| `Escape` | Dialogu kapat/iptal et |
| `Alt + F4` | **Windows:** Pencereyi kapat |
| `Alt + Tab` | **Windows:** Diğer pencereye geç |
| `Ctrl + Tab` | **Emülatör:** Sekme değiştir |

### 3. Emülatörde Klavye Gönderme

ADB üzerinden klavye tuşu gönderme:
```bash
adb shell input keyevent KEYCODE_TAB     # Tab
adb shell input keyevent KEYCODE_ENTER    # Enter
adb shell input keyevent KEYCODE_DPAD_UP  # Yukarı ok
adb shell input keyevent KEYCODE_DPAD_DOWN # Aşağı ok
```

### 4. UI Otomasyonu İle Keşfet

Önce UI dump al, butonların ne olduğunu gör:
```bash
adb shell uiautomator dump /sdcard/ui.xml
adb pull /sdcard/ui.xml
```

Sonra text'ten hangi butona basılacağını bul (Tab ile sırayla git).

### 5. Pratik Örnek — İzin Dialogu

Mikrofon/Bildirim izni dialogunda:
1. `Tab` ile "Allow" / "While using the app" butonuna git
2. `Enter` ile onayla
3. Dialog kapanır

## Faydalı Keycode'lar

| KEYCODE | Değer | İşlev |
|---------|-------|-------|
| KEYCODE_TAB | 61 | Tab |
| KEYCODE_ENTER | 66 | Enter |
| KEYCODE_DPAD_UP | 19 | Yukarı |
| KEYCODE_DPAD_DOWN | 20 | Aşağı |
| KEYCODE_DPAD_LEFT | 21 | Sol |
| KEYCODE_DPAD_RIGHT | 22 | Sağ |
| KEYCODE_BACK | 4 | Geri |
| KEYCODE_HOME | 3 | Ana ekran |
| KEYCODE_MENU | 82 | Menü |
| KEYCODE_DEL | 67 | Sil (Backspace) |

## Önemli

- Önce pencereye tıkla (aktif et), **sonra** klavye tuşları çalışır
- hermesmouse.py kullan: `python C:\Users\marko\hermesmouse.py click X Y`
- ADB input keyevent emülatörün iç komutudur, pencerenin odaklı olması gerekmez
- Klavye kısayolları (Tab/Enter) **pencerenin odaklı olmasını gerektirir**
