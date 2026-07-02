# -*- coding: utf-8 -*-
"""session_search_tool.py — Oturumlar Arası Arama Aracı.

ReYMeN'teki session_search tool'un ReYMeN uyarlaması.
FTS5 altyapısını (hafiza_genislet.py) kullanarak
geçmiş konuşmalarda tam metin arama yapar.

ToolRegistry'e kayıt için:
    TOOL_META = {...}
    def run(...)
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import logging
logger = logging.getLogger(__name__)

TOOL_META = {
    "ad": "session_search",
    "versiyon": "1.0.0",
    "aciklama": "Geçmiş konuşmalarda FTS5 ile tam metin arama yapar.",
    "kategori": "bellek",
    "parametreler": {
        "sorgu": {
            "tip": "str",
            "aciklama": "FTS5 arama sorgusu (örn: 'decorator AND python')",
            "zorunlu": True,
        },
        "limit": {
            "tip": "int",
            "aciklama": "Maksimum sonuç sayısı (varsayılan: 5)",
            "zorunlu": False,
        },
        "koleksiyon": {
            "tip": "str",
            "aciklama": "Koleksiyon filtresi (boş = tümü)",
            "zorunlu": False,
        },
    },
    "ornek": (
        'SESSION_SEARCH(sorgu="python AND hata", limit=3)'
    ),
}


def _get_hafiza():
    """GelismisHafiza örneğini al."""
    try:
        from reymen.hafiza.hafiza_genislet import GelismisHafiza
        hf = GelismisHafiza()
        if hf._hazir:
            return hf
    except Exception as _session__e52:
        print(f"[UYARI] session_search_tool.py:53 - {_session__e52}")
    return None


def run(sorgu: str, limit: int = 5, koleksiyon: str = "") -> str:
    """Geçmiş konuşmalarda FTS5 ile tam metin arama yap.

    Args:
        sorgu: FTS5 sorgusu (örn: 'decorator AND python')
        limit: Maks sonuç sayısı (varsayılan: 5)
        koleksiyon: Koleksiyon filtresi (boş = tümü)

    Returns:
        str: Formatlanmış arama sonuçları
    """
    if not sorgu.strip():
        return "[SESSION_SEARCH] Sorgu boş, sonuç yok."

    hf = _get_hafiza()
    if not hf:
        # Alternatif: session.db üzerinden SQLite arama
        return _fallback_ara(sorgu, limit, koleksiyon)

    try:
        sonuclar = hf.ara(
            sorgu=sorgu.strip(),
            koleksiyon=koleksiyon,
            limit=limit,
        )
    except Exception as e:
        return f"[SESSION_SEARCH_HATASI] {e}"

    if not sonuclar:
        return f"[SESSION_SEARCH] '{sorgu}' için sonuç bulunamadı."

    satirlar = []
    satirlar.append(f"🔍 '{sorgu}' için {len(sonuclar)} sonuç:")
    satirlar.append("")

    for i, doc in enumerate(sonuclar, 1):
        session = doc.get("session_id", "?")[:20]
        koleks = doc.get("koleksiyon", "?")
        icerik = doc.get("icerik", "")[:200]
        skor = doc.get("skor", 0)
        zaman = doc.get("zaman", "")

        satirlar.append(f"  {i}. [{koleks}] S:{session}")
        if zaman:
            satirlar.append(f"     ⏱ {zaman}")
        satirlar.append(f"     📄 {icerik}")
        satirlar.append(f"     ⭐ skor: {skor:.2f}")
        satirlar.append("")

    return "\n".join(satirlar)


def _fallback_ara(sorgu: str, limit: int = 5, koleksiyon: str = "") -> str:
    """GelismisHafiza yoksa SQLite fallback arama."""
    try:
        import sqlite3
        # session.db veya hafiza.db'yi bul
        db_yollari = [
            Path(".ReYMeN") / "session.db",
            Path(".ReYMeN") / "hafiza.db",
            Path(".reymen_hafiza") / "hafiza.db",
        ]
        for db_yol in db_yollari:
            if db_yol.exists():
                conn = sqlite3.connect(str(db_yol))
                c = conn.cursor()
                # LIKE ile basit arama
                like_sorgu = f"%{sorgu}%"
                satirlar = []
                satirlar.append(f"🔍 '{sorgu}' için fallback arama ({db_yol.name}):")

                try:
                    c.execute(
                        "SELECT session_id, icerik FROM kayitlar WHERE icerik LIKE ? LIMIT ?",
                        (like_sorgu, limit),
                    )
                    rows = c.fetchall()
                    if rows:
                        for i, (sid, icerik) in enumerate(rows, 1):
                            satirlar.append(f"  {i}. S:{str(sid)[:20]} → {str(icerik)[:150]}")
                    else:
                        satirlar.append("  Sonuç yok.")
                except Exception:
                    satirlar.append("  Tablo bulunamadı.")

                conn.close()
                return "\n".join(satirlar)
    except Exception as _session__e144:
        print(f"[UYARI] session_search_tool.py:145 - {_session__e144}")

    return f"[SESSION_SEARCH] Hafıza sistemi mevcut değil (pip install gerekiyor olabilir)."


def check_fn(parametreler: dict) -> tuple:
    """Doğrulama: sorgu parametresi zorunlu."""
    if not parametreler.get("sorgu"):
        return False, "SESSION_SEARCH: 'sorgu' parametresi zorunludur"
    return True, ""


# Kısa kullanım alias
SESSION_SEARCH = run
