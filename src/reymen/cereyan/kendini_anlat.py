# -*- coding: utf-8 -*-
"""
kendini_anlat.py — ReYMeN / ReYMeN icin oz refleksiyon araci.

Kullanim:
  python kendini_anlat.py            # Tum analiz
  python kendini_anlat.py --ozet     # Sadece ozet
  python kendini_anlat.py --eksik    # Sadece eksikler
  python kendini_anlat.py --cozum    # Sadece cozum tarzi

Bu dosya, ajanin kendi kod tabanini tarayarak:
  1. Kendine ozgu sorun cozme yaklasimini
  2. Eksik kalan / tamamlanmamis konulari
  analiz edip insan okunabilir bir rapor cikarir.
"""

import ast
import os
import sys
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

# ─── Proje Kok ______________________________
PROJE_KOK = Path(__file__).parent.resolve()

# ─── Analiz Edilecek Moduller _______________
ANA_MODULLER = [
    "motor.py",
    "beyin.py",
    "main.py",
    "reyment.py",
    "start.py",
    "planlayici.py",
    "konusma.py" if (PROJE_KOK / "konusma.py").exists() else None,
    "insan_arayuzu.py",
    "closed_learning_loop.py",
    "yetenek_fabrikasi.py",
    "vektorel_hafiza.py",
    "session_db.py",
    "gateway_runner.py",
    "web_ui.py",
    "cli.py",
    "agent_runtime.py",
    "prompt_builder.py",
    "trajectory.py",
    "context_compressor.py",
    "checkpoint_manager.py",
    "tirith_security.py",
]
ANA_MODULLER = [m for m in ANA_MODULLER if m is not None and (PROJE_KOK / m).exists()]


def satir_say(dosya: Path) -> int:
    """Bir dosyadaki kod satiri sayisi (bosluk/yorum haric)."""
    try:
        with open(dosya, encoding="utf-8") as f:
            return sum(
                1 for satir in f
                if satir.strip() and not satir.strip().startswith("#")
            )
    except Exception:
        return 0


def sinif_ve_fonksiyon_bul(dosya: Path) -> tuple[list[str], list[str]]:
    """Bir dosyadaki sinif ve fonksiyon adlarini bul."""
    siniflar, fonksiyonlar = [], []
    try:
        with open(dosya, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(dosya))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                siniflar.append(node.name)
            elif isinstance(node, ast.FunctionDef):
                fonksiyonlar.append(node.name)
    except SyntaxError as _kendini__e74:
        print(f"[UYARI] kendini_anlat.py:75 - {_kendini__e74}")
    return siniflar, fonksiyonlar


def docstring_oku(dosya: Path) -> str:
    """Dosyanin ilk docstring'ini (modul docstring) oku."""
    try:
        with open(dosya, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(dosya))
        return ast.get_docstring(tree) or ""
    except Exception:
        return ""


def import_analizi(dosya: Path) -> list[str]:
    """Bir dosyanin import ettigi ozel modulleri bul."""
    ozel_importlar = set()
    try:
        with open(dosya, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(dosya))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if not alias.name.startswith(("os", "sys", "json", "re", "time",
                                                   "datetime", "pathlib", "typing",
                                                   "threading", "subprocess", "io",
                                                   "argparse", "ast", "inspect")):
                        ozel_importlar.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module and not node.module.startswith(("os", "sys", "json", "re",
                                                                "time", "datetime", "typing",
                                                                "subprocess", "argparse")):
                    ozel_importlar.add(node.module.split(".")[0])
    except Exception as _kendini__e108:
        print(f"[UYARI] kendini_anlat.py:109 - {_kendini__e108}")
    return sorted(ozel_importlar)


# ─── Analiz Fonksiyonlari ___________________

def cozum_tarzi_analizi() -> dict:
    """
    1. Kendine ozgu sorun cozme yaklasimi.
    - Hangi pattern'ler kullaniliyor (ReAct, MCP, ACP, vs)?
    - Hangi tool'lar var?
    - Hangi provider'lar destekleniyor?
    - Mimarisi nasil?
    """
    sonuc = {
        "mimari_pattern": [],
        "tool_sayisi": 0,
        "provider_sayisi": 0,
        "gateway_sayisi": 0,
        "benzersiz_ozellikler": [],
    }

    # Tool analizi
    tools_dir = PROJE_KOK / "tools"
    if tools_dir.exists():
        tool_dosyalari = list(tools_dir.glob("*_tool.py")) + list(tools_dir.glob("*.py"))
        sonuc["tool_sayisi"] = len(tool_dosyalari)
        sonuc["tool_listesi"] = [t.name for t in tool_dosyalari if t.name != "__init__.py"]

    # Provider analizi
    provider_dir = PROJE_KOK / "providers"
    if provider_dir.exists():
        sonuc["provider_sayisi"] = len(list(provider_dir.glob("*.py")))

    # Gateway platform analizi
    gateway_dir = PROJE_KOK / "gateway" / "platforms"
    if not gateway_dir.exists():
        gateway_dir = PROJE_KOK / "gateway"
    if gateway_dir.exists():
        sonuc["gateway_sayisi"] = len(list(gateway_dir.glob("*.py")))

    # Mimari pattern'leri bul
    for modul_adi in ANA_MODULLER:
        dosya = PROJE_KOK / modul_adi
        doc = docstring_oku(dosya)
        if "ReAct" in doc or "react" in doc.lower():
            sonuc["mimari_pattern"].append("ReAct (Dusun-Eylem-Gozlem)")
        if "MCP" in doc:
            sonuc["mimari_pattern"].append("MCP (Model Context Protocol)")
        if "ACP" in doc:
            sonuc["mimari_pattern"].append("ACP (Agent Communication Protocol)")
        if "orchestr" in doc.lower() or "orkest" in doc.lower():
            sonuc["mimari_pattern"].append("Orkestrator (multi-service)")
        if "loop" in doc.lower() or "dongu" in doc.lower():
            sonuc["mimari_pattern"].append("Ogrenme Dongusu (Closed Learning Loop)")

    sonuc["mimari_pattern"] = list(set(sonuc["mimari_pattern"]))

    # Benzersiz ozellikler
    if (PROJE_KOK / "closed_learning_loop.py").exists():
        sonuc["benzersiz_ozellikler"].append("Kapali ogrenme dongusu (FTS5 beceri kristallestirme)")
    if (PROJE_KOK / "yetenek_fabrikasi.py").exists():
        sonuc["benzersiz_ozellikler"].append("Yetenek fabrikasi (beceri otomatik olusturma)")
    if (PROJE_KOK / "vektorel_hafiza.py").exists():
        sonuc["benzersiz_ozellikler"].append("Vektorel hafiza (anlamsal bellek)")
    if (PROJE_KOK / "araclar_ekran.py").exists():
        sonuc["benzersiz_ozellikler"].append("Ekran OCR ve tiklamatik (uygulama otomasyonu)")
    if (PROJE_KOK / "araclar_makro.py").exists():
        sonuc["benzersiz_ozellikler"].append("Makro kaydetme/oynatma")
    if (PROJE_KOK / "uygulama_hafizasi.py").exists():
        sonuc["benzersiz_ozellikler"].append("Uygulama adim hafizasi")
    if (PROJE_KOK / "tirith_security.py").exists():
        sonuc["benzersiz_ozellikler"].append("Tirith guvenlik katmani")
    if (PROJE_KOK / "checkpoint_manager.py").exists():
        sonuc["benzersiz_ozellikler"].append("Checkpoint yonetimi (duraklat/devam ettir)")

    return sonuc


def eksik_analizi() -> list[dict]:
    """
    2. Eksik kalan / tamamlanmamis konular.
    - Dosyalarda 'TODO', 'FIXME', 'XXX', 'pass', 'NotImplementedError' ara.
    - docstring'i olmayan sinif/fonksiyonlari bul.
    - Test dosyalarinda basarisiz testleri goster.
    """
    eksikler = []
    toplam_todo = 0
    toplam_fixme = 0
    toplam_pass = 0
    toplam_not_implemented = 0
    docstring_eksik = []

    for py_dosya in sorted(PROJE_KOK.glob("*.py")):
        if py_dosya.name.startswith("_"):
            continue
        if py_dosya.name == "kendini_anlat.py":
            continue

        icerik = py_dosya.read_text(encoding="utf-8")

        # TODO / FIXME / XXX
        todo_say = icerik.count("# TODO") + icerik.count("#TODO")
        fixme_say = icerik.count("# FIXME") + icerik.count("#FIXME")
        pass_say = sum(1 for satir in icerik.split("\n") if satir.strip() == "pass")
        ni_say = icerik.count("NotImplementedError")

        toplam_todo += todo_say
        toplam_fixme += fixme_say
        toplam_pass += pass_say
        toplam_not_implemented += ni_say

        # Docstring eksik
        siniflar, fonksiyonlar = sinif_ve_fonksiyon_bul(py_dosya)
        for s in siniflar:
            if s in ("Renk", "ServisDurumu", "Servis"):
                continue
            eksikler.append({
                "dosya": py_dosya.name,
                "turu": "eksik_docstring",
                "detay": f"Sinif '{s}' docstring kontrol edilmedi",
            })

        if todo_say > 0 or fixme_say > 0 or ni_say > 0:
            eksikler.append({
                "dosya": py_dosya.name,
                "turu": "yapilacak",
                "detay": f"{todo_say}x TODO, {fixme_say}x FIXME, {ni_say}x NotImplementedError",
            })

    # Test sonuclari
    test_raporu = ""
    test_dosyasi = PROJE_KOK / "test_suite.py"
    if test_dosyasi.exists():
        import subprocess
        try:
            sonuc = subprocess.run(
                [sys.executable, str(test_dosyasi)],
                capture_output=True, text=True, timeout=30, cwd=str(PROJE_KOK),
            )
            test_raporu = sonuc.stdout[-500:] if sonuc.stdout else ""
        except Exception as e:
            test_raporu = f"Test calistirilamadi: {e}"

    return {
        "eksik_listesi": eksikler,
        "istatistik": {
            "toplam_todo": toplam_todo,
            "toplam_fixme": toplam_fixme,
            "toplam_pass": toplam_pass,
            "toplam_not_implemented": toplam_not_implemented,
        },
        "test_sonucu": test_raporu,
    }


def genel_istatistik() -> dict:
    """Projenin genel istatistiklerini cikar."""
    py_dosyalari = list(PROJE_KOK.glob("*.py"))
    toplam_satir = sum(satir_say(d) for d in py_dosyalari)
    toplam_sinif = 0
    toplam_fonksiyon = 0

    for d in py_dosyalari:
        s, f = sinif_ve_fonksiyon_bul(d)
        toplam_sinif += len(s)
        toplam_fonksiyon += len(f)

    # Skills sayisi
    skills_dir = PROJE_KOK / "skills"
    skill_sayisi = 0
    if skills_dir.exists():
        skill_dosyalari = list(skills_dir.rglob("SKILL.md"))
        skill_sayisi = len(skill_dosyalari)

    return {
        "python_dosyasi": len(py_dosyalari),
        "toplam_kod_satiri": toplam_satir,
        "toplam_sinif": toplam_sinif,
        "toplam_fonksiyon": toplam_fonksiyon,
        "skill_sayisi": skill_sayisi,
    }


# ─── Raporlama ______________________________

def rapor_yaz(mod: str = "tum"):
    """Insan okunabilir rapor yazdir."""
    istatistik = genel_istatistik()
    cozum = cozum_tarzi_analizi()
    eksik = eksik_analizi()

    baslik = """
╔══════════════════════════════════════════════════════════╗
║           ReYMeN — Oz Refleksiyon Analizi               ║
║     Kendine Ozgu Sorun Cozme ve Eksik Konular           ║
╚══════════════════════════════════════════════════════════╝
"""
    print(baslik)
    print(f"  Analiz Tarihi: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Proje Koku: {PROJE_KOK}")
    print()

    # ── Genel ──
    if mod in ("tum", "ozet"):
        print("  \033[1mGENEL ISTATISTIK\033[0m")
        print(f"  {'─' * 50}")
        print(f"  Python dosyasi       : {istatistik['python_dosyasi']}")
        print(f"  Toplam kod satiri    : {istatistik['toplam_kod_satiri']}")
        print(f"  Toplam sinif         : {istatistik['toplam_sinif']}")
        print(f"  Toplam fonksiyon     : {istatistik['toplam_fonksiyon']}")
        print(f"  Skill sayisi         : {istatistik['skill_sayisi']}")
        print()

    # ── Cozum Tarzi ──
    if mod in ("tum", "cozum"):
        print("  \033[1m1. KENDINE OZGU SORUN COZME YAKLASIMI\033[0m")
        print(f"  {'─' * 50}")

        if cozum["mimari_pattern"]:
            print("  \033[1mMimari Pattern'ler:\033[0m")
            for p in cozum["mimari_pattern"]:
                print(f"    \u2713 {p}")

        print(f"\n  \033[1mTool Sayisi:\033[0m {cozum['tool_sayisi']}")
        if cozum.get("tool_listesi"):
            print("  Tools:")
            for t in sorted(cozum["tool_listesi"][:10]):
                print(f"    \u2022 {t}")
            if len(cozum["tool_listesi"]) > 10:
                print(f"    ... ve {len(cozum['tool_listesi']) - 10} daha")

        print(f"\n  \033[1mProvider Sayisi:\033[0m {cozum['provider_sayisi']}")
        print(f"  \033[1mGateway Platform:\033[0m {cozum['gateway_sayisi']}")

        if cozum["benzersiz_ozellikler"]:
            print(f"\n  \033[1mBenzersiz Ozellikler:\033[0m")
            for oz in cozum["benzersiz_ozellikler"]:
                print(f"    \u2713 {oz}")
        print()

    # ── Eksikler ──
    if mod in ("tum", "eksik"):
        print("  \033[1m2. EKSIK KALAN / TAMAMLANMAMIS KONULAR\033[0m")
        print(f"  {'─' * 50}")
        print(f"  TODO sayisi           : {eksik['istatistik']['toplam_todo']}")
        print(f"  FIXME sayisi          : {eksik['istatistik']['toplam_fixme']}")
        print(f"  Bos pass bloklari     : {eksik['istatistik']['toplam_pass']}")
        print(f"  NotImplementedError   : {eksik['istatistik']['toplam_not_implemented']}")
        print()

        yapilacaklar = [e for e in eksik["eksik_listesi"] if e["turu"] == "yapilacak"]
        if yapilacaklar:
            print("  \033[1mYapilacaklar / Tamamlanmamis:\033[0m")
            for e in yapilacaklar[:10]:
                print(f"    \u2022 {e['dosya']}: {e['detay']}")
            if len(yapilacaklar) > 10:
                print(f"    ... ve {len(yapilacaklar) - 10} daha")
            print()

        if eksik["test_sonucu"]:
            print("  \033[1mTest Sonucu:\033[0m")
            for satir in eksik["test_sonucu"].split("\n")[-8:]:
                if satir.strip():
                    print(f"    {satir.strip()}")
            print()

    # ── Oneriler ──
    if mod == "tum":
        print("  \033[1m3. ONERILER / GELISTIRME ALANLARI\033[0m")
        print(f"  {'─' * 50}")

        oneriler = []
        if eksik["istatistik"]["toplam_todo"] > 5:
            oneriler.append(f"{eksik['istatistik']['toplam_todo']} adet TODO tamamlanmali")

        if eksik["istatistik"]["toplam_not_implemented"] > 0:
            oneriler.append(f"{eksik['istatistik']['toplam_not_implemented']} adet NotImplementedError implemente edilmeli")

        if istatistik["skill_sayisi"] == 0:
            oneriler.append("Henuz skill kutuphanesi yok — ogrenme dongusu icin skill gerekli")

        if not (PROJE_KOK / "tests").exists() or not list((PROJE_KOK / "tests").glob("test_*.py")):
            oneriler.append("Test dosyalari eksik veya yetersiz")

        for o in oneriler:
            print(f"    \u26a0 {o}")
        if not oneriler:
            print("    \u2713 Kritik eksik bulunamadi.")
        print()

    print(f"  {'─' * 50}")
    print(f"  Analiz tamamlandi.")
    print()


# ─── CLI Entry Point ________________________

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="ReYMeN Oz Refleksiyon Araci",
    )
    parser.add_argument("--ozet", action="store_true", help="Sadece ozet")
    parser.add_argument("--eksik", action="store_true", help="Sadece eksikler")
    parser.add_argument("--cozum", action="store_true", help="Sadece cozum tarzi")

    args = parser.parse_args()

    if args.ozet:
        rapor_yaz("ozet")
    elif args.eksik:
        rapor_yaz("eksik")
    elif args.cozum:
        rapor_yaz("cozum")
    else:
        rapor_yaz("tum")
