# -*- coding: utf-8 -*-
"""
nisan_yakala.py — Ekranda fare altindaki UI elemanini kirpar ve nisan olarak kaydeder.

Kullanim:
    python nisan_yakala.py
    -> Fareyi hedef buton/alan uzerine getir, ENTER'a bas
    -> Onizleme gosterilir (2 sn)
    -> Konsol: "Nisan adi: " yazar, orn: "giris_buton" yazip ENTER
    -> .ReYMeN/nisanlar/giris_buton.png kaydedilir
    -> ESC ile cikis
"""

import os
import time
import ctypes
from pathlib import Path

import cv2
import mss
import numpy as np
import keyboard

# Dizin konfigurasyonu
PROJE_KOKU = Path(__file__).parent.resolve()
NISAN_DIZINI = PROJE_KOKU / ".ReYMeN" / "nisanlar"


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def fare_konumunu_oku():
    """Windows API ile anlik fare koordinatlarini dondurur."""
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def nisan_yakalayiciyi_baslat():
    NISAN_DIZINI.mkdir(parents=True, exist_ok=True)

    print("=" * 50)
    print("[NISAN YAKALAYICI AKTIF]")
    print(f"Hedef Dizin: {NISAN_DIZINI}")
    print("Kullanim: Fareyi hedef uzerine getir ve ENTER'a bas.")
    print("Cikis: ESC tusuna bas.")
    print("=" * 50)

    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Ana ekran

        while True:
            if keyboard.is_pressed('esc'):
                print("\n[!] Cikis saglandi.")
                break

            if keyboard.is_pressed('enter'):
                time.sleep(0.2)  # Cift tetiklenmeyi onle

                x, y = fare_konumunu_oku()

                # 80x80 px kirpma (40px offset)
                sol = max(0, x - 40)
                ust = max(0, y - 40)
                sag = min(monitor["width"], x + 40)
                alt = min(monitor["height"], y + 40)

                bbox = {"top": ust, "left": sol, "width": sag - sol, "height": alt - ust}

                # Yakala ve BGR'a cevir
                sct_img = sct.grab(bbox)
                img = np.array(sct_img)
                img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

                # Onizleme (2 sn)
                cv2.imshow("Nisan Onizleme (2 sn)", img_bgr)
                cv2.waitKey(2000)
                cv2.destroyAllWindows()

                time.sleep(0.1)

                # Isimlendirme ve kayit
                ad = input("\n[?] Nisan adi (bos = iptal): ").strip()
                if ad:
                    dosya_yolu = NISAN_DIZINI / f"{ad}.png"
                    cv2.imwrite(str(dosya_yolu), img_bgr)
                    print(f"[+] Kaydedildi: {dosya_yolu}\n")
                else:
                    print("[-] Iptal edildi.\n")

                print("[*] Yeni nisan icin fareyi konumlandirip ENTER'a bas (Cikis: ESC)...")


if __name__ == "__main__":
    nisan_yakalayiciyi_baslat()
