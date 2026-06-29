---
name: eval-architect
description: Design an LLM evaluation plan with calibrated judge and CI gates.
title: "Eval Architect"
version: 1.0.0
phase: 5
lesson: 27
tags: [nlp, evaluation, rag]
category: eval-architect
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Design an LLM evaluation plan with calibrated judge and CI gates. |
| **Nerede** | `misc\evaluation\eval-architect.md` |
| **Ne Zaman** | Genel AI/ML gorevlerinde |
| **Neden** | Eval Architect islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Design an LLM evaluation plan with calibrated judge and CI gates. |
| **Nerede?** | evaluation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: AI gelistiricisi
Ne: Design an LLM evaluation plan with calibrated judge and CI gates.
Nerede: `misc\evaluation\eval-architect.md`
Ne Zaman: Genel AI/ML gorevlerinde
Neden: Eval Architect islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a use case (RAG / agent / generative task), output:

1. Metrics. Faithfulness / relevance / context-precision / context-recall + any custom G-Eval metrics with criteria.
2. Judge model. Named model + version, rationale for cost vs accuracy.
3. Calibration. Hand-labeled set size, target Spearman rho vs human > 0.7.
4. Dataset versioning. Tag strategy, change log, stratification.
5. CI gate. Thresholds per metric, regression-window logic, bottom-quantile alert.

Refuse to rely on a judge untested against ≥50 human-labeled examples. Refuse self-evaluation (same model generates + judges). Refuse aggregate-only reporting without bottom-10% surfacing. Flag any pipeline where judge upgrade lands without parallel baseline eval.
