---
name: tersine-muhendislik
title: "Tersine Muhendislik"
tags: [security]
description: Kullanıcı bir .exe, .dll, .apk, .elf veya bilinmeyen ikili dosyayı analiz ettirmek istediğinde çalıştır. RE-HERMES v3 aracıyla pasif statik analiz yapar; hash, entropy, IOC, şüpheli API ve 5N1K raporu üretir. Dosya hiçbir zaman çalıştırılmaz.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [security, reverse-engineering, malware, apk, pe, elf, static-analysis, ioc]
audience: user
related_skills: [security-best-practices, port-firewall-taramasi]
---

# Tersine Mühendislik — RE-HERMES v3

## Ne Zaman Kullan

Kullanıcı şunlardan birini söylediğinde bu skill'i yükle ve adımları uygula:
- "Bu dosyayı analiz et / incele / tara"
- ".exe / .apk / .dll / .so dosyasına bak"
- "Zararlı mı değil mi?"
- "Tersine mühendislik yap"
- "IOC çıkar", "hash al", "izin listesi"

## Script Konumu

```
C:\Users\marko\OneDrive\payton kodları\tersine mühendislik.py
```

## Kullanım

### Temel çalıştırma (dosya yolu argüman olarak ver)
```powershell
python "C:\Users\marko\OneDrive\payton kodları\tersine mühendislik.py" "<HEDEF_DOSYA_YOLU>"
```

Örnek:
```powershell
python "C:\Users\marko\OneDrive\payton kodları\tersine mühendislik.py" "C:\Users\marko\Downloads\ornek.apk"
```

### İlk çalıştırmada ne sorar?
1. **API anahtarı** — DeepSeek anahtarı girilirse AI yorumu da eklenir. Boş bırakılırsa OFFLINE mod (yalnız yerel statik analiz).
   → API anahtarı `.env` veya `config.json` içinde varsa otomatik yüklenir, tekrar sorulmaz.
2. **Çalışma alanı klasörü** — Boş bırakılırsa otomatik oluşturur (`workspace_<dosyaadı>/`).

## Çıktılar

Script bitince `workspace_<dosyaadı>/` içinde şunlar oluşur:

| Dosya/Klasör | İçerik |
|---|---|
| `report.md` | Tam analiz raporu (hash, format, entropy, IOC, 5N1K, AI yorumu) |
| `static_analysis/extracted_strings.txt` | Tüm ASCII + UTF-16 string'ler |
| `static_analysis/iocs.json` | Yapılandırılmış IOC listesi (URL, IP, domain, registry) |
| `static_analysis/unpacked/` | APK içindeki DEX ve .so dosyaları |
| `bin/` | Analiz edilen dosyanın kopyası |

## Desteklenen Dosya Tipleri

| Uzantı | Ne analiz eder |
|---|---|
| `.exe` / `.dll` | PE header, mimari, section'lar, import DLL'leri |
| `.apk` | İzinler, classes.dex, lib/*.so ELF mimarisi, imza |
| ELF (uzantısız/`.so`) | Sınıf, endian, tip, mimari |
| Diğer | Hash, entropy, string'ler, IOC |

## Raporu Obsidian'a Taşı

Analiz tamamlanınca raporu vault'a kopyala:
```powershell
$src = "<workspace_klasoru>\report.md"
$dst = "C:\Users\marko\OneDrive\Belgeler\Obsidian Vault\Hermes\Analizler\<dosya_adi>_rapor.md"
Copy-Item $src $dst
```

## Güvenlik Kuralları

- Dosya **hiçbir zaman çalıştırılmaz** — tüm analiz pasif/statiktir.
- Script harici bağımlılık gerektirmez (yalnız Python stdlib kullanır).
- IOC'ler raporda **defang'lı** gösterilir (tıklanabilir değil).
- Şüpheli dosyayı asla sandbox dışında çalıştırma.

## Sık Karşılaşılan Durumlar

**"config.json yok" uyarısı** → Normal, ilk çalıştırmada otomatik oluşturulur.

**API anahtarı istiyor** → Boş bırak (Enter), OFFLINE mod yeterlidir; statik rapor tam gelir.

**APK analizi uzun sürüyor** → DEX ve .so dosyaları tek tek işleniyor, normaldir.

**"Import DLL'leri" bölümü boş** → Dosya packed/şifreli olabilir; entropy değerine bak (>7.5 = şüpheli).
