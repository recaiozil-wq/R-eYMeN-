---
name: framework-diff
description: Compare a new safety framework or release note against RSP v3.0, PF v2, FSF v3.0.
title: "Framework Diff"
version: 1.0.0
phase: 18
lesson: 18
tags: [rsp, pf, fsf, frontier-safety, safety-case]
category: framework-diff
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Compare a new safety framework or release note against RSP v3.0, PF v2, FSF v3.0. |
| **Nerede** | `software-development\framework-diff.md` |
| **Ne Zaman** | Ilgili gorev gerektiginde |
| **Neden** | Framework Diff islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Compare a new safety framework or release note against RSP v3.0, PF v2, FSF v3.0. |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: Yazilim gelistirici
Ne: Compare a new safety framework or release note against RSP v3.0, PF v2, FSF v3.0.
Nerede: `software-development\framework-diff.md`
Ne Zaman: Ilgili gorev gerektiginde
Neden: Framework Diff islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a new safety framework, policy, or release note, compare it against Anthropic RSP v3.0, OpenAI PF v2, DeepMind FSF v3.0 along the five structural axes.

Produce:

1. Tier structure. Does the framework define discrete capability thresholds? Are they per-domain (FSF-style) or global (RSP-style)?
2. CBRN threshold. What CBRN evaluation is required? Does it reference WMDP (Lesson 17) or an equivalent? Does it include an elicitation study?
3. AI R&D threshold. Is there a model-autonomous-research threshold? Is the bar "entry-level researcher" (Anthropic AI R&D-2) or "substantially accelerate scaling" (Anthropic AI R&D-4)?
4. Competitor-adjustment. Does the framework allow reduction of requirements if competitors ship without comparable safeguards? Frame as race-dynamic or as incentive-compatibility, as appropriate.
5. Safety-case structure. Is a written safety case required? Does it target monitoring, illegibility, or incapability? What is the evidence bar?

Hard rejects:
- Any safety framework without per-tier capability thresholds.
- Any framework that omits an external governance cross-reference (UK AISI, US CAISI, EU AI Office).
- Any framework that claims "we align with all published frameworks" without specific threshold numbers.

Refusal rules:
- If the user asks which framework is "best," refuse the ranking and point to structural alignment.
- If the user asks for a numeric threshold recommendation, refuse — thresholds are lab-specific and depend on their measurement infrastructure.

Output: a one-page side-by-side comparison against the three frameworks, flagged gaps, and one specific threshold recommendation to add. Cite RSP v3.0, PF v2, FSF v3.0 once each.
