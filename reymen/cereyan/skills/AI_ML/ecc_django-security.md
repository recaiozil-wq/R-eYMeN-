
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ecc_Django Security |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: django-security
description: Django security best practices, authentication, authorization, CSRF protection, SQL injection prevention, XSS prevention, and secure deployment configurations.
title: "Django Security"
origin: ECC

audience: contributor
tags: [ai, automation, development, security]
category: ecc---

# Django Security

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Django Security Best Practices | `references/django-security-best-practices.md` |
| When to Activate | `references/when-to-activate.md` |
| Core Security Settings | `references/core-security-settings.md` |
| settings/production.py | `references/settings-production-py.md` |
| Security headers | `references/security-headers.md` |
| HTTPS and Cookies | `references/https-and-cookies.md` |
| Secret key (must be set via environment variable) | `references/secret-key-must-be-set-via-environment-variable.md` |
| Password validation | `references/password-validation.md` |
| Authentication | `references/authentication.md` |
| apps/users/models.py | `references/apps-users-models-py.md` |
| settings/base.py | `references/settings-base-py.md` |
| Django uses PBKDF2 by default. For stronger security: | `references/django-uses-pbkdf2-by-default-for-stronger-security.md` |
| Session configuration | `references/session-configuration.md` |
| Authorization | `references/authorization.md` |
| models.py | `references/models-py.md` |
| views.py | `references/views-py.md` |
| permissions.py | `references/permissions-py.md` |
| Read permissions allowed for any request | `references/read-permissions-allowed-for-any-request.md` |
| Write permissions only for owner | `references/write-permissions-only-for-owner.md` |
| models.py | `references/models-py.md` |
| Mixins | `references/mixins.md` |
| SQL Injection Prevention | `references/sql-injection-prevention.md` |
| GOOD: Django ORM automatically escapes parameters | `references/good-django-orm-automatically-escapes-parameters.md` |
| GOOD: Using parameters with raw() | `references/good-using-parameters-with-raw.md` |
| BAD: Never directly interpolate user input | `references/bad-never-directly-interpolate-user-input.md` |
| GOOD: Using filter with proper escaping | `references/good-using-filter-with-proper-escaping.md` |
| GOOD: Using Q objects for complex queries | `references/good-using-q-objects-for-complex-queries.md` |
| If you must use raw SQL, always use parameters | `references/if-you-must-use-raw-sql-always-use-parameters.md` |
| XSS Prevention | `references/xss-prevention.md` |
| BAD: Never mark user input as safe without escaping | `references/bad-never-mark-user-input-as-safe-without-escaping.md` |
| GOOD: Escape first, then mark safe | `references/good-escape-first-then-mark-safe.md` |
| GOOD: Use format_html for HTML with variables | `references/good-use-format_html-for-html-with-variables.md` |
| settings.py | `references/settings-py.md` |
| Custom middleware | `references/custom-middleware.md` |
| CSRF Protection | `references/csrf-protection.md` |
| settings.py - CSRF is enabled by default | `references/settings-py-csrf-is-enabled-by-default.md` |
| Template usage | `references/template-usage.md` |
| AJAX requests | `references/ajax-requests.md` |
| Webhook from external service | `references/webhook-from-external-service.md` |
| File Upload Security | `references/file-upload-security.md` |
| models.py | `references/models-py.md` |
| settings.py | `references/settings-py.md` |
| Use a separate domain for media in production | `references/use-a-separate-domain-for-media-in-production.md` |
| Use a separate server or S3 for media files | `references/use-a-separate-server-or-s3-for-media-files.md` |
| API Security | `references/api-security.md` |
| settings.py | `references/settings-py.md` |
| Custom throttle | `references/custom-throttle.md` |
| settings.py | `references/settings-py.md` |
| views.py | `references/views-py.md` |
| Security Headers | `references/security-headers.md` |
| settings.py | `references/settings-py.md` |
| Middleware | `references/middleware.md` |
| Environment Variables | `references/environment-variables.md` |
| Use python-decouple or django-environ | `references/use-python-decouple-or-django-environ.md` |
| set casting, default value | `references/set-casting-default-value.md` |
| reading .env file | `references/reading-env-file.md` |
| .env file (never commit this) | `references/env-file-never-commit-this.md` |
| Logging Security Events | `references/logging-security-events.md` |
| settings.py | `references/settings-py.md` |
| Quick Security Checklist | `references/quick-security-checklist.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
