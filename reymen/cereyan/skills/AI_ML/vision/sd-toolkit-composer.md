---
name: sd-toolkit-composer
description: Compose ControlNets, LoRAs, and IP-Adapters on top of an SD / Flux base for a given set of inputs.
title: "Sd Toolkit Composer"
version: 1.0.0
phase: 8
lesson: 08
tags: [controlnet, lora, ip-adapter, diffusion]
category: sd-toolkit-composer
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Compose ControlNets, LoRAs, and IP-Adapters on top of an SD / Flux base for a given set of inputs. |
| **Nerede** | `misc\vision\sd-toolkit-composer.md` |
| **Ne Zaman** | Genel AI/ML gorevlerinde |
| **Neden** | Sd Toolkit Composer islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Compose ControlNets, LoRAs, and IP-Adapters on top of an SD / Flux base for a given set of inputs. |
| **Nerede?** | vision/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: AI gelistiricisi
Ne: Compose ControlNets, LoRAs, and IP-Adapters on top of an SD / Flux base for a given set of inputs.
Nerede: `misc\vision\sd-toolkit-composer.md`
Ne Zaman: Genel AI/ML gorevlerinde
Neden: Sd Toolkit Composer islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a task (target image), inputs (prompt, reference image, pose / depth / scribble / seg, subject identity), and base model (SDXL, SD3.5, Flux.1-dev), output:

1. ControlNet stack. Which ControlNets (canny / openpose / depth / scribble / seg / lineart / tile), at what weight, in what order. Max sum of weights &lt;= 1.5.
2. LoRA stack. Named LoRAs, rank, alpha. Warn when alpha &gt; 1.5 or multiple LoRAs target the same concept.
3. IP-Adapter. None, plain, or FaceID variant; weight 0.4-0.8 typical.
4. Text prompt + negative prompt. Keyword order, token budget, negative scaffolding.
5. Sampler + CFG + seed. Euler A / DPM-Solver++ / LCM; CFG scale tied to base. Reproducible seed protocol.
6. QA checklist. Visual check for ControlNet drift, LoRA over-saturation, IP-Adapter identity leak, anatomy issues.

Refuse to stack a SD 1.5 LoRA on an SDXL base (dimension mismatch). Refuse to run 3+ ControlNets at weight 1.0 each (feature collision). Flag any SD 1.5 recommendation when the user has GPU budget for SDXL or Flux. Flag LoRA identity training on &lt; 10 images as likely to overfit.
