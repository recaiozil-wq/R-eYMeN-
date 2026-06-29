
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ecc_Perl Patterns |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: perl-patterns
description: Modern Perl 5.36+ idioms, best practices, and conventions for building robust, maintainable Perl applications.
title: "Perl Patterns"
origin: ECC

audience: contributor
tags: [ai, automation, development]
category: ecc---

# Perl Patterns

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Modern Perl Development Patterns | `references/modern-perl-development-patterns.md` |
| When to Activate | `references/when-to-activate.md` |
| How It Works | `references/how-it-works.md` |
| Core Principles | `references/core-principles.md` |
| Good: Modern preamble | `references/good-modern-preamble.md` |
| Bad: Legacy boilerplate | `references/bad-legacy-boilerplate.md` |
| $host is required, others have defaults | `references/host-is-required-others-have-defaults.md` |
| Good: Slurpy parameter for variable args | `references/good-slurpy-parameter-for-variable-args.md` |
| Bad: Manual argument unpacking | `references/bad-manual-argument-unpacking.md` |
| ... | `references/bolum.md` |
| Good: Postfix dereferencing | `references/good-postfix-dereferencing.md` |
| Bad: Circumfix dereferencing (harder to read in chains) | `references/bad-circumfix-dereferencing-harder-to-read-in-chains.md` |
| Error Handling | `references/error-handling.md` |
| Modern OO with Moo | `references/modern-oo-with-moo.md` |
| Good: Moo class | `references/good-moo-class.md` |
| Usage | `references/usage.md` |
| Bad: Blessed hashref (no validation, no accessors) | `references/bad-blessed-hashref-no-validation-no-accessors.md` |
| Regular Expressions | `references/regular-expressions.md` |
| Good: Named captures with /x for readability | `references/good-named-captures-with-x-for-readability.md` |
| Bad: Positional captures (hard to maintain) | `references/bad-positional-captures-hard-to-maintain.md` |
| Good: Compile once, use many | `references/good-compile-once-use-many.md` |
| Data Structures | `references/data-structures.md` |
| Hash and array references | `references/hash-and-array-references.md` |
| Safe deep access (returns undef if any level missing) | `references/safe-deep-access-returns-undef-if-any-level-missing.md` |
| Hash slices | `references/hash-slices.md` |
| Array slices | `references/array-slices.md` |
| Multi-variable for loop (experimental in 5.36, stable in 5.40) | `references/multi-variable-for-loop-experimental-in-5-36-stable-in-5-40.md` |
| File I/O | `references/file-i-o.md` |
| Good: Three-arg open with autodie (core module, eliminates 'or die') | `references/good-three-arg-open-with-autodie-core-module-eliminates-or-d.md` |
| Bad: Two-arg open (shell injection risk, see perl-security) | `references/bad-two-arg-open-shell-injection-risk-see-perl-security.md` |
| Iterate directory | `references/iterate-directory.md` |
| Module Organization | `references/module-organization.md` |
| Tooling | `references/tooling.md` |
| cpanfile | `references/cpanfile.md` |
| Quick Reference: Modern Perl Idioms | `references/quick-reference-modern-perl-idioms.md` |
| Anti-Patterns | `references/anti-patterns.md` |
| 1. Two-arg open (security risk) | `references/1-two-arg-open-security-risk.md` |
| 2. Indirect object syntax (ambiguous parsing) | `references/2-indirect-object-syntax-ambiguous-parsing.md` |
| 3. Excessive reliance on $_ | `references/3-excessive-reliance-on-_.md` |
| 4. Disabling strict refs | `references/4-disabling-strict-refs.md` |
| 5. Global variables as configuration | `references/5-global-variables-as-configuration.md` |
| 6. String eval for module loading | `references/6-string-eval-for-module-loading.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
