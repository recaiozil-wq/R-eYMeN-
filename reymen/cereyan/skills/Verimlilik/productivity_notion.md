---

name: notion
description: "Notion API + ntn CLI: pages, databases, markdown, Workers."
version: 2.0.0
author: community
license: MIT
platforms: [linux, macos, windows]
prerequisites:
  env_vars: [NOTION_API_KEY]
metadata:
  hermes:
    tags: [Notion, Productivity, Notes, Database, API, CLI, Workers]
audience: user
    homepage: https://developers.notion.com
---


> **Kategori:** productivity

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Notion API + ntn CLI: pages, databases, markdown, Workers. |
| **Nerede?** | productivity/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Notion

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Notion | `references/notion.md` |
| Setup | `references/setup.md` |
| Recommended | `references/recommended.md` |
| Or via npm (needs Node 22+, npm 10+) | `references/or-via-npm-needs-node-22-npm-10.md` |
| fall back to curl | `references/fall-back-to-curl.md` |
| API Basics | `references/api-basics.md` |
| Path A — `ntn` CLI (preferred, macOS / Linux) | `references/path-a-ntn-cli-preferred-macos-linux.md` |
| Path B — HTTP + curl (cross-platform, default on Windows) | `references/path-b-http-curl-cross-platform-default-on-windows.md` |
| 1. Create upload | `references/1-create-upload.md` |
| 2. PUT bytes to the upload_url returned above | `references/2-put-bytes-to-the-upload_url-returned-above.md` |
| 3. Reference {file_upload_id} in a page/block payload | `references/3-reference-file_upload_id-in-a-page-block-payload.md` |
| Property Types | `references/property-types.md` |
| API Version 2025-09-03 — Databases vs Data Sources | `references/api-version-2025-09-03-databases-vs-data-sources.md` |
| Notion Workers (advanced, requires `ntn`) | `references/notion-workers-advanced-requires-ntn.md` |
| Edit src/index.ts | `references/edit-src-index-ts.md` |
| Notion-Flavored Markdown (used by `/markdown` endpoints) | `references/notion-flavored-markdown-used-by-markdown-endpoints.md` |
| Choosing the Right Path | `references/choosing-the-right-path.md` |
| Notes | `references/notes.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
