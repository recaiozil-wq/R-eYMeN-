
> **Kategori:** security

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | >- |
| **Nerede?** | security/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: port-firewall-taramasi
description: >-
title: "Port Firewall Taramasi"
  risk değerlendirmesi. TETİKLEYİCİ: "güvenlik taraması", "açık port",
  "firewall kontrol", "port tara", "hangi portlar açık"
version: 1.0.0
author: marko
tags: [guvenlik, windows, port, firewall, tarama, nmap]
category: security
audience: user
---Açık port tespiti ve firewall analizi — netstat + güvenlik duvarı kontrolü,



# Windows Güvenlik Taraması

## Sıralama

### 1. Açık Portları Listele
```powershell
netstat -ano | Select-String LISTENING
```

Çıktıda `0.0.0.0:PORT` = her arayüzde dinliyor, `127.0.0.1:PORT` = sadece localhost.

### 2. Firewall Profillerini Kontrol Et
```powershell
Get-NetFirewallProfile | Format-Table Name,Enabled,DefaultInboundAction
```
- `DefaultInboundAction: Block` = güvenli ✅
- `DefaultInboundAction: Allow` = tüm gelen bağlantılar serbest ❌

### 3. Belirli Portlar İçin Aktif Allow Kuralı Var mı?
```powershell
Get-NetFirewallPortFilter | Where-Object { $_.LocalPort -eq 135 -or $_.LocalPort -eq 445 } | Get-NetFirewallRule | Where-Object { $_.Enabled -eq 'True' -and $_.Direction -eq 'Inbound' -and $_.Action -eq 'Allow' }
```
Hiç sonuç dönmezse → portlar firewallda bloke.

## Yorumlama

| netstat | Firewall | Gerçek Durum |
|---------|----------|-------------|
| Port dinliyor (0.0.0.0) | Block + Allow kuralı yok | ✅ Bloke — güvenli |
| Port dinliyor (0.0.0.0) | Allow kuralı var | ❌ Açık — riskli |
| Sadece localhost | Farketmez | ✅ Güvenli |

## Kritik Portlar ve Ne Yapmalı

| Port | Servis | Kapatılabilir mi? |
|------|--------|------------------|
| 135/tcp | RPC | ❌ Kapatma — Windows çekirdek servisi |
| 445/tcp | SMB | ❌ Kapatma — Docker bağımlı |
| 139/tcp | NetBIOS | ✅ Kapatılabilir ama gerek yok (LAN) |
| 7680/tcp | Windows Update | ✅ Dokunma |
| 27036/tcp | Steam | ✅ Dokunma |
| 11434/tcp | Ollama | ✅ localhost — güvenli |

## Risk Değerlendirme Şartları

1. **NAT arkası (ev routerı):** Güvende. Portlar internete kapalı.
2. **Public IP (modem bridge mode):** Acil kapatma gerekir.
3. **Router port forward:** Varsayılan kapalıdır, kontrol edilebilir.

## Uyarılar
- 135 kapatılırsa → Task Scheduler, COM, WMI çalışmaz
- 445 kapatılırsa → Docker volume paylaşımları, dosya paylaşımı kırılır
- Firewall Block ise dokunma — portların dinlemesi sorun değil

## Kaynak
LuNiZz/siber-guvenlik-sss + canlı Windows taraması (2026-06-11)
Obsidian: vault/Hermes/windows-guvenlik-taramasi.md
