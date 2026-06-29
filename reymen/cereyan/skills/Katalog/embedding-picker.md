---
name: embedding-picker
description: Pick embedding model, dimension, and retrieval mode for a given corpus and deployment.
title: "Embedding Picker"
version: 1.0.0
phase: 5
lesson: 22
tags: [nlp, embeddings, retrieval]
category: embedding-picker
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Pick embedding model, dimension, and retrieval mode for a given corpus and deployment. |
| **Nerede** | `misc\rag-search\embedding-picker.md` |
| **Ne Zaman** | Genel AI/ML gorevlerinde |
| **Neden** | Embedding Picker islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Pick embedding model, dimension, and retrieval mode for a given corpus and deployment. |
| **Nerede?** | rag-search/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: AI gelistiricisi
Ne: Pick embedding model, dimension, and retrieval mode for a given corpus and deployment.
Nerede: `misc\rag-search\embedding-picker.md`
Ne Zaman: Genel AI/ML gorevlerinde
Neden: Embedding Picker islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a corpus (size, languages, domain, avg length), deployment target (cloud / edge / on-prem), latency budget, and storage budget, output:

1. Model. Named checkpoint or API. One-sentence reason.
2. Dimension. Full / Matryoshka-truncated / int8-quantized. Reason tied to storage budget.
3. Mode. Dense / sparse / multi-vector / hybrid. Reason.
4. Query prefix / template if required by the model card.
5. Evaluation plan. MTEB tasks relevant to domain + held-out domain eval with nDCG@10.

Refuse recommendations that truncate Matryoshka to <64 dims without domain validation. Refuse ColBERTv2 for corpora under 10k passages (overhead not justified). Flag long-document corpora (>8k tokens) routed to models with 512-token windows.
