# -*- coding: utf-8 -*-
"""Web tetikleyici — web tarama sonuclarina gore ogrenmeleri tetikler."""

import os
import re
import json
import logging
import sqlite3
from datetime import datetime, date
from pathlib import Path

logger = logging.getLogger(__name__)

# Uygulama yolu
try:
    APP_DIR = Path(__file__).resolve().parent.parent.parent
except (NameError, OSError):
    APP_DIR = Path.cwd()

# DB yolu (ogrenmeler.db ile ayni)
DB_YOLU = APP_DIR / ".ReYMeN" / "ogrenmeler.db"

# Bilinen versiyonlar
BILINEN_VERSIYONLAR = {
    "nmap": "7.95",
    "python": "3.11",
    "node": "22",
    "docker": "27",
    "git": "2.45",
    "curl": "8.10",
}


def _var_mi(hedef: str) -> bool:
    """Hedef DB'de var mi kontrol et."""
    try:
        conn = sqlite3.connect(str(DB_YOLU))
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM ogrenmeler WHERE hedef = ?", (hedef,))
        count = c.fetchone()[0]
        conn.close()
        return count > 0
    except sqlite3.Error:
        return False


def _gecerlilik_kontrol(gecerlilik_tarihi: str, tool_adi: str = None) -> str:
    """
    Gecerlilik kontrolu (T4).
    - Tarih gecmisse uyar
    - Tool versiyonu degismisse uyar
    """
    bugun = date.today()
    
    # Tarih kontrolu
    if gecerlilik_tarihi:
        try:
            gec_tarih = datetime.strptime(gecerlilik_tarihi[:10], "%Y-%m-%d").date()
            if gec_tarih < bugun:
                gun_fark = (bugun - gec_tarih).days
                return f"T4: {gun_fark} gun gecikmis - web'de tazele"
        except (ValueError, TypeError, OSError):
            logger.warning("[fix_01_sessiz_except] Exception")
    
    # Versiyon kontrolu
    if tool_adi and tool_adi.lower() in BILINEN_VERSIYONLAR:
        try:
            conn = sqlite3.connect(str(DB_YOLU))
            c = conn.cursor()
            c.execute("""
                SELECT icerik FROM ogrenmeler 
                WHERE hedef = ? ORDER BY olusturulma DESC LIMIT 1
            """, (f"{tool_adi}_versiyon",))
            row = c.fetchone()
            conn.close()
            
            if row:
                kayitli_versiyon = row[0].strip()
                guncel_versiyon = BILINEN_VERSIYONLAR[tool_adi.lower()]
                if kayitli_versiyon != guncel_versiyon:
                    return (f"T4: {tool_adi} versiyon degismis "
                            f"({kayitli_versiyon} -> {guncel_versiyon})")
        except (sqlite3.Error, ValueError, TypeError, OSError):
            logger.warning("[fix_01_sessiz_except] Exception")
    
    return ""


def _icerik_uyumu(icerik1: str, icerik2: str) -> float:
    """Iki icerik arasindaki uyum orani (0-1)."""
    if not icerik1 or not icerik2:
        return 0.5
