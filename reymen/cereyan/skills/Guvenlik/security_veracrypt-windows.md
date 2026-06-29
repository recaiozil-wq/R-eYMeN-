---
name: veracrypt-windows
title: "Veracrypt Windows"
tags: [security, windows]
description: VeraCrypt container creation, formatting, mounting, and Obsidian vault encryption on Windows. CLI syntax for VeraCrypt Format.exe and VeraCrypt.exe, elevation pitfalls, and multi-session workflow.
version: 1.1.0
author: hermes
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [veracrypt, encryption, container, volume, obsidian, vault, windows, cli, uac]
audience: user
related_skills: [obsidian-vault-kurallari, tam-sistem-yetkisi, gorsel-onaylama]
---


> **Kategori:** security

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | VeraCrypt container creation, formatting, mounting, and Obsidian vault encryption on Windows. CLI syntax for VeraCrypt Format.exe and VeraCrypt.exe, elevation pitfalls, and multi-session workflow. |
| **Nerede?** | security/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# VeraCrypt Windows — Container Yönetimi

## Overview

VeraCrypt ile şifreli container oluşturma, formatlama ve bağlama işlemleri. Özellikle Obsidian vault şifreleme senaryosu için kullanılır.

**TETİKLEYİCİLER:** "veracrypt", "şifrele", "encrypt", "container", "vault kutusu", "kutu oluştur", "kutuyu bağla"

## Adım 0 — Container Dosyasını Oluştur (Boş Dosya)

VeraCrypt Format.exe **kendi dosyasını oluşturmaz** — boş container dosyası önce elle yaratılmalıdır.

**Python ile (GÜVENİLİR — Git Bash'te çalışır):**
```python
f = r'C:\Users\marko\vault.hc'
with open(f, 'wb') as fh:
    fh.seek(524288000 - 1)  # 500 MB
    fh.write(b'\x00')
```

**fsutil ile (DİKKAT — Git Bash'te yol bozulur):**
```bash
# Git Bash'te ÇALIŞMAZ — C:\Users\marko → C:\Usersmarko'ya dönüşür
fsutil file createnew C:\Users\marko\vault.hc 524288000

# Doğru yol: PowerShell ile
powershell -Command "fsutil file createnew 'C:\Users\marko\vault.hc' 524288000"
```

## Adım 1 — Container Formatlama

VeraCrypt Format.exe ile CLI üzerinden format:

```bash
# VARSAYILAN (önerilen): AES + SHA-512 + FAT
"C:/Program Files/VeraCrypt/VeraCrypt Format.exe" /create C:\Users\marko\vault.hc /password SIFRE /size 500M /encryption AES /hash SHA-512 /filesystem FAT /silent
```

**Parametreler:**
| Parametre | Değer | Açıklama |
|-----------|-------|----------|
| `/create` | `<path>` | Container dosya yolu |
| `/password` | `<pwd>` | Şifre |
| `/size` | `<N>M` veya `<N>G` | Boyut (500M, 1G, vb.) |
| `/encryption` | AES, Serpent, TwoFish | Şifreleme algoritması |
| `/hash` | SHA-512, SHA-256, RIPEMD-160 | Hash algoritması |
| `/filesystem` | FAT, NTFS, exFAT | Dosya sistemi |
| `/silent` | (flag) | GUI'siz mod |

**🔴 KRİTİK UYARI — `/silent` Tuzağı:**
- `/silent` modunda VeraCrypt Format.exe **exit code 0 döner ama format GERÇEKLEŞMEMİŞ olabilir**
- Format.exe bir GUI uygulamasıdır — Git Bash'ten çağrıldığında komut satırını sessizce yok sayar ve hiçbir şey yapmadan çıkar
- **Exit code 0 ASLA güvenilir değildir.** Tek doğrulama yöntemi: dosyayı mount etmeyi denemek
- Eğer mount ederken "Parola yanlış" hatası alınırsa → format gerçekte başarısız olmuştur
- **Çözüm:** GUI üzerinden format yap (VeraCrypt → Birim Oluştur → adımları takip et)

**Notlar:**
- Şifre CLI'da düz metin geçilir — terminal geçmişinde kalır
- Container adı `.hc` uzantılı olabilir veya uzantısız — VeraCrypt içerikten tanır

## Adım 2 — Container'ı Bağlama (Mount)

```bash
# CLI mount (non-elevated — genellikle exit code 1 ile başarısız olur)
"C:/Program Files/VeraCrypt/VeraCrypt.exe" /volume C:\Users\marko\vault.hc /letter V /password SIFRE
```

**ÖNEMLİ:** VeraCrypt.exe mount komutu **Git Bash terminalinden** çalıştırıldığında exit code 1 döner ve başarısız olur. Nedeni:
1. **Elevation eksik** — VeraCrypt mount için admin yetkisi gerekebilir
2. **Git Bash ortamı** — Windows GUI uygulamaları Git Bash'ten her zaman düzgün çalışmaz

**Çözümler:**

**A) PowerShell ile elevation:**
```powershell
Start-Process 'C:\Program Files\VeraCrypt\VeraCrypt.exe' -ArgumentList '/volume C:\Users\marko\vault.hc /letter V /password SIFRE /q' -Verb RunAs -Wait
```
⚠️ Bu yöntem UAC prompt'u açar ve terminal kullanıcının "Evet" demesini bekler. Timeout riski vardır.

**B) GUI üzerinden manuel (kullanıcıya anlat):**
1. VeraCrypt'i aç
2. Sürücü harfi seç (V:)
3. "Select File..." → vault.hc'yi bul
4. "Mount" → şifreyi gir

## Adım 3 — Obsidian Vault'u Container'a Taşıma

```bash
# Container bağlıyken (V: sürücüsü):
xcopy "C:\Users\marko\OneDrive\Belgeler\Obsidian Vault\*" "V:\" /E /H /K /Y
# Sonra eski vault'u sil:
# (Opsiyonel: güvenli silme)
```

## Adım 4 — Başlangıçta Otomatik Bağlama

Henüz implemente edilmedi. Seçenekler:
1. **Manuel şifre girişli** — Windows Task Scheduler + VeraCrypt GUI
2. **Script ile şifre saklamalı** — Daha az güvenli ama otomatik
3. **Hiç otomatik bağlama** — Her kullanımda elle bağla

## Common Pitfalls

1. **"Komut satırı işlenirken sorun çıktı"** — VeraCrypt Format.exe CLI hatası. Format.exe bir GUI uygulamasıdır, Git Bash'ten çağrıldığında parametreleri işlemeyebilir. GUI üzerinden yap.
2. **🔴 /silent exit code 0 YALANCI** — Format.exe `/silent` modunda exit 0 döner ama format gerçekleşmemiş olabilir. **TEK doğrulama:** dosyayı mount et. "Parola yanlış" hatası alınırsa format başarısız demektir.
3. **Mount exit code 1** — VeraCrypt.exe mount Git Bash'ten çalışmaz. PowerShell + RunAs dene veya GUI kullan.
4. **fsutil yol bozulması** — Git Bash'te `C:\Users\marko\vault.hc` yolu `C:\Usersmarkovault.hc` olur. Python ile dosya oluştur (yukarıdaki gibi).
5. **Dosya masaüstünde değil** — Container dosyası farklı bir dizinde kalabilir (`C:\\Users\\marko\\` altına kaydedilmiş olabilir). Windows araması veya `find` ile bul.
6. **UAC timeout** — PowerShell RunAs terminal'de bekler, kullanıcının UAC'ı onaylaması gerekir. Zaman aşarsa yeniden dene.
7. **Dosya türü "VeraCrypt Volume" görünüyor ama mount olmuyor** — Windows dosya türü imzasına bakar, VeraCrypt mount ayrı bir işlemdir. Tür "VeraCrypt Volume" görünse bile format başarısız olmuş olabilir.

## Verification Checklist

- [ ] vault.hc dosyası mevcut (500 MB veya belirtilen boyutta)
- [ ] Windows "VeraCrypt Volume" olarak tanıyor
- [ ] VeraCrypt GUI'den mount edilebiliyor
- [ ] V: sürücüsü erişilebilir
- [ ] Obsidian vault içeriği başarıyla taşınmış
