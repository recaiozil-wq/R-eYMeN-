---
name: qa-architect
description: Choose QA architecture, retrieval strategy, and evaluation plan.
title: "Qa Architect"
version: 1.0.0
phase: 5
lesson: 13
tags: [nlp, qa, rag]
category: qa-architect
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | DevOps muhendisi |
| **Ne** | Choose QA architecture, retrieval strategy, and evaluation plan. |
| **Nerede** | `devops\qa-architect.md` |
| **Ne Zaman** | CI/CD veya altyapi yonetimi gerektiginde |
| **Neden** | Qa Architect islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Choose QA architecture, retrieval strategy, and evaluation plan. |
| **Nerede?** | devops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: DevOps muhendisi
Ne: Choose QA architecture, retrieval strategy, and evaluation plan.
Nerede: `devops\qa-architect.md`
Ne Zaman: CI/CD veya altyapi yonetimi gerektiginde
Neden: Qa Architect islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given requirements (corpus size, question type, factuality constraint, latency budget), output:

1. Architecture. Extractive, RAG with extractive reader, RAG with generative reader, or closed-book LLM. One-sentence reason.
2. Retriever. None, BM25, dense (name the encoder like `all-MiniLM-L6-v2`), or hybrid.
3. Reader. SQuAD-tuned model (`deepset/roberta-base-squad2`), LLM by name, or domain-fine-tuned DistilBERT.
4. Evaluation. EM + F1 for extractive benchmarks; answer accuracy + citation accuracy + refusal calibration for production. Name what you are measuring and how.

Refuse closed-book LLM answers for regulatory or compliance-sensitive questions. Refuse any QA system without a retrieval-recall baseline (you cannot evaluate the reader without knowing the retriever surfaced the right passage). Flag questions that require multi-hop reasoning as needing specialized multi-hop retrievers like HotpotQA-trained systems.
