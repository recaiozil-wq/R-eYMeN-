#!/usr/bin/env python3
"""Sessiz except:pass temizleyici.
except Exception: pass -> except Exception as _e: log.warning(...)
"""
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent

# Pattern: except Exception: pass (veya except Exception as _e: pass)
# Yakalamak: girinti + except Exception + opsiyonel as _e + : + newline + girinti + pass
PATTERN1 = re.compile(
    r'(^[ \t]*)except Exception(\s+as\s+\w+)?:\s*\n\s*pass',
    re.MULTILINE
)

REPLACEMENT = (
    r'\1except Exception\2:\n'
    r'\1    _log = __import__("logging").getLogger(__name__)\n'
    r'\1    _log.warning("[SessizExcept] %%s: %%s", type(\2).__name__ if \2 else "?", str(\2) if \2 else "?"))'
)

# Daha basit: sadece except Exception: pass -> except Exception: _log.warning(...)
PATTERN_SADE = re.compile(
    r'(^[ \t]*)except Exception(\s+as\s+(\w+))?:\s*\n\s*pass',
    re.MULTILINE
)

def _replacement(m):
    indent = m.group(1)
    as_var = m.group(2) or ''
    var_name = m.group(3) or '_e'
    if not m.group(2):
        as_var = ' as _e'
        var_name = '_e'
    
    return (
        f'{indent}except Exception{as_var}:\n'
        f'{indent}    __import__("logging").getLogger(__name__).warning(\n'
        f'{indent}        "[SessizExcept] %%s: %%s", type({var_name}).__name__, {var_name}\n'
        f'{indent}    )'
    )

def temizle(dosya: Path) -> bool:
    """Dosyadaki sessiz except:pass'i log.warning'e cevir. True=degisti"""
    try:
        icerik = dosya.read_text(encoding='utf-8')
    except Exception:
        return False
    
    yeni = PATTERN_SADE.sub(_replacement, icerik)
    if yeni != icerik:
        dosya.write_text(yeni, encoding='utf-8')
        return True
    return False

def main():
    hedef = list(KOK.rglob('*.py'))
    # Test/backup/skills dizinlerini atla
    atla = {'__pycache__', 'test', 'hermes-memory-backup', 'ReYMeN_reference', 'skills', '.git', 'venv', 'scripts'}
    
    degisen = 0
    for f in sorted(hedef):
        if any(a in str(f) for a in atla):
            continue
        if temizle(f):
            degisen += 1
            print(f'  ✅ {f.relative_to(KOK)}')
    
    print(f'\nToplam {degisen} dosyada duzeltme yapildi.')

if __name__ == '__main__':
    main()
