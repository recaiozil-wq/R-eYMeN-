# -*- coding: utf-8 -*-
"""schema_manager.py — ReYMeN Schema Versionlama Yoneticisi.

Alembic + SQLite PRAGMA user_version ile tum veritabanlarinin
schema versiyonlarini takip eder, migrate eder ve raporlar.

Twin module consolidation: reymen.core.schema_manager -> ana kaynak.
Bu modul core'dan import eder + motor_kaydet() ekler.

Desteklenen DB'ler:
  - session.db (ana konusma DB) — Alembic ile
  - self_improve.db — PRAGMA user_version ile
  - hata_toplama.db — PRAGMA user_version ile
  - ogrenmeler.db — PRAGMA user_version ile
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

# Ana kaynak: reymen.core.schema_manager
from src.core.schema_manager import (
    Migration,
    SchemaManager,
    upsert,
)

logger = logging.getLogger(__name__)

PROJE_KOK = Path(__file__).parent.parent.parent  # ReYMeN-Ajan/

# Tum veritabanlari
VERITABANLARI = {
    "session": {
        "yol": PROJE_KOK / ".ReYMeN" / "session.db",
        "aciklama": "Ana konusma oturum DB",
        "yontem": "alembic",
        "versiyon": 1,
    },
    "self_improve": {
        "yol": PROJE_KOK / "reymen" / "sistem" / "self_improve.db",
        "aciklama": "Kendini gelistirme DB",
        "yontem": "pragma",
        "versiyon": 1,
    },
    "hata_toplama": {
        "yol": PROJE_KOK / "reymen" / "sistem" / "hata_toplama.db",
        "aciklama": "Hata toplama DB",
        "yontem": "pragma",
        "versiyon": 1,
    },
    "ogrenmeler": {
        "yol": PROJE_KOK / "reymen" / "cereyan" / "ogrenmeler.db",
        "aciklama": "OnceHafiza ogrenme DB",
        "yontem": "pragma",
        "versiyon": 1,
    },
    "karar": {
        "yol": PROJE_KOK / ".ReYMeN" / "decisions.db",
        "aciklama": "Karar takip DB",
        "yontem": "pragma",
        "versiyon": 1,
    },
}

# Singleton
_SCHEMA: Optional[SchemaManager] = None


def schema_manager() -> SchemaManager:
    global _SCHEMA
    if _SCHEMA is None:
        _SCHEMA = SchemaManager()
    return _SCHEMA


def durum_text() -> str:
    """Schema durumunu text olarak dondur (motor tool'u icin)."""
    yonetici = schema_manager()
    satirlar = ["📊 Schema Durumu:"]
    for db_adi, info in VERITABANLARI.items():
        db_yol = info["yol"]
        versiyon = "?"
        if db_yol.exists():
            try:
                import sqlite3
                con = sqlite3.connect(str(db_yol))
                versiyon = con.execute("PRAGMA user_version").fetchone()[0]
                con.close()
            except Exception as e:
                versiyon = f"hata: {e}"
        else:
            versiyon = "❌ DB yok"
        satirlar.append(f"  {db_adi}: v{versiyon} ({info['yontem']})")
    return "\n".join(satirlar)


def motor_kaydet(motor):
    """Motor'a schema yonetim araclarini kaydet."""
    yonetici = schema_manager()

    if hasattr(motor, "_plugin_arac_kaydet"):
        motor._plugin_arac_kaydet(
            "SCHEMA_DURUM",
            lambda: durum_text(),
            "Veritabani schema versiyon durumu",
        )
        motor._plugin_arac_kaydet(
            "SCHEMA_MIGRATE",
            lambda db="": _schema_migrate_arac(db),
            "Veritabanini migrate et. Parametre: db_adi (bos=batch: tumu). "
            "DB'ler: session, self_improve, hata_toplama, ogrenmeler, karar",
        )
        logger.info("[Schema] Motor'a 2 arac kaydedildi")


def _schema_migrate_arac(db_adi: str) -> str:
    """Schema migrate arac wrapper."""
    import sqlite3
    from datetime import datetime

    yonetici = schema_manager()

    if db_adi:
        hedefler = [db_adi]
    else:
        hedefler = list(VERITABANLARI.keys())

    sonuclar = []
    for db_adi in hedefler:
        info = VERITABANLARI.get(db_adi)
        if not info:
            sonuclar.append(f"❌ {db_adi}: Bilinmeyen DB")
            continue

        db_yol = info["yol"]
        if not db_yol.exists():
            sonuclar.append(f"⚠️ {db_adi}: DB dosyasi yok, olusturuluyor...")
            db_yol.parent.mkdir(parents=True, exist_ok=True)
            con = sqlite3.connect(str(db_yol))
            con.execute("PRAGMA user_version = 1")
            con.commit()
            con.close()

        try:
            con = sqlite3.connect(str(db_yol))
            mevcut = con.execute("PRAGMA user_version").fetchone()[0]
            hedef = info["versiyon"]

            if mevcut < hedef:
                for v in range(mevcut + 1, hedef + 1):
                    _uygula_migrasyon(con, db_adi, v)
                con.commit()
                sonuclar.append(f"✅ {db_adi}: v{mevcut} -> v{hedef}")
            elif mevcut == hedef:
                sonuclar.append(f"➡️ {db_adi}: v{mevcut} (guncel)")
            else:
                sonuclar.append(f"⚠️ {db_adi}: v{mevcut} > v{hedef} (daha ileri)")
            con.close()
        except Exception as e:
            sonuclar.append(f"❌ {db_adi}: {e}")

    return "\n".join(sonuclar)


def _uygula_migrasyon(con, db_adi: str, versiyon: int) -> None:
    """Tek bir migrasyon adimini uygula."""
    from datetime import datetime

    con.execute("PRAGMA user_version = ?", (versiyon,))
    logger.info("[Schema] %s migrate edildi: v%s", db_adi, versiyon)


# Tüm public API'yi re-export et
__all__ = [
    "Migration",
    "SchemaManager",
    "upsert",
    "VERITABANLARI",
    "schema_manager",
    "motor_kaydet",
    "durum_text",
]
