---

name: obliteratus
title: "Obliteratus"
tags: [machine-learning, mlops]
description: "OBLITERATUS: abliterate LLM refusals (diff-in-means)."
version: 2.0.0
author: Hermes Agent
license: MIT
dependencies: [obliteratus, torch, transformers, bitsandbytes, accelerate, safetensors]
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Abliteration, Uncensoring, Refusal-Removal, LLM, Weight-Projection, SVD, Mechanistic-Interpretability, HuggingFace, Model-Surgery]
audience: user
related_skills: [vllm, gguf, huggingface-tokenizers]
---


> **Kategori:** mlops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | OBLITERATUS: abliterate LLM refusals (diff-in-means). |
| **Nerede?** | mlops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Obliteratus

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| What's inside | `references/what-s-inside.md` |
| Video Guide | `references/video-guide.md` |
| When to Use This Skill | `references/when-to-use-this-skill.md` |
| Step 1: Installation | `references/step-1-installation.md` |
| pip install -e ".[spaces]" | `references/pip-install-e-spaces.md` |
| Step 2: Check Hardware | `references/step-2-check-hardware.md` |
| Step 3: Browse Available Models & Get Recommendations | `references/step-3-browse-available-models-get-recommendations.md` |
| Browse models by compute tier | `references/browse-models-by-compute-tier.md` |
| Get architecture info for a specific model | `references/get-architecture-info-for-a-specific-model.md` |
| Get telemetry-driven recommendation for best method & params | `references/get-telemetry-driven-recommendation-for-best-method-params.md` |
| Step 4: Choose a Method | `references/step-4-choose-a-method.md` |
| Step 5: Run Abliteration | `references/step-5-run-abliteration.md` |
| Default method (advanced) — recommended for most models | `references/default-method-advanced-recommended-for-most-models.md` |
| With 4-bit quantization (saves VRAM) | `references/with-4-bit-quantization-saves-vram.md` |
| Large models (70B+) — conservative defaults | `references/large-models-70b-conservative-defaults.md` |
| Interactive guided mode (hardware → model → preset) | `references/interactive-guided-mode-hardware-model-preset.md` |
| Web UI (Gradio) | `references/web-ui-gradio.md` |
| Run a full ablation study from YAML config | `references/run-a-full-ablation-study-from-yaml-config.md` |
| Tournament: pit all methods against each other | `references/tournament-pit-all-methods-against-each-other.md` |
| Step 6: Verify Results | `references/step-6-verify-results.md` |
| Step 7: Use the Abliterated Model | `references/step-7-use-the-abliterated-model.md` |
| Test locally with transformers | `references/test-locally-with-transformers.md` |
| Upload to HuggingFace Hub | `references/upload-to-huggingface-hub.md` |
| Serve with vLLM | `references/serve-with-vllm.md` |
| CLI Command Reference | `references/cli-command-reference.md` |
| Analysis Modules | `references/analysis-modules.md` |
| Run specific analysis modules | `references/run-specific-analysis-modules.md` |
| - causal_tracing: Causally necessary components | `references/causal_tracing-causally-necessary-components.md` |
| Python API only — for user's own projects | `references/python-api-only-for-user-s-own-projects.md` |
| Ablation Strategies | `references/ablation-strategies.md` |
| Evaluation | `references/evaluation.md` |
| Platform Support | `references/platform-support.md` |
| YAML Config Templates | `references/yaml-config-templates.md` |
| Telemetry | `references/telemetry.md` |
| Common Pitfalls | `references/common-pitfalls.md` |
| Complementary Skills | `references/complementary-skills.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
