---
name: bulk-text-replace
title: "Bulk Text Replace Across a Codebase"
tags: [devops, codebase, refactoring, text-manipulation]
description: "Mass find-and-replace across thousands of source files using find + perl. Covers backup, word boundary semantics, Windows git-bash quoting, and verification. Use when renaming identifiers, migrating imports, or doing codebase-wide text substitutions."
audience: contributor
---


> **Kategori:** devops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Mass find-and-replace across thousands of source files using find + perl. Covers backup, word boundary semantics, Windows git-bash quoting, and verification. Use when renaming identifiers, migrating imports, or doing codebase-wide text substitutions. |
| **Nerede?** | devops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Bulk Text Replace Across a Codebase

Use when you need to replace every occurrence of a string across a large codebase (hundreds to thousands of files).

## Workflow

### 1. Baseline — Count Files

```bash
# Total .py files (exclude noise dirs)
find . -name '*.py' -type f \
  -not -path '*/venv/*' \
  -not -path '*/node_modules/*' \
  -not -path '*/.git/*' \
  -not -path '*/__pycache__/*' | wc -l

# Files containing the target string
grep -rln 'TARGET_STRING' --include='*.py' \
  --exclude-dir=venv --exclude-dir=node_modules \
  --exclude-dir=.git --exclude-dir=__pycache__ \
  -i 2>/dev/null | wc -l
```

### 2. Backup Before Changes

```bash
# Option A: Git commit (if repo)
git add -A && git commit -m "backup before mass replace"

# Option B: File backup (if not a repo)
mkdir -p /tmp/bulk-replace-backup
grep -rln 'TARGET' --include='*.py' [excludes] -i > /tmp/target_files.txt
while IFS= read -r f; do
  mkdir -p "/tmp/bulk-replace-backup/$(dirname "$f")"
  cp "$f" "/tmp/bulk-replace-backup/$f"
done < /tmp/target_files.txt
```

### 3. Apply Replacement

**RECOMMENDED** — single `find -exec perl` command (most reliable):

```bash
find . -name '*.py' -type f \
  -not -path '*/venv/*' -not -path '*/node_modules/*' \
  -not -path '*/.git/*' -not -path '*/__pycache__/*' \
  -exec perl -i -pe 's/OLD_STRING/NEW_STRING/gi' {} +
```

**Why NOT batch loops:** Python `for f in files: terminal(f"perl ... '{f}'")` loops are unreliable when file paths contain spaces, special chars, or absolute paths with `/c/...` prefixes. `find -exec` handles all paths natively.

### 4. Verify

```bash
# Should be 0
grep -rln 'OLD_STRING' --include='*.py' [excludes] -i | wc -l

# Count replacements
grep -ro 'NEW_STRING' --include='*.py' [excludes] | wc -l
```

## Word Boundary Semantics

Perl `\b` treats underscore (`_`) as a **word character**. This means:

| Pattern | `\bhermes\b` matches? | Plain `hermes` matches? |
|---------|----------------------|------------------------|
| `hermes` standalone | ✅ | ✅ |
| `Hermes` (capital) | ✅ (with `/i`) | ✅ |
| `.hermes/skills` | ✅ (`.` is non-word) | ✅ |
| `hermes_pkce` | ❌ (`_` is word char) | ✅ |
| `hermes_cli` | ❌ (`_` is word char) | ✅ |
| `hermes_output` | ❌ (`_` is word char) | ✅ |

**Choose the right mode:**
- Word boundary (`\b`): Safe for identifiers, won't break compound names
- Plain substring: Complete cleanup, may break imports referencing directory names (e.g., `import hermes_cli.xxx` → `import R>eYMeN_cli.xxx` while the actual directory is still `hermes_cli/`)

## Windows / Git-Bash Specifics

- **Single quotes work** in git-bash for perl inline scripts
- **Spaces in paths:** Use `cd '/path/with spaces/project' && find . ...` with relative paths rather than absolute paths
- **Exclude dirs:** Use `-not -path '*/venv/*'` syntax, not `-path` prefix
- **Timeout:** For 1000+ files, set timeout ≥ 300s in terminal()

## Reference Files

- `references/real-world-example.md` — Full-scale rename (2,845 files, hermes → R>eYMeN)
- `references/context-aware-rename.md` — **Context-aware rename:** project name change when some occurrences reference external projects. Covers categorization (rename / skip / adapt), user review workflow, and special character handling (`>` in batch scripts).

## Pitfalls

1. **Import breakage:** Plain substring replace changes directory references in import statements without renaming actual directories. Warn the user before doing this.
2. **Batch loops fail silently:** `perl` called from Python `terminal()` inside a loop may skip files with special characters in paths. Always verify with a fresh grep after.
3. **R>eYMeN special chars:** The `>` character in `R>eYMeN` is literal in Perl replacement strings — no escaping needed for the replacement side of `s///`.
4. **Case sensitivity with `grep -i`:** When verifying, use the same case sensitivity as the replacement to avoid false positives.
5. **File encoding:** Perl `-i` preserves the original encoding. No special handling needed for UTF-8 files.
6. **File rename vs content replace — import chain risk:** When renaming actual files (`mv old_name.py new_name.py`) rather than just replacing text inside them, always check import chains first (`grep -rn "import old_name\|from old_name"`). Import-less modules are safe; anything else needs caller updates. See `references/context-aware-rename.md` for the full workflow.
7. **Windows filename restrictions:** Characters `\ / : * ? " < > |` cannot appear in Windows filenames. If the new name includes any (e.g., `R>eYMeN.bat`), use an alternative without them. Windows is case-insensitive for filenames — `ReYMeN.bat` ≡ `reyemen.bat`.
