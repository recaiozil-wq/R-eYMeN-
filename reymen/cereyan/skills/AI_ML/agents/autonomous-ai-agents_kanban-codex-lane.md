---
name: kanban-codex-lane
title: "Kanban Codex Lane"
tags: [agents, ai]
description: Use when a Hermes Kanban worker wants to run Codex CLI as an isolated implementation lane while Hermes keeps ownership of task lifecycle, reconciliation, testing, and handoff.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [kanban, codex, worktrees, autonomous-agents, prediction-market-bot]
audience: user
related_skills: [kanban-worker, codex, hermes-agent]


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Use when a Hermes Kanban worker wants to run Codex CLI as an isolated implementation lane while Hermes keeps ownership of task lifecycle, reconciliation, testing, and handoff. |
| **Nerede** | `autonomous-ai-agents\autonomous-ai-agents_kanban-codex-lane.md` |
| **Ne Zaman** | Ilgili gorev gerektiginde |
| **Neden** | Autonomous Ai Agents Kanban Codex Lane islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Use when a Hermes Kanban worker wants to run Codex CLI as an isolated implementation lane while Hermes keeps ownership of task lifecycle, reconciliation, testing, and handoff. |
| **Nerede?** | autonomous-ai-agents/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: Otonom ajan gelistiricisi
Ne: Use when a Hermes Kanban worker wants to run Codex CLI as an isolated implementation lane while Hermes keeps ownership of task lifecycle, reconciliation, testing, and handoff.
Nerede: `autonomous-ai-agents\autonomous-ai-agents_kanban-codex-lane.md`
Ne Zaman: Ilgili gorev gerektiginde
Neden: Autonomous Ai Agents Kanban Codex Lane islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Kanban Codex Lane

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Overview | `references/overview.md` |
| When to Use | `references/when-to-use.md` |
| Ownership Rules | `references/ownership-rules.md` |
| Required Worktree and Branch Pattern | `references/required-worktree-and-branch-pattern.md` |
| Codex Capability Checks | `references/codex-capability-checks.md` |
| Mode Selection | `references/mode-selection.md` |
| Prompt Construction | `references/prompt-construction.md` |
| Monitoring, Timeout, and Kill Behavior | `references/monitoring-timeout-and-kill-behavior.md` |
| Reconciliation Checklist | `references/reconciliation-checklist.md` |
| kanban_complete Metadata Schema | `references/kanban_complete-metadata-schema.md` |
| Common Pitfalls | `references/common-pitfalls.md` |
| Verification Checklist | `references/verification-checklist.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
