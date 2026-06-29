---
name: ner-picker
description: Pick the right NER approach for a given extraction task.
title: "Ner Picker"
version: 1.0.0
phase: 5
lesson: 06
tags: [nlp, ner, extraction]
category: ner-picker
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ML/Veri bilimci |
| **Ne** | Pick the right NER approach for a given extraction task. |
| **Nerede** | `mlops\nlp\ner-picker.md` |
| **Ne Zaman** | ML modeli egitimi veya deploy gerektiginde |
| **Neden** | Ner Picker islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Pick the right NER approach for a given extraction task. |
| **Nerede?** | nlp/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: ML/Veri bilimci
Ne: Pick the right NER approach for a given extraction task.
Nerede: `mlops\nlp\ner-picker.md`
Ne Zaman: ML modeli egitimi veya deploy gerektiginde
Neden: Ner Picker islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a task description (domain, label set, language, latency, data volume), output:

1. Approach. Rule-based + gazetteer, CRF, BiLSTM-CRF, or transformer fine-tune.
2. Starting model. Name it (spaCy model ID like `en_core_web_sm` / `en_core_web_trf`, Hugging Face checkpoint ID like `dslim/bert-base-NER`, or "custom, trained from scratch").
3. Labeling strategy. BIO, BILOU, or span-based. Justify in one sentence.
4. Evaluation. Use `seqeval`. Always report entity-level F1, never token-level.

Refuse to recommend fine-tuning a transformer for under 500 labeled examples unless the user already has a pretrained domain model (e.g., BioBERT for medical). Flag nested entities as needing span-based or multi-pass models. Require a gazetteer audit if the user mentions "production scale" while using out-of-the-box CoNLL-2003 labels.
