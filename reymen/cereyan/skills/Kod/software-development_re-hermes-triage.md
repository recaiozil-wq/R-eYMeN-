---
name: re-hermes-triage
id: re-hermes-triage
title: "RE-Hermes — Pasif Statik Tersine Mühendislik Triyaj Aracı"
description: "User-developed Python tool for static RE triage of PE/ELF/APK/ham binaries. Zero external deps (stdlib only). Optional DeepSeek AI commentary. 5N1K educational layer."
tags: [reverse-engineering, malware-analysis, triage, static-analysis, pe, elf, apk, python, self-developed]
category: software-development
audience: contributor
trigger: "User says 're-hermes', 'triyaj', 'tersine mühendislik', 'apk analiz', 'exe analiz', 'zararlı analiz', or asks to analyze a binary/APK/executable"
---

# RE-Hermes Triyaj Aracı

## Lokasyon

```
C:\Users\marko\re-hermes\re-hermes.py
C:\Users\marko\re-hermes\re-hermes.bat    (çift tıkla çalıştırma)
C:\Users\marko\re-hermes\config.json       (API anahtarı)
```

## Kullanım

```bash
cd C:\Users\marko\re-hermes

# APK analizi
python re-hermes.py dosya.apk

# PE (.exe/.dll) analizi
python re-hermes.py dosya.exe

# ELF analizi
python re-hermes.py dosya.elf

# Ham/bilinmeyen ikili
python re-hermes.py dosya.bin
```

Ya da `.bat` ile (çift tıkla, dosya yolunu sorar):
```
re-hermes.bat
```

## Desteklenen Formatlar

| Format | Tespit | Analiz |
|--------|--------|--------|
| PE (.exe/.dll) | MZ header | makine, section'lar, import DLL'ler, bits (32/64) |
| ELF | \x7fELF magic | sınıf, endian, tip (EXEC/DYN/REL), mimari |
| APK | ZIP + AndroidManifest.xml | izinler, classes.dex IOC, lib/*.so (ELF parse), imza, resources |
| Ham veri | — | hash, entropy, strings, IOC, suspicious token |

## Çıktılar

- **Terminal özeti** — hash, format, entropy, IOC sayısı, suspicious token'lar
- **Markdown rapor** — `workspace_<dosya>/report.md`
  - Format bilgisi
  - APK içeriği (varsa izin + dex + .so)
  - Entropy yorumu
  - IOC (defang'li URL/IP/domain/email/registry)
  - Suspicious token'lar
  - **5N1K eğitim katmanı** — her dosya tipini sıfırdan açıklar
  - **DeepSeek AI yorumu** (API anahtarı varsa)

## API Anahtarı

İlk çalıştırmada sorulur. `config.json` içinde saklanır:
```json
{
  "api_setting": {
    "api_key": "sk-...",
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-v4-flash"
  }
}
```

Boş bırakılırsa OFFLINE mod (statik + 5N1K, AI yorumu yok).

## Önemli Kurallar

- **HİÇBİR DOSYA ÇALIŞTIRILMAZ** — tamamen pasif/statik analiz
- **Sıfır harici bağımlılık** — sadece Python stdlib (zipfile, hashlib, struct, re, urllib)
- Windows, Linux, macOS'te çalışır

## Bilinen Bug Fix Geçmişi

- v3'te `_init_` (tek underscore) → `__init__` (dunder) düzeltildi — constructor çalışmıyordu
- `import subprocess` kaldırıldı (v3'te kullanılmıyor)
- APK string çıkarma: ZIP içindeki raw byte'lar yerine unpack edilen dex/so üzerinden yapılır
