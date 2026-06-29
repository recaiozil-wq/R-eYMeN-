---

name: hermes-s6-container-supervision
title: "Hermes S6 Container Supervision"
tags: [ai, coding, development]
description: Modify, debug, or extend the s6-overlay supervision tree inside the Hermes Agent Docker image — adding new services, debugging profile gateways, understanding the Architecture B main-program pattern.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [docker, s6, supervision, gateway, profiles]
audience: contributor
related_skills: [hermes-agent, hermes-agent-dev]
---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Modify, debug, or extend the s6-overlay supervision tree inside the Hermes Agent Docker image — adding new services, debugging profile gateways, understanding the Architecture B main-program pattern. |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Hermes S6 Container Supervision

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| When to use this skill | `references/when-to-use-this-skill.md` |
| Architecture at a glance | `references/architecture-at-a-glance.md` |
| Key files | `references/key-files.md` |
| Why Architecture B (CMD as main program, not s6-supervised) | `references/why-architecture-b-cmd-as-main-program-not-s6-supervised.md` |
| Quick recipes | `references/quick-recipes.md` |
| Expect: s6-svscan or init / /package/admin/s6/.../s6-svscan | `references/expect-s6-svscan-or-init-package-admin-s6-s6-svscan.md` |
| "down … normally up, ready …"     → user stopped it | `references/down-normally-up-ready-user-stopped-it.md` |
| 2026-05-21T06:18:05+0000 profile=writer prior_state=stopped action=registered | `references/2026-05-21t06-18-05-0000-profile-writer-prior_state-stopped-.md` |
| Expect 19 passed, 0 xfailed against the s6 image | `references/expect-19-passed-0-xfailed-against-the-s6-image.md` |
| Common pitfalls | `references/common-pitfalls.md` |
| Related skills | `references/related-skills.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
