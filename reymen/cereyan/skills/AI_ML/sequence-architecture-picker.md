---
name: sequence-architecture-picker
description: Pick sequence architecture (RNN, transformer, SSM, hybrid) given length, throughput, and training budget.
title: "Sequence Architecture Picker"
version: 1.0.0
phase: 7
lesson: 1
tags: [transformers, architecture, rnn, ssm]
category: sequence-architecture-picker
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ML/Veri bilimci |
| **Ne** | Pick sequence architecture (RNN, transformer, SSM, hybrid) given length, throughput, and training budget. |
| **Nerede** | `mlops\nlp\sequence-architecture-picker.md` |
| **Ne Zaman** | ML modeli egitimi veya deploy gerektiginde |
| **Neden** | Sequence Architecture Picker islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Pick sequence architecture (RNN, transformer, SSM, hybrid) given length, throughput, and training budget. |
| **Nerede?** | nlp/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: ML/Veri bilimci
Ne: Pick sequence architecture (RNN, transformer, SSM, hybrid) given length, throughput, and training budget.
Nerede: `mlops\nlp\sequence-architecture-picker.md`
Ne Zaman: ML modeli egitimi veya deploy gerektiginde
Neden: Sequence Architecture Picker islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a sequence problem (max length, batch shape, training tokens budgeted, inference latency target, device class), output:

1. Primary architecture. One of: transformer, state-space model (Mamba/RWKV), hybrid SSM+attention, RNN. One-sentence reason tied to the dominant constraint.
2. Context length strategy. If transformer: full attention cutoff, sliding window size, RoPE scaling factor. If SSM: scan chunk size. If RNN: hidden width.
3. Training FLOP profile. Approximate FLOPs per token from architecture + context; note whether the spec fits the compute budget.
4. Inference memory profile. KV cache for transformers, state size for SSMs, per-token memory for RNNs. Flag if the target device can hold a single batch of 1.
5. Risk note. One specific failure mode that this choice is known to have at the scale of the spec (e.g. transformer OOM at 64K context on a 24GB GPU without Flash Attention).

Refuse to recommend a pure RNN for any training run above 1B tokens without explicitly stating the gradient-flow and parallelism penalties. Refuse to recommend a full-attention transformer for >64K context without stating the `O(N^2)` memory cost. Refuse to recommend a brand-new architecture (published <12 months ago) for production without a named fallback.
