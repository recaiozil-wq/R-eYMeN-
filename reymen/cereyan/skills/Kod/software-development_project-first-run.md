---
name: project-first-run
title: "Project First-Run Setup"
description: >-
  Take a multi-module Python project that's 100% coded but 0% configured,
  and bring it to first-run operational state. Execution counterpart to
  project-gap-analysis — this skill does the fixes, not the analysis.
version: 1.0.0
tags: [python, setup, deployment, integration, windows]
audience: contributor
---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | >- |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Project First-Run Setup

## When to Use

- A project has all its source files written but has never been configured or run
- pip install / uv sync / venv setup was never executed
- `.env` contains masked values (`***`) instead of real API keys
- Multiple separate modules need to be integrated into one working system
- You completed a `project-gap-analysis` and now need to execute the fixes

## Core Workflow

### 1. Bulk Compilation Check

Before running anything, verify every `.py` file parses without syntax errors:

```bash
python -c "import ast, glob; errors=[]; [errors.append(f'{f}: {e}') for f in glob.glob('*.py') for e in [__import__('ast').parse(open(f).read())] and 0 if isinstance(e, SyntaxError) else None]; print(f'✅ 0 hata' if not errors else '\n'.join(errors))"
```

Always do this FIRST — a project with syntax errors cannot run regardless of config.

### 2. Install Dependencies

Check requirements files exist, then install:

```bash
pip install -r requirements.txt
```

If the project has multiple sub-modules with their own `requirements.txt`, install all of them.

### 3. Environment Wiring

Most projects have a hardcoded CONFIG dict that's never wired to `.env`. The fix pattern:

```python
import os
from pathlib import Path
from dotenv import load_dotenv

DOT_ENV = Path(__file__).parent / ".env"
if DOT_ENV.exists():
    load_dotenv(DOT_ENV, override=True)

def _env_anahtar(anahtar, varsayilan=""):
    """Read env var, ignore masked (***) values."""
    deger = os.environ.get(anahtar, "").strip()
    if not deger or deger == "***":
        return varsayilan
    return deger
```

Key insight: `***` masking is common in shared `.env` files. The helper must skip masked values and fall back to defaults. Use `startswith("***")` not `== "***"` — some editors write `***` with trailing whitespace or comments on the same line.

### 4. Import Structure Audit

Check all module subdirectories have `__init__.py`:

```python
from pathlib import Path
for subdir in ['dashboard', 'llm_provider', 'telegram_bot', 'notion_writer']:
    p = Path('.') / subdir / '__init__.py'
    if not p.exists():
        p.touch()  # or create with content
```

Without `__init__.py`, subdirectory modules cannot be imported.

### 5. Import Verification

Test that the main entry point imports without errors:

```bash
python -c "from main import AIAgentOrchestrator; print('OK')"
```

This is a low-cost sanity check before any actual execution.

### 6. Module Integration Wiring (CRITICAL)

Creating files is NOT enough — each new module must be WIRED into the main
application. Integration means the main loop (main.py), LLM layer (beyin.py),
execution engine (motor.py), CLI (reyment.py), and gateway all need to know
about the new module.

**Integration point map for a typical agent project:**

```
New Module -> motor.py calistir()        -> add if/else or registry entry
           -> main.py imports            -> add to import chain
           -> beyin.py config            -> add to provider list
           -> reyment.py CLI dispatch    -> add subcommand handler
           -> gateway_runner.py startup  -> add to service list
```

**Verification:** After wiring, run:
```bash
python -c "from main import AIAgentOrchestrator; from motor import Motor; from beyin import Beyin"
python -c "from tool_registry import ToolRegistry; r=ToolRegistry(); print(r.calistir('KOMUT_CALISTIR', 'echo test'))"
python test_suite.py
```

**Critical lesson:** Creating 80 standalone files is wasted effort if none are
wired into the main application. Always wire first, verify second.

### 7. Service Connectivity

Check external services that the project depends on:

```bash
# LM Studio / local API
curl -s -m 3 http://localhost:1234/v1/models

# Remote API (DeepSeek, OpenAI — expect 401 without key, but connection works)
curl -s -m 3 -o /dev/null -w "%{http_code}" https://api.deepseek.com/v1/models
```

### 7. Test Run

Execute a minimal task with low max_turns to verify the ReAct loop works end-to-end.

## Reference Files

- [references/env-wiring.md](references/env-wiring.md) — detailed `.env` → config wiring patterns
- [references/windows-launcher.md](references/windows-launcher.md) — `.bat` launcher template for multi-service projects
- [references/module-integration.md](references/module-integration.md) — integrating separate modules (dashboard, telegram, notion, llm provider)

## Pitfalls

1. **Skipping compilation check** — A project with syntax errors will waste time on misleading import errors. Always bulk-check first.
2. **Not handling `***` masking** — Users often share `.env` files with `***` placeholders. Reading them directly gives empty configs. The helper must ignore these.
3. **Forgetting `__init__.py`** — Python 3.3+ doesn't require them for implicit namespace packages, but many projects still rely on explicit imports that fail without them.
4. **Assuming one requirements file** — Multi-module projects often have separate `requirements.txt` in each subdirectory. Check all of them.
6. **Wasting time on config when the real issue is compilation** — Syntax errors block everything. Always check compilation before touching config.
7. **`__init__` attribute ordering** — A common Python bug: referencing `self.attribute` before it's assigned. In `__init__`, define ALL attributes before passing them to other objects:
   ```python
   # WRONG — self.learning used before defined
   self.learning = ClosedLearningLoop()           # line 1
   self.prompt_engine = PromptAssemblyEngine(
       learning_loop=self.learning,                # uses self.learning
   )

   # RIGHT — define first, then use
   self.learning = ClosedLearningLoop()           # define FIRST
   self.prompt_engine = PromptAssemblyEngine(
       learning_loop=self.learning,                # now safe to reference
   )
   ```
8. **Shared JSON files without FileLock** — When multiple processes/modules write to the same JSON file (e.g. `data/jobs.json` shared by dashboard + telegram bot), concurrent writes corrupt the file. Fix:
   ```python
   from filelock import FileLock
   LOCK_FILE = DATA_DIR / "jobs.json.lock"
   def load_jobs() -> dict:
       with FileLock(str(LOCK_FILE), timeout=5):
           if JOBS_FILE.exists():
               return json.loads(JOBS_FILE.read_text())
           return {}
   def save_jobs(jobs: dict):
       with FileLock(str(LOCK_FILE), timeout=5):
           JOBS_FILE.write_text(json.dumps(jobs, indent=2, default=str))
   ```
6. **Testing with real API calls on first run** — Start with the local provider (LM Studio) if available. Save remote API testing for later after the loop works.
