
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ecc_Perl Testing |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: perl-testing
description: "Perl testing patterns using Test2::V0, Test::More, prove runner, mocking, coverage with Devel::Cover, and TDD methodology."
title: "Perl Testing"
origin: ECC

audience: contributor
tags: [ai, automation, development, testing]
category: ecc---

# Perl Testing

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Perl Testing Patterns | `references/perl-testing-patterns.md` |
| When to Activate | `references/when-to-activate.md` |
| TDD Workflow | `references/tdd-workflow.md` |
| t/unit/calculator.t | `references/t-unit-calculator-t.md` |
| lib/Calculator.pm | `references/lib-calculator-pm.md` |
| Run: prove -lv t/unit/calculator.t | `references/run-prove-lv-t-unit-calculator-t.md` |
| Test::More Fundamentals | `references/test-more-fundamentals.md` |
| Equality | `references/equality.md` |
| Boolean | `references/boolean.md` |
| Deep comparison | `references/deep-comparison.md` |
| Pattern matching | `references/pattern-matching.md` |
| Type check | `references/type-check.md` |
| Skip tests conditionally | `references/skip-tests-conditionally.md` |
| Mark expected failures | `references/mark-expected-failures.md` |
| Test2::V0 Modern Framework | `references/test2-v0-modern-framework.md` |
| Hash builder — check partial structure | `references/hash-builder-check-partial-structure.md` |
| Ignore other fields | `references/ignore-other-fields.md` |
| Array builder | `references/array-builder.md` |
| Bag — order-independent comparison | `references/bag-order-independent-comparison.md` |
| Test that code dies | `references/test-that-code-dies.md` |
| Test that code lives | `references/test-that-code-lives.md` |
| Combined pattern | `references/combined-pattern.md` |
| Test Organization and prove | `references/test-organization-and-prove.md` |
| Run all tests | `references/run-all-tests.md` |
| Verbose output | `references/verbose-output.md` |
| Run specific test | `references/run-specific-test.md` |
| Recursive search | `references/recursive-search.md` |
| Parallel execution (8 jobs) | `references/parallel-execution-8-jobs.md` |
| Run only failing tests from last run | `references/run-only-failing-tests-from-last-run.md` |
| Colored output with timer | `references/colored-output-with-timer.md` |
| TAP output for CI | `references/tap-output-for-ci.md` |
| Fixtures and Setup/Teardown | `references/fixtures-and-setup-teardown.md` |
| Setup | `references/setup.md` |
| Test | `references/test.md` |
| Teardown happens automatically (CLEANUP => 1) | `references/teardown-happens-automatically-cleanup-1.md` |
| Mocking | `references/mocking.md` |
| Good: Mock returns controlled data | `references/good-mock-returns-controlled-data.md` |
| Verify call count | `references/verify-call-count.md` |
| Mock is automatically restored when $mock goes out of scope | `references/mock-is-automatically-restored-when-mock-goes-out-of-scope.md` |
| *MyApp::API::fetch_user = sub { ... };  NEVER — leaks across tests | `references/myapp-api-fetch_user-sub-never-leaks-across-tests.md` |
| Coverage with Devel::Cover | `references/coverage-with-devel-cover.md` |
| Basic coverage report | `references/basic-coverage-report.md` |
| Or step by step | `references/or-step-by-step.md` |
| HTML report | `references/html-report.md` |
| Specific thresholds | `references/specific-thresholds.md` |
| CI-friendly: fail under threshold | `references/ci-friendly-fail-under-threshold.md` |
| Best Practices | `references/best-practices.md` |
| Quick Reference | `references/quick-reference.md` |
| Common Pitfalls | `references/common-pitfalls.md` |
| Bad: Test file runs but doesn't verify all tests executed | `references/bad-test-file-runs-but-doesn-t-verify-all-tests-executed.md` |
| Good: Always end with done_testing | `references/good-always-end-with-done_testing.md` |
| Good: Include lib/ in @INC | `references/good-include-lib-in-inc.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
