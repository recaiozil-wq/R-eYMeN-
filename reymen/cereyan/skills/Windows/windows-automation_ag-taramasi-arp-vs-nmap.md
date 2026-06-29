
> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Windows Automation_Ag Taramasi Arp Vs Nmap |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: ag-taramasi-arp-vs-nmap
description: Karsilastirmali ag tarama egitimi — arp-scan vs nmap -sn. Hangisi daha hizli, hangisi daha fazla cihaz bulur, nasil birlikte kullanilir.
title: "Ag Taramasi Arp Vs Nmap"

audience: user
tags: [automation, windows]
category: windows-automation---

# Ag Tarama Karsilastirmasi: arp-scan vs nmap -sn

Kali Linux uzerinde ag tarama yontemlerinin karsilastirmasi.

Referans: `references/kablosuz-ve-kablolu-ag-karsilastirmasi.md` (WiFi scan verisi)

## Komutlar

### 1. arp-scan (L2 — ARP Protokolu)
```bash
sudo arp-scan --interface eth1 --localnet
```
- **Sure**: ~1.8 saniye
- **Cihaz sayisi**: 7 (or: .1 .10 .14 .16 .17 .20 .23)
- **Protokol**: ARP (Ethernet seviyesi — L2)
- **Vendor bilgisi**: Yok (Unknown gorunur, `/usr/share/arp-scan/` altinda MAC vendor dosyasi yoksa)
- **Kendini listeler**: Hayir

**Avantaj**: Cok hizli, tum cihazlar ARP'ye cevap vermek zorunda oldugu icin daha fazla cihaz bulur

### 2. nmap -sn (L3 — ICMP + TCP Ping)
```bash
sudo nmap -sn 192.168.0.0/24
```
- **Sure**: ~3.5 saniye
- **Cihaz sayisi**: 6 (or: .1 .14 .16 .17 .19 .20)
- **Protokol**: ICMP ping + TCP ping (L3)
- **Vendor bilgisi**: Var (Castlenet, Intel, Hikvision gibi)
- **Kendini listeler**: Evet (.19 Kali)

**Avantaj**: Vendor bilgisi verir, hangi cihaz hangi marka gorulebilir

## Karsilastirma Tablosu

| Ozelik | arp-scan | nmap -sn |
|--------|----------|----------|
| Sure | **~1.8 sn** ⚡ | ~3.5 sn |
| Cihaz sayisi | **7** (daha fazla) | 6 |
| Vendor bilgisi | Yok | **Var** |
| Protokol | ARP (L2) | ICMP+TCP (L3) |
| Kendini listeler | Hayir | Evet |
| Calisma prensibi | Her cihaz ARP'ye cevap vermek zorunda | Ping bloklanabilir |

## Neden arp-scan daha fazla cihaz bulur?

Cunku ARP (Address Resolution Protocol) ethernet seviyesinde calisir. Agdaki tum cihazlar ARP isteklerine cevap vermek zorundadir — bu protokolun temelidir, engellenemez.

Nmap ise ICMP ping kullanir. Bazi cihazlar:
- ICMP ping'i bloke edebilir (guvenlik duvari)
- TCP ping'e cevap vermeyebilir

Bu yuzden `.10` ve `.23` gibi cihazlar nmap'te gorulmezken arp-scan'da gorulur.

## En Iyi Kullanim

**Cift asamali tarama:**
1. **Hizli on tarama**: `sudo arp-scan --interface eth1 --localnet` (1.8 sn, tum cihazlari bul)
2. **Detayli dogrulama**: `sudo nmap -sn 192.168.0.0/24` (3.5 sn, vendor bilgisiyle)

Ikisi birlikte kullanildiginda eksiksiz sonuc alinir.

## Ornek Cikti

```
# arp-scan
192.168.0.1    98:f2:17:02:03:4f    (Unknown)
192.168.0.20   88:f4:da:d3:24:3a    (Unknown)
192.168.0.17   e0:ba:ad:17:b1:84    (Unknown)
...

# nmap -sn
192.168.0.1    (Castlenet Technology)
192.168.0.20   (Intel Corporate)
192.168.0.17   (Hangzhou Hikvision Digital Technology)
...
```

## Referans Dosyalari

| Dosya | Icerik |
|-------|--------|
| `references/kamera-tespit-rtsp-onvif.md` | Agdaki guvenlik kameralarini tespit etme, RTSP/ONVIF kesfi, sifre brute force ve sorun giderme |

## Problem Giderme

- **arp-scan: "Cannot open MAC/Vendor file"**: Onemsiz uyari, tarama calisir. Vendor bilgisi gostermez ama IP/MAC alir.
- **arp-scan: "Interface not found"**: Dogru interface adini kontrol et: `ip a` veya `iw dev`
- **nmap: "Failed to resolve"**: IP araligini dogru yaz: `192.168.0.0/24` (CIDR notasyonu)
- **Hic cihaz bulunamadi**: Ag kablosu / WiFi bagli mi kontrol et, DHCP'den IP almis mi
