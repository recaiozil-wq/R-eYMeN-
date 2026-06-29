---
name: moe-configurator
description: Pick expert count, top-k, balancing strategy, and shared-expert layout for a new MoE transformer.
title: "Moe Configurator"
version: 1.0.0
phase: 7
lesson: 11
tags: [transformers, moe, mixture-of-experts, scaling]
category: moe-configurator
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Pick expert count, top-k, balancing strategy, and shared-expert layout for a new MoE transformer. |
| **Nerede** | `misc\architecture\moe-configurator.md` |
| **Ne Zaman** | Genel AI/ML gorevlerinde |
| **Neden** | Moe Configurator islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Pick expert count, top-k, balancing strategy, and shared-expert layout for a new MoE transformer. |
| **Nerede?** | architecture/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: AI gelistiricisi
Ne: Pick expert count, top-k, balancing strategy, and shared-expert layout for a new MoE transformer.
Nerede: `misc\architecture\moe-configurator.md`
Ne Zaman: Genel AI/ML gorevlerinde
Neden: Moe Configurator islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a transformer spec (total parameter budget, desired active params per token, training tokens available, inference hardware), output:

1. MoE layout. `n_experts`, `top_k`, `n_shared`. Pick fine-grained (256+ experts, top-8) for frontier scales; classic (8 experts, top-2) for smaller. One-sentence reason.
2. Balancing strategy. Auxiliary-loss-free (DeepSeek-V3, default), Switch-style auxiliary loss, or expert-capacity + token drop. Name the `γ` value if aux-loss-free.
3. Expert parallelism plan. How to shard experts across GPUs given VRAM. State per-expert VRAM cost and total fleet size.
4. Routing precision. fp32 router scores vs fp16. Router precision matters at scale.
5. Failure mode check. Named risk: router collapse, expert starvation, all-to-all network bottleneck, inference latency from routing overhead, checkpoint memory footprint.

Refuse to recommend MoE for active-parameter counts below 4B — dense wins at matched compute. Refuse auxiliary-loss-only balancing for new projects in 2026 (aux-loss-free is the default). Refuse to ship an MoE without an expert-parallel plan if total params exceed 80 GB. Flag MoE for latency-critical single-user paths as likely slower than dense equivalents.
