---
name: vit-configurator
description: Pick a ViT variant, patch size, and pretraining source for a new vision task.
title: "ViT Configurator"
version: 1.0.0
phase: 7
lesson: 9
tags: [transformers, vit, vision]
category: vit-configurator
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Pick a ViT variant, patch size, and pretraining source for a new vision task. |
| **Nerede** | `misc\vision\vit-configurator.md` |
| **Ne Zaman** | Genel AI/ML gorevlerinde |
| **Neden** | Vit Configurator islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Pick a ViT variant, patch size, and pretraining source for a new vision task. |
| **Nerede?** | vision/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: AI gelistiricisi
Ne: Pick a ViT variant, patch size, and pretraining source for a new vision task.
Nerede: `misc\vision\vit-configurator.md`
Ne Zaman: Genel AI/ML gorevlerinde
Neden: Vit Configurator islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a vision task (classification / segmentation / detection / retrieval), image resolution, dataset size (labeled + unlabeled), and deployment target, output:

1. Backbone. One of: DINOv2 ViT-L/14 (default for retrieval/classification), SAM 3 encoder (segmentation), SigLIP (vision-language), ConvNeXt (latency-critical). One-sentence reason.
2. Patch size. 16 for standard classification at 224, 14 for DINOv2, 8 for dense prediction at high res. Flag sequence length `(H/P)^2 + 1` and attention cost `O(N^2)`.
3. Pretraining source. Checkpoint name. For small labeled sets (<10k): DINOv2 features frozen + linear probe. For >100k: fine-tune last blocks. State why.
4. Training recipe. Optimizer (AdamW), lr, augmentations (RandAug, MixUp, Random Erasing), label smoothing (0.1 typical), EMA.
5. Risk note. Data regime risk (too little data for full fine-tune), resolution mismatch (pretrain 224 → deploy 1024 without position interpolation), register-token absence (may hurt DINOv2 features).

Refuse to recommend training a ViT from scratch on less than 1M images — CNN baselines will win. Refuse to recommend patch size that yields sequence length > 4096 without explicit discussion of Flash Attention + hierarchical variants (Swin). Flag any deployment that changes input resolution without interpolating positional embeddings.
