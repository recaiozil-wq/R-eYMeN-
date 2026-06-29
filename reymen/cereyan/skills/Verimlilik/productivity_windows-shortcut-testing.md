---
name: windows-shortcut-testing
description: "Windows klavye kýsayolu otomasyon testi: pyautogui ile sistem seviyesi Win kombinasyonlarýný test etme, ekran görüntüsü doðrulama, hash tabanlı benzersizlik kontrolü ve klasik test döngüsü. Hem kullanýcýnýn 134 testli yolculuðu hem de gelecekteki benzer otomasyonlar için kalýcý kurallar içerir."
title: "Windows Shortcut Testing"
tags: [windows, keyboard, shortcuts, testing, automation, pyautogui, screenshot, hash-validation]
category: productivity
audience: user
version: 1.0.0
---


> **Kategori:** productivity

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Windows klavye kýsayolu otomasyon testi: pyautogui ile sistem seviyesi Win kombinasyonlarýný test etme, ekran görüntüsü doðrulama, hash tabanlı benzersizlik kontrolü ve klasik test döngüsü. Hem kullanýcýnýn 134 testli yolculuðu hem de gelecekteki benzer otomasyonlar için kalýcý kurallar içerir. |
| **Nerede?** | productivity/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Windows Klavye Kýsayolu Test Otomasyonu

## Ne Zaman Kullanýlýr

- Windows sistem kýsayollarýný Python + pyautogui ile doðrulamak gerektiðinde
- Sistem seviyesi Win kombinasyonlarýnýn (Win+Ctrl, Win+Shift, Win+Tab, Win+D vb.) çalýþtýðýný kanýtlamak gerektiðinde
- Testlerin tekrar çalýþtýrýlabilir, benzersiz ekran görüntüleri üretecek þekilde ayarlanmasý gerektiðinde
- Hash tabaný doðrulama ile testlerin güvenilirliðini artýrmak gerektiðinde

## Ortam Seviyesi Kural

**Çýktý dizini OneDrive-senkronize Obsidian Vault altýnda OLMAZ.**
OneDrive gecikmeleri/senkronizasyon çakýþmalarý dosya yazma/görsel doðrulamalarýn bozulmasýna neden olur.
Ýzin verilen çýktý örnekleri:
- `C:\Users\<kullanýcý>\hermes_tests\test_<numara>\`
- `C:\Users\<kullanýcý>\AppData\Local\hermes\test_outputs\`

## Çýktý Dizini Garantisi (Obligatory)

Her test execution script'in baþýnda þu blok olmalý:

```python
import os
output_dir = r'C:\Users\marko\hermes_tests\test_135'
os.makedirs(output_dir, exist_ok=True)
```

Klasör yoksa oluþturulur, varsa sorunsuz devam edilir.

## Görsel Doðrulama Protokolü

1. **Ekran görüntüsü zorunlu:** Her test çalýþtýktan sonra `pyautogui.screenshot()` ile PNG kaydet.
2. **Bekleme süresi:** Her kýsayol tetiklemesinden sonra en az **0.5 saniye** bekle.
3. **Kontrol sýrasý:** Tetikle → bekle → ekran görüntüsü al (eskisinden önce ekran görüntüsü alýnýyorsa geçersizdir).
4. **Hash kontrolü:** Kaydedilen her PNG'nin MD5 hash'ini hesapla. Benzersiz hash'ler testi geçer; ayný hash baþka bir test ile ayný ekraný üretmiþ demektir.
5. **Doðrulanamaz iþaretleme:** Bazý sistem kýsayollarý ekran görüntüsüyle doðrulanamaz (ör. sanal masaüstü deðiþimi). Bunlarý 'baþarýlý' olarak iþaretle ama durumu **"ekran görüntüsüyle doðrulanamaz"** olarak belirt. Baþarýsýzlýk olarak deðil, doðrulama metodu sýnýrý olarak kaydet.

## Win Kombinasyonlarý Ýçin Kritik Kural

`pyautogui.hotkey()` **Win + X** gibi sistem seviyesi kýsayollarý için UYGUN DEÐÝLDÝR.
Nedeni: `hotkey()` tüm tuþlarý çok hýzlý serbest býrakýr; sistem kýsayolu kaydedilmez.

**Doðru yöntem — MANUEL keyDown/press/keyUp:**

```python
from pyautogui import keyDown, press, keyUp

def press_win_combo(win_key='winleft', combo_keys=None):
    if combo_keys is None:
        combo_keys = []
    keyDown(win_key)
    for k in combo_keys:
        press(k)
    keyUp(win_key)
```

**Kullaným örnekleri:**

- Win + Ctrl + Sol: `press_win_combo('winleft', ['ctrl', 'left'])`
- Win + Shift + S: `press_win_combo('winleft', ['shift', 's'])`
- Win + D: `press_win_combo('winleft', ['d'])`
- Win + Tab: `press_win_combo('winleft', ['tab'])`
- Win + E (Dosya Gezgini): `press_win_combo('winleft', ['e'])`
- Win + V (Pano geçmiþi): `press_win_combo('winleft', ['v'])`

**Ýzin verilen tek istisna:** Yalnýzca Win + Sol/Sað/Yukarý/Aþaðý pencere snap tuþlarý için manuel yöntem zorunlu deðildir ama güvenilirliði artýrmak için yine manuel kullanýlabilir.

## Test Tanýmý Formatý

Her test kaydedilirken þu alanlarý içeren kayýt tut:

```python
{
  "test_id": "test_071",
  "shortcut": "win+ctrl+left",
  "method": "manual",
  "status": "verified",          # veya "ekran görüntüsüyle doğrulanamaz"
  "hash": "c692521a3f50b443551f5dcadf72b210",
  "screenshot": "C:\\Users\\marko\\hermes_tests\\test_135\\test_071.png",
  "note": ""
}
```

## Doðrulama Tablosu Ýçin Format

Geçmiþ test sonuçlarýný kullanýcýya þu sütunlarla sun:

| Test No | Kýsayol | Hash | Durum |
|---------|---------|------|-------|
| 071 | Win + Ctrl + ← | c6925... | Doðrulandý |
| 072 | Win + Ctrl + → | 54076... | Doðrulandý |
| 084 | Win + ... | — | Ekran görüntüsüyle doðrulanamaz |

**Not:** Kullanýcý yalnýzca bu tabloyu ister; açýklama veya geçmiþ anlatma yapma.

## Beþerli Doðrulama (Cross-Verification)

Kullanýcýnýn gereksinimi varsa:
- **Script çýktýsý** (`FINAL_COUNT): ...` ) ile **baðýmsýz doðrulama** (`VERIFY_COUNT`) birbirini tutmalý.
- Klasördeki dosya sayýsý ile script tarafýndan raporlanan test sayýsý örtüþmeli.

## Kaynaklar

- `references/manual-key-method.md` — Manuel keyDown/press/keyUp kullaným örnekleri ve yaygýn hatalar.
- `references/output-directory-guarantee.md` — Çýktý dizini oluþturma ve OneDrive uzaklaþtýrma rehberi.
- `references/screenshot-hash-validation.md` — Hash hesaplama ve benzersizlik doðrulama adýmlarý.
- `references/shortcut-verification-limits.md` — Ekran görüntüsüyle doðrulanamaz Windows kýsayollarý listesi.
