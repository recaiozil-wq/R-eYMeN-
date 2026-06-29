
> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Windows Automation_Usb Driver Kontrol |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: usb-driver-kontrol
description: Herhangi bir cihaz bağlantısı (ADB, USB) öncesinde sürücülerin yüklü olup olmadığını kontrol eder. Eksikse kurulum yapar.
title: "Usb Driver Kontrol"

audience: user
tags: [automation, windows]
category: windows-automation---

# USB Sürücü Kontrol Kuralı

## Amaç
Bir telefona/cihaza bağlanmaya çalışmadan ÖNCE:
1. Gerekli sürücülerin yüklü olup olmadığını kontrol et
2. Eksikse kur
3. Sonra bağlantı dene

Bu kural ASLA ATLANAMAZ. Önce sürücü kontrolü yapılmadan ADB/bağlantı denenmez.

## Adım Adım

### 1. Sürücü Durumunu Kontrol Et
```powershell
# Samsung USB Driver yüklü mü kontrol et
Get-CimInstance -ClassName Win32_PnPSignedDriver | Where-Object { $_.DeviceName -like "*Samsung*" -or $_.DeviceName -like "*Android*" } | Select-Object DeviceName, DriverVersion, IsSigned
```

Veya:
```bash
# Windows'ta driver klasörünü kontrol et
ls /c/Windows/INF/setupapi*.log 2>/dev/null | head -1
# Samsung driver klasörü
ls "/c/Program Files (x86)/Samsung/" 2>/dev/null
ls "/c/Program Files/Samsung/" 2>/dev/null
```

### 2. ADB'nin Cihazı Görüp Görmediğini Kontrol Et
```bash
/c/Users/marko/AppData/Local/Android/Sdk/platform-tools/adb.exe devices
```
Çıktı `List of devices attached` (boş) ise cihaz görünmüyor demektir.

### 3. Sürücü Eksikse İndir ve Kur
Samsung USB Driver for Windows:
- **Resmi URL:** https://developer.samsung.com/android-usb-driver
- **Sürüm:** v1.9.5.0 (35.5 MB, Mayıs 2026)
- İndir → `C:\Users\marko\Downloads\`
- Kurulum: exe dosyasını çalıştır, ileri-ileri-bitir

### 4. Kurulum Sonrası
```bash
# ADB'yi yeniden başlat
/c/Users/marko/AppData/Local/Android/Sdk/platform-tools/adb.exe kill-server
/c/Users/marko/AppData/Local/Android/Sdk/platform-tools/adb.exe devices
```

### 5. Telefonda Yapılması Gerekenler
- **Ayarlar → Telefon hakkında → Yazılım bilgisi → Yapı numarası**'na 7 kere tıkla (Geliştirici seçenekleri açılır)
- **Ayarlar → Geliştirici seçenekleri → USB Debugging** AÇ
- USB kablosunu çıkar tak
- Telefonda "Bilgisayara güveniyor musun?" → İzin ver

## Desteklenen Cihazlar ve Sürücüler

| Cihaz | Sürücü | Kaynak |
|-------|--------|--------|
| Samsung Galaxy | Samsung Android USB Driver | developer.samsung.com |
| Google Pixel | Google USB Driver | developer.android.com |
| Xiaomi | Xiaomi USB Driver | xiaomi.com |
| OnePlus | OnePlus USB Driver | oneplus.com |
| Genel Android | Google USB Driver (ADB) | SDK Manager ile |

## Sık Sorunlar
- **"USB cihazı tanınmadı"** → sürücü eksik, yukarıdaki adımları uygula
- **ADB'de cihaz görünüyor ama "offline"** → telefonda "Bilgisayara güveniyor musun?" onayı verilmemiş
- **Samsung için MTP driver da gerekebilir** → Samsung Smart Switch ile otomatik kurulur

## Uyarı
Bu kontrol olmadan asla ADB bağlantısı deneme. ÖNCE sürücü kontrol et, SONRA bağlan.
