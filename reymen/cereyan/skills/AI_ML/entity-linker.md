---
name: entity-linker
description: Design an entity linking pipeline — KB, candidate generator, disambiguator, evaluation.
title: "Entity Linker"
version: 1.0.0
phase: 5
lesson: 25
tags: [nlp, entity-linking, knowledge-graph]
category: entity-linker
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ML/Veri bilimci |
| **Ne** | Design an entity linking pipeline — KB, candidate generator, disambiguator, evaluation. |
| **Nerede** | `mlops\nlp\entity-linker.md` |
| **Ne Zaman** | ML modeli egitimi veya deploy gerektiginde |
| **Neden** | Entity Linker islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Design an entity linking pipeline — KB, candidate generator, disambiguator, evaluation. |
| **Nerede?** | nlp/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: ML/Veri bilimci
Ne: Design an entity linking pipeline — KB, candidate generator, disambiguator, evaluation.
Nerede: `mlops\nlp\entity-linker.md`
Ne Zaman: ML modeli egitimi veya deploy gerektiginde
Neden: Entity Linker islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a use case (domain KB, language, volume, latency budget), output:

1. Knowledge base. Wikidata / Wikipedia / custom KB. Version date. Refresh cadence.
2. Candidate generator. Alias-index, embedding, or hybrid. Target mention recall @ K.
3. Disambiguator. Prior + context, embedding-based, generative, or LLM-prompted.
4. NIL strategy. Threshold on top score, classifier, or explicit NIL candidate.
5. Evaluation. Mention recall @ 30, top-1 accuracy, NIL-detection F1 on held-out set.

Refuse any EL pipeline without a mention-recall baseline (you cannot evaluate a disambiguator without knowing candidate gen surfaced the right entity). Refuse any pipeline using LLM-prompted EL without constrained output to valid KB ids. Flag systems where popularity bias affects minority entities (e.g. name-clashes) without domain fine-tuning.
