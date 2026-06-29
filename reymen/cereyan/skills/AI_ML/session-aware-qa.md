---
name: session-aware-qa
title: Session Bilinçli QA
description: Soruları önce geçmiş session'larda kontrol et, aynıysa tekrar cevaplama.
category: kullanici
---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ML/Veri bilimci |
| **Ne** | Soruları önce geçmiş session'larda kontrol et, aynıysa tekrar cevaplama. |
| **Nerede** | `mlops\session-aware-qa.md` |
| **Ne Zaman** | ML model yonetimi gerektiginde |
| **Neden** | Session Aware Qa islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |

Kim: ML/Veri bilimci
Ne: Soruları önce geçmiş session'larda kontrol et, aynıysa tekrar cevaplama.
Nerede: `mlops\session-aware-qa.md`
Ne Zaman: ML modeli egitimi veya deploy gerektiginde
Neden: Session Aware Qa islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Session Bilinçli QA

> **Kategori:** kullanici/tekrar

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar. |
| **Ne?** | Kullanıcı sorusunu önce geçmiş session'da kontrol eder. Aynı/benzer soru bulunursa önceki cevabı referans verir. |
| **Nerede?** | `session_search()` ile FTS5 SQLite mesaj veritabanı. |
| **Ne Zaman?** | Her kullanıcı sorusunda, LLM çağrısından önce. |
| **Neden?** | Tutarlı cevap vermek + token tasarrufu. Aynı soruya her seferinde farklı cevap verilmez. |
| **Nasıl?** | `session_search(query)` → FTS5 ile geçmişte ara → bulunduysa "önceki session'da şöyle cevaplamıştım" de + aynı cevabı ver. |

## Akış

```
Kullanıcı sorusu gelir
  ↓
session_search(query, limit=3)
  ├─ Bulundu (benzer soru+cevap)
  │   → "Bu soruyu daha önce sormuştun. [önceki cevap]"
  └─ Bulunamadı
      → normal LLM akışı
```

## Kurallar

1. Kimlik/model sorularında (`sen kimsin?`, `hangi modelsin?`) her zaman AYNI cevap ver
2. Bulunan cevabı teyit için tekrar LLM'e sorma — direkt hafızadan döndür
3. session_search'te tam eşleşme yoksa keyword benzerliği de dene
