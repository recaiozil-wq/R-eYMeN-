
> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Windows Automation_Tor Kore Siteleri Bypass |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: tor-kore-siteleri-bypass
description: Kore sitelerine Tor üzerinden erişim. Bing KR ve Naver çalışır. BoanNews SOCKS bloklu.
title: "Tor Kore Siteleri Bypass"
version: 1.0.0
platforms: [windows]

audience: user
tags: [automation, tor, windows]
category: windows-automation---

# Kore Siteleri Tor Bypass Çözümü

**Problem:** BoanNews, DailySec SOCKS bloklu.

**Çalışan:**
- Bing KR: `https://www.bing.com/search?q={urllib.parse.quote(sorgu)}&cc=KR`
- Naver: `https://search.naver.com/search.naver?query={urllib.parse.quote(sorgu)}`

## Örnek
```python
r = requests.get(f'https://www.bing.com/search?q={q}&cc=KR', proxies=proxies, headers=headers)
# 119KB, Korece sonuçlar
```
