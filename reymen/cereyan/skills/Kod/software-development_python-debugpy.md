---

name: python-debugpy
title: "Python Debugpy"
tags: [coding, development, python]
description: "Debug Python: pdb REPL + debugpy remote (DAP)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [debugging, python, pdb, debugpy, breakpoints, dap, post-mortem]
audience: contributor
related_skills: [systematic-debugging, node-inspect-debugger, debugging-hermes-tui-commands]
---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Debug Python: pdb REPL + debugpy remote (DAP). |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Python Debugpy

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Overview | `references/overview.md` |
| When to Use | `references/when-to-use.md` |
| pdb Quick Reference | `references/pdb-quick-reference.md` |
| Recipe 1: Local breakpoint | `references/recipe-1-local-breakpoint.md` |
| Recipe 2: Launch a script under pdb (no source edits) | `references/recipe-2-launch-a-script-under-pdb-no-source-edits.md` |
| Lands at first line of script | `references/lands-at-first-line-of-script.md` |
| Recipe 3: Debug a pytest test | `references/recipe-3-debug-a-pytest-test.md` |
| Drop to pdb on failure (or on any raised exception): | `references/drop-to-pdb-on-failure-or-on-any-raised-exception.md` |
| Drop to pdb at the START of the test: | `references/drop-to-pdb-at-the-start-of-the-test.md` |
| Show locals in tracebacks without pdb: | `references/show-locals-in-tracebacks-without-pdb.md` |
| or | `references/or.md` |
| Recipe 4: Post-mortem on any exception | `references/recipe-4-post-mortem-on-any-exception.md` |
| When it crashes, pdb catches it and you're in the frame of the exception | `references/when-it-crashes-pdb-catches-it-and-you-re-in-the-frame-of-th.md` |
| Recipe 5: Remote debug with debugpy (attach to running process) | `references/recipe-5-remote-debug-with-debugpy-attach-to-running-process.md` |
| debugpy injects itself into the process. Then attach a client as below. | `references/debugpy-injects-itself-into-the-process-then-attach-a-client.md` |
| /tmp/dap_client.py | `references/tmp-dap_client-py.md` |
| ... loop reading events and sending continue/stepIn/etc. | `references/loop-reading-events-and-sending-continue-stepin-etc.md` |
| You get a (Pdb) prompt exactly as if debugging locally. | `references/you-get-a-pdb-prompt-exactly-as-if-debugging-locally.md` |
| Debugging Hermes-specific Processes | `references/debugging-hermes-specific-processes.md` |
| tui_gateway/server.py near the top of serve() | `references/tui_gateway-server-py-near-the-top-of-serve.md` |
| Common Pitfalls | `references/common-pitfalls.md` |
| Verification Checklist | `references/verification-checklist.md` |
| One-Shot Recipes | `references/one-shot-recipes.md` |
| then in pdb: | `references/then-in-pdb.md` |
| But if it only fails WITH other tests: | `references/but-if-it-only-fails-with-other-tests.md` |
| Now it pdb-traps at the exact failing test after state accumulated. | `references/now-it-pdb-traps-at-the-exact-failing-test-after-state-accum.md` |
| Add at handler entry | `references/add-at-handler-entry.md` |
| On crash, pdb lands at the frame of the exception with full locals | `references/on-crash-pdb-lands-at-the-frame-of-the-exception-with-full-l.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
