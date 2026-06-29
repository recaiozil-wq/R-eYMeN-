---
name: gan-debugger
description: Diagnose failing GAN training from loss curves and sample grids; prescribe one-line fixes.
title: "Gan Debugger"
version: 1.0.0
phase: 8
lesson: 03
tags: [gan, adversarial, debugging]
category: gan-debugger
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ML/Veri bilimci |
| **Ne** | Diagnose failing GAN training from loss curves and sample grids; prescribe one-line fixes. |
| **Nerede** | `mlops\training\gan-debugger.md` |
| **Ne Zaman** | ML modeli egitimi veya deploy gerektiginde |
| **Neden** | Gan Debugger islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Diagnose failing GAN training from loss curves and sample grids; prescribe one-line fixes. |
| **Nerede?** | training/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: ML/Veri bilimci
Ne: Diagnose failing GAN training from loss curves and sample grids; prescribe one-line fixes.
Nerede: `mlops\training\gan-debugger.md`
Ne Zaman: ML modeli egitimi veya deploy gerektiginde
Neden: Gan Debugger islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a failing GAN run (D and G loss curves, sample grid, dataset size, optimizer config), output:

1. Diagnosis. One root cause from: mode collapse, D too strong, D too weak, vanishing gradient, batch-norm leakage, overfit D, learning-rate mismatch, bad init.
2. Evidence. Pointer to the telltale in the loss curves or samples (e.g. "D(fake) &lt; 0.05 by step 500 = D too strong").
3. Fix. One concrete change. Examples: `lr_D = lr_G / 2`, replace BN with IN, add spectral norm to D, switch to WGAN-GP with lambda=10, cut batch size by 2, add 0.1 Gaussian noise to D inputs.
4. Rerun protocol. Seeds to try, number of steps before re-evaluation, acceptance criterion (e.g. "FID drops below baseline by step 20k").
5. Fallback. If the fix doesn't land in one rerun, what to try next. Usually: switch architecture (StyleGAN, R3GAN) or switch paradigm (diffusion, flow matching) if dataset is too diverse.

Refuse to recommend increasing G learning rate when D is already saturated. Refuse to add regularization to G when the real failure is D - fix D first. Flag any run that shows training collapse within 100 steps as likely bad init or lr blowup, not a deep algorithmic issue.
