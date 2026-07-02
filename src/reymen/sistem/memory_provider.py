# -*- coding: utf-8 -*-
"""
memory_provider.py — Plugin tabanli bellek saglayici sistemi.

Iki katman:
  1. MemoryProvider (ABC) + MemoryProviderRegistry
     Depolama backend'leri icin interface: JsonBackend, SQLiteBackend, ChromaBackend.
     Yeni backend eklemek icin @MemoryProviderRegistry.register dekoratorunu kullan.

  2. AbstraktHafizaSaglayici + HafizaPluginKayit
     ReYMeN Memory Provider Plugin arayuzu (lifecycle kancalari).
     Plugin'ler plugins/memory/<ad>/__init__.py icinde bu sinifi miras alir.

Kullanim:
    # Dogrudan:
    backend = JsonBackend(dosya_yolu=".ReYMeN/memory.json")
    backend.initialize(session_id="abc123")
    backend.save("notlar", {"baslik": "test", "icerik": "deneme"})

    # Registry ile:
    provider_cls = MemoryProviderRegistry.get("sqlite")
    backend = provider_cls(db_yolu=".ReYMeN/memory.db")
    backend.initialize(session_id="abc123")

    # Mevcut provider'lari listele:
    MemoryProviderRegistry.list_available()  # -> ["json", "sqlite"]
"""

import os
import json
import time
import logging
import threading
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# sqlite3 guvenli import (standart kutuphanede olsa da)
try:
    import sqlite3
    _SQLITE_AVAILABLE = True
except ImportError:
    _SQLITE_AVAILABLE = False

# chromadb guvenli import
try:
    import chromadb
    _CHROMA_AVAILABLE = True
except ImportError:
    _CHROMA_AVAILABLE = False


# =====================================================================
# KATMAN 1: DEPOLAMA BACKEND ARAYUZU
# =====================================================================

class MemoryProvider(ABC):
    """Tum depolama backend'leri icin temel sinif.

    Yeni bir backend olusturmak icin bu sinifi genisletin ve
    @MemoryProviderRegistry.register dekoratorunu kullanin.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider kisa adi (ornek: 'json', 'sqlite', 'chroma')."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Provider aktiflesebilir mi? Ag cagrisi yapma, sadece import/config kontrol et."""
        ...

    @abstractmethod
    def initialize(self, session_id: str, **kwargs) -> None:
        """Ajan baslarken bir kez cagirilir.

        kwargs her zaman icermelidir:
          hermes_home (str): Aktif REYMEN_HOME dizin yolu — depolama icin kullan.
        """
        ...

    @abstractmethod
    def save(self, collection: str, document: dict, **kwargs) -> str:
        """Bir dokumani kaydet. Dondurulen: dokuman ID."""
        ...

    @abstractmethod
    def search(self, collection: str, query: str, limit: int = 5) -> List[dict]:
        """Anlamsal veya metin tabanli arama yap."""
        ...

    @abstractmethod
    def get(self, collection: str, doc_id: str) -> Optional[dict]:
        """ID ile tek dokuman getir. Bulunamazsa None dondur."""
        ...

    @abstractmethod
    def delete(self, collection: str, doc_id: str) -> bool:
        """Dokumani sil. Basarili ise True dondur."""
        ...

    @abstractmethod
    def list_collections(self) -> List[str]:
        """Tum koleksiyon adlarini listele."""
        ...

    @abstractmethod
    def clear(self, collection: str) -> bool:
        """Koleksiyondaki tum dokumanlari sil."""
        ...

    @abstractmethod
    def stats(self) -> dict:
        """Provider istatistiklerini dondur (kayit sayisi, boyut, vs)."""
        ...


# =====================================================================
# PLUGIN KAYIT SISTEMI
# =====================================================================

class MemoryProviderRegistry:
    """Depolama backend'lerini kaydetmek ve secmek icin merkezi kayit defteri.

    Kullanim (dekorator ile):
        @MemoryProviderRegistry.register
        class BenimBackend(MemoryProvider):
            _provider_name = "benim"
            ...
    """

    _providers: Dict[str, type] = {}

    @classmethod
    def register(cls, provider_class: type) -> type:
        """Provider sinifini kaydet. Dekorator olarak kullanilir.

        Oncelik sirasi: sinif uzerindeki _provider_name attribute'u;
        yoksa provider_class().name ile anlık ornekleme.
        """
        try:
            name = getattr(provider_class, "_provider_name", None)
            if name is None:
                name = provider_class().name
            cls._providers[name] = provider_class
            logger.debug(f"MemoryProviderRegistry: '{name}' kayit edildi")
        except Exception as e:
            logger.warning(f"MemoryProviderRegistry: {provider_class.__name__} kayit basarisiz — {e}")
        return provider_class

    @classmethod
    def get(cls, name: str) -> Optional[type]:
        """Isme gore provider sinifini getir. Bulunamazsa None dondur."""
        return cls._providers.get(name)

    @classmethod
    def list_available(cls) -> List[str]:
        """Sadece is_available() == True olan provider'lari listele."""
        available = []
        for name, klass in cls._providers.items():
            try:
                check = getattr(klass, "_check_available", None)
                ok = check() if callable(check) else klass().is_available()
                if ok:
                    available.append(name)
            except Exception:
                logger.warning("[fix_01_sessiz_except] Exception")
        return available

    @classmethod
    def list_all(cls) -> List[str]:
        """Kayitli tum provider adlarini dondur (aktiflik farketmeksizin)."""
        return list(cls._providers.keys())


# =====================================================================
# JSON BACKEND
# =====================================================================

@MemoryProviderRegistry.register
class JsonBackend(MemoryProvider):
    """JSON dosya tabanli bellek backend'i. Her zaman kullanilabilir."""

    _provider_name = "json"

    def __init__(self, dosya_yolu: str = "memory_store.json"):
        self._dosya_yolu = dosya_yolu
        self._veri: Dict[str, List[Dict[str, Any]]] = {}
        self._session_id: Optional[str] = None
        self._istatistik: Dict[str, int] = {"kayit": 0, "sorgu": 0, "silme": 0}
        self._yukle()

    # --- MemoryProvider interface ---

    @property
    def name(self) -> str:
        return "json"

    def is_available(self) -> bool:
        return True

    @staticmethod
    def _check_available() -> bool:
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        """Oturumu baslatir; hermes_home verilirse dosya yolunu gunceller."""
        self._session_id = session_id
        hermes_home = kwargs.get("hermes_home")
        if hermes_home:
            yeni_yol = os.path.join(str(hermes_home), "memory.json")
            if yeni_yol != self._dosya_yolu:
                self._dosya_yolu = yeni_yol
                self._yukle()
        logger.info(f"JsonBackend baslatildi: session={session_id}, dosya={self._dosya_yolu}")

    def save(self, collection: str, document: dict, **kwargs) -> str:
        """Bir dokumani koleksiyona ekler. Dondurulen: dokuman ID."""
        try:
            dokuman = dict(document)
            dok_id = dokuman.get("id") or f"doc_{int(time.time() * 1000)}_{len(self._veri.get(collection, []))}"
            dokuman["id"] = dok_id
            dokuman.setdefault("zaman", time.time())

            if collection not in self._veri:
                self._veri[collection] = []
            self._veri[collection].append(dokuman)
            self._kaydet_dosya()
            self._istatistik["kayit"] += 1
            logger.info(f"JsonBackend.save: koleksiyon={collection}, id={dok_id}")
            return dok_id
        except Exception as e:
            logger.error(f"JsonBackend.save hatasi: {e}")
            return ""

    def search(self, collection: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Koleksiyonda metin sorgusu yapar. Bos sorgu tum kayitlari dondurur."""
        try:
            dokumanlar = self._veri.get(collection, [])
            if not query:
                sonuclar = dokumanlar[:limit]
            else:
                sorgu_lower = query.lower()
                sonuclar = []
                for doc in dokumanlar:
                    doc_str = json.dumps(doc, ensure_ascii=False).lower()
                    if sorgu_lower in doc_str:
                        sonuclar.append(doc)
                        if len(sonuclar) >= limit:
                            break
            self._istatistik["sorgu"] += 1
            return sonuclar
        except Exception as e:
            logger.error(f"JsonBackend.search hatasi: {e}")
            return []

    def get(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """ID ile dokuman getirir."""
        try:
            for doc in self._veri.get(collection, []):
                if doc.get("id") == doc_id:
                    return doc
            return None
        except Exception as e:
            logger.error(f"JsonBackend.get hatasi: {e}")
            return None

    def delete(self, collection: str, doc_id: str) -> bool:
        """Bir dokumani koleksiyondan siler."""
        try:
            if collection not in self._veri:
                return False
            onceki_boy = len(self._veri[collection])
            self._veri[collection] = [
                d for d in self._veri[collection] if d.get("id") != doc_id
            ]
            silindi = len(self._veri[collection]) < onceki_boy
            if silindi:
                self._kaydet_dosya()
                self._istatistik["silme"] += 1
                logger.info(f"JsonBackend.delete: koleksiyon={collection}, id={doc_id}")
            return silindi
        except Exception as e:
            logger.error(f"JsonBackend.delete hatasi: {e}")
            return False

    def list_collections(self) -> List[str]:
        """Mevcut koleksiyonlari listeler."""
        return list(self._veri.keys())

    def clear(self, collection: str) -> bool:
        """Koleksiyondaki tum dokumanlari siler."""
        try:
            if collection in self._veri:
                self._veri[collection] = []
                self._kaydet_dosya()
                return True
            return False
        except Exception as e:
            logger.error(f"JsonBackend.clear hatasi: {e}")
            return False

    def stats(self) -> dict:
        """Istatistik bilgilerini dondurur."""
        toplam = sum(len(v) for v in self._veri.values())
        return {
            "backend": "json",
            "koleksiyonlar": len(self._veri),
            "toplam_dokuman": toplam,
            "dosya": self._dosya_yolu,
            "kayit_sayisi": self._istatistik["kayit"],
            "sorgu_sayisi": self._istatistik["sorgu"],
            "silme_sayisi": self._istatistik["silme"],
        }

    # --- Dahili yardimcilar ---

    def _yukle(self) -> None:
        """JSON dosyasini yukler; dosya yoksa veya bozuksa bos baslar."""
        try:
            if os.path.exists(self._dosya_yolu):
                with open(self._dosya_yolu, "r", encoding="utf-8") as f:
                    self._veri = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"JSON yuklenemedi: {e}, yeni baslanıyor")
            self._veri = {}

    def _kaydet_dosya(self) -> None:
        """JSON dosyasina kaydeder; gerekirse dizin olusturur."""
        try:
            Path(self._dosya_yolu).parent.mkdir(parents=True, exist_ok=True)
            with open(self._dosya_yolu, "w", encoding="utf-8") as f:
                json.dump(self._veri, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"JSON kaydedilemedi: {e}")

    # --- Geriye uyumluluk (eski Turkce API) ---

    def kaydet(self, koleksiyon: str, dokuman: Dict[str, Any]) -> str:
        return self.save(koleksiyon, dokuman)

    def sorgula(self, koleksiyon: str, sorgu: str, limit: int = 5) -> List[Dict[str, Any]]:
        return self.search(koleksiyon, sorgu, limit)

    def sil(self, koleksiyon: str, doc_id: str) -> bool:
        return self.delete(koleksiyon, doc_id)

    def koleksiyon_listele(self) -> List[str]:
        return self.list_collections()

    def istatistik(self) -> dict:
        return self.stats()

    def _kaydet(self) -> None:
        """Eski icsel cagriler icin alias."""
        self._kaydet_dosya()


# =====================================================================
# SQLITE BACKEND
# =====================================================================

@MemoryProviderRegistry.register
class SQLiteBackend(MemoryProvider):
    """SQLite tabanli bellek backend'i."""

    _provider_name = "sqlite"

    def __init__(self, db_yolu: str = "memory_store.db"):
        self._db_yolu = db_yolu
        self._conn = None
        self._session_id: Optional[str] = None
        if _SQLITE_AVAILABLE:
            self._baglan()
            self._tablolari_olustur()
        else:
            logger.warning("SQLiteBackend: sqlite3 modulu bulunamadi, devre disi")

    # --- MemoryProvider interface ---

    @property
    def name(self) -> str:
        return "sqlite"

    def is_available(self) -> bool:
        return _SQLITE_AVAILABLE

    @staticmethod
    def _check_available() -> bool:
        return _SQLITE_AVAILABLE

    def initialize(self, session_id: str, **kwargs) -> None:
        """Oturumu baslatir; hermes_home verilirse db yolunu gunceller."""
        self._session_id = session_id
        hermes_home = kwargs.get("hermes_home")
        if hermes_home and _SQLITE_AVAILABLE:
            yeni_yol = os.path.join(str(hermes_home), "memory.db")
            if yeni_yol != self._db_yolu:
                self.kapat()
                self._db_yolu = yeni_yol
                self._baglan()
                self._tablolari_olustur()
        logger.info(f"SQLiteBackend baslatildi: session={session_id}, db={self._db_yolu}")

    def save(self, collection: str, document: dict, **kwargs) -> str:
        """Bir dokumani koleksiyona kaydeder."""
        if not _SQLITE_AVAILABLE or not self._conn:
            return ""
        try:
            cursor = self._conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO koleksiyonlar (ad, olusturma_zamani) VALUES (?, ?)",
                (collection, time.time())
            )
            dok_id = document.get("id") or f"doc_{int(time.time() * 1000)}"
            icerik = document.get("icerik", json.dumps(document, ensure_ascii=False))
            metadata = json.dumps(
                {k: v for k, v in document.items() if k not in ("id", "icerik")},
                ensure_ascii=False
            )
            cursor.execute(
                "INSERT OR REPLACE INTO dokumanlar (id, koleksiyon_adi, icerik, metadata, zaman) VALUES (?, ?, ?, ?, ?)",
                (dok_id, collection, icerik, metadata, time.time())
            )
            self._conn.commit()
            logger.info(f"SQLiteBackend.save: koleksiyon={collection}, id={dok_id}")
            return dok_id
        except sqlite3.Error as e:
            logger.error(f"SQLiteBackend.save hatasi: {e}")
            return ""

    def search(self, collection: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Koleksiyonda LIKE ile sorgu yapar. Bos sorgu tum kayitlari dondurur."""
        if not _SQLITE_AVAILABLE or not self._conn:
            return []
        try:
            cursor = self._conn.cursor()
            if query:
                cursor.execute(
                    """SELECT id, koleksiyon_adi, icerik, metadata, zaman
                       FROM dokumanlar
                       WHERE koleksiyon_adi = ? AND (icerik LIKE ? OR metadata LIKE ?)
                       ORDER BY zaman DESC LIMIT ?""",
                    (collection, f"%{query}%", f"%{query}%", limit)
                )
            else:
                cursor.execute(
                    """SELECT id, koleksiyon_adi, icerik, metadata, zaman
                       FROM dokumanlar WHERE koleksiyon_adi = ?
                       ORDER BY zaman DESC LIMIT ?""",
                    (collection, limit)
                )
            sonuclar = []
            for row in cursor.fetchall():
                doc = {
                    "id": row["id"],
                    "koleksiyon": row["koleksiyon_adi"],
                    "icerik": row["icerik"],
                    "zaman": row["zaman"],
                }
                try:
                    meta = json.loads(row["metadata"])
                    doc.update(meta)
                except (json.JSONDecodeError, TypeError):
                    logger.warning("[fix_01_sessiz_except] Exception")
                sonuclar.append(doc)
            return sonuclar
        except sqlite3.Error as e:
            logger.error(f"SQLiteBackend.search hatasi: {e}")
            return []

    def get(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """ID ile tek dokuman getirir."""
        if not _SQLITE_AVAILABLE or not self._conn:
            return None
        try:
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT id, koleksiyon_adi, icerik, metadata, zaman FROM dokumanlar WHERE koleksiyon_adi = ? AND id = ?",
                (collection, doc_id)
            )
            row = cursor.fetchone()
            if not row:
                return None
            doc = {
                "id": row["id"],
                "koleksiyon": row["koleksiyon_adi"],
                "icerik": row["icerik"],
                "zaman": row["zaman"],
            }
            try:
                meta = json.loads(row["metadata"])
                doc.update(meta)
            except (json.JSONDecodeError, TypeError):
                logger.warning("[fix_01_sessiz_except] Exception")
            return doc
        except sqlite3.Error as e:
            logger.error(f"SQLiteBackend.get hatasi: {e}")
            return None

    def delete(self, collection: str, doc_id: str) -> bool:
        """Bir dokumani siler."""
        if not _SQLITE_AVAILABLE or not self._conn:
            return False
        try:
            cursor = self._conn.cursor()
            cursor.execute(
                "DELETE FROM dokumanlar WHERE koleksiyon_adi = ? AND id = ?",
                (collection, doc_id)
            )
            self._conn.commit()
            silindi = cursor.rowcount > 0
            if silindi:
                logger.info(f"SQLiteBackend.delete: koleksiyon={collection}, id={doc_id}")
            return silindi
        except sqlite3.Error as e:
            logger.error(f"SQLiteBackend.delete hatasi: {e}")
            return False

    def list_collections(self) -> List[str]:
        """Mevcut koleksiyonlari listeler."""
        if not _SQLITE_AVAILABLE or not self._conn:
            return []
        try:
            cursor = self._conn.cursor()
            cursor.execute("SELECT ad FROM koleksiyonlar ORDER BY ad")
            return [row["ad"] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"SQLiteBackend.list_collections hatasi: {e}")
            return []

    def clear(self, collection: str) -> bool:
        """Koleksiyondaki tum dokumanlari siler."""
        if not _SQLITE_AVAILABLE or not self._conn:
            return False
        try:
            cursor = self._conn.cursor()
            cursor.execute("DELETE FROM dokumanlar WHERE koleksiyon_adi = ?", (collection,))
            self._conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"SQLiteBackend.clear hatasi: {e}")
            return False

    def stats(self) -> dict:
        """Istatistik bilgilerini dondurur."""
        if not _SQLITE_AVAILABLE or not self._conn:
            return {"backend": "sqlite", "aktif": False}
        try:
            cursor = self._conn.cursor()
            cursor.execute("SELECT COUNT(*) as n FROM dokumanlar")
            toplam = cursor.fetchone()["n"]
            cursor.execute("SELECT COUNT(*) as n FROM koleksiyonlar")
            kol_sayisi = cursor.fetchone()["n"]
            return {
                "backend": "sqlite",
                "aktif": True,
                "koleksiyonlar": kol_sayisi,
                "toplam_dokuman": toplam,
                "db": self._db_yolu,
            }
        except sqlite3.Error as e:
            return {"backend": "sqlite", "hata": str(e)}

    # --- Dahili yardimcilar ---

    def _baglan(self) -> None:
        """SQLite baglantisi acar."""
        try:
            self._conn = sqlite3.connect(self._db_yolu, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            logger.error(f"SQLiteBackend baglanti hatasi: {e}")
            raise

    def _tablolari_olustur(self) -> None:
        """Gerekli tablolari olusturur."""
        try:
            cursor = self._conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS koleksiyonlar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ad TEXT UNIQUE NOT NULL,
                    olusturma_zamani REAL NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dokumanlar (
                    id TEXT PRIMARY KEY,
                    koleksiyon_adi TEXT NOT NULL,
                    icerik TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    zaman REAL NOT NULL,
                    FOREIGN KEY (koleksiyon_adi) REFERENCES koleksiyonlar(ad)
                )
            """)
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_koleksiyon ON dokumanlar(koleksiyon_adi)"
            )
            self._conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Tablo olusturma hatasi: {e}")

    def kapat(self) -> None:
        """Baglantiyi kapatir (Windows file handle'i serbest birakir)."""
        try:
            if self._conn:
                self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                self._conn.close()
                self._conn = None
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")

    # --- Geriye uyumluluk (eski Turkce API) ---

    def kaydet(self, koleksiyon: str, dokuman: Dict[str, Any]) -> str:
        return self.save(koleksiyon, dokuman)

    def sorgula(self, koleksiyon: str, sorgu: str, limit: int = 5) -> List[Dict[str, Any]]:
        return self.search(koleksiyon, sorgu, limit)

    def sil(self, koleksiyon: str, doc_id: str) -> bool:
        return self.delete(koleksiyon, doc_id)

    def koleksiyon_listele(self) -> List[str]:
        return self.list_collections()

    def istatistik(self) -> dict:
        return self.stats()


# SqliteBackend alias (task tanim uyumlulugu icin)
SqliteBackend = SQLiteBackend


# =====================================================================
# CHROMA BACKEND (opsiyonel — chromadb yoksa graceful degrade)
# =====================================================================

@MemoryProviderRegistry.register
class ChromaBackend(MemoryProvider):
    """ChromaDB tabanli semantik bellek backend'i.

    chromadb kurulu degilse is_available() False dondurur;
    initialize() ve diger metotlar crash yapmaz.
    """

    _provider_name = "chroma"

    def __init__(self, chroma_yolu: str = ".ReYMeN/chroma"):
        self._chroma_yolu = chroma_yolu
        self._client = None
        self._koleksiyonlar: Dict[str, Any] = {}
        self._session_id: Optional[str] = None

    @property
    def name(self) -> str:
        return "chroma"

    def is_available(self) -> bool:
        return _CHROMA_AVAILABLE

    @staticmethod
    def _check_available() -> bool:
        return _CHROMA_AVAILABLE

    def initialize(self, session_id: str, **kwargs) -> None:
        """ChromaDB istemcisini baslatir. chromadb yoksa sessizce atlar."""
        self._session_id = session_id
        hermes_home = kwargs.get("hermes_home")
        yol = os.path.join(str(hermes_home), "chroma") if hermes_home else self._chroma_yolu
        if not _CHROMA_AVAILABLE:
            logger.warning("ChromaBackend: chromadb kurulu degil, devre disi")
            return
        try:
            Path(yol).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=yol)
            logger.info(f"ChromaBackend baslatildi: session={session_id}, yol={yol}")
        except Exception as e:
            logger.error(f"ChromaBackend baslatilamadi: {e}")
            self._client = None

    def _kol_al(self, collection: str):
        """Koleksiyonu cache'den veya client'tan getirir."""
        if not self._client:
            return None
        if collection not in self._koleksiyonlar:
            try:
                self._koleksiyonlar[collection] = self._client.get_or_create_collection(name=collection)
            except Exception as e:
                logger.error(f"ChromaBackend koleksiyon hatasi: {e}")
                return None
        return self._koleksiyonlar[collection]

    def save(self, collection: str, document: dict, **kwargs) -> str:
        kol = self._kol_al(collection)
        if not kol:
            return ""
        try:
            dok_id = document.get("id") or f"doc_{int(time.time() * 1000)}"
            icerik = document.get("icerik", json.dumps(document, ensure_ascii=False))
            metadata = {k: str(v) for k, v in document.items() if k not in ("id", "icerik")}
            kol.upsert(ids=[dok_id], documents=[icerik], metadatas=[metadata])
            logger.info(f"ChromaBackend.save: koleksiyon={collection}, id={dok_id}")
            return dok_id
        except Exception as e:
            logger.error(f"ChromaBackend.save hatasi: {e}")
            return ""

    def search(self, collection: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        kol = self._kol_al(collection)
        if not kol:
            return []
        try:
            q = query or " "
            sonuclar = kol.query(query_texts=[q], n_results=limit)
            cikti: List[Dict[str, Any]] = []
            ids = sonuclar.get("ids", [[]])[0]
            docs = sonuclar.get("documents", [[]])[0]
            metas = sonuclar.get("metadatas", [[]])[0]
            for dok_id, doc, meta in zip(ids, docs, metas):
                entry: Dict[str, Any] = {"id": dok_id, "icerik": doc}
                if meta:
                    entry.update(meta)
                cikti.append(entry)
            return cikti
        except Exception as e:
            logger.error(f"ChromaBackend.search hatasi: {e}")
            return []

    def get(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        kol = self._kol_al(collection)
        if not kol:
            return None
        try:
            result = kol.get(ids=[doc_id])
            if not result["ids"]:
                return None
            entry: Dict[str, Any] = {"id": result["ids"][0], "icerik": result["documents"][0]}
            if result.get("metadatas") and result["metadatas"][0]:
                entry.update(result["metadatas"][0])
            return entry
        except Exception as e:
            logger.error(f"ChromaBackend.get hatasi: {e}")
            return None

    def delete(self, collection: str, doc_id: str) -> bool:
        kol = self._kol_al(collection)
        if not kol:
            return False
        try:
            kol.delete(ids=[doc_id])
            return True
        except Exception as e:
            logger.error(f"ChromaBackend.delete hatasi: {e}")
            return False

    def list_collections(self) -> List[str]:
        if not self._client:
            return []
        try:
            return [c.name for c in self._client.list_collections()]
        except Exception as e:
            logger.error(f"ChromaBackend.list_collections hatasi: {e}")
            return []

    def clear(self, collection: str) -> bool:
        kol = self._kol_al(collection)
        if not kol:
            return False
        try:
            all_ids = kol.get()["ids"]
            if all_ids:
                kol.delete(ids=all_ids)
            return True
        except Exception as e:
            logger.error(f"ChromaBackend.clear hatasi: {e}")
            return False

    def stats(self) -> dict:
        if not self._client:
            sebep = "chromadb kurulu degil" if not _CHROMA_AVAILABLE else "baglanti yok"
            return {"backend": "chroma", "aktif": False, "sebep": sebep}
        try:
            kollar = self._client.list_collections()
            toplam = sum(k.count() for k in kollar)
            return {
                "backend": "chroma",
                "aktif": True,
                "koleksiyonlar": len(kollar),
                "toplam_dokuman": toplam,
            }
        except Exception as e:
            return {"backend": "chroma", "hata": str(e)}

    # Geriye uyumluluk
    def kaydet(self, koleksiyon: str, dokuman: Dict[str, Any]) -> str:
        return self.save(koleksiyon, dokuman)

    def sorgula(self, koleksiyon: str, sorgu: str, limit: int = 5) -> List[Dict[str, Any]]:
        return self.search(koleksiyon, sorgu, limit)

    def sil(self, koleksiyon: str, doc_id: str) -> bool:
        return self.delete(koleksiyon, doc_id)

    def koleksiyon_listele(self) -> List[str]:
        return self.list_collections()

    def istatistik(self) -> dict:
        return self.stats()


# =====================================================================
# YARDIMCI FONKSİYON
# =====================================================================

def get_default_provider(backend: str = "json", dosya_yolu: Optional[str] = None) -> MemoryProvider:
    """Registry'den backend secip baslatilmamis ornek dondurur.

    Eski MemoryProvider(backend_turu=...) kullanimi icin uyumluluk koprusu.
    """
    provider_cls = MemoryProviderRegistry.get(backend)
    if provider_cls is None:
        logger.warning(f"Bilinmeyen backend '{backend}', JSON kullanilıyor")
        provider_cls = JsonBackend

    if backend == "sqlite":
        return provider_cls(db_yolu=dosya_yolu or "memory_store.db")
    if backend == "chroma":
        return provider_cls(chroma_yolu=dosya_yolu or ".ReYMeN/chroma")
    return provider_cls(dosya_yolu=dosya_yolu or "memory_store.json")


# =====================================================================
# KATMAN 2: ReYMeN MEMORY PROVIDER PLUGIN ARAYUZU
# =====================================================================

class AbstraktHafizaSaglayici(ABC):
    """ReYMeN Memory Provider Plugin ABC'si — ReYMeN uyarlamasi.

    Her hafiza plugin'i bu sinifi miras alir ve plugins/memory/<ad>/ altinda
    yasar. Tek bir eklenti ayni anda aktif olabilir (cakisma onleme).

    Zorunlu metodlar:
        ad              — saglayici tanimlanici (property)
        musait_mi()     — dis bagimlilik kontrolu (ag cagrisi yapma)
        baslat()        — ajan baslatildiginda cagrilir
        arac_sema_al()  — ajan arac listesine enjekte edilecek schema
        arac_cagri_isle() — arac cagrilarini isle

    Opsiyonel kancalar (override et):
        sistem_prompt_bloku()
        onceden_getir(sorgu)
        tur_senkronize()      <- BLOKLAMAMALI; daemon thread kullan
        oturum_bitti()
        kapat()
    """

    @property
    @abstractmethod
    def ad(self) -> str:
        """Saglayici tanimlanici ('sqlite_fts', 'chromadb_vektor', vb.)."""

    @abstractmethod
    def musait_mi(self) -> bool:
        """Saglayicinin aktive edilebilecegini dogrula. AG CAGRISI YAPMA."""

    @abstractmethod
    def baslat(self, oturum_id: str, **kwargs) -> None:
        """Ajan baslatildiginda cagrilir. kwargs icinde 'reymen_dizin' (Path) gelir."""

    @abstractmethod
    def arac_sema_al(self) -> List[Dict[str, Any]]:
        """Baslat() sonrasi ajana enjekte edilecek arac tanimlari. Bos liste olabilir."""

    @abstractmethod
    def arac_cagri_isle(self, arac_adi: str, args: Dict[str, Any], **kwargs) -> str:
        """Gelen arac cagrisini isle ve sonucu string olarak dondur."""

    def konfig_sema_al(self) -> List[Dict[str, Any]]:
        """'reymen memory setup' icin konfigurasyon alanlari."""
        return []

    def konfig_kaydet(self, degerler: Dict[str, str], reymen_dizin: Path) -> None:
        """Gizli olmayan konfigurasyonu kaydet. Sirlar .env'e gider."""

    def sistem_prompt_bloku(self) -> str:
        """Sistem prompt'una eklenecek statik bilgi blogu. Bos olabilir."""
        return ""

    def onceden_getir(self, sorgu: str) -> str:
        """API cagrisi oncesi ilgili hafiza parcalarini dondur."""
        return ""

    def tur_senkronize(self, mesajlar: List[Dict[str, Any]]) -> None:
        """Tur bittikten sonra konusmayi kalici hafizaya kaydet. NON-BLOCKING."""
        def _arka_plan():
            try:
                self._tur_senkronize_impl(mesajlar)
            except Exception as e:
                logger.debug(f"[{self.ad}] tur_senkronize hata: {e}")
        threading.Thread(target=_arka_plan, daemon=True).start()

    def _tur_senkronize_impl(self, mesajlar: List[Dict[str, Any]]) -> None:
        """Alt siniflar bu metodu override eder (thread icinde calisir)."""

    def oturum_bitti(self) -> None:
        """Konusma sonunda son ayiklama/ozet. Opsiyonel."""

    def kapat(self) -> None:
        """Surec cikisinda kaynak temizligi. Opsiyonel."""

    def cli_kaydet(self, alt_komut_ekleyici) -> None:
        """'reymen memory <komut>' CLI uzantisi kaydet."""


# =====================================================================
# HAFIZA PLUGIN KAYIT BAGLAMI
# =====================================================================

class HafizaPluginKayit:
    """Plugin kayit baglami.

    plugins/memory/<ad>/__init__.py icindeki kaydet(ctx) fonksiyonuna gecer.

    Kullanim:
        ctx = HafizaPluginKayit()
        ctx.hafiza_saglayici_kaydet(BenimSaglayicim())
    """

    def __init__(self):
        self._saglayicilar: Dict[str, AbstraktHafizaSaglayici] = {}
        self._aktif: Optional[AbstraktHafizaSaglayici] = None

    def hafiza_saglayici_kaydet(self, saglayici: AbstraktHafizaSaglayici) -> None:
        """Saglayiciyi kesfedilebilir listeye ekle."""
        self._saglayicilar[saglayici.ad] = saglayici
        logger.debug(f"Hafiza saglayici kayit: {saglayici.ad}")

    def saglayici_listele(self) -> List[str]:
        return list(self._saglayicilar.keys())

    def saglayici_al(self, ad: str) -> Optional[AbstraktHafizaSaglayici]:
        return self._saglayicilar.get(ad)

    def aktif_saglayici_sec(self, ad: str, oturum_id: str, **kwargs) -> bool:
        """Saglayiciyi musait_mi() ile dogrula, baslat() ile aktive et.

        Tek saglayici ayni anda aktif olabilir.
        """
        if self._aktif:
            try:
                self._aktif.kapat()
            except Exception:
                logger.warning("[fix_01_sessiz_except] Exception")
            self._aktif = None

        saglayici = self._saglayicilar.get(ad)
        if not saglayici:
            logger.warning(f"Hafiza saglayici bulunamadi: {ad}")
            return False

        if not saglayici.musait_mi():
            logger.warning(f"Hafiza saglayici musait degil: {ad}")
            return False

        try:
            saglayici.baslat(oturum_id, **kwargs)
            self._aktif = saglayici
            logger.info(f"Aktif hafiza saglayici: {ad}")
            return True
        except Exception as e:
            logger.error(f"Hafiza saglayici baslatilamadi [{ad}]: {e}")
            return False

    def aktif_al(self) -> Optional[AbstraktHafizaSaglayici]:
        return self._aktif

    def hepsini_kapat(self) -> None:
        if self._aktif:
            try:
                self._aktif.kapat()
            except Exception:
                logger.warning("[fix_01_sessiz_except] Exception")
        self._aktif = None


# Modul duzeyinde paylasilan kayit nesnesi
_global_kayit = HafizaPluginKayit()


def global_hafiza_kayit_al() -> HafizaPluginKayit:
    """Modul genelinde tek HafizaPluginKayit ornegi dondurur."""
    return _global_kayit


# =====================================================================
# MODUL TEST FONKSİYONU
# =====================================================================

def run(**kwargs) -> str:
    """memory_provider modulunu basit bir donguyle test eder.

    Args:
        backend (str): "json", "sqlite" veya "chroma"

    Returns:
        str: JSON formatlı test sonucu
    """
    try:
        backend_adi = kwargs.get("backend", "json")
        provider = get_default_provider(backend=backend_adi)
        provider.initialize(session_id="test_session")

        doc_id = provider.save("test_koleksiyon", {
            "id": "test_doc_1",
            "baslik": "Test Dokumani",
            "icerik": "Bu bir test dokumanidir.",
        })

        sonuclar = provider.search("test_koleksiyon", "test")
        silindi = provider.delete("test_koleksiyon", "test_doc_1")

        if hasattr(provider, "kapat"):
            provider.kapat()

        # AbstraktHafizaSaglayici ABC dogrulama
        class _TestSaglayici(AbstraktHafizaSaglayici):
            @property
            def ad(self): return "test"
            def musait_mi(self): return True
            def baslat(self, oturum_id, **kw): pass
            def arac_sema_al(self): return []
            def arac_cagri_isle(self, arac, args, **kw): return "ok"

        ts = _TestSaglayici()
        kayit = HafizaPluginKayit()
        kayit.hafiza_saglayici_kaydet(ts)
        aktif = kayit.aktif_saglayici_sec("test", "oturum-001")

        return json.dumps({
            "backend": backend_adi,
            "kaydedilen_id": doc_id,
            "bulunan_sonuc": len(sonuclar),
            "silindi": silindi,
            "istatistik": provider.stats(),
            "available_backends": MemoryProviderRegistry.list_available(),
            "abc_test": "basarili" if aktif else "basarisiz",
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"run() hatasi: {e}")
        return json.dumps({"hata": str(e)}, ensure_ascii=False)


if __name__ == "__main__":
    import tempfile

    print("=== MemoryProviderRegistry ===")
    print("Kayitli:", MemoryProviderRegistry.list_all())
    print("Kullanilabilir:", MemoryProviderRegistry.list_available())

    with tempfile.TemporaryDirectory() as tmp:
        print("\n=== JsonBackend testi ===")
        jb = JsonBackend(dosya_yolu=os.path.join(tmp, "test.json"))
        jb.initialize(session_id="s1")
        dok_id = jb.save("notlar", {"baslik": "Merhaba", "icerik": "Deneme"})
        print("Kaydedilen ID:", dok_id)
        print("Arama:", jb.search("notlar", "Deneme"))
        print("Get:", jb.get("notlar", dok_id))
        print("Koleksiyonlar:", jb.list_collections())
        print("Stats:", jb.stats())
        print("Silindi:", jb.delete("notlar", dok_id))

        if _SQLITE_AVAILABLE:
            print("\n=== SQLiteBackend testi ===")
            sb = SQLiteBackend(db_yolu=os.path.join(tmp, "test.db"))
            sb.initialize(session_id="s2")
            dok_id = sb.save("notlar", {"baslik": "SQLite", "icerik": "Veritabani"})
            print("Kaydedilen ID:", dok_id)
            print("Arama:", sb.search("notlar", "Veritabani"))
            print("Stats:", sb.stats())
            sb.kapat()

        print("\n=== run() testi ===")
        print(run(backend="json"))
