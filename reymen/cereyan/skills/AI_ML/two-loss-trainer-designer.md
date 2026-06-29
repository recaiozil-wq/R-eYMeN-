---
name: two-loss-trainer-designer
description: Design a Transfusion / MMDiT-style two-loss training setup (NTP on one modality, diffusion on another) with loss weights, mask design, and schedule.
title: "Two Loss Trainer Designer"
version: 1.0.0
phase: 12
lesson: 13
tags: [transfusion, mmdit, two-loss, flow-matching, hybrid-attention]
category: two-loss-trainer-designer
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ML/Veri bilimci |
| **Ne** | Design a Transfusion / MMDiT-style two-loss training setup (NTP on one modality, diffusion on another) with loss weights, mask design, and schedule. |
| **Nerede** | `mlops\training\two-loss-trainer-designer.md` |
| **Ne Zaman** | ML modeli egitimi veya deploy gerektiginde |
| **Neden** | Two Loss Trainer Designer islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Design a Transfusion / MMDiT-style two-loss training setup (NTP on one modality, diffusion on another) with loss weights, mask design, and schedule. |
| **Nerede?** | training/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: ML/Veri bilimci
Ne: Design a Transfusion / MMDiT-style two-loss training setup (NTP on one modality, diffusion on another) with loss weights, mask design, and schedule.
Nerede: `mlops\training\two-loss-trainer-designer.md`
Ne Zaman: ML modeli egitimi veya deploy gerektiginde
Neden: Two Loss Trainer Designer islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a multimodal training spec (two modalities, which gets NTP and which gets diffusion, target model scale, target sample length), design a working two-loss setup.

Produce:

1. Modality split. Which tokens are discrete (NTP) and which are continuous (diffusion). Justify by content type (text always discrete; images, audio, video can go either way).
2. Attention mask. Draw the block-triangular mask for an example sequence. Specify bidirectional regions and causal regions.
3. Loss weights. Starting weights for (text_loss, image_loss). Recommend tuning by target gradient-norm ratio. Cite Transfusion's ~0.1 default.
4. Flow-matching vs DDPM. Pick the diffusion variant; flow matching for simpler math, rectified flow for fewer inference steps.
5. Inference plan. NTP path (autoregressive sampling over text) + diffusion path (conditional denoise over image patches). Specify denoise steps (10-30).
6. MMDiT vs Transfusion split. When to add modality-specific block weights (MMDiT) vs share fully (Transfusion); rule of thumb by parameter count.

Hard rejects:
- Claiming one mask fits all sequences. Each sample has a different image span and needs its own block-triangular mask.
- Using DDPM without rectified flow or flow matching. Both need fewer inference steps and are simpler to tune.
- Balancing losses by fixed weight without measuring gradient-norm ratio.

Refusal rules:
- If user wants only understanding (image in, text out), refuse and recommend LLaVA-style late fusion (Lesson 12.05). Two-loss is for generation.
- If user wants <1B model, refuse two-loss and recommend discrete tokens (Chameleon) — at small scale the diffusion head underfits.
- If user cannot afford dual inference (NTP + diffusion loops), refuse and recommend Show-o (discrete diffusion, single loop) or Emu3.

Output: one-page design with modality split, mask diagram, loss weights, flow variant, inference plan, and MMDiT-vs-shared decision. End with arXiv 2408.11039 (Transfusion) and 2403.03206 (SD3) for canonical references.
