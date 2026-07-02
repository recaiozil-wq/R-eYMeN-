# -*- coding: utf-8 -*-
"""
semantic_cache.py — Anlamsal LLM Onbellek.

Ayni veya cok benzer promptlara verilen LLM yanitlarini saklar.
ChromaDB varsa vektörel benzerlik, yoksa SHA-256 karma ile eslesme yapar.

Kullanim::

    cache = SemanticCache(esik=0.92)
    hit = cache.ara(sistem_prompt, mesajlar)
    if hit:
        return hit
    yanit = llm.uret(...)
    cache.kaydet(sistem_prompt, mesajlar, yanit)
"""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional
import logging
logger = logging.getLogger(__name__)

# ChromaDB varsa vektörel, yoksa hash tabanlı çalışır
try:
    import chromadb
    _CHROMA_VAR = True
except ImportError:
    _CHROMA_VAR = False

# Gömme (embedding) için SentenceTransformers opsiyonel
try:
    from sentence_transformers import SentenceTransformer
    _EMBED_VAR = True
except ImportError:
    _EMBED_VAR = False


class SemanticCache:
    """Anlamsal LLM onbellek.

    Yakin anlam tasıyan promptlara once onbellekten yanit verir.
    ChromaDB + SentenceTransformers varsa kosinus benzerligi hesaplar,
    yoksa SHA-256 karma ile tam eslesme yapar.
    """

    def __init__(self,
                 esik: float = 0.90,
                 maks_kayit: int = 500,
                 gecerlilik_sn: int = 3600,
                 cache_dizin: str = ".ReYMeN/semantic_cache"):
        """
        Args:
            esik:           Benzerlik esigi (0-1). Bu deger asildiysa onbellekten don.
            maks_kayit:     Tutulacak maksimum onbellek kaydi.
            gecerlilik_sn:  Kayitlarin gecerlilik suresi (saniye). 0=sinirsiz.
            cache_dizin:    Hash-tabanli cache icin dosya dizini.
        """
        self.esik = esik
        self.maks_kayit = maks_kayit
        self.gecerlilik_sn = gecerlilik_sn
        self._cache_dizin = Path(cache_dizin)
        self._hash_cache: dict = {}       # {hash: (yanit, zaman)}
        self._hit_sayisi = 0
        self._miss_sayisi = 0

        # ChromaDB koleksiyonu
        self._chroma = None
        self._embed_fn = None
        if _CHROMA_VAR and _EMBED_VAR:
            try:
                self._cache_dizin.mkdir(parents=True, exist_ok=True)
                client = chromadb.PersistentClient(path=str(self._cache_dizin / "chroma"))
                self._chroma = client.get_or_create_collection(
                    name="semantic_cache",
                    metadata={"hnsw:space": "cosine"},
                )
                self._embed_fn = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception:
                self._chroma = None

        # Basit hash-cache dizini
        if not self._chroma:
            self._cache_dizin.mkdir(parents=True, exist_ok=True)

    # ── Onbellek anahtari ──────────────────────────────────────────────────────

    @staticmethod
    def _anahtar(sistem_prompt: str, mesajlar: list) -> str:
        """SHA-256 tabanlı deterministik anahtar."""
        ham = json.dumps(
            {"sp": sistem_prompt[:500], "msgs": [m.get("content", "")[:200] for m in mesajlar[-4:]]},
            ensure_ascii=False, sort_keys=True,
        )
        return hashlib.sha256(ham.encode("utf-8")).hexdigest()[:32]

    @staticmethod
    def _metin_birlestir(sistem_prompt: str, mesajlar: list) -> str:
        """Embed edilecek birlesik metin."""
        parca = sistem_prompt[:300]
        for m in mesajlar[-3:]:
            parca += " " + m.get("content", "")[:150]
        return parca.strip()

    # ── Arama ─────────────────────────────────────────────────────────────────

    def ara(self, sistem_prompt: str, mesajlar: list) -> Optional[str]:
        """Onbellekte eslesme ara.

        Returns:
            Bulunan yanit metni veya None (miss).
        """
        if self._chroma and self._embed_fn:
            return self._chroma_ara(sistem_prompt, mesajlar)
        return self._hash_ara(sistem_prompt, mesajlar)

    def _hash_ara(self, sistem_prompt: str, mesajlar: list) -> Optional[str]:
        anahtar = self._anahtar(sistem_prompt, mesajlar)
        kayit = self._hash_cache.get(anahtar)
        if kayit is None:
            # Dosyadan dene
            dosya = self._cache_dizin / f"{anahtar}.json"
            if dosya.exists():
                try:
                    kayit = json.loads(dosya.read_text("utf-8"))
                    self._hash_cache[anahtar] = kayit
                except Exception as _semantic_e127:
                    print(f"[UYARI] semantic_cache.py:128 - {_semantic_e127}")

        if kayit:
            yanit, zaman = kayit
            if self.gecerlilik_sn == 0 or (time.time() - zaman) < self.gecerlilik_sn:
                self._hit_sayisi += 1
                return yanit

        self._miss_sayisi += 1
        return None

    def _chroma_ara(self, sistem_prompt: str, mesajlar: list) -> Optional[str]:
        try:
            metin = self._metin_birlestir(sistem_prompt, mesajlar)
            vektor = self._embed_fn.encode([metin]).tolist()
            sonuclar = self._chroma.query(
                query_embeddings=vektor, n_results=1,
                include=["documents", "distances", "metadatas"],
            )
            if not sonuclar["ids"][0]:
                self._miss_sayisi += 1
                return None

            mesafe = sonuclar["distances"][0][0]
            # Cosine distance: 0=ayni, 2=tamamen farkli. Benzerlik = 1 - mesafe/2
            benzerlik = 1 - mesafe / 2
            if benzerlik >= self.esik:
                meta = sonuclar["metadatas"][0][0]
                # Gecerlilik kontrolu
                zaman = float(meta.get("zaman", 0))
                if self.gecerlilik_sn == 0 or (time.time() - zaman) < self.gecerlilik_sn:
                    self._hit_sayisi += 1
                    return sonuclar["documents"][0][0]

            self._miss_sayisi += 1
            return None
        except Exception:
            return self._hash_ara(sistem_prompt, mesajlar)

    # ── Kaydetme ──────────────────────────────────────────────────────────────

    def kaydet(self, sistem_prompt: str, mesajlar: list, yanit: str):
        """LLM yanitini onbelleğe kaydet."""
        if self._chroma and self._embed_fn:
            self._chroma_kaydet(sistem_prompt, mesajlar, yanit)
        else:
            self._hash_kaydet(sistem_prompt, mesajlar, yanit)

    def _hash_kaydet(self, sistem_prompt: str, mesajlar: list, yanit: str):
        anahtar = self._anahtar(sistem_prompt, mesajlar)
        kayit = (yanit, time.time())
        self._hash_cache[anahtar] = kayit
        try:
            dosya = self._cache_dizin / f"{anahtar}.json"
            dosya.write_text(json.dumps(list(kayit), ensure_ascii=False), "utf-8")
        except Exception as _semantic_e183:
            print(f"[UYARI] semantic_cache.py:184 - {_semantic_e183}")
        # Kapasite temizligi
        if len(self._hash_cache) > self.maks_kayit:
            silmek = list(self._hash_cache.keys())[:len(self._hash_cache) - self.maks_kayit]
            for k in silmek:
                del self._hash_cache[k]
                try:
                    (self._cache_dizin / f"{k}.json").unlink(missing_ok=True)
                except Exception as _semantic_e192:
                    print(f"[UYARI] semantic_cache.py:193 - {_semantic_e192}")

    def _chroma_kaydet(self, sistem_prompt: str, mesajlar: list, yanit: str):
        try:
            anahtar = self._anahtar(sistem_prompt, mesajlar)
            metin = self._metin_birlestir(sistem_prompt, mesajlar)
            vektor = self._embed_fn.encode([metin]).tolist()
            self._chroma.upsert(
                ids=[anahtar],
                documents=[yanit],
                embeddings=vektor,
                metadatas=[{"zaman": str(time.time()), "prompt_ozet": metin[:100]}],
            )
        except Exception:
            self._hash_kaydet(sistem_prompt, mesajlar, yanit)

    # ── İstatistik ────────────────────────────────────────────────────────────

    def istatistik(self) -> dict:
        """Onbellek hit/miss istatistikleri."""
        toplam = self._hit_sayisi + self._miss_sayisi
        oran = self._hit_sayisi / toplam if toplam else 0
        return {
            "hit": self._hit_sayisi,
            "miss": self._miss_sayisi,
            "oran": round(oran, 3),
            "mod": "chroma+embed" if (self._chroma and self._embed_fn) else "hash",
            "kayit_sayisi": len(self._hash_cache),
        }

    def temizle(self):
        """Tüm onbellek kayitlarini sil."""
        self._hash_cache.clear()
        try:
            for dosya in self._cache_dizin.glob("*.json"):
                dosya.unlink(missing_ok=True)
        except Exception as _semantic_e229:
            print(f"[UYARI] semantic_cache.py:230 - {_semantic_e229}")
        if self._chroma:
            try:
                self._chroma.delete(where={"zaman": {"$gt": "0"}})
            except Exception as _semantic_e234:
                print(f"[UYARI] semantic_cache.py:235 - {_semantic_e234}")


# ── Tekil ornek (singleton) ──────────────────────────────────────────────────

_GLOBAL_CACHE: Optional[SemanticCache] = None


def global_cache_al() -> SemanticCache:
    """Uygulama genelinde paylasilan SemanticCache ornegini dondur."""
    global _GLOBAL_CACHE
    if _GLOBAL_CACHE is None:
        _GLOBAL_CACHE = SemanticCache()
    return _GLOBAL_CACHE


# ── Test blogu ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cache = SemanticCache(gecerlilik_sn=60)
    sp = "Sen bir asistan ajanissin."
    msgs = [{"role": "user", "content": "Python'da liste nasil olusturulur?"}]

    print("1. Ara (miss bekleniyor):", cache.ara(sp, msgs))
    cache.kaydet(sp, msgs, "Liste = [] ile olusturulur.")
    print("2. Ara (hit bekleniyor):", cache.ara(sp, msgs))
    print("3. Istatistik:", cache.istatistik())
