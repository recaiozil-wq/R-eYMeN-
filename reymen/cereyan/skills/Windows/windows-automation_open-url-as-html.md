---
name: open-url-as-html
description: ""7000 aç" veya "localhost:PORT aç" dendiğinde otomatik giriş yapıp sayfayı tarayıcıda açar. Soru sormadan direkt yapar."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [browser, html, windows, url, açma, login, odysseus]
audience: user
related_skills: [open_vscode_focus]
---


> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | 7000 aç" veya "localhost:PORT aç" dendiğinde otomatik giriş yapıp sayfayı tarayıcıda açar. Soru sormadan direkt yapar. |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Localhost Sayfası Aç + Otomatik Giriş

## Tetikleyiciler

Kullanıcı şunları söylediğinde bu skill devreye girer:
- "7000 aç"
- "localhost:7000 aç"
- "sayfayı aç"
- "aç" (aktif bağlamda PORT geçiyorsa)
- "PORT aç" (herhangi bir port numarası)

**Kural:** Soru sorma. Onay alma. "Basayım mı?" deme. Direkt yap. Bitince tek satır yaz: "Açıldı ✔"

## Hedef Davranış

Kullanıcı "7000 aç" der → Hermes:
1. `browser_navigate` → `http://localhost:7000/login`
2. `browser_type` → username alanına kullanıcı adı gir
3. `browser_type` → password alanına şifre gir (`$env:ODYSSEUS_PASS` veya Hermes vault'tan)
4. `browser_click` → Sign In butonu
5. Giriş sonrası sayfa yüklenir → kullanıcı giriş yapmış halde görür
6. Hermes sadece yazar: "Açıldı ✔"

## Giriş Bilgileri (Odysseus / localhost:7000)

Şifre `$env:ODYSSEUS_PASS` environment variable'ından okunur.
Yoksa Hermes vault'tan `odysseus_admin` anahtarıyla al.

| Alan | Değer |
|------|-------|
| URL | `http://localhost:7000/login` |
| Kullanıcı | `admin` |
| Şifre | `$env:ODYSSEUS_PASS` |
| Remember Me | işaretle |

## HTML Olarak Kaydet (alternatif)

Kullanıcı "html olarak aç" veya "kaydet" derse:

```python
import urllib.request, http.cookiejar, os, subprocess

pw = os.environ.get("ODYSSEUS_PASS", "")
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
login_data = f"username=admin&password={pw}&remember=on".encode()
opener.open("http://localhost:7000/login", login_data)

resp = opener.open("http://localhost:7000/")
html = resp.read().decode('utf-8', errors='replace')

tmp = os.path.join(os.environ.get('TEMP', '/tmp'), 'hermes_page.html')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(html)

subprocess.Popen(['start', tmp], shell=True)
print(f"Açıldı: {tmp}")
```

## Encoding Notu

Windows'ta `cp1254` codec hatası alınır. `curl`/`wget` terminal çıktısı KULLANMA. Her zaman Python `decode('utf-8', errors='replace')` kullan.
