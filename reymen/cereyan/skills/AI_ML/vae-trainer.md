---
name: vae-trainer
description: Specify VAE architecture, latent size, beta schedule, and eval plan for a given dataset and downstream use.
title: "Vae Trainer"
version: 1.0.0
phase: 8
lesson: 02
tags: [vae, latent, generative]
category: vae-trainer
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ML/Veri bilimci |
| **Ne** | Specify VAE architecture, latent size, beta schedule, and eval plan for a given dataset and downstream use. |
| **Nerede** | `mlops\training\vae-trainer.md` |
| **Ne Zaman** | ML modeli egitimi veya deploy gerektiginde |
| **Neden** | Vae Trainer islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Specify VAE architecture, latent size, beta schedule, and eval plan for a given dataset and downstream use. |
| **Nerede?** | training/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: ML/Veri bilimci
Ne: Specify VAE architecture, latent size, beta schedule, and eval plan for a given dataset and downstream use.
Nerede: `mlops\training\vae-trainer.md`
Ne Zaman: ML modeli egitimi veya deploy gerektiginde
Neden: Vae Trainer islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a dataset profile (modality, resolution, dataset size) and the downstream use (reconstruction only, sampling, or input-encoder for a latent-diffusion or token-AR model), output:

1. Variant. Plain VAE, beta-VAE, VQ-VAE, RVQ (residual), or NVAE. One-sentence reason tied to modality and downstream use.
2. Architecture. Encoder / decoder topology (conv downsample factor, channel width, hidden dim, attention blocks). Mention public reference weights (`sd-vae-ft-ema`, Encodec, DAC, WAN-VAE) when applicable.
3. Latent dim. Spatial and channel dims. Total bits per sample. Compression ratio vs the raw data.
4. Beta schedule. Warmup ramp, final value, and free-bits threshold if used.
5. Eval plan. Reconstruction MSE / SSIM / PSNR, KL per dim, active-dim count, posterior-collapse alarm threshold, Frechet distance between `q(z|x)` and prior.

Refuse to ship a VAE with beta > 0.5 at training start (posterior collapse). Refuse to use a plain Gaussian VAE as the final generator for images - it will be blurry; use it as a latent encoder for a diffusion or flow-matching model instead. Flag any VQ-VAE with codebook usage under 20% as a misconfigured codebook reset policy.
