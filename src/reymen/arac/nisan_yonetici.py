# -*- coding: utf-8 -*-
"""
nisan_yonetici.py — Nisan sablonu cikarma yoneticisi.

Iki yontem:
  1. OTONOM — DOM uzerinden otomatik tarama (otonom_nisan_olusturucu)
  2. MANUEL — Fare ile elle secim (nisan_yakala)

Kullanim:
    python nisan_yonetici.py
    -> Hangi yontem kullanilacak sorulur
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

PROJE_KOKU = Path(__file__).parent.resolve()


def main() -> None:
    print("=" * 55)
    print("  NISAN SABLONU CIKARMA YONETICI")
    print("=" * 55)
    print()
    print("Hedef: .ReYMeN/nisanlar/ klasorune .png sablonlari kaydetmek")
    print()
    print("Yontemler:")
    print("  1. OTONOM - DOM uzerinden otomatik tarama")
    print("     (Tor Browser acilir, elementler bulunur, kaydedilir)")
    print()
    print("  2. MANUEL - Fare ile elle secim")
    print("     (Fareyi hedef uzerine getir, ENTER'a bas, isim ver)")
    print()
    print("  3. IPTAL")
    print()

    secim = input("Secim [1/2/3]: ").strip()

    if secim == "1":
        print("\n[+] OTONOM mod secildi.")
        print("[i] Tor Browser acilacak, elementler taranacak...\n")
        subprocess.run([
            sys.executable,
            str(PROJE_KOKU / "otonom_nisan_olusturucu.py")
        ])

    elif secim == "2":
        print("\n[+] MANUEL mod secildi.")
        print("[i] Fareyi hedef uzerine getirip ENTER'a bas.")
        print("[i] Cikis icin ESC.\n")
        subprocess.run([
            sys.executable,
            str(PROJE_KOKU / "nisan_yakala.py")
        ])

    elif secim == "3":
        print("\n[-] Iptal edildi.")
        return

    else:
        print("\n[!] Gecersiz secim.")
        return

    print("\n[+] Islem tamam. .ReYMeN/nisanlar/ klasorunu kontrol edin.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
