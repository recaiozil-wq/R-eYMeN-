---

name: airtable
description: Airtable REST API via curl. Records CRUD, filters, upserts.
version: 1.1.0
author: community
license: MIT
platforms: [linux, macos, windows]
prerequisites:
  env_vars: [AIRTABLE_API_KEY]
  commands: [curl]
metadata:
  hermes:
    tags: [Airtable, Productivity, Database, API]
audience: user
    homepage: https://airtable.com/developers/web/api/introduction
---


> **Kategori:** productivity

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Airtable REST API via curl. Records CRUD, filters, upserts. |
| **Nerede?** | productivity/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Airtable

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Airtable — Bases, Tables & Records | `references/airtable-bases-tables-records.md` |
| Prerequisites | `references/prerequisites.md` |
| API Basics | `references/api-basics.md` |
| Field Types (request body shapes) | `references/field-types-request-body-shapes.md` |
| Common Queries | `references/common-queries.md` |
| Common Mutations | `references/common-mutations.md` |
| Pagination | `references/pagination.md` |
| Typical Hermes Workflow | `references/typical-hermes-workflow.md` |
| Pitfalls | `references/pitfalls.md` |
| Important Notes for Hermes | `references/important-notes-for-hermes.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
