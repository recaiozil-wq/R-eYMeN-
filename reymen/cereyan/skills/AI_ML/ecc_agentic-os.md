
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ecc_Agentic Os |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: agentic-os
description: Build persistent multi-agent operating systems on Claude Code. Covers kernel architecture, specialist agents, slash commands, file-based memory, scheduled automation, and state management without external databases.
title: "Agentic OS"
origin: ECC

audience: user
tags: [ai, automation, development]
category: ecc---

# Agentic Os

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Agentic OS | `references/agentic-os.md` |
| When to Activate | `references/when-to-activate.md` |
| Architecture Overview | `references/architecture-overview.md` |
| The Kernel | `references/the-kernel.md` |
| Identity | `references/identity.md` |
| Agent Registry | `references/agent-registry.md` |
| Routing Rules | `references/routing-rules.md` |
| Model Policies | `references/model-policies.md` |
| Specialist Agents | `references/specialist-agents.md` |
| Identity | `references/identity.md` |
| Memory Scope | `references/memory-scope.md` |
| Tool Access | `references/tool-access.md` |
| Constraints | `references/constraints.md` |
| Commands and Daily Workflows | `references/commands-and-daily-workflows.md` |
| /daily-sync | `references/daily-sync.md` |
| Persistent Memory | `references/persistent-memory.md` |
| Sessions | `references/sessions.md` |
| Decisions | `references/decisions.md` |
| Blockers | `references/blockers.md` |
| Next Actions | `references/next-actions.md` |
| Reflection - Session 3 | `references/reflection-session-3.md` |
| Scheduled Automation | `references/scheduled-automation.md` |
| ~/.config/systemd/user/agentic-daily-sync.service | `references/config-systemd-user-agentic-daily-sync-service.md` |
| ~/.config/systemd/user/agentic-daily-sync.timer | `references/config-systemd-user-agentic-daily-sync-timer.md` |
| ecosystem.config.js | `references/ecosystem-config-js.md` |
| Data Layer | `references/data-layer.md` |
| Anti-Patterns | `references/anti-patterns.md` |
| BAD - One agent does everything | `references/bad-one-agent-does-everything.md` |
| BAD - No memory between sessions | `references/bad-no-memory-between-sessions.md` |
| BAD - API keys in agent files or CLAUDE.md | `references/bad-api-keys-in-agent-files-or-claude-md.md` |
| BAD - PostgreSQL for a solo user's agentic OS | `references/bad-postgresql-for-a-solo-user-s-agentic-os.md` |
| BAD - Routing logic in code instead of markdown tables | `references/bad-routing-logic-in-code-instead-of-markdown-tables.md` |
| Best Practices | `references/best-practices.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
