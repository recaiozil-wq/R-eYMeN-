# -*- coding: utf-8 -*-
"""
vektorel_hafiza.py — ChromaDB anlamsal bellek (RAG).

Ozellikler:
- ChromaDB varsa kosi benzerligiyle arama, yoksa TF benzeri yedek
- Otomatik zaman damgasi + basari/basarisiz metadata
- Esik onlemesi: cok benzer tecrubeler tekrar kaydedilmez
- Hafiza budama: maks_kayit asiminda en eski kayitlar siliner
- Oturumlar arasi kalici (PersistentClient)
"""

import time
import math
import logging
from collections import Counter

logger = logging.getLogger(__name__)

try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

MAKS_HAFIZA = 2000   # En fazla bu kadar kayit
ESIK_BENZERLIK = 0.85  # Bu benzerligin ustundeki kayit tekrar kaydedilmez


class _BasitYedek:
    """ChromaDB yoksa kullanilan TF-IDF benzeri bellek yedegi."""

    def __init__(self):
        self._kayitlar: list = []

    def add(self, ids, documents, metadatas):
        mevcut_idler = {k["id"] for k in self._kayitlar}
        for i, d, m in zip(ids, documents, metadatas):
            if i not in mevcut_idler:
                self._kayitlar.append({"id": i, "doc": d, "meta": m or {}})

    def upsert(self, ids, documents, metadatas):
        mevcut = {k["id"]: k for k in self._kayitlar}
        for i, d, m in zip(ids, documents, metadatas):
            if i in mevcut:
                mevcut[i]["doc"] = d
                mevcut[i]["meta"] = m or {}
            else:
                self._kayitlar.append({"id": i, "doc": d, "meta": m or {}})

    @staticmethod
    def _counter_cosine(query_words, doc_words):
        """Counter tabanli kosinus benzerligi (std11, ek paket yok)."""
        if not query_words or not doc_words:
            return 0.0
        all_words = set(query_words.keys()) | set(doc_words.keys())
        q_vec = [float(query_words.get(w, 0)) for w in all_words]
        d_vec = [float(doc_words.get(w, 0)) for w in all_words]
        dot = sum(a * b for a, b in zip(q_vec, d_vec))
        q_norm = math.sqrt(sum(a * a for a in q_vec))
        d_norm = math.sqrt(sum(a * a for a in d_vec))
        if q_norm == 0 or d_norm == 0:
            return 0.0
        return dot / (q_norm * d_norm)

    def query(self, query_texts, n_results=3, **kwargs):
        sorgu_kelimeleri = Counter(query_texts[0].lower().split())
        skorlu = []
        for k in self._kayitlar:
            doc_kelimeleri = Counter(k["doc"].lower().split())
            benzerlik = self._counter_cosine(sorgu_kelimeleri, doc_kelimeleri)
            skorlu.append((benzerlik, k))
        skorlu.sort(key=lambda x: x[0], reverse=True)
        secili = [k for s, k in skorlu[:n_results] if s > 0]
        return {
            "documents": [[k["doc"] for k in secili]],
            "metadatas": [[k["meta"] for k in secili]],
            "ids": [[k["id"] for k in secili]],
            "distances": [[1 - s for s, k in skorlu[:n_results] if s > 0]],
        }

    def delete(self, ids=None, where=None):
        if ids:
            id_set = set(ids)
            self._kayitlar = [k for k in self._kayitlar if k["id"] not in id_set]

    def count(self):
        return len(self._kayitlar)

    def peek(self, limit=5):
        return {
            "ids": [k["id"] for k in self._kayitlar[:limit]],
            "documents": [k["doc"] for k in self._kayitlar[:limit]],
        }


def vektorel_hafiza_sistemini_kur(yol="./vektor_hafizasi"):
    """ChromaDB koleksiyonu veya yedek bellek olustur."""
    if CHROMA_AVAILABLE:
        try:
            client = chromadb.PersistentClient(path=yol)
            return client.get_or_create_collection(
                name="ReYMeN_tecrube",
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as _e:
            logger.warning("[VektorelHafiza] except Exception (L88): %s", Exception)
            pass
    return _BasitYedek()


def tecrube_kaydet(collection, kayit_id: str, icerik: str, metadata: dict = None) -> bool:
    """Tecrube kaydet — zaman damgasi ve metadata otomatik eklenir.

    Cok benzer bir kayit zaten varsa tekrar kaydedilmez (dedup).
    """
    if not icerik or not icerik.strip():
        return False

    meta = {"zaman": str(time.time()), "basari": "evet"}
    if metadata:
        meta.update({k: str(v) for k, v in metadata.items()})

    # Dedup: benzer icerik zaten var mi?
    try:
        sonuc = collection.query(query_texts=[icerik[:200]], n_results=1)
        mevcut_doclar = sonuc.get("documents", [[]])[0]
        mesafeler = sonuc.get("distances", [[]])[0]
        if mevcut_doclar and mesafeler:
            benzerlik = 1 - mesafeler[0]  # cosine distance → similarity
            if benzerlik >= ESIK_BENZERLIK:
                return False  # Zaten mevcut
    except Exception as _e:
        logger.warning("[VektorelHafiza] except Exception (L114): %s", Exception)
        pass

    try:
        # upsert: ayni id varsa guncelle
        if hasattr(collection, "upsert"):
            collection.upsert(ids=[kayit_id], documents=[icerik], metadatas=[meta])
        else:
            collection.add(ids=[kayit_id], documents=[icerik], metadatas=[meta])
        # Maks kayit asiminda en eski kayitlari budama
        _budama_yap(collection)
        return True
    except Exception:
        return False


def _budama_yap(collection):
    """Hafizanin asiminda en eski kayitlari sil."""
    try:
        adet = collection.count()
        if adet <= MAKS_HAFIZA:
            return
        fazla = adet - MAKS_HAFIZA
        peek = collection.peek(limit=fazla + 10)
        silinecek = peek.get("ids", [])[:fazla]
        if silinecek:
            collection.delete(ids=silinecek)
    except Exception as _e:
        logger.warning("[VektorelHafiza] except Exception (L141): %s", Exception)
        pass


def anlamsal_hafiza_ara(collection, sorgu: str, adet: int = 3) -> str:
    """Anlamsal arama — ilgili tecrübeleri dondurur.

    Returns:
        Bulunan tecrübelerin metin listesi veya bulunamadı mesajı.
    """
    try:
        sonuc = collection.query(query_texts=[sorgu[:300]], n_results=adet)
        dokumanlar = sonuc.get("documents", [[]])[0]
        if not dokumanlar:
            return "[Hafıza]: İlgili tecrübe bulunamadı."

        # Mesafeye gore siralama (dusuk mesafe = yuksek benzerlik)
        mesafeler = sonuc.get("distances", [[]])[0]
        if mesafeler and len(mesafeler) == len(dokumanlar):
            ciftler = sorted(zip(mesafeler, dokumanlar), key=lambda x: x[0])
            dokumanlar = [d for _, d in ciftler]

        return "\n".join(f"- {d[:200]}" for d in dokumanlar)
    except Exception as e:
        return f"[Hafıza]: Arama hatasi: {e}"


def hafiza_ozeti_al(collection, adet: int = 5) -> str:
    """Son N tecrübenin ozetini dondur (oturum basinda baglam icin)."""
    try:
        peek = collection.peek(limit=adet)
        docs = peek.get("documents", [])
        if not docs:
            return ""
        return "Son tecrübeler:\n" + "\n".join(f"- {d[:120]}" for d in docs)
    except Exception:
        return ""


def basarili_tecrube_kaydet(collection, hedef: str, ozet: str):
    """Basarili gorev tecrübesini kaydet (kullanim kolayligi)."""
    kayit_id = f"basarili-{abs(hash(hedef)) % 100000}"
    tecrube_kaydet(collection, kayit_id, f"[BASARILI] {hedef[:80]}: {ozet[:120]}",
                   {"tur": "basarili", "hedef": hedef[:80]})


def basarisiz_tecrube_kaydet(collection, hedef: str, hata: str):
    """Basarisiz gorev tecrübesini kaydet."""
    kayit_id = f"hata-{abs(hash(hedef + hata)) % 100000}"
    tecrube_kaydet(collection, kayit_id, f"[HATA] {hedef[:80]}: {hata[:120]}",
                   {"tur": "hata", "hedef": hedef[:80]})


class VektorelHafiza:
    """ChromaDB tabanli vektorel hafiza sinifi (Counter-TF-IDF yedekli).

    chromadb varsa ChromaDB PersistentCollection, yoksa Counter tabanli
    TF-IDF benzeri bellek kullanir. Ek paket gerektirmez (stdlib-only).
    """

    def __init__(self, yol="./vektor_hafizasi"):
        self._yol = yol
        self._collection = vektorel_hafiza_sistemini_kur(yol)
        self._embedder = None

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def chromadb_available(self):
        """ChromaDB kullanilabilir mi?"""
        return CHROMA_AVAILABLE

    @property
    def embedder(self):
        """Basit embedder (None — std11 surumde gomme yok)."""
        return self._embedder

    @property
    def collection(self):
        """Alttaki koleksiyon nesnesi (_BasitYedek veya ChromaDB koleksiyonu)."""
        return self._collection

    # ── CRUD ─────────────────────────────────────────────────────────────

    def ekle(self, text: str, metadata: dict = None) -> bool:
        """Metin ve metadata ekle / guncelle.

        Args:
            text: Kaydedilecek metin.
            metadata: Opsiyonel metadata sozlugu.

        Returns:
            Basariliysa True, dedup veya hata durumunda False.
        """
        kayit_id = (
            f"vh_{abs(hash(text)) % 1000000}_"
            f"{int(time.time() * 1000)}"
        )
        return tecrube_kaydet(self._collection, kayit_id, text, metadata)

    def ara(self, query: str, limit: int = 3) -> dict:
        """Anlamsal arama yap.

        Args:
            query: Arama sorgusu.
            limit: Kac sonuc donecegi.

        Returns:
            {
                "success": bool,
                "results": [
                    {"id": str, "text": str, "metadata": dict, "score": float},
                    ...
                ],
                "message": str  # Hata veya bilgi mesaji
            }
        """
        try:
            sonuc = self._collection.query(
                query_texts=[query[:300]],
                n_results=limit,
            )
            dokumanlar = sonuc.get("documents", [[]])[0]
            metadatalar = sonuc.get("metadatas", [[]])[0]
            idler = sonuc.get("ids", [[]])[0]
            mesafeler = sonuc.get("distances", [[]])[0]

            if not dokumanlar:
                return {
                    "success": False,
                    "results": [],
                    "message": "[Hafiza]: Ilgili tecrube bulunamadi.",
                }

            results = []
            for i, doc in enumerate(dokumanlar):
                score = 1 - mesafeler[i] if i < len(mesafeler) else 0.0
                results.append({
                    "id": idler[i] if i < len(idler) else "",
                    "text": doc,
                    "metadata": metadatalar[i] if i < len(metadatalar) else {},
                    "score": round(score, 4),
                })

            # Skora gore sirala (yuksek skor once)
            results.sort(key=lambda x: x["score"], reverse=True)

            return {"success": True, "results": results, "message": ""}

        except Exception as e:
            return {
                "success": False,
                "results": [],
                "message": f"[Hafiza]: Arama hatasi: {e}",
            }

    def sil(self, id: str) -> bool:
        """ID ile kayit sil.

        Args:
            id: Silinecek kaydin ID'si.

        Returns:
            Basariliysa True.
        """
        try:
            if hasattr(self._collection, "delete"):
                self._collection.delete(ids=[id])
                return True
            return False
        except Exception:
            return False

    def __len__(self):
        """Koleksiyondaki kayit sayisi."""
        try:
            return self._collection.count()
        except Exception:
            return 0

    def __repr__(self):
        return (
            f"<VektorelHafiza chromadb={CHROMA_AVAILABLE} "
            f"kayit={len(self)}>"
        )


if __name__ == "__main__":
    # Test: VektorelHafiza sinifi ile
    vh = VektorelHafiza()
    vh.ekle("dosya olustur", {"tur": "test"})
    vh.ekle("web arama", {"tur": "test"})
    print(vh.ara("dosya islemi", limit=2))
    print(f"Kayit sayisi: {len(vh)}")
    print(vh)
