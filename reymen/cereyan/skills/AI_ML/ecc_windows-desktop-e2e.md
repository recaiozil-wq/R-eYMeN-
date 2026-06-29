
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Ecc_Windows Desktop E2E |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: windows-desktop-e2e
description: E2E testing for Windows native desktop apps (WPF, WinForms, Win32/MFC, Qt) using pywinauto and Windows UI Automation.
title: "Windows Desktop E2E"
origin: ECC

audience: contributor
tags: [ai, automation, development, windows]
category: ecc---

# Windows Desktop E2E

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Windows Desktop E2E Testing | `references/windows-desktop-e2e-testing.md` |
| When to Activate | `references/when-to-activate.md` |
| Core Concepts | `references/core-concepts.md` |
| Setup & Prerequisites | `references/setup-prerequisites.md` |
| Install ffmpeg and add to PATH: https://ffmpeg.org/download.html | `references/install-ffmpeg-and-add-to-path-https-ffmpeg-org-download-htm.md` |
| Testability Setup (by Framework) | `references/testability-setup-by-framework.md` |
| Page Object Model | `references/page-object-model.md` |
| --- Locators (priority order) --- | `references/locators-priority-order.md` |
| --- Waits --- | `references/waits.md` |
| --- Actions --- | `references/actions.md` |
| Qt 5.x fallback: UIA Value Pattern may be incomplete | `references/qt-5-x-fallback-uia-value-pattern-may-be-incomplete.md` |
| --- Artifacts --- | `references/artifacts.md` |
| Screenshot on failure | `references/screenshot-on-failure.md` |
| proc is a pywinauto Application — use wait_for_process_exit(), not wait_for_process() | `references/proc-is-a-pywinauto-application-use-wait_for_process_exit-no.md` |
| Locator Strategy | `references/locator-strategy.md` |
| or narrow scope: | `references/or-narrow-scope.md` |
| Wait Patterns | `references/wait-patterns.md` |
| Wait for control to appear | `references/wait-for-control-to-appear.md` |
| Wait for control to disappear (e.g. loading spinner) | `references/wait-for-control-to-disappear-e-g-loading-spinner.md` |
| Wait for a dialog to pop up | `references/wait-for-a-dialog-to-pop-up.md` |
| Custom condition (e.g. text changes) | `references/custom-condition-e-g-text-changes.md` |
| Artifact Management | `references/artifact-management.md` |
| Screenshot on demand | `references/screenshot-on-demand.md` |
| Full-screen capture (when window is off-screen or minimised) | `references/full-screen-capture-when-window-is-off-screen-or-minimised.md` |
| Screen recording with ffmpeg (start before test, stop after) | `references/screen-recording-with-ffmpeg-start-before-test-stop-after.md` |
| Per-Step Trace (opt-in) | `references/per-step-trace-opt-in.md` |
| Include typed text in the JSONL log (DO NOT use on tests that type credentials/PII): | `references/include-typed-text-in-the-jsonl-log-do-not-use-on-tests-that.md` |
| ... existing set_edit_text / keyboard fallback ... | `references/existing-set_edit_text-keyboard-fallback.md` |
| Flaky Test Handling | `references/flaky-test-handling.md` |
| Quarantine — equivalent to Playwright's test.fixme() | `references/quarantine-equivalent-to-playwright-s-test-fixme.md` |
| Skip in CI only | `references/skip-in-ci-only.md` |
| Test Isolation & Sandbox | `references/test-isolation-sandbox.md` |
| conftest.py — replace the basic `app` fixture with this | `references/conftest-py-replace-the-basic-app-fixture-with-this.md` |
| Redirect all per-user storage to an isolated tmp directory | `references/redirect-all-per-user-storage-to-an-isolated-tmp-directory.md` |
| Launch via subprocess so we can pass env; connect pywinauto by PID | `references/launch-via-subprocess-so-we-can-pass-env-connect-pywinauto-b.md` |
| tmp_path is cleaned up automatically by pytest | `references/tmp_path-is-cleaned-up-automatically-by-pytest.md` |
| Minimal rights: SET_QUOTA (0x0100) | TERMINATE (0x0001) | `references/minimal-rights-set_quota-0x0100-terminate-0x0001.md` |
| Correct struct layout — LimitFlags is at offset +16, not +44 | `references/correct-struct-layout-limitflags-is-at-offset-16-not-44.md` |
| After proc = subprocess.Popen(...):  job = restrict_process(proc.pid) | `references/after-proc-subprocess-popen-job-restrict_process-proc-pid.md` |
| CI/CD Integration | `references/ci-cd-integration.md` |
| .github/workflows/e2e-desktop.yml | `references/github-workflows-e2e-desktop-yml.md` |
| Qt Specific | `references/qt-specific.md` |
| conftest.py — add at module top | `references/conftest-py-add-at-module-top.md` |
| Qt 5.x: "Qt5QWindowIcon"  |  Qt 6.x: "Qt6QWindowIcon" — verify with Accessibility Insights | `references/qt-5-x-qt5qwindowicon-qt-6-x-qt6qwindowicon-verify-with-acce.md` |
| Fallback: Screenshot Mode | `references/fallback-screenshot-mode.md` |
| Anti-Patterns | `references/anti-patterns.md` |
| BAD: fixed sleep | `references/bad-fixed-sleep.md` |
| GOOD: condition wait | `references/good-condition-wait.md` |
| BAD: brittle class+index locator as primary strategy | `references/bad-brittle-class-index-locator-as-primary-strategy.md` |
| GOOD: AutomationId | `references/good-automationid.md` |
| BAD: assert on pixel coordinates | `references/bad-assert-on-pixel-coordinates.md` |
| GOOD: assert on content / state | `references/good-assert-on-content-state.md` |
| BAD: share app instance across all tests (state leaks) | `references/bad-share-app-instance-across-all-tests-state-leaks.md` |
| GOOD: fresh process per test (or per class at most) | `references/good-fresh-process-per-test-or-per-class-at-most.md` |
| Running Tests | `references/running-tests.md` |
| All tests | `references/all-tests.md` |
| Smoke only | `references/smoke-only.md` |
| Specific file | `references/specific-file.md` |
| With custom app path | `references/with-custom-app-path.md` |
| Detect flaky tests (repeat each 5 times) | `references/detect-flaky-tests-repeat-each-5-times.md` |
| Related Skills | `references/related-skills.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
