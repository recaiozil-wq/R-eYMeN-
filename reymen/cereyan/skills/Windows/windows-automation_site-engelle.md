
> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | >- |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: site-engelle
description: >-
title: "Site Engelle"
  hosts dosyası + Windows Firewall ile çift katmanlı engelleme.
  Tor Browser da dahil hiçbir şekilde erişilemez.
version: 1.0.0
author: Hermes
platforms: [windows]
metadata:
  hermes:
    tags: [block, firewall, hosts, credit-card, payment, security]
category: windows-automation
audience: maintainer
tags: [automation, system, windows]
---Kredi kartı/ödeme sayfası görülen domain'i derhal engeller.



# Site Engelle

## Tetikleyici
Hermes'in açtığı bir sayfada şunlardan biri görülürse DERHAL engelle:
- Kredi kartı formu
- Ödeme / satın alma sayfası
- cart/add, checkout, payment, billing
- Herhangi bir ücret talep eden sayfa

## Yöntem (Çift Katman)

### 1. Hosts dosyası (normal tarayıcılar için)
```
C:\Windows\System32\drivers\etc\hosts
```
Satır: `127.0.0.1 domain.com`

Script: `C:\Users\marko\AppData\Local\hermes\scripts\block_site.ps1`

### 2. Windows Firewall (Tor dahil her şey için)
IP adresini bul:
```powershell
nslookup domain.com
```
Firewall kuralı ekle:
```powershell
New-NetFirewallRule -DisplayName "Block-domain" -Direction Outbound -RemoteAddress IP -Action Block
```

### 3. Obsidian notu güncelle
`07-System/Engelli-Siteler.md` tablosuna ekle.

## Kullanıcıdan onay
Onay istenmez. Direkt engellenir.
