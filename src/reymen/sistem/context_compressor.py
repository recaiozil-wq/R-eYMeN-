# -*- coding: utf-8 -*-
"""
context_compressor.py — Baglam sikistirma modulu.

Konusma gecmisini sikistirir, onemli bilgileri korur
ve ozet olusturur.
"""

import re
import json
import time
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ContextCompressor:
    """
    Baglam sikistirici.

    Konusma gecmisini token limitine gore sikistirir,
    onemli bilgileri saklar ve ozetler olusturur.
    """

    def __init__(self, max_token: int = 4096):
        """
        ContextCompressor baslatici.

        Args:
            max_token: Maksimum token sayisi
        """
        self._max_token = max_token
        self._onemli_bilgiler: Dict[str, Any] = {}
        self._ozet_gecmisi: List[Dict[str, Any]] = []
        self._etiket_puani: Dict[str, float] = {}

    def sikistir(
        self,
        gecmis: List[Dict[str, Any]],
        max_token: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Konusma gecmisini sikistirir.

        Args:
            gecmis: Konusma mesajlari listesi
            max_token: Maksimum token sayisi

        Returns:
            list: Sikistirilmis gecmis
        """
        try:
            limit = max_token or self._max_token

            if not gecmis:
                return []

            # Once ozet ekle
            ozet = self.ozet_olustur(gecmis)
            sikistirilmis = [{"rol": "sistem", "icerik": f"[OZET] {ozet}", "sikistirilmis": True}]

            # Onemli bilgileri ekle
            if self._onemli_bilgiler:
                onemli_str = json.dumps(self._onemli_bilgiler, ensure_ascii=False)
                sikistirilmis.append({
                    "rol": "sistem",
                    "icerik": f"[ONEMLI] {onemli_str}",
                    "sikistirilmis": True,
                })

            # Son mesajlari ekle (token limitine kadar)
            mevcut_token = self._token_hesapla(sikistirilmis)
            for mesaj in reversed(gecmis[-10:]):
                mesaj_token = self._token_hesapla([mesaj])
                if mevcut_token + mesaj_token > limit:
                    break
                sikistirilmis.append(mesaj)
                mevcut_token += mesaj_token

            logger.info(
                f"Gecmis sikistirildi: {len(gecmis)} -> {len(sikistirilmis)} mesaj"
            )
            return sikistirilmis

        except Exception as e:
            logger.error(f"Sikistirma hatasi: {e}")
            return gecmis[-5:] if gecmis else []

    def _token_hesapla(self, mesajlar: List[Dict[str, Any]]) -> int:
        """Basit token sayisi hesaplar (karakter / 4)."""
        try:
            toplam = 0
            for m in mesajlar:
                icerik = m.get("icerik", "") if isinstance(m, dict) else str(m)
                toplam += len(str(icerik)) // 4 + 1
            return toplam
        except Exception:
            return len(mesajlar) * 10

    def onemli_bilgileri_sakla(
        self,
        anahtar_ya_dict,
        deger=None,
        etiket: Optional[str] = None
    ) -> None:
        """
        Onemli bilgileri saklar.

        Iki kullanim bicimi:
          onemli_bilgileri_sakla("anahtar", deger)     -> dogrudan key/value
          onemli_bilgileri_sakla({"k": "v"}, etiket=X) -> sozluk, prefix ile
        """
        try:
            if isinstance(anahtar_ya_dict, dict):
                # Eski API: sozluk + opsiyonel etiket prefix'i
                prefix = etiket or f"bilgi_{int(time.time())}"
                for k, v in anahtar_ya_dict.items():
                    self._onemli_bilgiler[f"{prefix}.{k}"] = v
                self._etiket_puani[prefix] = 1.0
            else:
                # Yeni API: (anahtar, deger) cifti
                self._onemli_bilgiler[anahtar_ya_dict] = deger
                self._etiket_puani[str(anahtar_ya_dict)] = 1.0

            logger.debug(f"Onemli bilgi saklandi: {anahtar_ya_dict}")

        except Exception as e:
            logger.error(f"Bilgi saklama hatasi: {e}")

    def ozet_olustur(
        self,
        gecmis: List[Dict[str, Any]],
        max_karakter: int = 500
    ) -> str:
        """
        Konusma gecmisinin ozetini olusturur.

        Args:
            gecmis: Konusma mesajlari
            max_karakter: Maksimum ozet uzunlugu

        Returns:
            str: Ozet metni
        """
        try:
            if not gecmis:
                return "Henuz mesaj yok."

            # Mesaj turlerini say
            kullanici_say = sum(1 for m in gecmis if isinstance(m, dict) and m.get("rol") == "kullanici")
            asistan_say = sum(1 for m in gecmis if isinstance(m, dict) and m.get("rol") == "asistan")
            sistem_say = sum(1 for m in gecmis if isinstance(m, dict) and m.get("rol") == "sistem")

            # Ilk ve son mesajlari al
            ilk_mesaj = ""
            son_mesaj = ""
            for m in gecmis:
                if isinstance(m, dict) and m.get("icerik"):
                    ilk_mesaj = m["icerik"][:100]
                    break
            for m in reversed(gecmis):
                if isinstance(m, dict) and m.get("icerik"):
                    son_mesaj = m["icerik"][:100]
                    break

            # Anahtar kelimeleri cikar
            anahtar_kelimeler = self._anahtar_kelime_cikar(gecmis)

            # Ozet olustur
            ozet_parcalari = [
                f"Toplam {len(gecmis)} mesaj",
                f"({kullanici_say} kullanici, {asistan_say} asistan, {sistem_say} sistem)",
                f"Konu: {ilk_mesaj}",
                f"Son: {son_mesaj}",
            ]

            if anahtar_kelimeler:
                ozet_parcalari.append(f"Anahtar kelimeler: {', '.join(anahtar_kelimeler[:10])}")

            ozet = " | ".join(ozet_parcalari)

            if len(ozet) > max_karakter:
                ozet = ozet[:max_karakter] + "..."

            # Ozet gecmisine ekle
            self._ozet_gecmisi.append({
                "ozet": ozet,
                "mesaj_sayisi": len(gecmis),
                "zaman": time.time(),
            })

            return ozet

        except Exception as e:
            logger.error(f"Ozet hatasi: {e}")
            return "Ozet olusturulamadi."

    def _anahtar_kelime_cikar(self, gecmis: List[Dict[str, Any]]) -> List[str]:
        """Metinden anahtar kelimeleri cikarir."""
        try:
            tum_metin = " ".join(
                str(m.get("icerik", "")) for m in gecmis
                if isinstance(m, dict) and m.get("icerik")
            )

            # Turkce stop words
            stop_words = {
                "bir", "bu", "ve", "veya", "ile", "icin", "ama", "ancak",
                "olarak", "olan", "daha", "en", "cok", "kadar", "gibi",
                "kendi", "diger", "her", "tum", "bazi", "arasinda",
                "sonra", "once", "yani", "uzere", "de", "da", "mi", "mu",
            }

            kelimeler = re.findall(r'\w+', tum_metin.lower())
            kelime_say = {}
            for k in kelimeler:
                if len(k) > 2 and k not in stop_words:
                    kelime_say[k] = kelime_say.get(k, 0) + 1

            sirali = sorted(kelime_say.items(), key=lambda x: -x[1])
            return [k for k, v in sirali[:20]]

        except Exception as e:
            logger.error(f"Anahtar kelime hatasi: {e}")
            return []

    def onemli_bilgileri_getir(self) -> Dict[str, Any]:
        """Saklanan onemli bilgileri dondurur."""
        return dict(self._onemli_bilgiler)

    def temizle(self) -> None:
        """Tum bilgileri temizler."""
        self._onemli_bilgiler.clear()
        self._ozet_gecmisi.clear()
        self._etiket_puani.clear()

    def istatistik(self) -> Dict[str, Any]:
        """Istatistik bilgilerini dondurur."""
        return {
            "onemli_bilgi_sayisi": len(self._onemli_bilgiler),
            "ozet_sayisi": len(self._ozet_gecmisi),
            "max_token": self._max_token,
        }


def run(**kwargs) -> str:
    """
    ContextCompressor'i calistirir.

    Args:
        **kwargs: Test parametreleri

    Returns:
        str: Test sonucu
    """
    try:
        compressor = ContextCompressor()
        gecmis = kwargs.get("gecmis", [
            {"rol": "kullanici", "icerik": "Merhaba, nasilsin?"},
            {"rol": "asistan", "icerik": "Iyiyim, tesekkurler. Sana nasil yardimci olabilirim?"},
            {"rol": "kullanici", "icerik": "Python ile dosya islemleri yapmak istiyorum."},
            {"rol": "asistan", "icerik": "Python'da dosya islemleri icin open() fonksiyonunu kullanabilirsin."},
        ])

        sikistirilmis = compressor.sikistir(gecmis)
        ozet = compressor.ozet_olustur(gecmis)
        compressor.onemli_bilgileri_sakla({"kullanici_adi": "test_user"})

        return json.dumps({
            "orijinal_sayi": len(gecmis),
            "sikistirilmis_sayi": len(sikistirilmis),
            "ozet": ozet,
            "onemli_bilgiler": compressor.onemli_bilgileri_getir(),
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return f"Context compressor hatasi: {e}"
