# -*- coding: utf-8 -*-
"""reymen/sistem/coverage_report.py — Coverage Rapor Motoru.

Statik analiz + pytest-cov entegrasyonu.
Zaman bazlı geçmiş tutar ve Web UI'a veri sağlar.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PROJE_KOK = Path(__file__).resolve().parent.parent.parent
HISTORY_FILE = PROJE_KOK / "tests" / "coverage_history.json"


def _modul_sayisi() -> int:
    """reymen altındaki .py dosya sayısı (__init__.py hariç)."""
    say = 0
    for root, _dirs, files in os.walk(str(PROJE_KOK / "reymen")):
        if "__pycache__" in root or "venv" in root or "node_modules" in root:
            continue
        for f in files:
            if f.endswith(".py") and f != "__init__.py":
                say += 1
    return say


def _satir_sayisi() -> int:
    """reymen altındaki toplam Python satır sayısı."""
    toplam = 0
    for root, _dirs, files in os.walk(str(PROJE_KOK / "reymen")):
        if "__pycache__" in root or "venv" in root or "node_modules" in root:
            continue
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                try:
                    with open(path, "rb") as fh:
                        toplam += fh.read().count(b"\n")
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                    )
    return toplam


def _sonuc_al(veri: dict) -> dict:
    """coverage JSON raporundan sonuç al."""
    try:
        toplam = veri.get("totals", {})
        return {
            "toplam_satir": toplam.get("num_statements", 0),
            "kapsanan_satir": toplam.get("covered_statements", 0),
            "kapsanmayan_satir": toplam.get("missing_statements", 0),
            "yuzde": round(toplam.get("percent_covered", 0), 1),
            "modul_sayisi": len(veri.get("files", {})),
            "basari": True,
        }
    except Exception as e:
        return {"basari": False, "hata": str(e)}


def calistir(hizli: bool = False) -> dict:
    """Coverage çalıştır ve sonuç döndür.

    Args:
        hizli: True = sadece reymen/ dizini, False = tüm proje

    Returns:
        {"basari": True, "yuzde": 45.2, "toplam_satir": 1000, ...}
    """
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["COVERAGE_FILE"] = str(PROJE_KOK / ".coverage")

        kaynak = "reymen"
        test_hedef = "tests/ -q --tb=short -x --timeout=30"
        if hizli:
            test_hedef = "tests/test_guvenli_sandbox.py tests/test_hata_topla.py -q --tb=short --timeout=30"

        basla = time.time()

        subprocess.run(
            [sys.executable, "-m", "coverage", "run",
             f"--source={kaynak}",
             "--omit=*/venv/*,*/bot_venv/*,*/node_modules/*,*/__pycache__/*,*/tests/*",
             "-m", "pytest"] + test_hedef.split(),
            cwd=str(PROJE_KOK), capture_output=True, text=True,
            timeout=120, env=env,
        )

        # JSON rapor
        rc = subprocess.run(
            [sys.executable, "-m", "coverage", "json", "-o", "-",
             "--omit=*/venv/*,*/bot_venv/*,*/node_modules/*,*/__pycache__/*,*/tests/*"],
            cwd=str(PROJE_KOK), capture_output=True, text=True,
            timeout=30, env=env,
        )

        sure = round(time.time() - basla, 2)
        veri = json.loads(rc.stdout) if rc.stdout.strip() else {}
        sonuc = _sonuc_al(veri)
        sonuc["sure"] = sure

        # Geçmişe ekle
        _gecmis_ekle(sonuc)

        return sonuc

    except subprocess.TimeoutExpired:
        return {"basari": False, "hata": "Zaman aşımı (120s)", "yuzde": 0}
    except Exception as e:
        logger.warning("Coverage hatası: %s", e)
        return {"basari": False, "hata": str(e), "yuzde": 0}


def statik_analiz() -> dict:
    """Import analizi ile yaklaşık coverage (hızlı)."""
    modul_say = _modul_sayisi()
    satir_say = _satir_sayisi()

    # Import edilebilen modüller
    import_edilebilen = 0
    import_edilemeyen = 0
    for root, _dirs, files in os.walk(str(PROJE_KOK / "reymen")):
        if "__pycache__" in root or "venv" in root or "node_modules" in root:
            continue
        for f in files:
            if f.endswith(".py") and f != "__init__.py":
                mod_path = os.path.join(root, f)
                mod_name = (
                    "reymen."
                    + os.path.relpath(mod_path, str(PROJE_KOK))
                    .replace(os.sep, ".")[:-3]
                )
                try:
                    __import__(mod_name)
                    import_edilebilen += 1
                except Exception:
                    import_edilemeyen += 1

    yuzde = round(
        import_edilebilen / (import_edilebilen + import_edilemeyen) * 100, 1
    ) if (import_edilebilen + import_edilemeyen) > 0 else 0

    sonuc = {
        "basari": True,
        "yuzde": yuzde,
        "toplam_modul": modul_say,
        "toplam_satir": satir_say,
        "import_edilebilen": import_edilebilen,
        "import_edilemeyen": import_edilemeyen,
        "tur": "statik",
    }
    _gecmis_ekle(sonuc)
    return sonuc


def _gecmis_ekle(sonuc: dict) -> None:
    """Sonucu geçmiş dosyasına ekle."""
    try:
        history = []
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE) as f:
                history = json.load(f)

        history.append({
            "tarih": datetime.now().isoformat(),
            "yuzde": sonuc.get("yuzde", 0),
            "toplam_satir": sonuc.get("toplam_satir", 0),
            "kapsanan_satir": sonuc.get("kapsanan_satir", 0),
            "sure": sonuc.get("sure", 0),
            "tur": sonuc.get("tur", "coverage"),
        })

        # Son 100 kayıt
        history = history[-100:]
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.debug("Geçmiş kaydedilemedi: %s", e)


def gecmis_getir(limit: int = 30) -> list[dict]:
    """Geçmiş coverage verilerini getir."""
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE) as f:
            history = json.load(f)
        return history[-limit:]
    except Exception:
        return []
