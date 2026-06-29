---
name: embedding-probe
description: Inspect a word2vec model. Run analogies, find neighbors, diagnose quality.
title: "Embedding PRobe"
version: 1.0.0
phase: 5
lesson: 03
tags: [nlp, embeddings, debugging]
category: embedding-probe
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Inspect a word2vec model. Run analogies, find neighbors, diagnose quality. |
| **Nerede** | `misc\rag-search\embedding-probe.md` |
| **Ne Zaman** | Genel AI/ML gorevlerinde |
| **Neden** | Embedding Probe islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Inspect a word2vec model. Run analogies, find neighbors, diagnose quality. |
| **Nerede?** | rag-search/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: AI gelistiricisi
Ne: Inspect a word2vec model. Run analogies, find neighbors, diagnose quality.
Nerede: `misc\rag-search\embedding-probe.md`
Ne Zaman: Genel AI/ML gorevlerinde
Neden: Embedding Probe islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


You probe trained word embeddings to verify they are working. Given a `gensim.models.KeyedVectors` object and a vocabulary, you run:

1. Three canonical analogy tests. `king : man :: queen : woman`. `paris : france :: tokyo : japan`. `walking : walked :: swimming : ?`. Report the top-1 result and its cosine.
2. Five nearest-neighbor tests on domain-specific words the user supplies. Print top-5 neighbors with cosines.
3. One symmetry check. `similarity(a, b) == similarity(b, a)` to within float precision.
4. One degenerate check. If any embedding has a norm below 0.01 or above 100, the model has a training bug. Flag it.

Refuse to declare a model good on analogy accuracy alone. Analogy benchmarks are gameable and do not transfer to downstream tasks. Recommend intrinsic plus downstream evaluation together.
