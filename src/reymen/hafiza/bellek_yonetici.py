# -*- coding: utf-8 -*-
"""
bellek_yonetici.py — BellekYonetici: Vektor + SQLite hibrit hafiza yoneticisi.

VektorBellek (anlamsal arama) ile SQLite hafiza (yapisal kayit) sistemini
tek bir API altinda birlestirir. Hibrit arama, eski kayit temizleme ve
entegre bellek yonetimi saglar.

Kullanim:
    >>> from reymen.hafiza.bellek_yonetici import BellekYonetici
    >>> by = BellekYonetici()
    >>> by.hatirla("ChromaDB hakkinda bilgi")
    >>> by.unut(esik_saat=72)
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.reymen.hafiza.vektor_bellek import VektorBellek, vektor_bellek_al

logger = logging.getLogger(__name__)

# ── SQLite Hafiza (AltAjanHafiza tabanli) ────────────────────────────────────
try:
    from reymen.hafiza.hafiza import AltAjanHafiza, alt_ajan_hafiza

    _HAFIZA_MEVCUT = True
except ImportError:
    _HAFIZA_MEVCUT = False
    AltAjanHafiza = None
    alt_ajan_hafiza = None


# ═══════════════════════════════════════════════════════════════════════════════
#  BellekYonetici
# ═══════════════════════════════════════════════════════════════════════════════

class BellekYonetici:
    """Vektor + SQLite hibrit hafiza yoneticisi.

    Iki bellek sistemini tek bir API altinda toplar:
    - Vektor bellek: anlamsal arama (VektorBellek/ChromaDB)
    - SQLite bellek: yapisal kayit (AltAjanHafiza)

    Ozellikler:
    - hatirla(sorgu): vektor + SQLite hibrit sonuc
    - unut(esik_saat): eski kayitlari temizle
    - otomatik senkronizasyon
    """

    def __init__(
        self,
        vektor_bellek: Optional[VektorBellek] = None,
        sqlite_hafiza: Optional[Any] = None,
        varsayilan_k: int = 5,
    ):
        """
        Args:
            vektor_bellek: VektorBellek instance (None = varsayilan singleton)
            sqlite_hafiza: AltAjanHafiza instance (None = varsayilan singleton)
            varsayilan_k: Varsayilan arama sonuc sayisi
        """
        self._vektor = vektor_bellek or vektor_bellek_al()
        self._sqlite = sqlite_hafiza or alt_ajan_hafiza if _HAFIZA_MEVCUT else None
        self._k = varsayilan_k

    # ── Vektor bellek islemleri ───────────────────────────────────────────────

    def vektor_ekle(self, metin: str, metadata: Optional[Dict] = None) -> str:
        """Vektor bellege metin ekle.

        Args:
            metin: Eklenecek metin
            metadata: Opsiyonel metadata

        Returns:
            Kayit ID'si
        """
        return self._vektor.ekle(metin, metadata)

    def vektor_ara(self, sorgu: str, k: Optional[int] = None) -> List[Tuple]:
        """Vektor belleginde anlamsal ara.

        Args:
            sorgu: Arama sorgusu
            k: Kac sonuc (None = varsayilan)

        Returns:
            [(id, metin, skor, metadata), ...]
        """
        return self._vektor.ara(sorgu, k=k or self._k)

    def vektor_sil(self, kayit_id: str) -> bool:
        """Vektor bellekten kayit sil."""
        return self._vektor.sil(kayit_id)

    def vektor_listele(self, limit: int = 100) -> List[Dict]:
        """Vektor bellek icerigini listele."""
        return self._vektor.listele(limit=limit)

    # ── SQLite hafiza islemleri ───────────────────────────────────────────────

    def sqlite_kaydet(self, task_id: str, tur: str, veri: dict) -> None:
        """SQLite hafizaya kayit ekle (AltAjanHafiza)."""
        if self._sqlite:
            self._sqlite.kaydet(task_id, tur, veri)

    def sqlite_yukle(self, task_id: str) -> Optional[Dict]:
        """SQLite hafizadan kayit yukle."""
        if self._sqlite:
            return self._sqlite.yukle(task_id)
        return None

    def sqlite_ara(self, sorgu: str, limit: int = 10) -> List[Dict]:
        """SQLite hafizada keyword ara (task listesi icinde)."""
        if not self._sqlite:
            return []
        # task_listele'den gelen sonuclari sorgu ile filtrele
        tasklar = self._sqlite.task_listele(limit=50)
        sorgu_lower = sorgu.lower()
        sonuc = []
        for t in tasklar:
            # task_id'de veya son_tur'de sorgu var mi?
            if sorgu_lower in str(t.get("task_id", "")).lower():
                sonuc.append(t)
                if len(sonuc) >= limit:
                    break
        return sonuc

    # ── Hibrit arama ──────────────────────────────────────────────────────────

    def hatirla(self, sorgu: str, k: Optional[int] = None) -> Dict:
        """Hibrit arama: vektor + SQLite sonuclarini birlestir.

        Args:
            sorgu: Arama sorgusu
            k: Maksimum sonuc sayisi

        Returns:
            {
                "vektor": [...],      # vektor arama sonuclari
                "sqlite": [...],       # SQLite arama sonuclari
                "hibrit": [...],       # birlestirilmis, siralanmis sonuclar
                "toplam": int
            }
        """
        k_gercek = k or self._k

        # Vektor arama
        vektor_sonuc = self._vektor.ara(sorgu, k=k_gercek)
        vektor_liste = []
        for vid, metin, skor, meta in vektor_sonuc:
            vektor_liste.append({
                "kaynak": "vektor",
                "id": vid,
                "icerik": metin,
                "skor": skor,
                "metadata": meta,
            })

        # SQLite arama
        sqlite_sonuc = self.sqlite_ara(sorgu, limit=k_gercek)
        sqlite_liste = []
        for s in sqlite_sonuc:
            sqlite_liste.append({
                "kaynak": "sqlite",
                "id": s.get("task_id", ""),
                "icerik": f"Task: {s.get('task_id', '')} - {s.get('son_tur', '')}",
                "skor": 0.5,  # SQLite icin sabit skor
                "metadata": s,
            })

        # Hibrit birlesim: once vektor (yuksek skor), sonra SQLite
        hibrit = list(vektor_liste)
        # SQLite sonuclarini ekle (vektor'de olmayanlari)
        mevcut_idler = {h["id"] for h in hibrit}
        for s in sqlite_liste:
            if s["id"] not in mevcut_idler:
                hibrit.append(s)

        return {
            "vektor": vektor_liste,
            "sqlite": sqlite_liste,
            "hibrit": hibrit[: k_gercek + len(sqlite_liste)],
            "toplam": len(vektor_liste) + len(sqlite_liste),
        }

    # ── Eski kayit temizleme ──────────────────────────────────────────────────

    def unut(self, esik_saat: int = 72) -> Dict:
        """Eski kayitlari temizle.

        Args:
            esik_saat: Su andan kac saat onceki kayitlar silinsin (default: 72)

        Returns:
            {
                "vektor_silinen": int,
                "sqlite_silinen": int,
                "mesaj": str
            }
        """
        sonuc = {"vektor_silinen": 0, "sqlite_silinen": 0}

        # Vektor bellek budama (varsayilan mekanizma)
        # Vektor bellek otomatik budama yapar, manuel mudahale gerekmez
        vektor_adet = len(self._vektor)
        sonuc["vektor_sayisi"] = vektor_adet

        # SQLite eski task'lari temizle
        if self._sqlite and hasattr(self._sqlite, "task_listele"):
            silinen = 0
            tasklar = self._sqlite.task_listele(limit=200)
            simdi = time.time()
            esik_saniye = esik_saat * 3600
            for t in tasklar:
                son_guncelleme = t.get("son_guncelleme", 0)
                if son_guncelleme and (simdi - son_guncelleme) > esik_saniye:
                    task_id = t.get("task_id", "")
                    if task_id and self._sqlite.temizle(task_id):
                        silinen += 1
            sonuc["sqlite_silinen"] = silinen

        sonuc["mesaj"] = (
            f"Temizlik tamam. "
            f"Vektor bellek: {sonuc.get('vektor_sayisi', '?')} kayit, "
            f"SQLite: {sonuc['sqlite_silinen']} eski task silindi."
        )
        return sonuc

    # ── Bilgi ─────────────────────────────────────────────────────────────────

    def bilgi(self) -> Dict:
        """Bellek yoneticisi hakkinda bilgi dondur."""
        return {
            "vektor": self._vektor.bilgi(),
            "sqlite_mevcut": self._sqlite is not None,
            "varsayilan_k": self._k,
        }

    def ozet(self) -> str:
        """Insan okunabilir ozet."""
        info = self.bilgi()
        lines = [
            "=== BellekYonetici Ozeti ===",
            f"  Vektor bellek : {info['vektor']['backend']} ({info['vektor']['kayit_sayisi']} kayit)",
            f"  SQLite hafiza : {'Aktif' if info['sqlite_mevcut'] else 'Devre disi'}",
            f"  Varsayilan k  : {info['varsayilan_k']}",
        ]
        return "\n".join(lines)


# ── Varsayilan singleton ──────────────────────────────────────────────────────
_bellek_yonetici_instance: Optional[BellekYonetici] = None


def bellek_yonetici_al() -> BellekYonetici:
    """Varsayilan BellekYonetici singleton'ini al."""
    global _bellek_yonetici_instance
    if _bellek_yonetici_instance is None:
        _bellek_yonetici_instance = BellekYonetici()
    return _bellek_yonetici_instance


# ═══════════════════════════════════════════════════════════════════════════════
#  Test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== BellekYonetici Test ===")

    by = BellekYonetici()
    print(by.ozet())

    # Vektor ekle
    id1 = by.vektor_ekle("ReYMeN projesi ChromaDB ile calisir", {"kategori": "teknik"})
    id2 = by.vektor_ekle("Kullanici kisa cevaplari sever", {"kategori": "kullanici"})
    print(f"Vektor kayit: {id1}, {id2}")

    # Hibrit ara
    sonuc = by.hatirla("ChromaDB", k=3)
    print(f"\nHibrit arama: {sonuc['toplam']} sonuc")
    for item in sonuc["hibrit"]:
        print(f"  [{item['kaynak']}] ({item['skor']}) {item['icerik'][:60]}")

    # Bilgi
    print(f"\n{by.ozet()}")

    print("\n✓ Test tamamlandi")
