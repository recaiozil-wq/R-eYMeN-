"""reymen_launcher.py'den _FINANS sozlugunu ve kullanimini kaldir."""
import re

with open("reymen_launcher.py", "r", encoding="utf-8") as f:
    src = f.read()

# 1. _FINANS sozlugunu kaldir
# _FINANS = { ile baslayip } ile biten blogu bul
pattern_finans = r'^_FINANS = \{[^}]*\}^\n'
src2 = re.sub(pattern_finans, '', src, count=1, flags=re.MULTILINE | re.DOTALL)

if src2 != src:
    print("_FINANS sozlugu kaldirildi")
    src = src2
else:
    print("_FINANS bulunamadi")

# 2. _repl icindeki _FINANS kullanimini kaldir
# "# ── OnceHafiza'dan + _FINANS" ile baslayip "cevap, kaynak = _sor"den onceki satira kadar
pattern_ref = r'# ── OnceHafiza.*?\n(?:.*?\n)*?        cevap, kaynak = _sor\(girdi\)'
src2 = re.sub(pattern_ref, '        cevap, kaynak = _sor(girdi)', src, count=1, flags=re.DOTALL)

if src2 != src:
    print("_FINANS kullanimi kaldirildi")
    src = src2
else:
    print("_FINANS kullanimi bulunamadi")

with open("reymen_launcher.py", "w", encoding="utf-8") as f:
    f.write(src)

print("OK")
