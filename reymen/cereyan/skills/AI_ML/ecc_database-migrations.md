
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ecc_Database Migrations |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: database-migrations
description: Database migration best practices for schema changes, data migrations, rollbacks, and zero-downtime deployments across PostgreSQL, MySQL, and common ORMs (Prisma, Drizzle, Kysely, Django, TypeORM, golang-migrate).
title: "Database Migrations"
origin: ECC

audience: contributor
tags: [ai, automation, database, development]
category: ecc---

# Database Migrations

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Database Migration Patterns | `references/database-migration-patterns.md` |
| When to Activate | `references/when-to-activate.md` |
| Core Principles | `references/core-principles.md` |
| Migration Safety Checklist | `references/migration-safety-checklist.md` |
| PostgreSQL Patterns | `references/postgresql-patterns.md` |
| Prisma (TypeScript/Node.js) | `references/prisma-typescript-node-js.md` |
| Create migration from schema changes | `references/create-migration-from-schema-changes.md` |
| Apply pending migrations in production | `references/apply-pending-migrations-in-production.md` |
| Reset database (dev only) | `references/reset-database-dev-only.md` |
| Generate client after schema changes | `references/generate-client-after-schema-changes.md` |
| Create empty migration, then edit the SQL manually | `references/create-empty-migration-then-edit-the-sql-manually.md` |
| Drizzle (TypeScript/Node.js) | `references/drizzle-typescript-node-js.md` |
| Generate migration from schema changes | `references/generate-migration-from-schema-changes.md` |
| Apply migrations | `references/apply-migrations.md` |
| Push schema directly (dev only, no migration file) | `references/push-schema-directly-dev-only-no-migration-file.md` |
| Kysely (TypeScript/Node.js) | `references/kysely-typescript-node-js.md` |
| Initialize config file (kysely.config.ts) | `references/initialize-config-file-kysely-config-ts.md` |
| Create a new migration file | `references/create-a-new-migration-file.md` |
| Apply all pending migrations | `references/apply-all-pending-migrations.md` |
| Rollback last migration | `references/rollback-last-migration.md` |
| Show migration status | `references/show-migration-status.md` |
| Django (Python) | `references/django-python.md` |
| Generate migration from model changes | `references/generate-migration-from-model-changes.md` |
| Apply migrations | `references/apply-migrations.md` |
| Show migration status | `references/show-migration-status.md` |
| Generate empty migration for custom SQL | `references/generate-empty-migration-for-custom-sql.md` |
| golang-migrate (Go) | `references/golang-migrate-go.md` |
| Create migration pair | `references/create-migration-pair.md` |
| Apply all pending migrations | `references/apply-all-pending-migrations.md` |
| Rollback last migration | `references/rollback-last-migration.md` |
| Force version (fix dirty state) | `references/force-version-fix-dirty-state.md` |
| Zero-Downtime Migration Strategy | `references/zero-downtime-migration-strategy.md` |
| Anti-Patterns | `references/anti-patterns.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
