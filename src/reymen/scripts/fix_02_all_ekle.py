#!/usr/bin/env python3
"""
FIX 02 — __all__ Ekleyici (121 __init__.py)
Yapar : Boş veya __all__ eksik __init__.py'lere otomatik __all__ ekler
Test  : Her dosyayı AST parse + __all__ varlığı ile doğrular
Rapor : fix_02_rapor.json + konsol özeti
Kullanım: python fix_02_all_ekle.py [proje_koku]
"""
import ast, sys, json, time, shutil
from pathlib import Path
from datetime import datetime

class C:
    RED="\033[91m"; YEL="\033[93m"; GRN="\033[92m"
    BLU="\033[94m"; BOLD="\033[1m"; RESET="\033[0m"
def ok(m):   print(f"  {C.GRN}✅ {m}{C.RESET}")
def warn(m): print(f"  {C.YEL}⚠️  {m}{C.RESET}")
def err(m):  print(f"  {C.RED}❌ {m}{C.RESET}")
def hdr(t):  print(f"\n{C.BOLD}{C.BLU}{'═'*60}\n  {t}\n{'═'*60}{C.RESET}")

def public_isimleri_bul(src: str) -> list[str]:
    public = []
    try: tree = ast.parse(src)
    except SyntaxError: return []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname or alias.name
                if name and not name.startswith("_"): public.append(name.split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"): public.append(node.name)
    return sorted(set(public))

def all_ekle(src: str, isimler: list[str]) -> str:
    all_satir = f'__all__ = {isimler!r}\n'
    if not src.strip(): return all_satir
    lines = src.splitlines(keepends=True)
    # Çok satırlı docstring'i tek blok olarak atla
    insert_at = 0
    in_docstring = False
    doc_char = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if in_docstring:
            if doc_char and doc_char in stripped:
                in_docstring = False
            insert_at = i + 1
            continue
        if stripped.startswith('"""') or stripped.startswith("'''"):
            doc_char = stripped[:3]
            in_docstring = True
            insert_at = i + 1
            continue
        if stripped.startswith("#") or stripped == "":
            insert_at = i + 1
        else:
            break
    lines.insert(insert_at, "\n" + all_satir)
    return "".join(lines)

def dosya_test_et(yol: Path) -> tuple[bool, str]:
    try:
        src = yol.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(src)
        has_all = any(isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets) for node in ast.walk(tree))
        if has_all: return True, "AST OK + __all__ mevcut"
        return False, "__all__ bulunamadı (parse OK ama eksik)"
    except SyntaxError as e: return False, f"SyntaxError: {e}"

def main():
    kok = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(".").resolve()
    hdr(f"FIX 02 — __all__ Ekleyici\nKök: {kok}")
    t0 = time.time()
    rapor = {"tarih": datetime.now().isoformat(), "kok": str(kok), "islenen": [], "zaten_var": [], "test_gecen": [], "test_hata": [], "atlanan": []}
    inits = sorted(kok.rglob("__init__.py"))
    inits = [f for f in inits if not any(p in str(f) for p in ["__pycache__", ".venv", "venv", "site-packages", ".git", "node_modules"])]
    print(f"  Bulunan __init__.py: {len(inits)}")
    for f in inits:
        try: src = f.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc: rapor["atlanan"].append({"dosya": str(f.relative_to(kok)), "sebep": str(exc)}); continue
        if "__all__" in src: rapor["zaten_var"].append(str(f.relative_to(kok))); continue
        yedek = f.with_suffix(".py.bak")
        shutil.copy2(f, yedek)
        try:
            isimler = public_isimleri_bul(src)
            yeni_src = all_ekle(src, isimler)
            f.write_text(yeni_src, encoding="utf-8")
            gecti, mesaj = dosya_test_et(f)
            if gecti:
                ok(f"{str(f.relative_to(kok)):<60} {len(isimler)} isim | {mesaj}")
                yedek.unlink(missing_ok=True)
                rapor["islenen"].append({"dosya": str(f.relative_to(kok)), "isim_sayisi": len(isimler), "isimler": isimler, "test": "PASS"})
                rapor["test_gecen"].append(str(f.relative_to(kok)))
            else:
                err(f"{f.relative_to(kok)} → TEST HATA: {mesaj} — GERİ ALINDI")
                shutil.copy2(yedek, f); yedek.unlink(missing_ok=True)
                rapor["test_hata"].append({"dosya": str(f.relative_to(kok)), "hata": mesaj})
        except Exception as exc:
            warn(f"{f.relative_to(kok)} → atlandı: {exc}")
            if yedek.exists(): shutil.copy2(yedek, f); yedek.unlink(missing_ok=True)
            rapor["atlanan"].append({"dosya": str(f.relative_to(kok)), "sebep": str(exc)})
    rapor["sure"] = round(time.time() - t0, 1)
    hdr("RAPOR")
    print(f"  Eklenen __all__   : {C.GRN}{len(rapor['islenen'])}{C.RESET}")
    print(f"  Zaten vardı       : {C.GRN}{len(rapor['zaten_var'])}{C.RESET}")
    print(f"  Test geçen        : {C.GRN}{len(rapor['test_gecen'])}{C.RESET}")
    print(f"  Test hata         : {C.RED}{len(rapor['test_hata'])}{C.RESET}")
    print(f"  Atlanan           : {C.YEL}{len(rapor['atlanan'])}{C.RESET}")
    print(f"  Süre              : {rapor['sure']}s")
    rapor_yolu = kok / "fix_02_rapor.json"
    with open(rapor_yolu, "w", encoding="utf-8") as fp: json.dump(rapor, fp, ensure_ascii=False, indent=2)
    ok(f"JSON rapor: {rapor_yolu}")
if __name__ == "__main__": main()
