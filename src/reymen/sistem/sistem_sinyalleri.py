# -*- coding: utf-8 -*-
"""
sistem_sinyalleri.py — Sistem sinyalleri.

SignalHandler sinifi ile isletim sistemi sinyallerini (SIGINT, SIGTERM vb.)
dinler, kaydeder ve uygun sekilde yonetir. Graceful shutdown ve restart
ozelliklerini saglar.
"""

import os
import sys
import signal
import time
import threading
import traceback
from typing import Optional, Dict, Any, Callable
import logging
logger = logging.getLogger(__name__)


class SignalHandler:
    """
    Sistem sinyal yoneticisi.

    Isletim sistemi sinyallerini (SIGINT, SIGTERM, SIGHUP vb.)
    dinler, kaydedilen handler fonksiyonlarini calistirir.
    Graceful shutdown ve restart islemlerini yonetir.

    Kullanim:
        sh = SignalHandler()
        sh.kaydet(signal.SIGINT, lambda: print("Kapatiliyor..."))
        sh.bekle()
    """

    def __init__(self):
        """
        SignalHandler baslatici.
        """
        self._handlerlar: Dict[int, Callable] = {}
        self._orijinal_handlerlar: Dict[int, Any] = {}
        self._kapatma_istegi = threading.Event()
        self._yeniden_baslatma_istegi = threading.Event()
        self._kilit = threading.Lock()
        self._aktif = False
        self._kapatma_fonksiyonlari: list = []
        self._threadler: list = []

    def kaydet(self, sinyal: int, handler: Callable) -> bool:
        """
        Bir sinyal icin handler fonksiyonu kaydeder.

        Desteklenen sinyaller: SIGINT (2), SIGTERM (15), SIGHUP (1),
        SIGUSR1 (10), SIGUSR2 (12).

        Args:
            sinyal: Sinyal numarasi (signal.SIGINT, signal.SIGTERM vb.).
            handler: Sinyal alindiginda calistirilacak fonksiyon.

        Returns:
            Basarili mi?
        """
        try:
            with self._kilit:
                # Kapatma isteginden sonra yeni kayit engelle
                if self._kapatma_istegi.is_set():
                    return False

                # Orijinal handler'i kaydet (ilk kayit icin)
                if sinyal not in self._orijinal_handlerlar:
                    self._orijinal_handlerlar[sinyal] = signal.getsignal(sinyal)

                self._handlerlar[sinyal] = handler

                # Sinyal handler'ini ayarla
                signal.signal(sinyal, self._sinyal_alindi)

                return True
        except ValueError as e:
            print(f"[Signal] Sinyal kaydi hatasi ({sinyal}): {e}")
            return False
        except Exception as e:
            print(f"[Signal] Beklenmeyen hata: {e}")
            return False

    def _sinyal_alindi(self, signum: int, frame) -> None:
        """
        Sinyal alindiginda cagrilir.

        Kayitli handler'lari calistirir. SIGINT/SIGTERM'de kapatma
        istegini tetikler.

        Args:
            signum: Alinan sinyal numarasi.
            frame: Mevcut yigin cercevesi.
        """
        try:
            print(f"\n[Signal] Sinyal alindi: {signum} ({signal.Signals(signum).name})")

            # Kayitli handler'i calistir
            handler = self._handlerlar.get(signum)
            if handler:
                try:
                    handler()
                except Exception as e:
                    print(f"[Signal] Handler hatasi: {e}")
                    traceback.print_exc()

            # Kapatma sinyalleri
            if signum in (signal.SIGINT, signal.SIGTERM):
                self._kapatma_istegi.set()
                print("[Signal] Guvenli kapatma baslatiliyor...")
                self.graceful_shutdown()

            # Yeniden baslatma sinyali (Windows'ta SIGHUP yok)
            sighup = getattr(signal, 'SIGHUP', None)
            if sighup is not None and signum == sighup:
                self._yeniden_baslatma_istegi.set()
                print("[Signal] Yeniden baslatma baslatiliyor...")
                self.restart()

            # Orijinal handler'a yonlendir
            orijinal = self._orijinal_handlerlar.get(signum)
            if orijinal and callable(orijinal) and orijinal != signal.SIG_DFL:
                if orijinal != signal.SIG_IGN:
                    try:
                        orijinal(signum, frame)
                    except BaseException as _sistem_s_e124:
                        print(f"[UYARI] sistem_sinyalleri.py:125 - {_sistem_s_e124}")

        except Exception as e:
            print(f"[Signal] Sinyal isleme hatasi: {e}")

    def bekle(self, timeout: Optional[float] = None) -> bool:
        """
        Kapatma veya yeniden baslatma sinyali gelene kadar bekler.

        Ana thread'i bloke eder. Ctrl+C veya SIGTERM ile kapatilabilir.

        Args:
            timeout: Maksimum bekleme suresi (saniye). None ise sinirsiz.

        Returns:
            True: kapatma istegi alindi.
            False: yeniden baslatma istegi alindi veya timeout.
        """
        try:
            self._aktif = True
            print("[Signal] Bekleniyor... (Ctrl+C ile kapatabilirsiniz)")

            if timeout:
                self._kapatma_istegi.wait(timeout)
            else:
                # Sonsuz bekle, sinyaller keser
                while not self._kapatma_istegi.is_set() and not self._yeniden_baslatma_istegi.is_set():
                    self._kapatma_istegi.wait(1.0)

            self._aktif = False

            if self._kapatma_istegi.is_set():
                return True
            if self._yeniden_baslatma_istegi.is_set():
                return False
            return False

        except Exception as e:
            print(f"[Signal] Bekleme hatasi: {e}")
            return False

    def graceful_shutdown(self, temizlik_fonksiyonu: Optional[Callable] = None) -> bool:
        """
        Guvenli kapatma islemini baslatir.

        Kayitli thread'leri bekler, temizlik fonksiyonlarini calistirir
        ve kaynaklari serbest birakir.

        Args:
            temizlik_fonksiyonu: Kapatma sirasinda calistirilacak ozel fonksiyon.

        Returns:
            Basarili mi?
        """
        try:
            print("[Shutdown] Guvenli kapatma basliyor...")

            # Ozel temizlik fonksiyonu
            if temizlik_fonksiyonu:
                try:
                    temizlik_fonksiyonu()
                    print("[Shutdown] Temizlik fonksiyonu calistirildi.")
                except Exception as e:
                    print(f"[Shutdown] Temizlik hatasi: {e}")

            # Kayitli kapatma fonksiyonlari
            for fn in self._kapatma_fonksiyonlari:
                try:
                    fn()
                except Exception as e:
                    print(f"[Shutdown] Kapatma fonksiyonu hatasi: {e}")

            # Thread'leri bekle
            aktif_threadler = [t for t in self._threadler if t.is_alive()]
            if aktif_threadler:
                print(f"[Shutdown] {len(aktif_threadler)} thread bekleniyor...")
                for t in aktif_threadler:
                    t.join(timeout=3.0)

            # Orijinal sinyal handler'larini geri yukle
            for sinyal, orijinal in self._orijinal_handlerlar.items():
                try:
                    signal.signal(sinyal, orijinal)
                except Exception as _sistem_s_e208:
                    print(f"[UYARI] sistem_sinyalleri.py:209 - {_sistem_s_e208}")

            self._kapatma_istegi.set()
            self._aktif = False
            print("[Shutdown] Guvenli kapatma tamamlandi.")
            return True

        except Exception as e:
            print(f"[Shutdown] Kritik hata: {e}")
            return False

    def restart(self) -> bool:
        """
        Uygulamayi yeniden baslatir.

        Mevcut sureci sonlandirip ayni komutla yeniden baslatir.
        Sadece SIGHUP sinyali ile calisir.

        Returns:
            Basarili mi?
        """
        try:
            print("[Restart] Yeniden baslatma basliyor...")

            # Temizlik yap
            self.graceful_shutdown()

            # Yeniden baslatma istegini ayarla
            self._yeniden_baslatma_istegi.set()

            # Ayni komutla yeniden baslat
            python = sys.executable
            script = sys.argv[0] if sys.argv else ""
            args = sys.argv[1:] if len(sys.argv) > 1 else []

            if script and os.path.exists(script):
                print(f"[Restart] Yeniden baslatiliyor: {python} {script}")
                os.execv(python, [python, script] + args)
            else:
                print("[Restart] Script yolu bulunamadi, cikiliyor.")
                sys.exit(0)

            return True

        except Exception as e:
            print(f"[Restart] Yeniden baslatma hatasi: {e}")
            return False

    def kapatma_ekle(self, fonk: Callable) -> bool:
        """
        Kapatma sirasinda calistirilacak fonksiyon ekler.

        Args:
            fonk: Kapatmada calistirilacak fonksiyon.

        Returns:
            Basarili mi?
        """
        try:
            self._kapatma_fonksiyonlari.append(fonk)
            return True
        except Exception as e:
            print(f"[Signal] Kapatma fonksiyonu ekleme hatasi: {e}")
            return False

    def thread_ekle(self, thread: threading.Thread) -> bool:
        """
        Kapatmada beklenecek thread ekler.

        Args:
            thread: Beklenecek thread.

        Returns:
            Basarili mi?
        """
        try:
            self._threadler.append(thread)
            return True
        except Exception as e:
            print(f"[Signal] Thread ekleme hatasi: {e}")
            return False

    def durum(self) -> Dict[str, Any]:
        """
        SignalHandler durumunu dondurur.

        Returns:
            Kayitli sinyaller, durum bilgisi.
        """
        try:
            kayitli_sinyaller = {}
            for sinyal_no in self._handlerlar:
                try:
                    ad = signal.Signals(sinyal_no).name
                except Exception:
                    ad = f"Sinyal-{sinyal_no}"
                kayitli_sinyaller[sinyal_no] = ad

            return {
                "aktif": self._aktif,
                "kayitli_sinyal": len(self._handlerlar),
                "sinyaller": kayitli_sinyaller,
                "kapatma_fonksiyonu": len(self._kapatma_fonksiyonlari),
                "izlenen_thread": len(self._threadler),
                "kapatma_istegi_var": self._kapatma_istegi.is_set(),
                "yeniden_baslatma_istegi_var": self._yeniden_baslatma_istegi.is_set(),
            }
        except Exception as e:
            return {"hata": str(e)}

    def run(self, **kwargs) -> str:
        """
        Evrensel calistirma metodu.

        kwargs icinde:
            - action: "kaydet", "bekle", "graceful_shutdown", "restart",
                      "kapatma_ekle", "durum"
            - Diger parametreler ilgili metoda yonlendirilir.

        Returns:
            JSON formatinda sonuc.
        """
        import json as json_mod
        try:
            action = kwargs.pop("action", "durum")
            if action == "kaydet":
                sinyal = kwargs.get("sinyal", signal.SIGINT)
                handler = kwargs.get("handler")
                if handler:
                    basarili = self.kaydet(sinyal, handler)
                else:
                    basarili = False
                return json_mod.dumps({"basarili": basarili}, ensure_ascii=False)
            elif action == "bekle":
                timeout = kwargs.get("timeout")
                sonuc = self.bekle(timeout=timeout)
                return json_mod.dumps({"kapatma_istegi": sonuc}, ensure_ascii=False)
            elif action == "graceful_shutdown":
                sonuc = self.graceful_shutdown()
                return json_mod.dumps({"basarili": sonuc}, ensure_ascii=False)
            elif action == "restart":
                sonuc = self.restart()
                return json_mod.dumps({"basarili": sonuc}, ensure_ascii=False)
            elif action == "kapatma_ekle":
                # run icinden fonk eklenemez
                return json_mod.dumps({"basarili": False, "hata": "Run uzerinden eklenemez"}, ensure_ascii=False)
            elif action == "durum":
                return json_mod.dumps(self.durum(), ensure_ascii=False, indent=2, default=str)
            else:
                return json_mod.dumps({"hata": f"Bilinmeyen action: {action}"}, ensure_ascii=False)
        except Exception as e:
            return json_mod.dumps({"hata": str(e)}, ensure_ascii=False)


def motor_kaydet(motor):
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return

    def _sistem_kaynak():
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.3)
            ram = psutil.virtual_memory().percent
            return f"CPU: {cpu:.1f}%  RAM: {ram:.1f}%"
        except ImportError:
            return "[Kaynak]: psutil kurulu degil."

    motor._plugin_arac_kaydet(
        "SISTEM_KAYNAK",
        lambda: _sistem_kaynak(),
        "CPU ve RAM kullanim yuzdesini goster",
    )
    motor._plugin_arac_kaydet(
        "SINYAL_DURUM",
        lambda: SignalHandler().run(action="durum"),
        "Sistem sinyal yoneticisi durumunu goster",
    )


if __name__ == "__main__":
    sh = SignalHandler()
    print("SignalHandler hazir.")

    # Test handler
    sh.kaydet(signal.SIGINT, lambda: print("SIGINT alindi!"))
    print("Sinyaller:", sh.durum())
    print("Ctrl+C ile test edebilirsiniz...")
    print("Bekleniyor...")
    # Test icin timeout'lu bekle
    sonuc = sh.bekle(timeout=5)
    print(f"Sonuc: {'Kapatma' if sonuc else 'Timeout/yeniden baslatma'}")
