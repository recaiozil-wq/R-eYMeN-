# -*- coding: utf-8 -*-
"""path_security.py — Yol Guvenligi.

Dosya yollarini dogrular, path traversal ve sembolik link
saldirilarina karsi korur.
"""

import os
from pathlib import Path

# Proje kok dizini (guvenli bolge)
PROJE_KOK = Path(__file__).parent.resolve()


def yol_dogrula(hedef_yol: str) -> tuple[bool, str]:
    """Bir yolun guvenli bolge icinde olup olmadigini dogrula.

    Args:
        hedef_yol: Dogrulanacak yol

    Returns:
        (gecerli_mi, normalize_edilmis_yol_veya_hata)
    """
    try:
        yol = Path(hedef_yol).resolve()
    except Exception as e:
        return False, f"Gecersiz yol: {e}"

    # Path traversal: yol proje kokunun disina cikiyor mu?
    try:
        yol.relative_to(PROJE_KOK)
    except ValueError:
        # Proje kokunun disinda - izin verilen ozel dizinler var mi?
        izinli_ozel = [
            Path.home() / ".ReYMeN",
            Path.home() / "AppData/Local/hermes",
        ]
        for izin in izinli_ozel:
            try:
                yol.relative_to(izin)
                return True, str(yol)
            except ValueError:
                continue
        return False, f"Guvenli bolge disi: {yol}"

    return True, str(yol)


def sembolik_link_kontrol(yol: str) -> tuple[bool, str]:
    """Sembolik link kontrolu.

    Args:
        yol: Kontrol edilecek yol

    Returns:
        (guvenli_mi, gercek_yol)
    """
    p = Path(yol)
    if p.is_symlink():
        gercek = p.resolve()
        try:
            gercek.relative_to(PROJE_KOK)
            return True, str(gercek)
        except ValueError:
            return False, f"Symlink guvenli bolge disina isaret ediyor: {gercek}"
    return True, str(p)


if __name__ == "__main__":
    testler = ["test.txt", "../disari.txt", __file__]
    for t in testler:
        gecerli, mesaj = yol_dogrula(t)
        print(f"  {t}: {'Gecerli' if gecerli else 'Gecersiz'} -> {mesaj}")
