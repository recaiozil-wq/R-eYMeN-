---
name: screen-vision-analiz
description: "'Use when user asks about screen content or wants visual analysis. PRIMARY: Tesseract OCR (Ollama removed). Backup: LM Studio vision model.'"
title: "Screen Vision Analiz"
tags: [screen, vision, screenshot, ocr, tesseract, gorsel, ekran, analiz]
category: windows-automation
audience: user
related_skills: [tam-sistem-yetkisi, tor-browser-arama]
---

> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | 'Use when user asks about screen content or wants visual analysis. PRIMARY: Tesseract OCR (Ollama removed). Backup: LM Studio vision model.' |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Ekran Görüntüsü + OCR/Metin Analizi

## Overview

Kullanıcı "ekranda ne var", "ekranı gör", "screenshot al ve analiz et" dediğinde
Hermes şu adımları uygular:

1. `mss` ile ekran görüntüsü alır (Python 3.14, `screenshot_v2.py`)
2. Tesseract OCR ile metne çevirir
3. OCR metnini mevcut model ile analiz eder
4. Sonucu kullanıcıya iletir

**ÖNEMLİ:** Ollama KALDIRILMISTIR. llava-llama3 vision modeli mevcut degil.
Vision analizi icin Tesseract OCR kullanilir. LM Studio local model olarak kullanilabilir.

## When to Use

- "Ekranda ne var?" sorusu
- "Ekranı gör ve anlat"
- "Ne görüyorsun?"
- "Screenshot al, analiz et"
- Herhangi bir görsel bağlam gerektiğinde
- Vision desteklemeyen modelle ekran okuma (DeepSeek V4 Flash)

Don't use for: Gizli bilgiler içeren ekranlarda (şifre, token vs.) — kullanıcıyı uyar.

---

## Hizli Komut (Sık Kullanılan)

```bash
# 1. Screenshot al
powershell -ExecutionPolicy Bypass -Command "& 'C:\Users\marko\AppData\Local\Python\PythonCore-3.14-64\python.exe' 'C:\Users\marko\AppData\Local\hermes\scripts\screenshot_v2.py'"

# 2. OCR ile oku (tum ekran)
powershell -ExecutionPolicy Bypass -Command "& 'C:\Users\marko\AppData\Local\Python\PythonCore-3.14-64\python.exe' -c \"from PIL import Image; import subprocess; from mss import mss; import os; tess=r'C:\Program Files\Tesseract-OCR\tesseract.exe'; img=Image.open(r'C:\Users\marko\AppData\Local\hermes\scripts\screen.png'); w,h=img.size; crop=img.crop((0,80,int(w*0.75),h-80)); crop.save(r'C:\Users\marko\AppData\Local\hermes\scripts\screen_ocr.png'); r=subprocess.run([tess, r'C:\Users\marko\AppData\Local\hermes\scripts\screen_ocr.png', 'stdout', '-l', 'eng', '--psm', '4'], capture_output=True, text=True, timeout=30); print(r.stdout[:3000])\""
```

---

## Teknik Uygulama — BIRINCI YONTEM: Tesseract OCR (Önerilen)

Aktif model vision desteklemiyorsa (DeepSeek V4 Flash gibi — `unknown variant 'image_url'` hatası), **Tesseract OCR + Metin Analizi** kullan.

## Ön koşul: Tesseract kurulu

```bash
"C:\Program Files\Tesseract-OCR\tesseract.exe" --version
# → tesseract v5.5.0+
```

## İş Akışı (Screenshot → OCR → Analiz)

### 1. Ekran görüntüsü al (Python 3.14 + mss)

```bash
powershell -ExecutionPolicy Bypass -Command "& 'C:\Users\marko\AppData\Local\Python\PythonCore-3.14-64\python.exe' 'C:\Users\marko\AppData\Local\hermes\scripts\screenshot_v2.py'"
```
Cikti: `OK size=... path=C:\Users\marko\AppData\Local\hermes\scripts\screen.png`

### 2. Hedef pencere alanini kırp + OCR

Tor Browser icin kanitlanmis crop (1920x1200 ekran):
```python
from PIL import Image
import subprocess
from mss import mss

with mss() as sct:
    monitor = sct.monitors[1]
    sct_img = sct.grab(monitor)
    img = Image.frombytes('RGB', sct_img.size, sct_img.rgb)
    w, h = img.size
    # Crop: browser alani (ust 80px toolbar, sol 75% icerik)
    crop = img.crop((0, 80, int(w*0.75), h-80))
    crop.save(r'C:\Users\marko\AppData\Local\hermes\scripts\screen_ocr.png')

tess = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
result = subprocess.run(
    [tess, r'C:\Users\marko\AppData\Local\hermes\scripts\screen_ocr.png',
     'stdout', '-l', 'eng', '--psm', '4'],
    capture_output=True, text=True, timeout=30
)
print(result.stdout[:3000])
```

**Neden `--psm 4`:** GitHub/liste sayfalari icin ideal (tek sutun).
**Crop mantigi:** Sol %75 = repo/liste icerigi, sag %25 = sidebar (gereksiz).

### 3. OCR metnini analiz et

OCR ciktisi mevcut model (DeepSeek V4 Flash) ile okunur:
- GitHub repolari / trending listesi
- Hata mesajlari
- Pencere basliklari

## İkinci Yöntem: Python Inline (Hızlı Test)

```bash
cd /c/Users/marko && "C:\Users\marko\AppData\Local\Python\PythonCore-3.14-64\python.exe" -c "
from PIL import Image; import subprocess; from mss import mss
with mss() as sct:
    img = Image.frombytes('RGB', sct.grab(sct.monitors[1]).size, sct.grab(sct.monitors[1]).rgb)
    img.save(r'C:\Users\marko\AppData\Local\hermes\scripts\screen_ocr.png')
tess = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
r = subprocess.run([tess, r'C:\Users\marko\AppData\Local\hermes\scripts\screen_ocr.png', 'stdout', '-l', 'eng', '--psm', '4'], capture_output=True, text=True, timeout=30)
print(r.stdout[:2000])
"
```

## Üçüncü Yöntem: Vision Desteği Olan Model (LM Studio)

Eger model vision destekliyorsa (veya gecici olarak degistirilirse):
```python
import requests, base64
with open(r'C:\path\to\screen.png', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()
resp = requests.post('http://localhost:1234/v1/chat/completions', json={
    'model': 'dolphin-8b',
    'messages': [{'role': 'user', 'content': [
        {'type': 'text', 'text': 'Ekranda ne var?'},
        {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{b64}'}}
    ]}]
}, timeout=60)
print(resp.json()['choices'][0]['message']['content'])
```

---

## Common Pitfalls

1. **Screenshot icin Python 3.14 kullan** — Hermes venv'inda (Python 3.11) `mss` paketi yok. Daima `C:\Users\marko\AppData\Local\Python\PythonCore-3.14-64\python.exe` kullan.
2. **`screenshot_v2.py` oncelikli** — `screenshot.ps1` bazen alt kismi keser. `screenshot_v2.py` (mss, monitors[1]) daha guvenilir.
3. **OCR karanlik temada karisik okur** — GitHub koyu temasiyla Tesseract bazen bozuk karakter verir. `ImageOps.invert()` dene veya parlaklik artir.
4. **Crop alani dogru ayarla** — 1920x1200 ekranda Tor Browser icin `(0, 80, 1440, 1120)` ise yaradi. Farkli cozunurlukte ayarla.
5. **`--psm 4` yerine `--psm 6`** — Blog/yazi sayfalari icin `--psm 6` (blok) daha iyi. Liste sayfalari icin `--psm 4` (tek sutun).
6. **Tesseract cok yavas** — Cok buyuk resimde once boyut kucult: `img.resize((img.width//2, img.height//2))`
7. **Ekran kilitliyse screenshot bos gelir** — fiziksel oturum acik olmali.
8. **OCR metni 3000 karakterle sinirla** — Tesseract tum ekrani okur, cogu gereksiz. `[:3000]` yeterli.
9. **Vision_analyze hatasi → direkt OCR'a gec** — DeepSeek V4 Flash `'unknown variant image_url'` hatasi verirse tekrar deneme, direkt OCR'a gec.
10. **Ollama kaldirildi** — `llava-llama3` mevcut degil. `hermestor.py connect` gibi llava gerektiren komutlar calismaz. Cozum: `hermesapprove.py scan` veya manuel tikla.

## Reference Files

| Dosya | Icerik |
|-------|--------|
| `references/3-asamali-nisanbulucu.md` | 3 asamali hiyerarsik ekran hedef bulma (DOM → Sablon → OCR) |

## Verification Checklist

- [ ] Tesseract kurulu: `"C:\Program Files\Tesseract-OCR\tesseract.exe" --version`
- [ ] Python 3.14 + mss: `...\PythonCore-3.14-64\python.exe -c "from mss import mss; print('OK')"`
- [ ] Screenshot alinabiliyor: `screenshot_v2.py` calisiyor
- [ ] OCR metin donduruyor: Tesseract `--psm 4` ile calisiyor
- [ ] Crop alani dogru: Tor Browser icerigi gorunuyor
- [ ] OCR sonucu okunabiliyor: mevcut model metni anlayabiliyor
