# -*- coding: utf-8 -*-
"""
skill_library.py — Skill kütüphane yöneticisi.

Skill dosyalarını bir kütüphane veritabanında (SQLite) yönetir:
- Kayıt formatı: {id, baslik, icerik_ozeti, etiketler, kaynak, aktif}
- Skill dosyalarını (.md) bir dizinden kütüphaneye senkronize etme
- Etiket/baslik bazinda arama
- CRUD işlemleri (kaydet, get, sil)

Kullanım:
    from skill_library import SkillLibrary
    lib = SkillLibrary()
    lib.sync("skills/")
    sonuclar = lib.ara("ag izleme")
"""

from __future__ import annotations

import logging
import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Varsayılan yollar ───────────────────────────────────────────────────────
ROOT = Path(__file__).parent.resolve()
DB_YOLU = ROOT / ".ReYMeN" / "skill_library.db"

_yazma_kilit = threading.Lock()


# ── YAML Front-Matter Ayrıştırıcı ───────────────────────────────────────────

def _yaml_front_matter_parse(content: str) -> tuple[dict[str, Any], str]:
    """
    .md dosyasındaki YAML front-matter'ı ayrıştırır.

    Desteklenen alanlar: title, name, description, tags
    ---
    title: ...
    tags: [tag1, tag2]
    ---

    Returns:
        (meta_dict, body_text)
    """
    meta: dict[str, Any] = {}
    content_clean = content.lstrip("\ufeff")  # BOM kaldır
    match = re.match(r"^---\s*\n(.*?)\n---", content_clean, re.DOTALL)
    if not match:
        return meta, content_clean

    yaml_blok = match.group(1)
    body = content_clean[match.end():].strip()

    for line in yaml_blok.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().lower()
        val = val.strip()

        if not val:
            continue

        # tags: [a, b, c] veya tags: [a, b, c]
        if key == "tags":
            # [...] formatı
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1]
                taglar = [t.strip().strip('"').strip("'") for t in inner.split(",")]
                meta["etiketler"] = [t for t in taglar if t]
            else:
                meta["etiketler"] = [t.strip() for t in val.split(",") if t.strip()]
        elif key == "title":
            meta["baslik"] = val.strip('"').strip("'")
        elif key == "name":
            meta["id"] = val.strip('"').strip("'")
        elif key == "description":
            meta["icerik_ozeti"] = val.strip('"').strip("'")

    # id yoksa dosya adından türet
    if "id" not in meta:
        meta["id"] = ""

    return meta, body


# ── Veritabanı ──────────────────────────────────────────────────────────────

def _kur(con: sqlite3.Connection) -> None:
    """skills tablosunu oluştur."""
    con.executescript("""
        CREATE TABLE IF NOT EXISTS skills (
            id              TEXT PRIMARY KEY,
            baslik          TEXT NOT NULL DEFAULT '',
            icerik_ozeti    TEXT NOT NULL DEFAULT '',
            etiketler       TEXT NOT NULL DEFAULT '',
            kaynak          TEXT NOT NULL DEFAULT '',
            aktif           INTEGER NOT NULL DEFAULT 0,
            son_guncelleme  TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_skills_aktif      ON skills(aktif);
        CREATE INDEX IF NOT EXISTS idx_skills_etiketler  ON skills(etiketler);
    """)
    # Migration: eski tabloya kolon ekleme (güvenli)
    for kolon, tip in [("baslik", "TEXT NOT NULL DEFAULT ''"),
                        ("icerik_ozeti", "TEXT NOT NULL DEFAULT ''"),
                        ("etiketler", "TEXT NOT NULL DEFAULT ''"),
                        ("kaynak", "TEXT NOT NULL DEFAULT ''"),
                        ("aktif", "INTEGER NOT NULL DEFAULT 0"),
                        ("son_guncelleme", "TEXT NOT NULL DEFAULT (datetime('now'))")]:
        try:
            con.execute(f"ALTER TABLE skills ADD COLUMN {kolon} {tip}")
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )


@contextmanager
def _baglanti():
    con = sqlite3.connect(str(DB_YOLU), timeout=15, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def _db_kur():
    DB_YOLU.parent.mkdir(parents=True, exist_ok=True)
    with _baglanti() as con:
        _kur(con)


# ── SkillLibrary Sınıfı ────────────────────────────────────────────────────

class SkillLibrary:
    """
    Skill kütüphane yöneticisi.

    Skill'leri bir SQLite veritabanında yönetir:
    - kaydet / get / sil / ara
    - sync: Bir dizindeki .md dosyalarını kütüphaneye ekle/güncelle
    """

    def __init__(self, db_yolu: str | Path | None = None):
        """
        Args:
            db_yolu: Veritabanı yolu (None = varsayılan)
        """
        self._db_yolu = Path(db_yolu) if db_yolu else DB_YOLU
        _db_kur()

    # ── Dahili ──────────────────────────────────────────────────────────

    def _con(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self._db_yolu), timeout=15, check_same_thread=False)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
        return con

    # ── Kaydet (upsert) ─────────────────────────────────────────────────

    def kaydet(self, skill_dict: dict[str, Any]) -> str:
        """
        Skill'i kütüphaneye ekle veya güncelle (upsert).

        Args:
            skill_dict: {
                "id": str (zorunlu),
                "baslik": str,
                "icerik_ozeti": str,
                "etiketler": list[str] | str,
                "kaynak": str,
                "aktif": bool | int,
            }

        Returns:
            Skill ID'si
        """
        skill_id = skill_dict.get("id", "").strip()
        if not skill_id:
            raise ValueError("skill_dict 'id' alani zorunludur.")

        baslik = skill_dict.get("baslik", "").strip()
        icerik_ozeti = skill_dict.get("icerik_ozeti", "").strip()

        # Etiketler: list -> virgülle ayrılmış string
        etiketler_raw = skill_dict.get("etiketler", "")
        if isinstance(etiketler_raw, list):
            etiketler = ", ".join(str(e).strip() for e in etiketler_raw if str(e).strip())
        else:
            etiketler = str(etiketler_raw).strip()

        kaynak = skill_dict.get("kaynak", "").strip()
        aktif = 1 if skill_dict.get("aktif", False) else 0
        simdi = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with _yazma_kilit:
            con = self._con()
            try:
                con.execute(
                    """INSERT INTO skills (id, baslik, icerik_ozeti, etiketler, kaynak, aktif, son_guncelleme)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET
                           baslik         = COALESCE(NULLIF(excluded.baslik, ''), skills.baslik),
                           icerik_ozeti   = COALESCE(NULLIF(excluded.icerik_ozeti, ''), skills.icerik_ozeti),
                           etiketler      = COALESCE(NULLIF(excluded.etiketler, ''), skills.etiketler),
                           kaynak         = COALESCE(NULLIF(excluded.kaynak, ''), skills.kaynak),
                           aktif          = excluded.aktif,
                           son_guncelleme = excluded.son_guncelleme""",
                    (skill_id, baslik, icerik_ozeti, etiketler, kaynak, aktif, simdi),
                )
                con.commit()
                logger.debug("[SkillLib] Upsert: %s (aktif=%d)", skill_id, aktif)
            except Exception:
                con.rollback()
                raise
            finally:
                con.close()

        return skill_id

    # ── Ara ─────────────────────────────────────────────────────────────

    def ara(self, sorgu: str, limit: int = 20) -> list[dict[str, Any]]:
        """
        Etiket/baslik bazinda skill ara.

        Strateji:
        1. Tam kelime eşleşmesi (baslik veya etiketlerde)
        2. LIKE ile kısmi eşleşme
        3. Skorla sırala

        Args:
            sorgu: Aranan metin
            limit: Maksimum sonuç sayısı

        Returns:
            [{"id", "baslik", "icerik_ozeti", "etiketler", "kaynak", "aktif", "son_guncelleme"}, ...]
        """
        if not sorgu or not sorgu.strip():
            return []

        kelimeler = [k.lower().strip() for k in sorgu.split() if len(k.strip()) > 1]

        if not kelimeler:
            return []

        con = self._con()
        try:
            # 1) Tam eşleşme: tüm kelimeler baslik veya etiketlerde
            kosullar = []
            params: list[str] = []
            for kelime in kelimeler:
                kosullar.append(
                    "(LOWER(baslik) LIKE ? OR LOWER(etiketler) LIKE ?)"
                )
                params.extend([f"%{kelime}%", f"%{kelime}%"])

            where = " AND ".join(kosullar) if kosullar else "1=1"

            rows = con.execute(
                f"""SELECT id, baslik, icerik_ozeti, etiketler, kaynak, aktif, son_guncelleme
                    FROM skills
                    WHERE {where}
                    ORDER BY aktif DESC, son_guncelleme DESC
                    LIMIT ?""",
                params + [limit],
            ).fetchall()

            # 2) Az sonuç geldiyse LIKE ile genişlet (tek kelime bazında)
            if len(rows) < limit:
                gorulen_ids = {r["id"] for r in rows}
                ek_kosullar = []
                ek_params: list[str] = []
                for kelime in kelimeler:
                    ek_kosullar.append(
                        "(LOWER(baslik) LIKE ? OR LOWER(etiketler) LIKE ? OR LOWER(icerik_ozeti) LIKE ?)"
                    )
                    ek_params.extend([f"%{kelime}%", f"%{kelime}%", f"%{kelime}%"])

                ek_where = " OR ".join(ek_kosullar) if ek_kosullar else "1=1"

                ek_rows = con.execute(
                    f"""SELECT id, baslik, icerik_ozeti, etiketler, kaynak, aktif, son_guncelleme
                        FROM skills
                        WHERE ({ek_where})
                        ORDER BY aktif DESC, son_guncelleme DESC
                        LIMIT ?""",
                    ek_params + [limit],
                ).fetchall()

                for r in ek_rows:
                    if r["id"] not in gorulen_ids:
                        rows.append(r)
                        gorulen_ids.add(r["id"])
                        if len(rows) >= limit:
                            break

            sonuc = []
            for r in rows:
                etiket_list = [e.strip() for e in r["etiketler"].split(",") if e.strip()]
                sonuc.append({
                    "id": r["id"],
                    "baslik": r["baslik"],
                    "icerik_ozeti": r["icerik_ozeti"],
                    "etiketler": etiket_list,
                    "kaynak": r["kaynak"],
                    "aktif": bool(r["aktif"]),
                    "son_guncelleme": r["son_guncelleme"],
                })

            return sonuc

        finally:
            con.close()

    # ── Sync ────────────────────────────────────────────────────────────

    def sync(self, kaynak_dizin: str | Path) -> dict[str, int]:
        """
        Bir dizindeki .md skill dosyalarını kütüphaneye senkronize et.

        Her .md dosyası için:
        1. YAML front-matter'ı ayrıştır
        2. Skill kaydı oluştur/güncelle (upsert)
        3. Dosya yoksa kütüphaneden silme (isteğe bağlı)

        Args:
            kaynak_dizin: .md dosyalarının bulunduğu dizin

        Returns:
            {"yeni": int, "guncellenen": int, "atlanan": int, "hata": int, "toplam": int}
        """
        kaynak = Path(kaynak_dizin)
        if not kaynak.is_dir():
            logger.warning("[SkillLib] Dizin bulunamadi: %s", kaynak)
            return {"yeni": 0, "guncellenen": 0, "atlanan": 0, "hata": 0, "toplam": 0}

        md_dosyalari = sorted(kaynak.rglob("*.md"))
        logger.info("[SkillLib] Sync basladi: %s (%d dosya)", kaynak, len(md_dosyalari))

        # Mevcut ID'leri al (stale tespiti için)
        con = self._con()
        try:
            mevcut_ids = set(
                r["id"] for r in con.execute("SELECT id FROM skills").fetchall()
            )
        finally:
            con.close()

        yeni = 0
        guncellenen = 0
        atlanan = 0
        hata = 0
        islenen_ids: set[str] = set()

        for fp in md_dosyalari:
            try:
                content = fp.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                logger.warning("[SkillLib] Okuma hatasi [%s]: %s", fp.name, e)
                hata += 1
                continue

            # YAML front-matter ayrıştır
            meta, _ = _yaml_front_matter_parse(content)

            skill_id = meta.get("id", fp.stem)
            baslik = meta.get("baslik", fp.stem)
            icerik_ozeti = meta.get("icerik_ozeti", "")
            etiketler = meta.get("etiketler", [])

            # id boşsa dosya adını kullan
            if not skill_id:
                skill_id = fp.stem

            # Kaynak yolunu normalize et
            try:
                rel_path = str(fp.relative_to(kaynak).as_posix())
            except ValueError:
                rel_path = fp.name

            skill_dict = {
                "id": skill_id,
                "baslik": baslik,
                "icerik_ozeti": icerik_ozeti,
                "etiketler": etiketler,
                "kaynak": rel_path,
            }

            try:
                self.kaydet(skill_dict)
                islenen_ids.add(skill_id)

                if skill_id in mevcut_ids:
                    guncellenen += 1
                else:
                    yeni += 1

                logger.debug("[SkillLib] Sync: %s (%s)", skill_id, baslik[:40])

            except Exception as e:
                logger.warning("[SkillLib] Sync hatasi [%s]: %s", fp.name, e)
                hata += 1

        # Stale temizliği: kütüphanede olup diskte olmayanları sil (opsiyonel)
        silinen = 0
        for sid in mevcut_ids:
            if sid not in islenen_ids:
                try:
                    self.sil(sid)
                    silinen += 1
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                    )

        ozet = {
            "yeni": yeni,
            "guncellenen": guncellenen,
            "atlanan": atlanan,
            "hata": hata,
            "silinen": silinen,
            "toplam": len(md_dosyalari),
        }

        logger.info(
            "[SkillLib] Sync tamam: +%d yeni, ~%d guncel, -%d silindi, !%d hata (%d dosya)",
            yeni, guncellenen, silinen, hata, len(md_dosyalari),
        )

        return ozet

    # ── Get ─────────────────────────────────────────────────────────────

    def get(self, skill_id: str) -> dict[str, Any] | None:
        """
        Skill detayını getir.

        Args:
            skill_id: Skill ID'si

        Returns:
            {"id", "baslik", "icerik_ozeti", "etiketler", "kaynak", "aktif", "son_guncelleme"}
            veya None (bulunamazsa)
        """
        if not skill_id:
            return None

        con = self._con()
        try:
            row = con.execute(
                """SELECT id, baslik, icerik_ozeti, etiketler, kaynak, aktif, son_guncelleme
                   FROM skills WHERE id = ?""",
                (skill_id,),
            ).fetchone()

            if not row:
                return None

            etiket_list = [e.strip() for e in row["etiketler"].split(",") if e.strip()]
            return {
                "id": row["id"],
                "baslik": row["baslik"],
                "icerik_ozeti": row["icerik_ozeti"],
                "etiketler": etiket_list,
                "kaynak": row["kaynak"],
                "aktif": bool(row["aktif"]),
                "son_guncelleme": row["son_guncelleme"],
            }
        finally:
            con.close()

    # ── Sil ─────────────────────────────────────────────────────────────

    def sil(self, skill_id: str) -> bool:
        """
        Skill'i kütüphaneden sil.

        Args:
            skill_id: Silinecek skill ID'si

        Returns:
            True (silindi) / False (bulunamadi)
        """
        if not skill_id:
            return False

        with _yazma_kilit:
            con = self._con()
            try:
                cur = con.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
                silindi = cur.rowcount > 0
                con.commit()
                if silindi:
                    logger.debug("[SkillLib] Silindi: %s", skill_id)
                return silindi
            except Exception:
                con.rollback()
                raise
            finally:
                con.close()

    # ── Tüm Skill'leri Listele ─────────────────────────────────────────

    def tumu(self, aktif_mi: bool | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """
        Tüm skill'leri listele.

        Args:
            aktif_mi: None = tümü, True = sadece aktif, False = sadece pasif
            limit: Maksimum sonuç sayısı

        Returns:
            [{"id", "baslik", "icerik_ozeti", "etiketler", "kaynak", "aktif", ...}, ...]
        """
        con = self._con()
        try:
            if aktif_mi is not None:
                deger = 1 if aktif_mi else 0
                rows = con.execute(
                    """SELECT id, baslik, icerik_ozeti, etiketler, kaynak, aktif, son_guncelleme
                       FROM skills WHERE aktif = ?
                       ORDER BY son_guncelleme DESC LIMIT ?""",
                    (deger, limit),
                ).fetchall()
            else:
                rows = con.execute(
                    """SELECT id, baslik, icerik_ozeti, etiketler, kaynak, aktif, son_guncelleme
                       FROM skills
                       ORDER BY aktif DESC, son_guncelleme DESC LIMIT ?""",
                    (limit,),
                ).fetchall()

            sonuc = []
            for r in rows:
                etiket_list = [e.strip() for e in r["etiketler"].split(",") if e.strip()]
                sonuc.append({
                    "id": r["id"],
                    "baslik": r["baslik"],
                    "icerik_ozeti": r["icerik_ozeti"],
                    "etiketler": etiket_list,
                    "kaynak": r["kaynak"],
                    "aktif": bool(r["aktif"]),
                    "son_guncelleme": r["son_guncelleme"],
                })

            return sonuc
        finally:
            con.close()

    # ── İstatistik ──────────────────────────────────────────────────────

    def istatistik(self) -> dict[str, Any]:
        """Kütüphane istatistikleri."""
        con = self._con()
        try:
            toplam = con.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
            aktif_say = con.execute(
                "SELECT COUNT(*) FROM skills WHERE aktif = 1"
            ).fetchone()[0]
            pasif_say = toplam - aktif_say
            etiket_dagilimi = con.execute(
                "SELECT etiketler, COUNT(*) FROM skills GROUP BY etiketler ORDER BY COUNT(*) DESC LIMIT 20"
            ).fetchall()

            return {
                "toplam": toplam,
                "aktif": aktif_say,
                "pasif": pasif_say,
                "etiket_dagilimi": {r[0]: r[1] for r in etiket_dagilimi if r[0]},
            }
        finally:
            con.close()


# ── Modül seviyesinde singleton ─────────────────────────────────────────────
_lib: SkillLibrary | None = None


def get_library(db_yolu: str | Path | None = None) -> SkillLibrary:
    """Singleton SkillLibrary örneği al."""
    global _lib
    if _lib is None:
        _lib = SkillLibrary(db_yolu)
    return _lib


# ── Kolay kullanım fonksiyonları ────────────────────────────────────────────

def kaydet(skill_dict: dict[str, Any]) -> str:
    """Skill ekle/güncelle (kolay kullanım)."""
    return get_library().kaydet(skill_dict)


def ara(sorgu: str, limit: int = 20) -> list[dict[str, Any]]:
    """Skill ara (kolay kullanım)."""
    return get_library().ara(sorgu, limit)


def sync(kaynak_dizin: str | Path) -> dict[str, int]:
    """Dizinden skill senkronize et (kolay kullanım)."""
    return get_library().sync(kaynak_dizin)


def get(skill_id: str) -> dict[str, Any] | None:
    """Skill detayı al (kolay kullanım)."""
    return get_library().get(skill_id)


def sil(skill_id: str) -> bool:
    """Skill sil (kolay kullanım)."""
    return get_library().sil(skill_id)


def motor_kaydet(motor) -> None:
    """Motor'a skill kutuphane araclarini kaydet."""
    if hasattr(motor, "_plugin_arac_kaydet"):
        motor._plugin_arac_kaydet(
            "SKILL_SENKRONIZE",
            lambda kaynak="": sync(kaynak) if kaynak else {"hata": "kaynak_dizin parametresi gerekli"},
            "Skill dosyalarini kutuphaneye senkronize et. Parametre: kaynak_dizin",
        )
        motor._plugin_arac_kaydet(
            "SKILL_ARA",
            lambda sorgu="": ara(sorgu) if sorgu else [],
            "Skill kutuphanesinde ara. Parametre: sorgu",
        )
        motor._plugin_arac_kaydet(
            "SKILL_DURUM",
            lambda: get_library().istatistik(),
            "Skill kutuphane istatistikleri",
        )


# ── İlk kurulum ────────────────────────────────────────────────────────────
_db_kur()
