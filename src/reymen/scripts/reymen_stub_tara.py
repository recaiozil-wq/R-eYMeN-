#!/usr/bin/env python3
"""reymen_stub_tara.py — ReYMeN'deki eksik/stub fonksiyonlari tara."""
import ast
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent  # reymen/scripts -> reymen
TARA_DIZINLER = [
    ROOT / "reymen_cli",
    ROOT / "cereyan",
    ROOT / "sistem",
    ROOT / "arac",
]

HARIC = {"__pycache__", "test", "tests", ".git", "venv", "node_modules", "__init__.py"}

stubs = []

def _stub_mu(node) -> tuple:
    """(tur, sebep) veya (None, None)"""
    body = node.body
    # pass
    if len(body) == 1 and isinstance(body[0], ast.Pass):
        return ("pass", "")
    # docstring + pass
    if len(body) == 2 and isinstance(body[0], ast.Expr) and isinstance(body[1], ast.Pass):
        return ("pass", "docstring+pass")
    # return "" / None / 0 / [] / {}
    if len(body) == 1 and isinstance(body[0], ast.Return):
        val = body[0].value
        if val is None:
            return ("return", "None")
        if isinstance(val, ast.Constant) and val.value in ("", None, 0, 0.0):
            return ("return", repr(val.value))
        if isinstance(val, ast.List) and len(val.elts) == 0:
            return ("return", "[]")
        if isinstance(val, ast.Dict) and len(val.keys) == 0:
            return ("return", "{}")
        if isinstance(val, ast.Name) and val.id == "None":
            return ("return", "None")
    return (None, None)

for tara in TARA_DIZINLER:
    if not tara.exists():
        print(f"  [YOK] {tara}")
        continue
    for py in sorted(tara.rglob("*.py")):
        if any(h in py.parts for h in HARIC):
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                tur, sebep = _stub_mu(node)
                if tur:
                    stubs.append((tur, sebep, py.relative_to(ROOT), node.name, node.lineno))
            elif isinstance(node, ast.ClassDef):
                tur, sebep = _stub_mu(node)
                if tur:
                    stubs.append((tur, sebep, py.relative_to(ROOT), node.name, node.lineno))

# TODO/FIXME tara
todolar = []
for tara in TARA_DIZINLER:
    if not tara.exists():
        continue
    for py in sorted(tara.rglob("*.py")):
        if any(h in py.parts for h in HARIC):
            continue
        for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#") and ("TODO" in stripped.upper() or "FIXME" in stripped.upper() or "HACK" in stripped.upper() or "XXX" in stripped.upper()):
                rel = py.relative_to(ROOT)
                todolar.append((rel, i, stripped))
                if len(todolar) >= 50:
                    break
        if len(todolar) >= 50:
            break

# NotImplementedError tara
not_implemented = []
for tara in TARA_DIZINLER:
    if not tara.exists():
        continue
    for py in sorted(tara.rglob("*.py")):
        if any(h in py.parts for h in HARIC):
            continue
        if "NotImplementedError" in py.read_text(encoding="utf-8"):
            for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
                if "NotImplementedError" in line:
                    rel = py.relative_to(ROOT)
                    not_implemented.append((rel, i, line.strip()))

# ImportError graceful degrade tara
import_fallback = []
for tara in TARA_DIZINLER:
    if not tara.exists():
        continue
    for py in sorted(tara.rglob("*.py")):
        if any(h in py.parts for h in HARIC):
            continue
        icerik = py.read_text(encoding="utf-8")
        if "ImportError" in icerik or "ModuleNotFoundError" in icerik:
            for i, line in enumerate(icerik.splitlines(), 1):
                if "ImportError" in line or "ModuleNotFoundError" in line:
                    rel = py.relative_to(ROOT)
                    import_fallback.append((rel, i, line.strip()))
                    if len(import_fallback) >= 30:
                        break
        if len(import_fallback) >= 30:
            break

# RAPOR
print("=" * 70)
print("  REYMEN EKSIK FONKSIYON RAPORU")
print("=" * 70)

print(f"\n--- 1. STUB FONKSIYONLAR ({len(stubs)} adet) ---")
if stubs:
    # Grupla
    from collections import Counter
    tur_say = Counter(s[0] for s in stubs)
    print(f"  pass govdeli:      {tur_say.get('pass', 0)}")
    print(f"  return literal:    {tur_say.get('return', 0)}")
    print()
    for tur, sebep, dosya, ad, satir in stubs:
        print(f"  [{tur:6s}] {dosya!s}:{satir} -> {ad} ({sebep})")
else:
    print("  HIC YOK!")

print(f"\n--- 2. TODO/FIXME/HACK ({len(todolar)} adet) ---")
if todolar:
    for dosya, satir, icerik in todolar:
        print(f"  {dosya!s}:{satir} -> {icerik[:80]}")
else:
    print("  HIC YOK!")

print(f"\n--- 3. raise NotImplementedError ({len(not_implemented)} adet) ---")
if not_implemented:
    for dosya, satir, icerik in not_implemented:
        print(f"  {dosya!s}:{satir} -> {icerik[:80]}")
else:
    print("  HIC YOK!")

print(f"\n--- 4. ImportError graceful degrade ({len(import_fallback)} adet) ---")
if import_fallback:
    for dosya, satir, icerik in import_fallback:
        print(f"  {dosya!s}:{satir} -> {icerik[:80]}")
else:
    print("  HIC YOK!")

print(f"\n{'=' * 70}")
print(f"  OZET: {len(stubs)} stub + {len(todolar)} TODO + {len(not_implemented)} NI + {len(import_fallback)} ImportError")
print(f"{'=' * 70}")
