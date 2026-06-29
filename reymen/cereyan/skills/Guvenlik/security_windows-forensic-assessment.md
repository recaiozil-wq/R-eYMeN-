---
name: windows-forensic-assessment
title: "Windows Forensic Assessment"
tags: [security, windows]
description: Systematic audit of forensic traces on Windows — Event Log, USBSTOR, SRUM, WiFi profiles, OneDrive, VirtualBox VM logs, PowerShell history, and disk encryption status. One-time evidence check before deciding on countermeasures.
version: 1.0.0
author: hermes
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [forensic, evidence, traces, windows, security, audit, event-log, usbstor, srum, virtualbox, onedrive, powershell]
audience: user
related_skills: [veracrypt-windows, guvenlik-izleme-sistemi, port-firewall-taramasi, tor-browser-arama]
---


> **Kategori:** security

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Systematic audit of forensic traces on Windows — Event Log, USBSTOR, SRUM, WiFi profiles, OneDrive, VirtualBox VM logs, PowerShell history, and disk encryption status. One-time evidence check before deciding on countermeasures. |
| **Nerede?** | security/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Windows Forensic Assessment

## Overview

Systematic check of what forensic evidence exists on a Windows machine. Use this when the user asks "siber polis gelse ne bulur", "forensic analiz", "adli bilişim incelemesi", "hangi izler kalır", "bilgisayarda hangi kayıtlar var", or similar questions about forensic readiness.

**TETİKLEYİCİLER:** "siber polis", "forensic", "adli", "izler", "kayıtlar", "bulunur", "ne açık bulabilir", "hangi loglar", "ne kalır"

## Adım Adım Kontrol Listesi

### 1. Event Log (Windows Olay Günlükleri) 🟠
```powershell
# Tüm log kanallarını listele
wevtutil el

# En kritik 4 kanal
wevtutil gl "Security"          # Oturum açma/kapama, ayrıcalık kullanımı
wevtutil gl "System"            # Servis başlatma/durdurma, sürücü yükleme
wevtutil gl "Windows PowerShell"         # PowerShell komutları (ScriptBlock log varsa içerik de kaydedilir)
wevtutil gl "Microsoft-Windows-PowerShell/Operational"  # PowerShell işlem detayı
wevtutil gl "Microsoft-Windows-Sysmon/Operational"      # Varsa — her process çalıştırması kaydedilir

# Log dosyası boyutu
Get-ChildItem "C:\Windows\System32\winevt\Logs\*.evtx" | Select-Object Name,Length | Sort-Object Length -Descending
```

**Silinebilir mi?**
- `wevtutil cl "Windows PowerShell"` ile temizlenir
- Ancak temizlik log'da zaman boşluğu bırakır
- PowerShell ScriptBlock logging varsa script kodları da kayıtlıdır

**Ne görünür?**
- Process creation events (Event ID 4688): python.exe, VeraCrypt.exe, powershell.exe çalıştırmaları
- Python komut içeriği değil, sadece "python.exe script.py" şeklinde komut satırı
- Tarih/saat damgaları

### 2. USB Takılış Geçmişi (USBSTOR) 🔴
```powershell
# USBSTOR registry
Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Enum\USBSTOR\*"
# MountedDevices (hangi harf hangi USB'ye ait)
Get-ItemProperty "HKLM:\SYSTEM\MountedDevices"
```

**Ne görünür?**
- Takılan her USB'nin marka, model, seri numarası
- İlk takılış tarihi, son takılış tarihi
- Windows başlatıldığında USB takılıysa tekrar kaydedilir

**Silinebilir mi?**
- Registry'den silinebilir ama Windows yeniden başlatınca USB hâlâ takılıysa tekrar oluşur
- Boş USBSTOR (hiç USB takılmamış) daha şüphelidir

### 3. Ağ Bağlantı Geçmişi (SRUM + WiFi + netstat) 🟠
```powershell
# WiFi profilleri
netsh wlan show profiles

# SRUM veritabanı
# C:\Windows\System32\sru\SRUDB.dat (kullanımda, admin gerektirir)
# Hangi uygulama ne kadar veri göndermiş/almiş, hangi ağlara bağlanılmış

# Aktif bağlantılar
netstat -n | Select-Object -Last 30

# NLA registry (önceden bağlanılan ağlar)
Get-Item "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\NetworkList\Profiles\*"
```

**Ne görünür?**
- Kaydedilmiş tüm WiFi ağları (SSID)
- SRUM: her uygulamanın ağ kullanımı (ne kadar veri alıp gönderdiği)
- Aktif TCP bağlantıları (hangi IP'lere bağlı)
- Bağlanılan her ağın profili (ilk ve son bağlantı tarihi)

**Çözüm:**
- Tek tek temizlemek yerine tam disk şifreleme (BitLocker) ile tüm kayıtlar anlamsızlaşır

### 4. OneDrive / Bulut Senkronizasyonu 🟠
```powershell
# OneDrive çalışıyor mu?
Get-Process OneDrive

# Senkronize edilen dosyalar
Get-ChildItem "$env:USERPROFILE\OneDrive" -Recurse -ErrorAction SilentlyContinue
```

**Ne görünür?**
- OneDrive'da senkronize edilen tüm dosyalar — düz metin ise okunabilir
- vault.hc senkronize edilse bile içeriği şifreli olduğu için okunamaz
- Ama Obsidian vault düz metinse bulutta okunabilir

**Risk:**
- Obsidian vault OneDrive'da ise tüm güvenlik notları, CVE'ler, Kali analizleri **bulutta düz metin**
- v2.hc container şifreli olsa bile, buluta yüklenir ve Microsoft erişebilir
- Çözüm: vault'u OneDrive dışına taşı veya container'a koy (vault.hc -> senkronize olan sadece şifreli dosya)

### 5. VirtualBox VM Kayıtları 🟠
```powershell
# VBox log'ları
Get-ChildItem "$env:USERPROFILE\.VirtualBox\*.log"
Get-ChildItem "$env:USERPROFILE\VirtualBox VMs\*\Logs\*.log"

# VM yapılandırma
Get-ChildItem "$env:USERPROFILE\VirtualBox VMs\*\*.vbox"
```

**Ne görünür?**
- VBox.log: işletim sistemi, açılış/kapanış zamanı, ağ trafiği istatistikleri, hata mesajları
- VBoxHardening.log: güvenlik kontrolleri, sürücü yüklemeleri
- selectorwindow.log: VirtualBox yöneticisi etkileşimleri
- VBoxSVC.log: VirtualBox servisi başlatma/durdurma
- Host-Only ağ IP/Mask bilgisi
- ISO dosya yolu (indirilen Kali ISO'nun yeri)
- Paylaşımlı klasör yapılandırması
- VM adı, RAM/CPU ayarları

**Silinebilir mi?**
- Log dosyaları manuel silinebilir (.log, selectorwindow.log, VBoxSVC.log)
- Ancak boş bir VirtualBox dizini daha şüpheli
- En iyi çözüm: disk şifreleme

### 6. PowerShell Geçmişi ve Script Bloğu ⚠️
```powershell
# PowerShell komut geçmişi
Get-Content "$env:USERPROFILE\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt"
```

**Ne görünür?**
- PowerShell'de yazılan her komut satırı
- Hermes'in çağırdığı Python script'lerinin tam yolu
- VeraCrypt şifresi (CLI'da geçildiyse düz metin)

**Silinebilir mi?** ✅
- `Clear-Host` ve dosyayı sil ile temizlenir
- Ancak Windows PowerShell event log'unda process creation kaydı kalır

### 7. Disk Şifreleme Durumu 🔴
```powershell
# BitLocker durumu
Get-BitLockerVolume -MountPoint "C:" -ErrorAction SilentlyContinue
# veya
manage-bde -status C:
```

**Sonuç:**
- BitLocker kapalı = tüm yukarıdaki veriler OKUNABİLİR
- BitLocker açık = disk şifreli, bu veriler anlamsız
- **Tam disk şifreleme (BitLocker) en etkili tek önlemdir**
- Kısmi önlemler (vault.hc, log temizlik) tek başına yetersiz kalır

## Forensic Readiness Matrisi

| Kayıt | Silinebilir? | BitLocker'sız | BitLocker'lı |
|-------|-------------|---------------|--------------|
| Event Log | ⚠️ Boşluk bırakır | Açık | Şifreli |
| USBSTOR | ⚠️ Tekrar oluşur | Açık | Şifreli |
| SRUM | Hayır | Açık | Şifreli |
| WiFi profilleri | Evet | Açık | Şifreli |
| OneDrive içeriği | Hayır | Düz metin | Düz metin* |
| VirtualBox log | Evet | Açık | Şifreli |
| PowerShell geçmiş | Evet | Açık | Şifreli |
| vault.hc içeriği | — | Şifreli | Şifreli |
| Obsidian notlar | — | ⚠️ vault.hc'deyse korunur | Korunur |

*OneDrive içeriği Microsoft sunucusunda olduğu için BitLocker korumaz

## Ana Öneriler

1. **Önce BitLocker** — en büyük korumayı tek adımda sağlar
2. **Sonra vault.hc** — Obsidian notlarını OneDrive'dan ayırır ve ek şifreleme katar
3. **Log temizleme** — sadece acil durumlar için, rutin değil
4. **PowerShell history temizleme** — VeraCrypt şifresi CLI'da geçildiyse zorunlu

## References

- `references/windows-forensic-trace-locations.md` — tüm trace noktalarının tam yolları
