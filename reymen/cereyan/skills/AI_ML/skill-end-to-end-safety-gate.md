---
name: skill-end-to-end-safety-gate
description: Three-checkpoint safety gate composing the input detector, streaming token filter, output classifier, and rules engine with a deterministic aggregation table and per-request trace
title: "Skill End To End Safety Gate"
version: 1.0.0
phase: 19
lesson: 87
tags: [safety, harness, composition]
category: skill-end-to-end-safety-gate
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ML/Veri bilimci |
| **Ne** | Three-checkpoint safety gate composing the input detector, streaming token filter, output classifier, and rules engine with a deterministic aggregation table and per-request trace |
| **Nerede** | `mlops\skills\skill-end-to-end-safety-gate.md` |
| **Ne Zaman** | ML modeli egitimi veya deploy gerektiginde |
| **Neden** | Skill End To End Safety Gate islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Three-checkpoint safety gate composing the input detector, streaming token filter, output classifier, and rules engine with a deterministic aggregation table and per-request trace |
| **Nerede?** | skills/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: ML/Veri bilimci
Ne: Three-checkpoint safety gate composing the input detector, streaming token filter, output classifier, and rules engine with a deterministic aggregation table and per-request trace
Nerede: `mlops\skills\skill-end-to-end-safety-gate.md`
Ne Zaman: ML modeli egitimi veya deploy gerektiginde
Neden: Skill End To End Safety Gate islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# End-to-End Safety Gate

## Lifecycle

1. pre-gen - run the lesson 83 detector on the prompt
   - if confidence >= block_threshold: return refusal, emit trace, stop
2. during-gen - stream from the model, buffer two chunks, scan for known harmful continuations
   - if matched: terminate iterator, mark trace, treat as medium severity
3. post-gen - if no early termination, run the lesson 85 classifier router and the lesson 86 rules engine on the completed output
4. aggregate - take the maximum severity across pre, during, post.classifier, post.rules
5. apply - map to block, redact, warn, or allow

## Aggregation table

| Signal state | Action |
|---|---|
| any high severity | block |
| any medium severity | redact |
| any low severity | warn |
| nothing | allow |

## Trace structure

```text
RequestTrace
  request_id: str
  prompt: str
  pre_gen: { category, confidence, fired[] }
  during_gen: { terminated_early, matched_pattern, partial_chunks }
  post_gen: { classifier_action, classifier_severity, rules_max_severity, rules_violations[] } | null
  final_action: block | redact | warn | allow
  final_output: str
  latency_ms: float
```

## Artifact

`outputs/gate_trace.json` contains the summary and one trace per request, including 50 taxonomy fixtures and 10 benign prompts.
