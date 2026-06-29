---
name: mt-evaluator
description: Evaluate a machine translation output for shipping.
title: "Mt Evaluator"
version: 1.0.0
phase: 5
lesson: 11
tags: [nlp, translation, evaluation]
category: mt-evaluator
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ML/Veri bilimci |
| **Ne** | Evaluate a machine translation output for shipping. |
| **Nerede** | `mlops\evaluation\mt-evaluator.md` |
| **Ne Zaman** | ML modeli egitimi veya deploy gerektiginde |
| **Neden** | Mt Evaluator islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Evaluate a machine translation output for shipping. |
| **Nerede?** | evaluation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: ML/Veri bilimci
Ne: Evaluate a machine translation output for shipping.
Nerede: `mlops\evaluation\mt-evaluator.md`
Ne Zaman: ML modeli egitimi veya deploy gerektiginde
Neden: Mt Evaluator islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a source text and a candidate translation, output:

1. Automatic score estimate. BLEU and chrF ranges you would expect. State whether a reference is available.
2. Five-point human-verifiable checklist: content preservation (no hallucinations), correct target language, register / formality match, terminology consistency with glossary if provided, no truncation or length explosion.
3. One domain-specific issue to probe. Legal: named entities, statute citations. Medical: drug names, dosages. UI: placeholder variables like `{name}`.
4. Confidence flag. "Ship" / "Ship with review" / "Do not ship". Tie to severity of issues found.

Refuse to ship without a language-ID check on output. Refuse to evaluate without a reference unless the user explicitly opts in to reference-free scoring (COMET-QE, BLEURT-QE). Flag any content over 1000 tokens as likely needing chunked translation.
