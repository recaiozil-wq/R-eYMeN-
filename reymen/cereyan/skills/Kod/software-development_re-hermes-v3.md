---
name: re-hermes-v3
title: "RE-Hermes v3 — Reverse Engineering Triage Agent"
description: "Python stdlib ile APK/PE/ELF/ham ikili dosyalardan PASIF statik analiz. Hash, entropy, PE/ELF header, APK izin+dex, IOC, suspicious token, 5N1K eğitim katmanı, opsiyonel DeepSeek AI yorumu."
tags: [reverse-engineering, malware-analysis, apk, pe, elf, static-analysis, triage]
category: software-development
audience: contributor
---

# RE-Hermes v3 — Reverse Engineering Triage Agent

## Konum
- Script: `C:\Users\marko\re-hermes\re-hermes.py`
- Batch: `C:\Users\marko\re-hermes\re-hermes.bat`
- Config: `C:\Users\marko\re-hermes\config.json`

## Kullanım
```bash
cd C:\Users\marko\re-hermes
python re-hermes.py <hedef_dosya>
# veya:
re-hermes.bat <hedef_dosya>
```

## Desteklenen dosya türleri
| Tür | Format | Analiz |
|-----|--------|--------|
| APK (.apk) | ZIP | izinler, classes.dex string/IOC, lib/*.so ELF header |
| PE (.exe/.dll/.sys) | MZ | header, mimari, section'lar, import DLL'leri |
| ELF | \x7fELF | tip, endian, bits, mimari |
| Ham/bilinmeyen | magic | hash, entropy, strings, IOC |

## Yaptığı analiz (pasif — dosya çalıştırılmaz)
1. **Hash** — MD5 / SHA1 / SHA256 (1MB chunk streaming)
2. **Entropy** — Shannon + packed/şifreli yorumu
3. **Format** — magic + PE/ELF header parse
4. **Strings** — ASCII + UTF-16LE streaming
5. **IOC** — URL / IPv4 / domain / e-posta / registry regex + defang
6. **Suspicious** — 70+ yüksek-sinyalli API/davranış token taraması
7. **5N1K** — Her dosya türü için "ne/nerede/ne zaman/nasıl/neden/kim" eğitim katmanı
8. **DeepSeek AI** (opsiyonel) — API anahtarı varsa bulgular LLM'e yorumlatılır

## Çıktı
- `workspace_<dosya>/report.md` — tüm statik bulgular + 5N1K + AI yorumu
- `workspace_<dosya>/static_analysis/extracted_strings.txt` — ham string dökümü
- `workspace_<dosya>/static_analysis/iocs.json` — IOC yapısal JSON

## Batch Karşılaştırma (Çoklu APK)

Bu skill altındaki `references/apk-comparison-methodology.md` dosyasında belgelenmiştir.

Kullanıcı birden çok APK'yı analiz edip karşılaştırmak istediğinde:
1. Tüm APK'ları arka planda paralel çalıştır
2. Raporlardan token/metrik verilerini çıkar
3. Token footprint'lerine göre grupla (aynı token × sayı = aynı familya)
4. Risk skorlama kriterlerine göre sırala
5. En tehlikeli grubu belirt

## Derin Analiz — Jadx ile Decompile

RE-Hermes triyajı tamamlandıktan sonra şüpheli APK'lar için:

```bash
# jadx kurulum (bir kere)
curl -sL "https://github.com/skylot/jadx/releases/download/v1.5.1/jadx-1.5.1.zip" -o /tmp/jadx.zip
unzip -qo /tmp/jadx.zip -d /c/Users/marko/jadx

# Decompile
/c/Users/marko/jadx/bin/jadx.bat -d output_dir hedef.apk

# Java kodunda token ara
find output_dir -name "*.java" | xargs grep -l "getDeviceId\|Runtime.exec\|AccessibilityService" 2>/dev/null
```

## BİLİNEN HATALAR — SuspiciousScanner False Positive

`SuspiciousScanner` substring eşleştirme kullanır (`"curl" in "left-curly-bracket"` -> True). Bu şu token'larda yanlış alarm üretir:

| Token | False Positive Kaynağı | Açıklama |
|-------|----------------------|----------|
| `curl` | `left-curly-bracket`, `right-curly-bracket` | "curl" substring "curly" içinde |
| `ptrace` | `perftools7tracing...` | "trace" içeren C++ sembol adları |
| `GetProcAddress` | `eglGetProcAddress` | OpenGL ES standard API |
| `getDeviceId` | `getDeviceIds` (çoğul) | TensorFlow/NNAPI diagnostic logging |

**Doğrulama yöntemi:** Şüpheli token bulunca, APK byte seviyesinde kontrol et:
```python
with open("hedef.apk", "rb") as f:
    data = f.read()
count = data.count(b"curl")  # substring degil, tam byte
```

**Düzeltme planı:** `SuspiciousScanner.KEYWORDS` iki kategoriye ayrılmalı:
- `EXACT_WORDS` = word boundary regex (`\bcurl\b`, `\bptrace\b`)
- `SUBSTRINGS` = mevcut `in` mantığı (`chmod`, `AccessibilityService` gibi kısa kelimeler)

## Notlar
- **SIFIR HARİCİ BAĞIMLILIK** — sadece Python stdlib (zipfile, hashlib, urllib, struct, re)
- OFFLINE çalışır; AI katmanı sadece API anahtarı varsa aktiftir
- APK içindeki .so dosyaları ELF olarak parse edilir (mimari tespiti)
- 5N1K katmanı bulunan her dosya türünü sıfırdan açıklar — eğitim amaçlı

## SuspiciousScanner — False Positive Koruması
`SuspiciousScanner` iki katmanlı eşleştirme kullanır:
1. **WORD_KEYWORDS**: `\b` word boundary regex ile eşleşir (harf/rakam/altçizgi sonunda sınır)
2. **PATH_KEYWORDS**: Slash/nokta/backslash içeren keyword'ler için path-aware regex (`(?<![a-zA-Z0-9_/\\])...`)

Bu sayede:
- `curl` → `left-curly-bracket` ile karışmaz
- `ptrace` → C++ symbol `tracing...` ile karışmaz
- `GetProcAddress` → `eglGetProcAddress` (OpenGL) ile karışmaz
- `getDeviceId` → `getDeviceIds` (TensorFlow NNAPI diagnostic) ile karışmaz

Yeni keyword eklerken dikkat:
- Normal kelime ise → `WORD_KEYWORDS` listesine
- `/` veya `\` veya `.` içeriyorsa → `PATH_KEYWORDS` listesine
- API adları (CamelCase) `\b` için sorunsuzdur
- Jadx hatalı decompile (12+ error) obfuscated APK'larda normaldir — native .so için Ghidra/IDA gerekir
