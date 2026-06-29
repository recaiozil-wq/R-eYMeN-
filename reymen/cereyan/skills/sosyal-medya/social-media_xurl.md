---

name: xurl
description: "X/Twitter via xurl CLI: post, search, DM, media, v2 API."
version: 1.1.1
author: xdevplatform + openclaw + Hermes Agent
license: MIT
platforms: [linux, macos]
prerequisites:
  commands: [xurl]
metadata:
  hermes:
    tags: [twitter, x, social-media, xurl, official-api]
audience: user
    homepage: https://github.com/xdevplatform/xurl
    upstream_skill: https://github.com/openclaw/openclaw/blob/main/skills/xurl/SKILL.md
---


> **Kategori:** social-media

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | X/Twitter via xurl CLI: post, search, DM, media, v2 API. |
| **Nerede?** | social-media/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Xurl

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| xurl — X (Twitter) API via the Official CLI | `references/xurl-x-twitter-api-via-the-official-cli.md` |
| Secret Safety (MANDATORY) | `references/secret-safety-mandatory.md` |
| Installation | `references/installation.md` |
| Shell script (installs to ~/.local/bin, no sudo, works on Linux + macOS) | `references/shell-script-installs-to-local-bin-no-sudo-works-on-linux-ma.md` |
| Homebrew (macOS) | `references/homebrew-macos.md` |
| npm | `references/npm.md` |
| Go | `references/go.md` |
| One-Time User Setup (user runs these outside the agent) | `references/one-time-user-setup-user-runs-these-outside-the-agent.md` |
| Quick Reference | `references/quick-reference.md` |
| Command Details | `references/command-details.md` |
| Another user's graph | `references/another-user-s-graph.md` |
| Auto-detect type | `references/auto-detect-type.md` |
| Explicit type/category | `references/explicit-type-category.md` |
| Videos need server-side processing — check status (or poll) | `references/videos-need-server-side-processing-check-status-or-poll.md` |
| Full workflow | `references/full-workflow.md` |
| Raw API Access | `references/raw-api-access.md` |
| GET | `references/get.md` |
| POST with JSON body | `references/post-with-json-body.md` |
| DELETE / PUT / PATCH | `references/delete-put-patch.md` |
| Custom headers | `references/custom-headers.md` |
| Force streaming | `references/force-streaming.md` |
| Full URLs also work | `references/full-urls-also-work.md` |
| Global Flags | `references/global-flags.md` |
| Streaming | `references/streaming.md` |
| Output Format | `references/output-format.md` |
| Common Workflows | `references/common-workflows.md` |
| Error Handling | `references/error-handling.md` |
| Agent Workflow | `references/agent-workflow.md` |
| Troubleshooting | `references/troubleshooting.md` |
| Notes | `references/notes.md` |
| Attribution | `references/attribution.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
