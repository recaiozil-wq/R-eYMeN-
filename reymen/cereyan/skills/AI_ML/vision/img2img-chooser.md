---
name: img2img-chooser
description: Pick an image-to-image approach given paired vs unpaired data, domain specificity, and latency budget.
title: "Img2Img Chooser"
version: 1.0.0
phase: 8
lesson: 04
tags: [pix2pix, img2img, conditional]
category: img2img-chooser
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Pick an image-to-image approach given paired vs unpaired data, domain specificity, and latency budget. |
| **Nerede** | `misc\vision\img2img-chooser.md` |
| **Ne Zaman** | Genel AI/ML gorevlerinde |
| **Neden** | Img2Img Chooser islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Pick an image-to-image approach given paired vs unpaired data, domain specificity, and latency budget. |
| **Nerede?** | vision/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: AI gelistiricisi
Ne: Pick an image-to-image approach given paired vs unpaired data, domain specificity, and latency budget.
Nerede: `misc\vision\img2img-chooser.md`
Ne Zaman: Genel AI/ML gorevlerinde
Neden: Img2Img Chooser islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a task description (source domain, target domain, data availability - paired/unpaired/N samples, latency budget, quality bar), output:

1. Approach. Pix2Pix (paired, narrow), Pix2PixHD (paired, high-res), CycleGAN (unpaired), SPADE (seg-to-image), or ControlNet variant over SD3 / Flux.1 (general, open-domain).
2. Training data spec. Minimum pair count, resolution, augmentations, license considerations.
3. Architecture. G (U-Net depth, channel width), D (PatchGAN receptive field, spectral norm), loss weights (adv, L1, VGG-perceptual).
4. Inference latency. Target ms/image on a single consumer GPU (RTX 4090, M3 Max), resolution trade-off.
5. Eval. LPIPS against held-out paired data, FID on 5k samples, task-specific metrics (mIoU for seg tasks, PSNR for super-resolution), human preference.

Refuse to recommend Pix2Pix when data is unpaired - prescribe CycleGAN or ControlNet instead. Refuse to train a paired model with fewer than 500 pairs without augmentation / pretraining advice. Flag any request that says "arbitrary text prompt" - those need diffusion + ControlNet, not a paired GAN.
