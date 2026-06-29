---

name: google-workspace
description: "Gmail, Calendar, Drive, Docs, Sheets via gws CLI or Python."
version: 1.1.0
author: Nous Research
license: MIT
platforms: [linux, macos, windows]
required_credential_files:
  - path: google_token.json
    description: Google OAuth2 token (created by setup script)
  - path: google_client_secret.json
    description: Google OAuth2 client credentials (downloaded from Google Cloud Console)
metadata:
  hermes:
    tags: [Google, Gmail, Calendar, Drive, Sheets, Docs, Contacts, Email, OAuth]
audience: user
    homepage: https://github.com/NousResearch/hermes-agent
related_skills: [himalaya]
---


> **Kategori:** productivity

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Gmail, Calendar, Drive, Docs, Sheets via gws CLI or Python. |
| **Nerede?** | productivity/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Google Workspace

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Google Workspace | `references/google-workspace.md` |
| References | `references/references.md` |
| Scripts | `references/scripts.md` |
| First-Time Setup | `references/first-time-setup.md` |
| Usage | `references/usage.md` |
| Search (returns JSON array with id, from, subject, date, snippet) | `references/search-returns-json-array-with-id-from-subject-date-snippet.md` |
| Read full message (returns JSON with body text) | `references/read-full-message-returns-json-with-body-text.md` |
| Send | `references/send.md` |
| Reply (automatically threads and sets In-Reply-To) | `references/reply-automatically-threads-and-sets-in-reply-to.md` |
| Labels | `references/labels.md` |
| List events (defaults to next 7 days) | `references/list-events-defaults-to-next-7-days.md` |
| Create event (ISO 8601 with timezone required) | `references/create-event-iso-8601-with-timezone-required.md` |
| Delete event | `references/delete-event.md` |
| Search existing files | `references/search-existing-files.md` |
| Get metadata for a single file | `references/get-metadata-for-a-single-file.md` |
| Upload a local file (auto-detects MIME type) | `references/upload-a-local-file-auto-detects-mime-type.md` |
| sensible default — Docs→pdf, Sheets→csv, Slides→pdf, Drawings→png) | `references/sensible-default-docs-pdf-sheets-csv-slides-pdf-drawings-png.md` |
| Create a folder | `references/create-a-folder.md` |
| Share | `references/share.md` |
| Delete — defaults to trash (reversible). Use --permanent to skip the trash. | `references/delete-defaults-to-trash-reversible-use-permanent-to-skip-th.md` |
| Create a new spreadsheet | `references/create-a-new-spreadsheet.md` |
| Read | `references/read.md` |
| Write | `references/write.md` |
| Append rows | `references/append-rows.md` |
| Read | `references/read.md` |
| Create a new Doc (optionally seeded with body text) | `references/create-a-new-doc-optionally-seeded-with-body-text.md` |
| Append text to the end of an existing Doc | `references/append-text-to-the-end-of-an-existing-doc.md` |
| Output Format | `references/output-format.md` |
| Rules | `references/rules.md` |
| Troubleshooting | `references/troubleshooting.md` |
| Revoking Access | `references/revoking-access.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
