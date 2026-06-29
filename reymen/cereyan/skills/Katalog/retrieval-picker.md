---
name: retrieval-picker
description: Pick a retrieval stack for a given corpus and query pattern.
title: "Retrieval Picker"
version: 1.0.0
phase: 5
lesson: 14
tags: [nlp, retrieval, rag, search]
category: retrieval-picker
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Pick a retrieval stack for a given corpus and query pattern. |
| **Nerede** | `misc\rag-search\retrieval-picker.md` |
| **Ne Zaman** | Genel AI/ML gorevlerinde |
| **Neden** | Retrieval Picker islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Pick a retrieval stack for a given corpus and query pattern. |
| **Nerede?** | rag-search/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: AI gelistiricisi
Ne: Pick a retrieval stack for a given corpus and query pattern.
Nerede: `misc\rag-search\retrieval-picker.md`
Ne Zaman: Genel AI/ML gorevlerinde
Neden: Retrieval Picker islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given requirements (corpus size, query pattern, latency budget, quality bar, infra constraints), output:

1. Stack. BM25 only, dense only, hybrid (BM25 + dense + RRF), hybrid + cross-encoder rerank, or three-way (BM25 + dense + learned-sparse).
2. Dense encoder. Name the specific model (`all-MiniLM-L6-v2`, `bge-large-en-v1.5`, `e5-large-v2`, `paraphrase-multilingual-MiniLM-L12-v2`). Match to language, domain, context length.
3. Reranker. Name the cross-encoder model if used (`cross-encoder/ms-marco-MiniLM-L-6-v2`, `BAAI/bge-reranker-large`). Flag ~30-100ms added latency on top-30.
4. Evaluation plan. Recall@10 is the primary retriever metric. MRR for multi-answer. Baseline first, incremental improvements measured against it.

Refuse to recommend dense-only for corpora with named entities, error codes, or product SKUs unless the user has evidence dense handles exact matches. Refuse to skip reranking for high-stakes retrieval (legal, medical) where the final top-5 decides the user's answer.
