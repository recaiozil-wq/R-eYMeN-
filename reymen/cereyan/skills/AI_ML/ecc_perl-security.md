
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ecc_Perl Security |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: perl-security
description: Comprehensive Perl security covering taint mode, input validation, safe process execution, DBI parameterized queries, web security (XSS/SQLi/CSRF), and perlcritic security policies.
title: "Perl Security"
origin: ECC

audience: contributor
tags: [ai, automation, development, security]
category: ecc---

# Perl Security

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Perl Security Patterns | `references/perl-security-patterns.md` |
| When to Activate | `references/when-to-activate.md` |
| How It Works | `references/how-it-works.md` |
| Taint Mode | `references/taint-mode.md` |
| Tainted: anything from outside the program | `references/tainted-anything-from-outside-the-program.md` |
| Sanitize PATH early (required in taint mode) | `references/sanitize-path-early-required-in-taint-mode.md` |
| Good: Validate and untaint with a specific regex | `references/good-validate-and-untaint-with-a-specific-regex.md` |
| Good: Validate and untaint a file path | `references/good-validate-and-untaint-a-file-path.md` |
| Bad: Overly permissive untainting (defeats the purpose) | `references/bad-overly-permissive-untainting-defeats-the-purpose.md` |
| Input Validation | `references/input-validation.md` |
| Good: Allowlist — define exactly what's permitted | `references/good-allowlist-define-exactly-what-s-permitted.md` |
| Good: Validate with specific patterns | `references/good-validate-with-specific-patterns.md` |
| Bad: Blocklist — always incomplete | `references/bad-blocklist-always-incomplete.md` |
| Safe Regular Expressions | `references/safe-regular-expressions.md` |
| Bad: Vulnerable to ReDoS (exponential backtracking) | `references/bad-vulnerable-to-redos-exponential-backtracking.md` |
| Good: Rewrite without nesting | `references/good-rewrite-without-nesting.md` |
| Good: Use possessive quantifiers or atomic groups to prevent backtracking | `references/good-use-possessive-quantifiers-or-atomic-groups-to-prevent-.md` |
| Good: Enforce timeout on untrusted patterns | `references/good-enforce-timeout-on-untrusted-patterns.md` |
| Safe File Operations | `references/safe-file-operations.md` |
| Good: Three-arg open, lexical filehandle, check return | `references/good-three-arg-open-lexical-filehandle-check-return.md` |
| Bad: Two-arg open with user data (command injection) | `references/bad-two-arg-open-with-user-data-command-injection.md` |
| Atomic file creation | `references/atomic-file-creation.md` |
| Validate path stays within allowed directory | `references/validate-path-stays-within-allowed-directory.md` |
| Safe Process Execution | `references/safe-process-execution.md` |
| Good: List form — no shell interpolation | `references/good-list-form-no-shell-interpolation.md` |
| Good: Capture output safely with IPC::Run3 | `references/good-capture-output-safely-with-ipc-run3.md` |
| Bad: String form — shell injection! | `references/bad-string-form-shell-injection.md` |
| Bad: Backticks with interpolation | `references/bad-backticks-with-interpolation.md` |
| SQL Injection Prevention | `references/sql-injection-prevention.md` |
| Good: Parameterized queries — always use placeholders | `references/good-parameterized-queries-always-use-placeholders.md` |
| Bad: String interpolation in SQL (SQLi vulnerability!) | `references/bad-string-interpolation-in-sql-sqli-vulnerability.md` |
| If $email = "' OR 1=1 --", returns all users | `references/if-email-or-1-1-returns-all-users.md` |
| Good: Validate column names against an allowlist | `references/good-validate-column-names-against-an-allowlist.md` |
| Bad: Directly interpolating user-chosen column | `references/bad-directly-interpolating-user-chosen-column.md` |
| DBIx::Class generates safe parameterized queries | `references/dbix-class-generates-safe-parameterized-queries.md` |
| Web Security | `references/web-security.md` |
| Good: Encode output for HTML context | `references/good-encode-output-for-html-context.md` |
| Good: Encode for URL context | `references/good-encode-for-url-context.md` |
| Good: Encode for JSON context | `references/good-encode-for-json-context.md` |
| Bad: Raw output in HTML | `references/bad-raw-output-in-html.md` |
| Mojolicious session + headers | `references/mojolicious-session-headers.md` |
| Output Encoding | `references/output-encoding.md` |
| CPAN Module Security | `references/cpan-module-security.md` |
| Security Tooling | `references/security-tooling.md` |
| .perlcriticrc — security-focused configuration | `references/perlcriticrc-security-focused-configuration.md` |
| Require three-arg open | `references/require-three-arg-open.md` |
| Require checked system calls | `references/require-checked-system-calls.md` |
| Prohibit string eval | `references/prohibit-string-eval.md` |
| Prohibit backtick operators | `references/prohibit-backtick-operators.md` |
| Require taint checking in CGI | `references/require-taint-checking-in-cgi.md` |
| Prohibit two-arg open | `references/prohibit-two-arg-open.md` |
| Prohibit bare-word filehandles | `references/prohibit-bare-word-filehandles.md` |
| Check a file | `references/check-a-file.md` |
| Check entire project | `references/check-entire-project.md` |
| CI integration | `references/ci-integration.md` |
| Quick Security Checklist | `references/quick-security-checklist.md` |
| Anti-Patterns | `references/anti-patterns.md` |
| 1. Two-arg open with user data (command injection) | `references/1-two-arg-open-with-user-data-command-injection.md` |
| 2. String-form system (shell injection) | `references/2-string-form-system-shell-injection.md` |
| 3. SQL string interpolation | `references/3-sql-string-interpolation.md` |
| 4. eval with user input (code injection) | `references/4-eval-with-user-input-code-injection.md` |
| 5. Trusting $ENV without sanitizing | `references/5-trusting-env-without-sanitizing.md` |
| 6. Disabling taint without validation | `references/6-disabling-taint-without-validation.md` |
| 7. Raw user data in HTML | `references/7-raw-user-data-in-html.md` |
| 8. Unvalidated redirects | `references/8-unvalidated-redirects.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
