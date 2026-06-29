
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ecc_Django Verification |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: django-verification
description: "Verification loop for Django projects: migrations, linting, tests with coverage, security scans, and deployment readiness checks before release or PR."
title: "Django Verification"
origin: ECC

audience: contributor
tags: [ai, automation, development]
category: ecc---

# Django Verification

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Django Verification Loop | `references/django-verification-loop.md` |
| When to Activate | `references/when-to-activate.md` |
| Phase 1: Environment Check | `references/phase-1-environment-check.md` |
| Verify Python version | `references/verify-python-version.md` |
| Check virtual environment | `references/check-virtual-environment.md` |
| Verify environment variables | `references/verify-environment-variables.md` |
| Phase 2: Code Quality & Formatting | `references/phase-2-code-quality-formatting.md` |
| Type checking | `references/type-checking.md` |
| Linting with ruff | `references/linting-with-ruff.md` |
| Formatting with black | `references/formatting-with-black.md` |
| Import sorting | `references/import-sorting.md` |
| Django-specific checks | `references/django-specific-checks.md` |
| Phase 3: Migrations | `references/phase-3-migrations.md` |
| Check for unapplied migrations | `references/check-for-unapplied-migrations.md` |
| Create missing migrations | `references/create-missing-migrations.md` |
| Dry-run migration application | `references/dry-run-migration-application.md` |
| Apply migrations (test environment) | `references/apply-migrations-test-environment.md` |
| Check for migration conflicts | `references/check-for-migration-conflicts.md` |
| Phase 4: Tests + Coverage | `references/phase-4-tests-coverage.md` |
| Run all tests with pytest | `references/run-all-tests-with-pytest.md` |
| Run specific app tests | `references/run-specific-app-tests.md` |
| Run with markers | `references/run-with-markers.md` |
| Coverage report | `references/coverage-report.md` |
| Phase 5: Security Scan | `references/phase-5-security-scan.md` |
| Dependency vulnerabilities | `references/dependency-vulnerabilities.md` |
| Django security checks | `references/django-security-checks.md` |
| Bandit security linter | `references/bandit-security-linter.md` |
| Secret scanning (if gitleaks is installed) | `references/secret-scanning-if-gitleaks-is-installed.md` |
| Environment variable check | `references/environment-variable-check.md` |
| Phase 6: Django Management Commands | `references/phase-6-django-management-commands.md` |
| Check for model issues | `references/check-for-model-issues.md` |
| Collect static files | `references/collect-static-files.md` |
| Create superuser (if needed for tests) | `references/create-superuser-if-needed-for-tests.md` |
| Database integrity | `references/database-integrity.md` |
| Cache verification (if using Redis) | `references/cache-verification-if-using-redis.md` |
| Phase 7: Performance Checks | `references/phase-7-performance-checks.md` |
| Query count analysis | `references/query-count-analysis.md` |
| Check for missing indexes | `references/check-for-missing-indexes.md` |
| Phase 8: Static Assets | `references/phase-8-static-assets.md` |
| Check for npm dependencies (if using npm) | `references/check-for-npm-dependencies-if-using-npm.md` |
| Build static files (if using webpack/vite) | `references/build-static-files-if-using-webpack-vite.md` |
| Verify static files | `references/verify-static-files.md` |
| Phase 9: Configuration Review | `references/phase-9-configuration-review.md` |
| Run in Python shell to verify settings | `references/run-in-python-shell-to-verify-settings.md` |
| Critical checks | `references/critical-checks.md` |
| Phase 10: Logging Configuration | `references/phase-10-logging-configuration.md` |
| Test logging output | `references/test-logging-output.md` |
| Check log files (if configured) | `references/check-log-files-if-configured.md` |
| Phase 11: API Documentation (if DRF) | `references/phase-11-api-documentation-if-drf.md` |
| Generate schema | `references/generate-schema.md` |
| Check if schema.json is valid JSON | `references/check-if-schema-json-is-valid-json.md` |
| Visit http://localhost:8000/swagger/ in browser | `references/visit-http-localhost-8000-swagger-in-browser.md` |
| Phase 12: Diff Review | `references/phase-12-diff-review.md` |
| Show diff statistics | `references/show-diff-statistics.md` |
| Show actual changes | `references/show-actual-changes.md` |
| Show changed files | `references/show-changed-files.md` |
| Check for common issues | `references/check-for-common-issues.md` |
| Output Template | `references/output-template.md` |
| Pre-Deployment Checklist | `references/pre-deployment-checklist.md` |
| Continuous Integration | `references/continuous-integration.md` |
| .github/workflows/django-verification.yml | `references/github-workflows-django-verification-yml.md` |
| Quick Reference | `references/quick-reference.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
