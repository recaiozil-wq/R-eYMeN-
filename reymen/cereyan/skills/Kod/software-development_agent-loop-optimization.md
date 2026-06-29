---
name: agent-loop-optimization
title: "Agent Loop Optimization — 8 Pattern Patch Set"
tags: [optimization, python, agent, performance, debugging]
description: "Eight proven patterns for optimizing Python agent loops: (1) cache deterministic ops outside loops, (2) active error feedback, (3) single init for persistent resources, (4) always-raise retry, (5) dispatch dict instead of if/elif, (6) init-order safety, (7) dataclass return types, (8) print→logging migration. Each pattern includes detection signals, fix code, and verification."
version: 2.0.0
author: marko
license: MIT
platforms: [windows, linux, macos]
audience: developer
related_skills: [python-patterns, benchmark-optimization-loop]
---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Eight proven patterns for optimizing Python agent loops: (1) cache deterministic ops outside loops, (2) active error feedback, (3) single init for persistent resources, (4) always-raise retry, (5) dispatch dict instead of if/elif, (6) init-order safety, (7) dataclass return types, (8) print→logging migration. Each pattern includes detection signals, fix code, and verification. |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Agent Loop Optimization — 3 Pattern Patch Set

## Overview

Three optimization patterns that together reduced per-task DB queries by 93%, fixed thread leaks, and made hallucination detection actively self-correcting. Apply to any Python agent loop where `for tur in range(max_tur)` drives repeated work.

---

## Pattern 1: Cache Deterministic Ops Outside Loops

**Problem:** DB/file queries inside agent loops run identically every tur because the input (user goal) doesn't change. Each call is wasted I/O.

**Detection signal:** Any of these inside a `for ... range(max_tur)` loop:
- `beceri_baglamini_al(hedef, ...)`
- `skill_ara(hedef, ...)`
- `tercih_blogu_al()`
- `sistem_prompt_bloku()`
- Any function call whose arguments don't change between tur iterations

**Fix:** Compute once before the loop, concatenate inside:

```python
# Before loop — one-time compute
_sabit_beceri_baglami = self.learning.beceri_baglamini_al(hedef, adet=3) or ""

# Inside loop — just concatenate
sistem_prompt += _sabit_beceri_baglami
```

**Impact:** N turs × 3 queries → 3 queries. 15 turs × 3 queries = 45 → 3.

**Pitfall:** Only cache if the result truly doesn't change mid-task. Adaptive learning preferences, skill databases, and user goals are stable per task. Don't cache things like `son_gozlem` or `tur` — those DO change.

### Pattern 1b: Cache File-Scanning Results (Motor/Skill Registry)

**Problem:** `__init__` methods that scan disk directories (skills/, plugins/) re-scan every time the object is instantiated — even when the files haven't changed since the last instantiation in the same session.

**Detection signal:** A `__init__` or constructor that calls:
```python
self._skill_araclari_kaydet()  # scans all .md files
self._skill_v2_araclari_kaydet()  # scans again
```

**Fix:** Add a `self._skill_araclari_cache` flag; only scan on first init:

```python
def __init__(self):
    self._skill_araclari_cache = None  # ← cache flag
    self._plugin_moduller_yukle()
    
    # Only scan skills on first call
    if self._skill_araclari_cache is None:
        self._skill_araclari_kaydet()
        self._skill_v2_araclari_kaydet()
        self._skill_araclari_cache = True
```

**Impact:** One-time disk scan per session instead of per-Motor-instantiation. With 500+ skill files, saves thousands of redundant `Path.rglob()` calls.

**Pitfall:** If skills can be added/removed mid-session, set `self._skill_araclari_cache = None` to force re-scan. Not suitable for hot-reload scenarios.

### Pattern 1c: Handle Module Loading Errors Gracefully

**Problem:** `except Exception: pass` around import blocks silently swallows real errors (syntax errors, dependency conflicts, circular imports) alongside expected `ImportError`s. You never know which modules failed and why.

**Detection signal:**
```python
for mod_adi in moduller:
    try:
        importlib.import_module(mod_adi)
    except Exception:
        pass  # ← silent: ImportError AND real errors both swallowed
```

**Fix:** Separate ImportError (module not installed—expected) from other exceptions (real problems):
```python
_yukleme_hatalari = []
for mod_adi in moduller:
    try:
        importlib.import_module(mod_adi)
    except ImportError:
        pass  # Module not installed — expected, silent
    except Exception as _e:
        _yukleme_hatalari.append(f"{mod_adi}: {type(_e).__name__}: {_e}")
if _yukleme_hatalari:
    print(f"[Motor] {len(_yukleme_hatalari)} modul yukleme hatasi:")
    for h in _yukleme_hatalari[:5]:
        print(f"  ⚠ {h}")
```

**Impact:** Real errors become visible instantly during startup. Debug time drops from "blind bisect" to immediate fix.

---

## Pattern 2: Active Error Feedback (Not Passive Logging)

**Problem:** Guard/filter modules detect problems (hallucinations, policy violations) but only `print()` the warning. The LLM never sees it, so the same error repeats next tur.

**Detection signal:**
```python
if self.filter and cevap:
    _, warnings = self.filter.filtrele(cevap)
    for w in warnings:
        print(w)  # ← passive: LLM never sees this
```

### Anti-pattern within Pattern 2: String-Contains Fallacy

A common sub-bug in fallback chains: checking if an error string **contains** a keyword, when the string **always** contains that keyword by construction.

```python
# ❌ WRONG — always False:
sonuc = f"[Bilinmeyen arac]: '{arac}'"  # "Bilinmeyen arac" already in the string!
if "Bilinmeyen arac" not in sonuc:       # always False → fallback never runs
    return sonuc

# ✅ RIGHT — use startswith or sentinel flag:
if _REGISTRY:
    _registry_sonuc = _REGISTRY.calistir(arac, *params)
    if not _registry_sonuc.startswith("[Bilinmeyen arac]"):
        return _registry_sonuc
```

**Detection:** Any `"keyword" not in result` check where `result` is initialized to a default that already contains `"keyword"`. Always use `startswith()` for sentinel prefixes.

**Fix:** When risk exceeds threshold, append corrective message to `mesajlar` and `continue`:

```python
if self.filter and cevap:
    _clean, warnings = self.filter.filtrele(cevap, hedef=hedef)
    if warnings:
        _kritik = sum(1 for w in warnings if "halusinasyon" in w.lower() or "yanlis" in w.lower())
        if _kritik >= 1:
            mesajlar.append({"role": "user", "content":
                f"Onceki yanitinda su sorunlar tespit edildi:\n{warnings_text}\n\n"
                "Lutfen yalnizca dogrulayabildigin bilgileri kullan ve ayni eylemi tekrar dene."})
            continue  # ← restart this tur with corrective context
```

**Impact:** LLM sees its own mistake and self-corrects. No more silent hallucination loops.

**Design rule:** `continue` must come BEFORE `mesajlar.append({"role": "assistant"})` in the loop body. Hallucination filter should be positioned right after the LLM response and before the message is committed to history.

---

## Pattern 3: Single Init for Persistent Resources

**Problem:** Threads, server connections, and API clients get spawned fresh each loop iteration (or worse, each `input()` call). Over time this leaks resources.

**Detection signal:**
```python
while True:
    if hasattr(agent, "module") and agent.module:
        agent.module.baslat_arkaplan(...)  # spawned every loop iteration
```

**Fix:** Move to single init right after the resource is created:

```python
# After agent creation — one-time
if hasattr(agent, "oz_yansima") and agent.oz_yansima:
    agent.oz_yansima.baslat_arkaplan(gecikme_sn=5)

# Inside loop — just check results
    _oz_bildirim = agent.oz_yansima.bildirim_al()
```

**Impact:** 1 thread/total instead of N threads/task. Zero thread leaks.

**Pitfall:** Make sure the init function itself is idempotent (checks `_baslatildi` flag internally) OR only call it once. The pattern above enforces single-call externally.

### Pattern 3b: Add Timeout to Parallel Executors

**Problem:** `ThreadPoolExecutor` + `as_completed(futures)` without timeout. If one worker hangs (network call, infinite loop), the executor never completes — the entire agent loop freezes forever.

```python
# WRONG — no timeout, can freeze:
with ThreadPoolExecutor(max_workers=8) as executor:
    futures = {executor.submit(fn, i): i for i in tasks}
    for future in as_completed(futures):  # blocks forever if one hangs
        idx, result = future.result()
```

**Fix:** Add timeout to both `as_completed` and `future.result()`:
```python
_TO = 30  # seconds per worker

try:
    with ThreadPoolExecutor(max_workers=min(len(tasks), 8)) as executor:
        futures = {executor.submit(fn, i, a, h): (i, a) for i, (a, h) in enumerate(tasks)}
        for future in as_completed(futures, timeout=_TO * len(tasks)):
            i_ref, a_ref = futures[future]
            try:
                idx, result = future.result(timeout=_TO)
            except TimeoutError:
                idx, result = i_ref, f"[Hata]: {a_ref} timeout ({_TO}s)."
            except Exception as _e:
                idx, result = i_ref, f"[Hata]: {_e}"
except TimeoutError:
    missing = set(range(len(tasks))) - set(results.keys())
    for i in missing:
        results[i] = f"[Hata]: Timeout — incomplete."
```

**Impact:** Buggy network tools can't freeze the agent. Failed workers get a timeout error instead of blocking forever.

---

## Applying All Three

Apply in this order (lowest risk first):

1. **Pattern 3** (2 lines, no logic change) — move init calls outside loops
2. **Pattern 1** (refactor) — identify loop-invariant ops, compute once
3. **Pattern 2** (behavior change) — convert passive logs to active feedback

Sub-patterns apply alongside their parent:

- **1b (scan cache):** Add `_cache_flag = None` to `__init__`, wrap first-time disk scans
- **1c (error separation):** Split `except Exception: pass` into `except ImportError: pass` + `except Exception: log`
- **2a (string fallacy):** Search for `"keyword" not in` where the string is initialized containing that keyword — replace with `startswith()`
- **3b (parallel timeout):** Add `timeout=` to every `as_completed()` call in ThreadPoolExecutor usage

---

## Pattern 4: Always-Raise Retry Loop

**Problem:** A retry loop that silently exits after the last failed attempt — the caller gets `None` (or an old variable) instead of an exception, making the failure invisible.

**Detection signal:**
```python
son_hata = None
for deneme in range(MAKS_DENEME):
    try:
        return self._cagir(...)
    except Exception as hata:
        son_hata = hata
        if _rate_limit_mi(hata) and deneme < MAKS_DENEME - 1:
            time.sleep(bekleme)
            bekleme *= 2
        else:
            raise   # ← GOOD: raises non-rate-limit errors immediately

# ← BUG: Falls through here after last rate-limit attempt without raising
# Caller gets None instead of an exception
```

**Fix:** Track `son_hata` and always `raise` it after the loop:

```python
son_hata = None
for deneme in range(1, MAKS_DENEME + 1):
    try:
        return self._cagir(...)
    except Exception as hata:
        son_hata = hata
        if _rate_limit_mi(hata) and deneme < MAKS_DENEME:
            time.sleep(bekleme)
            bekleme *= 2
        else:
            raise  # non-rate-limit → immediate

# Every path through the loop now raises
raise son_hata or RuntimeError("[Beyin] _cagir_ile_retry: unknown error")
```

**Key change:** Use `range(1, MAKS_DENEME + 1)` so `deneme < MAKS_DENEME` correctly identifies "not last attempt." The old `range(MAKS_DENEME)` with `deneme < MAKS_DENEME - 1` always left one silent fallthrough.

**Impact:** Zero silent failures. Every API call either returns or raises.

---

## Pattern 5: Dispatch Dict Instead of if/elif Chains

**Problem:** Long `if provider == "x": ... elif provider == "y": ...` chains are hard to extend, hard to read, and violate Open/Closed principle.

**Detection signal:** 5+ `elif` branches selecting the same kind of operation:

```python
def _cagir(self, provider, model, base_url, api_key, sp, msgs):
    if provider == "lmstudio":
        return self._cagir_lmstudio(...)
    elif provider == "anthropic":
        return self._cagir_anthropic(...)
    elif provider == "moonshot":
        ...
    # 9 more elifs...
    return self._cagir_openai_uyumlu(...)  # default fallback
```

**Fix:** Build a dispatch dict at module level:

```python
_PROVIDER_METOD: dict[str, str] = {
    "lmstudio":          "_cagir_lmstudio",
    "anthropic":         "_cagir_anthropic",
    "moonshot":          "_cagir_moonshot",
    "azure":             "_cagir_azure",
    "bedrock":           "_cagir_bedrock",
    "gemini":            "_cagir_gemini",
    "gemini_cloud":      "_cagir_gemini",
    "lmstudio_reasoning": "_cagir_lmstudio_reasoning",
    "codex_responses":   "_cagir_codex_responses",
}

def _cagir(self, provider, model, base_url, api_key, sp, msgs):
    metod_adi = _PROVIDER_METOD.get(provider, "_cagir_openai_uyumlu")
    metod = getattr(self, metod_adi)
    return metod(base_url, api_key, model, sp, msgs)
```

**Lambda variant** (when arguments differ per provider):

```python
dispatch: dict[str, Callable[[], str]] = {
    "lmstudio": lambda: self._cagir_lmstudio(adim.base_url, adim.model, sp, msgs),
    "anthropic": lambda: self._cagir_anthropic(adim.base_url, adim.api_key, adim.model, sp, msgs),
    ...
}
fn = dispatch.get(adim.provider, lambda: self._cagir_default(adim, sp, msgs))
metin = fn()
```

**Impact:** Adding a new provider = one dict entry + one method. No chain editing, no merge conflicts.

**Pitfall:** Lambda dispatch captures variables by reference — use `functools.partial` if late-binding causes issues.

---

## Pattern 6: Init-Order Safety (Shared State Before Usage)

**Problem:** A `threading.Event` (or other shared-state flag) created inside a method that's called from `__init__`. Other methods called between init start and that method may check the event before it exists → `AttributeError`.

**Detection signal:**
```python
class Beyin:
    def __init__(self, config):
        self.config = config
        self.base_url = ...
        self._fallback_zinciri = self._zincir_insa_et()  # ← calls other methods
        # self._iptal_olayi is NOT YET created

    def _zincir_insa_et(self):
        self._iptal_olayi = threading.Event()  # ← created here
        ...

    def iptal_et(self):
        if hasattr(self, "_iptal_olayi"):  # ← defensive check because unsure
            self._iptal_olayi.set()
```

**Fix:** Create all shared-state flags at the **very top** of `__init__`, before any method calls:

```python
class Beyin:
    def __init__(self, config):
        self._iptal_olayi = threading.Event()  # ← FIRST
        self.config = config
        self.base_url = ...
        self._fallback_zinciri = self._zincir_insa_et()  # ← can safely use _iptal_olayi

    def iptal_et(self):
        self._iptal_olayi.set()  # ← no hasattr check needed
```

**Impact:** No `hasattr` guards needed. All methods can safely check the event from the moment they're called. Predictable crash if something's wrong (fail-fast) instead of silent no-op.

---

## Pattern 7: Dataclass Return Types (Structured Metadata)

**Problem:** A method returns a raw string, but callers need metadata (execution time, token counts, provider info). Callers recompute this metadata separately, leading to inconsistency and duplicated work.

**Detection signal:**
```python
def _cagir(self, ...) -> str:
    t0 = time.time()
    icerik = self._cagir_lmstudio(base_url, model, sp, msgs)
    sure = time.time() - t0
    # ← sure computed here but THROWN AWAY because method returns str
    return icerik

# Caller recomputes:
sonuc = self._cagir(...)
sure = time.time() - t0  # ← recomputed! (inaccurate if there was retry logic)
token = len(sonuc) // 4  # ← computed again
```

**Fix:** Return a frozen dataclass:

```python
@dataclass(frozen=True)
class LLMYanitMeta:
    icerik: str
    sure_sn: float
    giris_token: int = 0
    cikis_token: int = 0

def _cagir(self, ...) -> LLMYanitMeta:
    t0 = time.time()
    giris_token = (len(sp) + len(str(msgs))) // 4
    icerik = self._cagir_lmstudio(...)
    sure = time.time() - t0
    cikis_token = len(icerik) // 4
    return LLMYanitMeta(icerik=icerik, sure_sn=sure,
                        giris_token=giris_token, cikis_token=cikis_token)

# Caller uses directly:
meta = self._cagir(adim, sp, msgs)
sonuc = meta.icerik
logger.info("API: %.2fs, %d tokens", meta.sure_sn, meta.cikis_token)
```

**Impact:** One source of truth for timing and token data. No recomputation. Works with `_cagir_ile_retry` — timing stays accurate across retries.

---

## Pattern 8: Systematic print() → logging Migration

**Problem:** Operational diagnostic messages use `print(f"[Prefix] ...")` — they appear mixed with user-facing CLI output, can't be filtered by log level, and don't include timestamps or source location.

**Detection signal:**
```python
print(f"[Beceri] Indeksleme hatasi ({anahtar}): {e}")        # ← error, should be logger.error
print(f"[Beceri] {eklenen} yeni beceri indekslendi.")        # ← info, should be logger.info
print(f"[Beceri] Merge edildi: {beceri_adi} -> {yol}")       # ← info, should be logger.info
```

**Fix — three categories:**

| print pattern | logging equivalent |
|---|---|
| `print(f"[X] Hata: {e}")` — error conditions | `logger.error("[X] Hata: %s", e)` |
| `print(f"[X] ...basarili...")` — normal flow | `logger.info("[X] %s ...", deger)` |
| `print(f"[X] ...uyari...")` — warnings | `logger.warning("[X] ... %s", deger)` |

**Steps:**

1. Add imports at top of file:
```python
import logging
logger = logging.getLogger(__name__)
```

2. Replace `print(f"[Prefix] ... {var}")` with:
   - `logger.error(...)` — for exception handlers and error paths
   - `logger.warning(...)` — for recoverable issues
   - `logger.info(...)` — for normal operational notifications

3. Use `%s`-style formatting (lazy evaluation) not f-strings:
   ```python
   # ✅ GOOD — lazy, no cost if log level filters it out
   logger.info("[Beceri] %d yeni beceri indeklendi.", eklenen)
   
   # ❌ BAD — f-string is always evaluated
   logger.info(f"[Beceri] {eklenen} yeni beceri indeklendi.")
   ```

4. **Never convert:**
   - `__main__` test block prints (test output is for human reading)
   - CLI user-facing output (`print(Renk.boya(...))` in CLI tools)
   - Progress bars and spinner displays

**Detection (bash one-liner):**
```bash
# Find production print() calls (not in __main__)
grep -n "print(" *.py | grep -v '__main__\|if __name__'
```

**Impact:** Logs can be filtered by severity, routed to files, enriched with timestamps, and searched without grep'ing through user-facing CLI output.

---

## Applying All Patterns

Recommended order (lowest risk first):

1. **Pattern 6** (Init-order) — 1 line move, no behavior change
2. **Pattern 7** (Dataclass return) — refactor return type, caller updates
3. **Pattern 4** (Always-raise) — retry safety, 3-line change
4. **Pattern 8** (print→logging) — mechanical, each replacement is trivial
5. **Pattern 5** (Dispatch dict) — structural, test after
6. **Patterns 1-3** — from original set, larger refactors

## Linked Files

| Path | Contents |
|------|----------|
| `references/patch-transcripts-beyin-guardrails.md` | Full diff transcripts for Pattern 4-8 implementations in beyin.py, guardrails.py, closed_learning_loop.py |

## Verification

After applying all patterns:

```python
python -c "from main import AIAgentOrchestrator; print('OK')"
```

Watch for:
- Pattern 1: Skill/beceri logs only appear on tur 1, not every tur
- Pattern 2: Hallucination trigger shows `[Guardrail]` + corrected continuation
- Pattern 3: Thread init appears only once in logs
