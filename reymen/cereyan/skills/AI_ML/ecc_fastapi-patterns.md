
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ecc_Fastapi Patterns |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: fastapi-patterns
description: FastAPI best practices covering project structure, Pydantic v2 schemas, dependency injection, async handlers, authentication, authorization, transactional service layers, and testing with httpx and pytest.
title: "FastAPI Patterns"
origin: ECC

audience: contributor
tags: [ai, api, automation, development]
category: ecc---

# Fastapi Patterns

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| FastAPI Patterns | `references/fastapi-patterns.md` |
| Project Structure | `references/project-structure.md` |
| App Factory and Lifespan | `references/app-factory-and-lifespan.md` |
| app/main.py | `references/app-main-py.md` |
| For strict production applications, manage schemas via Alembic migrations instead. | `references/for-strict-production-applications-manage-schemas-via-alembi.md` |
| Shutdown: close pooled resources. | `references/shutdown-close-pooled-resources.md` |
| Configuration with pydantic-settings | `references/configuration-with-pydantic-settings.md` |
| app/config.py | `references/app-config-py.md` |
| Pydantic-settings v2 safely evaluates mutable list literals directly | `references/pydantic-settings-v2-safely-evaluates-mutable-list-literals-.md` |
| Pydantic Schemas (v2) | `references/pydantic-schemas-v2.md` |
| app/schemas/user.py | `references/app-schemas-user-py.md` |
| Dependency Injection | `references/dependency-injection.md` |
| app/dependencies.py | `references/app-dependencies-py.md` |
| Router and Endpoint Design | `references/router-and-endpoint-design.md` |
| app/routers/users.py | `references/app-routers-users-py.md` |
| Service Layer | `references/service-layer.md` |
| app/services/user_service.py | `references/app-services-user_service-py.md` |
| Rely on atomic DB constraints rather than race-prone application-level prechecks | `references/rely-on-atomic-db-constraints-rather-than-race-prone-applica.md` |
| Enforce explicit deterministic ordering to ensure reliable pagination | `references/enforce-explicit-deterministic-ordering-to-ensure-reliable-p.md` |
| Testing with httpx and pytest | `references/testing-with-httpx-and-pytest.md` |
| tests/conftest.py | `references/tests-conftest-py.md` |
| Anti-Patterns | `references/anti-patterns.md` |
| Bad: business logic inside route handlers. | `references/bad-business-logic-inside-route-handlers.md` |
| Good: thin route, transactional service handling. | `references/good-thin-route-transactional-service-handling.md` |
| Bad: sync DB calls in async routes block the event loop. | `references/bad-sync-db-calls-in-async-routes-block-the-event-loop.md` |
| Good: use async SQLAlchemy executions. | `references/good-use-async-sqlalchemy-executions.md` |
| Best Practices | `references/best-practices.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
