---

name: linear
description: "Linear: manage issues, projects, teams via GraphQL + curl."
title: "Linear"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
prerequisites:
  env_vars: [LINEAR_API_KEY]
  commands: [curl]
metadata:
  hermes:
    tags: [Linear, Project Management, Issues, GraphQL, API, Productivity]
category: productivity
audience: user
tags: [productivity, tools]
---


> **Kategori:** productivity

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Linear: manage issues, projects, teams via GraphQL + curl. |
| **Nerede?** | productivity/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Linear

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Linear — Issue & Project Management | `references/linear-issue-project-management.md` |
| Setup | `references/setup.md` |
| API Basics | `references/api-basics.md` |
| Python helper script (ergonomic alternative) | `references/python-helper-script-ergonomic-alternative.md` |
| Workflow States | `references/workflow-states.md` |
| Common Queries | `references/common-queries.md` |
| Common Mutations | `references/common-mutations.md` |
| Documents | `references/documents.md` |
| Pagination | `references/pagination.md` |
| First page | `references/first-page.md` |
| Next page — use endCursor from previous response | `references/next-page-use-endcursor-from-previous-response.md` |
| Filtering Reference | `references/filtering-reference.md` |
| Typical Workflow | `references/typical-workflow.md` |
| Rate Limits | `references/rate-limits.md` |
| Important Notes | `references/important-notes.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
