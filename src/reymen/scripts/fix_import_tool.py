#!/usr/bin/env python3
"""Eksik import'ları toplu düzelt — Claude Code'un unuttuklarını ekle."""
import ast, sys
from pathlib import Path

kok = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")

# Her modül için bilinen eksik import mapping'i
FIX_MAP = {
    "re": "import re",
    "os": "import os",
    "sys": "import sys",
    "time": "import time",
    "math": "import math",
    "json": "import json",
    "shutil": "import shutil",
    "logging": "import logging",
    "textwrap": "import textwrap",
    "deque": "from collections import deque",
    "defaultdict": "from collections import defaultdict",
    "OrderedDict": "from collections import OrderedDict",
    "partial": "from functools import partial",
    "Path": "from pathlib import Path",
    "datetime": "from datetime import datetime",
    "List": "from typing import List",
    "Dict": "from typing import Dict",
    "Tuple": "from typing import Tuple",
    "Optional": "from typing import Optional",
    "Any": "from typing import Any",
    "Union": "from typing import Union",
    "contextmanager": "from contextlib import contextmanager",
}

for py_file in sorted((kok / "reymen" / "sistem").glob("cli_*.py")):
    src = py_file.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        print(f"❌ {py_file.name}: SyntaxError — {e}")
        continue

    # Kullanılan tüm name'leri bul
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used.add(node.id)
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            used.add(node.value.id)

    # Eksik import'ları bul
    eklenecek = []
    for name, imp in FIX_MAP.items():
        if name in used and imp not in src:
            eklenecek.append(imp)

    if eklenecek:
        # İlk import satırından veya dosya başından sonra ekle
        lines = src.splitlines(keepends=True)
        insert_at = 0
        for i, line in enumerate(lines):
            s = line.strip()
            if s.startswith("import ") or s.startswith("from "):
                insert_at = i + 1
            elif s.startswith("#") or s == "" or s.startswith('"""') or s.startswith("'''"):
                continue
            elif insert_at == 0:
                break
        for imp in reversed(eklenecek):
            lines.insert(insert_at, imp + "\n")
        py_file.write_text("".join(lines), encoding="utf-8")
        print(f"✅ {py_file.name}: {len(eklenecek)} import eklendi — {eklenecek}")
    else:
        print(f"✅ {py_file.name}: temiz")
