
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ecc_Santa Method |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: santa-method
description: "Multi-agent adversarial verification with convergence loop. Two independent review agents must both pass before output ships."
title: "Santa Method"
origin: "Ronald Skelton - Founder, RapportScore.ai"

audience: contributor
tags: [ai, automation, development]
category: ecc---

# Santa Method

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Santa Method | `references/santa-method.md` |
| When to Activate | `references/when-to-activate.md` |
| Architecture | `references/architecture.md` |
| Phase Details | `references/phase-details.md` |
| The generator runs as normal | `references/the-generator-runs-as-normal.md` |
| Task Specification | `references/task-specification.md` |
| Output Under Review | `references/output-under-review.md` |
| Evaluation Rubric | `references/evaluation-rubric.md` |
| Instructions | `references/instructions.md` |
| Spawn reviewers in parallel (Claude Code subagents) | `references/spawn-reviewers-in-parallel-claude-code-subagents.md` |
| Both run concurrently — neither sees the other | `references/both-run-concurrently-neither-sees-the-other.md` |
| Merge flags from both reviewers, deduplicate | `references/merge-flags-from-both-reviewers-deduplicate.md` |
| Fix all critical issues (suggestions are optional) | `references/fix-all-critical-issues-suggestions-are-optional.md` |
| Re-run BOTH reviewers on fixed output (fresh agents, no memory of previous round) | `references/re-run-both-reviewers-on-fixed-output-fresh-agents-no-memory.md` |
| Exhausted iterations — escalate | `references/exhausted-iterations-escalate.md` |
| Implementation Patterns | `references/implementation-patterns.md` |
| Both agents run in parallel for speed | `references/both-agents-run-in-parallel-for-speed.md` |
| Pseudocode for Agent tool invocation | `references/pseudocode-for-agent-tool-invocation.md` |
| Failure Modes and Mitigations | `references/failure-modes-and-mitigations.md` |
| Integration with Other Skills | `references/integration-with-other-skills.md` |
| Metrics | `references/metrics.md` |
| Cost Analysis | `references/cost-analysis.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
