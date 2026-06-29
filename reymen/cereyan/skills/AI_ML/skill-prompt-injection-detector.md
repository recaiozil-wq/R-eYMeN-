---
name: skill-prompt-injection-detector
description: Layered detector pipeline that returns a category and confidence for any prompt, with measurable precision and recall
title: "Skill PRompt Injection Detector"
version: 1.0.0
phase: 19
lesson: 83
tags: [safety, detector, prompt-injection]
category: skill-prompt-injection-detector
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ML/Veri bilimci |
| **Ne** | Layered detector pipeline that returns a category and confidence for any prompt, with measurable precision and recall |
| **Nerede** | `mlops\skills\skill-prompt-injection-detector.md` |
| **Ne Zaman** | ML modeli egitimi veya deploy gerektiginde |
| **Neden** | Skill Prompt Injection Detector islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Layered detector pipeline that returns a category and confidence for any prompt, with measurable precision and recall |
| **Nerede?** | skills/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: ML/Veri bilimci
Ne: Layered detector pipeline that returns a category and confidence for any prompt, with measurable precision and recall
Nerede: `mlops\skills\skill-prompt-injection-detector.md`
Ne Zaman: ML modeli egitimi veya deploy gerektiginde
Neden: Skill Prompt Injection Detector islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Prompt Injection Detector

A detector here is a function from prompt to verdict. A verdict carries a category from the lesson 82 taxonomy and a confidence in [0, 1].

## Pipeline

1. Normalize - strip zero-width characters, undo homoglyphs, decode base64/hex, fold leet-speak digits, attempt rot13 with a common-words sanity check.
2. Substring rules - hand-written needles such as `ignore previous`, `from now on you are`, `decode this base64`.
3. Regex rules - token-level patterns such as `\bignor\w*\s+(all|prior|previous|earlier)\b`.

Aggregation keeps the maximum score per category and returns the category with the largest score, or `benign` if nothing fires.

## Adding a rule

Edit `code/rules.py`. A rule is a dictionary with `name`, `category` (one of the six taxonomy categories), `score` (float 0 to 1), and one of `substring` or `regex`. Re-run `main.py` to see the impact on per-category precision and recall.

## Artifact

`outputs/detector_report.json` is the per-category metrics file. The end to end gate in lesson 87 reads it to threshold confidence.
