---
name: android-adb-python-workflow
title: Android ADB & APK Workflow
description: "ADB SDK yol boşluğu hatası çözümleri ve Android APK kontrol/yükleme workflow'u."
tags: [android, adb, apk, sdk, windows, workflow]
category: devops
audience: user
version: 1.0.0
triggers: [adb, apk, android-sdk, platform-tools]
related_skills: [android-api-apk-manager]
---


> **Kategori:** devops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | ADB SDK yol boşluğu hatası çözümleri ve Android APK kontrol/yükleme workflow'u. |
| **Nerede?** | devops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Android ADB & APK Workflow

## ADB SDK Path Boşluk Hatası Çözümleri

Windows'ta Android SDK `platform-tools` yolunda boşluk nedeniyle ADB komutları çalışmayabilir.

### 4 Çözüm:

1. **Tırnak içine al:**
   ```bash
   "C:\Program Files (x86)\Android\android-sdk\platform-tools\adb.exe" devices
   ```

2. **8.3 kısa yol kullan:**
   ```bash
   C:\PROGRA~2\Android\android-sdk\platform-tools\adb.exe devices
   ```
   Öğren: `dir /x "C:\Program Files (x86)\Android"`

3. **PATH değişkenine tırnak ekle:**
   ```
   "C:\Program Files (x86)\Android\android-sdk\platform-tools"
   ```

4. **PowerShell'de ampersand:**
   ```powershell
   & 'C:\Program Files (x86)\Android\android-sdk\platform-tools\adb.exe' devices
   ```

## Android APK Kontrol ve Yükleme

### Kontrol Listesi
- [ ] ADB/Platform-Tools kurulu mu?
- [ ] Cihaz USB hata ayıklama (ADB) açık mı?
- [ ] APK dosyaları var mı? (`Downloads`, `Projects/android`)
- [ ] Yüklü paketler listelendi mi?
- [ ] Kurulum test edildi mi?

### Hızlı Komutlar
```powershell
# Yüklü paketler
adb shell pm list packages | findstr /i "kelime"

# APK yolu kontrol
Get-ChildItem -Recurse -Filter *.apk C:\Users\marko\Downloads

# Tek APK kur
adb install "C:\yol\uygulama.apk"
```

### Yollar
- Android SDK Platform-Tools: `C:\Users\marko\AppData\Local\Android\Sdk\platform-tools`
- Hermes skill: `C:\Users\marko\AppData\Local\hermes\skills\devops\android-api-apk-manager`
