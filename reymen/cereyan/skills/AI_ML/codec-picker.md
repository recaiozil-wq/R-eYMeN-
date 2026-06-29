---
name: codec-picker
description: Pick a neural audio codec (EnCodec / DAC / SNAC / Mimi) for a given generative or compression task.
title: "Codec Picker"
version: 1.0.0
phase: 6
lesson: 13
tags: [codec, encodec, dac, snac, mimi, rvq, semantic-tokens]
category: codec-picker
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ML/Veri bilimci |
| **Ne** | Pick a neural audio codec (EnCodec / DAC / SNAC / Mimi) for a given generative or compression task. |
| **Nerede** | `mlops\nlp\codec-picker.md` |
| **Ne Zaman** | ML modeli egitimi veya deploy gerektiginde |
| **Neden** | Codec Picker islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Pick a neural audio codec (EnCodec / DAC / SNAC / Mimi) for a given generative or compression task. |
| **Nerede?** | nlp/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: ML/Veri bilimci
Ne: Pick a neural audio codec (EnCodec / DAC / SNAC / Mimi) for a given generative or compression task.
Nerede: `mlops\nlp\codec-picker.md`
Ne Zaman: ML modeli egitimi veya deploy gerektiginde
Neden: Codec Picker islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given the task (generative LM, compression, full-duplex dialogue, music editing, fidelity target), output:

1. Codec. EnCodec-24k · EnCodec-48k · DAC-44.1k · SNAC-24k · Mimi · (fallback: Opus for non-neural compression). One-sentence reason.
2. Frame rate + codebooks. Bitrate budget, codebook count (usually 4-12), sequence length for target clip duration.
3. Tokenization scheme. Flat vs hierarchical (SNAC) vs semantic+acoustic (Mimi). How the LM consumes tokens.
4. Decoder. In-codec decoder · external vocoder (HiFi-GAN) · LM-only (no vocoder, predict codec tokens directly). Explain why.
5. Training implications. Need to train encoder/decoder? Fine-tune on domain audio (speech-only → domain-specific music)? Frozen off-the-shelf?

Refuse DAC for AR-LM workloads on tight latency budgets — 86 Hz frame rate × 8 codebooks = 5,504 tokens per 10 s, too long for fast generation. Refuse Mimi for music — it's speech-tuned. Refuse EnCodec for semantic-conditional generation — no semantic codebook, blurry speech from text.

Example input: "Build an AR LM for text-to-speech TTS. Target TTFA 200 ms. English only."

Example output:
- Codec: Mimi. Semantic+acoustic split enables text → codebook 0 → codebooks 1-7 factorization, which is both fast and supports voice cloning.
- Frame rate + codebooks: 12.5 Hz · 8 codebooks · 4.4 kbps. 10 s = 1,000 tokens.
- Tokenization: predict codebook 0 first from text + speaker reference; then predict codebooks 1-7 given codebook 0 + speaker reference (depth-transformer pattern).
- Decoder: Mimi's built-in decoder, no external vocoder needed.
- Training: train the text-to-codec LM; freeze Mimi.
