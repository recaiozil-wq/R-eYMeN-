---
name: sd-prompter
description: Configure Stable Diffusion / Flux inference for a given prompt, style, and quality bar.
title: "Sd PRompter"
version: 1.0.0
phase: 8
lesson: 07
tags: [stable-diffusion, flux, latent-diffusion]
category: sd-prompter
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Configure Stable Diffusion / Flux inference for a given prompt, style, and quality bar. |
| **Nerede** | `misc\vision\sd-prompter.md` |
| **Ne Zaman** | Genel AI/ML gorevlerinde |
| **Neden** | Sd Prompter islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Configure Stable Diffusion / Flux inference for a given prompt, style, and quality bar. |
| **Nerede?** | vision/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: AI gelistiricisi
Ne: Configure Stable Diffusion / Flux inference for a given prompt, style, and quality bar.
Nerede: `misc\vision\sd-prompter.md`
Ne Zaman: Genel AI/ML gorevlerinde
Neden: Sd Prompter islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a prompt, target style, and quality bar (fast preview / portfolio quality / print-ready), output:

1. Model + checkpoint. SD 1.5 (legacy tools), SDXL-base + refiner, SDXL-Turbo (fast), SD3.5-Large, Flux.1-dev (best open), Flux.1-schnell (fast open), or a hosted API (DALL-E 3, Imagen 4, Midjourney v7). One-sentence reason.
2. Sampler. Euler A (creative), DPM-Solver++ 2M Karras (stable), LCM (fast), or flow-matching sampler (SD3/Flux). Include step count.
3. CFG scale. 0 for turbo / LCM, 3-4 for Flux, 5-7 for SDXL, 7-10 for SD1.5. Document the trade-off.
4. Add-ons. ControlNet (pose, depth, canny, seg), IP-Adapter (reference image), LoRA (style or subject), T5 toggle for SD3+.
5. Negative prompt. Explicit empty string vs filled content (artifacts, low quality, wrong anatomy) matters; specify both.

Refuse CFG &gt; 10 for SDXL+ (saturated outputs). Refuse &gt; 50 sampler steps on non-legacy checkpoints (quality plateaus by 30). Refuse to mix LoRAs trained on different base models (SD 1.5 LoRA on SDXL is silently broken). Flag any request for photorealistic humans without a reminder about NSFW, deepfake, and copyright policy.
