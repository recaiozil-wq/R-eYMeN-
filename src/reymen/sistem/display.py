# -*- coding: utf-8 -*-
"""
display.py — Goruntuleme sistemi.

Renkli cikti, progress bar ve tablo formatlama
islevlerini saglar.
"""

import os
import sys
import time
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


_ANSI = {
    "kalin": "\033[1m",
    "soluk": "\033[2m",
    "italik": "\033[3m",
    "altcizgi": "\033[4m",
    "yanip_sonder": "\033[5m",
    "sifirla": "\033[0m",
    "kirmizi": "\033[91m",
    "yesil": "\033[92m",
    "sari": "\033[93m",
    "mavi": "\033[94m",
    "magenta": "\033[95m",
    "cyan": "\033[96m",
    "beyaz": "\033[97m",
    "siyah": "\033[90m",
    "mor": "\033[95m",
    "turkuaz": "\033[96m",
    "koyu_kirmizi": "\033[31m",
    "koyu_yesil": "\033[32m",
    "koyu_sari": "\033[33m",
    "koyu_mavi": "\033[34m",
    "koyu_mor": "\033[35m",
    "koyu_turkuaz": "\033[36m",
    "koyu_beyaz": "\033[37m",
}


class Display:
    """
    Goruntuleme sistemi.

    Renkli terminal ciktisi, progress bar ve
    tablo formatlama islemlerini yapar.
    """

    RENKLER = {
        "kirmizi": "\033[91m",
        "yesil": "\033[92m",
        "sari": "\033[93m",
        "mavi": "\033[94m",
        "mor": "\033[95m",
        "magenta": "\033[95m",
        "turkuaz": "\033[96m",
        "cyan": "\033[96m",
        "beyaz": "\033[97m",
        "siyah": "\033[90m",
        "koyu_kirmizi": "\033[31m",
        "koyu_yesil": "\033[32m",
        "koyu_sari": "\033[33m",
        "koyu_mavi": "\033[34m",
        "koyu_mor": "\033[35m",
        "koyu_turkuaz": "\033[36m",
        "koyu_beyaz": "\033[37m",
    }

    STILLER = {
        "kalin": "\033[1m",
        "soluk": "\033[2m",
        "italik": "\033[3m",
        "altcizgi": "\033[4m",
        "yanip_sonder": "\033[5m",
    }

    BITIS = "\033[0m"

    def __init__(self, renkli: bool = True):
        """
        Display baslatici.

        Args:
            renkli: Renkli cikti kullanilsin mi
        """
        self._renkli = renkli
        self._satir_genisligi = self._terminal_genislik()
        self._progress_aktif = False

    def _terminal_genislik(self) -> int:
        """Terminal genisligini dondurur."""
        try:
            import shutil
            return shutil.get_terminal_size().columns
        except Exception:
            return 80

    def renkli_yaz(
        self,
        metin: str,
        renk: str = "",
        kalin: bool = False,
        stiller: Optional[List[str]] = None,
        yeni_satir: bool = True,
        son: Optional[str] = None,
    ) -> None:
        """
        Renkli metin yazdirir.

        Args:
            metin: Yazdirilacak metin
            renk: Renk adi (bos = renksiz)
            kalin: Kalin yaz
            stiller: Ekstra stil listesi (kalin, italik vb.)
            yeni_satir: Sonuna newline ekle (son parametresi varsa geçersiz)
            son: print() end parametresi (yeni_satir yerine kullanilir)
        """
        try:
            end = son if son is not None else ("\n" if yeni_satir else "")

            renk_kodu = self.RENKLER.get(renk, "") if renk else ""
            stil_kodu = self.STILLER.get("kalin", "") if kalin else ""
            if stiller:
                for s in stiller:
                    stil_kodu += self.STILLER.get(s, "")

            if not self._renkli or not (renk_kodu or stil_kodu):
                print(metin, end=end)
                return

            cikti = f"{stil_kodu}{renk_kodu}{metin}{self.BITIS}"
            print(cikti, end=end)

        except Exception as e:
            logger.error(f"Renkli yazma hatasi: {e}")
            print(metin)

    def tablo(
        self,
        basliklar: List[str],
        satirlar: List[List[str]],
        baslik_renk: str = "mavi",
        satir_renk: str = "beyaz",
        ayrac: str = " | ",
        sinir: bool = True,
    ) -> str:
        """
        Tablo formatinda cikti olusturur.

        Args:
            basliklar: Sutun basliklari
            satirlar: Satir verileri
            baslik_renk: Baslik rengi
            satir_renk: Satir rengi
            ayrac: Sutun ayraci

        Returns:
            str: Tablo metni
        """
        try:
            if not basliklar:
                return ""

            # Sutun genisliklerini hesapla
            sutun_say = len(basliklar)
            genislikler = [len(h) for h in basliklar]

            for satir in satirlar:
                for i, hucre in enumerate(satir):
                    if i < sutun_say:
                        genislikler[i] = max(genislikler[i], len(str(hucre)))

            # Baslik satiri
            cizgi = "+"
            for g in genislikler:
                cizgi += "-" * (g + 2) + "+"

            satirlar_cikti = [cizgi]

            # Basliklar
            baslik_satiri = "| "
            for i, h in enumerate(basliklar):
                baslik_satiri += h.ljust(genislikler[i]) + " | "
            satirlar_cikti.append(baslik_satiri)
            satirlar_cikti.append(cizgi)

            # Veri satirlari
            for satir in satirlar:
                veri_satiri = "| "
                for i in range(sutun_say):
                    hucre = str(satir[i]) if i < len(satir) else ""
                    veri_satiri += hucre.ljust(genislikler[i]) + " | "
                satirlar_cikti.append(veri_satiri)

            if sinir:
                satirlar_cikti.append(cizgi)

            # Birlestir ve yazdir
            sonuc = "\n".join(satirlar_cikti)

            if self._renkli:
                self._renkli_tablo_yaz(sonuc, baslik_renk, satir_renk)
            else:
                print(sonuc)

            return sonuc

        except Exception as e:
            logger.error(f"Tablo hatasi: {e}")
            return ""

    def _renkli_tablo_yaz(
        self,
        tablo_metni: str,
        baslik_renk: str,
        satir_renk: str
    ) -> None:
        """Renkli tablo yazdirir."""
        try:
            satirlar = tablo_metni.split("\n")
            for i, satir in enumerate(satirlar):
                if i == 1:
                    self.renkli_yaz(satir, baslik_renk, stiller=["kalin"])
                else:
                    self.renkli_yaz(satir, satir_renk)
        except Exception:
            print(tablo_metni)

    def progress_bar(
        self,
        ilerleme: int,
        toplam: int,
        genislik: int = 40,
        baslik: str = ""
    ) -> str:
        """
        Progress bar gosterir.

        Args:
            ilerleme: Mevcut ilerleme
            toplam: Toplam deger
            genislik: Bar genisligi
            baslik: Baslik metni

        Returns:
            str: Progress bar metni
        """
        try:
            if toplam <= 0:
                bar = f"[{'.' * genislik}] 0%"
                if baslik:
                    bar = f"{baslik}: {bar}"
                print(bar)
                return bar

            oran = ilerleme / toplam
            dolu = int(genislik * oran)
            bos = genislik - dolu

            yuzde = oran * 100
            yuzde_str = "100%" if ilerleme >= toplam else f"{yuzde:.0f}%"

            bar = f"[{'#' * dolu}{'.' * bos}] {yuzde_str}"
            if baslik:
                bar = f"{baslik}: {bar}"
            bar += f" ({ilerleme}/{toplam})"

            self._progress_aktif = True

            if sys.stdout.isatty():
                sys.stdout.write("\r" + bar)
                sys.stdout.flush()

                if ilerleme >= toplam:
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    self._progress_aktif = False
            else:
                print(bar)

            return bar

        except Exception as e:
            logger.error(f"Progress bar hatasi: {e}")
            return ""

    def baslik_goster(self, metin: str, seviye: int = 1) -> None:
        """Baslik gosterir."""
        try:
            sembol = "#" * seviye
            self.renkli_yaz(f"{sembol} {metin}", "mavi", stiller=["kalin"])
        except Exception as e:
            print(f"{'#' * seviye} {metin}")

    def ayrac_goster(self, karakter: str = "=", renk: str = "sari") -> None:
        """Ayrac cizgisi gosterir."""
        try:
            self.renkli_yaz(karakter * self._satir_genisligi, renk)
        except Exception:
            print(karakter * 60)

    def json_goster(self, veri: Any, baslik: str = "") -> None:
        """JSON formatinda veri gosterir."""
        try:
            if baslik:
                self.baslik_goster(baslik, 2)
            cikti = json.dumps(veri, ensure_ascii=False, indent=2)
            self.renkli_yaz(cikti, "turkuaz")
        except Exception as e:
            logger.error(f"JSON gosterim hatasi: {e}")


def run(**kwargs) -> str:
    """
    Display'i calistirir.

    Args:
        **kwargs: Test parametreleri

    Returns:
        str: Test sonucu
    """
    try:
        d = Display(renkli=False)
        d.baslik_goster("Display Testi")
        d.ayrac_goster("-")

        tablo_str = d.tablo(
            ["ID", "Ad", "Durum"],
            [
                ["1", "Test A", "Aktif"],
                ["2", "Test B", "Pasif"],
                ["3", "Test C", "Beklemede"],
            ],
        )

        bar = d.progress_bar(7, 10, baslik="Islem")
        d.renkli_yaz("Test basarili!", "yesil")

        return f"Tablo olusturuldu ({len(tablo_str)} karakter). Progress: {bar}"

    except Exception as e:
        return f"Display hatasi: {e}"
