---
name: fm-tuner
description: Convert a diffusion training plan into a flow-matching / rectified-flow config.
title: "Fm Tuner"
version: 1.0.0
phase: 8
lesson: 13
tags: [flow-matching, rectified-flow, diffusion]
category: fm-tuner
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ML/Veri bilimci |
| **Ne** | Convert a diffusion training plan into a flow-matching / rectified-flow config. |
| **Nerede** | `mlops\training\fm-tuner.md` |
| **Ne Zaman** | ML modeli egitimi veya deploy gerektiginde |
| **Neden** | Fm Tuner islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Convert a diffusion training plan into a flow-matching / rectified-flow config. |
| **Nerede?** | training/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: ML/Veri bilimci
Ne: Convert a diffusion training plan into a flow-matching / rectified-flow config.
Nerede: `mlops\training\fm-tuner.md`
Ne Zaman: ML modeli egitimi veya deploy gerektiginde
Neden: Fm Tuner islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a diffusion-style training plan (data, compute, schedule, target step count, quality bar), output a flow-matching equivalent:

1. Schedule + interpolant. Linear (rectified flow), optimal transport (Lipman OT-CFM), variance-preserving, or cosine. One-sentence reason.
2. Time sampling. Uniform, logit-normal (SD3), or mode-weighted. Warn when uniform sampling at 1000 Hz wastes capacity at endpoints.
3. Target. Velocity v = x_1 - x_0 (rectified flow) or alpha'(t)x_1 + sigma'(t)x_0 (CFM). State which.
4. Optimizer + lr warmup. Include AdamW with beta2 = 0.95 for stability at transformer scale.
5. Reflow plan. Whether to run 0, 1, or 2 reflow iterations; budget per iteration ~ full re-inference over a curated subset.
6. Step counts. Training step count target, expected inference steps (20, 4, 2, 1), guidance scale range.
7. Eval. FID / CLIP-score against the diffusion baseline, plot quality vs step count.

Refuse to do reflow before v_1 has converged (reflow on a bad model just bakes in the bad direction). Refuse to recommend 1-step inference without consistency distillation on top. Flag any flow-matching model that targets &gt; 20 step inference - if you need that many steps, you wasted the reformulation.
