---

name: evaluating-llms-harness
description: "lm-eval-harness: benchmark LLMs (MMLU, GSM8K, etc.)."
title: "Evaluating LLMs Harness"
version: 1.0.0
author: Orchestra Research
license: MIT
dependencies: [lm-eval, transformers, vllm]
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Evaluation, LM Evaluation Harness, Benchmarking, MMLU, HumanEval, GSM8K, EleutherAI, Model Quality, Academic Benchmarks, Industry Standard]
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
| **Ne?** | lm-eval-harness: benchmark LLMs (MMLU, GSM8K, etc.). |
| **Nerede?** | mlops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Lm Evaluation Harness

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| What's inside | `references/what-s-inside.md` |
| Quick start | `references/quick-start.md` |
| Common workflows | `references/common-workflows.md` |
| Full MMLU evaluation (57 subjects) | `references/full-mmlu-evaluation-57-subjects.md` |
| Multiple benchmarks at once | `references/multiple-benchmarks-at-once.md` |
| eval_checkpoint.sh | `references/eval_checkpoint-sh.md` |
| In training loop | `references/in-training-loop.md` |
| Run evaluation | `references/run-evaluation.md` |
| Save checkpoint | `references/save-checkpoint.md` |
| Run lm-eval | `references/run-lm-eval.md` |
| Load all results | `references/load-all-results.md` |
| Plot | `references/plot.md` |
| models.txt | `references/models-txt.md` |
| eval_all_models.sh | `references/eval_all_models-sh.md` |
| Extract model name for output file | `references/extract-model-name-for-output-file.md` |
| Get primary metric for each task | `references/get-primary-metric-for-each-task.md` |
| Standard HF: ~2 hours for MMLU on 7B model | `references/standard-hf-2-hours-for-mmlu-on-7b-model.md` |
| vLLM: ~15-20 minutes for MMLU on 7B model | `references/vllm-15-20-minutes-for-mmlu-on-7b-model.md` |
| When to use vs alternatives | `references/when-to-use-vs-alternatives.md` |
| Common issues | `references/common-issues.md` |
| Advanced topics | `references/advanced-topics.md` |
| Hardware requirements | `references/hardware-requirements.md` |
| Resources | `references/resources.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
