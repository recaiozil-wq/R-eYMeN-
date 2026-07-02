# -*- coding: utf-8 -*-
"""
tool_executor.py — Arac yurutucu modulu.

Arac cagrilarini guvenli sekilde yurutur,
timeout yonetimi ve gecmis kaydi yapar.
"""

import time
import json
import importlib
import logging
import threading
import traceback
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Arac yurutucu.

    Tool cagrilarini guvenli sekilde calistirir,
    timeout yonetir ve islem gecmisini tutar.
    """

    def __init__(self, varsayilan_timeout: float = 30.0):
        """
        ToolExecutor baslatici.

        Args:
            varsayilan_timeout: Varsayilan timeout (saniye)
        """
        self._varsayilan_timeout = varsayilan_timeout
        self._aktif_islemler: Dict[str, Dict[str, Any]] = {}
        self._gecmis: List[Dict[str, Any]] = []
        self._max_gecmis = 100
        self._kilit = threading.Lock()

    def calistir(
        self,
        arac: Callable,
        **params
    ) -> Dict[str, Any]:
        """
        Bir araci parametrelerle calistirir.

        Args:
            arac: Calistirilacak fonksiyon
            **params: Arac parametreleri

        Returns:
            dict: Islemin sonucu
        """
        islem_id = f"islem_{int(time.time() * 1000)}"
        baslangic = time.time()

        try:
            logger.debug(f"Arac calistiriliyor: {getattr(arac, '__name__', str(arac))}, ID: {islem_id}")

            # Islemi kaydet
            islem = {
                "id": islem_id,
                "arac_adi": getattr(arac, "__name__", str(arac)),
                "parametreler": params,
                "baslangic": baslangic,
                "durum": "calisiyor",
            }

            with self._kilit:
                self._aktif_islemler[islem_id] = islem

            # Araci calistir
            sonuc = arac(**params)

            sure = time.time() - baslangic
            islem["durum"] = "tamamlandi"
            islem["sonuc"] = sonuc
            islem["sure"] = sure

            self._gecmis_kaydet(islem)

            return {
                "basarili": True,
                "islem_id": islem_id,
                "sonuc": sonuc,
                "sure": round(sure, 3),
            }

        except Exception as e:
            sure = time.time() - baslangic
            hata_detay = traceback.format_exc()

            islem = {
                "id": islem_id,
                "arac_adi": getattr(arac, "__name__", str(arac)),
                "parametreler": params,
                "baslangic": baslangic,
                "durum": "hata",
                "hata": str(e),
                "traceback": hata_detay,
                "sure": sure,
            }

            self._gecmis_kaydet(islem)

            return {
                "basarili": False,
                "islem_id": islem_id,
                "hata": str(e),
                "sure": round(sure, 3),
            }

        finally:
            with self._kilit:
                self._aktif_islemler.pop(islem_id, None)

    def calistir_guvenli(
        self,
        arac: Callable,
        timeout: Optional[float] = None,
        **params
    ) -> Dict[str, Any]:
        """
        Araci timeout ile calistirir.

        Args:
            arac: Calistirilacak fonksiyon
            timeout: Maksimum bekleme (saniye)
            **params: Parametreler

        Returns:
            dict: Sonuc
        """
        timeout = timeout or self._varsayilan_timeout
        sonuc = [None]
        hata = [None]
        tamamlandi = [False]

        def runner():
            try:
                sonuc[0] = arac(**params)
                tamamlandi[0] = True
            except Exception as e:
                hata[0] = e
                tamamlandi[0] = True

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            return {
                "basarili": False,
                "hata": f"Timeout: {timeout}s",
                "timeout": True,
            }

        if hata[0]:
            return {
                "basarili": False,
                "hata": str(hata[0]),
                "timeout": False,
            }

        return {
            "basarili": True,
            "sonuc": sonuc[0],
            "timeout": False,
        }

    def _load_tool(self, module_name: str) -> Callable:
        """tools/ klasorundeki bir araci yukler ve run() fonksiyonunu dondurur."""
        mod = importlib.import_module(f"tools.{module_name}")
        run_fn = getattr(mod, "run", None)
        if not callable(run_fn):
            raise AttributeError(f"tools.{module_name} run() fonksiyonu bulunamadi")
        return run_fn

    def calistir_tool(
        self,
        module_name: str,
        timeout: Optional[float] = None,
        **params
    ) -> Dict[str, Any]:
        """tools.<module_name> icindeki run() fonksiyonunu calistirir."""
        try:
            run_fn = self._load_tool(module_name)
        except Exception as exc:
            return {
                "basarili": False,
                "hata": str(exc),
                "timeout": False,
            }
        return self.calistir_guvenli(run_fn, timeout=timeout or self._varsayilan_timeout, **params)

    def _gecmis_kaydet(self, islem: Dict[str, Any]) -> None:
        """Islem gecmisine kaydeder."""
        try:
            with self._kilit:
                self._gecmis.append(islem)
                if len(self._gecmis) > self._max_gecmis:
                    self._gecmis = self._gecmis[-self._max_gecmis:]
        except Exception as e:
            logger.error(f"Gecmis kaydi hatasi: {e}")

    def iptal(self, islem_id: str) -> bool:
        """
        Bir islemi iptal eder (isaretler).

        Args:
            islem_id: Islem ID'si

        Returns:
            bool: Basarili ise True
        """
        try:
            with self._kilit:
                if islem_id in self._aktif_islemler:
                    self._aktif_islemler[islem_id]["durum"] = "iptal_edildi"
                    logger.info(f"Islem iptal edildi: {islem_id}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Iptal hatasi: {e}")
            return False

    def durum(self, islem_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Islem durumunu dondurur.

        Args:
            islem_id: Islem ID'si (None ise tum aktif)

        Returns:
            dict: Durum bilgisi
        """
        try:
            if islem_id:
                with self._kilit:
                    aktif = self._aktif_islemler.get(islem_id)
                if aktif:
                    return {"bulundu": True, "islem": aktif}
                # Gecmiste ara
                for islem in reversed(self._gecmis):
                    if islem.get("id") == islem_id:
                        return {"bulundu": True, "islem": islem}
                return {"bulundu": False, "hata": f"Islem bulunamadi: {islem_id}"}

            with self._kilit:
                aktif_liste = list(self._aktif_islemler.values())

            return {
                "aktif_sayisi": len(aktif_liste),
                "aktif_islemler": aktif_liste,
                "gecmis_sayisi": len(self._gecmis),
            }

        except Exception as e:
            return {"hata": str(e)}

    def gecmis(
        self,
        limit: int = 10,
        arac_adi: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Islem gecmisini dondurur.

        Args:
            limit: Maksimum kayit sayisi
            arac_adi: Filtreleme icin arac adi

        Returns:
            list: Islem kayitlari
        """
        try:
            with self._kilit:
                kayitlar = list(self._gecmis)

            if arac_adi:
                kayitlar = [k for k in kayitlar if k.get("arac_adi") == arac_adi]

            return kayitlar[-limit:]

        except Exception as e:
            logger.error(f"Gecmis hatasi: {e}")
            return []

    def istatistik(self) -> Dict[str, Any]:
        """Executor istatistiklerini dondurur."""
        try:
            with self._kilit:
                basarili = sum(1 for k in self._gecmis if k.get("durum") == "tamamlandi")
                hatali = sum(1 for k in self._gecmis if k.get("durum") == "hata")

            return {
                "toplam_islem": len(self._gecmis),
                "basarili": basarili,
                "hatali": hatali,
                "aktif": len(self._aktif_islemler),
                "ortalama_sure": self._ortalama_sure_hesapla(),
            }
        except Exception as e:
            return {"hata": str(e)}

    def _ortalama_sure_hesapla(self) -> float:
        """Ortalama islem suresini hesaplar."""
        try:
            sureler = [
                k.get("sure", 0) for k in self._gecmis
                if isinstance(k.get("sure"), (int, float))
            ]
            if sureler:
                return round(sum(sureler) / len(sureler), 3)
            return 0.0
        except Exception:
            return 0.0


def execute_tool_module(
    module_name: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: Optional[float] = None,
) -> Dict[str, Any]:
    """tools.<module_name> modulu icindeki run() fonksiyonunu guvenli sekilde calistirir."""
    executor = ToolExecutor(timeout or 30.0)
    return executor.calistir_tool(module_name, timeout=timeout, **(params or {}))


def run(**kwargs) -> str:
    """
    ToolExecutor'u calistirir.

    Args:
        **kwargs: Test parametreleri

    Returns:
        str: Test sonucu
    """
    try:
        executor = ToolExecutor()

        def test_tool(ad: str, sayi: int = 1) -> str:
            return f"Tool calisti: {ad}, sayi={sayi}"

        sonuc1 = executor.calistir(test_tool, ad="ornek", sayi=42)
        sonuc2 = executor.calistir_guvenli(test_tool, ad="guvenli", sayi=99)
        gecmis_liste = executor.gecmis()
        istatistik = executor.istatistik()

        return json.dumps({
            "sonuc1": sonuc1,
            "sonuc2": sonuc2,
            "gecmis_sayisi": len(gecmis_liste),
            "istatistik": istatistik,
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return f"Tool executor hatasi: {e}"
