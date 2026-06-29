
> **Kategori:** nlp

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Seq2Seq Design |
| **Nerede?** | nlp/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: seq2seq-design
description: Design a sequence-to-sequence pipeline for a given task.
title: "Seq2Seq Design"
tags: [general]
phase: 5
lesson: 09

audience: user
category: seq2seq-design---

Given a task (translation, summarization, paraphrase, question rewrite), output:

1. Architecture. Pretrained transformer encoder-decoder (BART, T5, mBART, NLLB) is the default. RNN-based seq2seq only for specific constraints (streaming, edge inference, pedagogy).
2. Starting checkpoint. Name it (`facebook/bart-base`, `google/flan-t5-base`, `facebook/nllb-200-distilled-600M`). Match checkpoint to task and language coverage.
3. Decoding strategy. Greedy for deterministic output, beam search (width 4-5) for quality, sampling with temperature for diversity. One sentence justification.
4. One failure mode to verify before shipping. Exposure bias manifests as generation drift on longer outputs; sample 20 outputs at 90th-percentile length and eyeball.

Refuse to recommend training a seq2seq from scratch for under ~1M parallel examples. Flag any pipeline using greedy decoding for user-facing content as fragile (greedy repeats and loops).
