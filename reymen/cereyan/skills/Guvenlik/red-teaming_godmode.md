---
name: godmode
title: "Godmode"
tags: [security]
description: "Jailbreak LLMs: Parseltongue, GODMODE, ULTRAPLINIAN."
version: 1.0.0
author: Hermes Agent + Teknium
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [jailbreak, red-teaming, G0DM0D3, Parseltongue, GODMODE, uncensoring, safety-bypass, prompt-engineering, L1B3RT4S]
audience: user
related_skills: [obliteratus]


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | Guvenlik arastirmacisi |
| **Ne** | "Jailbreak LLMs: Parseltongue, GODMODE, ULTRAPLINIAN." |
| **Nerede** | `security\red-teaming_godmode.md` |
| **Ne Zaman** | Guvenlik denetimi veya zafiyet taramasi gerektiginde |
| **Neden** | Red Teaming Godmode islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Jailbreak LLMs: Parseltongue, GODMODE, ULTRAPLINIAN. |
| **Nerede?** | security/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: Guvenlik arastirmacisi
Ne: "Jailbreak LLMs: Parseltongue, GODMODE, ULTRAPLINIAN."
Nerede: `security\red-teaming_godmode.md`
Ne Zaman: Guvenlik denetimi veya zafiyet taramasi gerektiginde
Neden: Red Teaming Godmode islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Godmode

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| G0DM0D3 Jailbreaking Skill | `references/g0dm0d3-jailbreaking-skill.md` |
| When to Use This Skill | `references/when-to-use-this-skill.md` |
| Overview of Attack Modes | `references/overview-of-attack-modes.md` |
| Step 0: Auto-Jailbreak (Recommended) | `references/step-0-auto-jailbreak-recommended.md` |
| In execute_code — use the loader to avoid exec-scoping issues: | `references/in-execute_code-use-the-loader-to-avoid-exec-scoping-issues.md` |
| Auto-detect model from config and jailbreak it | `references/auto-detect-model-from-config-and-jailbreak-it.md` |
| Or specify a model explicitly | `references/or-specify-a-model-explicitly.md` |
| Dry run — test without writing config | `references/dry-run-test-without-writing-config.md` |
| Undo — remove jailbreak settings | `references/undo-remove-jailbreak-settings.md` |
| Step 1: Choose Your Attack Mode | `references/step-1-choose-your-attack-mode.md` |
| Step 2: GODMODE CLASSIC — Quick Start | `references/step-2-godmode-classic-quick-start.md` |
| Step 3: PARSELTONGUE — Obfuscating Queries | `references/step-3-parseltongue-obfuscating-queries.md` |
| Quick one-liner via execute_code | `references/quick-one-liner-via-execute_code.md` |
| Load the parseltongue module | `references/load-the-parseltongue-module.md` |
| Step 4: ULTRAPLINIAN — Multi-Model Racing | `references/step-4-ultraplinian-multi-model-racing.md` |
| Via execute_code | `references/via-execute_code.md` |
| Step 5: Detecting Refusals | `references/step-5-detecting-refusals.md` |
| Step 6: Advanced — Combining Techniques | `references/step-6-advanced-combining-techniques.md` |
| Full pipeline example via execute_code | `references/full-pipeline-example-via-execute_code.md` |
| 1. Jailbreak system prompt | `references/1-jailbreak-system-prompt.md` |
| 2. Prefill priming | `references/2-prefill-priming.md` |
| 3. Parseltongue-encoded query | `references/3-parseltongue-encoded-query.md` |
| Model-Specific Notes | `references/model-specific-notes.md` |
| Trigger Words (Reference) | `references/trigger-words-reference.md` |
| Source Credits | `references/source-credits.md` |
| Tested Results (March 2026) | `references/tested-results-march-2026.md` |
| Common Pitfalls | `references/common-pitfalls.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
