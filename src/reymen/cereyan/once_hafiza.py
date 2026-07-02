# -*- coding: utf-8 -*-
"""
once_hafiza.py — Hafıza-öncelikli çalışma motoru.

Her görev önce hafızaya bakar, bilgi varsa direkt uygular,
yoksa dener, sonucu kaydeder.

Kullanım:
    sonuc = once_hafiza.isle(
        hedef="nmap ile port tara",
        kategori="kali/network",
        calistir=lambda: kali_sandbox.calistir("nmap --help")
    )
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# ── Varsayılan yol ────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.resolve()
DB_YOLU = ROOT.parent / "merkez_db" / "ogrenmeler.db"

# 6 ay = ~180 gün
GECERLILIK_GUN = 180

_yazma_kilit = threading.Lock()


# ── Kademeli Güven Fonksiyonu ─────────────────────────────────────────────

def _kademeli_guven(basari: int, hata: int) -> float:
    """
    Sigmoid benzeri kademeli güven hesaplama.

    İlk başarıda 0.5, 3 başarıda ~0.75, 10 başarıda ~0.95.
    Hata oranı arttıkça güven düşer.

    Formül: 1 / (1 + e^(-0.5 * (basari - hata - 1)))
    - İlk kayıt (1 basari, 0 hata): 0.5
    - 3 basari, 0 hata: ~0.73
    - 10 basari, 0 hata: ~0.99
    - 1 basari, 3 hata: ~0.12
    """
    import math
    net = basari - hata - 1  # -1 offset: ilk kayıtta 0.5
    return 1.0 / (1.0 + math.exp(-0.5 * net))


# ── Veritabanı ────────────────────────────────────────────────────────────

def _kur(con: sqlite3.Connection) -> None:
    """ogrenmeler tablosunu oluştur."""
    con.executescript("""
        CREATE TABLE IF NOT EXISTS ogrenmeler (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            hedef           TEXT NOT NULL,
            kategori        TEXT NOT NULL DEFAULT 'genel',
            icerik          TEXT NOT NULL,
            guven_skoru     REAL NOT NULL DEFAULT 1.0,
            basari_sayisi   INTEGER NOT NULL DEFAULT 1,
            hata_sayisi     INTEGER NOT NULL DEFAULT 0,
            son_kullanim    TEXT NOT NULL DEFAULT (date('now')),
            gecerlilik_tarihi TEXT NOT NULL DEFAULT (date('now', '+180 days')),
            kaynak_url      TEXT DEFAULT NULL,
            olusturulma     TEXT NOT NULL DEFAULT (datetime('now')),
            guncelleme      TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_ogrenmeler_kategori ON ogrenmeler(kategori);
        CREATE INDEX IF NOT EXISTS idx_ogrenmeler_hedef   ON ogrenmeler(hedef);
        CREATE INDEX IF NOT EXISTS idx_ogrenmeler_gecerli ON ogrenmeler(gecerlilik_tarihi);
    """)

    # Migration: eski tablolara kaynak_url ekle (güvenli, sadece yoksa)
    try:
        con.execute("ALTER TABLE ogrenmeler ADD COLUMN kaynak_url TEXT DEFAULT NULL")
    except Exception as _e:
        err_msg = str(_e)
        if "duplicate column" not in err_msg.lower():
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %s: %s", type(_e).__name__, err_msg
            )


@contextmanager
def _baglanti():
    con = sqlite3.connect(str(DB_YOLU), timeout=15, check_same_thread=False)
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


# ── Ana API ───────────────────────────────────────────────────────────────

def kaydet(
    hedef: str,
    kategori: str = "genel",
    icerik: str = "",
    basari: bool = True,
    gecerlilik_gun: int = GECERLILIK_GUN,
    kaynak_url: str | None = None,
) -> int:
    """
    Yeni öğrenme kaydı oluştur veya varsa güncelle.

    Args:
        hedef: Görev tanımı (örn. "nmap ile port tara")
        kategori: "kali", "dron", "cad", "kali/network" vb.
        icerik: Öğrenilen bilgi / çözüm
        basari: Başarılı mı?
        gecerlilik_gun: Kaç gün geçerli? (default: 180)
        kaynak_url: Bilginin kaynağı (web URL'si) (default: None)

    Returns:
        Kayıt ID'si
    """
    _db_kur()
    bugun = date.today().isoformat()
    gecerlilik = (date.today() + timedelta(days=gecerlilik_gun)).isoformat()

    with _yazma_kilit:
        with _baglanti() as con:
            # Daha önce aynı hedef+kategori var mı?
            var = con.execute(
                "SELECT id, basari_sayisi, hata_sayisi, guven_skoru FROM ogrenmeler "
                "WHERE hedef = ? AND kategori = ? LIMIT 1",
                (hedef, kategori),
            ).fetchone()

            if var:
                kayit_id, basari_once, hata_once, guven_once = var
                yeni_basari = basari_once + (1 if basari else 0)
                yeni_hata = hata_once + (0 if basari else 1)
                toplam = yeni_basari + yeni_hata
                # Kademeli güven: sigmoid benzeri, 3 başarıda ~0.75
                guven = round(_kademeli_guven(yeni_basari, yeni_hata), 4)

                con.execute(
                    """UPDATE ogrenmeler SET
                        icerik = ?,
                        guven_skoru = ?,
                        basari_sayisi = ?,
                        hata_sayisi = ?,
                        son_kullanim = ?,
                        gecerlilik_tarihi = ?,
                        kaynak_url = COALESCE(?, kaynak_url),
                        guncelleme = datetime('now')
                    WHERE id = ?""",
                    (icerik, guven, yeni_basari, yeni_hata,
                     bugun, gecerlilik, kaynak_url, kayit_id),
                )
                logger.info("[Hafiza] Guncellendi: %s/%s (guven=%.2f, %d basari, %d hata)",
                           kategori, hedef[:40], guven, yeni_basari, yeni_hata)
                return kayit_id
            else:
                # İlk kayıt: guven=0.5 başlangıç, kademeli artar
                baslangic_guven = 0.5 if basari else 0.1
                con.execute(
                    """INSERT INTO ogrenmeler
                       (hedef, kategori, icerik, guven_skoru, basari_sayisi, hata_sayisi,
                        son_kullanim, gecerlilik_tarihi, kaynak_url)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (hedef, kategori, icerik,
                     baslangic_guven,
                     1 if basari else 0,
                     0 if basari else 1,
                     bugun, gecerlilik, kaynak_url),
                )
                kayit_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
                logger.info("[Hafiza] Yeni kayit: %s/%s (id=%d, guven=%.2f)",
                           kategori, hedef[:40], kayit_id, baslangic_guven)
                return kayit_id


def ara(
    hedef: str,
    kategori: str | None = None,
    min_guven: float = 0.3,
    gecerli_mi: bool = True,
) -> list[dict[str, Any]]:
    """
    Hafızada benzer görev/çözüm ara.

    Her sonuç için `durum` alanı:
      - "guvenilir" → guven_skoru >= 0.5
      - "belirsiz"  → guven_skoru < 0.5

    Args:
        hedef: Aranan görev
        kategori: Sınırla (None = tümü)
        min_guven: Minimum güven skoru (0.0-1.0)
        gecerli_mi: Sadece geçerlilik tarihi geçmemiş olanlar?

    Returns:
        [{"id", "hedef", "kategori", "icerik", "guven_skoru", "durum",
          "son_kullanim", "gecerlilik_tarihi", ...}, ...]
    """
    _db_kur()
    kosullar = ["guven_skoru >= ?"]
    params: list[Any] = [min_guven]

    if kategori:
        kosullar.append("kategori = ?")
        params.append(kategori)

    if gecerli_mi:
        kosullar.append("gecerlilik_tarihi >= date('now')")

    # Tam eşleşme önce, sonra LIKE
    with _baglanti() as con:
        # 1) Tam eşleşme
        tam_sql = (
            "SELECT id, hedef, kategori, icerik, guven_skoru, "
            "basari_sayisi, hata_sayisi, son_kullanim, gecerlilik_tarihi, kaynak_url "
            "FROM ogrenmeler WHERE hedef = ? AND {} "
            "ORDER BY guven_skoru DESC, son_kullanim DESC LIMIT 5"
        ).format(" AND ".join(kosullar))
        tam = con.execute(tam_sql, [hedef] + params).fetchall()

        # 2) Benzer (LIKE)
        benzer_sql = (
            "SELECT id, hedef, kategori, icerik, guven_skoru, "
            "basari_sayisi, hata_sayisi, son_kullanim, gecerlilik_tarihi, kaynak_url "
            "FROM ogrenmeler WHERE hedef LIKE ? AND {} "
            "ORDER BY guven_skoru DESC, son_kullanim DESC LIMIT 5"
        ).format(" AND ".join(kosullar))
        benzer = con.execute(benzer_sql, ["%{}%".format(hedef)] + params).fetchall()

    # Birleştir, duplicate'leri at
    gorulen: set[int] = set()
    sonuc = []
    for row in tam + benzer:
        if row[0] not in gorulen:
            gorulen.add(row[0])
            guven = row[4]
            sonuc.append({
                "id": row[0],
                "hedef": row[1],
                "kategori": row[2],
                "icerik": row[3],
                "guven_skoru": guven,
                "durum": "guvenilir" if guven >= 0.5 else "belirsiz",
                "basari_sayisi": row[5],
                "hata_sayisi": row[6],
                "son_kullanim": row[7],
                "gecerlilik_tarihi": row[8],
                "kaynak_url": row[9] if len(row) > 9 else None,
            })

    return sonuc


def hafizada_ara(
    hedef: str,
    kategori: str | None = None,
    min_guven: float = 0.3,
    gecerli_mi: bool = True,
) -> list[dict[str, Any]]:
    """Alias: ara() ile aynı. Kullanıcı 'hafizada_ara()' dediğinde çalışır."""
    return ara(hedef, kategori, min_guven, gecerli_mi)


def guven_guncelle(kayit_id: int, basari: bool) -> float:
    """
    Bir kaydın güven skorunu güncelle (başarı/hata sayısına göre).

    Returns:
        Yeni güven skoru
    """
    with _yazma_kilit:
        with _baglanti() as con:
            var = con.execute(
                "SELECT basari_sayisi, hata_sayisi FROM ogrenmeler WHERE id = ?",
                (kayit_id,),
            ).fetchone()
            if not var:
                return 0.0

            yeni_basari = var[0] + (1 if basari else 0)
            yeni_hata = var[1] + (0 if basari else 1)
            # Kademeli güven (sigmoid)
            guven = round(_kademeli_guven(yeni_basari, yeni_hata), 4)

            con.execute(
                """UPDATE ogrenmeler SET
                    guven_skoru = ?,
                    basari_sayisi = ?,
                    hata_sayisi = ?,
                    son_kullanim = date('now'),
                    guncelleme = datetime('now')
                WHERE id = ?""",
                (guven, yeni_basari, yeni_hata, kayit_id),
            )

            if basari:
                logger.info("[Hafiza] Basari +1 (id=%d, guven=%.2f)", kayit_id, guven)
            else:
                logger.info("[Hafiza] Hata +1 (id=%d, guven=%.2f)", kayit_id, guven)

            return guven


def eski_kayitlari_temizle(gun_limiti: int = 200) -> int:
    """
    Geçerlilik tarihi geçmiş kayıtları temizle.
    Ama yüksek güvenli (>=0.8) olanları koru.

    Returns:
        Silinen kayıt sayısı
    """
    _db_kur()
    with _yazma_kilit:
        with _baglanti() as con:
            sil = con.execute(
                "DELETE FROM ogrenmeler "
                "WHERE gecerlilik_tarihi < date('now', ?) AND guven_skoru < 0.8",
                ("-{} days".format(gun_limiti),),
            ).rowcount
            if sil:
                logger.info("[Hafiza] %d eski kayit temizlendi.", sil)
            return sil


def isle(
    hedef: str,
    kategori: str = "genel",
    calistir: Callable[[], T] | None = None,
    min_guven: float = 0.5,
    gecerli_mi: bool = True,
    zorla: bool = False,
) -> tuple[T | dict | None, str]:
    """
    *** ANA API — Hafıza-öncelikli görev çalıştırma ***

    Akış:
        1. Hafızada benzer görev ara
        2a. Bulundu + güven >= min_guven + geçerli → önbellekten döndür
        2b. Bulunamadı veya güven düşük → calistir() fonksiyonunu çalıştır
        3. Sonucu hafızaya kaydet
        4. Sonucu döndür

    Args:
        hedef: Görev tanımı
        kategori: Kategori
        calistir: Çalıştırılacak fonksiyon (None = sadece hafıza sorgula)
        min_guven: Önbellek için minimum güven
        gecerli_mi: Geçerlilik kontrolü yap?
        zorla: True = hafızaya bakma, direkt çalıştır

    Returns:
        (sonuc, kaynak)
        sonuc: calistir()'ın döndürdüğü değer veya hafızadaki kayıt
        kaynak: "cache" (hafızadan) / "exec" (çalıştırıldı) / "not_found"
    """
    _db_kur()

    if not zorla:
        kayitlar = ara(hedef, kategori, min_guven=min_guven, gecerli_mi=gecerli_mi)
        if kayitlar:
            en_iyi = kayitlar[0]
            logger.info("[Hafiza] ONBELLEK: %s/%s (guven=%.2f)",
                       en_iyi["kategori"], en_iyi["hedef"][:40], en_iyi["guven_skoru"])
            # Kullanım güncelle
            guven_guncelle(en_iyi["id"], basari=True)

            if calistir is None:
                # Sadece hafıza sorgulama modu
                return en_iyi, "cache"

            # Önbellekte var ama yine de çalıştır? Hayır — direkt döndür
            return en_iyi, "cache"

    if calistir is None:
        return None, "not_found"

    # Çalıştır
    try:
        sonuc = calistir()
        kaydet(hedef, kategori, str(sonuc)[:5000] if sonuc else "", basari=True)
        return sonuc, "exec"
    except Exception as e:
        hata_mesaji = "[HATA] {}: {}".format(type(e).__name__, e)
        logger.warning("[Hafiza] Basarisiz: %s/%s — %s", kategori, hedef[:40], hata_mesaji)
        kaydet(hedef, kategori, hata_mesaji, basari=False)
        raise


def istatistik() -> dict[str, Any]:
    """Hafıza istatistikleri."""
    _db_kur()
    with _baglanti() as con:
        toplam = con.execute("SELECT COUNT(*) FROM ogrenmeler").fetchone()[0]
        gecerli = con.execute(
            "SELECT COUNT(*) FROM ogrenmeler WHERE gecerlilik_tarihi >= date('now')"
        ).fetchone()[0]
        eski = con.execute(
            "SELECT COUNT(*) FROM ogrenmeler WHERE gecerlilik_tarihi < date('now')"
        ).fetchone()[0]
        kategori_say = con.execute(
            "SELECT kategori, COUNT(*) FROM ogrenmeler GROUP BY kategori ORDER BY COUNT(*) DESC"
        ).fetchall()
        ortalama_guven = con.execute(
            "SELECT ROUND(AVG(guven_skoru), 4) FROM ogrenmeler"
        ).fetchone()[0] or 0.0

    return {
        "toplam": toplam,
        "gecerli": gecerli,
        "eski": eski,
        "ortalama_guven": ortalama_guven,
        "kategori_dagilimi": {k: v for k, v in kategori_say},
    }


# ── Belirsiz Görev Çözümleme ──────────────────────────────────────────────

def belirsiz_gorev_cozumle(
    hedef: str,
    esik: float = 0.3,
    max_kategori: int = 3,
) -> dict[str, Any]:
    """
    Belirsiz bir görev geldiğinde hafızadaki en alakalı kategorileri bulur
    ve kullanıcıya tek bir tahmin önerisi hazırlar.

    Akış:
        1. Görevi anahtar kelimelere ayır
        2. Her kategori altındaki kayıtları tara
        3. En alakalı kategoriyi + ilgili kaydı bul
        4. Kullanıcıya soru formatında döndür

    Args:
        hedef: Kullanıcının verdiği belirsiz görev (örn. "sistemi güvenli yap")
        esik: Minimum benzerlik eşiği (0.0-1.0)
        max_kategori: Önerilecek maksimum alternatif kategori sayısı

    Returns:
        {
            "tahmin_kategori": "kali/network" veya None,
            "tahmin_kayit": {...} veya None,
            "guven": 0.75,
            "alternatifler": [...],
            "soru": "Sanırım port taraması yapmak istiyorsun, doğru mu?",
            "ham_hedef": "sistemi güvenli yap"
        }
    """
    _db_kur()

    # 1) Görevi normalize et ve anahtar kelimelere ayır
    kelimeler = _anahtar_kelimeler(hedef)
    if not kelimeler:
        return {
            "tahmin_kategori": None,
            "tahmin_kayit": None,
            "guven": 0.0,
            "alternatifler": [],
            "soru": None,
            "ham_hedef": hedef,
        }

    with _baglanti() as con:
        # 2) Tüm geçerli kayıtları çek
        tum_kayitlar = con.execute(
            "SELECT id, hedef, kategori, icerik, guven_skoru, basari_sayisi, hata_sayisi "
            "FROM ogrenmeler WHERE gecerlilik_tarihi >= date('now') "
            "ORDER BY guven_skoru DESC, basari_sayisi DESC"
        ).fetchall()

    if not tum_kayitlar:
        return {
            "tahmin_kategori": None,
            "tahmin_kayit": None,
            "guven": 0.0,
            "alternatifler": [],
            "soru": None,
            "ham_hedef": hedef,
        }

    # 3) Her kaydın görevle benzerlik skorunu hesapla
    skorlu: list[tuple[float, dict[str, Any]]] = []
    for row in tum_kayitlar:
        kayit = {
            "id": row[0],
            "hedef": row[1],
            "kategori": row[2],
            "icerik": row[3][:200],
            "guven_skoru": row[4],
            "basari_sayisi": row[5],
            "hata_sayisi": row[6],
        }
        skor = _benzerlik_skoru(hedef, kelimeler, kayit)
        if skor >= esik:
            skorlu.append((skor, kayit))

    # 4) Skora göre sırala
    skorlu.sort(key=lambda x: x[0], reverse=True)

    # 4b) Hiç kelime eşleşmezse en yüksek güvenli kaydı öner (backup)
    if not skorlu:
        # Güven skoru >= 0.8 olan en iyi kaydı bul
        en_guvenli = max(tum_kayitlar, key=lambda r: r[4]) if tum_kayitlar else None
        if en_guvenli and en_guvenli[4] >= 0.8:
            kayit = {
                "id": en_guvenli[0],
                "hedef": en_guvenli[1],
                "kategori": en_guvenli[2],
                "icerik": en_guvenli[3][:200],
                "guven_skoru": en_guvenli[4],
                "basari_sayisi": en_guvenli[5],
                "hata_sayisi": en_guvenli[6],
            }
            kategori = kayit["kategori"]
            kayit_hedef = kayit["hedef"]
            soru = ("Hiçbir kayıt tam eşleşmedi ama en güvenilir bildiğim "
                    + kategori + " kategorisindeki _" + kayit_hedef + "_.\n\n"
                    + "Sanırım **" + kayit_hedef + "** demek istiyorsun, doğru mu?")
            return {
                "tahmin_kategori": kategori,
                "tahmin_kayit": kayit,
                "guven": 0.01,
                "alternatifler": [],
                "soru": soru,
                "ham_hedef": hedef,
            }

        return {
            "tahmin_kategori": None,
            "tahmin_kayit": None,
            "guven": 0.0,
            "alternatifler": [],
            "soru": None,
            "ham_hedef": hedef,
        }

    # 5) En iyi tahmini seç
    en_iyi_skor, en_iyi_kayit = skorlu[0]

    # Alternatifler (farklı kategorilerden)
    gorulen_kategori: set[str] = set()
    alternatifler = []
    for skor, kayit in skorlu:
        if kayit["kategori"] not in gorulen_kategori and len(alternatifler) < max_kategori:
            gorulen_kategori.add(kayit["kategori"])
            alternatifler.append({"skor": round(skor, 2), **kayit})
            if len(alternatifler) >= max_kategori:
                break

    # 6) Soruyu oluştur
    kategori = en_iyi_kayit["kategori"]
    kayit_hedef = en_iyi_kayit["hedef"]
    satir1 = "Hafızamda **" + kategori + "** kategorisinde _" + kayit_hedef + "_ bilgisi var."
    soru = satir1 + "\n\nSanırım **" + kayit_hedef + "** demek istiyorsun, doğru mu?"

    return {
        "tahmin_kategori": kategori,
        "tahmin_kayit": en_iyi_kayit,
        "guven": round(en_iyi_skor, 2),
        "alternatifler": alternatifler[1:],
        "soru": soru,
        "ham_hedef": hedef,
    }


def _anahtar_kelimeler(metin: str) -> list[str]:
    """Metni temizle ve anlamlı anahtar kelimelere ayır."""
    # Türkçe karakterleri normalize et
    temiz = metin.lower().strip()
    # Noktalama işaretlerini kaldır
    for ch in ".,!?;:()[]{}''\"“”‘’…––/":
        temiz = temiz.replace(ch, " ")
    # Kelimelere ayır
    kelimeler = [k for k in temiz.split() if len(k) > 1]
    return kelimeler


def _benzerlik_skoru(
    hedef: str,
    kelimeler: list[str],
    kayit: dict[str, Any],
) -> float:
    """
    İki metin arasındaki benzerlik skorunu hesapla.

    3 faktör:
    - Anahtar kelime eşleşmesi (hedef kayit.hedef)
    - Kategori eşleşmesi (kelimeler kayit.kategori)
    - Güven skoru bonusu
    """
    kayit_kelimeler = _anahtar_kelimeler(kayit["hedef"] + " " + kayit["kategori"])
    if not kayit_kelimeler:
        return 0.0

    # Kelime eşleşme oranı
    eslesen = sum(1 for k in kelimeler if k in kayit_kelimeler)
    toplam = max(len(kelimeler), len(kayit_kelimeler))
    kelime_skor = eslesen / toplam if toplam > 0 else 0.0

    # Kategori eşleşmesi (kategori adındaki kelimeler)
    kat_kelimeler = _anahtar_kelimeler(kayit["kategori"])
    kat_eslesen = sum(1 for k in kelimeler if k in kat_kelimeler)
    kat_skor = kat_eslesen / max(len(kelimeler), 1) * 0.5  # max 0.5 bonus

    # Güven skoru bonusu (guven > 0.8 ise +0.1, guven > 0.5 ise +0.05)
    guven_bonus = 0.0
    if kayit["guven_skoru"] >= 0.8:
        guven_bonus = 0.1
    elif kayit["guven_skoru"] >= 0.5:
        guven_bonus = 0.05

    # Toplam skor [0.0, 1.0]
    skor = kelime_skor * 0.6 + kat_skor + guven_bonus
    return min(skor, 1.0)


# ── İlk kurulum ───────────────────────────────────────────────────────────
_db_kur()
