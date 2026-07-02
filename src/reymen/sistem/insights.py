# -*- coding: utf-8 -*-
"""insights.py — Kullanim icgoruleri.

Agent kullanim istatistiklerinden anlamli icgoruler cikarir.
"""

from pathlib import Path
from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)

USAGE_DIR = Path(__file__).parent / ".ReYMeN" / "usage"
TRAJ_DIR = Path(__file__).parent / ".ReYMeN" / "trajectories"


def en_cok_kullanilan_araclar(limit: int = 5) -> list[tuple[str, int]]:
    """En cok kullanilan araclari bul.

    Returns:
        [(arac_adi, kullanim_sayisi)]
    """
    arac_sayaci = {}
    if not TRAJ_DIR.exists():
        return []

    import json
    for f in sorted(TRAJ_DIR.glob("*.json"))[-20:]:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            for adim in data.get("adimlar", []):
                eylem = adim.get("eylem", "")
                arac = eylem.split("(")[0] if "(" in eylem else eylem
                if arac:
                    arac_sayaci[arac] = arac_sayaci.get(arac, 0) + 1
        except Exception as _e:
            logger.warning("[Insights] except Exception (L33): %s", Exception)
            pass

    return sorted(arac_sayaci.items(), key=lambda x: -x[1])[:limit]


def basari_orani() -> float:
    """Genel basari orani."""
    if not TRAJ_DIR.exists():
        return 0.0

    import json
    basarili = 0
    toplam = 0

    for f in TRAJ_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            for adim in data.get("adimlar", []):
                toplam += 1
                gozlem = adim.get("gozlem", "")
                if "[Hata]" not in gozlem and "[Hatasi]" not in gozlem:
                    basarili += 1
        except Exception as _e:
            logger.warning("[Insights] except Exception (L56): %s", Exception)
            pass

    return round(basarili / max(toplam, 1) * 100, 1)


def gunluk_aktivite() -> dict:
    """Gunluk aktivite ozeti.

    Returns:
        {"tarih": str, "gorev": int, "basari": float}
    """
    import json
    gorev_sayisi = 0
    if TRAJ_DIR.exists():
        gorev_sayisi = len(list(TRAJ_DIR.glob("*.json")))

    return {
        "tarih": date.today().isoformat(),
        "gorev": gorev_sayisi,
        "basari": basari_orani(),
    }


if __name__ == "__main__":
    print(f"En cok kullanilan: {en_cok_kullanilan_araclar()}")
    print(f"Basari orani: %{basari_orani()}")
    print(f"Gunluk: {gunluk_aktivite()}")
