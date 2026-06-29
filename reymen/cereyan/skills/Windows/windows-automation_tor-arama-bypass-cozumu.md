
> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Windows Automation_Tor Arama Bypass Cozumu |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: tor-arama-bypass-cozumu
description: "Tamamlayici skill - Tor bypass teknikleri. Ana skil: tor-browser-arama"
title: "Tor Arama Bypass Cozumu"
version: 1.0.0
author: hermes
platforms: [windows]

audience: user
tags: [automation, tor, windows]
category: windows-automation---

# Tor Arama Bypass Çözümü

> **Bu skill `tor-browser-arama` skill'ini tamamlar.** Ana Tor iş akışı ve temel komutlar için önce oraya bak.
>
> **Fazlalık notu:** Bu skill ile `tor-browser-arama` arasında önemli örtüşme var. İkisi de Tor blok aşma tekniklerini kapsar. Konsolidasyon önerilir.

## Problem
Tor çıkış düğümleri çoğu arama motoru tarafından bloklanıyor:
- Google → CAPTCHA
- DuckDuckGo → Tor blok mesajı
- Bing US → CAPTCHA
- Yandex → Verification
- Çoğu ülke sitesi → SOCKS hatası veya blok

## Çalışan Yöntemler

### 1. arXiv API (EN GÜVENİLİR)
```python
import requests
proxies = {'https': 'socks5h://127.0.0.1:9150', 'http': 'socks5h://127.0.0.1:9150'}
r = requests.get('http://export.arxiv.org/api/query?search_query=all:bluetooth+AND+all:sniffing&start=0&max_results=5',
                 proxies=proxies, timeout=20)
# XML/Atom formatında sonuç döner
```

### 2. Tor Browser DuckDuckGo Lite
Browser aracı ile `https://lite.duckduckgo.com/lite/` adresine git, sorgu yaz, sonuçları oku.

### 3. Direkt Site Erişimi
- GitHub RAW: `https://raw.githubusercontent.com/...`
- USENIX: `https://www.usenix.org/...`
- IEEE: `https://ieeexplore.ieee.org/...` (özetler)

### 4. Bing Bölgesel (kısmen çalışır)
- JP: `https://www.bing.com/search?q={q}&cc=JP&setlang=ja`
- KR: `https://www.bing.com/search?q={q}&cc=KR&setlang=ko`
- RU: `https://www.bing.com/search?q={q}&cc=RU&setlang=ru`
- IN: `https://www.bing.com/search?q={q}&cc=IN&setlang=en-IN`

## Scriptler

### tor_multi_search.py (30+ kaynak)
```bash
"/c/Users/marko/AppData/Local/Python/pythoncore-3.14-64/python.exe" "C:\Users\marko\Desktop\tor_multi_search.py" "sorgu buraya"
```
- DuckDuckGo Lite, Bing (US/CN/JP/KR/RU/IN), Yandex, Startpage, Mojeek, Qwant, SearX, Swisscows, Brave
- Rus siteleri (habr, xakep), Çin (freebuf, kaspersky), Japon, Kore, Hint
- Akademik (arXiv, Semantic Scholar)
- Güvenlik (PacketStorm, CXSecurity, Exploit-DB)
- Otomatik rapor kaydeder

### tor_hizli_arama.py (hedefli)
```bash
"/c/Users/marko/AppData/Local/Python/pythoncore-3.14-64/python.exe" "C:\Users\marko\Desktop\tor_hizli_arama.py" "sorgu"
```
- Daha hızlı, sadece çalışma ihtimali yüksek kaynaklar

## Önemli: Doğru Python Kullan
```bash
# Hermes varsayılan python (3.11) → PySocks yok!
python3 -c "..."  # HATA: Missing dependencies

# Python 3.14 → PySocks VAR
"/c/Users/marko/AppData/Local/Python/pythoncore-3.14-64/python.exe" -c "..."
```

## Tor Kimlik Döndürme
```python
import pyautogui
pyautogui.hotkey('ctrl', 'shift', 'l')  # New Identity
time.sleep(1)
pyautogui.press('enter')  # Onayla
time.sleep(5)
```

## Ülke Spesifik Çözümler

Detaylı referanslar: `references/` klasöründe.

| Ülke | Durum | Çözüm | Referans |
|---|---|---|---|
| 🇷🇺 Rusya | CAPTCHA blok | **RSS Feed** — habr.com/en/rss/search/ | `references/rusya-habr-rss.md` |
| 🇨🇳 Çin | SOCKS blok | **Kaspersky CN direkt**, diğerleri aşılamaz | `references/cin-siteleri.md` |
| 🇰🇷 Kore | SOCKS blok | **Bing KR** / **Naver** | `references/kore-siteleri.md` |
| 🇮🇳 Hindistan | Karışık | **GBHackers** / **Bing IN** | `references/hindistan-siteleri.md` |

### 🇷🇺 Rusya (habr.com CAPTCHA)
```python
# RSS kullan → CAPTCHA yok
r = requests.get(f'https://habr.com/en/rss/search/?q={q}', proxies=proxies, headers=headers)
# 20+ sonuç, BT güvenlik makaleleri dahil
```
Skill: `tor-rusya-siteleri-bypass`

### 🇨🇳 Çin (SOCKS blok)
- Kaspersky CN: `https://www.kaspersky.com.cn/blog/?s={q}` → direkt çalışır
- FreeBuf/CSDN/AnQuanKe → SOCKS bloklu (aşılamaz, CDN firewall)
Skill: `tor-cin-siteleri-bypass`

### 🇰🇷 Kore (SOCKS blok)
- Bing KR: `https://www.bing.com/search?q={q}&cc=KR` → çalışır
- Naver: `https://search.naver.com/search.naver?query={q}` → çalışır
- BoanNews/DailySec → SOCKS bloklu
Skill: `tor-kore-siteleri-bypass`

### 🇮🇳 Hindistan
- GBHackers: `https://gbhackers.com/?s={q}` → direkt çalışır (193KB)
- Bing IN: `https://www.bing.com/search?q={q}&cc=IN` → çalışır
- TheHackerNews → Cloudflare 403
Skill: `tor-hindistan-siteleri-bypass`

## Kaynak
Scriptler: `C:\Users\marko\Desktop\tor_multi_search.py` ve `tor_hizli_arama.py`
