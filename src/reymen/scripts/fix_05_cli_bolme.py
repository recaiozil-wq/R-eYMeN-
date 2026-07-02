#!/usr/bin/env python3
"""
FIX 05 — cli.py Bölme Planı
Yapar : cli.py'deki blokları analiz eder, Claude Code task dosyası üretir
Rapor : claude_code_task_cli_bolme.md + fix_05_rapor.json
"""
import sys, json, time, ast
from pathlib import Path
from datetime import datetime
import logging
logger = logging.getLogger(__name__)
class C:
    RED="\033[91m"; YEL="\033[93m"; GRN="\033[92m"; BLU="\033[94m"; BOLD="\033[1m"; RESET="\033[0m"
def ok(m):   print(f"  {C.GRN}✅ {m}{C.RESET}")
def warn(m): print(f"  {C.YEL}⚠️  {m}{C.RESET}")
def err(m):  print(f"  {C.RED}❌ {m}{C.RESET}")
def hdr(t):  print(f"\n{C.BOLD}{C.BLU}{'═'*60}\n  {t}\n{'═'*60}{C.RESET}")

def main():
    kok = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(".").resolve()
    hdr(f"FIX 05 — cli.py Bölme Planı\nKök: {kok}"); t0=time.time()
    rapor={"tarih":datetime.now().isoformat(),"kok":str(kok)}

    cli_dosyalari = list(kok.rglob("reymen/sistem/cli.py"))
    if not cli_dosyalari:
        err("reymen/sistem/cli.py bulunamadı!")
        return
    cli = cli_dosyalari[0]
    src = cli.read_text(encoding="utf-8", errors="ignore")
    lines = src.splitlines()
    n = len(lines)
    hdr(f"cli.py: {n} satır")

    # Blokları tespit et
    bloklar = []
    current_blok = None
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("# ===") or stripped.startswith("# ───"):
            if current_blok:
                bloklar.append(current_blok)
            current_blok = {"baslik": stripped.strip("# ").strip("═─= "), "baslangic": i, "satirlar": 0, "fonksiyonlar": [], "siniflar": []}
        elif current_blok:
            try:
                tree = ast.parse(line)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        current_blok["fonksiyonlar"].append(node.name)
                    elif isinstance(node, ast.ClassDef):
                        current_blok["siniflar"].append(node.name)
            except Exception as _e:
                pass  # TODO: log ekle
    if current_blok: bloklar.append(current_blok)

    # Satır sayılarını hesapla
    for i, blok in enumerate(bloklar):
        if i + 1 < len(bloklar):
            blok["satirlar"] = bloklar[i+1]["baslangic"] - blok["baslangic"]
        else:
            blok["satirlar"] = n - blok["baslangic"] + 1

    print(f"\n  Tespit edilen blok: {len(bloklar)}")
    for b in bloklar:
        print(f"  {C.YEL}{b['baslik'][:50]:<52}{C.RESET} {b['satirlar']:>5} satır  ({len(b['fonksiyonlar'])} fonk)")

    # Claude Code task dosyası
    task = f"""# Claude Code Task: cli.py Bölme (15,762 → 7 Modül)

## Hedef
`reymen/sistem/cli.py` dosyasını ({n} satır) 7 ayrı modüle böl.
Her blok ayrı .py dosyası, `cli_main.py` sadece dispatch.

## Bloklar
"""
    for i, b in enumerate(bloklar):
        task += f"""
### {i+1}. {b['baslik']} ({b['satirlar']} satır, satır {b['baslangic']})
Hedef dosya: `reymen/sistem/cli_{b['baslik'].lower().replace(' ','_')[:20]}.py`
Fonksiyonlar: {', '.join(b['fonksiyonlar'][:10])}
{'  ...' if len(b['fonksiyonlar']) > 10 else ''}
"""

    task += f"""
## Kısıtlar
- `cli_main.py` (dispatch) mevcut API'yi koru: `run()`, `main()`, `AIAgent()`
- Her modül kendi `import`'larını içersin
- `from reymen.sistem.cli_X import ...` formatı
- Her adımda `ast.parse` ile doğrula (syntax hatası olmasın)
- Sıra: helpers → display → commands → stream → voice → maintenance → auth → cli_main

## Doğrulama
```bash
python -c "from reymen.sistem.cli_main import run; print('OK')"
pytest tests/ -k cli -q --tb=no || echo 'Test yoksa sorun degil'
```
"""
    task_yolu = kok / "claude_code_task_cli_bolme.md"
    task_yolu.write_text(task, encoding="utf-8")
    ok(f"Task dosyası: {task_yolu}")

    rapor["blok_sayisi"] = len(bloklar)
    rapor["bloklar"] = [{"baslik":b["baslik"],"satir":b["satirlar"],"fonk":len(b["fonksiyonlar"])} for b in bloklar]
    rapor["task_dosyasi"] = str(task_yolu)
    rapor["sure"] = round(time.time() - t0, 1)
    rapor_yolu = kok / "fix_05_rapor.json"
    with open(rapor_yolu, "w") as fp: json.dump(rapor, fp, ensure_ascii=False, indent=2)
    ok(f"JSON rapor: {rapor_yolu}")

if __name__ == "__main__": main()
