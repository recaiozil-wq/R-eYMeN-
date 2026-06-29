---
name: windows-automation-shortcuts
description: Tüm Windows otomasyon script'leri için klavye kısayol atama rehberi + AutoHotkey script. Özel Script olanlara Ctrl+Alt+Harf atar, Windows doğal kısayolu olanları listeler.
title: "Windows Automation Shortcuts"
version: 2.1.0
tags: [ahk, autohotkey, shortcuts, kısayol, startup, windows, otomasyon, daemon, listener]
category: windows-automation
audience: user
related_skills: [mouse-klavye-ctypes, skill-obsidian-first-check, obsidian-vault-kurallari]
---


> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Tüm Windows otomasyon script'leri için klavye kısayol atama rehberi + AutoHotkey script. Özel Script olanlara Ctrl+Alt+Harf atar, Windows doğal kısayolu olanları listeler. |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Windows Otomasyon Kısayol Atama

Bu skill, `windows-automation` kategorisindeki tüm script'leri iki gruba ayırır:

1. **Windows doğal kısayolu olanlar** — zaten var, kullan
2. **Özel Script olanlar** — AutoHotkey ile `Ctrl+Alt+Harf` atanır

## Merkezi Kısayol Haritası

Tüm kısayolların güncel listesi Obsidian vault'ta:

```
C:\Users\marko\OneDrive\Belgeler\Obsidian Vault\Hermes_Shortcut_Map.md
```

Hermes her göreve başlamadan önce bu haritayı kontrol eder (`skill-obsidian-first-check`).

## Grup 1 — Windows Doğal Kısayolu Olanlar

Bu işlemlerin Windows'ta zaten bir kısayolu var. Doğrudan kullanılabilir.

| İşlem | Kısayol |
|-------|---------|
| aktif-pencere (geçiş) | `Alt + Tab` |
| aktif-pencere (tam ekran) | `Win + Yukarı Ok` |
| bilgisayari-kapat | `Win + X, U, U` |
| ekran-al | `PrtScn` veya `Win + Shift + S` |
| gorev-yoneticisi | `Ctrl + Shift + Esc` |
| guvenlik-ekrani | `Win + L` (kilit) veya `Ctrl + Alt + Del` |
| windows-screen-capture | `Win + Shift + S` |
| yeniden-baslat | `Win + X, U, R` |
| adb-sdk-path-fix | `Win + Pause/Break` (Sistem Değişkenleri) |
| usb-driver-kontrol | `Win + X, M` (Aygıt Yöneticisi) |
| wifi-network-tools | `Win + I` → Ağ ve İnternet |
| hafiza-temizligi-hard-reset (tarayıcı) | `Ctrl + Shift + Del` |
| tam-sistem-yetkisi (yönetici) | `Ctrl + Shift + Enter` |
| open_vscode_claude_terminal | `` Ctrl + ` `` veya `Ctrl + J` |
| vscode-control | `Ctrl + Shift + P` (komut paleti) |
| open_vscode_focus | `Win + 1, 2, 3...` (görev çubuğu) |
| vscode-ac | `Win + Sayı` (görev çubuğundan) |
| camera-capture | `Win` → "Kamera" yaz → Enter |
| emulator-klavye-navigasyonu | Yön tuşları, Tab, Enter |

## Grup 2 — Özel Script (Kısayol Ataması Gerekir)

Bunların Windows'ta doğrudan karşılığı yok. AutoHotkey ile `Ctrl+Alt+Harf` atanır.

### Kısayol Harf Tablosu

| Kısayol | Script | Ne Yapar |
|---------|--------|----------|
| `Ctrl+Alt+M` | mouse-klavye-ctypes | Fare/klavye simülasyonu |
| `Ctrl+Alt+O` | gorsel-onaylama | Popup onaylama |
| `Ctrl+Alt+V` | screen-vision-analiz | Ekran görüntüsü al + analiz |
| `Ctrl+Alt+K` | kali-linux-remote | Kali VM'e SSH |
| `Ctrl+Alt+H` | kali-help-explorer | Kali araç yardımı |
| `Ctrl+Alt+W` | kali-usb-wifi-scan | Kali USB WiFi tarama |
| `Ctrl+Alt+T` | vm-web-terminal-ui | Web terminal başlat |
| `Ctrl+Alt+Q` | ollama-baslat-ekran-goster | Ollama başlat |
| `Ctrl+Alt+A` | vscode-agent-control | Ajan kontrol |
| `Ctrl+Alt+B` | tor-browser-arama | Tor Browser aç |
| `Ctrl+Alt+I` | windows-python-cli-installer | CLI aracı kur |
| `Ctrl+Alt+R` | hafiza-temizligi-hard-reset | Hafıza temizle |
| `Ctrl+Alt+N` | env-kayit-kurallari | .env kayıt kuralları |
| `Ctrl+Alt+S` | skill-obsidian-first-check | Skill + Obsidian ön kontrol |

## AutoHotkey Script (AHK)

**Script yolu:** `scripts/windows-shortcuts.ahk`
**AutoHotkey v2** ile yazılmıştır. Tüm `Ctrl+Alt+Harf` atamaları burada tanımlı.

### AHK'yi Düzenleme

```bash
notepad "C:\Users\marko\AppData\Local\hermes\skills\windows-automation\windows-automation-shortcuts\scripts\windows-shortcuts.ahk"
```

### AHK'yi Yeniden Başlatma

```bash
# 1. Çalışan AHK'yi bul ve öldür
powershell -NoProfile -Command "Get-Process autohotkey* | Stop-Process -Force"
# 2. Yeniden başlat
start "" "C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe" "C:\Users\marko\AppData\Local\hermes\skills\windows-automation\windows-automation-shortcuts\scripts\windows-shortcuts.ahk"
```

## Başlangıç Entegrasyonu

AHK script'i, Windows başlangıcında otomatik çalışacak şekilde yapılandırılmıştır:

```
Kısayol: %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Hermes-AHK.lnk
Hedef:   AutoHotkey64.exe → windows-shortcuts.ahk
```

Bu kısayol sayesinde bilgisayar açıldığı anda tüm Hermes kısayolları hazırdır.

### Doğrulama

```bash
# Startup klasörü içeriği
dir "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
# AHK'nin çalıştığını görme
powershell -NoProfile -Command "Get-Process autohotkey* | Format-Table Id, ProcessName, StartTime"
```

## Grup 3 — Python Daemon (hermes_listener.py)

AHK'ye **alternatif** veya **paralel** çalışabilir. `keyboard` kütüphanesi ile global hotkey dinler.

Mimari referans: `references/listener-daemon.md` (hotkey map, dispatch pattern, platform caveats)

### Avantajları

- Tamamen Python ekosisteminde kalır
- `hermesmouse.py`'yi direkt import eder (subprocess yok)
- Loglar doğrudan Hermes ana paneline gider
- PID yönetimi ile tek instance garantisi

### Kullanım

```bash
# Başlat (arka plan)
python C:\Users\marko\hermes_listener.py

# Durdur
python C:\Users\marko\hermes_listener.py --stop

# Durum kontrol
python C:\Users\marko\hermes_listener.py --status

# Kısayolları listele
python C:\Users\marko\hermes_listener.py --list
```

### .bat ile kolay yönetim

```bash
hermes_listener.bat start      # başlat (arka plan, pythonw)
hermes_listener.bat stop       # durdur
hermes_listener.bat status     # kontrol et
hermes_listener.bat restart    # yeniden başlat
hermes_listener.bat list       # kısayolları göster
```

### Task Scheduler (otomatik başlangıç)

```bash
# Yönetici olarak çalıştır:
hermes_listener_install.bat
```

Veya manuel:
```bash
schtasks /create /tn "Hermes-Listener" /tr "C:\Users\marko\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe C:\Users\marko\hermes_listener.py" /sc onlogon /delay 0000:30 /rl highest /f
```

### Kısayol Haritası

| Kısayol | İşlev | Tip |
|---------|-------|-----|
| `Ctrl+Alt+M` | Fare konumu göster | Direkt (hermesmouse) |
| `Ctrl+Alt+S` | Ekran görüntüsü al | PowerShell inline |
| `Ctrl+Alt+V` | Ekran analizi (vision) | PowerShell + Ollama |
| `Ctrl+Alt+O` | Ollama başlat | Subprocess |
| `Ctrl+Alt+Q` | Ollama (alternatif) | Subprocess |
| `Ctrl+Alt+K` | Kali SSH | PowerShell SSH |
| `Ctrl+Alt+H` | Kali help explorer | Subprocess |
| `Ctrl+Alt+W` | Kali USB WiFi tarama | Subprocess |
| `Ctrl+Alt+T` | Web terminal başlat | Subprocess |
| `Ctrl+Alt+A` | VS Code ajan kontrol | PowerShell |
| `Ctrl+Alt+B` | Tor Browser aç | Subprocess |
| `Ctrl+Alt+I` | CLI installer | Subprocess |
| `Ctrl+Alt+R` | Hafıza temizliği | Subprocess |
| `Ctrl+Alt+N` | .env kurallarını göster | Direkt (Python) |

### Güvenlik Notu

`keyboard` kütüphanesi Windows'ta global hook için **admin yetkisi** gerektirir.
Terminal `python hermes_listener.py` ile çalışıyorsa admin yetkisi vardır.
Task Scheduler `rl highest` ile admin olarak çalışır.

### Log Dosyası

```bash
# Tüm loglar burada:
type C:\Users\marko\.hermes\logs\listener.log
```

### Dosyalar

| Dosya | Açıklama |
|-------|----------|
| `C:\Users\marko\hermes_listener.py` | Ana Python daemon (14 hotkey) |
| `C:\Users\marko\hermes_listener.bat` | Kolay yönetim .bat |
| `C:\Users\marko\hermes_listener.vbs` | Görünmez başlatma (Task Scheduler) |
| `C:\Users\marko\hermes_listener_install.bat` | Task Scheduler kayıt aracı |

## Skill Dosyaları

| Dosya | Açıklama |
|-------|----------|
| Bu skill | Kısayol atama rehberi + tablolar |
| `scripts/windows-shortcuts.ahk` | AutoHotkey script (tüm atamalar hazır) |
| `references/listener-daemon.md` | Python daemon mimari referansı (hotkey map, dispatch pattern, platform caveats) |
