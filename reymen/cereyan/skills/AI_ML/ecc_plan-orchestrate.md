
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ecc_Plan Orchestrate |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: plan-orchestrate
description: Read a plan document, decompose it into steps, design a per-step agent chain from the ECC catalogue, and emit ready-to-paste /orchestrate custom prompts. Generative only — never invokes /orchestrate itself. Use when the user has a multi-step plan and wants to drive it through orchestrate without composing chains by hand.
title: "Plan Orchestrate"
origin: ECC

audience: contributor
tags: [ai, automation, development]
category: ecc---

# Plan Orchestrate

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Plan Orchestrate | `references/plan-orchestrate.md` |
| When to Activate | `references/when-to-activate.md` |
| Inputs | `references/inputs.md` |
| Authoritative `/orchestrate` shape (do not deviate) | `references/authoritative-orchestrate-shape-do-not-deviate.md` |
| ECC install form and namespacing | `references/ecc-install-form-and-namespacing.md` |
| Available agent catalogue (must pick from these) | `references/available-agent-catalogue-must-pick-from-these.md` |
| How It Works | `references/how-it-works.md` |
| Plan-Orchestrate Result | `references/plan-orchestrate-result.md` |
| Steps overview | `references/steps-overview.md` |
| Step 1 — <title> | `references/step-1-title.md` |
| Edge cases | `references/edge-cases.md` |
| Examples | `references/examples.md` |
| Step 2 — Encrypt sensitive UserProfile fields | `references/step-2-encrypt-sensitive-userprofile-fields.md` |
| Notes | `references/notes.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
