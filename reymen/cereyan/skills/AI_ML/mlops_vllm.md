---

name: serving-llms-vllm-vllm
description: "vLLM: high-throughput LLM serving, OpenAI API, quantization."
title: "Serving LLMs Vllm"
version: 1.0.0
author: Orchestra Research
license: MIT
dependencies: [vllm, torch, transformers]
platforms: [linux, macos]
metadata:
  hermes:
    tags: [vLLM, Inference Serving, PagedAttention, Continuous Batching, High Throughput, Production, OpenAI API, Quantization, Tensor Parallelism]
category: mlops
audience: user
tags: [ai, machine-learning, mlops]

---


> **Kategori:** mlops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | vLLM: high-throughput LLM serving, OpenAI API, quantization. |
| **Nerede?** | mlops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Vllm

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| When to use | `references/when-to-use.md` |
| Quick start | `references/quick-start.md` |
| Query with OpenAI SDK | `references/query-with-openai-sdk.md` |
| Common workflows | `references/common-workflows.md` |
| For 7B-13B models on single GPU | `references/for-7b-13b-models-on-single-gpu.md` |
| For 30B-70B models with tensor parallelism | `references/for-30b-70b-models-with-tensor-parallelism.md` |
| For production with caching and metrics | `references/for-production-with-caching-and-metrics.md` |
| Install load testing tool | `references/install-load-testing-tool.md` |
| Run: locust -f test_load.py --host http://localhost:8000 | `references/run-locust-f-test_load-py-host-http-localhost-8000.md` |
| Run vLLM in Docker | `references/run-vllm-in-docker.md` |
| Load prompts from file | `references/load-prompts-from-file.md` |
| Process all prompts in one call | `references/process-all-prompts-in-one-call.md` |
| No need to manually chunk prompts | `references/no-need-to-manually-chunk-prompts.md` |
| Extract generated text | `references/extract-generated-text.md` |
| Save to file | `references/save-to-file.md` |
| Example: TheBloke/Llama-2-70B-AWQ | `references/example-thebloke-llama-2-70b-awq.md` |
| Using pre-quantized model | `references/using-pre-quantized-model.md` |
| Results: 70B model in ~40GB VRAM | `references/results-70b-model-in-40gb-vram.md` |
| Verify task-specific performance unchanged | `references/verify-task-specific-performance-unchanged.md` |
| When to use vs alternatives | `references/when-to-use-vs-alternatives.md` |
| Common issues | `references/common-issues.md` |
| Advanced topics | `references/advanced-topics.md` |
| Hardware requirements | `references/hardware-requirements.md` |
| Resources | `references/resources.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
