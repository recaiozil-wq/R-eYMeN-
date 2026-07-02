# -*- coding: utf-8 -*-
"""auto_budama.py — ReYMeN otomatik hafiza budama (memory consolidation).

Sorun: Kayitlar ttl_saat=0 (sonsuz) ile kaydediliyor, hic silinemiyor.
Cozum: Zaman bazli budama + koleksiyon limiti + otomatik temizlik dongusu.

Calisma:
  1. Module import edilir edilmez baslar (background thread)
  2. Her 30 dakikada bir:
     - 90 gunden eski tum kayitlari sil (zaman bazli)
     - Koleksiyon basina max 1000 kayit, fazlasi silinir
     - expire_zaman gecmis kayitlari sil
  3. bot_direkt.py, main.py, conversation_loop.py'den cagrilabilir
"""

import logging
import threading
import time
import logging
logger = logging.getLogger(__name__)

log = logging.getLogger(__name__)

# Opsiyonel import (graceful degrade)
try:
    import sqlite3
    from pathlib import Path
    _SQLITE = True
except ImportError:
    _SQLITE = False

# ── Sabitler ──────────────────────────────────────────────────────────
_VARSAYILAN_TTL_GUN = 90          # 90 gun sonra otomatik sil
_MAX_KAYIT_PER_KOL = 1000         # Koleksiyon basina max kayit
_BUDAMA_ARALIK_SN = 1800          # 30 dakika
_auto_thread = None
_auto_stop = threading.Event()


def _db_yollari():
    """hafiza.db ve session.db yollarini bul."""
    try:
        from reymen.hafiza.hafiza_genislet import _DB_PATH as hafiza_yol
    except (ImportError, AttributeError):
        hafiza_yol = str(Path(__file__).parent / ".reymen_hafiza" / "hafiza.db")
    return hafiza_yol


def buda(hafiza_yol: str = "", max_gun: int = _VARSAYILAN_TTL_GUN,
         max_kayit: int = _MAX_KAYIT_PER_KOL) -> dict:
    """Hafizayi buda: eski + asiri kayitlari temizle.

    Uc asama:
      1. expire_zaman gecmis kayitlari sil (TTL)
      2. max_gun'den eski kayitlari sil (zaman bazli)
      3. Koleksiyon basina max_kayit asimi varsa en eski kayitlari sil

    Args:
        hafiza_yol: hafiza.db yolu (bos = otomatik bul)
        max_gun: Gun cinsinden max yas (default 90)
        max_kayit: Koleksiyon basina max kayit (default 1000)

    Returns:
        {"silinen_ttl": N, "silinen_eski": N, "silinen_asiri": N,
         "session_budanan": N, "toplam_session": N}
    """
    sonuc = {"silinen_ttl": 0, "silinen_eski": 0, "silinen_asiri": 0,
             "session_budanan": 0, "toplam_session": 0}

    if not _SQLITE:
        return sonuc

    if not hafiza_yol:
        hafiza_yol = _db_yollari()

    # --- 1. Hafiza.db budama ---
    if Path(hafiza_yol).exists():
        try:
            conn = sqlite3.connect(hafiza_yol)
            conn.row_factory = sqlite3.Row
            simdi = time.time()
            esik_gun = simdi - (max_gun * 86400)

            # 1a. TTL gecmis kayitlari sil
            cur = conn.execute(
                "DELETE FROM kayitlar WHERE expire_zaman > 0 AND expire_zaman < ?",
                (simdi,),
            )
            sonuc["silinen_ttl"] = cur.rowcount

            # 1b. max_gun'den eski kayitlari sil (ttl=0 olanlar dahil)
            cur = conn.execute(
                "DELETE FROM kayitlar WHERE zaman < ?",
                (esik_gun,),
            )
            sonuc["silinen_eski"] = cur.rowcount

            # 1c. Koleksiyon basina max kayit kontrolu
            for row in conn.execute(
                "SELECT koleksiyon, COUNT(*) as n FROM kayitlar "
                "GROUP BY koleksiyon HAVING n > ?",
                (max_kayit,),
            ).fetchall():
                kol = row["koleksiyon"]
                sil = row["n"] - max_kayit
                conn.execute(
                    "DELETE FROM kayitlar WHERE rowid IN ("
                    "SELECT rowid FROM kayitlar WHERE koleksiyon=? "
                    "ORDER BY zaman ASC LIMIT ?)",
                    (kol, sil),
                )
                sonuc["silinen_asiri"] += sil

            conn.commit()
            conn.close()

            # Session DB budama
            try:
                _session_budama(max_gun)
                sonuc["session_budanan"] = 1
            except Exception as _auto_bud_e118:
                print(f"[UYARI] auto_budama.py:119 - {_auto_bud_e118}")

        except Exception as e:
            log.error("buda hatasi (hafiza): %s", e)

    # --- 2. Session.db budama ---
    try:
        from reymen.hafiza.session_db import AdvancedSessionStorage
        ROOT = Path(__file__).parent.resolve()
        db_path = str(ROOT.parent / "merkez_db" / "session_cereyan.db")
        storage = AdvancedSessionStorage(db_path)
        s = storage.konsolide_et(max_gun=max_gun, max_session=1000, max_toplam_karakter=500000)
        sonuc["session_budanan"] = s.get("silinen_session", 0)
        sonuc["toplam_session"] = s.get("toplam_session", 0)
    except Exception as _auto_bud_e133:
        print(f"[UYARI] auto_budama.py:134 - {_auto_bud_e133}")

    return sonuc


def _session_budama(max_gun: int):
    """Session DB'de eski kayitlari temizle (alternatif)."""
    try:
        from reymen.hafiza.session_db import AdvancedSessionStorage
        ROOT = Path(__file__).parent.resolve()
        db_path = str(ROOT / ".ReYMeN" / "session.db")
        storage = AdvancedSessionStorage(db_path)
        storage.konsolide_et(max_gun=max_gun, max_session=1000, max_toplam_karakter=500000)
    except Exception as _auto_bud_e147:
        print(f"[UYARI] auto_budama.py:148 - {_auto_bud_e147}")


# ── Otomatik Budama Thread ──────────────────────────────────────────

def _budama_dongusu():
    """Arka planda periyodik budama yap."""
    while not _auto_stop.is_set():
        try:
            sonuc = buda()
            toplam = sonuc["silinen_ttl"] + sonuc["silinen_eski"] + sonuc["silinen_asiri"]
            if toplam > 0:
                log.info(
                    "[AutoBudama] %d kayit silindi (ttl=%d, eski=%d, asiri=%d, session=%d)",
                    toplam, sonuc["silinen_ttl"], sonuc["silinen_eski"],
                    sonuc["silinen_asiri"], sonuc["session_budanan"],
                )
        except Exception as _auto_bud_e165:
            print(f"[UYARI] auto_budama.py:166 - {_auto_bud_e165}")
        _auto_stop.wait(_BUDAMA_ARALIK_SN)


def baslat(interval_sn: int = _BUDAMA_ARALIK_SN) -> bool:
    """Otomatik budama thread'ini baslat.

    Args:
        interval_sn: Kac saniyede bir budama yapilsin (default 1800 = 30dk)

    Returns:
        True basarili, False zaten calisiyor
    """
    global _auto_thread, _BUDAMA_ARALIK_SN
    if _auto_thread and _auto_thread.is_alive():
        return False
    _BUDAMA_ARALIK_SN = interval_sn
    _auto_stop.clear()
    _auto_thread = threading.Thread(
        target=_budama_dongusu,
        daemon=True,
        name="auto-budama",
    )
    _auto_thread.start()
    return True


def durdur():
    """Otomatik budama thread'ini durdur."""
    _auto_stop.set()
    global _auto_thread
    if _auto_thread:
        _auto_thread = None


def durum() -> dict:
    """Budama thread durumu."""
    return {
        "calisiyor": _auto_thread is not None and _auto_thread.is_alive(),
        "aralik_sn": _BUDAMA_ARALIK_SN,
        "max_gun": _VARSAYILAN_TTL_GUN,
        "max_kayit_per_kol": _MAX_KAYIT_PER_KOL,
    }


# ── Module baslangicinda otomatik basla ─────────────────────────────
baslat()


if __name__ == "__main__":
    print("=== AutoBudama Test ===")
    print(f"Durum: {durum()}")
    sonuc = buda()
    print(f"Budama sonucu: {sonuc}")
    print("Otomatik thread calisiyor:", durum()["calisiyor"])
    print("[OK] Test gecti")
