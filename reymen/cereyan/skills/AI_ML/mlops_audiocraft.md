---

name: audiocraft-audio-generation
description: "AudioCraft: MusicGen text-to-music, AudioGen text-to-sound."
title: "Audiocraft Audio Generation"
version: 1.0.0
author: Orchestra Research
license: MIT
dependencies: [audiocraft, torch>=2.0.0, transformers>=4.30.0]
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Multimodal, Audio Generation, Text-to-Music, Text-to-Audio, MusicGen]
category: mlops
audience: user
tags: [ai, audio, machine-learning, mlops]

---


> **Kategori:** mlops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | AudioCraft: MusicGen text-to-music, AudioGen text-to-sound. |
| **Nerede?** | mlops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Audiocraft

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| AudioCraft: Audio Generation | `references/audiocraft-audio-generation.md` |
| When to use AudioCraft | `references/when-to-use-audiocraft.md` |
| Quick start | `references/quick-start.md` |
| From PyPI | `references/from-pypi.md` |
| From GitHub (latest) | `references/from-github-latest.md` |
| Or use HuggingFace Transformers | `references/or-use-huggingface-transformers.md` |
| Load model | `references/load-model.md` |
| Set generation parameters | `references/set-generation-parameters.md` |
| Generate from text | `references/generate-from-text.md` |
| Save audio | `references/save-audio.md` |
| Load model and processor | `references/load-model-and-processor.md` |
| Generate music | `references/generate-music.md` |
| Save | `references/save.md` |
| Load AudioGen | `references/load-audiogen.md` |
| Generate sound effects | `references/generate-sound-effects.md` |
| Core concepts | `references/core-concepts.md` |
| MusicGen usage | `references/musicgen-usage.md` |
| Configure generation | `references/configure-generation.md` |
| Generate multiple samples | `references/generate-multiple-samples.md` |
| Generate (returns [batch, channels, samples]) | `references/generate-returns-batch-channels-samples.md` |
| Save each | `references/save-each.md` |
| Load melody model | `references/load-melody-model.md` |
| Load melody audio | `references/load-melody-audio.md` |
| Generate with melody conditioning | `references/generate-with-melody-conditioning.md` |
| Load stereo model | `references/load-stereo-model.md` |
| wav shape: [batch, 2, samples] for stereo | `references/wav-shape-batch-2-samples-for-stereo.md` |
| Load audio to continue | `references/load-audio-to-continue.md` |
| Process with text and audio | `references/process-with-text-and-audio.md` |
| Generate continuation | `references/generate-continuation.md` |
| MusicGen-Style usage | `references/musicgen-style-usage.md` |
| Load style model | `references/load-style-model.md` |
| Configure generation with style | `references/configure-generation-with-style.md` |
| Configure style conditioner | `references/configure-style-conditioner.md` |
| Load style reference | `references/load-style-reference.md` |
| Generate with text + style | `references/generate-with-text-style.md` |
| Generate matching style without text prompt | `references/generate-matching-style-without-text-prompt.md` |
| AudioGen usage | `references/audiogen-usage.md` |
| Generate various sounds | `references/generate-various-sounds.md` |
| EnCodec usage | `references/encodec-usage.md` |
| Load EnCodec | `references/load-encodec.md` |
| Load audio | `references/load-audio.md` |
| Ensure correct sample rate | `references/ensure-correct-sample-rate.md` |
| Encode to tokens | `references/encode-to-tokens.md` |
| Decode back to audio | `references/decode-back-to-audio.md` |
| Common workflows | `references/common-workflows.md` |
| Usage | `references/usage.md` |
| Usage | `references/usage.md` |
| Save to temp file | `references/save-to-temp-file.md` |
| Performance optimization | `references/performance-optimization.md` |
| Use smaller model | `references/use-smaller-model.md` |
| Clear cache between generations | `references/clear-cache-between-generations.md` |
| Generate shorter durations | `references/generate-shorter-durations.md` |
| Use half precision | `references/use-half-precision.md` |
| Process multiple prompts at once (more efficient) | `references/process-multiple-prompts-at-once-more-efficient.md` |
| Instead of | `references/instead-of.md` |
| Common issues | `references/common-issues.md` |
| References | `references/references.md` |
| Resources | `references/resources.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
