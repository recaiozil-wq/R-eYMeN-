
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ecc_Gan Style Harness |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: gan-style-harness
description: "GAN-inspired Generator-Evaluator agent harness for building high-quality applications autonomously. Based on Anthropic's March 2026 harness design paper."
title: "Gan Style Harness"
origin: ECC-community
tools: Read, Write, Edit, Bash, Grep, Glob, Task

audience: user
tags: [ai, automation, development]
category: ecc---

# Gan Style Harness

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| GAN-Style Harness Skill | `references/gan-style-harness-skill.md` |
| Core Insight | `references/core-insight.md` |
| When to Use | `references/when-to-use.md` |
| When NOT to Use | `references/when-not-to-use.md` |
| Architecture | `references/architecture.md` |
| The Three Agents | `references/the-three-agents.md` |
| Evaluation Criteria | `references/evaluation-criteria.md` |
| Evaluation Rubric | `references/evaluation-rubric.md` |
| Usage | `references/usage.md` |
| Full three-agent harness | `references/full-three-agent-harness.md` |
| With custom config | `references/with-custom-config.md` |
| Frontend design mode (generator + evaluator only, no planner) | `references/frontend-design-mode-generator-evaluator-only-no-planner.md` |
| Basic usage | `references/basic-usage.md` |
| With options | `references/with-options.md` |
| Step 1: Plan | `references/step-1-plan.md` |
| Step 2: Generate (iteration 1) | `references/step-2-generate-iteration-1.md` |
| Step 3: Evaluate (iteration 1) | `references/step-3-evaluate-iteration-1.md` |
| Step 4: Generate (iteration 2 — reads feedback) | `references/step-4-generate-iteration-2-reads-feedback.md` |
| Repeat steps 3-4 until pass threshold met | `references/repeat-steps-3-4-until-pass-threshold-met.md` |
| Evolution Across Model Capabilities | `references/evolution-across-model-capabilities.md` |
| Configuration | `references/configuration.md` |
| Anti-Patterns | `references/anti-patterns.md` |
| Results: What to Expect | `references/results-what-to-expect.md` |
| References | `references/references.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
