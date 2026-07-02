# -*- coding: utf-8 -*-
"""
robust_execution.py — Saglam calistirma modulu.

Yeniden deneme, geri alma ve checkpoint mekanizmalari
ile guvenilir fonksiyon calistirma saglar.
"""

import os
import json
import time
import random
import logging
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class RobustExecutor:
    """
    Saglam calistirma yoneticisi.

    Fonksiyonlari yeniden deneme, geri alma
    ve checkpoint mekanizmalari ile calistirir.
    """

    def __init__(
        self,
        checkpoint_dizini: str = ".checkpoints",
        max_deneme: int = 3,
        bekleme_suresi: float = 1.0
    ):
        """
        RobustExecutor baslatici.

        Args:
            checkpoint_dizini: Checkpoint kayit dizini
            max_deneme: Maksimum yeniden deneme sayisi
            bekleme_suresi: Denemeler arasi bekleme (saniye)
        """
        self._checkpoint_dizini = checkpoint_dizini
        self._max_deneme = max_deneme
        self._bekleme_suresi = bekleme_suresi
        self._checkpoint_verisi: Dict[str, Any] = {}
        self._geri_alma_gecmisi: List[Dict[str, Any]] = []
        self._calistirma_id = 0

        # Checkpoint dizinini olustur
        try:
            os.makedirs(checkpoint_dizini, exist_ok=True)
        except OSError as e:
            logger.warning(f"Checkpoint dizini olusturulamadi: {e}")

    def calistir(
        self,
        fonk: Callable,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Bir fonksiyonu calistirir.

        Args:
            fonk: Calistirilacak fonksiyon
            *args: Pozisyonel argumanlar
            **kwargs: Anahtarli argumanlar

        Returns:
            dict: Calistirma sonucu
        """
        self._calistirma_id += 1
        calistirma_id = self._calistirma_id
        baslangic = time.time()

        try:
            logger.debug(f"Calistirma #{calistirma_id}: {fonk.__name__}")

            # Geri alma icin kaydet
            self._geri_alma_gecmisi.append({
                "id": calistirma_id,
                "fonk_adi": getattr(fonk, "__name__", str(fonk)),
                "args": args,
                "kwargs": kwargs,
                "baslangic": baslangic,
            })

            # Fonksiyonu calistir
            sonuc = fonk(*args, **kwargs)

            sure = time.time() - baslangic

            # Basarili kaydi guncelle
            self._geri_alma_gecmisi[-1]["sonuc"] = sonuc
            self._geri_alma_gecmisi[-1]["basarili"] = True
            self._geri_alma_gecmisi[-1]["sure"] = sure

            return {
                "basarili": True,
                "sonuc": sonuc,
                "sure": round(sure, 3),
                "calistirma_id": calistirma_id,
                "deneme_sayisi": 1,
            }

        except Exception as e:
            sure = time.time() - baslangic
            hata_detay = traceback.format_exc()

            # Basarisiz kaydi guncelle
            self._geri_alma_gecmisi[-1]["hata"] = str(e)
            self._geri_alma_gecmisi[-1]["basarili"] = False
            self._geri_alma_gecmisi[-1]["sure"] = sure

            logger.error(
                f"Calistirma #{calistirma_id} hatasi: {e}\n{hata_detay}"
            )

            return {
                "basarili": False,
                "hata": str(e),
                "traceback": hata_detay,
                "sure": round(sure, 3),
                "calistirma_id": calistirma_id,
            }

    def yeniden_dene(
        self,
        fonk: Callable,
        *args,
        max_deneme: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Fonksiyonu hata durumunda yeniden dener.

        Args:
            fonk: Calistirilacak fonksiyon
            *args: Pozisyonel argumanlar
            max_deneme: Maksimum deneme sayisi
            **kwargs: Anahtarli argumanlar

        Returns:
            dict: Calistirma sonucu
        """
        deneme_sayisi = max_deneme or self._max_deneme
        son_hata = None
        baslangic = time.time()

        for deneme in range(1, deneme_sayisi + 1):
            try:
                logger.info(
                    f"Deneme {deneme}/{deneme_sayisi}: {fonk.__name__}"
                )

                sonuc = fonk(*args, **kwargs)

                toplam_sure = time.time() - baslangic
                return {
                    "basarili": True,
                    "sonuc": sonuc,
                    "deneme_sayisi": deneme,
                    "toplam_sure": round(toplam_sure, 3),
                }

            except Exception as e:
                son_hata = e

                if deneme < deneme_sayisi:
                    # Exponential backoff
                    bekleme = self._bekleme_suresi * (2 ** (deneme - 1))
                    # Jitter ekle
                    bekleme += random.uniform(0, bekleme * 0.1)

                    logger.warning(
                        f"Deneme {deneme} basarisiz: {e}. "
                        f"{bekleme:.1f}s bekleniyor..."
                    )
                    time.sleep(bekleme)

        toplam_sure = time.time() - baslangic
        return {
            "basarili": False,
            "hata": str(son_hata),
            "deneme_sayisi": deneme_sayisi,
            "toplam_sure": round(toplam_sure, 3),
        }

    def geri_al(self, adim_sayisi: int = 1) -> bool:
        """
        Son calistirmalari geri alir.

        Args:
            adim_sayisi: Geri alinacak adim sayisi

        Returns:
            bool: Basarili ise True
        """
        try:
            if not self._geri_alma_gecmisi:
                logger.warning("Geri alinacak islem yok")
                return False

            geri_alinan = 0
            for _ in range(min(adim_sayisi, len(self._geri_alma_gecmisi))):
                kayit = self._geri_alma_gecmisi.pop()
                logger.info(
                    f"Geri alindi: {kayit.get('fonk_adi', '?')} "
                    f"(#{kayit.get('id', '?')})"
                )
                geri_alinan += 1

            return geri_alinan > 0

        except Exception as e:
            logger.error(f"Geri alma hatasi: {e}")
            return False

    def checkpoint_kaydet(self, etiket: str, veri: Any) -> bool:
        """
        Bir checkpoint kaydeder.

        Args:
            etiket: Checkpoint etiketi
            veri: Kaydedilecek veri

        Returns:
            bool: Basarili ise True
        """
        try:
            zaman = time.time()
            dosya_adi = f"checkpoint_{etiket}_{int(zaman)}.json"
            dosya_yolu = os.path.join(self._checkpoint_dizini, dosya_adi)

            checkpoint = {
                "etiket": etiket,
                "zaman": zaman,
                "veri": veri,
                "calistirma_id": self._calistirma_id,
            }

            with open(dosya_yolu, "w", encoding="utf-8") as f:
                json.dump(checkpoint, f, ensure_ascii=False, indent=2)

            self._checkpoint_verisi[etiket] = veri
            logger.info(f"Checkpoint kaydedildi: {etiket} -> {dosya_yolu}")
            return True

        except (IOError, TypeError) as e:
            logger.error(f"Checkpoint kayit hatasi: {e}")
            return False

    def checkpoint_yukle(self, etiket: str) -> Optional[Any]:
        """
        Bir checkpoint'i yukler.

        Args:
            etiket: Checkpoint etiketi

        Returns:
            Any: Kaydedilmis veri veya None
        """
        try:
            # En son checkpoint dosyasini bul
            desen = f"checkpoint_{etiket}_"
            en_son = None
            en_son_zaman = 0

            if os.path.isdir(self._checkpoint_dizini):
                for dosya in os.listdir(self._checkpoint_dizini):
                    if dosya.startswith(desen) and dosya.endswith(".json"):
                        dosya_yolu = os.path.join(self._checkpoint_dizini, dosya)
                        dosya_zaman = os.path.getmtime(dosya_yolu)
                        if dosya_zaman > en_son_zaman:
                            en_son = dosya_yolu
                            en_son_zaman = dosya_zaman

            if en_son:
                with open(en_son, "r", encoding="utf-8") as f:
                    checkpoint = json.load(f)
                veri = checkpoint.get("veri")
                self._checkpoint_verisi[etiket] = veri
                logger.info(f"Checkpoint yuklendi: {etiket}")
                return veri

            logger.warning(f"Checkpoint bulunamadi: {etiket}")
            return None

        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Checkpoint yukleme hatasi: {e}")
            return None

    def gecmis(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Calistirma gecmisini dondurur."""
        return list(self._geri_alma_gecmisi[-limit:])

    def durum(self) -> Dict[str, Any]:
        """Mevcut durumu dondurur."""
        toplam = len(self._geri_alma_gecmisi)
        basarili = sum(1 for k in self._geri_alma_gecmisi if k.get("basarili"))
        return {
            "toplam_calistirma": toplam,
            "basarili": basarili,
            "basarisiz": toplam - basarili,
            "checkpoint_sayisi": len(self._checkpoint_verisi),
            "max_deneme": self._max_deneme,
            "calistirma_id": self._calistirma_id,
        }


def run(**kwargs) -> str:
    """
    RobustExecutor'u calistirir.

    Args:
        **kwargs: Test parametreleri

    Returns:
        str: Test sonucu
    """
    try:
        executor = RobustExecutor()

        # Basarili fonksiyon
        def basarili_fonk(ad: str) -> str:
            return f"Merhaba {ad}!"

        # Bazen hata veren fonksiyon
        def kararsiz_fonk(sayi: int) -> int:
            if random.random() < 0.6:
                raise ValueError("Rastgele hata!")
            return sayi * 2

        sonuc1 = executor.calistir(basarili_fonk, ad="Test")
        sonuc2 = executor.yeniden_dene(kararsiz_fonk, sayi=21, max_deneme=3)

        executor.checkpoint_kaydet("test_checkpoint", {"durum": "test"})
        yuklenen = executor.checkpoint_yukle("test_checkpoint")

        durum = executor.durum()

        return json.dumps({
            "basarili_calistirma": sonuc1,
            "yeniden_deneme": sonuc2,
            "checkpoint_yukleme": "yuklendi" if yuklenen else "bulunamadi",
            "durum": durum,
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return f"Robust execution hatasi: {e}"


# Eski ad uyumlulugu (main.py icin)
RobustExecutionEngine = RobustExecutor
