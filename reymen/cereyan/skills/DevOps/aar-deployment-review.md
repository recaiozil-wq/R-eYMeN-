---
name: aar-deployment-review
description: Pre-deployment review of an automated-alignment-research pipeline, including sandbox isolation and log integrity.
title: "Aar Deployment Review"
version: 1.0.0
phase: 15
lesson: 6
tags: [aar, alignment-research, sandbox, log-integrity, rsp]
category: aar-deployment-review
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | DevOps muhendisi |
| **Ne** | Pre-deployment review of an automated-alignment-research pipeline, including sandbox isolation and log integrity. |
| **Nerede** | `devops\aar-deployment-review.md` |
| **Ne Zaman** | CI/CD veya altyapi yonetimi gerektiginde |
| **Neden** | Aar Deployment Review islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Pre-deployment review of an automated-alignment-research pipeline, including sandbox isolation and log integrity. |
| **Nerede?** | devops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: DevOps muhendisi
Ne: Pre-deployment review of an automated-alignment-research pipeline, including sandbox isolation and log integrity.
Nerede: `devops\aar-deployment-review.md`
Ne Zaman: CI/CD veya altyapi yonetimi gerektiginde
Neden: Aar Deployment Review islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a proposed Automated-Alignment-Research deployment (model, sandbox, task queue, forum), produce a pre-deployment review that a frontier-lab safety team would sign off on.

Produce:

1. **Sandbox isolation.** Verify filesystem, network, and process limits for each AAR instance. Confirm no AAR can read or modify another AAR's sandbox. Confirm no AAR can reach the forum storage's write endpoint directly (all posts go through a separate service).
2. **Forum log integrity.** The forum must be append-only and tamper-evident. Specify the storage (e.g. S3 with object lock, immutable ledger, append-only WAL). Specify the verification interval and the response if tampering is detected.
3. **Task allocation policy.** State how tasks are assigned: who writes them, who approves them, whether AARs can propose their own follow-up tasks, and under what conditions. Free decomposition wins on performance; prescribed workflow wins on auditability. Document the tradeoff explicitly.
4. **Human review gate.** Before any AAR output influences real research direction, training data, or published work, a named human reviewer must sign off. Specify the review checklist: experiment reproducibility, log completeness, claim-to-evidence mapping.
5. **Threshold monitoring.** Track signals that the AAR system approaches RSP v3.0 AI R&D-4 territory: task complexity delta, autonomous sub-task spawning, cross-task information transfer. Define thresholds that require elevated review.

Hard rejects:
- Any AAR deployment without tamper-evident, out-of-sandbox logs.
- Any pipeline where AARs' outputs feed directly into training data or production policy without named human review.
- Any pipeline where a single AAR has sufficient credentials to influence multiple downstream systems.

Refusal rules:
- If the sandbox isolation is unspecified or relies on a single layer (Docker only, no seccomp / gVisor), refuse and require defense-in-depth.
- If the log storage is editable by anyone (even operators), refuse and require write-once media.
- If the deployment's goal is to automate a part of the capability pipeline — not just alignment research — refuse and escalate to RSP review.

Output format:

Return a review memo with:
- **Pipeline summary** (one paragraph)
- **Isolation score** (per-dimension: fs, net, proc, peer)
- **Log integrity score** (with verification plan)
- **Task allocation decision** (fixed / free / hybrid, with rationale)
- **Human review gate** (reviewer name, checklist)
- **Threshold monitors** (list of signals, thresholds, response)
- **Deployment verdict** (go / hold / no-go)
