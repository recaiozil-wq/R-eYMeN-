---
name: windows-hata-cozumu
title: Windows Hata Cozumu — Watchdog, Kodlama, Terminal Parse, Cozum Uygulama
description: "Windows'ta hata tespiti, kodlama ve cozum yonetimi. 4 bilesen: HataWatchdog (ekran OCR), HataKoduUretici (HATA-XXXX), TerminalHataParser (PowerShell/cmd), CozumUygulayici (patch)."
version: 1.0.0
author: marko
platforms: [windows]
audience: user
tags: [hata, error, watchdog, ocr, terminal, patch, cozum, ayiklama, hata-kodu]
category: windows-automation
related_skills: [screen-vision-analiz, gorsel-onaylama, tor-web-otomasyonu]
---

# Windows Hata Cozumu

## Overview

Windows ortaminda hata tespiti, kodlanmasi ve cozumu icin 4 bilesenli entegre sistem.

**Modul:** `hata_cozucu.py` (ReYMeN projesinde)
**Motor entegrasyonu:** `motor.py` icinde 5 HATA_ araci

## Bilesenler

### 1. HataWatchdog — Ekran Hatasi Izleme

```python
watchdog = HataWatchdog(aralik_sn=5.0)
watchdog.baslat()    # Arka planda ekrani tara
watchdog.durdur()    # Durdur
```

- `mss` ile periyodik ekran goruntusu alir
- `pytesseract` ile OCR yapar
- "Hata", "Error", "Exception", "Access Denied" gibi kelimeleri arar
- Bulunca callback tetikler
- `threading.Event.wait()` ile CPU kilitlemez
- mss/pytesseract yoksa graceful degrade (sessizce calisir)

### 2. HataKoduUretici — HATA-XXXX Kodlama

```python
uretici = HataKoduUretici()
kayit = uretici.kaydet("ModuleNotFoundError: No module named 'xyz'")
# -> HATA-0001: [import] ModuleNotFoundError...

uretici.cozum_ekle("HATA-0001", "Cozum: pip install xyz")
```

- `HATA-0001`, `HATA-0002` ... seklinde artan kod uretir
- `.ReYMeN/hata_kodlari/HATA-0001.md` formatinda kaydeder
- Icerik: kod, zaman, kategori, ozet, ham_metin, ekran_yolu, cozum_durumu
- Kategoriler: import, syntax, tip, dosya, baglanti, bellek, ekran, diger
- Sayaç: `_sayaç.txt` dosyasinda saklanir (hizli, dosya tarama yok)

### 3. TerminalHataParser — PowerShell/cmd Hata Ayiklama

```python
parser = TerminalHataParser()
sonuc = parser.parse("PS> python test.py\nError: Baglanti reddedildi")
# -> {"hata_var": True, "hata_sayisi": 1, "ozet": "..."}
```

- Regex ile "Hata:", "Error:", "Exception:", "failed:", "AccessDenied" kalıplarini arar
- PowerShell ozel desenleri: `TerminatingError()`, `CategoryInfo`, `FullyQualifiedErrorId`
- Traceback bloklarini ayiklar

### 4. CozumUygulayici — Dosya Yamalama

```python
cozum = CozumUygulayici()
sonuc = cozum.uygula("""
HATA-0001:
Dosya: hata_cozucu.py
Satir: 42
Eski: hatali_kod
Yeni: duzeltilmis_kod
""")
# -> {"basarili": True, "patch_sonuc": "..."}
```

- "HATA-XXXX:" ile baslayan cozum metnini parse eder
- Dosya/Satir/Eski/Yeni bilgilerini cikarir
- `Path().read_text()` + `replace()` veya satir bazli degisiklik yapar
- Basarili olursa `.ReYMeN/hata_kodlari/` dosyasinda durumu "cozuldu" yapar

## Motor Araclari

| Arac | Islev |
|------|-------|
| `HATA_WATCH_BASLAT` | Ekran izlemeyi baslat |
| `HATA_WATCH_DURDUR` | Ekran izlemeyi durdur |
| `HATA_KOD_AL("hata metni")` | Hatayi kodla, Claude'a gonderilecek kodu ver |
| `TERMINAL_HATA_PARSE("cikti")` | Terminal ciktisindaki hatalari ayikla |
| `COZUM_UYGULA("HATA-XXXX:...")` | Claude'dan gelen cozumu dosyaya uygula |

## Klasor Yapisi

```
.ReYMeN/
  hata_kodlari/
    _sayaç.txt          # Sayaç (1, 2, 3...)
    HATA-0001.md         # Hata kaydi
    HATA-0002.md
```

## Common Pitfalls

1. **mss/pytesseract yok** — Watchdog sinirli calisir, OCR yapamaz ama hata vermez
2. **Regex hatasi** — PowerShell desenlerinde `+` karakterini `\+` ile escape et
3. **Cozum dosya yolu** — Cozum metnindeki dosya yolu ReYMeN proje kokune gore verilir
4. **Cozum eski metin** — `replace()` ile calisir, eski metin dosyada tam eslesmeli
5. **Lock contention** — `threading.Lock` ile `tum_becerileri_indeksle` korunur
6. **baglanti() contextmanager** — commit/rollback otomatik, finally'de kapanir

## Verification Checklist

- [ ] `HATA_KOD_AL("test")` → HATA-0001 donuyor
- [ ] `.ReYMeN/hata_kodlari/HATA-0001.md` olusuyor
- [ ] `TERMINAL_HATA_PARSE("Error: test")` → 1 hata buluyor
- [ ] `HATA_WATCH_BASLAT` + `HATA_WATCH_DURDUR` → thread basliyor/duruyor
- [ ] `COZUM_UYGULA` ile patch uygulaniyor
- [ ] Tum import'lar try/except ile (graceful degrade)
