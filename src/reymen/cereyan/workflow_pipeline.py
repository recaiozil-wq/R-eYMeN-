# -*- coding: utf-8 -*-
"""
workflow_pipeline.py — Görev Çözüm Pipeline'ı.

GÖREV -> PLANLAMA -> ÖN DOĞRULAMA -> KOD -> TEST -> GÖZDEN GEÇİRME -> KAYDET

Her aşama broker üzerinden mesajlaşır. Consumer thread'lerde çalışır.
Mevcut sistemdeki orchestrator + ogrenme + hata_cozucu'yu birleştirir.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.reymen.cereyan.broker import (
    Mesaj, MesajTipi, MessageBroker, get_broker, mesaj_gonder
)

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.parent.resolve()
SCRIPTS_DIR = ROOT / "reymen" / "scripts"
COKLER_DIR = ROOT / "cozumler"


# ── Handler'lar (consumer callback'leri) ──────────────────────────────────────

def hata_handler(mesaj: Mesaj) -> None:
    """HATA mesajı → hata_cozucu'ya yönlendir."""
    veri = mesaj.veri
    hata = veri.get("hata", "")
    kod = veri.get("kod", "")
    kaynak = veri.get("kaynak", "")
    hata_imza = _imza_uret_string(hata)

    logger.info("[Pipeline] HATA handler: %s...", str(hata)[:100])

    # Önce çözüm hafızasında ara
    try:
        from reymen.core.ogrenme import cozum_bul, imza_uret, cozum_kaydet
        bulunan = cozum_bul(hata_imza)
        if bulunan:
            logger.info("[Pipeline] Çözüm hafızada bulundu: %s", hata_imza[:12])
            broker = get_broker()
            if broker:
                broker.yayinla_basit(MesajTipi.COZUM_BULUNDU, {
                    "cozum": bulunan,
                    "correlation_id": mesaj.correlation_id,
                })
            return
    except ImportError:
        logger.debug("[Pipeline] ogrenme modülü yok, LLM'e gidilecek")
    except Exception as e:
        logger.warning("[Pipeline] Hafıza sorgu hatası: %s", e)

    # Hafızada yoksa → orchestrator'a LLM çözümü için yönlendir
    try:
        _coz = None
        try:
            from reymen.core.orchestrator import coz_hata
            _coz = coz_hata
        except ImportError as _e:
            logger.warning("[WorkflowPipeline] Modul yuklenemedi (L71): %s", ImportError)
            pass

        if _coz:
            fix_kod = _coz(hata, kod, kaynak or "pipeline")
            if fix_kod and kod:
                # Fix script'ini kaydet
                fix_dizini = COKLER_DIR / "fix"
                fix_dizini.mkdir(parents=True, exist_ok=True)
                fix_path = fix_dizini / f"fix_{datetime.now():%Y%m%d_%H%M%S}.py"
                fix_path.write_text(fix_kod, encoding="utf-8")
                logger.info("[Pipeline] Fix kaydedildi: %s", fix_path)

                # Çözümü hafızaya kaydet
                try:
                    from reymen.core.ogrenme import cozum_kaydet as _kaydet
                    _kaydet(hata_imza, "pipeline", hata[:200], fix_kod, str(fix_path), True)
                except Exception as _e:
                    logger.warning("[WorkflowPipeline] except Exception (L88): %s", Exception)
                    pass

                broker = get_broker()
                if broker:
                    broker.yayinla_basit(MesajTipi.COZUM_BULUNDU, {
                        "cozum": fix_kod,
                        "path": str(fix_path),
                        "correlation_id": mesaj.correlation_id,
                    })
    except Exception as e:
        logger.error("[Pipeline] coz_hata başarısız: %s", e)


def cozum_ara_handler(mesaj: Mesaj) -> None:
    """COZUM_ARA mesajı → ogrenme.cozum_bul."""
    veri = mesaj.veri
    hata = veri.get("hata", "")
    hata_imza = _imza_uret_string(hata)

    try:
        from reymen.core.ogrenme import cozum_bul
        bulunan = cozum_bul(hata_imza)
        if bulunan:
            logger.info("[Pipeline] Çözüm bulundu: %s", hata_imza[:12])
            broker = get_broker()
            if broker:
                broker.yayinla_basit(MesajTipi.COZUM_BULUNDU, {
                    "cozum": bulunan,
                    "imza": hata_imza,
                    "correlation_id": mesaj.correlation_id,
                })
    except Exception as e:
        logger.debug("[Pipeline] cozum_ara hatası: %s", e)


def cozum_kaydet_handler(mesaj: Mesaj) -> None:
    """COZUM_KAYDET mesajı → ogrenme.cozum_kaydet + closed_learning_loop."""
    veri = mesaj.veri
    try:
        from reymen.core.ogrenme import cozum_kaydet
        cozum_kaydet(
            imza=veri.get("imza", ""),
            hata_tipi=veri.get("hata_tipi", "pipeline"),
            hata_ozet=veri.get("ozet", "")[:500],
            cozum_kodu=veri.get("cozum", ""),
            kaynak_script=veri.get("kaynak", ""),
            basarili=veri.get("basarili", True),
        )
        logger.info("[Pipeline] Çözüm hafızaya kaydedildi")
    except Exception as e:
        logger.warning("[Pipeline] cozum_kaydet hatası: %s", e)

    # closed_learning_loop'a da bildir
    try:
        from reymen.cereyan.closed_learning_loop import ClosedLearningLoop
        loop = ClosedLearningLoop()
        loop.beceri_kristallestir(
            beceri_adi=veri.get("ad", "otonom_cozum"),
            aciklama=veri.get("ozet", "")[:200],
            adimlar=veri.get("cozum", "")[:500],
        )
    except Exception as _e:
        logger.warning("[WorkflowPipeline] except Exception (L150): %s", Exception)
        pass


# ── Workflow Pipeline ─────────────────────────────────────────────────────────

def gorev_coz_pipeline(broker: MessageBroker, gorev_tanimi: str, script_path: str = "") -> str:
    """
    Ana pipeline: GÖREV -> PLANLA -> ÖN DOĞRULA -> KOD -> TEST -> İNCELE -> KAYDET
    
    Args:
        broker: MessageBroker instance
        gorev_tanimi: Görev açıklaması
        script_path: Varsa mevcut script yolu
    
    Returns:
        Başarılıysa ".py" dosya yolu, başarısızsa hata mesajı
    """
    corr_id = os.urandom(6).hex()
    logger.info("[Pipeline] ════════════════════════════════════════════")
    logger.info("[Pipeline] GÖREV BAŞLAT: %s", gorev_tanimi[:100])
    
    current_script = script_path
    
    # ── ADIM 1: PLANLAMA ────────────────────────────────────────────────
    logger.info("[Pipeline] ADIM 1/6: PLANLAMA")
    plan = _pipeline_planla(gorev_tanimi)
    if not plan:
        return "❌ PLANLAMA BAŞARISIZ"
    
    # ── ADIM 2: ÖN DOĞRULAMA ────────────────────────────────────────────
    logger.info("[Pipeline] ADIM 2/6: ÖN DOĞRULAMA")
    dogrulama = _pipeline_on_dogrula(plan)
    if not dogrulama.get("gecerli"):
        return f"❌ ÖN DOĞRULAMA: {dogrulama.get('sebep', 'bilinmiyor')}"
    
    # ── ADIM 3: KOD ─────────────────────────────────────────────────────
    logger.info("[Pipeline] ADIM 3/6: KOD ÜRETİMİ")
    if not current_script or not Path(current_script).exists():
        current_script = _pipeline_kod_uret(plan, gorev_tanimi)
        if not current_script:
            return "❌ KOD ÜRETİLEMEDİ"
    
    # ── ADIM 4: TEST ────────────────────────────────────────────────────
    logger.info("[Pipeline] ADIM 4/6: TEST")
    test_sonuc = _pipeline_test_et(current_script)
    if not test_sonuc.get("basarili"):
        # Hata → broker üzerinden çözüm döngüsü
        hata_msg = test_sonuc.get("hata", "bilinmiyor")
        broker.yayinla_basit(MesajTipi.HATA, {
            "hata": hata_msg,
            "kod": Path(current_script).read_text(encoding="utf-8") if Path(current_script).exists() else "",
            "kaynak": current_script,
        }, kaynak="pipeline")
        
        # Çözüm bekle (3 saniye)
        time.sleep(3)
        
        # Fix denenmiş olabilir, tekrar dene
        test_sonuc = _pipeline_test_et(current_script)
        if not test_sonuc.get("basarili"):
            return f"❌ TEST: {hata_msg}"
    
    # ── ADIM 5: GÖZDEN GEÇİR ───────────────────────────────────────────
    logger.info("[Pipeline] ADIM 5/6: GÖZDEN GEÇİRME")
    inceleme = _pipeline_gozden_gecir(current_script)
    if not inceleme.get("basarili"):
        logger.warning("[Pipeline] İnceleme uyarısı: %s", inceleme.get("uyari", ""))
        # Kritik değilse devam et
    
    # ── ADIM 6: KAYDET ─────────────────────────────────────────────────
    logger.info("[Pipeline] ADIM 6/6: KAYDET")
    kayit_path = _pipeline_kaydet(current_script, gorev_tanimi, corr_id)
    
    # Başarılı mesajı
    broker.yayinla_basit(MesajTipi.GOREV_BASARILI, {
        "path": kayit_path,
        "correlation_id": corr_id,
    }, kaynak="pipeline")
    
    # closed_learning_loop'a bildir
    try:
        from reymen.cereyan.closed_learning_loop import ClosedLearningLoop
        loop = ClosedLearningLoop()
        loop.beceri_kristallestir(
            beceri_adi=f"cozum_{corr_id}",
            aciklama=gorev_tanimi[:200],
            adimlar=Path(kayit_path).read_text(encoding="utf-8")[:500],
        )
    except Exception as _e:
        __import__("logging").getLogger(__name__).warning(
            "[SessizExcept] %%s: %%s", type(_e).__name__, _e
        )
    
    logger.info("[Pipeline] ✅ GÖREV TAMAM: %s", kayit_path)
    return kayit_path


# ── Pipeline Alt Adımları ─────────────────────────────────────────────────────

def _pipeline_planla(gorev: str) -> Optional[dict]:
    """ADIM 1: Görevi alt adımlara ayır."""
    return {
        "gorev": gorev[:200],
        "adimlar": ["hazirlik", "cozum", "dogrulama"],
        "hedef_dosya": f"cozum_{datetime.now():%Y%m%d_%H%M%S}.py",
    }


def _pipeline_on_dogrula(plan: dict) -> dict:
    """ADIM 2: Ön koşulları kontrol et."""
    import shutil
    eksikler = []
    
    # Python kontrolü
    if not shutil.which("python"):
        eksikler.append("python")
    
    return {
        "gecerli": len(eksikler) == 0,
        "sebep": ", ".join(eksikler) if eksikler else "",
    }


def _pipeline_kod_uret(plan: dict, gorev: str) -> Optional[str]:
    """ADIM 3: LLM ile Python script'i üret."""
    hedef = plan.get("hedef_dosya", "cozum.py")
    hedef_path = str(SCRIPTS_DIR / hedef)
    
    # LLM'den kod iste
    try:
        from reymen.core.orchestrator import ask_model_to_fix
        kod = ask_model_to_fix("", f"# GOREV: {gorev}\n# ")
        if kod and len(kod) > 10:
            SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
            Path(hedef_path).write_text(kod, encoding="utf-8")
            logger.info("[Pipeline] Kod üretildi: %s (%d byte)", hedef_path, len(kod))
            return hedef_path
    except Exception as e:
        logger.warning("[Pipeline] Kod üretimi başarısız: %s", e)
    
    return None


def _pipeline_test_et(script_path: str) -> dict:
    """ADIM 4: Script'i çalıştır ve doğrula."""
    path = Path(script_path)
    if not path.exists():
        return {"basarili": False, "hata": "Dosya bulunamadı"}
    
    try:
        # Syntax kontrolü
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    except SyntaxError as e:
        return {"basarili": False, "hata": f"SyntaxError: {e}"}
    
    try:
        # Import kontrolü (dosya adını module olarak dene)
        import importlib.util
        spec = importlib.util.spec_from_file_location(path.stem, str(path))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        return {"basarili": True, "cikti": ""}
    except Exception as e:
        return {"basarili": False, "hata": f"{type(e).__name__}: {e}"}


def _pipeline_gozden_gecir(script_path: str) -> dict:
    """ADIM 5: Kodu statik analiz ile gözden geçir."""
    path = Path(script_path)
    if not path.exists():
        return {"basarili": False, "uyari": "Dosya yok"}
    
    kod = path.read_text(encoding="utf-8")
    uyarilar = []
    
    # Basit kalite kontrolleri
    if "except:" in kod and "except Exception" not in kod:
        uyarilar.append("Bare except tespit edildi")
    if len(kod) < 20:
        uyarilar.append("Kod çok kısa")
    
    return {
        "basarili": len(uyarilar) == 0,
        "uyari": "; ".join(uyarilar) if uyarilar else "",
    }


def _pipeline_kaydet(script_path: str, gorev: str, corr_id: str) -> str:
    """ADIM 6: Başarılı script'i .py dosyasına kaydet."""
    hedef = COKLER_DIR / f"cozum_{corr_id}.py"
    hedef.parent.mkdir(parents=True, exist_ok=True)
    
    if Path(script_path).exists():
        import shutil
        shutil.copy2(script_path, hedef)
    else:
        hedef.write_text(f"# {gorev}\n# Correlation ID: {corr_id}\n", encoding="utf-8")
    
    return str(hedef)


# ── Yardımcı ──────────────────────────────────────────────────────────────────

def _imza_uret_string(hata_str: str) -> str:
    """String hata mesajından imza üret."""
    import hashlib
    import re
    soyut = re.sub(r"'[^']*'", "'<VAL>'", str(hata_str))
    soyut = re.sub(r"\d+", "<N>", soyut)
    soyut = re.sub(r"/\S+", "/<PATH>", soyut)
    ham = f"pipeline:{soyut[:200]}"
    return hashlib.sha256(ham.encode()).hexdigest()[:16]


def _get_broker() -> Optional[MessageBroker]:
    try:
        from reymen.cereyan.broker import get_broker as _gb
        return _gb()
    except Exception:
        return None
