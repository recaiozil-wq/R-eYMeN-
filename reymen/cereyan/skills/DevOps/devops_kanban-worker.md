---

name: kanban-worker
title: "Kanban Worker"
tags: [automation, devops, system]
description: Pitfalls, examples, and edge cases for Hermes Kanban workers. The lifecycle itself is auto-injected into every worker's system prompt as KANBAN_GUIDANCE (from agent/prompt_builder.py); this skill is what you load when you want deeper detail on specific scenarios.
version: 2.0.0
platforms: [linux, macos, windows]
environments: [kanban]
metadata:
  hermes:
    tags: [kanban, multi-agent, collaboration, workflow, pitfalls]
audience: maintainer
related_skills: [kanban-orchestrator]
---


> **Kategori:** devops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Pitfalls, examples, and edge cases for Hermes Kanban workers. The lifecycle itself is auto-injected into every worker's system prompt as KANBAN_GUIDANCE (from agent/prompt_builder.py); this skill is what you load when you want deeper detail on specific scenarios. |
| **Nerede?** | devops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Kanban Worker

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Kanban Worker — Pitfalls and Examples | `references/kanban-worker-pitfalls-and-examples.md` |
| Workspace handling | `references/workspace-handling.md` |
| Tenant isolation | `references/tenant-isolation.md` |
| Good summary + metadata shapes | `references/good-summary-metadata-shapes.md` |
| Claiming cards you actually created | `references/claiming-cards-you-actually-created.md` |
| GOOD — capture return values, then claim them. | `references/good-capture-return-values-then-claim-them.md` |
| BAD — claiming ids you don't have captured return values for. | `references/bad-claiming-ids-you-don-t-have-captured-return-values-for.md` |
| Block reasons that get answered fast | `references/block-reasons-that-get-answered-fast.md` |
| Heartbeats worth sending | `references/heartbeats-worth-sending.md` |
| Retry scenarios | `references/retry-scenarios.md` |
| Notification routing | `references/notification-routing.md` |
| Do NOT | `references/do-not.md` |
| Pitfalls | `references/pitfalls.md` |
| CLI fallback (for scripting) | `references/cli-fallback-for-scripting.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
