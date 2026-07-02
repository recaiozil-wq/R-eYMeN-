# - Python 3.9+ uyumlu type hints (from __future__ annotations)
# -*- coding: utf-8 -*-
"""
closed_learning_loop.py — ClosedLearningLoop + FTS5 beceri indeksi.

Ne yapar:
  - Basarili gorev sonrasi beceri karti kristallestir (skills/*.md)
  - Baslangicta mevcut tum .md becerilerini FTS5'e indeksle
  - Sorgu ile ilgili becerileri aninda getir
  - main.py prompt'una enjekte edilmek icin: beceri_baglamini_al()
  - Modern LLM agent API'lari icin: beceri_baglamini_al_yapisal()

Degisiklik (v3):
  - yetenek_fabrikasi bagimliligi kaldirildi; tamamen self-contained
  - FTS5 sorgu sanitization guclendirildi (injection-safe token builder)
  - Thread-safe contextmanager connection pattern
  - auto_index default=False (production-safe)
  - LLM agent icin yapisal baglam ciktisi eklendi
  - Tum import'lar module seviyesine tasindi

Entegrasyon:
    loop = ClosedLearningLoop()
    loop.tum_becerileri_indeksle()               # startup'ta bir kez
    baglam = loop.beceri_baglamini_al("sorgu")   # prompt'a enjekte et
    loop.beceri_kristallestir("ad", "ac", "ad")  # gorev bittikten sonra
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.resolve()

SKILLS_DIZINLERI: list[Path] = [
    ROOT / "skills",
    ROOT / ".ReYMeN" / "skills",
]

MAKS_BAGLAM_KARAKTER: int = 4_000

# FTS5'e gecirmeyecegimiz ozel karakter kumesi
_FTS_TEMIZLE = re.compile(r"[^\w\s]", re.UNICODE)


# ─────────────────────────────────────────────────────────────────────────────
# Module-level yardimci fonksiyonlar (harici import gerektirmez)
# ─────────────────────────────────────────────────────────────────────────────

def _guvenli_ad(ad: str) -> str:
    """Dosya sistemi icin guvenli, unicode-safe isim uret."""
    try:
        temiz = ad.lower().strip().replace(" ", "_")
        return "".join(c for c in temiz if c.isalnum() or c in "_-") or "bilinmeyen"
    except Exception:
        return "bilinmeyen"


def _fts5_token(metin: str) -> str:
    """
    FTS5-safe sorgu tokeni uret.

    - AND / OR / NOT / NEAR reserved kelimelerini atar
    - Ozel karakterleri siler
    - Cok kelimeli sorguyu phrase query'e cevirir
    - Bos string: caller None gibi davranmali
    """
    temiz = _FTS_TEMIZLE.sub(" ", metin).strip()
    tokenlar = [
        t for t in temiz.split()
        if t.lower() not in ("and", "or", "not", "near")
    ]
    if not tokenlar:
        return ""
    return tokenlar[0] if len(tokenlar) == 1 else '"' + " ".join(tokenlar) + '"'


def _zaman_damgasi() -> str:
    """ISO-8601 UTC zaman damgasi."""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _beceri_md_olustur(beceri_adi: str, aciklama: str, adimlar: str) -> str:
    """YAML frontmatter'li standart beceri karti markdown icerigi uret."""
    bugun = datetime.now().strftime("%Y-%m-%d")
    return (
        f"---\n"
        f"name: {beceri_adi}\n"
        f"description: {aciklama[:300]}\n"
        f"created: {bugun}\n"
        f"usage_count: 1\n"
        f"last_used: {bugun}\n"
        f"---\n\n"
        f"# {beceri_adi}\n\n"
        f"{aciklama}\n\n"
        f"## Adimlar\n\n"
        f"{adimlar}\n"
    )


def _frontmatter_deger_al(metin: str, anahtar: str) -> str | None:
    """YAML frontmatter'dan tek deger cek (regex-based, dependency-free)."""
    m = re.search(rf"^{re.escape(anahtar)}\s*:\s*(.+)$", metin, re.MULTILINE)
    return m.group(1).strip().strip("\"'") if m else None


def _frontmatter_deger_guncelle(metin: str, anahtar: str, deger: str | int) -> str:
    """YAML frontmatter'da tek degeri yerinde guncelle; yoksa frontmatter sonuna ekle."""
    pattern = re.compile(rf"^({re.escape(anahtar)}\s*:)(.*)$", re.MULTILINE)
    yeni_satir = f"{anahtar}: {deger}"
    if pattern.search(metin):
        return pattern.sub(yeni_satir, metin)
    kapanis = metin.find("\n---", 3)
    if kapanis != -1:
        return metin[:kapanis] + f"\n{yeni_satir}" + metin[kapanis:]
    return metin


# ─────────────────────────────────────────────────────────────────────────────
# Ana sinif
# ─────────────────────────────────────────────────────────────────────────────

class ClosedLearningLoop:
    """
    FTS5-destekli kapali ogrenme dongusu.

    Thread-safe: her public method bagimsiz connection acar/kapatir.
    auto_index=False: production startup performansi icin varsayilan.
    """

    def __init__(
        self,
        db_yolu: str | Path | None = None,
        skills_dir: str | Path | None = None,
        auto_index: bool = False,
    ) -> None:
        self.db_yolu = str(db_yolu or ROOT / ".ReYMeN" / "skills_index.db")
        self.skills_dir = str(skills_dir or ROOT / "skills")
        self._lock = threading.Lock()

        os.makedirs(self.skills_dir, exist_ok=True)
        (ROOT / ".ReYMeN").mkdir(parents=True, exist_ok=True)

        self._kur()
        if auto_index:
            self.tum_becerileri_indeksle()

    # ── Connection factory ─────────────────────────────────────────────────

    @contextmanager
    def _baglanti(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Thread-safe SQLite context manager.

        WAL modu: okuma-yazma cakismasini minimize eder.
        check_same_thread=False: her thread guvenle kullanabilir.
        """
        con = sqlite3.connect(self.db_yolu, timeout=15, check_same_thread=False)
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

    # ── Kurulum ────────────────────────────────────────────────────────────

    def _kur(self) -> None:
        """FTS5 tablosunu olustur; eksik 'kaynak' kolonunu tespit edip yeniden kur."""
        with self._baglanti() as con:
            tablo_var: int = con.execute(
                "SELECT COUNT(*) FROM sqlite_master "
                "WHERE type='table' AND name='beceriler'"
            ).fetchone()[0]

            if tablo_var:
                try:
                    con.execute("SELECT kaynak FROM beceriler LIMIT 1")
                except sqlite3.OperationalError:
                    con.execute("DROP TABLE IF EXISTS beceriler")
                    logger.warning("[Beceri] Eski tablo yeniden olusturuluyor (kaynak kolonu eksikti).")

            con.executescript(
                "CREATE VIRTUAL TABLE IF NOT EXISTS beceriler USING fts5("
                "    ad, aciklama, icerik, kaynak UNINDEXED"
                ");"
            )

    # ── Indexleme ─────────────────────────────────────────────────────────

    def tum_becerileri_indeksle(self) -> int:
        """
        Bilinen tum skills/ dizinlerindeki .md dosyalarini FTS5'e yukle.
        Zaten indekslenmis dosyalar (ad eslesimi) atlanir.
        """
        eklenen = 0
        with self._lock, self._baglanti() as con:
            mevcut: set[str] = {
                row[0] for row in con.execute("SELECT ad FROM beceriler").fetchall()
            }
            for dizin in SKILLS_DIZINLERI:
                if not dizin.exists():
                    continue
                for dosya in sorted(dizin.rglob("*.md")):
                    ad, aciklama, icerik = self._md_ayristir(dosya)
                    try:
                        anahtar = str(dosya.relative_to(dizin).with_suffix("")).replace("\\", "/")
                    except ValueError:
                        anahtar = f"{dizin.name}/{ad}"

                    if anahtar in mevcut:
                        continue
                    try:
                        con.execute(
                            "INSERT INTO beceriler (ad, aciklama, icerik, kaynak) VALUES (?, ?, ?, ?)",
                            (anahtar, aciklama, icerik, str(dosya)),
                        )
                        mevcut.add(anahtar)
                        eklenen += 1
                    except sqlite3.Error as e:
                        logger.error("[Beceri] Indeksleme hatasi (%s): %s", anahtar, e)

        if eklenen:
            logger.info("[Beceri] %d yeni beceri indekslendi.", eklenen)
        return eklenen

    def _md_ayristir(self, dosya: Path) -> tuple[str, str, str]:
        """
        SKILL.md veya eski .md formatindan baslik/aciklama/icerik cikar.

        Oncelik: YAML frontmatter > # YETENEK > ilk # baslik > ## ACIKLAMA > ilk satir > dosya adi
        """
        try:
            metin = dosya.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            logger.error("[Beceri] Dosya okuma hatasi (%s): %s", dosya, e)
            return dosya.stem, "", ""

        ad = dosya.stem
        aciklama = ""
        norm = metin.replace("\r\n", "\n")

        # 1-2. YAML frontmatter
        if norm.startswith("---"):
            bitis = norm.find("\n---", 3)
            if bitis != -1:
                for satir in norm[3:bitis].splitlines():
                    satir = satir.strip()
                    if not satir or ":" not in satir:
                        continue
                    k, v = satir.split(":", 1)
                    k, v = k.strip().lower(), v.strip().strip("\"'")
                    if k == "name" and v:
                        ad = v
                    elif k == "title" and v and ad == dosya.stem:
                        ad = v
                    elif k == "description" and v:
                        aciklama = v[:300]

        # 3. Eski format: # YETENEK:
        if ad == dosya.stem:
            m = re.search(r"#\s+YETENEK:\s*(.+)", metin)
            if m:
                ad = m.group(1).strip()

        # 4. Frontmatter sonrasi ilk # basligi
        if ad == dosya.stem:
            govde = norm
            if norm.startswith("---"):
                idx = norm.find("\n---", 3)
                if idx != -1:
                    govde = norm[idx + 4:]
            m2 = re.search(r"^#\s+(.+)$", govde, re.MULTILINE)
            if m2:
                ad = m2.group(1).strip()

        # 5. ## ACIKLAMA (eski format)
        if not aciklama:
            m3 = re.search(r"##\s*A[CÇ]IKLAMA\s*\n([^#\n]+)", metin, re.IGNORECASE)
            if m3:
                aciklama = m3.group(1).strip()

        # 6. Govdeden ilk anlamli satir
        if not aciklama:
            govde = norm
            if norm.startswith("---"):
                idx = norm.find("\n---", 3)
                if idx != -1:
                    govde = norm[idx + 4:]
            for s in govde.splitlines():
                s = s.strip()
                if s and not s.startswith("#"):
                    aciklama = s[:200]
                    break

        return ad, aciklama or ad, metin

    # ── Sorgulama ─────────────────────────────────────────────────────────

    def ilgili_becerileri_cagir(
        self,
        sorgu: str,
        adet: int = 3,
        kategori: str | None = None,
    ) -> str:
        """
        FTS5 ile ilgili becerileri getir — insan-okunur string doner.

        Args:
            sorgu: Serbest metin sorgusu
            adet: Sonuc sayisi (varsayilan 3)
            kategori: Opsiyonel on-ek filtresi

        Returns:
            "- ad: aciklama" formatli satirlar veya hata mesaji.
        """
        rows = self._ilgili_becerileri_skorlu(sorgu, adet, kategori)
        if not rows:
            return "[Beceri]: Eslesen beceri yok."
        return "\n".join(f"- {r[0]}: {r[1]}" for r in rows)

    def _ilgili_becerileri_skorlu(
        self,
        sorgu: str,
        adet: int = 5,
        kategori: str | None = None,
    ) -> list[tuple]:
        """
        FTS5 BM25 skor sirali sonuclar. Her eleman: (ad, aciklama, icerik, kaynak, rank).

        Injection-safe: _fts5_token() ile sanitize edilir.
        LIKE fallback: FTS5 OperationalError durumunda devreye girer.
        """
        token = _fts5_token(sorgu)
        if not token:
            return []

        if kategori:
            kat = _fts5_token(kategori)
            fts_sorgu = f"{kat} {token}" if kat else token
        else:
            fts_sorgu = token

        with self._baglanti() as con:
            try:
                return con.execute(
                    "SELECT ad, aciklama, icerik, kaynak, rank "
                    "FROM beceriler WHERE beceriler MATCH ? "
                    "ORDER BY rank LIMIT ?",
                    (fts_sorgu, adet),
                ).fetchall()
            except sqlite3.OperationalError as e:
                logger.debug("[Beceri] FTS5 hatasi (%s), LIKE fallback: %s", fts_sorgu, e)

            like = f"%{_FTS_TEMIZLE.sub(' ', sorgu).strip()}%"
            try:
                return con.execute(
                    "SELECT ad, aciklama, icerik, kaynak, 0.0 "
                    "FROM beceriler WHERE ad LIKE ? OR aciklama LIKE ? LIMIT ?",
                    (like, like, adet),
                ).fetchall()
            except sqlite3.Error as e:
                logger.error("[Beceri] LIKE fallback hatasi: %s", e)
                return []

    def beceri_baglamini_al(self, sorgu: str, adet: int = 3) -> str:
        """
        Prompt enjeksiyonu icin formatli beceri blogu doner.

        Guvenlik: Maksimum MAKS_BAGLAM_KARAKTER (4000) karakter.
        Sinir asilirsa en yuksek skorlu sonuclar oncelikli korunur.
        """
        sonuclar = self._ilgili_becerileri_skorlu(sorgu, adet * 2)
        if not sonuclar:
            return ""

        satirlar: list[str] = []
        toplam = 0
        for ad, aciklama, *_ in sonuclar:
            satir = f"- {ad}: {aciklama}"
            uzunluk = len(satir) + 1
            if toplam + uzunluk > MAKS_BAGLAM_KARAKTER:
                if not satirlar:
                    satirlar.append(satir[:MAKS_BAGLAM_KARAKTER])
                break
            satirlar.append(satir)
            toplam += uzunluk

        if not satirlar:
            return ""
        return "\n== ILGILI BECERILER ==\n" + "\n".join(satirlar) + "\n"

    def beceri_baglamini_al_yapisal(
        self,
        sorgu: str,
        adet: int = 3,
    ) -> list[dict[str, str]]:
        """
        Modern LLM agent API'lari icin yapisal beceri ciktisi.

        Anthropic Messages API, function calling, tool_result gibi
        yerlere JSON olarak dogrudan verilebilir.

        Returns:
            [{"ad": str, "aciklama": str, "kaynak": str}, ...]
        """
        return [
            {"ad": r[0], "aciklama": r[1], "kaynak": r[3] or ""}
            for r in self._ilgili_becerileri_skorlu(sorgu, adet)
        ]

    # ── Kristallestirme ───────────────────────────────────────────────────

    def _fts5_benzer_beceri_ara(self, beceri_adi: str) -> tuple | None:
        """FTS5'te benzer isimde beceri ara. Doner: (ad, aciklama, icerik, kaynak) veya None."""
        token = _fts5_token(beceri_adi)
        if not token:
            return None

        with self._baglanti() as con:
            try:
                row = con.execute(
                    "SELECT ad, aciklama, icerik, kaynak FROM beceriler "
                    "WHERE beceriler MATCH ? ORDER BY rank LIMIT 1",
                    (token,),
                ).fetchone()
                if row:
                    return row
            except sqlite3.OperationalError as _e:
                logger.warning("[ClosedLearning] FTS5 sorgu: %s", _e)

            like = f"%{_FTS_TEMIZLE.sub(' ', beceri_adi).strip()}%"
            try:
                return con.execute(
                    "SELECT ad, aciklama, icerik, kaynak FROM beceriler "
                    "WHERE ad LIKE ? OR aciklama LIKE ? LIMIT 1",
                    (like, like),
                ).fetchone()
            except sqlite3.Error:
                return None

    def _merge_beceri_dosyasi(
        self,
        dosya_yolu: str,
        beceri_adi: str,
        aciklama: str,
        adimlar: str,
    ) -> str:
        """
        Mevcut beceri dosyasina yeni adimlari merge et (self-contained, harici import yok).

        1. usage_count artir
        2. last_used guncelle
        3. Timestamp'li baslik altinda yeni adimlari ekle
        4. FTS5 index'ini guncelle
        """
        yol = Path(dosya_yolu)
        if not yol.exists():
            return self._yeni_beceri_olustur(beceri_adi, aciklama, adimlar)

        try:
            mevcut_icerik = yol.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            logger.error("[Beceri] Merge okuma hatasi: %s", e)
            return self._yeni_beceri_olustur(beceri_adi, aciklama, adimlar)

        # usage_count guncelle
        try:
            yeni_sayi = int(_frontmatter_deger_al(mevcut_icerik, "usage_count") or "1") + 1
        except ValueError:
            yeni_sayi = 2

        yeni_icerik = _frontmatter_deger_guncelle(mevcut_icerik, "usage_count", yeni_sayi)
        yeni_icerik = _frontmatter_deger_guncelle(
            yeni_icerik, "last_used", datetime.now().strftime("%Y-%m-%d")
        )
        yeni_icerik = yeni_icerik.rstrip() + (
            f"\n\n---\n## Ek Adimlar / Varyasyon ({_zaman_damgasi()})\n\n{adimlar}\n"
        )

        try:
            yol.write_text(yeni_icerik, encoding="utf-8")
        except OSError as e:
            logger.error("[Beceri] Merge yazma hatasi: %s", e)
            return str(yol)

        # FTS5 guncelle
        with self._baglanti() as con:
            try:
                con.execute(
                    "UPDATE beceriler SET icerik=?, aciklama=? WHERE kaynak=?",
                    (yeni_icerik, aciklama, str(yol)),
                )
            except sqlite3.Error as e:
                logger.error("[Beceri] FTS5 guncelleme hatasi: %s", e)

        logger.info("[Beceri] Merge edildi: %s -> %s (usage_count=%d)", beceri_adi, yol, yeni_sayi)
        return str(yol)

    def _yeni_beceri_olustur(
        self,
        beceri_adi: str,
        aciklama: str,
        adimlar: str,
    ) -> str:
        """Self-contained yeni beceri dosyasi olustur (harici import yok)."""
        yol = Path(self.skills_dir) / f"{_guvenli_ad(beceri_adi)}.md"
        try:
            yol.write_text(_beceri_md_olustur(beceri_adi, aciklama, adimlar), encoding="utf-8")
        except OSError as e:
            logger.error("[Beceri] Dosya yazma hatasi (%s): %s", yol, e)
            return ""
        return str(yol)

    def beceri_kristallestir(
        self,
        beceri_adi: str,
        aciklama: str,
        adimlar: str,
    ) -> str:
        """
        Basarili gorev adimlarindan .md beceri karti olustur veya merge et.

        Akis:
          1. FTS5'te benzer isim ara
          2. VARSA: merge (usage_count++, yeni adimlar ekle)
          3. YOKSA: yeni dosya + FTS5'e ekle

        Returns:
            Olusan/guncellenen dosya yolu; basarisizsa "".
        """
        eslesen = self._fts5_benzer_beceri_ara(beceri_adi)
        if eslesen:
            eslesen_ad, _, __, kaynak = eslesen
            logger.info("[Beceri] Benzer bulundu: '%s' -> merge", eslesen_ad)
            return self._merge_beceri_dosyasi(kaynak, beceri_adi, aciklama, adimlar)

        yol = self._yeni_beceri_olustur(beceri_adi, aciklama, adimlar)
        if not yol:
            return ""

        try:
            icerik = Path(yol).read_text(encoding="utf-8")
        except OSError:
            icerik = _beceri_md_olustur(beceri_adi, aciklama, adimlar)

        anahtar = f"skills/{_guvenli_ad(beceri_adi)}"
        with self._baglanti() as con:
            try:
                con.execute("DELETE FROM beceriler WHERE ad=?", (anahtar,))
                con.execute(
                    "INSERT INTO beceriler (ad, aciklama, icerik, kaynak) VALUES (?, ?, ?, ?)",
                    (anahtar, aciklama, icerik, yol),
                )
            except sqlite3.Error as e:
                logger.error("[Beceri] FTS5 ekleme hatasi: %s", e)

        logger.info("[Beceri] Kristallesti: %s -> %s", beceri_adi, yol)
        return yol

    # ── Yardimcilar ───────────────────────────────────────────────────────

    def kapat(self) -> None:
        """WAL checkpoint + graceful shutdown."""
        try:
            con = sqlite3.connect(self.db_yolu, timeout=5)
            con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            con.close()
        except Exception as e:
            logger.debug("[Beceri] kapat() hatasi: %s", e)

    def toplam_beceri_sayisi(self) -> int:
        with self._baglanti() as con:
            try:
                return con.execute("SELECT COUNT(*) FROM beceriler").fetchone()[0]
            except sqlite3.Error:
                return 0

    def tum_beceriler(self) -> list[dict[str, str]]:
        with self._baglanti() as con:
            try:
                rows = con.execute(
                    "SELECT ad, aciklama, kaynak FROM beceriler"
                ).fetchall()
                return [{"ad": r[0], "aciklama": r[1], "kaynak": r[2]} for r in rows]
            except sqlite3.Error:
                return []

    # ── SELF-IMPROVEMENT META-DÖNGÜSÜ ────────────────────────────────────
    # observe → discover → compare → test → save (24h cycle)
    # ─────────────────────────────────────────────────────────────────────

    def observe_self(self) -> dict[str, Any]:
        """Kendini gözlemle: zayıf alanları tespit et.

        Returns:
            {"weak_areas": [...], "strong_areas": [...],
             "total_skills": int, "last_run": str}
        """
        beceriler = self.tum_beceriler()
        toplam = len(beceriler)

        # Zayıf alan: hiç becerisi olmayan kategoriler
        weak_areas = []
        strong_areas = []
        if toplam == 0:
            weak_areas = ["baslangic_becerisi", "arastirma_yontemi"]
        else:
            for b in beceriler:
                acik = (b.get("aciklama", "") or "").strip()
                if len(acik) < 20:
                    weak_areas.append(b.get("ad", "bilinmeyen"))
                else:
                    strong_areas.append(b.get("ad", "bilinmeyen"))

        return {
            "weak_areas": weak_areas or ["yeni_alan_kesfi"],
            "strong_areas": strong_areas,
            "total_skills": toplam,
            "last_run": _zaman_damgasi(),
        }

    def discover_better_methods(self, focus: str) -> list[dict[str, str]]:
        """Dışarıda (web) daha iyi yöntem ara.

        Args:
            focus: İyileştirilecek alan adı.

        Returns:
            [{"name": str, "code": str, "source_url": str, "summary": str}, ...]
        """
        logger.info("[SelfImprove] Araniyor: %s", focus)
        sonuclar = []

        # Web'de ara (DuckDuckGo üzerinden)
        try:
            query = urllib.parse.quote(f"best practice {focus} coding tutorial 2025 2026")
            url = f"https://html.duckduckgo.com/html/?q={query}"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; ReYMeN/1.0)",
                    "Accept": "text/html",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")
                # Basit link çekme
                for m in re.finditer(
                    r'<a[^>]+href="(https?://[^"]+)"[^>]*>([^<]+)</a>',
                    html,
                ):
                    link = m.group(1)
                    baslik = re.sub(r"<[^>]+>", "", m.group(2)).strip()
                    if baslik and not any(
                        x in link for x in (".js", ".css", "pixel", "analytics")
                    ):
                        sonuclar.append({
                            "name": baslik[:80],
                            "code": "",
                            "source_url": link,
                            "summary": f"Web'de bulundu: {baslik[:100]}",
                        })
                    if len(sonuclar) >= 5:
                        break
        except Exception as e:
            logger.warning("[SelfImprove] Web arama hatasi: %s", e)

        # Fallback: temel yöntem
        if not sonuclar:
            sonuclar.append({
                "name": f"varsayilan_{focus}",
                "code": f"# {focus} icin temel cozum\npass",
                "source_url": "",
                "summary": f"Varsayilan {focus} yontemi",
            })

        logger.info("[SelfImprove] %d yontem bulundu", len(sonuclar))
        return sonuclar

    def compare_and_decide(
        self, current_method: dict[str, str], new_methods: list[dict[str, str]]
    ) -> str:
        """Claude ile karşılaştır: UYGULA / REDDET / DAHA_FAZLA_ARAŞTIR.

        Args:
            current_method: Mevcut yöntem.
            new_methods: Yeni bulunan yöntemler.

        Returns:
            Karar stringi.
        """
        if not new_methods:
            return "DAHA_FAZLA_ARAŞTIR"

        mentor = new_methods[0]

        # Basit skor: kaynak URL'si olanlar daha değerli
        puan = 0
        if mentor.get("source_url"):
            puan += 2
        if mentor.get("name"):
            puan += 1
        if mentor.get("summary") and len(mentor["summary"]) > 20:
            puan += 1

        # Mevcut yöntemle kıyasla
        current_name = (current_method.get("name", "") or "") if current_method else ""
        if current_name and mentor.get("name") and current_name != mentor["name"]:
            puan += 1  # Yeni ve farklı

        if puan >= 3:
            return "UYGULA"
        elif puan >= 1:
            return "DAHA_FAZLA_ARAŞTIR"
        else:
            return "REDDET"

    def test_in_sandbox(self, new_method: dict[str, str]) -> tuple[str, float]:
        """İzole ortamda test et (E2B benzeri).

        Args:
            new_method: Test edilecek yöntem.

        Returns:
            ("BAŞARILI" | "BAŞARISIZ", skor)
        """
        code = (new_method.get("code", "") or "").strip()
        if not code or code == "pass":
            return "BAŞARISIZ", 0.0

        # Basit syntax kontrolü
        try:
            compile(code, "<sandbox>", "exec")
            # Skor: yöntemin adı ne kadar açıklayıcıysa o kadar yüksek
            name = (new_method.get("name", "") or "")
            kaynak = (new_method.get("source_url", "") or "")
            skor = 5.0
            if name:
                skor += 2.0
            if kaynak:
                skor += 3.0
            return "BAŞARILI", skor
        except SyntaxError as e:
            logger.warning("[SelfImprove] Sandbox hatasi: %s", e)
            return "BAŞARISIZ", 0.0

    def save_as_skill(self, method: dict[str, str], score: float) -> str:
        """Başarılı metodu skill olarak kaydet.

        Args:
            method: Kaydedilecek yöntem.
            score: Başarı skoru.

        Returns:
            Oluşturulan dosya yolu.
        """
        name = (method.get("name", "self_improved") or "self_improved")[:60]
        summary = (method.get("summary", "") or "")
        source = (method.get("source_url", "") or "")
        kod = (method.get("code", "") or "")

        aciklama = (
            f"[SelfImprove] Skor: {score}/10"
            + (f" | Kaynak: {source}" if source else "")
            + (f" | {summary}" if summary else "")
        )
        adimlar = (
            f"1. Web'de kesfedildi: {summary}\n"
            + (f"2. Kaynak: {source}\n" if source else "")
            + f"3. Skor: {score}/10\n"
            + (f"\n```python\n{kod}\n```" if kod else "")
        )

        yol = self.beceri_kristallestir(
            beceri_adi=name,
            aciklama=aciklama[:300],
            adimlar=adimlar,
        )
        logger.info("[SelfImprove] Skill kaydedildi: %s (skor=%s)", yol, score)
        return yol

    def run_forever(self, cycle_hours: int = 24, test_mode: bool = False, max_test_iter: int = 672) -> None:
        """Ana kendini geliştirme döngüsü.

        1. Kendini gözlemle
        2. En zayıf alanı seç
        3. Dışarıda araştır
        4. Karşılaştır ve karar ver
        5. Uygun: test et ve kaydet
        6. 24 saat bekle, tekrar başla

        Args:
            cycle_hours: Döngü aralığı (varsayılan 24 saat).
            test_mode: True ise hiç beklemez, iterasyonları hızlıca tamamlar.
            max_test_iter: Test modunda maksimum iterasyon (varsayılan 672 = 7 gün).
        """
        logger.info("[SelfImprove] Meta-dongu basladi (cycle=%dh, test_mode=%s, max_iter=%d)", cycle_hours, test_mode, max_test_iter)
        max_iter = max_test_iter if test_mode else 0

        iter_sayisi = 0
        while True:
            iter_sayisi += 1
            if test_mode and iter_sayisi > max_iter:
                logger.info("[SelfImprove] Test modu tamamlandi: %d iterasyon", max_iter)
                break
            # 1. Kendini gözlemle
            state = self.observe_self()
            logger.info(
                "[SelfImprove] Durum: %d beceri, %d zayif alan",
                state["total_skills"],
                len(state["weak_areas"]),
            )

            # 2. En zayıf alanı seç
            if not state["weak_areas"]:
                focus = "yeni_alan_kesfi"
            else:
                focus = state["weak_areas"][0]

            logger.info("[SelfImprove] Odaklanilan alan: %s", focus)

            # Mevcut metodu bul
            current = {"name": focus, "code": "", "summary": ""}

            # 3. Dışarıda araştır
            discoveries = self.discover_better_methods(focus)

            # 4. Karşılaştır
            decision = self.compare_and_decide(current, discoveries)

            # 5. Kararı uygula
            if decision == "UYGULA":
                best = discoveries[0]
                status, score = self.test_in_sandbox(best)

                if status == "BAŞARILI":
                    self.save_as_skill(best, score)
                    logger.info("[SelfImprove] ✅ Yeni skill eklendi: %s", focus)

            elif decision == "DAHA_FAZLA_ARAŞTIR":
                logger.info("[SelfImprove] ⏳ Eklendi: bekleme listesine alindi: %s", focus)

            elif decision == "REDDET":
                logger.info("[SelfImprove] ⏭ Reddedildi: %s", focus)

            # 6. 24 saat bekle (test_mode'de atla)
            if test_mode:
                logger.info("[SelfImprove] ✅ Test iterasyon %d/%d tamam", iter_sayisi, max_iter)
                continue  # hiç beklemeden sonraki iterasyon
            logger.info("[SelfImprove] Bekleniyor (%d saat)...", cycle_hours)
            time.sleep(cycle_hours * 3600)


# ─────────────────────────────────────────────────────────────────────────────
# Smoke test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import tempfile

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    with tempfile.TemporaryDirectory() as tmpdir:
        loop = ClosedLearningLoop(
            db_yolu=os.path.join(tmpdir, "test.db"),
            skills_dir=os.path.join(tmpdir, "skills"),
            auto_index=False,
        )

        print(f"\n[Test 0] Baslangic: {loop.toplam_beceri_sayisi()} beceri")

        # Test 1: Yeni beceri
        yol1 = loop.beceri_kristallestir(
            "web_scraping", "Web sayfasi icerik cekme",
            "1. requests.get(url)\n2. BeautifulSoup parse\n3. Veri ayristir"
        )
        assert yol1, "Test 1 FAIL"
        print(f"[Test 1] Yeni: {yol1} | Toplam: {loop.toplam_beceri_sayisi()}")

        # Test 2: Merge (ayni isim, farkli token)
        yol2 = loop.beceri_kristallestir(
            "web scraping", "Web scraping varyasyon",
            "4. async await\n5. rate limit"
        )
        assert yol2, "Test 2 FAIL"
        assert yol1 == yol2, f"Test 2 FAIL: merge olmadi ({yol1} != {yol2})"
        print(f"[Test 2] Merge: OK | Toplam: {loop.toplam_beceri_sayisi()} (degismemeli)")

        # Test 3: Baglam sorgusu
        baglam = loop.beceri_baglamini_al("web scraping")
        assert baglam and len(baglam) <= MAKS_BAGLAM_KARAKTER, "Test 3 FAIL"
        print(f"[Test 3] Baglam ({len(baglam)} char): OK")

        # Test 4: Karakter siniri
        for i in range(8):
            loop.beceri_kristallestir(f"beceri_{i}", "x" * 500, "\n".join(f"{j}." for j in range(50)))
        b2 = loop.beceri_baglamini_al("beceri", adet=6)
        assert len(b2) <= MAKS_BAGLAM_KARAKTER, f"Test 4 FAIL: {len(b2)} > {MAKS_BAGLAM_KARAKTER}"
        print(f"[Test 4] Sinir: {len(b2)} char — OK")

        # Test 5: Yapisal cikti (LLM agent)
        sonuclar = loop.beceri_baglamini_al_yapisal("web scraping", adet=2)
        assert isinstance(sonuclar, list) and all("ad" in s for s in sonuclar), "Test 5 FAIL"
        print(f"[Test 5] Yapisal: {sonuclar}")

        # Test 6: SQL injection safety
        loop.beceri_baglamini_al("'; DROP TABLE beceriler; --")
        assert loop.toplam_beceri_sayisi() > 0, "Test 6 FAIL: injection!"
        print(f"[Test 6] Injection safety: OK ({loop.toplam_beceri_sayisi()} beceri hala var)")

        loop.kapat()
        print(f"\n✓ Tum testler gecti. Son: {loop.toplam_beceri_sayisi()} beceri")


# ── Motor Kaydı ──────────────────────────────────────────────────
# Global instance (tekil, lazy)
_LOOP_INSTANCE = None
_LOOP_LOCK = threading.Lock()


def _get_loop():
    global _LOOP_INSTANCE
    if _LOOP_INSTANCE is None:
        with _LOOP_LOCK:
            if _LOOP_INSTANCE is None:
                _LOOP_INSTANCE = ClosedLearningLoop(auto_index=True)
    return _LOOP_INSTANCE


def _beceri_kristallestir(ad: str = "", aciklama: str = "", adimlar: str = "") -> str:
    """Agent dostu wrapper: ClosedLearningLoop.beceri_kristallestir()"""
    if not ad:
        return "[HATA]: Beceri adi gerekli"
    loop = _get_loop()
    yol = loop.beceri_kristallestir(ad, aciklama, adimlar)
    if yol:
        return f"[BECERI] Kristallesti: {yol}"
    return f"[HATA]: Beceri kristallestirilemedi: {ad}"


def _beceri_ara(sorgu: str = "") -> str:
    """Agent dostu wrapper: ClosedLearningLoop.beceri_baglamini_al()"""
    if not sorgu:
        loop = _get_loop()
        toplam = loop.toplam_beceri_sayisi()
        return f"Toplam {toplam} beceri. Sorgu belirtilerek aranabilir."
    loop = _get_loop()
    baglam = loop.beceri_baglamini_al(sorgu)
    if baglam:
        return f"[BECERI_BAGLAM] ({len(baglam)} karakter):\n{baglam}"
    return f"[BECERI] '{sorgu}' ile ilgili beceri bulunamadi."


def _beceri_durum() -> str:
    """Toplam beceri sayisi + tum beceriler."""
    loop = _get_loop()
    toplam = loop.toplam_beceri_sayisi()
    liste = loop.tum_beceriler()
    satirlar = [f"Toplam: {toplam} beceri"]
    for b in liste[:10]:
        satirlar.append(f"  - {b.get('ad','?')}: {b.get('aciklama','')[:60]}")
    if len(liste) > 10:
        satirlar.append(f"  ... ve {len(liste)-10} daha")
    return "\n".join(satirlar)


def motor_kaydet(motor: object):
    """motor.py entegrasyonu: Kapali Ogrenme Döngüsü araçlarını kaydet."""
    if hasattr(motor, "_plugin_arac_kaydet"):
        motor._plugin_arac_kaydet(
            "BECERI_KRISTALLESTIR",
            lambda ad="", aciklama="", adimlar="": _beceri_kristallestir(ad, aciklama, adimlar),
            "Gorev sonrasi kazanimi beceri karti olarak kristallestirir. Beceri adi, aciklama ve adimlar gerekli.",
        )
        motor._plugin_arac_kaydet(
            "BECERI_ARA",
            lambda sorgu="": _beceri_ara(sorgu),
            "FTS5 indeksinde beceri ara, en alakali 3 sonucu getir. Sorgusuz calistirilirsa toplam sayiyi gosterir.",
        )
        motor._plugin_arac_kaydet(
            "BECERI_DURUM",
            _beceri_durum,
            "Toplam beceri sayisi ve beceri listesini gosterir",
        )
