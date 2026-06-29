---
name: windows-terminal-ajani
description: Windows Terminal Uzman Ajanı — CMD/PowerShell, ağ, sistem, servis yönetimi, Kali cross-platform
category: windows
version: 1.0.0
triggers:
  - windows
  - cmd
  - powershell
  - ipconfig
  - netstat
  - tasklist
  - terminal
---


> **Kategori:** windows-terminal-ajani

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Windows Terminal Uzman Ajanı — CMD/PowerShell, ağ, sistem, servis yönetimi, Kali cross-platform |
| **Nerede?** | windows-terminal-ajani/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Windows Terminal Ajanı

## CMD vs PowerShell

| Özellik | CMD | PowerShell |
|:---------|:----|:-----------|
| **Temel** | `dir`, `copy`, `del` | `Get-ChildItem`, `Copy-Item`, `Remove-Item` |
| **Pipe** | Metin bazlı (`find`, `more`) | Nesne bazlı (`Where-Object`, `Select-Object`) |
| **Script** | `.bat` / `.cmd` | `.ps1` (tam programlama) |
| **Hız** | Basit işlerde hızlı | Karmaşık otomasyon için |
| **Uyum** | Eski Windows | Windows + Linux (PowerShell Core) |

## Komut Kategorileri

### Ağ Bilgisi
```
ipconfig                    :: IP yapılandırması
ipconfig /all              :: Detaylı (MAC, DNS, DHCP)
netstat -an                :: Tüm bağlantılar + portlar
ping <hedef>               :: ICMP testi
tracert <hedef>             :: Yol izleme
nslookup <host>            :: DNS sorgulama
```

### Sistem Bilgisi
```
systeminfo                  :: OS, RAM, CPU detayı
tasklist                    :: Çalışan prosesler
taskkill /PID <id> /F      :: Proses öldür
```

### Dosya İşlem
```
dir [/s] [/w]              :: Klasör listele
copy <kay> <hedef>          :: Kopyala
move <kay> <hedef>          :: Taşı
del /s /f /q <dosya>        :: Sil (zorla)
mkdir <klasor>              :: Klasör oluştur
rmdir /s <klasor>           :: Klasör sil
```

### Servis Yönetimi
```
sc query                    :: Servisleri listele
sc start/stop <servis>      :: Servis başlat/durdur
net start/stop <servis>     :: Alternatif
```

## Kali vs Windows — Cross-Platform

| Amaç | Kali | Windows |
|:-----|:-----|:--------|
| Port tara | `nmap -sV` | `netstat -an` (yerel) |
| IP bilgisi | `ip addr` | `ipconfig /all` |
| DNS sorgula | `dig` | `nslookup` |
| Süreç listele | `ps aux` | `tasklist` |
| Servis yönet | `systemctl` | `sc` / `net` |
| Ping | `ping -c 4` | `ping -n 4` |
| Yol izle | `traceroute` | `tracert` |

**Fark:** nmap harici port tarar, netstat yerel portları gösterir.

### İki Ajan Koordinasyonu

Kali + Windows koordineli çalışması için:
1. Kali nmap ile port tara → şüpheli port bul
2. Kali → BLOCK_PORT mesajı → Windows
3. Windows netstat ile doğrula → firewall kuralı ekle
4. Windows → PORT_BLOCKED mesajı → Kali
5. Kali nmap ile filtered doğrula

**Skill:** `cross-platform-coordination` (detaylı protokol, hata yönetimi, simülasyon script'i)
**Hafıza:** `cross-platform/security` kategorisi ortak

### Windows Firewall Kuralı

```batch
:: Port engelleme
netsh advfirewall firewall add rule name="BLOCK_PORT_4444" dir=in action=block protocol=tcp localport=4444

:: Doğrulama
netsh advfirewall firewall show rule name="BLOCK_PORT_4444" verbose
```

### Ajanlar Arası Koordinasyon (Kali + Windows)

Port engelleme için kanıtlanmış 3-adım koordinasyon:

| Adım | Ajan | Eylem | Hafıza Kategorisi |
|:----:|:----:|:------|:-----------------:|
| 1 | Kali | `nmap -sV` ile açık port tara, şüpheli portu tespit et | `kali/network/nmap` |
| 2 | Windows | `netstat` ile doğrula → firewall kuralı ekle | `windows/terminal/network` |
| 3 | Kali | `nmap` ile doğrula (`filtered` görmeli) | `cross-platform/security` |

**Mesaj formatı (JSON-RPC benzeri):**
```
Kali → Windows:  {cmd: "BLOCK_PORT", port: 4444, protocol: "tcp", kaynak: "kali"}
Windows → Kali:  {cmd: "PORT_BLOCKED", port: 4444, durum: "engellendi", kaynak: "windows"}
```

**Orkestratör:** Kali (tespit eden). **Çalışan:** Windows (engelleyen). **Doğrulayıcı:** Kali (onay alan).

Her iki ajan aynı `hafiza.db`'yi kullanır — ayrı kategorilerde. Guven_skoru >= 0.8 ise LLM çağrılmaz, hafızadan direkt döner.

Detaylı koordinasyon desenleri için `cross-platform-coordination` skill'ine bak.

## Çalışma Akışı

Kanıtlanmış 6-adım akışı (bu skill bu akışla oluşturuldu):

| # | Adım | Açıklama |
|:-:|:-----|:---------|
| 1 | **Öğren** | CMD/PowerShell farkını öğren, komut kategorilerini belirle |
| 2 | **Test (Ağ)** | `ipconfig /all` + `netstat -an` çalıştır, çıktıyı analiz et |
| 3 | **Test (Sistem)** | `systeminfo` + `tasklist` çalıştır, sonuçları analiz et |
| 4 | **Hafızaya Kaydet** | `windows/terminal/network`, `windows/terminal/system` kategorilerinde hafıza DB'sine yaz |
| 5 | **Cross-Platform** | Kali (nmap, ip addr) ile Windows (netstat, ipconfig) karşılaştır |
| 6 | **Skill Oluştur** | SKILL.md + references/ ile kalıcı hale getir |

Her adımda RAW çıktıyı göster, onay al. Sırayla ilerle, her biteni test et.

## Hafıza Entegrasyonu

Bu skill'in komutları hafızaya şu kategorilerde kaydedilir:

- `windows/terminal/network` — ipconfig, netstat, ping, tracert, nslookup
- `windows/terminal/system` — systeminfo, tasklist, taskkill
- `cross-platform/network` — Kali vs Windows karşılaştırmaları

Hafıza kaydı formatı:
```json
{
  "koleksiyon": "beceriler",
  "anahtar": "windows ipconfig netstat egzersizi",
  "kategori": "windows/terminal/network",
  "guven_skoru": 0.8,
  "gecerlilik_tarihi": "<bugun+6ay>"
}
```

Guven_skoru >= 0.8 → LLM atlanır, hafızadan direkt döner.

## Referanslar

Bu skill'in `references/` dizininde canlı test çıktıları bulunur:
- `references/live-test-output.md` — ipconfig /all ve netstat -an çıktıları

## Pitfalls

- `ipconfig` IPv6 adreslerini de gösterir — bunlar genelde link-local, dikkat
- `netstat -an` sadece o anki bağlantıları gösterir, geçmişi göstermez
- Windows'ta `systeminfo` çıktısı çok uzundur — özetlemek gerekebilir
- PowerShell komutları CMD'de çalışmaz (ve tersi) — hangi shell'de olduğunu kontrol et
