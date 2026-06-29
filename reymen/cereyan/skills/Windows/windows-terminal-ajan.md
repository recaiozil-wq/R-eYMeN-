---
name: windows-terminal-ajan
title: Windows Terminal Ajanı
description: Windows terminal komutları, CMD vs PowerShell farkı, Kali karşılaştırması.
category: windows
Kim: Windows ajani
Ne: Windows terminal komutları, CMD vs PowerShell farkı, Kali karşılaştırması.
Nerede: `windows\windows-terminal-ajan.md`
Ne Zaman: Windows sistem yonetimi gerektiginde
Neden: Windows Terminal Ajan islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Windows Terminal Ajanı


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | Windows ajani |
| **Ne** | Windows terminal komutları, CMD vs PowerShell farkı, Kali karşılaştırması. |
| **Nerede** | `windows\windows-terminal-ajan.md` |
| **Ne Zaman** | Windows sistem yonetimi gerektiginde |
| **Neden** | Windows Terminal Ajan islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı. Kali ajanıyla cross-platform koordinasyon yapar. |
| **Ne?** | Windows CMD ve PowerShell komutlarını öğrenir, test eder, Kali Linux ile karşılaştırır. Ağ, sistem, dosya ve servis yönetimi. |
| **Nerede?** | Windows 10/11 — git-bash (MSYS2) üzerinden Windows native komutları. Ağ adaptörleri: Intel Wi-Fi 6E AX211, Realtek PCIe GbE, VirtualBox Host-Only, WSL Hyper-V. |
| **Ne Zaman?** | Kullanıcı Windows ağ/sistem/dosya işlemi istediğinde. Kali ajanı port tespit edip Windows'tan engelleme istediğinde. |
| **Neden?** | Windows terminal komutları Linux/Kali'den farklıdır. `ipconfig` vs `ifconfig`, `netstat` vs `nmap`. Bu skill farkı öğretir ve her iki platformda da çalışmayı sağlar. |
| **Nasıl?** | `ipconfig /all` ile ağ yapılandırması, `netstat -ano` ile port tespiti, `netsh advfirewall` ile güvenlik duvarı. Kali'den gelen PORT_BLOCK mesajını işler. |

---

## İçindekiler

1. CMD vs PowerShell
2. Ağ Komutları (ipconfig, netstat)
3. Sistem Komutları (systeminfo, tasklist)
4. Dosya Komutları (dir, copy, move, del)
5. Servis Komutları (sc, net start/stop)
6. Kali Karşılaştırması
7. Kali — Windows Koordinasyonu

---

## 1. CMD vs PowerShell

| Özellik | CMD | PowerShell |
|---------|-----|-----------|
| Çıkış | Text tabanlı | .NET nesnesi |
| Script uzantısı | .bat / .cmd | .ps1 |
| Pipeline | Text akışı | Nesne akışı |
| Çıkış yılı | ~1980'ler | 2006 |
| Uzaktan yönetim | Yok | WinRM |
| Liste komutu | `dir` | `Get-ChildItem` (alias: `ls`, `dir`) |
| Process list | `tasklist` | `Get-Process` (alias: `ps`) |
| Servis yönetimi | `sc`, `net start/stop` | `Get-Service`, `Start-Service`, `Stop-Service` |

**Hangi shell'de olduğunu anlama:**
- CMD: `echo %COMSPEC%`
- PowerShell: `$PSVersionTable`

---

## 2. Ağ Komutları

### ipconfig
- `ipconfig` — Temel IP yapılandırması
- `ipconfig /all` — Tüm detaylar (MAC, DNS, DHCP)
- `ipconfig /release` — DHCP IP bırakma
- `ipconfig /renew` — DHCP IP yenileme
- `ipconfig /flushdns` — DNS önbelleği temizleme

### netstat
- `netstat -an` — Tüm aktif bağlantılar ve portlar (sayısal)
- `netstat -b` — Hangi process hangi portu kullanıyor (admin)
- `netstat -r` — Routing tablosu
- `netstat -ano` — PID'lerle birlikte bağlantılar

---

## 3. Sistem Komutları

### systeminfo
Detaylı sistem bilgisi: OS, donanım, RAM, BIOS, ağ yapılandırması.

### tasklist
- `tasklist` — Process listesi (PID, Session, Memory)
- `tasklist /v` — Detaylı görünüm
- `tasklist /svc` — Her process'in servisleri

---

## 4. Dosya Komutları

| Komut | Açıklama | Örnek |
|-------|----------|-------|
| `dir` | Dizin listele | `dir /w`, `dir /s`, `dir /a`, `dir /b` |
| `copy` | Dosya kopyala | `copy /y kaynak hedef`, `copy /v` |
| `move` | Taşı / yeniden adlandır | `move eski_adi yeni_adi` |
| `del` | Dosya sil | `del /f /s /q dosya` |

---

## 5. Servis Komutları

### sc (Service Control)
- `sc query` — Servis durumu sorgula
- `sc queryex` — Detaylı servis sorgusu
- `sc config` — Servis yapılandırması (start type, account)
- `sc start/stop ServisAdi` — Servis başlat/durdur
- `sc delete ServisAdi` — Servis sil
- `sc create ServisAdi ...` — Yeni servis oluştur

### net start/stop
- `net start "ServisAdi"` — Servis başlat
- `net stop "ServisAdi"` — Servis durdur
- sc'den daha basit, daha az seçenek

---

## 6. Kali Karşılaştırması: netstat vs nmap

| Özellik | `netstat -an` (Windows) | `nmap` (Kali) |
|---------|------------------------|---------------|
| **Hedef** | Yerel makine | Uzak hedef |
| **Gösterir** | Açık portlar, bağlantı durumu | Hedefteki açık portlar |
| **Protokol** | TCP/UDP | TCP, UDP, SCTP |
| **STATE** | LISTENING, ESTABLISHED, TIME_WAIT | open, closed, filtered |
| **PID bilgisi** | `netstat -ano` ile | Process bilgisi yok |
| **Servis tespiti** | Yok | `-sV` ile versiyon tespiti |
| **OS tespiti** | Yok | `-O` ile işletim sistemi tespiti |
| **Script engine** | Yok | `--script` ile NSE script |
| **Hız** | Anında | Tarama tipine göre sn/dk |

### Özet
- **netstat**: localhost'ta hangi portların açık olduğunu ve hangi process'lerin bağlı olduğunu gösterir. Anında sonuç verir.
- **nmap**: Uzak bir hedefi tarar, açık portları, servisleri ve versiyonları tespit eder.
- **Tam resim**: Windows'ta `netstat -an` + Kali'de `nmap -sn 192.168.1.0/24` + `nmap -sV hedef_ip` = ağın tam görüntüsü.

---

## 7. Kali — Windows Koordinasyonu (Cross-Platform)

İki ajan birlikte çalıştığında:

### Senaryo: Şüpheli Port Engelleme

```
Kali Ajanı:
  nmap ile localhost tara
  → Port 1234 LISTENING (debug)
  → Windows ajanına PORT_BLOCK mesajı gönder

Windows Ajanı:
  Kali'den PORT_BLOCK al
  netstat ile doğrula
  netsh advfirewall firewall add rule name="BLOCK_1234" dir=in action=block protocol=TCP localport=1234
  Kali'ye PORT_BLOCKED cevabı gönder
```

### Mesaj Formatı (JSON)

| Alan | Değer | Açıklama |
|:-----|:------|:---------|
| `kaynak` | `kali` / `windows` | Gönderen ajan |
| `hedef` | `kali` / `windows` | Alıcı ajan |
| `komut` | `PORT_BLOCK` / `PORT_BLOCKED` / `SCAN_RESULT` / `ERROR` | İşlem türü |
| `port` | `1234` | Hedef port |
| `durum` | `LISTENING` / `BLOCKED` / `FAILED` | Port durumu |
| `sebep` | `"Debug portu herkese açık"` | Neden |
| `acil` | `true` / `false` | Acil durum flag |
| `hata` | `null` / `"Hata mesajı"` | Hata varsa |

### Orkestratör

- **conversation_loop** (ana thread) — İki ajan arasında köprü
- Ajanlar **OnceHafiza** üzerinden ortak hafıza kullanır
- Biri hata yaparsa: diğeri devralır (max 3 retry), ikisi de çalışamazsa circuit breaker
