---

name: comfyui
description: "Generate images, video, and audio with ComfyUI — install, launch, manage nodes/models, run workflows with parameter injection. Uses the official comfy-cli for lifecycle and direct REST/WebSocket API for execution."
title: "ComfyUI"
version: 5.1.0
author: [kshitijk4poor, alt-glitch, purzbeats]
license: MIT
platforms: [macos, linux, windows]
compatibility: "Requires ComfyUI (local, Comfy Desktop, or Comfy Cloud) and comfy-cli (auto-installed via pipx/uvx by the setup script)."
prerequisites:
  commands: ["python3"]
setup:
  help: "Run scripts/hardware_check.py FIRST to decide local vs Comfy Cloud; then scripts/comfyui_setup.sh auto-installs locally (or use Cloud API key for platform.comfy.org)."
metadata:
  hermes:
    tags:
category: creative
      - comfyui
      - image-generation
      - stable-diffusion
      - flux
      - sd3
      - wan-video
      - hunyuan-video
      - creative
      - generative-ai
      - video-generation
related_skills: [stable-diffusion-image-generation, image_gen]
    category: creative
audience: user
tags: [creative, design]
---


> **Kategori:** creative

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Generate images, video, and audio with ComfyUI — install, launch, manage nodes/models, run workflows with parameter injection. Uses the official comfy-cli for lifecycle and direct REST/WebSocket API for execution. |
| **Nerede?** | creative/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Comfyui

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| ComfyUI | `references/comfyui.md` |
| What's in this skill | `references/what-s-in-this-skill.md` |
| When to Use | `references/when-to-use.md` |
| Architecture: Two Layers | `references/architecture-two-layers.md` |
| Quick Start | `references/quick-start.md` |
| What's available? | `references/what-s-available.md` |
| Can this machine run ComfyUI locally? (GPU/VRAM/disk check) | `references/can-this-machine-run-comfyui-locally-gpu-vram-disk-check.md` |
| → JSON: comfy_cli on PATH? server reachable? at least one checkpoint? smoke-test passes? | `references/json-comfy_cli-on-path-server-reachable-at-least-one-checkpo.md` |
| Core Workflow | `references/core-workflow.md` |
| → {"parameter_count": 12, "has_negative_prompt": true, "has_seed": true, ...} | `references/parameter_count-12-has_negative_prompt-true-has_seed-true.md` |
| → full schema with parameters, model deps, embedding refs | `references/full-schema-with-parameters-model-deps-embedding-refs.md` |
| Local (defaults to http://127.0.0.1:8188) | `references/local-defaults-to-http-127-0-0-1-8188.md` |
| Cloud (export API key once; uses correct /api routing automatically) | `references/cloud-export-api-key-once-uses-correct-api-routing-automatic.md` |
| Real-time progress via WebSocket (requires `pip install websocket-client`) | `references/real-time-progress-via-websocket-requires-pip-install-websoc.md` |
| img2img / inpaint: pass --input-image to upload + reference automatically | `references/img2img-inpaint-pass-input-image-to-upload-reference-automat.md` |
| Batch / sweep: 8 random seeds, parallel up to cloud tier limit | `references/batch-sweep-8-random-seeds-parallel-up-to-cloud-tier-limit.md` |
| Decision Tree | `references/decision-tree.md` |
| Setup & Onboarding | `references/setup-onboarding.md` |
| Optional: also probe `torch` for actual CUDA/MPS: | `references/optional-also-probe-torch-for-actual-cuda-mps.md` |
| Or with overrides: | `references/or-with-overrides.md` |
| Or (if pipx/uvx unavailable): | `references/or-if-pipx-uvx-unavailable.md` |
| SDXL (general purpose, ~6.5 GB) | `references/sdxl-general-purpose-6-5-gb.md` |
| SD 1.5 (lighter, ~4 GB, good for 6 GB cards) | `references/sd-1-5-lighter-4-gb-good-for-6-gb-cards.md` |
| Flux Dev fp8 (smaller variant, ~12 GB) | `references/flux-dev-fp8-smaller-variant-12-gb.md` |
| CivitAI (set token first): | `references/civitai-set-token-first.md` |
| → comfy_cli on PATH? server reachable? checkpoints? smoke test? | `references/comfy_cli-on-path-server-reachable-checkpoints-smoke-test.md` |
| → are this workflow's nodes/models/embeddings installed? | `references/are-this-workflow-s-nodes-models-embeddings-installed.md` |
| Image Upload (img2img / Inpainting) | `references/image-upload-img2img-inpainting.md` |
| Cloud equivalent: | `references/cloud-equivalent.md` |
| Cloud Specifics | `references/cloud-specifics.md` |
| Queue & System Management | `references/queue-system-management.md` |
| Local | `references/local.md` |
| Cloud — same paths under /api/, plus: | `references/cloud-same-paths-under-api-plus.md` |
| Pitfalls | `references/pitfalls.md` |
| Verification Checklist | `references/verification-checklist.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
