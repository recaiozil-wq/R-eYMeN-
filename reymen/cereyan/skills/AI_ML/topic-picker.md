---
name: topic-picker
description: Pick LDA or BERTopic for a corpus. Specify library, knobs, evaluation.
title: "Topic Picker"
version: 1.0.0
phase: 5
lesson: 15
tags: [nlp, topic-modeling]
category: topic-picker
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ML/Veri bilimci |
| **Ne** | Pick LDA or BERTopic for a corpus. Specify library, knobs, evaluation. |
| **Nerede** | `mlops\nlp\topic-picker.md` |
| **Ne Zaman** | ML modeli egitimi veya deploy gerektiginde |
| **Neden** | Topic Picker islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Pick LDA or BERTopic for a corpus. Specify library, knobs, evaluation. |
| **Nerede?** | nlp/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: ML/Veri bilimci
Ne: Pick LDA or BERTopic for a corpus. Specify library, knobs, evaluation.
Nerede: `mlops\nlp\topic-picker.md`
Ne Zaman: ML modeli egitimi veya deploy gerektiginde
Neden: Topic Picker islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a corpus description (document count, avg length, domain, language, compute budget), output:

1. Algorithm. LDA / NMF / BERTopic / Top2Vec / FASTopic. One-sentence reason.
2. Configuration. Number of topics (start at ~sqrt(n_docs)), `min_df` / `max_df` filters, embedding model for neural approaches.
3. Evaluation. Topic coherence (c_v) via `gensim.models.CoherenceModel`, topic diversity, plus a 20-sample human read.
4. Failure mode to probe. For LDA, "junk topics" absorbing stopwords and frequent terms. For BERTopic, -1 outlier cluster swallowing ambiguous documents.

Refuse BERTopic on documents longer than the embedding model's context window without a chunking strategy. Refuse LDA on very short text (tweets, reviews under 10 tokens) as coherence collapses. Flag any n_topics choice below 5 or above 200 as likely wrong for real data.
