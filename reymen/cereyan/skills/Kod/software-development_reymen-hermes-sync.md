---
name: reymen-hermes-sync
title: "Reymen-Hermes Sync & Merge"
tags: [reymen, hermes, merge, sync, git, github, update, workflow]
description: "Systematic protocol for merging Hermes Agent updates into Reymen (derived project) while preserving Reymen-specific customizations. Covers 3-step merge, reymen_ prefix convention, duplicate detection, protected files, and self-update setup."
version: 1.0.0
author: marko
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [reymen, hermes, merge, sync, git, github, workflow, update, migration]
audience: agent
related_skills: [hermes-agent, obsidian-vault-kurallari, github-pr-workflow]
---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Systematic protocol for merging Hermes Agent updates into Reymen (derived project) while preserving Reymen-specific customizations. Covers 3-step merge, reymen_ prefix convention, duplicate detection, protected files, and self-update setup. |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Reymen-Hermes Sync & Merge

## Overview

When Hermes Agent gets updated, Reymen (a derived project) needs to selectively absorb the changes. Not all Hermes files can be blindly copied — Reymen has custom modifications, renamed modules, and a different architecture.

This skill defines the **3-step merge protocol** for safely propagating Hermes updates into Reymen.

## Principles

1. **NEVER overwrite a Reymen-customized file.** If a file exists in both Hermes and Reymen, check if Reymen modified it first.
2. **Two copies are fine if they serve different callers.** Root versions (Reymen's simplified) for `beyin.py`/`motor.py` callers, agent/ versions (Hermes full) for `run_agent.py`/`cli.py` callers.
3. **reymen_ prefix** — when Hermes replaces a file that has the same name but different purpose, rename Reymen's original to `reymen_<name>.py` before copying.
4. **Always compile-check** after every merge batch.
5. **Push only when user says OK** — never push to GitHub without explicit instruction.

## CRITICAL RULE: Check ALL Layers Before Reporting

**BEFORE you tell the user anything is "missing" from Reymen, you MUST check BOTH locations:**

1. `root/*.py` — Reymen's own simplified versions
2. `agent/*.py` — Hermes's full versions (often the REAL location of what's "missing")

### The Root/Agent Layer Pitfall

Hermes's core modules live in its top-level directory. Reymen has these same modules in TWO places:

| Location | Contains | Purpose |
|----------|----------|---------|
| `root/*.py` | Simplified versions | Used by Reymen-native modules (beyin.py, motor.py) |
| `agent/*.py` | Full Hermes versions | Used by Hermes-compatible modules (run_agent.py, cli.py) |

**If you only check root/ and find a file "missing," you haven't finished checking yet.** The file almost certainly exists in `agent/`. Verify with:

```bash
# Always check BOTH directories before reporting
for f in some_file.py; do
  echo "root:   $( [ -f \"REYMEN_DIR/$f\" ] && wc -l < \"REYMEN_DIR/$f\" || echo 'YOK' )"
  echo "agent:  $( [ -f \"REYMEN_DIR/agent/$f\" ] && wc -l < \"REYMEN_DIR/agent/$f\" || echo 'YOK' )"
done
```

### Full Directory Comparison

```bash
python -c "
import os
h = set(f for f in os.listdir('HERMES_DIR') if f.endswith('.py'))
r = set()
for d in ['REYMEN_DIR', 'REYMEN_DIR/agent']:
    for f in os.listdir(d):
        if f.endswith('.py'): r.add(f)
missing = sorted(h - r)
if missing:
    print(f'Gercekten eksik: {len(missing)} dosya')
    for f in missing: print(f'  + {f}')
else:
    print('Hermes\'teki her sey Reymen\'de mevcut')
"
```

Apply this comparison BEFORE any "eksik" report to the user.

## Cleanup Procedure (When Duplicates Were Created by Mistake)

If you copied files that turned out to be unwanted duplicates:

### 1. Identify the duplicates
```bash
# Find files that exist in BOTH root/ and agent/
for f in *.py; do
  [ -f "agent/$f" ] && echo "$f: root=$(wc -l < $f) | agent=$(wc -l < agent/$f)"
done
```

### 2. Check import dependencies
```bash
python -c "
import os, re
dupes = set(f.replace('.py','') for f in os.listdir('.') if os.path.isfile(f'agent/{f}') if f.endswith('.py'))
for f in sorted(os.listdir('.')):
    if not f.endswith('.py'): continue
    with open(f, encoding='utf-8') as fh:
        for imp in re.findall(r'^from (\w+) import|^import (\w+)', fh.read(), re.MULTILINE):
            m = [x for x in imp if x]
            if m and m[0] in dupes:
                print(f'  {f} imports {m[0]} — must update to agent.{m[0]}')
"
```

### 3. Fix imports, then delete
1. For each import found, change `from X` → `from agent.X`
2. Verify compilation: `python -m py_compile dispatcher.py`
3. Delete root duplicates: `rm file1.py file2.py ...`
4. Recompile test: `python -m py_compile main.py motor.py run_agent.py`

## 4-Step Merge Protocol

### Step 1: Copy Untouched Files

Files that exist ONLY in Hermes (not in Reymen at all) or are pure documentation/build files that Reymen hasn't modified:

```
AGENTS.md, CONTRIBUTING.md, .env.example
Dockerfile, docker-compose*.yml, flake*.nix
pyproject.toml, setup.py, setup.cfg
docs/, assets/, packaging/
```

**Action:** Copy directly from `HERMES_DIR` to `REYMEN_DIR`.

### Step 2: Copy Missing Agent Modules

Files that exist in Hermes's `agent/` directory but Reymen doesn't have a root equivalent for:

```bash
# Check what's missing
for f in coding_context.py credits_tracker.py errors.py runtime_cwd.py ssl_guard.py turn_context.py turn_finalizer.py turn_retry_state.py; do
  [ -f "REYMEN_DIR/$f" ] && echo "EXISTS: $f" || echo "MISSING: $f"
done
```

**Action:** Copy Hermes files to Reymen root. These are new modules that Reymen doesn't have yet.

### Step 3: Merge Shared Files

Files that exist in BOTH Hermes AND Reymen with different content. Use the comparison method:

```bash
# Quick size comparison
for f in file1.py file2.py; do
  H=$(wc -l < "HERMES_DIR/$f")
  R=$(wc -l < "REYMEN_DIR/$f")
  [ "$H" -ne "$R" ] && echo "DIFF: $f (Hermes=$H, Reymen=$R)" || echo "SAME: $f"
done
```

**Decision matrix:**

| Situation | Action |
|-----------|--------|
| Same purpose, Hermes has new functions | Keep Reymen's file, add new functions |
| Different purpose, same name | Rename Reymen's → `reymen_<name>.py`, copy Hermes's version |
| Hermes's version is standalone CLI tool | Rename Reymen's, copy Hermes's (both usable) |

### Protected Files (NEVER modified)

These 13 Reymen-specific files are protected from sync/overwrite:

```bash
cli.py, motor.py, beyin.py, main.py, guardrails.py
closed_learning_loop.py, hata_cozucu.py, tor_otomasyonu.py
araclar_nisan.py, nisan_yakala.py, otonom_nisan_olusturucu.py
akilli_yonlendirici.py, cokus_raporlayici.py
```

### Step 4: Fix Test Suite (Hermes API Adaptation)

After Steps 1-3, the test suite will likely break because tests were written for Reymen's simplified API but now use Hermes's full API (via agent/ imports).

Fix systematically:

**4a. Fix import paths — 17 common renames:**
```
iteration_budget → agent.iteration_budget
prompt_builder   → agent.prompt_builder
trajectory       → agent.trajectory
... (all modules that moved from root to agent/)
```

**4b. Fix API signatures — discover with inspect:**
```python
import inspect
from agent.iteration_budget import IterationBudget
print(inspect.signature(IterationBudget.__init__))
```

**4c. Property vs method check:**
```python
members = [(k, type(v).__name__) for k,v in inspect.getmembers(obj) if not k.startswith('_')]
# If type is 'int' or 'str', it's a property — no ()
```

**4d. Build mock agent for upstream functions:**

For simple tests a hand-rolled MockAgent works. For complex functions (e.g. `compress_context` which accesses 25+ agent attributes), use `unittest.mock.MagicMock` instead — it auto-creates any attribute on first access:

```python
from unittest.mock import MagicMock

agent = MagicMock()
agent.session_id = "test"
agent.conversation_id = "test"
agent.model = "test-model"
agent.provider = None
agent.context_compressor.compress.return_value = (messages, "summary")
agent._build_system_prompt.return_value = "system prompt"

# MagicMock handles _emit_status, _memory_manager, context_compressor,
# _compression_feasibility_checked, and all other attributes automatically.
sonuc = compress_context(agent, messages, "test", approx_tokens=100, force=True)
```

**Never use a hand-rolled MockAgent with complex upstream functions** — you'll play whack-a-mole adding missing attributes one by one. Switch to MagicMock at the first sign of multiple missing-attribute errors.

**4e. Run incrementally after every batch:**
```bash
python test_suite.py 2>&1 | grep -E "^(  OK|  FAIL|Sonuc)"
# Track: 15/35 → 21/35 → 26/35 → 31/35 → 35/35
```

Full reference: `references/test-suite-api-adaptation.md`

## Duplicate Detection (Root vs Agent/)

Reymen has **two layers** of files with the same names:

| Location | Contains | Used by |
|----------|----------|---------|
| `root/*.py` | Reymen's simplified/stripped versions | `beyin.py`, `motor.py` (Reymen ReAct loop) |
| `agent/*.py` | Hermes's full versions | `run_agent.py`, `cli.py` (Hermes-compatible modules) |

To detect duplicates:
```bash
for f in *.py; do
  if [ -f "agent/$f" ]; then
    R=$(wc -l < "$f")
    A=$(wc -l < "agent/$f")
    [ "$R" -ne "$A" ] && echo "DUAL: $f (root=$R, agent=$A)"
  fi
done
```

These are **intentional** — both layers are needed. Do NOT merge them.

## Self-Update Setup (GitHub)

Reymen self-updates from its own GitHub repo, NOT from Hermes source.

```bash
# Repo: https://github.com/Watcher-Hermes/ReYMeN-Ajan
# Sync script: .hermes_sync.sh
# Usage:
bash .hermes_sync.sh              # Status
bash .hermes_sync.sh --sync       # Pull from GitHub
bash .hermes_sync.sh --push       # Push local changes
```

**Cron:** Automatically runs every Monday at 03:00 (cron job ID: 659609b4799e).

## Verification After Merge

Always run these checks after any merge:

```bash
# 1. Compile all changed files
for f in file1.py file2.py ...; do
  python -m py_compile "$f" && echo "OK: $f" || echo "FAIL: $f"
done

# 2. Check imports (quick spot check)
python -c "from model_tools import get_tool_definitions; print('imports OK')"

# 3. Full test suite (when possible)
python -m pytest test_suite.py -x -q --timeout=60
```

## Common Pitfalls

1. **CRLF vs LF line endings** — Windows `diff` output shows the entire file as changed when the only difference is line endings. Use `diff --strip-trailing-cr` or compare wc -l first.
2. **Python import timeout** — Some modules (e.g., model_tools.py) import many deep dependencies; `py_compile` is faster than full import for verification.
3. **reymen_ prefix collision** — After renaming with reymen_ prefix, update all internal imports. Check with `grep -rn "old_name" *.py`.
4. **User does NOT want GitHub push without permission** — Always ask before `git push`. "Sakin githab yollama" is the rule.
5. **"Hayir asla" reaction** — When user says "hayir asla" to a decision you made about what to skip/merge, you skipped something you shouldn't have. Do ALL merges the user asked for.
6. **Size-based duplicate detection** — `wc -l` comparison catches most duplicates, but content can still differ at same size. Use `diff --brief` for certainty.
7. **Test suite progress is not linear** — expect 15/35 → 21/35 → 26/35 → 31/35 → 35/35. Each batch of fixes reveals deeper API mismatches. Don't try to fix all 20 at once.
8. **`**kwargs` called with positional args** — When a function signature is `calistir(self, komut, **kwargs)` and you call `calistir(komut, timeout)`, Python rejects `timeout` as an unexpected positional arg. Always pass extra kwargs by keyword: `calistir(komut, timeout=timeout)`. A real case: `tools/shell.py → TerminalBackendDispatcher.calistir()` took `timeout` positionally and failed.

## Related References

- `references/test-suite-api-adaptation.md` (in fork-project-audit skill) — full API adaptation workflow
- `references/2026-06-17-83-dupe-cleanup.md` — 83 duplicate file cleanup protocol
- `references/2026-06-30-merge-session.md` — previous merge session details
- `references/batch-test-runner.md` — parallel batch test runner for 1,500+ files (10-at-a-time ThreadPoolExecutor pattern)
