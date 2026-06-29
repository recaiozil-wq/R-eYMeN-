
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ecc_Python Patterns |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: python-patterns
description: Pythonic idioms, PEP 8 standards, type hints, and best practices for building robust, efficient, and maintainable Python applications.
title: "Python Patterns"
origin: ECC

audience: contributor
tags: [ai, automation, development, python]
category: ecc---

# Python Patterns

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Python Development Patterns | `references/python-development-patterns.md` |
| When to Activate | `references/when-to-activate.md` |
| Core Principles | `references/core-principles.md` |
| Good: Clear and readable | `references/good-clear-and-readable.md` |
| Bad: Clever but confusing | `references/bad-clever-but-confusing.md` |
| Good: Explicit configuration | `references/good-explicit-configuration.md` |
| Bad: Hidden side effects | `references/bad-hidden-side-effects.md` |
| Good: EAFP style | `references/good-eafp-style.md` |
| Bad: LBYL (Look Before You Leap) style | `references/bad-lbyl-look-before-you-leap-style.md` |
| Type Hints | `references/type-hints.md` |
| Python 3.9+ - Use built-in types | `references/python-3-9-use-built-in-types.md` |
| Python 3.8 and earlier - Use typing module | `references/python-3-8-and-earlier-use-typing-module.md` |
| Type alias for complex types | `references/type-alias-for-complex-types.md` |
| Generic types | `references/generic-types.md` |
| Error Handling Patterns | `references/error-handling-patterns.md` |
| Good: Catch specific exceptions | `references/good-catch-specific-exceptions.md` |
| Bad: Bare except | `references/bad-bare-except.md` |
| Chain exceptions to preserve the traceback | `references/chain-exceptions-to-preserve-the-traceback.md` |
| Usage | `references/usage.md` |
| Context Managers | `references/context-managers.md` |
| Good: Using context managers | `references/good-using-context-managers.md` |
| Bad: Manual resource management | `references/bad-manual-resource-management.md` |
| Usage | `references/usage.md` |
| Usage | `references/usage.md` |
| Comprehensions and Generators | `references/comprehensions-and-generators.md` |
| Good: List comprehension for simple transformations | `references/good-list-comprehension-for-simple-transformations.md` |
| Bad: Manual loop | `references/bad-manual-loop.md` |
| Bad: Too complex | `references/bad-too-complex.md` |
| Good: Use a generator function | `references/good-use-a-generator-function.md` |
| Good: Generator for lazy evaluation | `references/good-generator-for-lazy-evaluation.md` |
| Bad: Creates large intermediate list | `references/bad-creates-large-intermediate-list.md` |
| Usage | `references/usage.md` |
| Data Classes and Named Tuples | `references/data-classes-and-named-tuples.md` |
| Usage | `references/usage.md` |
| Validate email format | `references/validate-email-format.md` |
| Validate age range | `references/validate-age-range.md` |
| Usage | `references/usage.md` |
| Decorators | `references/decorators.md` |
| slow_function() prints: slow_function took 1.0012s | `references/slow_function-prints-slow_function-took-1-0012s.md` |
| greet("Alice") returns ["Hello, Alice!", "Hello, Alice!", "Hello, Alice!"] | `references/greet-alice-returns-hello-alice-hello-alice-hello-alice.md` |
| Each call to process() prints the call count | `references/each-call-to-process-prints-the-call-count.md` |
| Concurrency Patterns | `references/concurrency-patterns.md` |
| Package Organization | `references/package-organization.md` |
| Good: Import order - stdlib, third-party, local | `references/good-import-order-stdlib-third-party-local.md` |
| pip install isort | `references/pip-install-isort.md` |
| mypackage/__init__.py | `references/mypackage-__init__-py.md` |
| Export main classes/functions at package level | `references/export-main-classes-functions-at-package-level.md` |
| Memory and Performance | `references/memory-and-performance.md` |
| Bad: Regular class uses __dict__ (more memory) | `references/bad-regular-class-uses-__dict__-more-memory.md` |
| Good: __slots__ reduces memory usage | `references/good-__slots__-reduces-memory-usage.md` |
| Bad: Returns full list in memory | `references/bad-returns-full-list-in-memory.md` |
| Good: Yields lines one at a time | `references/good-yields-lines-one-at-a-time.md` |
| Bad: O(n²) due to string immutability | `references/bad-o-n-due-to-string-immutability.md` |
| Good: O(n) using join | `references/good-o-n-using-join.md` |
| Good: Using StringIO for building | `references/good-using-stringio-for-building.md` |
| Python Tooling Integration | `references/python-tooling-integration.md` |
| Code formatting | `references/code-formatting.md` |
| Linting | `references/linting.md` |
| Type checking | `references/type-checking.md` |
| Testing | `references/testing.md` |
| Security scanning | `references/security-scanning.md` |
| Dependency management | `references/dependency-management.md` |
| Quick Reference: Python Idioms | `references/quick-reference-python-idioms.md` |
| Anti-Patterns to Avoid | `references/anti-patterns-to-avoid.md` |
| Bad: Mutable default arguments | `references/bad-mutable-default-arguments.md` |
| Good: Use None and create new list | `references/good-use-none-and-create-new-list.md` |
| Bad: Checking type with type() | `references/bad-checking-type-with-type.md` |
| Good: Use isinstance | `references/good-use-isinstance.md` |
| Bad: Comparing to None with == | `references/bad-comparing-to-none-with.md` |
| Good: Use is | `references/good-use-is.md` |
| Bad: from module import * | `references/bad-from-module-import.md` |
| Good: Explicit imports | `references/good-explicit-imports.md` |
| Bad: Bare except | `references/bad-bare-except.md` |
| Good: Specific exception | `references/good-specific-exception.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
