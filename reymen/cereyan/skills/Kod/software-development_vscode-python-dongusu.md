---
name: vscode-python-dongusu
description: VS Code + Python zorunlu akis dongusu. Kod yaz, terminalde calistir, HAM ciktiyi goster. Asla atlanamaz.
title: "VS Code Python Dongusu"
category: software-development
audience: contributor
tags: [coding, development, python]
triggers: [kod yaz, python, vs code, terminal, calistir, ran]
---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | VS Code + Python zorunlu akis dongusu. Kod yaz, terminalde calistir, HAM ciktiyi goster. Asla atlanamaz. |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# VS Code + Python Zorunlu Akis Dongusu

**Bu dongu HER SEFERINDE uygulanir. Atlanamaz, kisa yola gidilemez.**

## Adim Adim

### 1. VS Code'u ac
```bash
code "/c/Users/marko/Desktop/test-python"
```

### 2. Klasoru dogrula
VS Code sol panelde `test-python` klasoru altindaki dosyalar gorunmeli.

### 3. Kodu yaz
- `write_file` ile kodu `C:\Users\marko\Desktop\test-python\` altina yaz
- Dosya adi aciklayici olsun (ornek: `wifi_tara.py`)

### 4. Terminal'de calistir
```bash
cd /c/Users/marko/Desktop/test-python && python dosya_adi.py
```

### 5. CIKTIYI HAM OLARAK GÖSTER (ZORUNLU — ATLANAMAZ KURAL)
**Kuralin adi: VERI BUTUNLUGU. Ihlal edilirse kullanici guvenini kaybederiz.**
- Terminal ciktisini **oldugu gibi, harfiyen, hic degistirmeden** kullaniciya gonder
- Kopyala-yapistir yap, kendi cumlenle ifade etme
- **Degistirme, filtreleme, sayi azaltma, yorum katma, "sunu elersek" deme KESINLIKLE YASAK**
- Ham veride 5 IP varsa "5 IP" de. "2 cihaz" deme. Veriyi kucultme.
- "Benim yorumum:" basligiyla ANCAK ham veriden sonra ayri bir bolum ekleyebilirsin

### 6. Ekran goruntusu al (istege bagli)
```powershell
powershell -ExecutionPolicy Bypass -Command "& 'C:\Users\marko\AppData\Local\Python\PythonCore-3.14-64\python.exe' 'C:\Users\marko\AppData\Local\hermes\scripts\screenshot_v2.py'"
```

## KOD YAZMA KURALLARI
- Kod her zaman `C:\Users\marko\Desktop\test-python\` altinda olacak
- Kod yazilmadan once amacini kullaniciya sor
- Kod yaz, terminalde calistir, ciktiyi goster

## YASAKLAR
- Terminal ciktisini filtrelemek
- "Sunu elersek" gibi varsayimla konusmak
- VS Code acmadan direkt terminalde calistirmak
- Ciktiyi oldugundan farkli gostermek
