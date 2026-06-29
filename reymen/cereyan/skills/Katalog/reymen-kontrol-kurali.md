---
name: reymen-kontrol-kurali
title: ReYMeN Kontrol Kuralı
description: "Yok" demeden önce 3 farklı yöntemle kontrol et, altyapı eksikse pes etme.
category: kullanici
---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | "Yok" demeden önce 3 farklı yöntemle kontrol et, altyapı eksikse pes etme. |
| **Nerede** | `misc\hermes-integration\reymen-kontrol-kurali.md` |
| **Ne Zaman** | Genel AI gorevlerinde |
| **Neden** | Reymen Kontrol Kurali islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |

Kim: AI gelistiricisi
Ne: "Yok" demeden önce 3 farklı yöntemle kontrol et, altyapı eksikse pes etme.
Nerede: `misc\hermes-integration\reymen-kontrol-kurali.md`
Ne Zaman: Genel AI/ML gorevlerinde
Neden: Reymen Kontrol Kurali islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# ReYMeN Kontrol Kuralı

> **Kategori:** kullanici/kontrol

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Bir şeyin "yok" olduğunu söylemeden önce 3 farklı yöntemle kontrol eder. |
| **Nerede?** | Terminal (find, ls, registry, vs.) |
| **Ne Zaman?** | Bir tool/paket/dosya bulunamadığında hemen "yok" denmeden önce. |
| **Neden?** | Karar #3: PowerBI "yok" hatası. Kiral38 buldu, asistan bulamadı. Sebep: yüzeysel arama. |
| **Nasıl?** | 1. find ile kapsamlı tarama 2. Store Apps / kayıtlı uygulamalar 3. VS Code extensions / alternatif yollar |

## Akış

```
"X yok" deme eşiğine gelindiğinde:
  ↓
1. Yöntem: find /c/ -iname "*X*" (kapsamlı tarama)
2. Yöntem: Get-StartApps / kayıtlı uygulamalar (PowerShell)
3. Yöntem: ~/.vscode/extensions/ + alternatif yollar
  ↓
3'ü de boşsa → "X yok" DE (gerçekten yok)
Biri bulursa → kullan
```

## Köken

Karar #3 (21 Haziran 2026): Power BI Desktop'ı Kiral38 buldu, Hermes bulamadı. Çözüm olarak bu skill oluşturuldu.
