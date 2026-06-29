---
name: skill-refusal-evaluation
description: Two-sided refusal metrics with calibration and per-category breakdown over a labeled prompt corpus
title: "Skill Refusal Evaluation"
version: 1.0.0
phase: 19
lesson: 84
tags: [safety, evaluation, calibration]
category: skill-refusal-evaluation
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ML/Veri bilimci |
| **Ne** | Two-sided refusal metrics with calibration and per-category breakdown over a labeled prompt corpus |
| **Nerede** | `mlops\skills\skill-refusal-evaluation.md` |
| **Ne Zaman** | ML modeli egitimi veya deploy gerektiginde |
| **Neden** | Skill Refusal Evaluation islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Two-sided refusal metrics with calibration and per-category breakdown over a labeled prompt corpus |
| **Nerede?** | skills/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: ML/Veri bilimci
Ne: Two-sided refusal metrics with calibration and per-category breakdown over a labeled prompt corpus
Nerede: `mlops\skills\skill-refusal-evaluation.md`
Ne Zaman: ML modeli egitimi veya deploy gerektiginde
Neden: Skill Refusal Evaluation islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Refusal Evaluation

A labeled corpus of safe and unsafe prompts goes through one or more model policies. Outputs are classified as refusals or answers. The framework returns:

- under-refusal: answered prompts labeled unsafe / total unsafe
- over-refusal: refused prompts labeled safe / total safe
- accuracy: (correct refusals + correct answers) / total
- ECE: expected calibration error binned by stated confidence
- per-category under-refusal: joined against the lesson 82 taxonomy

## Plugging in a real model

The mock LLM is a callable `(prompt: str) -> str`. Replace it with an HTTP wrapper that returns the model output and embeds a confidence tag (or modify `parse_confidence` to read whatever your provider exposes). Everything else stays the same.

## Artifact

`outputs/refusal_eval_report.json` contains the per-policy metrics. Lesson 87 reads this report to set thresholds.
