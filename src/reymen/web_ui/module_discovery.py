"""📦 Dinamik modül keşfi — reymen/ altındaki tüm modülleri bulur ve durumlarını raporlar."""

from __future__ import annotations

import logging
import pkgutil
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REYMEN_PAKET = "reymen"

# ---------------------------------------------------------------------------
# Modül bilgisi
# ---------------------------------------------------------------------------

class ModulBilgisi:
    """Bir modülün adı, yolu, yüklenme durumu ve açıklaması."""

    __slots__ = ("adi", "yolu", "yuklu", "hata", "aciklama", "satir_sayisi", "kategori")

    def __init__(
        self,
        adi: str,
        yolu: str = "",
        yuklu: bool = False,
        hata: str = "",
        aciklama: str = "",
        satir_sayisi: int = 0,
        kategori: str = "",
    ) -> None:
        self.adi = adi
        self.yolu = yolu
        self.yuklu = yuklu
        self.hata = hata
        self.aciklama = aciklama
        self.satir_sayisi = satir_sayisi
        self.kategori = kategori

    def to_dict(self) -> dict[str, Any]:
        return {
            "adi": self.adi,
            "yolu": self.yolu,
            "yuklu": self.yuklu,
            "hata": self.hata,
            "aciklama": self.aciklama,
            "satir_sayisi": self.satir_sayisi,
            "kategori": self.kategori,
        }

# ---------------------------------------------------------------------------
# Modül tarayıcı
# ---------------------------------------------------------------------------

class ModulTarayici:
    """reymen/ paketini tarar, tüm alt modülleri keşfeder."""

    def __init__(self, kok: Path | None = None) -> None:
        self.kok = kok or Path(__file__).resolve().parent.parent

    def tara(self) -> list[ModulBilgisi]:
        """Tüm reymen.* modüllerini tara ve durumlarını döndür."""
        moduller: list[ModulBilgisi] = []
        gorulen: set[str] = set()

        # 1. pkgutil ile paket taraması
        try:
            import reymen
            for importer, mod_adi, is_pkg in pkgutil.walk_packages(
                reymen.__path__, prefix=f"{REYMEN_PAKET}."
            ):
                if mod_adi in gorulen:
                    continue
                gorulen.add(mod_adi)
                bilgi = self._modul_bilgisi(mod_adi, is_pkg)
                moduller.append(bilgi)
        except Exception as e:
            logger.warning("pkgutil taramasi basarisiz: %s", e)

        # 2. __pycache__, .venv, site-packages filtrele
        moduller = [m for m in moduller if self._filtrele(m)]

        return sorted(moduller, key=lambda m: m.adi)

    def _modul_bilgisi(self, mod_adi: str, is_pkg: bool = False) -> ModulBilgisi:
        """Tek modül için bilgi topla."""
        yuklu = mod_adi in sys.modules
        hata = ""
        satir_sayisi = 0
        aciklama = ""
        yolu = ""

        mod = sys.modules.get(mod_adi)
        if mod:
            try:
                yolu = getattr(mod, "__file__", "") or ""
                if yolu and Path(yolu).exists():
                    satir_sayisi = sum(1 for _ in open(yolu, encoding="utf-8", errors="ignore"))
                doc = getattr(mod, "__doc__", "") or ""
                if doc:
                    # İlk satırı al
                    aciklama = doc.strip().split("\n")[0][:120]
            except Exception as _e:
                __import__("logging").getLogger(__name__).warning(
                    "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                )

        # Kategori: reymen.xxx.yyy -> xxx
        kategori = ""
        bas = mod_adi[len(REYMEN_PAKET) + 1:]
        if "." in bas:
            kategori = bas.split(".")[0]

        return ModulBilgisi(
            adi=mod_adi,
            yolu=yolu,
            yuklu=yuklu,
            hata=hata,
            aciklama=aciklama,
            satir_sayisi=satir_sayisi,
            kategori=kategori or "kok",
        )

    @staticmethod
    def _filtrele(m: ModulBilgisi) -> bool:
        """__pycache__, .venv, site-packages içindekileri filtrele."""
        if not m.yolu:
            return True
        y = m.yolu.replace("\\", "/")
        if "__pycache__" in y:
            return False
        if "/site-packages/" in y:
            return False
        return True


def modul_kategorileri(moduller: list[ModulBilgisi]) -> dict[str, list[ModulBilgisi]]:
    """Modülleri kategorilerine göre grupla."""
    kategoriler: dict[str, list[ModulBilgisi]] = {}
    for m in moduller:
        kat = m.kategori or "kok"
        kategoriler.setdefault(kat, []).append(m)
    return kategoriler
