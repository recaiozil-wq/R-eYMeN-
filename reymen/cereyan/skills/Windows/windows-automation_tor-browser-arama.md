---
name: tor-browser-arama
description: "Use when searching for information, browsing the web, or researching any topic. ALWAYS use Tor Browser for ALL web searches — never use regular browser or direct connections. Tor Browser exe is at C:\Users\marko\OneDrive\Desktop\Tor Browser\Browser\firefox.exe and SOCKS5 proxy runs on port 9150."
version: 2.1.0
author: marko
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [tor, browser, search, arama, web, gizlilik, duckduckgo, proxy, socks5, internet]
audience: user
related_skills: [gorsel-onaylama, screen-vision-analiz, mouse-klavye-ctypes]
---


> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Use when searching for information, browsing the web, or researching any topic. ALWAYS use Tor Browser for ALL web searches — never use regular browser or direct connections. Tor Browser exe is at C:\Users\marko\OneDrive\Desktop\Tor Browser\Browser\firefox.exe and SOCKS5 proxy runs on port 9150. |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Tor Browser ile Web Araması

## Overview

Hermes, internette bilgi ararken DAIMA Tor Browser kullanır.
Normal tarayıcı veya doğrudan bağlantı YASAK. Her arama Tor üzerinden yapılır.

**Script:** `C:\Users\marko\hermestor.py`
**Tor Browser:** `C:\Users\marko\OneDrive\Desktop\Tor Browser\Browser\firefox.exe`
**SOCKS5 Proxy:** `socks5h://127.0.0.1:9150`

## When to Use

- Herhangi bir konuda web araması yapılacağında
- "Araştır", "internette bak", "bul", "araştır" denildiğinde
- Güncel bilgi gerektiğinde
- Herhangi bir URL içerik okuma gerektiğinde

KURAL: Web'e bağlanmak gerekiyorsa → Tor kullan. İstisna yok.

---

## Is Akisi (Adim Adim)

### Arama Yaparken:

```
1. Tor proxy aktif mi kontrol et:
   python C:\Users\marko\hermestor.py status

2a. Aktifse → dogrudan arama yap:
   python C:\Users\marko\hermestor.py search "sorgu buraya"

2b. Aktif degilse → Tor'u baslatii:
   python C:\Users\marko\hermestor.py start
   (Ekranda "Connect" butonu cikabilir → otomatik gorsel tikla)

3. Sonuclari al, gerekirse sayfayi oku:
   python C:\Users\marko\hermestor.py proxy "https://example.com"
```

### Ekranda "Connect" Butonu Cikarsa:

```bash
python C:\Users\marko\hermestor.py connect
```
**NOT:** `connect` komutu llava-llama3 (Ollama) gerektirir. Ollama KALDIRILMISTIR. Connect butonu manuel tiklanmali veya `hermesapprove.py` kullanilmali.

Alternatif (gorsel-onaylama):
```bash
python C:\Users\marko\hermesapprove.py scan
# Buton koordinatini bulup tiklar
```

Manuel alternatif: mouse ile Connect butonuna tikla (Tor Browser ortasinda, yaklasik 960, 540).

---

## Komut Referansi

```bash
# Durum kontrol
python C:\Users\marko\hermestor.py status
# Cikti: "Tor proxy: AKTIF (port 9150)"  veya  "KAPALI"

# Tor Browser'i ac ve baglan
python C:\Users\marko\hermestor.py start
# Otomatik proxy hazir olana kadar bekler (max 60s)

# Gorsel "Connect" butonu tikla (ekrana bakar)
python C:\Users\marko\hermestor.py connect

# Web aramasi (DuckDuckGo, Tor uzerinden)
python C:\Users\marko\hermestor.py search "Python ChromaDB kullanimi"

# URL icerigini Tor ile yukle ve oku
python C:\Users\marko\hermestor.py proxy "https://docs.python.org/3/"

# Tor Browser'da URL ac (yeni sekme/pencere)
python C:\Users\marko\hermestor.py open "https://check.torproject.org"
# NOT: `--new-tab` flag'i kullanilmaz. Firefox URL'i direkt alir:
# aciksa yeni sekmede, kapaliysa direkt o sayfada acar (varsayilan sayfa atlanir).

# Gorsel adres cubugu kullanimi
python C:\Users\marko\hermestor.py navigate "https://duckduckgo.com"
```

---

## Python API (Script Icinden)

```python
import sys
sys.path.insert(0, r"C:\Users\marko")
import hermestor as tor

# Durum kontrol
if not tor.tor_running():
    tor.start_tor()

# Arama yap
results = tor.tor_search("Python asyncio ornegi")
for r in results:
    print(r['title'], r['url'])

# Sayfa oku
icerik = tor.tor_get("https://docs.python.org/3/library/asyncio.html")
print(icerik[:1000])

# Gorsel baglanti
tor.visual_connect()
```

---

## Ekran Goruntu Analizi ile Navigasyon

Tor Browser ekranda acikken ve bir sey yapmak gerekiyorsa:

```bash
# 1. Ekrana bak, ne gorunuyor?
#    Vision destekli model varsa:
python C:\\Users\\marko\\hermesapprove.py scan

#    Vision destegi yoksa (DeepSeek V4 Flash gibi):
#    Tesseract OCR ile oku (skill ref: tor-curl-ocr-workflow.md)

# 2. Connect / Baglanti butonu varsa tikla
python C:\\Users\\marko\\hermestor.py connect

# 3. Adres cubuguna git (TERCIH EDILEN)
python C:\\Users\\marko\\hermestor.py navigate "https://duckduckgo.com/?q=sorgu"
#    NOT: navigate, Ctrl+L'den daha guvenilirdir.
#    Ctrl+L bazen sayfadaki DuckDuckGo kutusuna gider, adres cubuguna degil.

# 4. Gerekirse manuel koordinata tikla
python C:\\Users\\marko\\hermesmouse.py click X Y
```

---

## Tor Proxy Ayarlari

| Parametre | Deger |
|-----------|-------|
| Host | 127.0.0.1 |
| Port | 9150 (Tor Browser) |
| Protokol | SOCKS5h (DNS de Tor uzerinden) |
| requests proxies | `{"https": "socks5h://127.0.0.1:9150"}` |

`socks5h://` kullan — `socks5://` degil. `h` harfi DNS'i de Tor'dan gecirmek icin gerekli.

---

## Arama Sonuclari Yorumlama

`tor_search()` su formati doner:
```python
[
  {"title": "Sayfa Basligi", "url": "https://..."},
  ...
]
```

Sayfa icerigi okumak icin ilgili URL'i `tor_get()` ile al.

### 14. Site engelleme — hosts dosyası ile
Kullanıcı "şu siteyi engelle" derse: Windows hosts dosyasına `127.0.0.1 siteadi.com` eklenir. Yönetici yetkisi gerekir. Self-elevating PowerShell scripti ile yap. Engellenen siteleri Obsidian `07-System/Engelli-Siteler.md` notuna kaydet. Detay: `skill_view(name='tor-browser-arama', file_path='references/local-site-blocking.md')`.

## Common Pitfalls

### 1. PENCERE ODAKLAMA + NAVİGASYON (KRİTİK)
Tor Browser işlemleri ŞU SIRAYLA yapılır:
```
1. Kullanıcıya ne yapılacağını SÖYLE (örn: "Şimdi X reposuna gidiyorum")
2. focus_tor.ps1 çalıştır (pencereyi öne getir)
3. 1 sn bekle
4. hermestor.py navigate <URL> çalıştır
5. 4-5 sn bekle (Tor yavaş, kullanıcı ekranda görsün)
6. Gerekirse ekran görüntüsü al + OCR ile kontrol et
```
- ASLA ctypes ile manuel URL yazma — Türkçe Q klavyede `:`, `/`, `?` karakterleri bozulur
- "llava-adres" hatası NORMALDİR — Ollama kaldırıldı, navigate yine de çalışır (Ctrl+L + URL + Enter)
- Hiçbir şekilde `type_string()` veya elle klavye ile URL yazma
- SADECE `hermestor.py navigate <URL>` kullan (klavye düzeninden etkilenmez)
- Alternatif: `curl --socks5-hostname 127.0.0.1:9150` ile API'den veri al (GitHub API, hızlı liste için)

### 2. KULLANICI İZLERKEN GEZİNME
Kullanıcı ekrana bakıyorsa:
- Önce ne yapacağını söyle: "Şimdi X reposuna gidiyorum"
- `focus_tor.ps1`'i HER navigate ÖNCESİ çalıştır
- Her navigate arası 4-5 sn bekle (kullanıcı görsün)
- Navigasyon sonrası ekran görüntüsü alıp OCR ile kontrol et
- GitHub aramalarında: önce `curl --socks5-hostname` ile API'den liste al, sonra sadece en iyi repo'ya navigate et

### 3. REPO ONAY KURALI
GitHub'dan clone yapmadan ÖNCE kullanıcıya sor. Asla izinsiz clone yapma.

### 4. Tor acik ama proxy hazir degil
3. **DuckDuckGo bos sonuc** — Tor cikis dugumu bloke olabilir; `start` ile Tor'u yeniden baslat (yeni devre).
4. **Ekranda captcha** — Tor IP'si banli olabilir; Tor Browser'da "New Identity" kullan.
5. **Port 9150 yerine 9050** — 9050 Tor daemon'u, 9150 Tor Browser'u. Tor Browser aciksa 9150.
6. **SOCKS bagimliligi eksik → "Missing dependencies for SOCKS support""** — `hermestor.py search` ve `proxy` komutlari `requests[socks]` gerektirir. Cozum: `pip install requests[socks]` veya `pip install pysocks` calistir.
7. **Windows bash (git-bash) yol bozulmasi** — Hermes `C:\WINDOWS\System32` altindan calisirken `python C:\Users\marko\hermestor.py` yazinca MSYS yol donusumu bozuyor (`C:\WINDOWS\System32\Usersmarkohermestor.py` haline geliyor). Cozum: `/c/Users/marko/hermestor.py` yaz (UNIX stil yol, bash duzgun cozer).
8. **`open` komutu varsayilan sayfa acabilir** — `hermestor.py open` eski halinde `--new-tab` flag'i vardi; Tor Browser ilk acilista varsayilan donate.torproject.org sayfasini ana pencerede gosteriyor, verilen URL ise arka planda yeni sekmede aciyordu. Cozum: `--new-tab` kaldirildi, Firefox URL'i direkt aliyor. Eger hala default sayfa goruyorsan `hermestor.py`'nin `open_url` fonksiyonunu kontrol et — `--new-tab` flag'i OLMAMALI.

9. **Python SOCKS timeout → curl ile fallback** — `hermestor.py proxy` veya `tor_get()` bazen SOCKS baglantisinda zaman asimina ugruyor. Cozum: `curl --socks5-hostname 127.0.0.1:9150 --connect-timeout 10 -s "https://..."` ile dogrudan HTTP al. Python `requests[socks]` yerine curl alternatifi genelde daha hizli baglanir. Detay icin `skill_view(name='tor-browser-arama', file_path='references/tor-curl-ocr-workflow.md')` yap.

10. **Tarayici penceresi arka plandaysa** — Klavye komutlari dogru pencereye gitmez. Cozum: `scripts/focus_tor.ps1` ile EnumWindows + SetForegroundWindow kullan. Kullanim: `powershell -ExecutionPolicy Bypass -File "...\\scripts\\focus_tor.ps1"`.

11. **Vision destegi olmayan modelle ekran okuma** — DeepSeek V4 Flash gibi modeller `vision_analyze`'i desteklemez. Cozum: Tesseract OCR ile ekran goruntusunu metne cevir, Tor Browser alanini kırp (sol %75, kenar bosluklari), `--psm 4` ile oku. Tam komut: `skill_view(name='tor-browser-arama', file_path='references/tor-curl-ocr-workflow.md')`.

12. **Klavye tuşları adres çubuğu yerine DuckDuckGo arama kutusuna gider** — `Ctrl+L` + URL + Enter gönderince bazen sayfadaki DuckDuckGo kutusu odaklanır, adres çubuğu değil. OCR'da `"...{ENTER}github.com/ — DuckDuckGo ile ara"` görürsen bu olmuştur. **Cozum: `hermestor.py navigate <URL>` kullan** — bu komut dogrudan Firefox adres çubuğuna yazar, Ctrl+L'den daha güvenilir. Alternatif: adres çubuğu koordinatına mouse ile tıkla (`click 300 85`), sonra Ctrl+A + URL + Enter.

13. **`open` komutu sayfayı arka planda açar** — Tor Browser açıksa yeni sekmede açar ama o anki sekmede kalmaz. Sayfayı görmek icin `open`'tan sonra focus script'ini calistir: `powershell -ExecutionPolicy Bypass -File "...scripts\\focus_tor.ps1"`

## Verification Checklist

- [ ] `python hermestor.py status` -> "AKTIF" yazdi
- [ ] `python hermestor.py search "test"` sonuc getirdi
- [ ] `https://check.torproject.org` Tor kullanildigini dogruladi
- [ ] Ekranda "Connect" tiklandiktan sonra proxy aktif oldu
