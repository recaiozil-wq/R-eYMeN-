---
name: skill-content-classifier-integration
description: Three output-side classifiers (toxicity, PII, instruction-leakage) behind a single severity router with block, redact, warn, log actions
title: "Skill Content Classifier Integration"
version: 1.0.0
phase: 19
lesson: 85
tags: [safety, classifier, output-filter]
category: skill-content-classifier-integration
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ML/Veri bilimci |
| **Ne** | Three output-side classifiers (toxicity, PII, instruction-leakage) behind a single severity router with block, redact, warn, log actions |
| **Nerede** | `mlops\skills\skill-content-classifier-integration.md` |
| **Ne Zaman** | ML modeli egitimi veya deploy gerektiginde |
| **Neden** | Skill Content Classifier Integration islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Three output-side classifiers (toxicity, PII, instruction-leakage) behind a single severity router with block, redact, warn, log actions |
| **Nerede?** | skills/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: ML/Veri bilimci
Ne: Three output-side classifiers (toxicity, PII, instruction-leakage) behind a single severity router with block, redact, warn, log actions
Nerede: `mlops\skills\skill-content-classifier-integration.md`
Ne Zaman: ML modeli egitimi veya deploy gerektiginde
Neden: Skill Content Classifier Integration islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Content Classifier Integration

Three classifiers, one router, four actions.

## Verdict structure

```text
ClassifierVerdict
  name: str
  severity: none | low | medium | high
  score: float in [0, 1]
  findings: list[str]
```

## Action table

| Severity | Action | Effect |
|---|---|---|
| high | block | output replaced by a policy refusal |
| medium | redact | per-classifier redactors applied in order |
| low | warn | output shipped with a soft notice appended |
| none | log | output shipped unchanged, verdict logged |

## Per-classifier behavior

- toxicity - harassment terms with whitespace boundary and a small left-window negation check; redacts to `[redacted-language]`
- pii - email, phone, SSN, Luhn-validated card, IPv4; severity escalates for SSN and card; redacts each shape to a tag
- instruction-leakage - trigram cosine vs a known system prompt; severity scales with overlap; redacts the first system-prompt line

## Artifact

`outputs/classifier_report.json` carries action verb, severity, redacted output, and full verdict list per case.
