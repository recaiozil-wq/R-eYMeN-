---
name: trajectory-compressor-deseni
title: Trajectory Compressor ile Context Yonetimi
description: "LLM destekli konusma gecmisi sikistirma: token budget, yapisal ozet, rule-based fallback, iteratif guncelleme, arac cikti budama"
tags: [context, compression, token-management, pattern]
audience: contributor
---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | LLM destekli konusma gecmisi sikistirma: token budget, yapisal ozet, rule-based fallback, iteratif guncelleme, arac cikti budama |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Trajectory Compressor ile Context Yonetimi

## Problem
Uzun ReAct konusmalari token limitini asar. Tum gecmisi atmak baglam kaybina yol acar.

## Cozum: TrajectoryCompressor
- Token budget: esik oranina gore tetiklenir (%75)
- Son N mesaj korunur (varsayilan: 8)
- Arac ciktilari budanir (max 300 karakter)
- LLM ile yapisal ozet: Aktif Gorev / Tamamlananlar / Devam Eden / Bekleyen / Bulgular
- LLM yoksa rule-based fallback (eylem+gozlem regex)
- Iteratif: onceki ozet bir sonraki ozete eklenir

## Kullanim
```python
comp = TrajectoryCompressor(provider=provider)
mesajlar = comp.compress(mesajlar, context_length=8192)
```

## Avantaj
- Token tasarrufu: 50 mesaj -> 2 mesaj (ozet + son 8)
- Baglam kaybi yok: yapisal ozet tum ana noktalari icerir
- LLM dusse bile rule-based fallback calisir
