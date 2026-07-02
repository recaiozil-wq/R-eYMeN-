# -*- coding: utf-8 -*-
"""
vektor_bellek.py — VektorBellek: Embedding + semantic search.

ChromaDB backend (varsayilan), SQLite fallback.
Embedding model: sentence-transformers/all-MiniLM-L6-v2 (opsiyonel)
Eger sentence-transformers yoksa ChromaDB'nin built-in embedding fonksiyonu kullanilir.

Kullanim:
    >>> from reymen.hafiza.vektor_bellek import VektorBellek
    >>> vb = VektorBellek()
    >>> vid = vb.ekle("ReYMeN projesi ChromaDB ile calisir", {"kategori": "not"})
    >>> sonuc = vb.ara("ChromaDB hakkinda bilgi", k=3)
    >>> vb.sil(vid)
    >>> vb.listele()
"""

from __future__ import annotations

import logging
import time
import os
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── ChromaDB ──────────────────────────────────────────────────────────────────
try:
    import chromadb
    from chromadb.config import Settings as _ChromaSettings

    CHROMA_MEVCUT = True
except ImportError:
    CHROMA_MEVCUT = False

# ── sentence-transformers (opsiyonel) ─────────────────────────────────────────
try:
    import sentence_transformers

    SENTENCE_TRANSFORMERS_MEVCUT = True
except ImportError:
    SENTENCE_TRANSFORMERS_MEVCUT = False

# ── Varsayilan sabitler ───────────────────────────────────────────────────────
VARSAYILAN_DIZIN = str(Path(__file__).parent.parent.parent / "vektor_hafizasi")
VARSAYILAN_MODEL = "all-MiniLM-L6-v2"
MAKS_KAYIT = 8000          # Baslangic 5000'di, 8000'e yukseltildi
ESIK_BENZERLIK = 0.15       # Arama esigi (altindaki sonuclar filtrelenir)
ESIK_DEDUP = 0.85           # Dedup esigi (ustundeki kayit tekrar eklenmez)


# ═══════════════════════════════════════════════════════════════════════════════
#  SQLite Fallback
# ═══════════════════════════════════════════════════════════════════════════════

class _SQLiteVektorBellek:
    """ChromaDB yoksa kullanilacak SQLite tabanli basit vektor benzeri bellek.

    Gercek embedding yapamaz; Jaccard benzerligi + keyword match kullanir.
    """

    def __init__(self, db_path: str = ""):
        import sqlite3

        self._db_path = db_path or str(
            Path(__file__).parent.parent.parent / "vektor_hafizasi" / "vektor_fallback.db"
        )
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vektor_kayit (
                id TEXT PRIMARY KEY,
                metin TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                zaman REAL NOT NULL
            )
            """
        )
        self._conn.commit()

    def ekle(self, metin: str, metadata: Optional[Dict] = None) -> str:
        """Metni kaydet, hash tabanli ID don."""
        kayit_id = hashlib.sha256(metin.encode("utf-8")).hexdigest()[:16]
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)
        try:
            self._conn.execute(
                "INSERT OR REPLACE INTO vektor_kayit (id, metin, metadata, zaman) VALUES (?, ?, ?, ?)",
                (kayit_id, metin, meta_json, time.time()),
            )
            self._conn.commit()
        except Exception as e:
            logger.warning("[SQLiteVektorBellek] Ekleme hatasi: %s", e)
        return kayit_id

    def ara(self, sorgu: str, k: int = 5) -> List[Tuple[str, str, float, Dict]]:
        """Jaccard benzerligi ile ara (kelime ortakligi tabanli)."""
        sorgu_kelimeleri = set(sorgu.lower().split())
        if not sorgu_kelimeleri:
            return []

        cursor = self._conn.execute(
            "SELECT id, metin, metadata, zaman FROM vektor_kayit ORDER BY zaman DESC LIMIT ?",
            (MAKS_KAYIT,),
        )
        skorlu = []
        for row in cursor.fetchall():
            doc_kelimeleri = set(row[1].lower().split())
            ortak = len(sorgu_kelimeleri & doc_kelimeleri)
            birlesim = len(sorgu_kelimeleri | doc_kelimeleri)
            jaccard = ortak / birlesim if birlesim else 0.0
            if jaccard > 0:
                try:
                    meta = json.loads(row[2])
                except (json.JSONDecodeError, TypeError):
                    meta = {}
                skorlu.append((row[0], row[1], jaccard, meta))

        skorlu.sort(key=lambda x: x[2], reverse=True)
        return skorlu[:k]

    def sil(self, kayit_id: str) -> bool:
        try:
            self._conn.execute("DELETE FROM vektor_kayit WHERE id = ?", (kayit_id,))
            self._conn.commit()
            return True
        except Exception as e:
            logger.warning("[SQLiteVektorBellek] Silme hatasi: %s", e)
            return False

    def listele(self, limit: int = 100) -> List[Dict]:
        cursor = self._conn.execute(
            "SELECT id, metin, metadata, zaman FROM vektor_kayit ORDER BY zaman DESC LIMIT ?",
            (limit,),
        )
        sonuc = []
        for row in cursor.fetchall():
            try:
                meta = json.loads(row[2])
            except (json.JSONDecodeError, TypeError):
                meta = {}
            sonuc.append({"id": row[0], "metin": row[1], "metadata": meta, "zaman": row[3]})
        return sonuc

    def __len__(self) -> int:
        try:
            cursor = self._conn.execute("SELECT COUNT(*) FROM vektor_kayit")
            return cursor.fetchone()[0]
        except Exception:
            return 0

    def kapat(self):
        try:
            self._conn.close()
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )


# ═══════════════════════════════════════════════════════════════════════════════
#  VektorBellek Ana Sinif
# ═══════════════════════════════════════════════════════════════════════════════

class VektorBellek:
    """Embedding tabanli anlamsal bellek.

    ChromaDB backend (varsayilan) kullanir, yoksa SQLite fallback'e gecer.
    sentence-transformers opsiyoneldir; yoksa ChromaDB'nin built-in embedding'i
    (onnx all-MiniLM-L6-v2) kullanilir.

    Kullanim:
        vb = VektorBellek(koleksiyon_adi="ReYMeN_bellek")
        vb.ekle("Proje hakkinda not", {"kategori": "genel"})
        sonuclar = vb.ara("Proje notlari", k=3)
        vb.sil("id123")
        kayitlar = vb.listele()
    """

    def __init__(
        self,
        koleksiyon_adi: str = "ReYMeN_bellek",
        kalici_dizin: str = "",
        embedding_model: str = VARSAYILAN_MODEL,
    ):
        self._koleksiyon_adi = koleksiyon_adi
        self._kalici_dizin = kalici_dizin or VARSAYILAN_DIZIN
        self._embedding_model = embedding_model
        self._fallback: Optional[_SQLiteVektorBellek] = None

        # ChromaDB'yi dene
        self._koleksiyon = None
        if CHROMA_MEVCUT:
            self._chroma_kur()
        else:
            logger.info("[VektorBellek] ChromaDB mevcut degil, SQLite fallback kullanilacak")
            self._fallback = _SQLiteVektorBellek()

    def _chroma_kur(self):
        """ChromaDB PersistentClient ile koleksiyonu kur."""
        try:
            Path(self._kalici_dizin).mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(
                path=self._kalici_dizin,
                settings=_ChromaSettings(anonymized_telemetry=False),
            )
            self._koleksiyon = client.get_or_create_collection(
                name=self._koleksiyon_adi,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                "[VektorBellek] ChromaDB koleksiyonu '%s' hazir (%s kayit)",
                self._koleksiyon_adi,
                self._koleksiyon.count(),
            )
        except Exception as e:
            logger.warning("[VektorBellek] ChromaDB kurulum hatasi: %s — SQLite fallback", e)
            self._koleksiyon = None
            self._fallback = _SQLiteVektorBellek()

    # ── Temel metotlar ────────────────────────────────────────────────────────

    def ekle(self, metin: str, metadata: Optional[Dict] = None) -> str:
        """Metni vektor bellege ekle.

        Args:
            metin: Eklenecek metin (bos olamaz)
            metadata: Opsiyonel metadata dict

        Returns:
            Kayit ID'si (str)
        """
        if not metin or not metin.strip():
            logger.warning("[VektorBellek] Bos metin eklenemez")
            return ""

        # Fallback modu
        if self._fallback:
            return self._fallback.ekle(metin, metadata)

        # ChromaDB modu
        kayit_id = hashlib.sha256(metin.encode("utf-8")).hexdigest()[:16]
        meta = {"zaman": str(time.time())}
        if metadata:
            meta.update({k: str(v) for k, v in metadata.items()})

        # Dedup: benzer icerik var mi?
        try:
            sonuc = self._koleksiyon.query(query_texts=[metin[:500]], n_results=1)
            mevcut_doclar = sonuc.get("documents", [[]])[0]
            mesafeler = sonuc.get("distances", [[]])[0]
            if mevcut_doclar and mesafeler:
                benzerlik = 1 - mesafeler[0]
                if benzerlik >= ESIK_DEDUP:
                    logger.debug("[VektorBellek] Tekrar eden kayit atlandi: %.2f benzerlik", benzerlik)
                    return kayit_id
        except Exception as e:
            logger.debug("[VektorBellek] Dedup sorgu hatasi (goz ardi edildi): %s", e)

        # Kaydet
        try:
            self._koleksiyon.add(ids=[kayit_id], documents=[metin], metadatas=[meta])
            # Budama
            self._budama_yap()
            return kayit_id
        except Exception as e:
            logger.warning("[VektorBellek] ChromaDB ekleme hatasi: %s", e)
            return ""

    def ara(self, sorgu: str, k: int = 5) -> List[Tuple[str, str, float, Dict]]:
        """Anlamsal arama yap.

        Args:
            sorgu: Arama sorgusu
            k: Kac sonuc donsun (default: 5)

        Returns:
            [(id, metin, skor, metadata), ...] — skor cosine similarity (0-1)
        """
        if not sorgu or not sorgu.strip():
            return []

        # Fallback modu
        if self._fallback:
            return self._fallback.ara(sorgu, k=k)

        # ChromaDB modu
        try:
            sonuc = self._koleksiyon.query(
                query_texts=[sorgu[:500]],
                n_results=min(k, MAKS_KAYIT),
            )
            dokumanlar = sonuc.get("documents", [[]])[0]
            ids = sonuc.get("ids", [[]])[0]
            mesafeler = sonuc.get("distances", [[]])[0]
            metadatalar = sonuc.get("metadatas", [[]])[0]

            sonuclar = []
            for i, doc_id in enumerate(ids):
                if i < len(dokumanlar) and i < len(mesafeler):
                    skor = 1 - mesafeler[i]  # cosine distance -> cosine similarity
                    if skor >= ESIK_BENZERLIK:
                        meta_raw = metadatalar[i] if i < len(metadatalar) else {}
                        meta = {k: v for k, v in meta_raw.items()} if meta_raw else {}
                        sonuclar.append((doc_id, dokumanlar[i], round(skor, 4), meta))

            # Skor'a gore sirala (yuksek -> dusuk)
            sonuclar.sort(key=lambda x: x[2], reverse=True)
            return sonuclar

        except Exception as e:
            logger.warning("[VektorBellek] ChromaDB arama hatasi: %s", e)
            return []

    def sil(self, kayit_id: str) -> bool:
        """Belirtilen ID'ye sahip kaydi sil.

        Args:
            kayit_id: Silinecek kaydin ID'si

        Returns:
            Basarili mi?
        """
        if not kayit_id:
            return False

        if self._fallback:
            return self._fallback.sil(kayit_id)

        try:
            self._koleksiyon.delete(ids=[kayit_id])
            return True
        except Exception as e:
            logger.warning("[VektorBellek] Silme hatasi: %s", e)
            return False

    def listele(self, limit: int = 100) -> List[Dict]:
        """Tum kayitlari listele (en yeniden eskiye).

        Args:
            limit: Maksimum kayit sayisi

        Returns:
            [{"id": ..., "metin": ..., "metadata": ..., "zaman": ...}, ...]
        """
        if self._fallback:
            return self._fallback.listele(limit=limit)

        try:
            peek = self._koleksiyon.peek(limit=limit)
            ids = peek.get("ids", [])
            dokumanlar = peek.get("documents", [])
            metadatalar = peek.get("metadatas", [])

            sonuc = []
            for i, doc_id in enumerate(ids):
                meta = {}
                if i < len(metadatalar) and metadatalar[i]:
                    meta = {k: v for k, v in metadatalar[i].items()}
                sonuc.append({
                    "id": doc_id,
                    "metin": dokumanlar[i] if i < len(dokumanlar) else "",
                    "metadata": meta,
                    "zaman": meta.get("zaman", ""),
                })
            return sonuc
        except Exception as e:
            logger.warning("[VektorBellek] Listeleme hatasi: %s", e)
            return []

    def __len__(self) -> int:
        """Kayit sayisi."""
        if self._fallback:
            return len(self._fallback)
        try:
            return self._koleksiyon.count()
        except Exception:
            return 0

    def _budama_yap(self):
        """Maks kayit limitini asan en eski kayitlari sil."""
        try:
            adet = self._koleksiyon.count()
            if adet <= MAKS_KAYIT:
                return
            fazla = adet - MAKS_KAYIT
            peek = self._koleksiyon.peek(limit=fazla + 10)
            silinecek = peek.get("ids", [])[:fazla]
            if silinecek:
                self._koleksiyon.delete(ids=silinecek)
                logger.info("[VektorBellek] Budama: %d kayit silindi", len(silinecek))
        except Exception as e:
            logger.debug("[VektorBellek] Budama hatasi (goz ardi edildi): %s", e)

    def kapat(self):
        """Baglantilari kapat (fallback modunda)."""
        if self._fallback:
            try:
                self._fallback.kapat()
            except Exception as _e:
                __import__("logging").getLogger(__name__).warning(
                    "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                )

    # ── Bilgi ─────────────────────────────────────────────────────────────────

    def bilgi(self) -> Dict:
        """Vektor bellek hakkinda bilgi dondur."""
        return {
            "backend": "chromadb" if self._koleksiyon else ("sqlite_fallback" if self._fallback else "yok"),
            "koleksiyon": self._koleksiyon_adi,
            "kayit_sayisi": len(self),
            "dizin": self._kalici_dizin,
            "embedding_model": self._embedding_model,
            "esik_benzerlik": ESIK_BENZERLIK,
            "esik_dedup": ESIK_DEDUP,
            "maks_kayit": MAKS_KAYIT,
        }


# ── Varsayilan singleton ──────────────────────────────────────────────────────
_vb_instance: Optional[VektorBellek] = None


def vektor_bellek_al() -> VektorBellek:
    """Varsayilan VektorBellek singleton'ini al."""
    global _vb_instance
    if _vb_instance is None:
        _vb_instance = VektorBellek()
    return _vb_instance


# ═══════════════════════════════════════════════════════════════════════════════
#  Test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print("=== VektorBellek Test ===")

    vb = VektorBellek(koleksiyon_adi="test_bellek")
    print(f"Bilgi: {vb.bilgi()}")

    # Ekle
    id1 = vb.ekle("ReYMeN projesi ChromaDB ile calisir", {"kategori": "teknik"})
    id2 = vb.ekle("Kullanici kisa cevaplari sever", {"kategori": "kullanici"})
    id3 = vb.ekle("Python dilinde yazilmis bir ajan sistemi", {"kategori": "teknik"})
    print(f"Eklenen ID'ler: {id1}, {id2}, {id3}")

    # Ara
    sonuclar = vb.ara("ChromaDB hakkinda bilgi", k=3)
    print(f"\nArama sonuclari ({len(sonuclar)}):")
    for sid, metin, skor, meta in sonuclar:
        print(f"  [{skor:.4f}] {metin[:80]} | meta: {meta}")

    # Listele
    print(f"\nTum kayitlar ({len(vb)}):")
    for kayit in vb.listele():
        print(f"  {kayit['id']}: {kayit['metin'][:60]}")

    # Sil
    if id1:
        vb.sil(id1)
        print(f"\nSilindi: {id1}")
        print(f"Kalan kayit: {len(vb)}")

    vb.kapat()
    print("\n✓ Test tamamlandi")
