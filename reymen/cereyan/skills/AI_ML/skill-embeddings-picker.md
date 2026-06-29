---
name: skill-embeddings-picker
description: Pick a tokenization approach for a new language model or text pipeline.
title: "Skill Embeddings Picker"
version: 1.0.0
phase: 5
lesson: 04
tags: [nlp, tokenization, embeddings]
category: skill-embeddings-picker
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ML/Veri bilimci |
| **Ne** | Pick a tokenization approach for a new language model or text pipeline. |
| **Nerede** | `mlops\skills\skill-embeddings-picker.md` |
| **Ne Zaman** | ML modeli egitimi veya deploy gerektiginde |
| **Neden** | Skill Embeddings Picker islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Pick a tokenization approach for a new language model or text pipeline. |
| **Nerede?** | skills/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: ML/Veri bilimci
Ne: Pick a tokenization approach for a new language model or text pipeline.
Nerede: `mlops\skills\skill-embeddings-picker.md`
Ne Zaman: ML modeli egitimi veya deploy gerektiginde
Neden: Skill Embeddings Picker islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a task and dataset description, you output:

1. Tokenization strategy (word-level, BPE, WordPiece, SentencePiece, byte-level BPE). One-sentence reason.
2. Vocabulary size target. English-only LM: 32k. Multilingual: 64k-100k. Code: 50k-100k.
3. Library call with the exact training command. Name the library (Hugging Face `tokenizers`, `sentencepiece`). Quote arguments.
4. One reproducibility pitfall. Tokenizer-model mismatch is the single most common silent production bug. Name which tokenizer pairs with which pretrained checkpoint and warn against swapping.

Refuse to recommend training a custom tokenizer when the user is fine-tuning a pretrained LLM (the fine-tune must use the pretrained tokenizer). Refuse to recommend word-level tokenization for any production inference path. Flag non-English or multi-script corpora as needing SentencePiece with byte fallback.
