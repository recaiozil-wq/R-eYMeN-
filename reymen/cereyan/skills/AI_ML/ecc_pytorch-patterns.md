
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ecc_Pytorch Patterns |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: pytorch-patterns
description: PyTorch deep learning patterns and best practices for building robust, efficient, and reproducible training pipelines, model architectures, and data loading.
title: "PyTorch Patterns"
origin: ECC

audience: user
tags: [ai, automation, development, tor]
category: ecc---

# Pytorch Patterns

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| PyTorch Development Patterns | `references/pytorch-development-patterns.md` |
| When to Activate | `references/when-to-activate.md` |
| Core Principles | `references/core-principles.md` |
| Good: Device-agnostic | `references/good-device-agnostic.md` |
| Bad: Hardcoded device | `references/bad-hardcoded-device.md` |
| Good: Full reproducibility setup | `references/good-full-reproducibility-setup.md` |
| Bad: No seed control | `references/bad-no-seed-control.md` |
| x: (batch_size, channels, height, width) | `references/x-batch_size-channels-height-width.md` |
| Bad: No shape tracking | `references/bad-no-shape-tracking.md` |
| Model Architecture Patterns | `references/model-architecture-patterns.md` |
| Good: Well-organized module | `references/good-well-organized-module.md` |
| Bad: Everything in forward | `references/bad-everything-in-forward.md` |
| Good: Explicit initialization | `references/good-explicit-initialization.md` |
| Training Loop Patterns | `references/training-loop-patterns.md` |
| Good: Complete training loop with best practices | `references/good-complete-training-loop-with-best-practices.md` |
| Mixed precision training | `references/mixed-precision-training.md` |
| Good: Proper evaluation | `references/good-proper-evaluation.md` |
| Data Pipeline Patterns | `references/data-pipeline-patterns.md` |
| Good: Clean Dataset with type hints | `references/good-clean-dataset-with-type-hints.md` |
| Good: Optimized DataLoader | `references/good-optimized-dataloader.md` |
| Bad: Slow defaults | `references/bad-slow-defaults.md` |
| Good: Pad sequences in collate_fn | `references/good-pad-sequences-in-collate_fn.md` |
| Pad to max length in batch | `references/pad-to-max-length-in-batch.md` |
| Checkpointing Patterns | `references/checkpointing-patterns.md` |
| Good: Complete checkpoint with all training state | `references/good-complete-checkpoint-with-all-training-state.md` |
| Bad: Only saving model weights (can't resume training) | `references/bad-only-saving-model-weights-can-t-resume-training.md` |
| Performance Optimization | `references/performance-optimization.md` |
| Good: AMP with GradScaler | `references/good-amp-with-gradscaler.md` |
| Good: Trade compute for memory | `references/good-trade-compute-for-memory.md` |
| Recompute activations during backward to save memory | `references/recompute-activations-during-backward-to-save-memory.md` |
| Good: Compile the model for faster execution (PyTorch 2.0+) | `references/good-compile-the-model-for-faster-execution-pytorch-2-0.md` |
| Modes: "default" (safe), "reduce-overhead" (faster), "max-autotune" (fastest) | `references/modes-default-safe-reduce-overhead-faster-max-autotune-faste.md` |
| Quick Reference: PyTorch Idioms | `references/quick-reference-pytorch-idioms.md` |
| Anti-Patterns to Avoid | `references/anti-patterns-to-avoid.md` |
| Bad: Forgetting model.eval() during validation | `references/bad-forgetting-model-eval-during-validation.md` |
| Good: Always set eval mode | `references/good-always-set-eval-mode.md` |
| Bad: In-place operations breaking autograd | `references/bad-in-place-operations-breaking-autograd.md` |
| Good: Out-of-place operations | `references/good-out-of-place-operations.md` |
| Bad: Moving data to GPU inside the training loop repeatedly | `references/bad-moving-data-to-gpu-inside-the-training-loop-repeatedly.md` |
| Good: Move model once before the loop | `references/good-move-model-once-before-the-loop.md` |
| Bad: Using .item() before backward | `references/bad-using-item-before-backward.md` |
| Good: Call .item() only for logging | `references/good-call-item-only-for-logging.md` |
| Bad: Not using torch.save properly | `references/bad-not-using-torch-save-properly.md` |
| Good: Save state_dict | `references/good-save-state_dict.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
