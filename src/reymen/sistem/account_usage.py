# -*- coding: utf-8 -*-
"""account_usage.py — Hesap Kullanim Gecmisi.

Provider bazinda kullanim gecmisi, aylik/ gunluk raporlar,
maliyet tahminleri ve limit uyarilari.
"""

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

USAGE_LOG = Path(__file__).parent / ".ReYMeN" / "usage"
USAGE_LOG.mkdir(parents=True, exist_ok=True)
RAPOR_DOSYASI = USAGE_LOG / "account_summary.json"


class AccountUsage:
    """Hesap kullanim takipcisi."""

    def __init__(self):
        self._veri = self._yukle()

    def _yukle(self) -> dict:
        if RAPOR_DOSYASI.exists():
            try:
                return json.loads(RAPOR_DOSYASI.read_text(encoding="utf-8"))
            except Exception as e:
                logger.debug("Usage JSON okunamadi, sifirlaniyor: %s", e)
        return {
            "olusturma": datetime.now().isoformat(),
            "toplam_istek": 0,
            "toplam_token": 0,
            "toplam_maliyet": 0.0,
            "providerlar": {},
            "aylik_veri": {},
        }

    def _kaydet(self):
        RAPOR_DOSYASI.write_text(json.dumps(self._veri, ensure_ascii=False, indent=2), encoding="utf-8")

    def ekle(self, provider: str, model: str, giris_token: int, cikis_token: int, maliyet: float):
        """Yeni kullanim kaydi ekle.

        Args:
            provider: Provider adi
            model: Model adi
            giris_token: Girdi token
            cikis_token: Cikti token
            maliyet: USD maliyet
        """
        # Genel toplam
        self._veri["toplam_istek"] += 1
        self._veri["toplam_token"] += giris_token + cikis_token
        self._veri["toplam_maliyet"] = round(self._veri["toplam_maliyet"] + maliyet, 4)

        # Provider bazli
        if provider not in self._veri["providerlar"]:
            self._veri["providerlar"][provider] = {"istek": 0, "token": 0, "maliyet": 0.0, "model": model}
        p = self._veri["providerlar"][provider]
        p["istek"] += 1
        p["token"] += giris_token + cikis_token
        p["maliyet"] = round(p["maliyet"] + maliyet, 4)

        # Aylik
        ay = date.today().isoformat()[:7]
        if ay not in self._veri["aylik_veri"]:
            self._veri["aylik_veri"][ay] = {"istek": 0, "token": 0, "maliyet": 0.0}
        a = self._veri["aylik_veri"][ay]
        a["istek"] += 1
        a["token"] += giris_token + cikis_token
        a["maliyet"] = round(a["maliyet"] + maliyet, 4)

        self._kaydet()

    def ozet(self) -> str:
        """Kullanim ozeti."""
        return (
            f"[Hesap Kullanim]\n"
            f"  Toplam istek: {self._veri['toplam_istek']}\n"
            f"  Toplam token: {self._veri['toplam_token']:,}\n"
            f"  Toplam maliyet: ${self._veri['toplam_maliyet']:.4f}\n"
            f"  Provider: {', '.join(self._veri['providerlar'].keys())}"
        )

    def provider_raporu(self, provider: str) -> str:
        """Bir provider icin detayli rapor."""
        p = self._veri["providerlar"].get(provider)
        if not p:
            return f"[Hesap] Provider kaydi yok: {provider}"
        return (
            f"[Hesap] {provider}\n"
            f"  Model: {p['model']}\n"
            f"  Istek: {p['istek']}\n"
            f"  Token: {p['token']:,}\n"
            f"  Maliyet: ${p['maliyet']:.4f}"
        )

    def aylik_rapor(self, yil_ay: str = "") -> str:
        """Belirli bir ayin raporu."""
        if not yil_ay:
            yil_ay = date.today().isoformat()[:7]
        a = self._veri["aylik_veri"].get(yil_ay)
        if not a:
            return f"[Hesap] Kayit yok: {yil_ay}"
        return (
            f"[Hesap] {yil_ay}\n"
            f"  Istek: {a['istek']}\n"
            f"  Token: {a['token']:,}\n"
            f"  Maliyet: ${a['maliyet']:.4f}"
        )

    def butce_uyarisi(self, aylik_limit: float = 10.0) -> str | None:
        """Butce asim uyarisi (aylik limit gecildiyse)."""
        ay = date.today().isoformat()[:7]
        a = self._veri["aylik_veri"].get(ay)
        if not a:
            return None
        if a["maliyet"] >= aylik_limit:
            return f"[Uyari] Aylik butce asildi! ${a['maliyet']:.2f} / ${aylik_limit:.2f}"
        if a["maliyet"] >= aylik_limit * 0.8:
            return f"[Uyari] Aylik butcenin %80'i kullanildi (${a['maliyet']:.2f}/${aylik_limit:.2f})"
        return None

    def sifirla(self):
        self._veri = {"olusturma": datetime.now().isoformat(), "toplam_istek": 0, "toplam_token": 0, "toplam_maliyet": 0.0, "providerlar": {}, "aylik_veri": {}}
        self._kaydet()


# Global instance
_hesap = AccountUsage()


def hesap_ekle(provider: str, model: str, giris_token: int, cikis_token: int, maliyet: float):
    _hesap.ekle(provider, model, giris_token, cikis_token, maliyet)


def hesap_ozet() -> str:
    return _hesap.ozet()


if __name__ == "__main__":
    h = AccountUsage()
    h.ekle("deepseek", "deepseek-chat", 500, 200, 0.0001)
    h.ekle("lmstudio", "dolphin3.0", 1000, 500, 0.0)
    print(h.ozet())
    print()
    print(h.butce_uyarisi(10.0) or "Butce normal")
