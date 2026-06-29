---

name: systematic-debugging
title: "Systematic Debugging"
tags: [coding, development]
description: "4-phase root cause debugging: understand bugs before fixing."
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, troubleshooting, problem-solving, root-cause, investigation]
audience: contributor
related_skills: [test-driven-development, plan, subagent-driven-development]
---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | 4-phase root cause debugging: understand bugs before fixing. |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Systematic Debugging

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Overview | `references/overview.md` |
| The Iron Law | `references/the-iron-law.md` |
| When to Use | `references/when-to-use.md` |
| The Four Phases | `references/the-four-phases.md` |
| Phase 1: Root Cause Investigation | `references/phase-1-root-cause-investigation.md` |
| Run specific failing test | `references/run-specific-failing-test.md` |
| Run with verbose output | `references/run-with-verbose-output.md` |
| Recent commits | `references/recent-commits.md` |
| Uncommitted changes | `references/uncommitted-changes.md` |
| Changes in specific file | `references/changes-in-specific-file.md` |
| Find where the function is called | `references/find-where-the-function-is-called.md` |
| Find where the variable is set | `references/find-where-the-variable-is-set.md` |
| Phase 2: Pattern Analysis | `references/phase-2-pattern-analysis.md` |
| Phase 3: Hypothesis and Testing | `references/phase-3-hypothesis-and-testing.md` |
| Phase 4: Implementation | `references/phase-4-implementation.md` |
| Run the specific regression test | `references/run-the-specific-regression-test.md` |
| Run full suite — no regressions | `references/run-full-suite-no-regressions.md` |
| Red Flags — STOP and Follow Process | `references/red-flags-stop-and-follow-process.md` |
| Common Rationalizations | `references/common-rationalizations.md` |
| Quick Reference | `references/quick-reference.md` |
| ToolRegistry Resolution Failures | `references/tool-registry-resolution-failures.md` |
| Hermes Agent Integration | `references/hermes-agent-integration.md` |
| Registry Prefix Mismatch & Dead Code | `references/registry-prefix-dead-code.md` |
| Real-World Impact | `references/real-world-impact.md` |
| Import Chain Debugging | `references/module-import-chain-debugging.md` |
| Test-Pattern Mismatch Debugging | `references/test-pattern-mismatch-debugging.md` |
| Fork Sync — Debug After Upstream Merge | `references/fork-sync-test-debugging.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
