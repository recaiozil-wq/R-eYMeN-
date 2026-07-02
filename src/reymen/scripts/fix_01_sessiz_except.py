#!/usr/bin/env python3
"""
FIX 01 — Sessiz Except Temizleyici
Yapar : except:pass / except Exception:pass → logger.warning(...)
Test  : Her düzeltilen dosyayı ast.parse ile doğrular
Rapor : fix_01_rapor.json + konsol özeti
Kullanım: python fix_01_sessiz_except.py [proje_koku]
"""
import ast, os, sys, json, re, shutil, time
from pathlib import Path
from datetime import datetime

class C:
    RED="\033[91m"; YEL="\033[93m"; GRN="\033[92m"; BLU="\033[94m"; BOLD="\033[1m"; RESET="\033[0m"

def ok(m):   print(f"  {C.GRN}✅ {m}{C.RESET}")
def warn(m): print(f"  {C.YEL}⚠️  {m}{C.RESET}")
def err(m):  print(f"  {C.RED}❌ {m}{C.RESET}")
def hdr(t):  print(f"\n{C.BOLD}{C.BLU}{'═'*60}\n  {t}\n{'═'*60}{C.RESET}")

EXCLUDE = {"__pycache__", ".venv", "venv", "site-packages", ".git", "node_modules", "bot_venv"}
LOGGER_IMPORT = 'import logging\nlogger = logging.getLogger(__name__)'

def logger_ekle(src: str) -> str:
    """Dosyada logger tanımı yoksa, import'lardan sonra logger satırını ekle."""
    if "logger = logging.getLogger" in src or "logger = getLogger" in src or "from hermes_tools" in src:
        return src
    lines = src.splitlines(keepends=True)
    # import satırlarından sonra ekle
    insert_at = 0
    last_import = -1
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("import ") or s.startswith("from "):
            last_import = i
        elif last_import >= 0 and s != "" and not s.startswith("#"):
            break
    if last_import >= 0:
        insert_at = last_import + 1
    lines.insert(insert_at, LOGGER_IMPORT + "\n")
    return "".join(lines)

def except_duzelt(src: str) -> tuple[str, int]:
    """Sessiz except bloklarını logger.warning'e çevir. Düzeltme sayısını döndür."""
    try: tree = ast.parse(src)
    except SyntaxError: return src, 0

    duzeltmeler = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            body = node.body
            # Sessiz except kontrolü: sadece pass/.../None
            sessiz = all(
                isinstance(stmt, (ast.Pass, ast.Expr, ast.Raise)) for stmt in body
            )
            if not sessiz:
                continue

            # node.lineno ile satır numarası
            lineno = node.lineno
            # except satırını bul
            lines = src.splitlines()
            if lineno <= 0 or lineno > len(lines):
                continue

            # Hata mesajı oluştur
            if node.type:
                if isinstance(node.type, ast.Name):
                    exc_type = node.type.id
                elif isinstance(node.type, ast.Attribute):
                    exc_type = node.type.attr
                else:
                    exc_type = "Exception"
            else:
                exc_type = "Exception"

            dosya_adi = os.path.basename(sys.argv[0]).replace(".py", "")
            
            if node.name:
                # except X as e: → e kullan
                warning_line = f"    logger.warning(\"[{dosya_adi}] {exc_type}: %s\", {node.name})"
            else:
                # except: → traceback ekle
                warning_line = f"    logger.warning(\"[{dosya_adi}] {exc_type}\")"

            duzeltmeler.append((lineno, warning_line))

    # Satır bazlı düzeltme (ters sırada)
    lines = src.splitlines(keepends=True)
    for lineno, warning_line in sorted(duzeltmeler, reverse=True):
        # except satırından sonraki pass/... satırlarını bul ve değiştir
        for j in range(lineno, len(lines)):
            s = lines[j].strip()
            if s == "pass" or s == "...":
                # Girintiyi koru
                indent = len(lines[j]) - len(lines[j].lstrip())
                lines[j] = " " * indent + warning_line.strip() + "\n"
                break
            elif s != "" and not s.startswith("#") and not s.startswith("..."):
                break

    return "".join(lines), len(duzeltmeler)

def dosya_test_et(yol: Path) -> tuple[bool, str]:
    try:
        src = yol.read_text(encoding="utf-8", errors="ignore")
        ast.parse(src)
        return True, "AST OK"
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"

def main():
    kok = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(".").resolve()
    hdr(f"FIX 01 — Sessiz Except Temizleyici\nKök: {kok}")
    t0 = time.time()
    rapor = {"tarih": datetime.now().isoformat(), "kok": str(kok), "islenen": [], "atlanan": [], "test_hata": [], "toplam_duzeltme": 0, "test_gecen": []}

    py_files = sorted(kok.rglob("*.py"))
    py_files = [f for f in py_files if not any(p in str(f) for p in EXCLUDE) and "test" not in f.name.lower()]

    print(f"  Taranan dosya: {len(py_files)}")

    for f in py_files:
        try: src = f.read_text(encoding="utf-8", errors="ignore")
        except: continue

        # Sessiz except var mı?
        yeni_src, sayi = except_duzelt(src)
        if sayi == 0:
            continue

        # Logger ekle (gerekirse)
        yeni_src = logger_ekle(yeni_src)

        # Yedek al
        yedek = f.with_suffix(".py.bak")
        shutil.copy2(f, yedek)

        # Yaz
        f.write_text(yeni_src, encoding="utf-8")

        # Test
        gecti, mesaj = dosya_test_et(f)
        if gecti:
            ok(f"{str(f.relative_to(kok)):<60} {sayi} düzeltme")
            yedek.unlink(missing_ok=True)
            rapor["islenen"].append({"dosya": str(f.relative_to(kok)), "duzeltme": sayi})
            rapor["toplam_duzeltme"] += sayi
            rapor["test_gecen"].append(str(f.relative_to(kok)))
        else:
            err(f"{f.relative_to(kok)} → TEST HATA: {mesaj} — GERİ ALINDI")
            shutil.copy2(yedek, f); yedek.unlink(missing_ok=True)
            rapor["test_hata"].append({"dosya": str(f.relative_to(kok)), "hata": mesaj})

    rapor["sure"] = round(time.time() - t0, 1)
    hdr("RAPOR")
    print(f"  Düzeltme          : {C.GRN}{rapor['toplam_duzeltme']}{C.RESET}")
    print(f"  Dosya işlenen     : {C.GRN}{len(rapor['islenen'])}{C.RESET}")
    print(f"  Test geçen        : {C.GRN}{len(rapor['test_gecen'])}{C.RESET}")
    print(f"  Test hata         : {C.RED}{len(rapor['test_hata'])}{C.RESET}")
    print(f"  Süre              : {rapor['sure']}s")

    rapor_yolu = kok / "fix_01_rapor.json"
    with open(rapor_yolu, "w", encoding="utf-8") as fp: json.dump(rapor, fp, ensure_ascii=False, indent=2)
    ok(f"JSON rapor: {rapor_yolu}")

if __name__ == "__main__": main()
