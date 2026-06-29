
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ecc_Autonomous Loops |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: autonomous-loops
description: "Patterns and architectures for autonomous Claude Code loops — from simple sequential pipelines to RFC-driven multi-agent DAG systems."
title: "Autonomous Loops"
origin: ECC

audience: contributor
tags: [ai, automation, development]
category: ecc---

# Autonomous Loops

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Autonomous Loops Skill | `references/autonomous-loops-skill.md` |
| When to Use | `references/when-to-use.md` |
| Loop Pattern Spectrum | `references/loop-pattern-spectrum.md` |
| 1. Sequential Pipeline (`claude -p`) | `references/1-sequential-pipeline-claude-p.md` |
| daily-dev.sh — Sequential pipeline for a feature branch | `references/daily-dev-sh-sequential-pipeline-for-a-feature-branch.md` |
| Step 1: Implement the feature | `references/step-1-implement-the-feature.md` |
| Step 2: De-sloppify (cleanup pass) | `references/step-2-de-sloppify-cleanup-pass.md` |
| Step 3: Verify | `references/step-3-verify.md` |
| Step 4: Commit | `references/step-4-commit.md` |
| Research with Opus (deep reasoning) | `references/research-with-opus-deep-reasoning.md` |
| Implement with Sonnet (fast, capable) | `references/implement-with-sonnet-fast-capable.md` |
| Review with Opus (thorough) | `references/review-with-opus-thorough.md` |
| Pass context via files, not prompt length | `references/pass-context-via-files-not-prompt-length.md` |
| Read-only analysis pass | `references/read-only-analysis-pass.md` |
| Write-only implementation pass | `references/write-only-implementation-pass.md` |
| 2. NanoClaw REPL | `references/2-nanoclaw-repl.md` |
| Start the default session | `references/start-the-default-session.md` |
| Named session with skill context | `references/named-session-with-skill-context.md` |
| 3. Infinite Agentic Loop | `references/3-infinite-agentic-loop.md` |
| 4. Continuous Claude PR Loop | `references/4-continuous-claude-pr-loop.md` |
| Basic: 10 iterations | `references/basic-10-iterations.md` |
| Cost-limited | `references/cost-limited.md` |
| Time-boxed | `references/time-boxed.md` |
| With code review pass | `references/with-code-review-pass.md` |
| Parallel via worktrees | `references/parallel-via-worktrees.md` |
| Progress | `references/progress.md` |
| Next Steps | `references/next-steps.md` |
| 5. The De-Sloppify Pattern | `references/5-the-de-sloppify-pattern.md` |
| Step 1: Implement (let it be thorough) | `references/step-1-implement-let-it-be-thorough.md` |
| Step 2: De-sloppify (separate context, focused cleanup) | `references/step-2-de-sloppify-separate-context-focused-cleanup.md` |
| Implement | `references/implement.md` |
| De-sloppify | `references/de-sloppify.md` |
| Verify | `references/verify.md` |
| Commit | `references/commit.md` |
| 6. Ralphinho / RFC-Driven DAG Orchestration | `references/6-ralphinho-rfc-driven-dag-orchestration.md` |
| MERGE CONFLICT — RESOLVE BEFORE NEXT LANDING | `references/merge-conflict-resolve-before-next-landing.md` |
| Choosing the Right Pattern | `references/choosing-the-right-pattern.md` |
| Simple formatting fix | `references/simple-formatting-fix.md` |
| Complex architectural change | `references/complex-architectural-change.md` |
| Anti-Patterns | `references/anti-patterns.md` |
| References | `references/references.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
