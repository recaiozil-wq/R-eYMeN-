# -*- coding: utf-8 -*-
"""
vector_memory.py — P2 Vector Memory: Embedding + semantic search.

Vektor bellek sistemi. Mevcut VektorBellek (reymen/hafiza/vektor_bellek.py)
üzerine kurulmuştur. DeepSeek embeddings API ile embedding üretir,
ChromaDB (varsa) veya SQLite fallback kullanır.

Motor Tools:
    VEKTOR_EKLE(metin, metadata) → Kayıt ekle
    VEKTOR_ARA(sorgu, limit)     → Anlamsal arama
"""

from __future__ import annotations

import json
import logging
import hashlib
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Mevcut VektorBellek'i kullan ──────────────────────────────────────────────
try:
    from reymen.hafiza.vektor_bellek import (
        VektorBellek as _VektorBellek,
        vektor_bellek_al as _varsayilan_vb_al,
        CHROMA_MEVCUT,
    )
    VARSAYILAN_VB_MEVCUT = True
except ImportError:
    _VektorBellek = None  # type: ignore
    _varsayilan_vb_al = None  # type: ignore
    CHROMA_MEVCUT = False
    VARSAYILAN_VB_MEVCUT = False

# ── DeepSeek embeddings API (opsiyonel) ───────────────────────────────────────
try:
    from openai import OpenAI
    _OPENAI_MEVCUT = True
except ImportError:
    _OPENAI_MEVCUT = False

# ── numpy (opsiyonel, embedding islemleri icin) ────────────────────────────────
try:
    import numpy as np
    _NUMPY_MEVCUT = True
except ImportError:
    _NUMPY_MEVCUT = False

# ── Varsayilan sabitler ────────────────────────────────────────────────────────
VARSAYILAN_MODEL = "text-embedding-ada-002"  # DeepSeek / OpenAI uyumlu
VARSAYILAN_DIZIN = str(Path(__file__).parent.parent.parent / "vektor_hafizasi")
ESIK_BENZERLIK = 0.15
MAKS_EMBEDDING_BOYUT = 2048
EMBEDDING_BATCH_SIZE = 10


# ═══════════════════════════════════════════════════════════════════════════════
#  Embedding Motoru (LLM / DeepSeek API)
# ═══════════════════════════════════════════════════════════════════════════════


class EmbeddingMotor:
    """LLM (DeepSeek / OpenAI) embeddings API ile vektor uretimi.

    Strateji:
        1. OpenAI uyumlu API (DeepSeek embeddings)
        2. sentence-transformers (opsiyonel)
        3. Basit hash tabanli gomme (fallback)
    """

    def __init__(self, api_key: str = "", model: str = VARSAYILAN_MODEL, base_url: str = ""):
        self._model = model
        self._client = None
        self._fallback_aktif = False

        # 1. OpenAI uyumlu API
        if _OPENAI_MEVCUT:
            try:
                # DeepSeek base_url veya standart OpenAI
                actual_base = base_url or "https://api.deepseek.com/v1"
                actual_key = api_key or self._env_oku("DEEPSEEK_API_KEY") or self._env_oku("OPENAI_API_KEY")
                if actual_key:
                    self._client = OpenAI(api_key=actual_key, base_url=actual_base)
                    self._model = model
                    logger.info("[EmbeddingMotor] OpenAI uyumlu API hazir: %s", actual_base)
                else:
                    logger.warning("[EmbeddingMotor] API key bulunamadi, fallback kullanilacak")
                    self._fallback_aktif = True
            except Exception as e:
                logger.warning("[EmbeddingMotor] API kurulum hatasi: %s", e)
                self._fallback_aktif = True
        else:
            logger.info("[EmbeddingMotor] openai paketi yok, fallback kullanilacak")
            self._fallback_aktif = True

    def _env_oku(self, key: str) -> str:
        import os
        return os.getenv(key, "")

    def embed(self, metin: str) -> List[float]:
        """Tek metin icin embedding vektoru uret."""
        if not metin or not metin.strip():
            return []

        if self._client and not self._fallback_aktif:
            try:
                resp = self._client.embeddings.create(
                    model=self._model,
                    input=metin[:MAKS_EMBEDDING_BOYUT],
                )
                return resp.data[0].embedding if resp.data else []
            except Exception as e:
                logger.warning("[EmbeddingMotor] API embedding hatasi: %s — fallback", e)
                self._fallback_aktif = True

        # Fallback: hash tabanli gomme
        return self._hash_embed(metin)

    def embed_batch(self, metinler: List[str]) -> List[List[float]]:
        """Toplu embedding."""
        if not metinler:
            return []

        if self._client and not self._fallback_aktif:
            try:
                # Batch halinde gonder
                trimmed = [m[:MAKS_EMBEDDING_BOYUT] for m in metinler]
                resp = self._client.embeddings.create(model=self._model, input=trimmed)
                return [d.embedding for d in resp.data] if resp.data else []
            except Exception as e:
                logger.warning("[EmbeddingMotor] Batch embedding hatasi: %s — fallback", e)
                self._fallback_aktif = True

        return [self._hash_embed(m) for m in metinler]

    def _hash_embed(self, metin: str) -> List[float]:
        """Basit hash tabanli gomme (fallback)."""
        h = hashlib.sha256(metin.encode("utf-8")).digest()
        return [b / 255.0 for b in h[:32]]  # 32 boyutlu gomme

    def boyut(self) -> int:
        """Embedding vektor boyutu."""
        return 32 if self._fallback_aktif else 1536  # ada-002 = 1536, fallback = 32

    @property
    def hazir(self) -> bool:
        return not self._fallback_aktif or self._client is not None


# ═══════════════════════════════════════════════════════════════════════════════
#  VectorMemory Ana Sinif (Mevcut VektorBellek'i sarmalar)
# ═══════════════════════════════════════════════════════════════════════════════


class VectorMemory:
    """P2 Vector Memory: embedding tabanli anlamsal bellek.

    Mevcut VektorBellek (ChromaDB / SQLite) uzerine kuruludur.
    DeepSeek embeddings API ile embedding uretir.

    Kullanim:
        vm = VectorMemory()
        vm.ekle("Bugun hava cok guzel", {"kategori": "not"})
        sonuclar = vm.ara("hava durumu", limit=3)
        vm.sil("id123")
        vm.guncelle("id123", "Yeni metin")
    """

    def __init__(
        self,
        koleksiyon_adi: str = "ReYMeN_vektor_bellek",
        kalici_dizin: str = "",
        embedding_model: str = VARSAYILAN_MODEL,
        embedding_api_key: str = "",
        embedding_base_url: str = "",
    ):
        self._koleksiyon_adi = koleksiyon_adi
        self._kalici_dizin = kalici_dizin or VARSAYILAN_DIZIN

        # Embedding motoru
        self._embedder = EmbeddingMotor(
            api_key=embedding_api_key,
            model=embedding_model,
            base_url=embedding_base_url,
        )

        # Mevcut VektorBellek (varsa)
        self._vb = None
        if VARSAYILAN_VB_MEVCUT and _VektorBellek is not None:
            try:
                self._vb = _VektorBellek(
                    koleksiyon_adi=koleksiyon_adi,
                    kalici_dizin=self._kalici_dizin,
                )
                logger.info("[VectorMemory] VektorBellek baslatildi: %s", koleksiyon_adi)
            except Exception as e:
                logger.warning("[VectorMemory] VektorBellek baslatma hatasi: %s — SQLite fallback", e)
                self._vb = None

        # SQLite fallback (her zaman hazir)
        self._sqlite = _SQLiteVectorMemory(kalici_dizin=self._kalici_dizin)

    # ── Temel Metotlar ───────────────────────────────────────────────────────

    def ekle(self, metin: str, metadata: Optional[Dict] = None) -> str:
        """Metni vektor bellege ekle.

        Args:
            metin: Eklenecek metin
            metadata: Opsiyonel metadata dict

        Returns:
            Kayit ID
        """
        if not metin or not metin.strip():
            logger.warning("[VectorMemory] Bos metin eklenemez")
            return ""

        # Embedding uret
        embedding = self._embedder.embed(metin)

        # Oncelik: mevcut VektorBellek (ChromaDB)
        if self._vb is not None:
            kid = self._vb.ekle(metin, metadata)
            if kid:
                # Embedding'i de SQLite'e kaydet (yedek)
                self._sqlite.ekle(metin, metadata, embedding)
                return kid

        # Fallback: SQLite
        return self._sqlite.ekle(metin, metadata, embedding)

    def ara(self, sorgu: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Anlamsal arama yap.

        Args:
            sorgu: Arama sorgusu
            limit: Kac sonuc donsun

        Returns:
            [{"id": ..., "metin": ..., "skor": ..., "metadata": ...}, ...]
        """
        if not sorgu or not sorgu.strip():
            return []

        try:
            # Oncelik: VektorBellek (ChromaDB) ile ara
            if self._vb is not None:
                chroma_sonuc = self._vb.ara(sorgu, k=limit)
                if chroma_sonuc:
                    return [
                        {
                            "id": sid,
                            "metin": metin,
                            "skor": round(skor, 4),
                            "metadata": meta,
                        }
                        for sid, metin, skor, meta in chroma_sonuc
                    ]
        except Exception as e:
            logger.debug("[VectorMemory] ChromaDB arama hatasi: %s — SQLite", e)

        # Fallback: SQLite + embedding benzerligi
        sorgu_embed = self._embedder.embed(sorgu)
        return self._sqlite.ara(sorgu_embed, sorgu, limit=limit)

    def sil(self, kayit_id: str) -> bool:
        """Belirtilen ID'ye sahip kaydi sil."""
        if not kayit_id:
            return False

        basarili = False
        if self._vb is not None:
            try:
                basarili = self._vb.sil(kayit_id) or basarili
            except Exception:
                pass

        return self._sqlite.sil(kayit_id) or basarili

    def guncelle(self, kayit_id: str, yeni_metin: str, yeni_metadata: Optional[Dict] = None) -> bool:
        """Varolan kaydi guncelle (sil + yeniden ekle).

        Args:
            kayit_id: Guncellenecek kayit ID
            yeni_metin: Yeni metin
            yeni_metadata: Opsiyonel yeni metadata

        Returns:
            Basarili mi?
        """
        if not kayit_id or not yeni_metin:
            return False

        # Sil
        self.sil(kayit_id)

        # Yeniden ekle (yeni ID ile)
        yeni_id = self.ekle(yeni_metin, yeni_metadata)
        return bool(yeni_id)

    def listele(self, limit: int = 100) -> List[Dict]:
        """Tum kayitlari listele."""
        if self._vb is not None:
            try:
                return self._vb.listele(limit=limit)
            except Exception:
                pass
        return self._sqlite.listele(limit=limit)

    def __len__(self) -> int:
        if self._vb is not None:
            try:
                return len(self._vb)
            except Exception:
                pass
        return len(self._sqlite)

    def bilgi(self) -> Dict:
        """VectorMemory hakkinda bilgi."""
        return {
            "koleksiyon": self._koleksiyon_adi,
            "backend": "chromadb" if (self._vb and hasattr(self._vb, '_koleksiyon') and self._vb._koleksiyon) else "sqlite",
            "embedding": {
                "model": self._embedder._model,
                "api_hazir": self._embedder.hazir,
                "boyut": self._embedder.boyut(),
            },
            "kayit_sayisi": len(self),
            "dizin": self._kalici_dizin,
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  SQLite Vector Memory (Embedding destekli fallback)
# ═══════════════════════════════════════════════════════════════════════════════


class _SQLiteVectorMemory:
    """SQLite tabanli vektor bellek (gercek embedding destegi ile).

    ChromaDB yoksa kullanilir. Embedding vektorlerini JSON olarak saklar.
    """

    def __init__(self, kalici_dizin: str = ""):
        import sqlite3

        self._db_path = Path(kalici_dizin or VARSAYILAN_DIZIN) / "vector_memory.db"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vector_memory (
                id TEXT PRIMARY KEY,
                metin TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                embedding TEXT DEFAULT '[]',
                zaman REAL NOT NULL
            )
            """
        )
        # FTS5 index (keyword search icin)
        try:
            self._conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS vector_memory_fts USING fts5(id, metin)"
            )
        except Exception:
            pass
        self._conn.commit()

    def ekle(self, metin: str, metadata: Optional[Dict] = None, embedding: Optional[List[float]] = None) -> str:
        """Metni kaydet."""
        kayit_id = hashlib.sha256(metin.encode("utf-8")).hexdigest()[:16]
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)
        embed_json = json.dumps(embedding or [], ensure_ascii=False)

        try:
            self._conn.execute(
                "INSERT OR REPLACE INTO vector_memory (id, metin, metadata, embedding, zaman) VALUES (?, ?, ?, ?, ?)",
                (kayit_id, metin, meta_json, embed_json, time.time()),
            )
            # FTS5 guncelle
            try:
                self._conn.execute(
                    "INSERT OR REPLACE INTO vector_memory_fts (id, metin) VALUES (?, ?)",
                    (kayit_id, metin),
                )
            except Exception:
                pass
            self._conn.commit()
        except Exception as e:
            logger.warning("[SQLiteVectorMemory] Ekleme hatasi: %s", e)
        return kayit_id

    def ara(self, sorgu_embed: List[float], sorgu_metin: str = "", limit: int = 5) -> List[Dict]:
        """Cosine benzerligi ile ara (embedding varsa) veya FTS5 keyword ara."""
        if not sorgu_embed and not sorgu_metin:
            return []

        sonuclar = []

        if sorgu_embed and _NUMPY_MEVCUT:
            # Cosine similarity ile ara
            cursor = self._conn.execute(
                "SELECT id, metin, metadata, embedding, zaman FROM vector_memory ORDER BY zaman DESC LIMIT 2000"
            )
            sorgu_np = np.array(sorgu_embed, dtype=np.float32)
            sorgu_norm = np.linalg.norm(sorgu_np)
            if sorgu_norm == 0:
                return []

            for row in cursor.fetchall():
                try:
                    embed_list = json.loads(row[3])
                    if not embed_list:
                        continue
                    doc_np = np.array(embed_list, dtype=np.float32)
                    doc_norm = np.linalg.norm(doc_np)
                    if doc_norm == 0:
                        continue
                    cos_benzerlik = float(np.dot(sorgu_np, doc_np) / (sorgu_norm * doc_norm))
                    if cos_benzerlik >= ESIK_BENZERLIK:
                        try:
                            meta = json.loads(row[2])
                        except (json.JSONDecodeError, TypeError):
                            meta = {}
                        sonuclar.append({
                            "id": row[0],
                            "metin": row[1],
                            "skor": round(cos_benzerlik, 4),
                            "metadata": meta,
                        })
                except Exception:
                    continue

            sonuclar.sort(key=lambda x: x["skor"], reverse=True)
            return sonuclar[:limit]

        # FTS5 keyword fallback
        if sorgu_metin:
            try:
                fts_sorgu = " OR ".join(sorgu_metin.split()[:10])
                cursor = self._conn.execute(
                    "SELECT vm.id, vm.metin, vm.metadata, vm.zaman "
                    "FROM vector_memory_fts fts "
                    "JOIN vector_memory vm ON fts.id = vm.id "
                    "WHERE vector_memory_fts MATCH ? "
                    "ORDER BY rank LIMIT ?",
                    (fts_sorgu, limit),
                )
                for row in cursor.fetchall():
                    try:
                        meta = json.loads(row[2])
                    except (json.JSONDecodeError, TypeError):
                        meta = {}
                    sonuclar.append({
                        "id": row[0],
                        "metin": row[1],
                        "skor": 0.5,
                        "metadata": meta,
                    })
            except Exception:
                pass

        return sonuclar[:limit]

    def sil(self, kayit_id: str) -> bool:
        try:
            self._conn.execute("DELETE FROM vector_memory WHERE id = ?", (kayit_id,))
            try:
                self._conn.execute("DELETE FROM vector_memory_fts WHERE id = ?", (kayit_id,))
            except Exception:
                pass
            self._conn.commit()
            return True
        except Exception as e:
            logger.warning("[SQLiteVectorMemory] Silme hatasi: %s", e)
            return False

    def listele(self, limit: int = 100) -> List[Dict]:
        cursor = self._conn.execute(
            "SELECT id, metin, metadata, zaman FROM vector_memory ORDER BY zaman DESC LIMIT ?",
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
            cursor = self._conn.execute("SELECT COUNT(*) FROM vector_memory")
            return cursor.fetchone()[0] or 0
        except Exception:
            return 0

    def kapat(self):
        try:
            self._conn.close()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
#  Singleton
# ═══════════════════════════════════════════════════════════════════════════════

_vector_memory_instance: Optional[VectorMemory] = None


def vector_memory_al() -> VectorMemory:
    """Varsayilan VectorMemory singleton'ini al."""
    global _vector_memory_instance
    if _vector_memory_instance is None:
        _vector_memory_instance = VectorMemory()
    return _vector_memory_instance


# ═══════════════════════════════════════════════════════════════════════════════
#  Motor Tools
# ═══════════════════════════════════════════════════════════════════════════════


def motor_kaydet(motor) -> None:
    """Motor'a vektor bellek araclarini kaydeder.

    Kaydettigi araclar:
        - VEKTOR_EKLE: Metni vektor bellege ekle
        - VEKTOR_ARA: Anlamsal arama yap
    """
    vm = vector_memory_al()

    motor._plugin_arac_kaydet(
        "VEKTOR_EKLE",
        _vektor_ekle_tool,
        "VEKTOR_EKLE(metin, metadata) — Metni vektor bellege ekle. "
        "Parametreler: metin=eklenecek_metin metadata=opsiyonel_json_dict. "
        "Ornek: VEKTOR_EKLE(metin='Bugun hava cok guzel', metadata={\"kategori\":\"not\"})"
    )
    motor._plugin_arac_kaydet(
        "VEKTOR_ARA",
        _vektor_ara_tool,
        "VEKTOR_ARA(sorgu, limit) — Anlamsal arama yap. "
        "Parametreler: sorgu=arama_sorgusu limit=kac_sonuc (varsayilan 5). "
        "Ornek: VEKTOR_ARA(sorgu='hava durumu', limit=3)"
    )
    logger.info("[VectorMemory] Motor'a 2 arac kaydedildi (VEKTOR_EKLE, VEKTOR_ARA)")


def _vektor_ekle_tool(**kw) -> str:
    """VEKTOR_EKLE aracı."""
    args = kw.get("args", [])
    metin = args[0] if args else kw.get("metin", "")
    metadata = args[1] if len(args) > 1 else kw.get("metadata", None)

    if not metin:
        return "[HATA] VEKTOR_EKLE: metin parametresi zorunlu"

    vm = vector_memory_al()
    kid = vm.ekle(metin, metadata)

    if kid:
        return f"[OK] Kayit eklendi: {kid}"
    return "[HATA] Kayit eklenemedi"


def _vektor_ara_tool(**kw) -> str:
    """VEKTOR_ARA aracı."""
    args = kw.get("args", [])
    sorgu = args[0] if args else kw.get("sorgu", "")
    limit = int(args[1]) if len(args) > 1 else int(kw.get("limit", 5))

    if not sorgu:
        return "[HATA] VEKTOR_ARA: sorgu parametresi zorunlu"

    vm = vector_memory_al()
    sonuclar = vm.ara(sorgu, limit=limit)

    if not sonuclar:
        return "[Bilgi] Sonuc bulunamadi"

    satirlar = [
        f"[{i+1}] skor={r['skor']:.4f} | {r['metin'][:120]}"
        for i, r in enumerate(sonuclar)
    ]
    return "\n".join(satirlar)


# ═══════════════════════════════════════════════════════════════════════════════
#  Test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== VectorMemory Test ===")

    vm = VectorMemory()
    print(f"Bilgi: {vm.bilgi()}")

    # Ekle
    id1 = vm.ekle("ReYMeN projesi ChromaDB ile calisir", {"kategori": "teknik"})
    id2 = vm.ekle("Kullanici kisa cevaplari sever", {"kategori": "kullanici"})
    id3 = vm.ekle("Python dilinde yazilmis bir ajan sistemi", {"kategori": "teknik"})
    print(f"Eklenen ID'ler: {id1}, {id2}, {id3}")

    # Ara
    sonuclar = vm.ara("ChromaDB hakkinda bilgi", limit=3)
    print(f"\nArama sonuclari ({len(sonuclar)}):")
    for r in sonuclar:
        print(f"  [{r['skor']:.4f}] {r['metin'][:80]} | meta: {r['metadata']}")

    # Guncelle
    if id1:
        vm.guncelle(id1, "ReYMeN projesi ChromaDB + SQLite ile calisir")
        print(f"\nGuncellendi: {id1}")

    # Listele
    print(f"\nTum kayitlar ({len(vm)}):")
    for kayit in vm.listele():
        print(f"  {kayit['id']}: {kayit['metin'][:60]}")

    print("\n✓ Test tamamlandi")
