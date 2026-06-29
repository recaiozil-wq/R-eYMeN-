
> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Windows Automation_Adb Sdk Path Fix |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: adb-sdk-path-fix
description: Windows'ta Android SDK Platform-Tools yolundaki boşluk nedeniyle ADB komutlarının çalışmaması durumunda PATH düzeltme ve tırnak kullanma rehberi.
title: "Adb Sdk Path Fix"

audience: user
tags: [automation, windows]
category: windows-automation---

# ADB/SDK Kurulum + PATH Boşluk Hatası Çözümü

## Hızlı Kurulum (tercih sırası)

### 1. PlatformTools
```bash
winget install -e --id Google.PlatformTools --accept-source-agreements --accept-package-agreements
```
Eğer `Google.PlatformTools` bulunamazsa:
```bash
winget search PlatformTools
```
Sol sütunda `Id` görünüyorsa o ID ile kur. Kullanıcı profiline göre bu paket bazen ilk denemede görünmeyebilir.

### 2. Alternatif kurulum (yukarıdaki başarısız olursa)
Android Studio kurulumu genellikle `platform-tools` ile gelir. `winget search Android` ile uygun paket bulunabilir ancak state durumu bağımlıdır.

## Windows'ta PATH Boşluk Hatası Çözümü

### 1. Tırnak içine al
Komut çalıştırırken yolu tırnak içine al:
```bash
"C:\Program Files (x86)\Android\android-sdk\platform-tools\adb.exe" devices
```

### 2. 8.3 kısa yol kullan
Windows 8.3 kısa yolu ile çalıştır:
```bash
C:\PROGRA~2\Android\android-sdk\platform-tools\adb.exe devices
```
Kısa yolu öğren:
```bash
dir /x "C:\Program Files (x86)\Android"
```

### 3. PATH ayarlamasına tırnak ekle
`System Properties` > `Advanced` > `Environment Variables`
Path değişkenindeki boşluklu girişleri tırnak içine al:
```
"C:\Program Files (x86)\Android\android-sdk\platform-tools"
```

### 4. Güvenli komut örnekleri
PowerShell:
```powershell
& 'C:\Program Files (x86)\Android\android-sdk\platform-tools\adb.exe' devices
```
CMD:
```cmd
"C:\Program Files (x86)\Android\android-sdk\platform-tools\adb.exe" devices
```

## Kontrol
ADB çalışıyor mu:
```bash
adb version
```
Cihaz listesi:
```bash
adb devices
```

Bu adımlarla PATH’teki boşluk sorunu çözülebilir.