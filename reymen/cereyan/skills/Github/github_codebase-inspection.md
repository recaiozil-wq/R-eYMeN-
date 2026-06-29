---
name: codebase-inspection
title: "Codebase Inspection"
tags: [development, git, github]
description: "Inspect codebases w/ pygount: LOC, languages, ratios."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [LOC, Code Analysis, pygount, Codebase, Metrics, Repository]
audience: contributor
related_skills: [github-repo-management]
prerequisites:
  commands: [pygount]
---


> **Kategori:** github

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Inspect codebases w/ pygount: LOC, languages, ratios. |
| **Nerede?** | github/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Codebase Inspection with pygount

Analyze repositories for lines of code, language breakdown, file counts, and code-vs-comment ratios using `pygount`.

## When to Use

- User asks for LOC (lines of code) count
- User wants a language breakdown of a repo
- User asks about codebase size or composition
- User wants code-vs-comment ratios
- General "how big is this repo" questions

## Prerequisites

```bash
pip install --break-system-packages pygount 2>/dev/null || pip install pygount
```

## 1. Basic Summary (Most Common)

Get a full language breakdown with file counts, code lines, and comment lines:

```bash
cd /path/to/repo
pygount --format=summary \
  --folders-to-skip=".git,node_modules,venv,.venv,__pycache__,.cache,dist,build,.next,.tox,.eggs,*.egg-info" \
  .
```

**IMPORTANT:** Always use `--folders-to-skip` to exclude dependency/build directories, otherwise pygount will crawl them and take a very long time or hang.

## 2. Common Folder Exclusions

Adjust based on the project type:

```bash
# Python projects
--folders-to-skip=".git,venv,.venv,__pycache__,.cache,dist,build,.tox,.eggs,.mypy_cache"

# JavaScript/TypeScript projects
--folders-to-skip=".git,node_modules,dist,build,.next,.cache,.turbo,coverage"

# General catch-all
--folders-to-skip=".git,node_modules,venv,.venv,__pycache__,.cache,dist,build,.next,.tox,vendor,third_party"
```

## 3. Filter by Specific Language

```bash
# Only count Python files
pygount --suffix=py --format=summary .

# Only count Python and YAML
pygount --suffix=py,yaml,yml --format=summary .
```

## 4. Detailed File-by-File Output

```bash
# Default format shows per-file breakdown
pygount --folders-to-skip=".git,node_modules,venv" .

# Sort by code lines (pipe through sort)
pygount --folders-to-skip=".git,node_modules,venv" . | sort -t$'\t' -k1 -nr | head -20
```

## 5. Output Formats

```bash
# Summary table (default recommendation)
pygount --format=summary .

# JSON output for programmatic use
pygount --format=json .

# Pipe-friendly: Language, file count, code, docs, empty, string
pygount --format=summary . 2>/dev/null
```

## 6. Interpreting Results

The summary table columns:
- **Language** — detected programming language
- **Files** — number of files of that language
- **Code** — lines of actual code (executable/declarative)
- **Comment** — lines that are comments or documentation
- **%** — percentage of total

Special pseudo-languages:
- `__empty__` — empty files
- `__binary__` — binary files (images, compiled, etc.)
- `__generated__` — auto-generated files (detected heuristically)
- `__duplicate__` — files with identical content
- `__unknown__` — unrecognized file types

## 7. Import Dependency Audit (Fork/Copy Analysis)

Use when analyzing whether a forked or copied codebase has broken imports. This is a three-pass technique to separate real problems from harmless legacy imports.

### Pass 1: Count + Categorize

```bash
# Total Python files (exclude venv/pycache)
find /path/to/project -name "*.py" \
  -not -path "*/venv/*" -not -path "*/__pycache__/*" -not -path "*/.git/*" \
  | wc -l

# Files per directory (find the heavy folders)
cd /path/to/project && for d in */; do
  count=$(find "$d" -name "*.py" -not -path "*/venv/*" -not -path "*/__pycache__/*" 2>/dev/null | wc -l)
  echo "$count  $d"
done | sort -rn

# Largest files (sorted by line count)
find /path/to/project -name "*.py" \
  -not -path "*/venv/*" -not -path "*/__pycache__/*" \
  -exec wc -l {} \; 2>/dev/null | sort -rn | head -20
```

### Pass 2: Import Chain Analysis

The critical question: **does your own code actually import from the broken modules?**

```bash
# Step 1 — Find what YOUR code imports (exclude copied test/legacy dirs)
grep -rn "^from\|^import" your_code/ --include="*.py" | sort -u

# Step 2 — Find what the COPIED code imports from the upstream
grep -rn "^from hermes\|^import hermes\|^from upstream_pkg" tests/ --include="*.py" | sort -u

# Step 3 — Count who imports what
echo "Your code imports FROM upstream:"
grep -rl "^from upstream_pkg\|^import upstream_pkg" your_code/ --include="*.py" | wc -l

echo "Copied tests import FROM upstream:"
grep -rl "^from upstream_pkg\|^import upstream_pkg" tests/ --include="*.py" | wc -l
```

### Pass 3: Verify Actual Importability

Don't guess — test if the key modules actually import:

```bash
cd /path/to/project
python -c "import your_module; print('OK')" 2>&1
python -c "from your_package import YourClass; print('OK')" 2>&1
python -c "from main import YourEngine; print('OK')" 2>&1
```

### Interpreting Results

| Pattern | Meaning | Action |
|---------|---------|--------|
| Your code imports upstream → upstream is broken | **REAL PROBLEM** | Fix the import chain or add shims |
| Only tests import upstream → upstream is broken | **FALSE ALARM** | Tests test the upstream, not your code. Skip or move to `tests/_reference/` |
| Your code imports upstream → upstream works | **NO ISSUE** | Upstream modules are usable |
| Nothing imports upstream → upstream is broken | **NO ISSUE** | Dead code, safe to delete |

## 8. Duplicate File Detection (Cross-Directory Analysis)

Use when a codebase has files with the **same name** across different directories (e.g., `root/xxx.py` and `agent/xxx.py`). This is common in forked/derived projects where one directory has simplified wrappers and another has the full upstream implementation.

### Pass 1: Find Duplicates

```bash
# List both directories and find common filenames
ls root/*.py | xargs -n1 basename > /tmp/root_files.txt
ls agent/*.py | xargs -n1 basename > /tmp/agent_files.txt
comm -12 <(sort /tmp/root_files.txt) <(sort /tmp/agent_files.txt)
```

### Pass 2: Check Line Count Differences

```bash
# For each duplicate, compare sizes to spot which is the simplified version
for f in $(comm -12 <(sort /tmp/root_files.txt) <(sort /tmp/agent_files.txt)); do
  rl=$(wc -l < "root/$f" 2>/dev/null)
  al=$(wc -l < "agent/$f" 2>/dev/null)
  [ "$rl" != "$al" ] && echo "DIFF: $f — root=$rl vs agent=$al"
done
```

### Pass 3: Verify Nothing Imports From the Root Version

**CRITICAL** — before deleting any duplicate, confirm that your own code doesn't import from the root version:

```bash
for f in $(comm -12 <(sort /tmp/root_files.txt) <(sort /tmp/agent_files.txt)); do
  mod=$(basename "$f" .py)
  count=$(grep -rn "^from $mod import\|^import $mod$" *.py --include="*.py" 2>/dev/null | grep -v "agent/" | wc -l)
  [ "$count" -gt 0 ] && echo "USED: $mod ($count references)"
done
```

**Key heuristic:** When your own code has NO import references to root versions, the root duplicates are safe to delete — the agent/ versions are the ones actually used.

### Pass 4: Two-Pass Deletion

1. **Fix imports first:** For any root file that IS imported, update imports to `agent.XXX` before deleting
2. **Delete duplicates:** Remove all root copies with zero remaining import references
3. **Recompile:** `python -m py_compile` on critical modules to verify nothing broke

### Common Architecture Pattern

Projects forked from a larger upstream often develop this structure:

| Directory | Content | Used By |
|-----------|---------|---------|
| `root/` | Simplified/minimal versions for fork's own architecture | Fork-specific modules |
| `agent/` or `core/` | Full upstream versions | Upstream-compatible modules |

**Always disclose this architecture upfront** — it can cause significant wasted work if discovered late.

### Example: This Session's Finding

```bash
# Reymen (fork) → Hermes (upstream) analysis

# Step 1: Reymen's own files use NO Hermes imports
grep -n "^from hermes\|^import hermes" motor.py main.py yetenek_fabrikasi.py ...
# → empty! No real dependency.

# Step 2: Only copied test files use Hermes imports
grep -rl "^from hermes\|^import hermes" tests/ --include="*.py" | wc -l
# → 561 test files (out of 1,578 total)

# Step 3: Verify Reymen imports work
python -c "from motor import Motor; print('OK')"  # ✅
python -c "from closed_learning_loop import ClosedLearningLoop; print('OK')"  # ✅
python -c "from main import Motor; print('OK')"  # ✅ (chromadb graceful degrade)
# → All core modules work. Import "problem" is harmless.
```

**Key heuristic:** A broken import in a forked project is only a real problem if **your own code** (not copied tests/legacy files) depends on it. Always check who imports what before attempting fixes.

## Pitfalls

1. **Always exclude .git, node_modules, venv** — without `--folders-to-skip`, pygount will crawl everything and may take minutes or hang on large dependency trees.
2. **Markdown shows 0 code lines** — pygount classifies all Markdown content as comments, not code. This is expected behavior.
3. **JSON files show low code counts** — pygount may count JSON lines conservatively. For accurate JSON line counts, use `wc -l` directly.
4. **Large monorepos** — for very large repos, consider using `--suffix` to target specific languages rather than scanning everything.
