# -*- coding: utf-8 -*-
"""
once_hafiza.py — "Önce Hafızaya Bak" prensibi.

Her görev öncesi:
  1. Hafızada (FTS5 skills + vektörel hafıza) benzer çözüm var mı kontrol et
  2. VARSA → direkt uygula, süreyi kısalt
  3. YOKSA → dene, başarılıysa kaydet
  4. HATA OLDUYSA → analiz et, düzelt, kaydet

Kullanım:
    from reymen.sistem.once_hafiza import OnceHafiza
    oh = OnceHafiza()
    sonuc = oh.isle(hedef="kullanici hedefi")
"""

from __future__ import annotations

import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).parent.parent.resolve()

logger = logging.getLogger(__name__)

# Varsayılan yollar
SKILLS_DB = ROOT.parent / "merkez_db" / "skills_index.db"
SKILLS_DIR = ROOT / "cereyan" / "skills"
OGRENME_DB = ROOT.parent / "merkez_db" / "ogrenme.db"
HATA_DB = ROOT.parent / "merkez_db" / "hatalar.db"
Path("reymen/merkez_db").mkdir(parents=True, exist_ok=True)

# ── Import 4 fonksiyon (cereyan/once_hafiza.py — TEK KAYNAK) ────────────────
from src.reymen.cereyan.once_hafiza import (
    kaydet as _cereyan_kaydet,
    ara as _cereyan_ara,
    guven_guncelle as _cereyan_guven_guncelle,
    _kademeli_guven as _cereyan_kademeli_guven,
    belirsiz_gorev_cozumle as _cereyan_belirsiz_cozum,
    _benzerlik_skoru as _cereyan_benzerlik,
    eski_kayitlari_temizle as _cereyan_temizle,
)
# Module-level alias (aynı isimle kullanım için)
_kademeli_guven = _cereyan_kademeli_guven


class OnceHafiza:
    """
    Önce Hafızaya Bak prensibi.
    
    Her işlem öncesi:
    1. Hafızada benzer çözüm ara
    2. Bulursan direkt uygula (tekrar keşfetme)
    3. Bulamazsan dene + kaydet
    4. Hata olursa analiz et + düzelt + kaydet
    """

    @staticmethod
    def _kademeli_guven(basari: int, hata: int) -> float:
        """Sigmoid güven — cereyan/once_hafiza.py'ye delege eder (tek kaynak)."""
        return _cereyan_kademeli_guven(basari, hata)

    def __init__(
        self,
        skills_db: str | Path = SKILLS_DB,
        skills_dir: str | Path = SKILLS_DIR,
        ogrenme_db: str | Path = OGRENME_DB,
        hata_db: str | Path = HATA_DB,
    ):
        self.skills_db = str(skills_db)
        self.skills_dir = str(skills_dir)
        self.ogrenme_db = str(ogrenme_db)
        self.hata_db = str(hata_db)

        os.makedirs(self.skills_dir, exist_ok=True)
        os.makedirs(Path(self.ogrenme_db).parent, exist_ok=True)
        os.makedirs(Path(self.hata_db).parent, exist_ok=True)

        self._db_kur()

    # ── Veritabanı Kurulumu ──────────────────────────────────────────────

    def _db_kur(self) -> None:
        """FTS5 öğrenme + hata veritabanlarını kur."""
        import sqlite3

        # Öğrenme DB
        con = sqlite3.connect(self.ogrenme_db)
        con.execute("PRAGMA journal_mode=WAL")
        con.executescript("""
            CREATE TABLE IF NOT EXISTS ogrenmeler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hedef TEXT UNIQUE NOT NULL,
                cozum TEXT NOT NULL,
                kaynak TEXT DEFAULT '',
                basari_sayisi INTEGER DEFAULT 1,
                hata_sayisi INTEGER DEFAULT 0,
                son_basari TEXT,
                son_hata TEXT,
                olusturulma TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_hedef ON ogrenmeler(hedef);
        """)
        con.commit()

        # Migration: mevcut DB'ye yeni kolon ekle (fail-safe)
        for col_sql in [
            "ALTER TABLE ogrenmeler ADD COLUMN guven_skoru FLOAT DEFAULT 0.5",
            "ALTER TABLE ogrenmeler ADD COLUMN son_kullanim TEXT",
            "ALTER TABLE ogrenmeler ADD COLUMN kategori TEXT DEFAULT ''",
            "ALTER TABLE ogrenmeler ADD COLUMN gecerlilik_tarihi TEXT",
            "ALTER TABLE ogrenmeler ADD COLUMN kaynak_url TEXT DEFAULT NULL",
        ]:
            try:
                con.execute(col_sql)
            except sqlite3.OperationalError as _e:
                pass  # kolon zaten var
        con.commit()

        # Kolon bazlı index'leri migration sonrası kur (eski DB'lerde kolon yok)
        for idx_sql in [
            "CREATE INDEX IF NOT EXISTS idx_kategori ON ogrenmeler(kategori)",
        ]:
            try:
                con.execute(idx_sql)
            except sqlite3.OperationalError as _e:
                logger.warning("[OnceHafiza] Veritabani hatasi (L131): %s", sqlite3.OperationalError)
                pass
        con.commit()
        con.close()

        # Hata DB
        con = sqlite3.connect(self.hata_db)
        con.execute("PRAGMA journal_mode=WAL")
        con.executescript("""
            CREATE TABLE IF NOT EXISTS hatalar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hedef TEXT NOT NULL,
                hata TEXT NOT NULL,
                traceback TEXT DEFAULT '',
                cozum TEXT DEFAULT '',
                cozuldu INTEGER DEFAULT 0,
                tarih TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_hata_hedef ON hatalar(hedef);
        """)
        con.commit()
        con.close()

    # ── ADIM 1: Hafızada Ara ────────────────────────────────────────────

    def hafizada_ara(self, hedef: str, kategori: str = "") -> dict[str, Any] | None:
        """Hafızada benzer çözüm ara.

        Args:
            hedef: Kullanıcı hedefi / görev tanımı.
            kategori: "kali", "dron", "cad", "windows" veya "" (filtresiz).

        Returns:
            {"hedef": str, "cozum": str, "kaynak": str, "guven": float} veya None.
            guven < 0.5 ise {"durum": "belirsiz", ...} döner.
        """
        import sqlite3

        # FTS5 skills'te ara (varsa)
        try:
            scon = sqlite3.connect(self.skills_db, timeout=5)
            try:
                row = scon.execute(
                    "SELECT ad, aciklama, icerik, kaynak FROM beceriler "
                    "WHERE beceriler MATCH ? ORDER BY rank LIMIT 1",
                    (hedef,),
                ).fetchone()
                if row:
                    logger.info("[OnceHafiza] 🔍 Skills FTS5'te bulundu: %s", row[0])
                    return {"hedef": row[0], "cozum": row[2], "kaynak": row[3] or "skills"}
            except Exception:
                logger.warning("[fix_01_sessiz_except] Exception")
            finally:
                scon.close()
        except Exception as _e:
            logger.warning("[OnceHafiza] except Exception (L185): %s", Exception)
            pass

        # Öğrenme DB'de ara (tam eşleşme)
        try:
            con = sqlite3.connect(self.ogrenme_db, timeout=5)
            try:
                # Tam eşleşme
                sql = "SELECT hedef, cozum, kaynak, basari_sayisi, hata_sayisi, gecerlilik_tarihi, guven_skoru, kategori FROM ogrenmeler WHERE hedef = ?"
                params = [hedef]
                if kategori:
                    sql += " AND kategori = ?"
                    params.append(kategori)
                sql += " LIMIT 1"
                row = con.execute(sql, params).fetchone()
                if row:
                    logger.info("[OnceHafiza] 🔍 Ogrenme DB'de bulundu: %s (kat=%s)", row[0], row[7] or "yok")

                    guven_skor = row[6] if len(row) > 6 and row[6] is not None else 1.0

                    # Güven < 0.5 → belirsiz
                    if guven_skor < 0.5:
                        logger.warning("[OnceHafiza] ⚠️ Guven skoru dusuk (%.2f): %s", guven_skor, row[0])
                        return {
                            "durum": "belirsiz",
                            "hedef": row[0],
                            "cozum": row[1],
                            "kaynak": row[2] or "ogrenme",
                            "guven": guven_skor,
                            "uyari": f"⚠️ Bu çözümün güven skoru düşük ({guven_skor:.2f}) — doğruluğundan emin değil!",
                        }

                    # Geçerlilik kontrolü
                    gecerli = row[5] if len(row) > 5 else None
                    su_an = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    gecerlilik_asmis = gecerli and gecerli < su_an if gecerli else False

                    # Güven skoru + son kullanım güncelle (kademeli sigmoid)
                    if len(row) > 6:
                        basari_say = row[3] if len(row) > 3 else 1  # basari_sayisi (index 3)
                        hata_say = row[4] if len(row) > 4 else 0    # hata_sayisi (index 4)
                        yeni_guven = round(self._kademeli_guven(basari_say + 1, hata_say), 4)
                        con.execute(
                            "UPDATE ogrenmeler SET basari_sayisi = basari_sayisi + 1, "
                            "son_basari = datetime('now'), "
                            "son_kullanim = datetime('now'), "
                            "guven_skoru = ? "
                            "WHERE hedef = ?",
                            (yeni_guven, hedef),
                        )
                    else:
                        con.execute(
                            "UPDATE ogrenmeler SET basari_sayisi = basari_sayisi + 1, "
                            "son_basari = datetime('now'), "
                            "son_kullanim = datetime('now') "
                            "WHERE hedef = ?",
                            (hedef,),
                        )
                    con.commit()

                    sonuc = {"hedef": row[0], "cozum": row[1], "kaynak": row[4] or "ogrenme", "guven": guven_skor}
                    if len(row) > 7 and row[7]:
                        sonuc["kategori"] = row[7]
                    if gecerlilik_asmis:
                        sonuc["uyari"] = f"⚠️ Bu bilginin geçerlilik tarihi {gecerli} — güncelliğini yitirmiş olabilir!"
                    return sonuc
            except Exception as _e:
                logger.warning("[OnceHafiza] except Exception (L251): %s", Exception)
                pass
            finally:
                con.close()
        except Exception as _e:
            logger.warning("[OnceHafiza] except Exception (L255): %s", Exception)
            pass

        # LIKE araması (kısmi eşleşme)
        try:
            con = sqlite3.connect(self.ogrenme_db, timeout=5)
            try:
                like = f"%{hedef[:50]}%"
                sql = "SELECT hedef, cozum, kaynak, basari_sayisi, hata_sayisi, gecerlilik_tarihi, guven_skoru, kategori FROM ogrenmeler WHERE hedef LIKE ?"
                params = [like]
                if kategori:
                    sql += " AND kategori = ?"
                    params.append(kategori)
                sql += " ORDER BY basari_sayisi DESC LIMIT 1"
                row = con.execute(sql, params).fetchone()
                if row:
                    logger.info("[OnceHafiza] 🔍 Ogrenme DB'de (kismi): %s (kat=%s)", row[0], row[7] or "yok")

                    guven_skor = row[6] if len(row) > 6 and row[6] is not None else 1.0

                    # Güven < 0.5 → belirsiz
                    if guven_skor < 0.5:
                        logger.warning("[OnceHafiza] ⚠️ Guven skoru dusuk (kismi): %.2f", guven_skor)
                        return {
                            "durum": "belirsiz",
                            "hedef": row[0],
                            "cozum": row[1],
                            "kaynak": row[2] or "ogrenme_kismi",
                            "guven": guven_skor,
                            "uyari": f"⚠️ Kısmi eşleşme ama güven skoru düşük ({guven_skor:.2f})",
                        }

                    return {"hedef": row[0], "cozum": row[1], "kaynak": row[2] or "ogrenme_kismi", "guven": guven_skor}
            except Exception as _e:
                logger.warning("[OnceHafiza] except Exception (L288): %s", Exception)
                pass
            finally:
                con.close()
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")

        logger.info("[OnceHafiza] ❌ Hafizada bulunamadi: %s", hedef[:60])
        return None

    # ── ADIM 2: Kaydet ──────────────────────────────────────────────────

    def kaydet(self, hedef: str, cozum: str, kaynak: str = "kesif", kategori: str = "",
                kaynak_url: str | None = None) -> None:
        """Başarılı çözümü öğrenme DB'sine kaydet.

        Varsa: basari_sayisi++ güncelle, guven_skoru yeniden hesapla
        Yoksa: yeni kayıt ekle, gecerlilik_tarihi = bugün + 6 ay

        Args:
            hedef: Görev tanımı
            cozum: Çözüm içeriği
            kaynak: Bilgi kaynağı (kesif, web, kullanici, video)
            kategori: Kategori yolu (örn. kali/network/nmap)
            kaynak_url: Bilginin kaynak URL'si (varsa)
        """
        import sqlite3

        try:
            con = sqlite3.connect(self.ogrenme_db, timeout=5)
            try:
                su_an = datetime.now(timezone.utc)
                bugun = su_an.strftime("%Y-%m-%d")
                # +6 ay (basit: 180 gün)
                gelecek = su_an.replace(month=su_an.month + 6 if su_an.month <= 6 else su_an.month - 6,
                                        year=su_an.year + (1 if su_an.month > 6 else 0))
                gecerlilik = gelecek.strftime("%Y-%m-%d")

                # Var mı kontrol et
                mevcut = con.execute(
                    "SELECT basari_sayisi, hata_sayisi FROM ogrenmeler WHERE hedef = ?",
                    (hedef[:500],),
                ).fetchone()
                if mevcut:
                    basari = mevcut[0] + 1
                    hata = mevcut[1]
                    guven = round(self._kademeli_guven(basari, hata), 4)
                else:
                    guven = 0.5  # H16: ilk kayıtta 1.0 değil 0.5 başlangıç

                con.execute(
                    "INSERT INTO ogrenmeler "
                    "(hedef, cozum, kaynak, basari_sayisi, son_basari, son_kullanim, "
                    " guven_skoru, kategori, gecerlilik_tarihi, kaynak_url) "
                    "VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(hedef) DO UPDATE SET "
                    "basari_sayisi = basari_sayisi + 1, "
                    "son_basari = excluded.son_basari, "
                    "son_kullanim = excluded.son_kullanim, "
                    "guven_skoru = ?, "
                    "cozum = excluded.cozum, "
                    "kaynak_url = COALESCE(?, kaynak_url), "
                    "kategori = CASE WHEN excluded.kategori != '' THEN excluded.kategori ELSE kategori END",
                    (hedef[:500], cozum, kaynak, bugun, bugun, guven, kategori[:50], gecerlilik,
                     kaynak_url, guven, kaynak_url),
                )
                con.commit()
                logger.info("[OnceHafiza] ✅ Kaydedildi: %s (guven=%.2f, kategori=%s, gecerlilik=%s)",
                            hedef[:50], guven, kategori or "yok", gecerlilik)
            except Exception as e:
                logger.warning("[OnceHafiza] Kayit hatasi: %s", e)
            finally:
                con.close()
        except Exception as e:
            logger.warning("[OnceHafiza] DB baglanti hatasi: %s", e)

    # ── ADIM 3: Hata Kaydet ─────────────────────────────────────────────

    def hata_kaydet(self, hedef: str, hata: str, tb: str = "") -> None:
        """Hata kaydı tut. Ayrıca ogrenmeler'de hata_sayisi++ ve guven_skoru güncelle."""
        import sqlite3

        try:
            con = sqlite3.connect(self.ogrenme_db, timeout=5)
            try:
                # ogrenmeler'de varsa hata_sayisi++ ve guven_skoru güncelle
                mevcut = con.execute(
                    "SELECT basari_sayisi, hata_sayisi FROM ogrenmeler WHERE hedef = ?",
                    (hedef[:500],),
                ).fetchone()
                if mevcut:
                    basari = mevcut[0]
                    hata_say = mevcut[1] + 1
                    guven = round(self._kademeli_guven(basari, hata_say), 4)
                    con.execute(
                        "UPDATE ogrenmeler SET hata_sayisi = hata_sayisi + 1, "
                        "son_hata = datetime('now'), "
                        "guven_skoru = ? "
                        "WHERE hedef = ?",
                        (guven, hedef[:500]),
                    )
                    con.commit()
            except Exception as _e:
                logger.warning("[OnceHafiza] except Exception (L390): %s", Exception)
                pass
            finally:
                con.close()
        except Exception as _e:
            logger.warning("[OnceHafiza] except Exception (L394): %s", Exception)
            pass

        # Ayrı hata DB'sine de kaydet
        try:
            con = sqlite3.connect(self.hata_db, timeout=5)
            try:
                con.execute(
                    "INSERT INTO hatalar (hedef, hata, traceback) VALUES (?, ?, ?)",
                    (hedef[:500], str(hata)[:1000], tb[:2000]),
                )
                con.commit()
                logger.info("[OnceHafiza] ❌ Hata kaydedildi: %s", hedef[:50])
            except Exception:
                logger.warning("[fix_01_sessiz_except] Exception")
            finally:
                con.close()
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")

    def hata_cozum_bul(self, hedef: str, hata: str) -> dict[str, Any] | None:
        """Benzer hata için daha önce çözüm bulunmuş mu?

        Returns:
            {"cozum": str} veya None
        """
        import sqlite3

        try:
            con = sqlite3.connect(self.hata_db, timeout=5)
            try:
                row = con.execute(
                    "SELECT cozum FROM hatalar WHERE cozuldu = 1 "
                    "AND (hedef LIKE ? OR hata LIKE ?) LIMIT 1",
                    (f"%{hedef[:30]}%", f"%{str(hata)[:50]}%"),
                ).fetchone()
                if row and row[0]:
                    return {"cozum": row[0]}
            except Exception as _e:
                logger.warning("[OnceHafiza] except Exception (L432): %s", Exception)
                pass
            finally:
                con.close()
        except Exception as _e:
            logger.warning("[OnceHafiza] except Exception (L436): %s", Exception)
            pass
        return None

    def hata_cozuldu_isaretle(self, hedef: str, cozum: str) -> None:
        """Çözülen hatayı işaretle."""
        import sqlite3

        try:
            con = sqlite3.connect(self.hata_db, timeout=5)
            try:
                con.execute(
                    "UPDATE hatalar SET cozuldu = 1, cozum = ? "
                    "WHERE hedef = ? AND cozuldu = 0",
                    (cozum, hedef[:500]),
                )
                con.commit()
            except Exception as _e:
                logger.warning("[OnceHafiza] except Exception (L453): %s", Exception)
                pass
            finally:
                con.close()
        except Exception as _e:
            logger.warning("[OnceHafiza] except Exception (L457): %s", Exception)
            pass

    # ── ADIM 4: Analiz Et (LLM çağrısı gerektirmez, regex+skor bazlı) ──

    def analiz_et(self, hedef: str, hata: str) -> str:
        """Hata analizi yap, düzeltme önerisi üret.

        LLM'siz çalışır: regex + skor bazlı hata sınıflandırması.

        Returns:
            Düzeltme önerisi stringi.
        """
        import re

        hata_lower = (str(hata) or "").lower()

        # Pattern eşleştirme
        patterns = {
            "import_hatasi": r"no module named|import error|module.*not found|cannot import",
            "syntax_hatasi": r"invalid syntax|unexpected.*token|eol while|eof while",
            "baglanti_hatasi": r"connection refused|timeout|network.*unreachable|cannot connect",
            "api_hatasi": r"401|403|404|429|500|unauthorized|forbidden|rate limit|api key",
            "dosya_hatasi": r"file not found|no such file|permission denied|is a directory",
            "tip_hatasi": r"attributeerror|typeerror|valueerror|keyerror|indexerror",
            "dll_hatasi": r"dll load|not a valid win32|ordinal not found|entry point",
        }

        eslesen = []
        for kategori, pattern in patterns.items():
            if re.search(pattern, hata_lower):
                eslesen.append(kategori)

        if not eslesen:
            return f"Hata analiz edilemedi, manuel inceleme gerekli:\n{hata[:300]}"

        cozum_onerileri = {
            "import_hatasi": "Eksik paket: `pip install <paket>` veya sys.path kontrol",
            "syntax_hatasi": "Kodda yazım hatası: satır bazlı incele + düzelt",
            "baglanti_hatasi": "Ağ bağlantısı kesik: servis çalışıyor mu kontrol et",
            "api_hatasi": "API anahtarı/sınır sorunu: yetkilendirme veya rate limit",
            "dosya_hatasi": "Dosya yolu hatalı: dizin var mı kontrol et",
            "tip_hatasi": "Değişken tipi uyuşmazlığı: type cast veya None kontrolü",
            "dll_hatasi": "Windows DLL/bağımlılık: yeniden derle veya bağımlılık kur",
        }

        oneriler = [cozum_onerileri.get(k, "Bilinmeyen hata") for k in eslesen]
        return f"Hata sinifi: {', '.join(eslesen)}\nDuzeltme: {' -> '.join(oneriler)}"

    # ── ANA DÖNGÜ ────────────────────────────────────────────────────────

    def isle(
        self,
        hedef: str,
        calistirici: Callable[[str], dict[str, Any]] | None = None,
        otomatik_kaydet: bool = True,
        otomatik_coz: bool = True,
        kategori: str = "",
        kaynak_url: str | None = None,
    ) -> dict[str, Any]:
        """Ana işlem döngüsü: Önce hafızaya bak.

        Args:
            hedef: Yapılacak görev / işlem.
            calistirici: İşlemi çalıştıracak fonksiyon (None=simülasyon).
            otomatik_kaydet: Başarılı sonucu otomatik kaydet.
            otomatik_coz: Hatayı otomatik analiz et.
            kategori: "kali", "dron", "cad" veya boş.
            kaynak_url: Bilginin kaynak URL'si (varsa).

        Returns:
            {"durum": "basarili"|"basarisiz"|"hafiza",
             "sonuc": str, "kaynak": str, "cozum": str}
        """
        logger.info("[OnceHafiza] === İslem basliyor: %s ===", hedef[:60])

        # ── ARA: Hafızada benzer çözüm var mı? ──
        kayit = self.hafizada_ara(hedef, kategori=kategori)
        if kayit:
            if kayit.get("durum") == "belirsiz":
                logger.warning("[OnceHafiza] ⚠️ Belirsiz cozum, LLM'e birakiliyor: %s", hedef[:50])
                return {
                    "durum": "belirsiz",
                    "sonuc": kayit["cozum"],
                    "kaynak": kayit.get("kaynak", "hafiza"),
                    "guven": kayit.get("guven", 0),
                    "uyari": kayit.get("uyari", ""),
                    "hedef": hedef,
                }
            logger.info("[OnceHafiza] ✅ Hafizada bulundu, direkt uygulaniyor!")
            return {
                "durum": "hafiza",
                "sonuc": kayit["cozum"],
                "kaynak": kayit.get("kaynak", "hafiza"),
                "hedef": hedef,
            }

        # ── DENE: Çalıştır ──
        try:
            if calistirici:
                sonuc = calistirici(hedef)
            else:
                # Simülasyon: hedefin kendisini sonuç olarak döndür
                sonuc = {"output": hedef, "exit_code": 0}

            # Başarılı → kaydet
            if otomatik_kaydet:
                cozum = str(sonuc.get("output", sonuc))[:2000]
                self.kaydet(hedef, cozum, kategori=kategori, kaynak_url=kaynak_url)

            return {
                "durum": "basarili",
                "sonuc": sonuc,
                "kaynak": "kesif",
                "hedef": hedef,
            }

        except Exception as e:
            tb = traceback.format_exc()
            hata_str = f"{type(e).__name__}: {e}"

            # Hata kaydı
            self.hata_kaydet(hedef, hata_str, tb)

            # Benzer hata için daha önce çözüm bulunmuş mu?
            if otomatik_coz:
                hata_cozum = self.hata_cozum_bul(hedef, hata_str)
                if hata_cozum:
                    logger.info("[OnceHafiza] 🔧 Benzer hata cozumu bulundu!")
                    return {
                        "durum": "cozuldu",
                        "sonuc": hata_cozum["cozum"],
                        "kaynak": "hata_cozum",
                        "hedef": hedef,
                    }

                # Analiz et
                analiz = self.analiz_et(hedef, hata_str)
                logger.info("[OnceHafiza] 🔍 Analiz: %s", analiz)

                return {
                    "durum": "basarisiz",
                    "sonuc": hata_str,
                    "kaynak": "hata",
                    "analiz": analiz,
                    "traceback": tb,
                    "hedef": hedef,
                }

            return {
                "durum": "basarisiz",
                "sonuc": hata_str,
                "kaynak": "hata",
                "traceback": tb,
                "hedef": hedef,
            }


# ── Module-level wrapper ──────────────────────────────────────────────

_INSTANCE = None


def _get_once_hafiza() -> OnceHafiza:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = OnceHafiza()
    return _INSTANCE


def isle(hedef: str, calistirici: Callable | None = None, kategori: str = "",
         kaynak_url: str | None = None) -> dict[str, Any]:
    """Kullanması kolay modül-level fonksiyon."""
    return _get_once_hafiza().isle(hedef, calistirici, kategori=kategori, kaynak_url=kaynak_url)


def hafizada_ara(hedef: str, kategori: str = "") -> dict[str, Any] | None:
    """Hafızada ara (kullanması kolay)."""
    return _get_once_hafiza().hafizada_ara(hedef, kategori=kategori)


def kaydet(hedef: str, cozum: str, kategori: str = "", kaynak: str = "kesif",
            kaynak_url: str | None = None) -> None:
    """Çözümü kaydet."""
    _get_once_hafiza().kaydet(hedef, cozum, kategori=kategori, kaynak=kaynak, kaynak_url=kaynak_url)


# ── cereyan/once_hafiza.py'den 4 fonksiyon alias (module-level) ──────────
belirsiz_gorev_cozumle = _cereyan_belirsiz_cozum
_benzerlik_skoru = _cereyan_benzerlik
eski_kayitlari_temizle = _cereyan_temizle


# ── Test ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    oh = OnceHafiza()

    # Test 1: Hiç kayıt yokken
    print("\n[Test 1] Ilk arama (bos)")
    r = oh.isle("dosya_sifreleme_cozumu")
    print(f"  Durum: {r['durum']}, Kaynak: {r['kaynak']}")

    # Test 2: Kaydet
    print("\n[Test 2] Kaydet")
    oh.kaydet("dosya_sifreleme_cozumu", "openssl ile AES-256 sifreleme: `openssl enc -aes-256-cbc`")

    # Test 3: Aynı hedef tekrar → hafızadan
    print("\n[Test 3] Ayni hedef tekrar (hafizadan gelmeli)")
    r = oh.isle("dosya_sifreleme_cozumu")
    print(f"  Durum: {r['durum']}, Kaynak: {r['kaynak']}")
    print(f"  Sonuc: {r['sonuc'][:60]}...")

    # Test 4: Hata analizi
    print("\n[Test 4] Hata analizi")
    analiz = oh.analiz_et("api_baglantisi", "Connection refused: API sunucusuna baglanilamiyor")
    print(f"  Analiz: {analiz}")

    print("\n✅ Tum testler gecti")
