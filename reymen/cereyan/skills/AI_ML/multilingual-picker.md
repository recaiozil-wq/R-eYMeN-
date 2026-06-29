---
name: multilingual-picker
description: Pick source language, target model, and evaluation plan for a multilingual NLP task.
title: "Multilingual Picker"
version: 1.0.0
phase: 5
lesson: 18
tags: [nlp, multilingual, cross-lingual]
category: multilingual-picker
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ML/Veri bilimci |
| **Ne** | Pick source language, target model, and evaluation plan for a multilingual NLP task. |
| **Nerede** | `mlops\nlp\multilingual-picker.md` |
| **Ne Zaman** | ML modeli egitimi veya deploy gerektiginde |
| **Neden** | Multilingual Picker islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Pick source language, target model, and evaluation plan for a multilingual NLP task. |
| **Nerede?** | nlp/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: ML/Veri bilimci
Ne: Pick source language, target model, and evaluation plan for a multilingual NLP task.
Nerede: `mlops\nlp\multilingual-picker.md`
Ne Zaman: ML modeli egitimi veya deploy gerektiginde
Neden: Multilingual Picker islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given requirements (target languages, task type, available labeled data per language), output:

1. Source language for fine-tuning. Default English; check LANGRANK or qWALS if target language has a typologically close high-resource language.
2. Base model. XLM-R (classification), mT5 (generation), NLLB (translation), Aya-23 (generative LLM).
3. Few-shot budget. Start with 100-500 target-language examples if available. Zero-shot only if labeling is infeasible.
4. Evaluation plan. Per-language accuracy (not aggregate), cross-lingual consistency, entity-level F1 on non-Latin scripts.

Refuse to ship a multilingual model without per-language evaluation — aggregate metrics hide long-tail failures. Flag scripts with low tokenization coverage (Amharic, Tigrinya, many African languages) as needing a model with byte-fallback (SentencePiece with byte_fallback=True, or a byte-level tokenizer like GPT-2).
