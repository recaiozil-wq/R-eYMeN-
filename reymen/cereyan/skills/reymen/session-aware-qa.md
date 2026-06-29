---
name: session-aware-qa
title: Session Bilinçli QA
description: Soruları önce geçmiş session'da kontrol et, aynıysa önceki cevabı ver.
category: reymen
---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ReYMeN ajani |
| **Ne** | Soruları önce geçmiş session'da kontrol et, aynıysa önceki cevabı ver. |
| **Nerede** | `reymen\session-aware-qa.md` |
| **Ne Zaman** | ReYMeN yapilandirmasi gerektiginde |
| **Neden** | Session Aware Qa islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |

Kim: ReYMeN ajani
Ne: Soruları önce geçmiş session'da kontrol et, aynıysa önceki cevabı ver.
Nerede: `reymen\session-aware-qa.md`
Ne Zaman: ReYMeN sistemi yapilandirmasi gerektiginde
Neden: Session Aware Qa islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Session Bilinçli QA

> **Kategori:** reymen/tekrar

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Soruyu önce geçmiş session'da ara, aynıysa önceki cevabı ver |
| **Nerede?** | `session_search()` FTS5 |
| **Ne Zaman?** | Her soruda, LLM'den önce |
| **Neden?** | Tutarlı cevap + token tasarrufu |
| **Nasıl?** | FTS5 ara → bulunduysa "önceki session'da şöyle cevaplamıştım" + aynı cevap |

**Kural:** Kimlik sorularında (`sen kimsin?`) her zaman AYNI cevap ver.
