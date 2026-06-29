---
name: web-tetikleyici-sistemi
title: Web Tetikleyici Sistemi
description: 5 tetikleyici ile ajanin ne zaman web'e gidecegini otomatik belirleme.
category: sistem
Kim: ReYMeN ajani
Ne: 5 tetikleyici ile ajanin ne zaman web'e gidecegini otomatik belirleme.
Nerede: `reymen\web-tetikleyici-sistemi.md`
Ne Zaman: ReYMeN sistemi yapilandirmasi gerektiginde
Neden: Web Tetikleyici Sistemi islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Web Tetikleyici Sistemi


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ReYMeN ajani |
| **Ne** | 5 tetikleyici ile ajanin ne zaman web'e gidecegini otomatik belirleme. |
| **Nerede** | `reymen\web-tetikleyici-sistemi.md` |
| **Ne Zaman** | ReYMeN sistemi yapilandirmasi gerektiginde |
| **Neden** | Web Tetikleyici Sistemi islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar (Kali, Windows, CAD). OnceHafiza kullanan her ajan. |
| **Ne?** | Ajanın web araması yapması gereken 5 durumu otomatik tespit eder. Gereksiz web çağrısını önler. |
| **Nerede?** | `reymen/sistem/_web_tetikleyici.py` → `ogrenmeler.web_arama_sebebi` kolonu. |
| **Ne Zaman?** | Her görev geldiğinde, hafıza kontrolünden hemen sonra, LLM çağrısından önce. |
| **Neden?** | LLM token israfını önlemek için. Boşuna web araması yapıp 50KB context şişirmek yerine, sadece gerektiğinde ara. |
| **Nasıl?** | 5 tetikleyici sırayla kontrol edilir: T1(boş)→T3(hata)→T2(güven)→T4(tarih)→T5(çelişki). Her biri bir puan döndürür, eşik aşılırsa web'e gidilir. |

---

## 5 Tetikleyici (Öncelik Sırasıyla)

| # | Tetikleyici | Koşul | Puan | Ne Zaman? |
|:-:|:------------|:------|:----|:----------|
| 1 | **T1: Hafiza bos** | `COUNT=0` | 1.0 | Yeni tool/kategori hic bilinmiyor |
| 2 | **T3: Gorev basarisiz** | `hata >= 2` | 0.8 | 2. hatadan sonra web'de cozum ara |
| 3 | **T2: Guven dusuk** | `guven < 0.5` | 0.5-0.3 | 1 basari 3 hata = guven 0.25 |
| 4 | **T4: Gecerlilik asmis** | `tarih < bugun` | 0.3 | 6+ ay once ogrenilmis bilgi |
| 5 | **T5: Celiski** | `icerik1 != icerik2` | 0.6-0.4 | Video/Kullanici farkli soyluyor |

---

## Akış

```
GÖREV GELDİ
  ↓
T1: Hafizada kayit var mi?
  ├─ HAYIR → WEB'E GİT (direkt)
  └─ EVET → devam
              ↓
T3: hata_sayisi >= 2 mi?
  ├─ EVET → WEB'E GİT (cozum ara)
  └─ HAYIR → devam
              ↓
T2: guven_skoru < 0.5 mi?
  ├─ EVET → WEB'E GİT (dogrula)
  └─ HAYIR → devam
              ↓
T4: gecerlilik_tarihi < bugun mu?
  ├─ EVET → WEB'E GİT (arka planda tazele)
  └─ HAYIR → devam
              ↓
T5: Iki kaynak celisiyor mu?
  ├─ EVET → WEB'E GİT (hakem karar)
  └─ HAYIR → HAFIZADAN KULLAN
```

---

## Veritabanı

`ogrenmeler` tablosuna eklenen kolon:
- `web_arama_sebebi TEXT DEFAULT ''` — neden arama yapildi?

## Test

```python
from _web_tetikleyici import web_gerekli_mi

ateslendi, sebep, puan = web_gerekli_mi("yeni_tool", hata_sayisi=0)
if ateslendi:
    web_search(sebep)  # web'de ara
else:
    once_hafiza.ara(hedef)  # hafizadan kullan
```
