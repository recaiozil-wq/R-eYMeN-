---
name: rollout-runbook
description: Design a shadow → canary → A/B → 100% rollout plan for a new LLM model or prompt template, with five canary gates, noise-floor-aware thresholds, and a seconds-fast rollback path.
title: "Rollout Runbook"
version: 1.0.0
phase: 17
lesson: 20
tags: [rollout, canary, shadow, progressive-delivery, feature-flags, argo-rollouts, flagger, kserve]
category: rollout-runbook
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | DevOps muhendisi |
| **Ne** | Design a shadow → canary → A/B → 100% rollout plan for a new LLM model or prompt template, with five canary gates, noise-floor-aware thresholds, and a seconds-fast rollback path. |
| **Nerede** | `devops\rollout-runbook.md` |
| **Ne Zaman** | CI/CD veya altyapi yonetimi gerektiginde |
| **Neden** | Rollout Runbook islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Design a shadow → canary → A/B → 100% rollout plan for a new LLM model or prompt template, with five canary gates, noise-floor-aware thresholds, and a seconds-fast rollback path. |
| **Nerede?** | devops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: DevOps muhendisi
Ne: Design a shadow → canary → A/B → 100% rollout plan for a new LLM model or prompt template, with five canary gates, noise-floor-aware thresholds, and a seconds-fast rollback path.
Nerede: `devops\rollout-runbook.md`
Ne Zaman: CI/CD veya altyapi yonetimi gerektiginde
Neden: Rollout Runbook islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a candidate change (new model, new prompt template, new router policy), baseline production metrics, and risk tolerance, produce a rollout runbook.

Produce:

1. Shadow plan. Duration (24-72 hours). Metrics logged: outputs, token counts, latency, refusal, error. Alert on: >20% cost shift, >30% output length shift, any schema violation.
2. Canary progression. Stages (1% → 10% → 25% → 50% → 75% → 100%). Duration per stage (30m-24h based on traffic volume; ensure each stage has enough data for statistical confidence).
3. Five gates. Specify the exact thresholds for latency P99, cost/request, error/refusal, output-length P99, thumbs-down rate. Set above noise floor (expect 15% irreducible variance).
4. Tooling. Name the rollout controller (Argo Rollouts, Flagger, KServe) and the feature flag system for instant rollback.
5. Rollback path. Document the three actions: flip flag → revert pinned digest → verify. Target time: under 60 seconds end to end.
6. Skip A/B? Justify. Improved-variant changes skip A/B; distinctly different changes (new behavior, new cost curve) require A/B.

Hard rejects:
- Skipping shadow mode. Refuse — cost spikes and length regressions slip past offline eval.
- Gates tighter than 15% variance. Refuse — false alarms will halt legitimate rollouts.
- Rollback that requires redeploy. Refuse — it is not a rollback, it is a damage report.

Refusal rules:
- If the change is safety-critical (e.g., PII handling change), require explicit additional gate: zero PII leakage in shadow sample before starting canary.
- If traffic volume is <100 req/hour, require extended canary stages — otherwise gate noise overwhelms signal.
- If the team cannot provide baseline metrics for the five canary gates, refuse the rollout — baseline is prerequisite.

Output: a one-page runbook with shadow, canary, gates, tooling, rollback, A/B posture. End with a rollback drill requirement: rehearse rollback once before first real deploy.
