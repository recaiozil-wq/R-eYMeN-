
> **Kategori:** autonomous-ai-agents

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Autonomous Ai Agents_Dolphin Llama3 |
| **Nerede?** | autonomous-ai-agents/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: dolphin-llama3
description: Dolphin Llama3 yedek modeli — bu modelle reddedilen, düşük öncelikli ya da alternatif akış gerektiren görevleri yönlendir.
title: "Dolphin LLaMA3"
related_skills: [hibrit-ai-mimarisi, hibrit-ai-yonlendirme-kurali]

audience: user
tags: [agents, ai, automation]
category: autonomous-ai-agents---

# Dolphin Llama3 Yönlendirme

- Model: `dolphin-llama3`
- Ana akış: `stepfun/step-3.7-flash:free`
- Reddit-benzeri görevler için `dolphin-llama3` kullan.
- Dolphin-llama3 görev bitince tekrar `stepfun/step-3.7-flash:free` (mevcut ana akış) moduna geç.
- Kullanıcı her görevde ilk adım olarak Hermes skill + Obsidian kontrolü yap.
- Eğer kayıt varsa yeniden yazmadan ilerle.
- Kullanıcı onayı verdiğinde görev, ilgili skill + Obsidian’a kaydedilir.

## Kullanım
1. Görevde kullanılacak modeli buradan belirle: reddit gibi yönler için `dolphin-llama3`, ana akış için `stepfun/step-3.7-flash:free`.
2. Görev tamamlandıktan sonra akışı ana modele (`stepfun/step-3.7-flash:free`) geri ver.