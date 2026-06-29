---
name: python-testing
description: Python testing strategies using pytest, TDD methodology, fixtures, mocking, parametrization, and coverage requirements.
title: "Python Testing"
origin: ECC

audience: contributor
tags: [ai, automation, development, python, testing]
category: ecc


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI muhendisi |
| **Ne** | Python testing strategies using pytest, TDD methodology, fixtures, mocking, parametrization, and coverage requirements. |
| **Nerede** | `ai\ecc\ecc_python-testing.md` |
| **Ne Zaman** | AI modeli secimi veya degerlendirmesi gerektiginde |
| **Neden** | Ecc Python Testing islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Python testing strategies using pytest, TDD methodology, fixtures, mocking, parametrization, and coverage requirements. |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: AI muhendisi
Ne: Python testing strategies using pytest, TDD methodology, fixtures, mocking, parametrization, and coverage requirements.
Nerede: `ai\ecc\ecc_python-testing.md`
Ne Zaman: AI modeli secimi veya degerlendirmesi gerektiginde
Neden: Ecc Python Testing islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Python Testing

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Python Testing Patterns | `references/python-testing-patterns.md` |
| Test-Kod Sürüklenmesi (Test-Code Drift) | `references/test-code-drift.md` |
| When to Activate | `references/when-to-activate.md` |
| Core Testing Philosophy | `references/core-testing-philosophy.md` |
| Step 1: Write failing test (RED) | `references/step-1-write-failing-test-red.md` |
| Step 2: Write minimal implementation (GREEN) | `references/step-2-write-minimal-implementation-green.md` |
| Step 3: Refactor if needed (REFACTOR) | `references/step-3-refactor-if-needed-refactor.md` |
| pytest Fundamentals | `references/pytest-fundamentals.md` |
| Equality | `references/equality.md` |
| Inequality | `references/inequality.md` |
| Truthiness | `references/truthiness.md` |
| Membership | `references/membership.md` |
| Comparisons | `references/comparisons.md` |
| Type checking | `references/type-checking.md` |
| Exception testing (preferred approach) | `references/exception-testing-preferred-approach.md` |
| Check exception message | `references/check-exception-message.md` |
| Check exception attributes | `references/check-exception-attributes.md` |
| Fixtures | `references/fixtures.md` |
| Setup | `references/setup.md` |
| Teardown | `references/teardown.md` |
| Function scope (default) - runs for each test | `references/function-scope-default-runs-for-each-test.md` |
| Module scope - runs once per module | `references/module-scope-runs-once-per-module.md` |
| Session scope - runs once per test session | `references/session-scope-runs-once-per-test-session.md` |
| reset_config runs automatically | `references/reset_config-runs-automatically.md` |
| tests/conftest.py | `references/tests-conftest-py.md` |
| Parametrization | `references/parametrization.md` |
| Markers and Test Selection | `references/markers-and-test-selection.md` |
| Mark slow tests | `references/mark-slow-tests.md` |
| Mark integration tests | `references/mark-integration-tests.md` |
| Mark unit tests | `references/mark-unit-tests.md` |
| Run only fast tests | `references/run-only-fast-tests.md` |
| Run only integration tests | `references/run-only-integration-tests.md` |
| Run integration or slow tests | `references/run-integration-or-slow-tests.md` |
| Run tests marked as unit but not slow | `references/run-tests-marked-as-unit-but-not-slow.md` |
| Mocking and Patching | `references/mocking-and-patching.md` |
| This would fail if DBConnection doesn't have query method | `references/this-would-fail-if-dbconnection-doesn-t-have-query-method.md` |
| Testing Async Code | `references/testing-async-code.md` |
| Testing Exceptions | `references/testing-exceptions.md` |
| Testing Side Effects | `references/testing-side-effects.md` |
| tmp_path automatically cleaned up | `references/tmp_path-automatically-cleaned-up.md` |
| Test Organization | `references/test-organization.md` |
| Best Practices | `references/best-practices.md` |
| Common Patterns | `references/common-patterns.md` |
| pytest Configuration | `references/pytest-configuration.md` |
| Running Tests | `references/running-tests.md` |
| Run all tests | `references/run-all-tests.md` |
| Run specific file | `references/run-specific-file.md` |
| Run specific test | `references/run-specific-test.md` |
| Run with verbose output | `references/run-with-verbose-output.md` |
| Run with coverage | `references/run-with-coverage.md` |
| Run only fast tests | `references/run-only-fast-tests.md` |
| Run until first failure | `references/run-until-first-failure.md` |
| Run and stop on N failures | `references/run-and-stop-on-n-failures.md` |
| Run last failed tests | `references/run-last-failed-tests.md` |
| Run tests with pattern | `references/run-tests-with-pattern.md` |
| Run with debugger on failure | `references/run-with-debugger-on-failure.md` |
| Pytest Stdout Capture (I/O closed file) | `references/pytest-stdout-capture.md` |
| Quick Reference | `references/quick-reference.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
