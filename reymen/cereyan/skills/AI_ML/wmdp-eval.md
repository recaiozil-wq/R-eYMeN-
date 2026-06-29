---
name: wmdp-eval
description: Audit a dual-use capability claim against WMDP, unlearning evaluation, and elicitation studies.
title: "Wmdp Eval"
version: 1.0.0
phase: 18
lesson: 17
tags: [wmdp, rmu, dual-use, biosecurity, cybersecurity, chemistry]
category: wmdp-eval
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ML/Veri bilimci |
| **Ne** | Audit a dual-use capability claim against WMDP, unlearning evaluation, and elicitation studies. |
| **Nerede** | `mlops\evaluation\wmdp-eval.md` |
| **Ne Zaman** | ML modeli egitimi veya deploy gerektiginde |
| **Neden** | Wmdp Eval islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Audit a dual-use capability claim against WMDP, unlearning evaluation, and elicitation studies. |
| **Nerede?** | evaluation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: ML/Veri bilimci
Ne: Audit a dual-use capability claim against WMDP, unlearning evaluation, and elicitation studies.
Nerede: `mlops\evaluation\wmdp-eval.md`
Ne Zaman: ML modeli egitimi veya deploy gerektiginde
Neden: Wmdp Eval islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a dual-use capability claim ("our model does not meaningfully help with bioweapons / cyberattack / chemistry"), audit the supporting evaluation.

Produce:

1. Benchmark coverage. Was WMDP (or an equivalent yellow-zone benchmark) run? Report per-domain scores (bio, cyber, chem). A claim without per-domain numbers cannot be evaluated.
2. Unlearning trace. If unlearning was applied (RMU or alternative), report the general-capability delta (MMLU, HELM, HumanEval). Unlearning with no general-capability report is not credible.
3. Refusal-path-audit. Was the benchmark administered via raw completion or via the production safety stack? A model that scores low only because of the safety stack is still dual-use capable when the stack is bypassed.
4. Elicitation study. Multiple-choice capability does not equal elicitation-hardened capability. Are Anthropic-style acquisition trials, or equivalent novice-in-the-loop studies, referenced? If not, the claim is limited to WMDP-style evidence.
5. Novice-vs-expert split. Novice-relative uplift and expert-absolute capability are different quantities. Are both addressed?

Hard rejects:
- Any dual-use safety claim without WMDP-equivalent capability measurement.
- Any unlearning claim without general-capability delta.
- Any "no meaningful uplift" claim without novice-in-the-loop study.

Refusal rules:
- If the user asks whether their model crosses ASL-3, refuse a direct answer; the thresholds are lab-specific (Lesson 18) and elicitation-dependent.
- If the user asks for a WMDP cutoff that is "safe," refuse — the threshold depends on elicitation resistance, tacit-knowledge barriers, and the deployment surface.

Output: a one-page audit that fills the five sections above, flags the most important missing evidence, and identifies whether the claim is WMDP-level or deployment-level. Cite Li et al. (arXiv:2403.03218) once as the benchmark source.
