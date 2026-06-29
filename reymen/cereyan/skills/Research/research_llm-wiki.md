---

name: llm-wiki
title: "Llm Wiki"
tags: [academic, research]
description: "Karpathy's LLM Wiki: build/query interlinked markdown KB."
version: 2.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [wiki, knowledge-base, research, notes, markdown, rag-alternative]
    category: research
audience: user
related_skills: [obsidian, arxiv]
---


> **Kategori:** research

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Karpathy's LLM Wiki: build/query interlinked markdown KB. |
| **Nerede?** | research/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Llm Wiki

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Karpathy's LLM Wiki | `references/karpathy-s-llm-wiki.md` |
| When This Skill Activates | `references/when-this-skill-activates.md` |
| Wiki Location | `references/wiki-location.md` |
| Architecture: Three Layers | `references/architecture-three-layers.md` |
| Resuming an Existing Wiki (CRITICAL — do this every session) | `references/resuming-an-existing-wiki-critical-do-this-every-session.md` |
| Orientation reads at session start | `references/orientation-reads-at-session-start.md` |
| Initializing a New Wiki | `references/initializing-a-new-wiki.md` |
| Domain | `references/domain.md` |
| Conventions | `references/conventions.md` |
| Frontmatter | `references/frontmatter.md` |
| Optional quality signals: | `references/optional-quality-signals.md` |
| Tag Taxonomy | `references/tag-taxonomy.md` |
| Page Thresholds | `references/page-thresholds.md` |
| Entity Pages | `references/entity-pages.md` |
| Concept Pages | `references/concept-pages.md` |
| Comparison Pages | `references/comparison-pages.md` |
| Update Policy | `references/update-policy.md` |
| Wiki Index | `references/wiki-index.md` |
| Entities | `references/entities.md` |
| Queries | `references/queries.md` |
| Wiki Log | `references/wiki-log.md` |
| [YYYY-MM-DD] create | Wiki initialized | `references/yyyy-mm-dd-create-wiki-initialized.md` |
| Core Operations | `references/core-operations.md` |
| Use execute_code for this — programmatic scan across all wiki pages | `references/use-execute_code-for-this-programmatic-scan-across-all-wiki-.md` |
| Pages with zero inbound links are orphans | `references/pages-with-zero-inbound-links-are-orphans.md` |
| Working with the Wiki | `references/working-with-the-wiki.md` |
| Find pages by content | `references/find-pages-by-content.md` |
| Find pages by filename | `references/find-pages-by-filename.md` |
| Find pages by tag | `references/find-pages-by-tag.md` |
| Recent activity | `references/recent-activity.md` |
| Requires Node.js 22+ | `references/requires-node-js-22.md` |
| Login (requires Obsidian account with Sync subscription) | `references/login-requires-obsidian-account-with-sync-subscription.md` |
| Create a remote vault for the wiki | `references/create-a-remote-vault-for-the-wiki.md` |
| Connect the wiki directory to the vault | `references/connect-the-wiki-directory-to-the-vault.md` |
| Initial sync | `references/initial-sync.md` |
| Continuous sync (foreground — use systemd for background) | `references/continuous-sync-foreground-use-systemd-for-background.md` |
| ~/.config/systemd/user/obsidian-wiki-sync.service | `references/config-systemd-user-obsidian-wiki-sync-service.md` |
| Enable linger so sync survives logout: | `references/enable-linger-so-sync-survives-logout.md` |
| Pitfalls | `references/pitfalls.md` |
| Related Tools | `references/related-tools.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
