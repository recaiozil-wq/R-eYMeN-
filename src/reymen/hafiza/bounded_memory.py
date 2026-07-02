# -*- coding: utf-8 -*-
"""
bounded_memory.py — Sinirli bellek.

LRU (Least Recently Used) mantigiyla calisan,
maksimum kapasiteli bir bellek yonetimi sinifi.

Kullanim:
    mem = BoundedMemory(max_boyut=100)
    mem.hatirla("anahtar", "deger")
    deger = mem.unut("anahtar")  # anahtar var mi kontrol et
    mem.temizle()
"""

import os
import json
import time
import logging
from collections import OrderedDict
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class BoundedMemory:
    """Sinirli kapasiteli, LRU tabanli bellek.

    Maksimum boyuta ulasildiginda en az kullanilan ogeler
    otomatik olarak silinir. Her oge bir zaman damgasi tasir.

    Ornek kullanim:
        mem = BoundedMemory(max_boyut=3)
        mem.hatirla("renk", "mavi")
        mem.hatirla("sayi", 42)
        print(mem.kapasite())  # 1/3
    """

    def __init__(self, max_boyut: int = 100, kayit_yolu: Optional[str] = None):
        """BoundedMemory sinifini baslat.

        Args:
            max_boyut: Maksimum oge sayisi (varsayilan: 100)
            kayit_yolu: Opsiyonel, JSON dosyaya kayit yolu
        """
        self._max_boyut = max(max_boyut, 1)
        self._veri: OrderedDict = OrderedDict()
        self._zaman_damgalari: dict = {}
        self._kayit_yolu = kayit_yolu
        self._istatistik = {
            "ekleme": 0,
            "silme": 0,
            "atilma": 0,
            "hit": 0,
            "miss": 0,
        }
        logger.info("BoundedMemory baslatildi. Max: %d, Kayit: %s",
                     self._max_boyut, self._kayit_yolu or "yok")

    def hatirla(self, anahtar: str, deger: Any) -> str:
        """Bir degeri bellekte sakla.

        Anahtar zaten varsa degeri guncellenir ve LRU sirasinda
        en sona tasinir. Kapasite dolmussa en eski oge silinir.

        Args:
            anahtar: Saklanacak anahtar
            deger: Saklanacak deger

        Returns:
            Islem sonucu mesaji
        """
        try:
            if not isinstance(anahtar, str):
                anahtar = str(anahtar)

            # Kapasite kontrolu - zaten varolan anahtar sayilmaz
            if anahtar not in self._veri and len(self._veri) >= self._max_boyut:
                self._en_eskiyi_at()

            # Varsa once guncelle, yoksa ekle
            if anahtar in self._veri:
                self._veri.move_to_end(anahtar)
            else:
                self._veri[anahtar] = deger

            self._zaman_damgalari[anahtar] = time.time()
            self._istatistik["ekleme"] += 1
            self._otomatik_kaydet()

            return f"[Bellek] '{anahtar}' kaydedildi. ({len(self._veri)}/{self._max_boyut})"
        except Exception as e:
            logger.exception("Bellek kayit hatasi")
            return f"[Bellek] Kayit hatasi: {e}"

    def _en_eskiyi_at(self):
        """LRU mantigiyla en eski (en az kullanilan) ogeleri at."""
        try:
            atilacak = len(self._veri) - self._max_boyut + 1
            if atilacak <= 0:
                atilacak = 1
            for _ in range(atilacak):
                eski_anahtar, eski_deger = self._veri.popitem(last=False)
                self._zaman_damgalari.pop(eski_anahtar, None)
                self._istatistik["atilma"] += 1
                logger.debug("LRU atma: '%s'", eski_anahtar)
        except Exception as e:
            logger.warning("Oge atma hatasi: %s", e)

    def unut(self, anahtar: str) -> str:
        """Bir anahtari bellekten sil.

        Args:
            anahtar: Silinecek anahtar

        Returns:
            Islem sonucu mesaji
        """
        try:
            if anahtar in self._veri:
                self._veri.pop(anahtar)
                self._zaman_damgalari.pop(anahtar, None)
                self._istatistik["silme"] += 1
                self._otomatik_kaydet()
                return f"[Bellek] '{anahtar}' silindi."
            return f"[Bellek] '{anahtar}' bulunamadi."
        except Exception as e:
            logger.exception("Bellek silme hatasi")
            return f"[Bellek] Silme hatasi: {e}"

    def temizle(self) -> str:
        """Tum bellegi temizle.

        Returns:
            Islem sonucu mesaji
        """
        try:
            onceki_sayi = len(self._veri)
            self._veri.clear()
            self._zaman_damgalari.clear()
            self._otomatik_kaydet()
            return f"[Bellek] {onceki_sayi} oge temizlendi."
        except Exception as e:
            logger.exception("Bellek temizleme hatasi")
            return f"[Bellek] Temizleme hatasi: {e}"

    def kapasite(self) -> str:
        """Mevcut kapasite durumunu goster.

        Returns:
            "kullanilan/maks" formatinda metin
        """
        return f"{len(self._veri)}/{self._max_boyut}"

    def dolu_mu(self) -> bool:
        """Bellegin dolu olup olmadigini kontrol et.

        Returns:
            True ise bellek dolu
        """
        return len(self._veri) >= self._max_boyut

    def oku(self, anahtar: str) -> Any:
        """Bir anahtarin degerini oku (silmadan).

        Args:
            anahtar: Okunacak anahtar

        Returns:
            Deger veya None
        """
        try:
            if anahtar in self._veri:
                self._veri.move_to_end(anahtar)
                self._zaman_damgalari[anahtar] = time.time()
                self._istatistik["hit"] += 1
                return self._veri[anahtar]
            self._istatistik["miss"] += 1
            return None
        except Exception:
            return None

    def anahtarlar(self) -> list:
        """Tum anahtarlari listele.

        Returns:
            Anahtar listesi
        """
        return list(self._veri.keys())

    def istatistik(self) -> dict:
        """Bellek istatistiklerini dondur.

        Returns:
            Istatistik sozlugu
        """
        return {
            **self._istatistik,
            "boyut": len(self._veri),
            "max_boyut": self._max_boyut,
            "dolu": self.dolu_mu(),
        }

    def kaydet(self, icerik: str, dosya_adi: str = "MEMORY.md") -> str:
        """Icerigi kalici bellek dosyasina ekle (MEMORY.md gibi).

        Args:
            icerik: Eklenecek metin
            dosya_adi: Hedef dosya adi (varsayilan: MEMORY.md)
        """
        try:
            yol = Path(dosya_adi)
            if not yol.is_absolute():
                ReYMeN_home = Path(os.environ.get("ReYMeN_HOME", ".ReYMeN"))
                yol = ReYMeN_home / "memories" / yol
            yol.parent.mkdir(parents=True, exist_ok=True)
            with open(yol, "a", encoding="utf-8") as f:
                f.write(icerik + "\n")
            logger.debug("Bellek dosyasi guncellendi: %s", yol)
            return f"[BoundedMemory] {dosya_adi} guncellendi."
        except Exception as e:
            logger.warning("Kayit hatasi: %s", e)
            return f"[BoundedMemory] Kayit hatasi: {e}"

    def _otomatik_kaydet(self):
        """JSON dosyaya otomatik kaydet (egitim yolu varsa)."""
        if not self._kayit_yolu:
            return
        try:
            with open(self._kayit_yolu, "w", encoding="utf-8") as f:
                json.dump({
                    "veri": dict(self._veri),
                    "zaman_damgalari": self._zaman_damgalari,
                    "istatistik": self._istatistik,
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("Otomatik kayit basarisiz: %s", e)

    def _yukle(self) -> bool:
        """JSON dosyadan yukle.

        Returns:
            Basarili ise True
        """
        if not self._kayit_yolu or not os.path.exists(self._kayit_yolu):
            return False
        try:
            with open(self._kayit_yolu, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._veri = OrderedDict(data.get("veri", {}))
            self._zaman_damgalari = data.get("zaman_damgalari", {})
            self._istatistik = data.get("istatistik", self._istatistik)
            logger.info("Bellek yuklendi: %d oge", len(self._veri))
            return True
        except Exception as e:
            logger.warning("Bellek yukleme hatasi: %s", e)
            return False


def run(**kwargs) -> str:
    """BoundedMemory sinifini calistir.

    Args:
        **kwargs: Su parametreler desteklenir:
            - islem: "hatirla", "unut", "temizle", "kapasite", "dolu_mu",
                     "oku", "anahtarlar", "istatistik"
            - anahtar: Islem yapilacak anahtar
            - deger: Kaydedilecek deger
            - max_boyut: Maksimum bellek boyutu

    Returns:
        Islem sonucu metni
    """
    try:
        mem = BoundedMemory(max_boyut=kwargs.get("max_boyut", 100))
        islem = kwargs.get("islem", "kapasite")
        anahtar = kwargs.get("anahtar", "")
        deger = kwargs.get("deger")

        if islem == "hatirla":
            return mem.hatirla(anahtar, deger)
        elif islem == "unut":
            return mem.unut(anahtar)
        elif islem == "temizle":
            return mem.temizle()
        elif islem == "kapasite":
            return mem.kapasite()
        elif islem == "dolu_mu":
            return "Evet" if mem.dolu_mu() else "Hayir"
        elif islem == "oku":
            sonuc = mem.oku(anahtar)
            return str(sonuc) if sonuc is not None else f"'{anahtar}' bulunamadi."
        elif islem == "anahtarlar":
            return ", ".join(mem.anahtarlar()) or "(bos)"
        elif islem == "istatistik":
            return json.dumps(mem.istatistik(), ensure_ascii=False, indent=2)
        else:
            return mem.kapasite()
    except Exception as e:
        return f"[BoundedMemory] Calistirma hatasi: {e}"


if __name__ == "__main__":
    print("=== BoundedMemory Test ===")
    mem = BoundedMemory(max_boyut=3)
    print(mem.hatirla("renk", "mavi"))
    print(mem.hatirla("sayi", 42))
    print(mem.hatirla("sehir", "Istanbul"))
    print(mem.kapasite())
    print(mem.dolu_mu())
    print(mem.hatirla("dorduncu", "tasacak!"))
    print(mem.anahtarlar())
    print(mem.unut("sayi"))
    print(mem.kapasite())
    print(mem.temizle())
    print(json.dumps(mem.istatistik(), ensure_ascii=False, indent=2))
    print("=== Test Tamam ===")
