# -*- coding: utf-8 -*-
"""
insan_arayuzu.py — Kullanıcı arayüzü.

HumanInterface sinifi ile konsol tabanli kullanici arayuzu
bilesenleri sunar. Progress bar, kullanici girdisi, onay
diyalogu ve tablo gosterimi saglar.
"""

import os
import sys
import time
import shutil
from typing import Optional, List, Dict, Any, Tuple


class HumanInterface:
    """
    Kullanici arayuzu.

    Konsol tabanli ilerleme cubugu, kullanici girdisi, onay
    mesaji ve tablo gosterimi gibi arayuz bilesenlerini saglar.

    Kullanim:
        ui = HumanInterface()
        ui.progress_bar(mevcut=5, toplam=10, baslik="Isleniyor")
        secim = ui.input("Devam et?", secenekler=["e", "h"])
    """

    def __init__(self, genislik: int = 50, sembol: str = "=", bos_sembol: str = "."):
        """
        HumanInterface baslatici.

        Args:
            genislik: Progress bar genisligi (karakter sayisi).
            sembol: Dolu kisim sembolu.
            bos_sembol: Bos kisim sembolu.
        """
        self.genislik = genislik
        self._genislik = genislik  # alias (eski/test uyumlulugu)
        self.sembol = sembol
        self.bos_sembol = bos_sembol
        self._konsol_genislik = self._konsol_boyut()

    def _konsol_boyut(self) -> int:
        """
        Konsol genisligini dondurur.

        Returns:
            Konsol genisligi (karakter). Bulunamazsa 80.
        """
        try:
            boyut = shutil.get_terminal_size()
            return boyut.columns
        except Exception:
            return 80

    def progress_bar(self, mevcut: int, toplam: int, baslik: str = "",
                     goster_yuzde: bool = True, goster_sayi: bool = True) -> str:
        """
        Konsolda ilerleme cubugu gosterir.

        Args:
            mevcut: Su anki adim.
            toplam: Toplam adim sayisi.
            baslik: Cubuk basligi.
            goster_yuzde: Yuzde gosterilsin mi?
            goster_sayi: Sayi bilgisi gosterilsin mi?

        Returns:
            Olusturulan ilerleme cubugu metni.
        """
        try:
            if toplam <= 0:
                return "[Progress: gecersiz deger]"

            yuzde = min(100, max(0, (mevcut / toplam) * 100))
            dolu = int((yuzde / 100) * self.genislik)
            bos = self.genislik - dolu

            bar = self.sembol * dolu + self.bos_sembol * bos

            parcalar = []
            if baslik:
                parcalar.append(baslik)
            parcalar.append(f"[{bar}]")
            if goster_yuzde:
                parcalar.append(f"%{yuzde:.1f}")
            if goster_sayi:
                parcalar.append(f"({mevcut}/{toplam})")

            cikti = " ".join(parcalar)

            # Konsol satirina yaz
            if sys.stdout.isatty():
                sys.stdout.write("\r" + cikti)
                sys.stdout.flush()
                if mevcut >= toplam:
                    sys.stdout.write("\n")
                    sys.stdout.flush()

            return cikti

        except Exception as e:
            return f"[Progress hatasi: {e}]"

    def input(self, prompt: str, secenekler: Optional[List[str]] = None,
              varsayilan: str = "", zorunlu: bool = False) -> str:
        """
        Kullanicidan girdi alir.

        Args:
            prompt: Kullaniciya gosterilecek metin.
            secenekler: Gecerli secenekler listesi. Verilirse secim kontrolu yapar.
            varsayilan: Varsayilan deger.
            zorunlu: True ise bos girdi kabul edilmez.

        Returns:
            Kullanici girdisi.
        """
        try:
            while True:
                # Prompt olustur
                tam_prompt = prompt
                if secenekler:
                    secim_str = "/".join(
                        f"[{s}]" if s.lower() == varsayilan.lower() else s
                        for s in secenekler
                    )
                    tam_prompt = f"{prompt} ({secim_str})"
                if varsayilan:
                    tam_prompt = f"{tam_prompt} [{varsayilan}]"
                tam_prompt += ": "

                try:
                    girdi = input(tam_prompt).strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    return varsayilan or ""

                # Varsayilan kullan
                if not girdi and varsayilan:
                    return varsayilan

                # Zorunlu kontrol
                if zorunlu and not girdi:
                    print("[Hata] Bu alan zorunludur.")
                    continue

                # Secenek kontrolu
                if secenekler and girdi:
                    eslenen = [s for s in secenekler if s.lower() == girdi.lower()]
                    if not eslenen:
                        print(f"[Hata] Gecersiz secenek. Gecerli: {', '.join(secenekler)}")
                        continue
                    return eslenen[0].lower()

                return girdi

        except Exception as e:
            print(f"[Input hatasi: {e}]")
            return varsayilan or ""

    def onay(self, mesaj: str, varsayilan: bool = True) -> bool:
        """
        Kullanicidan onay alir.

        REYMEN_OTOMATIK_ONAY=true ise direkt True döner (kullanıcıya sormaz).
        ReYMeN Agent'ın approvals.mode=off / Allow Once pattern'i ile aynı.

        Args:
            mesaj: Onay mesaji.
            varsayilan: Varsayilan deger (True=e, False=h).

        Returns:
            True (onaylandi) veya False (reddedildi).
        """
        # Otomatik onay: .env'de REYMEN_OTOMATIK_ONAY=true ise direkt onayla
        if os.environ.get("REYMEN_OTOMATIK_ONAY", "").lower() in ("true", "1", "yes"):
            return True

        try:
            vars_str = "E/h" if varsayilan else "e/H"
            tam_mesaj = f"{mesaj} ({vars_str})"

            try:
                girdi = input(tam_mesaj + ": ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return varsayilan

            if not girdi:
                return varsayilan
            if girdi in ("e", "evet", "yes", "y", "1"):
                return True
            if girdi in ("h", "hayir", "no", "n", "0"):
                return False
            return varsayilan

        except Exception as e:
            print(f"[Onay hatasi: {e}]")
            return varsayilan

    def tablo(self, veri: List[Dict[str, Any]], basliklar: Optional[List[str]] = None,
              max_sutun: int = 80) -> str:
        """
        Veriyi tablo formatinda gosterir.

        Args:
            veri: Sozluk listesi (her sozluk bir satir).
            basliklar: Goruntulenecek sutun basliklari. None ise tum anahtarlar.
            max_sutun: Maksimum sutun genisligi.

        Returns:
            Tablo metni.
        """
        try:
            if not veri:
                return "[Tablo: veri yok]"

            # Basliklari belirle
            if not basliklar:
                basliklar = list(veri[0].keys())

            # Sutun genisliklerini hesapla
            sutun_genislikleri = {}
            for baslik in basliklar:
                max_genislik = len(str(baslik))
                for satir in veri:
                    deger = str(satir.get(baslik, ""))
                    max_genislik = max(max_genislik, min(len(deger), max_sutun))
                sutun_genislikleri[baslik] = min(max_genislik + 2, max_sutun + 2)

            # Toplam genislik kontrolu
            toplam_genislik = sum(sutun_genislikleri.values()) + len(basliklar) + 1
            if toplam_genislik > self._konsol_genislik:
                # Sutunlari kis
                oran = (self._konsol_genislik - len(basliklar) - 1) / sum(sutun_genislikleri.values())
                for baslik in basliklar:
                    sutun_genislikleri[baslik] = max(5, int(sutun_genislikleri[baslik] * oran))

            # Ayrac satiri
            ayrac = "+" + "+".join("-" * w for w in sutun_genislikleri.values()) + "+"

            satirlar = [ayrac]

            # Baslik satiri
            baslik_satiri = "|"
            for baslik in basliklar:
                baslik_satiri += baslik.center(sutun_genislikleri[baslik]) + "|"
            satirlar.append(baslik_satiri)
            satirlar.append(ayrac)

            # Veri satirlari
            for satir in veri:
                veri_satiri = "|"
                for baslik in basliklar:
                    deger = str(satir.get(baslik, ""))
                    if len(deger) > sutun_genislikleri[baslik] - 1:
                        deger = deger[:sutun_genislikleri[baslik] - 4] + "..."
                    veri_satiri += " " + deger.ljust(sutun_genislikleri[baslik] - 1) + "|"
                satirlar.append(veri_satiri)

            satirlar.append(ayrac)

            cikti = "\n".join(satirlar)
            print(cikti)
            return cikti

        except Exception as e:
            hata = f"[Tablo hatasi: {e}]"
            print(hata)
            return hata

    def menu(self, baslik: str, secenekler: List[Tuple[str, str]],
             aciklama: str = "") -> str:
        """
        Kullaniciya menu gosterir ve secim yaptirir.

        Args:
            baslik: Menu basligi.
            secenekler: (anahtar, aciklama) tuple listesi.
            aciklama: Menu aciklamasi.

        Returns:
            Secilen anahtar.
        """
        try:
            print(f"\n=== {baslik} ===")
            if aciklama:
                print(aciklama)
            print()

            for i, (anahtar, aciklama_sec) in enumerate(secenekler, 1):
                print(f"  {i}. {aciklama_sec}")

            print()
            while True:
                try:
                    girdi = input(f"Seciminiz (1-{len(secenekler)}): ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    return secenekler[0][0] if secenekler else ""

                if girdi.isdigit():
                    indeks = int(girdi) - 1
                    if 0 <= indeks < len(secenekler):
                        return secenekler[indeks][0]

                # Anahtar ile de secilebilir
                for anahtar, _ in secenekler:
                    if girdi.lower() == anahtar.lower():
                        return anahtar

                print(f"Gecersiz secim. 1-{len(secenekler)} arasi girin.")

        except Exception as e:
            print(f"[Menu hatasi: {e}]")
            return secenekler[0][0] if secenekler else ""

    def onay_iste(self, baslik: str, mesaj: str) -> bool:
        """Windows MessageBox veya konsol onay diyalogu.

        Args:
            baslik: Pencere / konsol basligı
            mesaj:  Kullaniciya gosterilecek mesaj

        Returns:
            True: onaylandi, False: reddedildi
        """
        try:
            import ctypes
            # MB_YESNO=4, MB_ICONQUESTION=0x20; IDYES=6
            sonuc = ctypes.windll.user32.MessageBoxW(0, mesaj, baslik, 4 | 0x20)
            return sonuc == 6
        except Exception:
            print(f"\n[{baslik}]\n{mesaj}")
            return self.onay("Onayliyor musunuz?")

    def run(self, **kwargs) -> str:
        """
        Evrensel calistirma metodu.

        kwargs icinde:
            - action: "progress_bar", "input", "onay", "tablo", "menu"
            - Diger parametreler ilgili metoda yonlendirilir.

        Returns:
            Metin ciktisi.
        """
        try:
            action = kwargs.pop("action", "progress_bar")
            if action == "progress_bar":
                return self.progress_bar(**kwargs)
            elif action == "input":
                return self.input(**kwargs)
            elif action == "onay":
                return str(self.onay(**kwargs))
            elif action == "tablo":
                return self.tablo(**kwargs)
            elif action == "menu":
                return self.menu(**kwargs)
            else:
                return f"[UI] Bilinmeyen action: {action}"
        except Exception as e:
            return f"[UI] run hatasi: {e}"


if __name__ == "__main__":
    ui = HumanInterface()
    print("HumanInterface hazir.")

    # Test progress bar
    for i in range(1, 11):
        ui.progress_bar(mevcut=i, toplam=10, baslik="Test")
        time.sleep(0.05)
    print()

    # Test tablo
    ui.tablo(
        veri=[
            {"isim": "Ali", "yas": 30, "sehir": "Istanbul"},
            {"isim": "Ayse", "yas": 25, "sehir": "Ankara"},
        ]
    )

# Eski ad uyumlulugu
InsanArayuzu = HumanInterface
