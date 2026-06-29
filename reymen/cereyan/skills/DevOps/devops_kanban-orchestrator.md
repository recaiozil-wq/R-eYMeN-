---

name: kanban-orchestrator
title: "Kanban Orchestrator"
tags: [automation, devops, system, tor]
description: Decomposition playbook + anti-temptation rules for an orchestrator profile routing work through Kanban. The "don't do the work yourself" rule and the basic lifecycle are auto-injected into every kanban worker's system prompt; this skill is the deeper playbook when you're specifically playing the orchestrator role.
version: 3.0.0
platforms: [linux, macos, windows]
environments: [kanban]
metadata:
  hermes:
    tags: [kanban, multi-agent, orchestration, routing]
audience: maintainer
related_skills: [kanban-worker]
---


> **Kategori:** devops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Decomposition playbook + anti-temptation rules for an orchestrator profile routing work through Kanban. The "don't do the work yourself" rule and the basic lifecycle are auto-injected into every kanban worker's system prompt; this skill is the deeper playbook when you're specifically playing the orchestrator role. |
| **Nerede?** | devops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Kanban Orchestrator

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Kanban Orchestrator — Decomposition Playbook | `references/kanban-orchestrator-decomposition-playbook.md` |
| Profiles are user-configured — not a fixed roster | `references/profiles-are-user-configured-not-a-fixed-roster.md` |
| When to use the board (vs. just doing the work) | `references/when-to-use-the-board-vs-just-doing-the-work.md` |
| The anti-temptation rules | `references/the-anti-temptation-rules.md` |
| Decomposition playbook | `references/decomposition-playbook.md` |
| Common patterns | `references/common-patterns.md` |
| Pitfalls | `references/pitfalls.md` |
| Goal-mode cards (persistent workers) | `references/goal-mode-cards-persistent-workers.md` |
| Recovering stuck workers | `references/recovering-stuck-workers.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
