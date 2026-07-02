# -*- coding: utf-8 -*-
"""
motor_tool.py — Bot'lar icin motor arayüzü.

Bu modül, Telegram/Discord bot'lari ve diger platform gateway'leri icin
ReYMeN motor'una erisim saglar. Dogrudan motor.py'yi import etmek yerine
buradan erisilir (bagimliliklari soyutlar).

Kullanim (bot icinde):
    from reymen.scripts.motor_tool import motor_erisimi_al, motor_calistir
    
    motor = motor_erisimi_al()
    sonuc = motor_calistir("bir dosya olustur")

Kullanim (scripts/ icinde):
    python -m reymen.scripts.motor_tool "kullanici hedefi"
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# ── Motor Erisimi ─────────────────────────────────────────────────────────

_MOTOR_INSTANCE = None


def motor_erisimi_al() -> Any:
    """Motor singleton'ina erisir.
    
    Motor, tool registry, plugin manager ve diger alt bilesenleri
    yukler. Her cagrıda yeniden yukleme yapmaz (singleton).
    
    Returns:
        Motor instance'i veya None (yuklenemezse)
    """
    global _MOTOR_INSTANCE
    if _MOTOR_INSTANCE is not None:
        return _MOTOR_INSTANCE

    try:
        ROOT = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(ROOT.parent))  # ReYMeN-Ajan/

        from reymen.cereyan.motor import Motor

        _MOTOR_INSTANCE = Motor()
        logger.info("[MotorTool] Motor basariyla yuklendi")

        # Scripts tool'larini kaydet (varsa)
        try:
            from reymen.scripts.ReYMeN_tools import motor_kaydet as _scripts_kaydet
            _scripts_kaydet(_MOTOR_INSTANCE)
            logger.info("[MotorTool] ReYMeN_tools scriptleri kaydedildi")
        except ImportError:
            logger.debug("[MotorTool] ReYMeN_tools bulunamadi, atlaniyor")
        except Exception as e:
            logger.warning("[MotorTool] ReYMeN_tools kayit hatasi: %s", e)

        # Delegasyon araclarini kaydet (varsa)
        try:
            from reymen.ag.delegasyon import motor_kaydet as _delegasyon_kaydet
            _delegasyon_kaydet(_MOTOR_INSTANCE)
            logger.info("[MotorTool] Delegasyon araclari kaydedildi")
        except ImportError:
            logger.debug("[MotorTool] Delegasyon modulu bulunamadi, atlaniyor")
        except Exception as e:
            logger.warning("[MotorTool] Delegasyon kayit hatasi: %s", e)

        return _MOTOR_INSTANCE

    except Exception as e:
        logger.error("[MotorTool] Motor yukleme hatasi: %s", e)
        return None


def motor_calistir(
    hedef: str,
    baglam: Optional[Dict[str, Any]] = None,
    timeout: int = 120,
) -> Dict[str, Any]:
    """Motor uzerinden bir hedefi calistirir.
    
    Args:
        hedef: Kullanici hedefi / komut
        baglam: Ek baglam bilgisi (opsiyonel)
        timeout: Zaman asimi saniye
        
    Returns:
        {
            "basarili": bool,
            "sonuc": str (veya hata mesaji),
            "sure": float,
            "hata": str (opsiyonel),
        }
    """
    motor = motor_erisimi_al()
    if motor is None:
        return {
            "basarili": False,
            "sonuc": "[HATA] Motor yuklenemedi",
            "sure": 0.0,
            "hata": "Motor instance'i olusturulamadi",
        }

    baslangic = time.time()
    try:
        # Motor'un coz metodunu cagir
        sonuc = motor.coz(hedef, baglam or {})

        sure = round(time.time() - baslangic, 2)
        basarili = sonuc.get("basarili", False) if isinstance(sonuc, dict) else True

        return {
            "basarili": basarili,
            "sonuc": str(sonuc) if not isinstance(sonuc, dict) else str(sonuc.get("sonuc", sonuc.get("cikti", sonuc))),
            "sure": sure,
            "ham_sonuc": sonuc,
        }

    except Exception as e:
        sure = round(time.time() - baslangic, 2)
        logger.error("[MotorTool] Calistirma hatasi: %s", e)
        return {
            "basarili": False,
            "sonuc": f"[HATA] {type(e).__name__}: {e}",
            "sure": sure,
            "hata": traceback.format_exc(),
        }


def motor_araclari_listele() -> List[Dict[str, str]]:
    """Motor'a kayitli tum araclari listeler.
    
    Returns:
        [{"ad": "arac_adi", "aciklama": "..."}, ...]
    """
    motor = motor_erisimi_al()
    if motor is None:
        return []

    araclar = []
    try:
        if hasattr(motor, "_plugin_araclar") and motor._plugin_araclar:
            for ad, deger in motor._plugin_araclar.items():
                aciklama = ""
                if isinstance(deger, tuple) and len(deger) >= 2:
                    aciklama = str(deger[1]) if deger[1] else ad
                else:
                    aciklama = str(deger) if hasattr(deger, "__doc__") and deger.__doc__ else ad
                araclar.append({"ad": ad, "aciklama": aciklama[:200]})

        if hasattr(motor, "araclar") and motor.araclar:
            for ad, deger in motor.araclar.items():
                if not any(a["ad"] == ad for a in araclar):
                    araclar.append({"ad": ad, "aciklama": str(deger)[:200]})

    except Exception as e:
        logger.warning("[MotorTool] Arac listeleme hatasi: %s", e)

    return araclar


def motor_durum() -> Dict[str, Any]:
    """Motor durum bilgisini dondurur.
    
    Returns:
        Motor durumu (arac sayisi, plugin sayisi, vs.)
    """
    motor = motor_erisimi_al()
    if motor is None:
        return {"durum": "yuklenemedi", "arac_sayisi": 0}

    try:
        arac_sayisi = 0
        if hasattr(motor, "_plugin_araclar") and motor._plugin_araclar:
            arac_sayisi += len(motor._plugin_araclar)
        if hasattr(motor, "araclar") and motor.araclar:
            arac_sayisi += len(motor.araclar)

        return {
            "durum": "hazir",
            "arac_sayisi": arac_sayisi,
            "motor_tipi": type(motor).__name__,
        }
    except Exception as e:
        return {"durum": "hata", "hata": str(e), "arac_sayisi": 0}


def motor_kaydet(motor) -> None:
    """Motor'a bu modulun tool'larini kaydeder.
    
    Bu fonksiyon, motor._plugin_arac_kaydet API'sine uygun olarak
    scripts tool'larini motora ekler.
    
    Kaydettigi araclar:
        - MOTOR_CALISTIR: Motor uzerinden hedef calistir
        - MOTOR_ARAC_LISTELE: Motor arac listesi
        - MOTOR_DURUM: Motor durumu
    """
    try:
        motor._plugin_arac_kaydet(
            "MOTOR_CALISTIR",
            _motor_calistir_araci,
            "MOTOR_CALISTIR(hedef, baglam) — Motor uzerinden bir hedefi "
            "calistirir. Parametreler: hedef=hedef_metni (zorunlu), "
            "baglam=json_baglam (opsiyonel). "
            "Ornek: MOTOR_CALISTIR(hedef='Dosya olustur')",
        )

        motor._plugin_arac_kaydet(
            "MOTOR_ARAC_LISTELE",
            _motor_arac_listele_araci,
            "MOTOR_ARAC_LISTELE() — Motor'a kayitli tum araclari listeler. "
            "Ornek: MOTOR_ARAC_LISTELE()",
        )

        motor._plugin_arac_kaydet(
            "MOTOR_DURUM",
            _motor_durum_araci,
            "MOTOR_DURUM() — Motor durum bilgisini gosterir: "
            "arac sayisi, motor tipi, calisma durumu. "
            "Ornek: MOTOR_DURUM()",
        )

        logger.info("[MotorTool] 3 arac kaydedildi: MOTOR_CALISTIR, MOTOR_ARAC_LISTELE, MOTOR_DURUM")

    except Exception as e:
        logger.warning("[MotorTool] Arac kayit hatasi: %s", e)


def _motor_calistir_araci(**kw) -> str:
    """MOTOR_CALISTIR aracı: motor uzerinden hedef calistir."""
    args = kw.get("args", [])
    hedef = args[0] if args else kw.get("hedef", "")
    baglam_str = args[1] if len(args) > 1 else kw.get("baglam", "{}")

    if not hedef:
        return "[HATA] MOTOR_CALISTIR: 'hedef' parametresi zorunlu"

    baglam = {}
    if baglam_str:
        try:
            baglam = json.loads(baglam_str) if isinstance(baglam_str, str) else baglam_str
        except json.JSONDecodeError:
            baglam = {"raw": baglam_str}

    sonuc = motor_calistir(hedef, baglam)

    if sonuc.get("basarili"):
        return (
            f"[MOTOR_CALISTIR] Basarili ({sonuc['sure']:.1f}s)\n"
            f"  Sonuc: {str(sonuc['sonuc'])[:500]}"
        )
    return (
        f"[MOTOR_CALISTIR] Hata ({sonuc['sure']:.1f}s)\n"
        f"  Hata: {sonuc.get('hata', sonuc.get('sonuc', 'Bilinmeyen'))[:300]}"
    )


def _motor_arac_listele_araci(**kw) -> str:
    """MOTOR_ARAC_LISTELE aracı: motor arac listesi."""
    _ = kw
    araclar = motor_araclari_listele()
    if not araclar:
        return "[MOTOR_ARAC_LISTELE] Motor'a kayitli arac bulunamadi"

    lines = [f"[MOTOR_ARAC_LISTELE] Toplam {len(araclar)} arac:"]
    for arac in araclar[:30]:
        ad = arac.get("ad", "?")
        aciklama = arac.get("aciklama", "")[:80]
        lines.append(f"  - {ad}: {aciklama}")

    if len(araclar) > 30:
        lines.append(f"  ... ve {len(araclar) - 30} arac daha")

    return "\n".join(lines)


def _motor_durum_araci(**kw) -> str:
    """MOTOR_DURUM aracı: motor durumu."""
    _ = kw
    durum = motor_durum()
    return (
        f"[MOTOR_DURUM]\n"
        f"  Durum: {durum.get('durum', '?')}\n"
        f"  Arac Sayisi: {durum.get('arac_sayisi', 0)}\n"
        f"  Motor Tipi: {durum.get('motor_tipi', '?')}"
    )


# ── CLI Kullanimi ────────────────────────────────────────────────────────

def main():
    """CLI'den dogrudan calistirma: python motor_tool.py <hedef>"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    hedef = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "test"
    print(f"\n🔧 MotorTool: {hedef[:60]}")
    print("=" * 50)

    sonuc = motor_calistir(hedef)
    print(f"\n✅ Basarili: {sonuc['basarili']}")
    print(f"⏱️  Sure: {sonuc['sure']:.1f}s")
    print(f"\n📋 Sonuc:\n{str(sonuc['sonuc'])[:1000]}")

    if sonuc.get("hata"):
        print(f"\n❌ Hata:\n{sonuc['hata'][:500]}")


if __name__ == "__main__":
    main()
