
> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Windows Automation_Tor Hindistan Siteleri Bypass |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: tor-hindistan-siteleri-bypass
description: Hindistan sitelerine Tor üzerinden erişim. GBHackers ve Bing IN çalışır. TheHackerNews Cloudflare bloklu.
title: "Tor Hindistan Siteleri Bypass"
version: 1.0.0
platforms: [windows]

audience: user
tags: [automation, tor, windows]
category: windows-automation---

# Hindistan Siteleri Tor Bypass Çözümü

**Problem:** TheHackerNews Cloudflare bloklu (HTTP 403).

**Çalışan:**
- GBHackers: `https://gbhackers.com/?s={urllib.parse.quote(sorgu)}`
- Bing IN: `https://www.bing.com/search?q={urllib.parse.quote(sorgu)}&cc=IN`

## Örnek
```python
# GBHackers (direkt çalışır)
r = requests.get(f'https://gbhackers.com/?s=bluetooth+sniffing', proxies=proxies, headers=headers)
# 193KB, gerçek güvenlik içeriği

# Bing IN
r = requests.get(f'https://www.bing.com/search?q=bluetooth+sniffing&cc=IN', proxies=proxies, headers=headers)
# 122KB
```
