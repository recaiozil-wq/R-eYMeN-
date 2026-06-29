
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ecc_Prisma Patterns |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: prisma-patterns
description: Prisma ORM patterns for TypeScript backends — schema design, query optimization, transactions, pagination, and critical traps like updateMany returning count not records, $transaction timeouts, migrate dev resetting the DB, @updatedAt skipped on bulk writes, and serverless connection exhaustion.
title: "PRisma Patterns"
origin: ECC

audience: contributor
tags: [ai, automation, development]
category: ecc---

# Prisma Patterns

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Prisma Patterns | `references/prisma-patterns.md` |
| When to Activate | `references/when-to-activate.md` |
| Core Concepts | `references/core-concepts.md` |
| Code Examples | `references/code-examples.md` |
| .env — preferred: embed params in the URL | `references/env-preferred-embed-params-in-the-url.md` |
| With an external pooler (PgBouncer, Supabase pooler) | `references/with-an-external-pooler-pgbouncer-supabase-pooler.md` |
| Anti-Patterns | `references/anti-patterns.md` |
| NEVER on shared dev, staging, or production | `references/never-on-shared-dev-staging-or-production.md` |
| Safe everywhere except local solo dev | `references/safe-everywhere-except-local-solo-dev.md` |
| Check drift without applying | `references/check-drift-without-applying.md` |
| Step 1: create migration locally, then deploy | `references/step-1-create-migration-locally-then-deploy.md` |
| Step 3: create the NOT NULL constraint migration locally, then deploy | `references/step-3-create-the-not-null-constraint-migration-locally-then.md` |
| Best Practices | `references/best-practices.md` |
| Related Skills | `references/related-skills.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
