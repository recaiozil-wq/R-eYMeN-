---
name: vscode-otomasyon
title: "VS Code Otomasyon"
tags: [coding, development]
description: Use when writing, running, or debugging Python code in VS Code. Hermes opens VS Code, writes code, runs it, reads output/errors, asks AI for fixes, and retries automatically (try-fix loop). Use for any coding task that needs real execution and error correction.
version: 1.0.0
author: marko
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [vscode, python, kod, calistir, hata, duzelt, otomasyon, loop, debug, try-fix]
audience: contributor
related_skills: [screen-vision-analiz, gorsel-onaylama, mouse-klavye-ctypes, tor-browser-arama]
---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Use when writing, running, or debugging Python code in VS Code. Hermes opens VS Code, writes code, runs it, reads output/errors, asks AI for fixes, and retries automatically (try-fix loop). Use for any coding task that needs real execution and error correction. |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# VS Code Otomasyonu — Kullanıcı Gibi Kod Yaz, Calistir, Duzelt

## !!! KRITIK KURAL — ASLA IHLAL ETME !!!

**"kopyala", "kopyala ben yapistiririm", "bana gonder", "sana gonder" dendiginde:
METNI BURADA (HERMES CHAT'TE) GOSTER. ASLA VS CODE'A/CLAUDE CODE'A GONDERME.
Kullanici "kesin mir culadue gondermeyecegim" diyerek bunu netlestirdi.**

Bu kural 17 Haziran 2026'da 2 KEZ ihlal edildi ve kullanici sinirlendi.
Tekrar ihlal = kullanici guveni kaybi.

Detay: references/kopyala-uyari.md
Not: "VS Code'a yaz", "Claude terminaline yaz" -> vscode_yaz.bat (bunlar farkli)

---

## Overview

Hermes, VS Code'u bir kullanıcı gibi kullanır:
1. Yeni dosya oluşturur
2. Kod yazar (AI'dan alınan veya kendi yazdığı)
3. Çalıştırır, çıktıyı okur
4. Hata varsa AI'dan düzeltme ister
5. Çalışana kadar tekrar dener (dene-yanıl-düzelt döngüsü)

**Script:** `C:\Users\marko\hermesvsode.py`
**Çalışma klasörü:** `C:\Users\marko\hermes_projects\`

## When to Use

- "Bu kodu dene/çalıştır"
- "VS Code'da aç ve test et"
- "Kodu düzelt ve çalıştır"
- AI'dan alınan Python kodunu test etmek için
- Hata mesajını otomatik düzeltmek için
- "Dene-yanıl-düzelt" gerektiğinde

Don't use for: Sistem komutları, terminal-only işlemler.

## NE ZAMAN VS CODE'A YAZ, NE ZAMAN BURADA GÖSTER

**vscode_yaz.bat kullan (VS Code'a yaz):**
- "VS Code'a yaz", "Claude terminaline yaz", "agent'a yaz", "imlec getir" gibi AÇIK hedef belirtildiğinde
- Kullanıcı "vscode_yaz.bat" veya "vscode_ctrl.py" dediğinde
- Kullanıcı "Culaude yazdır" gibi VS Code/Claude Code işlemi istediğinde

**Burada (Hermes chat) göster:**
- "kopyala", "gönder", "sana gönder", "bana gönder" → metni burada göster, kullanıcı kopyalasın
- "kopyala ben yapıştırırım" → aynı, burada göster
- Hedef belirtilmeyen tüm durumlar → burada göster

---

## Temel Komutlar

```bash
# VS Code ac (hermes_projects klasorunde)
python C:\Users\marko\hermesvsode.py open

# Yeni dosya olustur
python C:\Users\marko\hermesvsode.py new "benim_kodum.py"

# Dosyaya kod yaz
python C:\Users\marko\hermesvsode.py write "benim_kodum.py" "print('Merhaba')"

# Calistir (ciktiyi oku)
python C:\Users\marko\hermesvsode.py run "benim_kodum.py"

# Kodu yaz + calistir (tek adim)
python C:\Users\marko\hermesvsode.py paste_and_run "test.py" "print(1+1)"

# DENE-YANIL-DUZELT DONGUSU (en onemli!)
python C:\Users\marko\hermesvsode.py loop "benim_kodum.py" 5

# Ekran analizi (hata gormek icin)
python C:\Users\marko\hermesvsode.py screenshot "VS Code'da hata mesaji var mi?"

# VS Code'u one getir
python C:\Users\marko\hermesvsode.py focus
```

---

## Tam Is Akisi: AI'dan Kod Al → Test Et → Duzelt

```
1. AI'dan (DeepSeek/Ollama) Python kodu al
         ↓
2. Dosyaya yaz:
   python hermesvsode.py write "test.py" "<kod>"
         ↓
3. Dene-yanil-duzelt dongusu basla:
   python hermesvsode.py loop "test.py" 5
         ↓
4. Otomatik olarak:
   - Calistir → hata varsa AI'a sor → duzelt → tekrar calistir
   - Max 5 tur, calisiyor sa erken cik
         ↓
5. [BASARILI] veya [BASARISIZ] raporu al
```

## Python API (Script Icerisinden)

```python
import sys
sys.path.insert(0, r"C:\Users\marko")
import hermesvsode as vs

# Dosya olustur ve kod yaz
path = vs.new_file("hesaplama.py")
vs.write_code(path, """
def toplam(a, b):
    return a + b

print(toplam(3, 5))
""")

# Calistir
rc, stdout, stderr = vs.run_python(path)
print(f"Sonuc: {stdout}")

# Dene-yanil-duzelt
basarili = vs.try_fix_loop(path, max_turns=5)
```

## Dene-Yanil-Duzelt Dongusu (try_fix_loop)

```
Tur 1: Calistir → SyntaxError (parantez kapanmamis)
  AI: "Eksik parantezi ekle" → Kodu duzelt
Tur 2: Calistir → NameError (yanlis fonksiyon adi)
  AI: "primt → print" → Kodu duzelt
Tur 3: Calistir → [BASARILI] rc=0
```

Gercek test sonucu:
- Kasitli 2 hatali kod verildi
- **2 turda otomatik duzeltildi ve calisti**

## VS Code Klavye Kisayollari (Gorsel Otomasyon Icin)

```python
import hermesvsode as vs

vs.hotkey("ctrl", "s")      # Kaydet
vs.hotkey("ctrl", "grave")  # Terminal ac (Ctrl+`)
vs.hotkey("ctrl", "f5")     # Calistir (debug olmadan)
vs.hotkey("ctrl", "shift", "p")  # Command Palette
vs.hotkey("ctrl", "n")      # Yeni dosya
vs.type_text("python test.py")   # Terminal'e komut yaz
vs.press("enter")
```

## Cikti Okuma ve Kopyalama

```python
import hermesvsode as vs

# Dogrudan subprocess ile (en guvenilir)
rc, stdout, stderr = vs.run_in_terminal('python test.py')
print(stdout)   # Basarili cikti
print(stderr)   # Hata mesaji

# Sonucu clipboard'a kopyala (Windows)
import subprocess
subprocess.run(["clip"], input=stdout.encode(), check=False)
```

## AI ile Hata Analizi

```python
import hermesvsode as vs

# Hata mesajini analiz et
rc, stdout, stderr = vs.run_python("test.py")
if rc != 0:
    analiz = vs.analyze_error(stdout, stderr)
    print("AI Oneri:", analiz)
```

## Dosya Yolu Kuralları

```python
# Calisma klasoru: C:\Users\marko\hermes_projects\
# Dosyalar buraya kaydedilir

WORKSPACE = r"C:\Users\marko\hermes_projects"

# Doğru:
filepath = rf"{WORKSPACE}\benim_kodum.py"

# hermesvsode.py otomatik ekler:
python hermesvsode.py run "benim_kodum.py"
# → C:\Users\marko\hermes_projects\benim_kodum.py
```

## CRITICAL — "kopyala" VS "VS Code'a yaz" KARIŞTIRMA

"kopyala", "kopyala ben yapıştırırım", "bana gönder" → metni burada göster, ASLA VS Code'a gönderme.
Kullanıcı kontrolü kendinde tutmak istiyor. Detay: references/kopyala-uyari.md

## Common Pitfalls

1. **VS Code acik degilse** — `open` komutu ile once ac, 3 saniye bekle.
2. **Kod cok uzunsa write komutu kesilir** — Dosyaya direkt yaz: `write_code()`.
3. **AI hata duzeltemiyor** — Max tur sayisini artir veya farkli model dene.
4. **Cikti Turkce karakter bozuk** — `encoding="utf-8", errors="replace"` kullan.
5. **Loop orijinal kodu bozdu** — `try_fix_loop` basarisizsa orijinal kodu geri yukler.
6. **venv Python kullanilmiyor** — Script otomatik `hermes-ai\venv\Scripts\python.exe` kullanir.

## Verification Checklist

- [ ] `python hermesvsode.py open` VS Code acildi
- [ ] `python hermesvsode.py new "test.py"` dosya olusturuldu
- [ ] `python hermesvsode.py run "test.py"` cikti geldi
- [ ] `python hermesvsode.py loop "test.py" 3` hatali kod duzeltildi
- [ ] `C:\Users\marko\hermes_projects\` klasorunde dosyalar var
