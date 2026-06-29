---
name: tor-web-otomasyonu
title: Tor Web Otomasyonu — Form Doldurma, Login, Kayit, Siparis
description: "Tor Browser ile Selenium tabanli web otomasyonu: form doldurma, giris yapma, yeni uyelik olusturma ve siparis verme. HITL onayi ve OCR fallback entegredir."
version: 1.0.0
author: marko
platforms: [windows]
audience: user
tags: [tor, selenium, form, login, kayit, siparis, web-otomasyonu, hata-cozucu]
category: windows-automation
related_skills: [tor-arama-bypass-cozumu, gorsel-onaylama, screen-vision-analiz]
---


> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Tor Browser ile Selenium tabanli web otomasyonu: form doldurma, giris yapma, yeni uyelik olusturma ve siparis verme. HITL onayi ve OCR fallback entegredir. |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Tor Web Otomasyonu

## Overview

ReYMeN'in Tor Browser uzerinden web otomasyonu yapmasini saglar.  
Form doldurma, siteye giris, yeni uyelik olusturma ve siparis verme islemleri icin kullanilir.

**Modul:** `tor_otomasyonu.py` (ReYMeN projesinde)
**Motor entegrasyonu:** `motor.py` icinde 6 TOR_ araci

## When to Use

- Bir web sitesinde form doldurulmasi gerekiyorsa → `TOR_FORM_DOLDUR`
- Siteye kullanici adi/sifre ile giris yapilacaksa → `TOR_LOGIN`
- Yeni uyelik olusturulacaksa → `TOR_KAYIT` (HITL onayi gerektirir)
- Siparis verilecekse → `TOR_SIPARIS` (HITL onayi gerektirir)
- Anonimlik gerekiyorsa → `TOR_AC` ile basla

## Mimari

```
TOR_AC → Tor Browser baslat (Selenium + geckodriver)
  │
  ├─ TOR_FORM_DOLDUR({"ad":"Ali", "soyad":"Yilmaz"})
  │    → Asama 1: DOM (Selenium find_element)
  │    → Asama 2: Gorsel Sablon (OpenCV + .ReYMeN/nisanlar/)
  │    → Asama 3: Metin OCR (pytesseract)
  │
  ├─ TOR_LOGIN({"url":"...", "kullanici":"...", "sifre":"..."})
  │    → Sayfaya git → form doldur → submit
  │
  ├─ TOR_KAYIT({"url":"...", "bilgiler":{...}})
  │    → HITL onayi (insan_arayuzu.onay_iste)
  │    → Sayfaya git → form doldur → submit
  │
  ├─ TOR_SIPARIS({"url":"...", "urun":"...", "adres":{...}})
  │    → HITL onayi
  │    → Urun sayfasi → sepete ekle → adres gir → siparis ver
  │
  └─ TOR_KAPAT → Browser'i kapat
```

## Tor Browser Yolu (Windows)

```python
# Otomatik bulma sirasi:
C:\Users\{kullanici}\Desktop\Tor Browser\Browser\firefox.exe
C:\Tor Browser\Browser\firefox.exe
```

## Gereksinimler

```bash
pip install selenium
pip install mss pytesseract opencv-python numpy Pillow
# + geckodriver PATH'te veya belirt
```

## Onemli Uyarilar

1. **Tor yuksek gecikmelidir** — Sayfa yukleme 30-45sn surebilir. `_SAYFA_BEKLEME=45`, `_FORM_BEKLEME=30`
2. **CAPTCHA/WAF** — Tor cikis dugumleri Cloudflare captcha ile karsilasabilir. Basit captcha'lar OCR ile cozulur, reCAPTCHA harici API gerektirir.
3. **HITL** — `TOR_KAYIT` ve `TOR_SIPARIS` insan onayi gerektirir (`insan_arayuzu.onay_iste`). Import yoksa sessizce atlanir.
4. **Proxy** — Tor SOCKS5 port 9150 (Tor Browser), alternatif 9050 (Tor service)
5. **Gecici dosya** — `.ReYMeN/nisanlar/` klasorune .png sablonlar eklenebilir (opsiyonel)

## Form Alan Adi Donusumleri (Turkce)

`FormDoldurucu._ALAN_KARESi` sozlugu Turkce alan adlarini DOM'daki karsiliklariyla eslestirir:

| Kullanici gonderir | DOM'da aranir |
|-------------------|---------------|
| `"ad"` | name, firstname, first_name, ad, isim, adınız |
| `"soyad"` | surname, lastname, last_name, soyad, soyisim |
| `"eposta"` | email, e-mail, mail, eposta, e_posta |
| `"telefon"` | phone, tel, telefon, mobile, gsm |
| `"sifre"` | password, pass, sifre, parola |
| `"adres"` | address, adres, street |
| `"il"` | city, il, sehir, province |
| `"ilce"` | district, ilce, county |
| `"posta_kodu"` | zip, postcode, zipcode |
| `"tc_kimlik"` | tc, tckimlik, identity, ssn |
| `"kullanici_adi"` | username, user, kullanici |

## Common Pitfalls

1. **geckodriver bulunamadi** — PATH'e ekle veya `geckodriver_yolu` parametresiyle belirt
2. **Tor Browser kapaliysa hata** — `TOR_AC` ile once baslat, sonra diger araclari kullan
3. **DOM'da form alani bulunamadi** — 3 asamali NisanBulucu devreye girer (DOM → Sablon → OCR)
4. **CAPTCHA cikarsa** — `hata_cozucu.HataWatchdog` yakalar, `HATA_KOD_AL` ile kod uretir
5. **HITL onayi ImportError** — `insan_arayuzu` yoksa onay atlanir, log uyarisi yazilir
6. **JSON parse hatasi** — Parametreler her zaman JSON string olarak gonderilmeli

## Referans Dosyalari

| Dosya | Icerik |
|-------|--------|
| `tor_otomasyonu.py` | Ana modul (ReYMeN projesinde) |
| `.ReYMeN/nisanlar/` | Gorsel sablon .png dosyalari (opsiyonel) |

## Verification Checklist

- [ ] `TOR_AC` → Browser basliyor
- [ ] `TOR_KAPAT` → Browser kapaniyor
- [ ] `TOR_FORM_DOLDUR` → Form alanlari doluyor
- [ ] `TOR_LOGIN` → Siteye giris yapiliyor
- [ ] `TOR_KAYIT` → HITL onayi isteniyor
- [ ] `TOR_SIPARIS` → HITL onayi isteniyor
- [ ] OCR fallback: DOM basarisiz olunca NisanBulucu devreye giriyor
