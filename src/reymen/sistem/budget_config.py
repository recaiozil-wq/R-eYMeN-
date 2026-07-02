# -*- coding: utf-8 -*-
"""
budget_config.py — Butce ayarlari.

Provider ve islem tiplerine gore butce yonetimi.
Her tip icin ayri limit, kullanim ve sifirlama destegi.

Kullanim:
    bc = BudgetConfig()
    bc.butce_ayarla("gunluk_token", 50000)
    bc.butce_kullan(15000)
    print(bc.kalan_butce("gunluk_token"))
"""

import os
import json
import time
import logging
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)


class BudgetConfig:
    """Butce yapilandirma ve kullanim takibi.

    Farkli butce tipleri (gunluk, haftalik, aylik, toplam)
    icin ayri ayri limit ve kullanim bilgisi tutar.

    Ornek kullanim:
        bc = BudgetConfig()
        bc.butce_ayarla("gunluk_api", 1000)
        bc.butce_kullan(250)  # 250 adet harca
        print(bc.kalan_butce("gunluk_api"))  # 750
    """

    VARSAYILAN_LIMITLER = {
        "gunluk_token": 100000,
        "gunluk_api": 1000,
        "haftalik_token": 500000,
        "aylik_maliyet": 50.0,
        "gunluk_dosya": 100,
    }

    def __init__(self, kayit_yolu: Optional[str] = None):
        """BudgetConfig sinifini baslat.

        Args:
            kayit_yolu: Opsiyonel, JSON kayit dosyasi yolu
        """
        self._kayit_yolu = kayit_yolu
        self._limitler: dict[str, float] = {}
        self._kullanim: dict[str, float] = {}
        self._baslangic_tarihi = date.today().isoformat()
        self._son_sifirlama = time.time()
        self._toplam_kullanim = 0.0
        self._uyari_esigi = 0.8  # %80 uyari

        # Varsayilan limitleri yukle
        for tip, limit in self.VARSAYILAN_LIMITLER.items():
            env_degiskeni = f"ReYMeN_BUDGET_{tip.upper()}"
            env_deger = os.environ.get(env_degiskeni)
            if env_deger:
                try:
                    self._limitler[tip] = float(env_deger)
                except ValueError:
                    self._limitler[tip] = limit
            else:
                self._limitler[tip] = limit

        logger.debug("BudgetConfig baslatildi. Limitler: %s", self._limitler)

    def butce_getir(self, tip: Optional[str] = None) -> dict:
        """Butce bilgilerini getir.

        Args:
            tip: Belirli bir tipin butcesi (None = tumu)

        Returns:
            Butce bilgisi sozlugu
        """
        try:
            if tip:
                if tip not in self._limitler:
                    return {"hata": f"'{tip}' tipi tanimli degil"}
                kullanim = self._kullanim.get(tip, 0)
                limit = self._limitler[tip]
                return {
                    "tip": tip,
                    "limit": limit,
                    "kullanim": kullanim,
                    "kalan": round(limit - kullanim, 2),
                    "yuzde": round(kullanim / limit * 100, 1) if limit > 0 else 0,
                }
            return {
                tip: {
                    "limit": lim,
                    "kullanim": self._kullanim.get(tip, 0),
                    "kalan": round(lim - self._kullanim.get(tip, 0), 2),
                }
                for tip, lim in self._limitler.items()
            }
        except Exception as e:
            logger.exception("Butce getirme hatasi")
            return {"hata": str(e)}

    def butce_ayarla(self, tip: str, limit: float) -> str:
        """Bir butce tipi icin limit belirle.

        Args:
            tip: Butce tipi (ornek: "gunluk_token", "aylik_maliyet")
            limit: Yeni limit degeri

        Returns:
            Islem sonucu mesaji
        """
        try:
            if limit < 0:
                return f"[BudgetConfig] Limit negatif olamaz: {limit}"
            self._limitler[tip] = float(limit)
            logger.info("Butce ayarlandi: %s = %s", tip, limit)
            return f"[BudgetConfig] '{tip}' limiti {limit} olarak ayarlandi."
        except Exception as e:
            logger.exception("Butce ayarlama hatasi")
            return f"[BudgetConfig] Ayar hatasi: {e}"

    def butce_kullan(self, adet: float, tip: str = "gunluk_token") -> str:
        """Belirtilen miktarda butce kullan.

        Args:
            adet: Kullanilacak miktar
            tip: Hangi butce tipinden kullanilacak

        Returns:
            Islem sonucu mesaji (limit asimi uyarisi dahil)
        """
        try:
            if adet < 0:
                return f"[BudgetConfig] Negatif kullanim: {adet}"

            if tip not in self._limitler:
                return f"[BudgetConfig] '{tip}' tipi tanimli degil. once butce_ayarla() cagir."

            onceki = self._kullanim.get(tip, 0)
            yeni = onceki + adet
            limit = self._limitler[tip]

            if yeni > limit:
                self._kullanim[tip] = yeni
                asim = round(yeni - limit, 2)
                self._toplam_kullanim += adet
                return (f"[BudgetConfig] UYARI: '{tip}' limiti asildi! "
                        f"{onceki}/{limit} -> {yeni} (asim: {asim})")

            self._kullanim[tip] = yeni
            self._toplam_kullanim += adet

            # Uyari esigi kontrolu
            kalan_yuzde = (limit - yeni) / limit * 100 if limit > 0 else 0
            mesaj = f"[BudgetConfig] '{tip}' kullanildi: {onceki} -> {yeni}/{limit} (%{round(100 - kalan_yuzde, 1)})"
            if kalan_yuzde < (1 - self._uyari_esigi) * 100:
                mesaj += " [UYARI: Limit yaklasiyor!]"

            logger.debug(mesaj)
            return mesaj
        except Exception as e:
            logger.exception("Butce kullanim hatasi")
            return f"[BudgetConfig] Kullanim hatasi: {e}"

    def kalan_butce(self, tip: str) -> float:
        """Belirtilen tip icin kalan butceyi hesapla.

        Args:
            tip: Butce tipi

        Returns:
            Kalan butce miktari. Tip yoksa 0.0 doner.
        """
        try:
            if tip not in self._limitler:
                logger.warning("Bilinmeyen butce tipi: %s", tip)
                return 0.0
            return round(self._limitler[tip] - self._kullanim.get(tip, 0), 2)
        except Exception as e:
            logger.exception("Kalan butce hesaplama hatasi")
            return 0.0

    def sifirla(self, tip: Optional[str] = None) -> str:
        """Butce kullanimini sifirla.

        Args:
            tip: Sifirlanacak tip (None = tumu)

        Returns:
            Islem sonucu mesaji
        """
        try:
            if tip:
                if tip in self._kullanim:
                    onceki = self._kullanim[tip]
                    self._kullanim[tip] = 0
                    return f"[BudgetConfig] '{tip}' sifirlandi (onceki: {onceki})."
                return f"[BudgetConfig] '{tip}' icin kullanim verisi yok."
            else:
                toplam = sum(self._kullanim.values())
                self._kullanim.clear()
                self._toplam_kullanim = 0
                self._son_sifirlama = time.time()
                return f"[BudgetConfig] Tum butceler sifirlandi (onceki toplam: {toplam})."
        except Exception as e:
            logger.exception("Sifirlama hatasi")
            return f"[BudgetConfig] Sifirlama hatasi: {e}"

    def liste_tipleri(self) -> list:
        """Tanimli butce tiplerini listele.

        Returns:
            Tip listesi
        """
        return list(self._limitler.keys())

    def ozet(self) -> dict:
        """Butce ozet raporu.

        Returns:
            Ozet sozlugu
        """
        try:
            return {
                "toplam_kullanim": self._toplam_kullanim,
                "aktif_limitler": len(self._limitler),
                "baslangic_tarihi": self._baslangic_tarihi,
                "son_sifirlama": datetime.fromtimestamp(self._son_sifirlama).isoformat(),
                "tipler": self.butce_getir(),
            }
        except Exception as e:
            return {"hata": str(e)}

    def provider_maliyeti(self, provider: str, miktar: float) -> float:
        """Provider maliyetini hesapla (varsayilan: miktari aynen don)."""
        return miktar


def run(**kwargs) -> str:
    """BudgetConfig sinifini calistir.

    Args:
        **kwargs: Su parametreler desteklenir:
            - islem: "butce_getir", "butce_ayarla", "butce_kullan",
                    "kalan_butce", "sifirla", "liste", "ozet"
            - tip: Butce tipi
            - limit: Limit degeri (butce_ayarla icin)
            - adet: Kullanim miktari (butce_kullan icin)

    Returns:
        Islem sonucu metni
    """
    try:
        bc = BudgetConfig()
        islem = kwargs.get("islem", "ozet")
        tip = kwargs.get("tip", "")
        limit = kwargs.get("limit")

        if islem == "butce_getir":
            sonuc = bc.butce_getir(tip if tip else None)
            return json.dumps(sonuc, ensure_ascii=False, indent=2)
        elif islem == "butce_ayarla":
            return bc.butce_ayarla(tip, limit or 0)
        elif islem == "butce_kullan":
            return bc.butce_kullan(adet=kwargs.get("adet", 0), tip=tip)
        elif islem == "kalan_butce":
            return str(bc.kalan_butce(tip))
        elif islem == "sifirla":
            return bc.sifirla(tip if tip else None)
        elif islem == "liste":
            return ", ".join(bc.liste_tipleri())
        else:
            return json.dumps(bc.ozet(), ensure_ascii=False, indent=2)
    except Exception as e:
        return f"[BudgetConfig] Calistirma hatasi: {e}"


if __name__ == "__main__":
    print("=== BudgetConfig Test ===")
    bc = BudgetConfig()
    print(bc.butce_ayarla("gunluk_token", 50000))
    print(bc.butce_kullan(15000, "gunluk_token"))
    print(bc.butce_kullan(25000, "gunluk_token"))
    print(f"Kalan: {bc.kalan_butce('gunluk_token')}")
    print(bc.butce_getir("gunluk_token"))
    print(bc.sifirla("gunluk_token"))
    print(json.dumps(bc.ozet(), ensure_ascii=False, indent=2))
    print("=== Test Tamam ===")
