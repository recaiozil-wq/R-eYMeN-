---
name: reymen-motor-arac-ekleme
description: ReYMeN motor.py'ye yeni arac/tool modulu ekleme pattern'i. Graceful degradation, TOOLSET kaydi, calistir() erken kontrol, sistem_talimati.py guncellemesi.
---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | ReYMeN motor.py'ye yeni arac/tool modulu ekleme pattern'i. Graceful degradation, TOOLSET kaydi, calistir() erken kontrol, sistem_talimati.py guncellemesi. |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# ReYMeN Motor Arac Ekleme

ReYMeN'in `motor.py` katmanina yeni bir arac modulu eklemek icin standart pattern.

## Adim 1: Modulu Olustur

Yeni `.py` dosyasi su kurallara uyar:
- `from __future__ import annotations`
- Tum opsiyonel import'lar `try/except` ile (graceful degrade)
- `print()` yerine `logging`
- Windows path'leri icin `pathlib.Path`
- Turkce degisken/fonksiyon adlari (ASCII: `sikilastir`, `kayit_olustur`)
- Her sinifin `__main__` test blogu
- Motor entegrasyonu icin `motor_kaydet()` veya dogrudan cagri fonksiyonu

## Adim 2: motor.py'ye Ekle

**A. TOOLSET_GRUPLARI'na ekle:**
```python
"grup_adi": {"ARAC1", "ARAC2", ...},
```

**B. _DURUM_MESAJLARI'na ekle:**
```python
"ARAC_ADI": "Durum mesaji...",
```

**C. calistir() metoduna erken kontrol ekle** (ToolRegistry/PluginManager oncesi):
```python
if arac in ("ARAC1", "ARAC2", ...):
    try:
        from yeni_modul import Sinif1, Sinif2
        if not hasattr(self, "_ornek"):
            self._ornek = Sinif1()
        if arac == "ARAC1":
            return self._ornek.metod(params)
    except Exception as e:
        return f"[Hata]: yeni_modul: {e}"
```

**ONEMLI:** Erken kontrol ToolRegistry ve PluginManager'dan ONCE eklenmeli, yoksa Hermes araclari intercept eder.

## Adim 3: sistem_talimati.py'yi Guncelle

**A. ARAC SECIM REHBERI bolumune ekle:**
```
  - Kisa aciklama -> ARAC_ADI
```

**B. KULLANILABILIR ARACLAR bolumune detayli tanim ekle:**
```
|ARAC_ADI("parametre")
  Aciklama...
  Ornek: ARAC_ADI("...")
```

## Adim 4: Test

```bash
python -m py_compile motor.py yeni_modul.py sistem_talimati.py
python -c "from motor import Motor; m = Motor(); print(m.calistir('ARAC_ADI', 'test'))"
```

## Ornek: hata_cozucu.py (Error Watchdog + Cozum)

- `HataWatchdog` — Ekran OCR ile hata tespiti (threading.Event ile guvenli)
- `HataKoduUretici` — `HATA-0001` formatli kod + `.ReYMeN/hata_kodlari/` .md kayit
- `TerminalHataParser` — PowerShell/cmd ciktisindan hata ayiklama (regex)
- `CozumUygulayici` — Claude'dan gelen cozumu patch olarak uygula
- Dosya: `hata_cozucu.py`
- 5 arac: `HATA_WATCH_BASLAT`, `HATA_WATCH_DURDUR`, `HATA_KOD_AL`, `TERMINAL_HATA_PARSE`, `COZUM_UYGULA`

## Ornek: tor_otomasyonu.py (Tor Browser Web Automation)

- `TorBrowserKontrol` — Tor Browser bul/baslat/kapat (Selenium + geckodriver)
- `FormDoldurucu` — DOM'da alanlari bulup doldur (Turkce alan adi destegi)
- [nisan_yakala.py](references/nisan_yakala.md) — Gorsel sablon yakalama araci (calistir: `python nisan_yakala.py`)
- `OtomasyonAkislari` — Login, kayit, siparis akislari
- Timeout: sayfa 45sn, form 30sn (Tor yuksek gecikmeli)
- UYARI: Tor cikis dugumleri Cloudflare/WAF captcha zorlayabilir
- Dosya: `tor_otomasyonu.py`
- 6 arac: `TOR_AC`, `TOR_KAPAT`, `TOR_FORM_DOLDUR`, `TOR_LOGIN`, `TOR_KAYIT`, `TOR_SIPARIS`

## HITL (Human-in-the-Loop) Pattern

Riskli araclar (kayit, siparis, odeme) icin `insan_arayuzu.onay_iste()` ile onay zorunludur:

```python
if arac in ("TOR_KAYIT", "TOR_SIPARIS"):
    try:
        from insan_arayuzu import onay_iste
        izin = onay_iste(arac, "Riskli islem. Onayliyor musun?")
        if not izin:
            return f"[{arac}] REDDEDILDI: Kullanici onay vermedi."
    except ImportError:
        logger.warning("[Modul] insan_arayuzu bulunamadi, onay atlandi.")
    # ... isleme devam
```

- Her zaman `try/except ImportError` ile sarmala (insan_arayuzu yoksa sessizce atla)
- Onay mesaji Turkce ve net olmali
- REDDEDILDI durumu kullaniciya acikca bildirilmeli

## 3 Asamali OCR Fallback (NisanBulucu)

Form doldurma basarisiz oldugunda DOM -> Gorsel Sablon -> Metin OCR hiyerarsisi:

**Asama 1:** Selenium DOM find_element (name, id, placeholder, XPath)
**Asama 2:** OpenCV template matching (`.ReYMeN/nisanlar/*.png`)
**Asama 3:** pytesseract metin OCR

Dosya: `araclar_nisan.py`
Sinif: `NisanBulucu`
On tanimli DOM lokatorler: giris_buton, kayit_buton, captcha_kutu, onay_kutusu, ad_alani, soyad_alani, eposta_alani, sifre_alani, adres_alani, telefon_alani

Sablon yakalama araci: `nisan_yakala.py` (ENTER'a basinca fare altindaki UI elemanini 80x80 kirpar)

```python
# motor.py icinde kullanim
from araclar_nisan import NisanBulucu
nisan = NisanBulucu()
sonuc = nisan.bul("giris_buton", driver=tor_driver, metin_alternatif="Giris Yap")
# -> {"asama": 1|2|3, "x": int, "y": int, "guven": float}
```

## Global Singleton Pattern

Tor gibi tek instance gerektiren moduller icin global degisken pattern'i:

```python
# tor_otomasyonu.py
_aktif_tor: Optional[TorBrowserKontrol] = None
_aktif_akislar: Optional[OtomasyonAkislari] = None

def tor_baslat() -> str:
    global _aktif_tor, _aktif_akislar
    _aktif_tor = TorBrowserKontrol()
    _aktif_tor.baslat()
    _aktif_akislar = OtomasyonAkislari(_aktif_tor)
    return "[Tor] Browser baslatildi."
```

motor.py'de:
```python
from tor_otomasyonu import _aktif_tor, _aktif_akislar, tor_baslat, tor_kapat
```

## Pitfalls

- **Sonsuz recursion**: `_orijinal_calistir` uzerinden cagri yapma. Dogrudan class'lari cagir, monkey-patch kullanma.
- **ToolRegistry intercept**: Yeni araclari `calistir()`'in en basinda, Registry/Plugin kontrollerinden ONCE ele al.
- **Regex escape**: PowerShell ciktisindaki `+` karakteri regex'te `\\\\+` ile escape edilmeli, yoksa `re.error: nothing to repeat`.
- **Tor timeouts**: Standart 10sn yetmez. Sayfa yukleme 30-45sn, form 30sn olmali.
- **Selenium import**: Selenium yoksa tum Tor araclari `"Selenium yuklu degil"` dondurmeli, crash degil.
- **Dogrudan entegrasyon**: Dosyayi yazmak yetmez, ENTEGRE etmek gerek. 4 nokta: TOOLSET + durum mesaji + calistir erken kontrol + sistem_talimati.
- **`__main__` test blogu**: Her yeni modulun sonunda `if __name__ == "__main__":` ile calistirilabilir test blogu olmali. Boylece `python modul.py` ile bagimsiz dogrulama yapilabilir. test blogu olmadan modulu "tamam" sayma.
- **HITL atlama**: Insan_arayuzu import edilemezse sessizce atla, crash verme. Logger.warning yeterli.
- **Tor Browser yolu**: Windows'ta `C:\\Users\\{kullanici}\\Desktop\\Tor Browser\\Browser\\firefox.exe` ve `Masaüstü` varyanti ayr ayri kontrol edilmeli.
- **Nisan sablonu cozunurlugu**: Sablonlar Tor Browser'in letterboxing ozelligi ile ayni cozunurlukte alinmali, yoksa OpenCV eslesme basarisiz olur.
