---
name: test-suite-ve-api-setup-deseni
title: Test Suite ve API Anahtar Kurulumu Deseni
description: "Entegrasyon test suite (try/except'li, 13 test) ve interaktif API anahtar kurulumu (--liste, --kontrol, interaktif)"
tags: [testing, setup, api-keys, pattern]
audience: contributor
---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Entegrasyon test suite (try/except'li, 13 test) ve interaktif API anahtar kurulumu (--liste, --kontrol, interaktif) |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Test Suite ve API Anahtar Kurulumu

## Test Suite
```python
def test(ad, fn):
    try:
        fn()
        gecti.append(ad)
        print(f"  OK {ad}")
    except Exception as e:
        gecemedi.append((ad, str(e)))
        print(f"  FAIL {ad}: {e}")

TESTLER = [("Provider test", t_providers), ...]
for ad, fn in TESTLER:
    test(ad, fn)
print(f"Sonuc: {len(gecti)}/{len(TESTLER)}")
```

Her modul icin ayri test fonksiyonu, try/except ile guvenli calistirma.

## API Anahtar Kurulumu
```python
python setup_keys.py           # Interaktif kurulum
python setup_keys.py --liste   # Eksik anahtarlari listele
python setup_keys.py --kontrol # Provider durum raporu
```

Anahtarlar: env_adi, aciklama, zorunlu_mu, kaynak_url
- Bos birakilan anahtarlar atlanir
- .env satir sirasi korunur
- *** prefix kontrolu ile mevcut degerleri ezmez
