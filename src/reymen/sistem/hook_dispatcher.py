# -*- coding: utf-8 -*-
"""
hook_dispatcher.py — Olay dagitici.

TOOL_CALLED, TOOL_ERROR gibi hook olaylarini
dinler ve kayitli fonksiyonlari tetikler.
"""

import time
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Cereyan hook API'sini import et — aynı arayüz, class+fonksiyon
from src.reymen.cereyan.hook_dispatcher import (  # noqa: F401
    hook_kaydet, hook_kaldir, hook_cagir, tum_hooklari_temizle,
    kayitli_hooklar, hook, oturum_baslat_tetikle, oturum_bitir_tetikle,
    tur_baslat_tetikle, tur_bitir_tetikle, arac_cagri_tetikle,
    arac_sonuc_tetikle, hata_tetikle, context_sikistirma_tetikle,
)


class HookDispatcher:
    """Olay dagitici.

    Uygulama icindeki olaylari (hook'lari) dinler ve
    kayitli callback fonksiyonlarini tetikler.
    """

    def __init__(self, max_workers=4):
        """HookDispatcher baslatma.

        Args:
            max_workers: Ayni anda calisacak maksimum is parcacigi
        """
        self._hooks = defaultdict(list)
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._aktif = True
        self._istatistik = defaultdict(int)

    def kaydet(self, olay, fn):
        """Bir olay icin callback fonksiyonu kaydet.

        Args:
            olay: Olay adi (ornek: "on_tool_call", "TOOL_CALLED")
            fn: Callback fonksiyonu

        Returns:
            Basarili mesaj veya hata mesaji
        """
        try:
            if not callable(fn):
                return "[HookDispatcher] fn cagrilabilir olmali."
            # Ayni anda kendi havuzuna ve cereyan API'sina kaydet
            if fn not in self._hooks[olay]:
                self._hooks[olay].append(fn)
            # Cereyan API'sina da kaydet (konusma dongusu ile uyum)
            try:
                from reymen.cereyan.hook_dispatcher import hook_kaydet as _hk
                _hk(olay, fn)
            except Exception as _e:
                __import__("logging").getLogger(__name__).warning(
                    "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                )
            logger.info(f"Hook kaydedildi: {olay} -> {fn.__name__}")
            return f"[HookDispatcher] '{olay}' icin {fn.__name__} kaydedildi."
        except Exception as e:
            logger.exception("Hook kayit hatasi")
            return f"[HookDispatcher] Kayit hatasi: {e}"

    def kaldir(self, olay, fn):
        """Bir olay icin kayitli callback fonksiyonunu kaldir.

        Args:
            olay: Olay adi
            fn: Kaldirilacak callback fonksiyonu

        Returns:
            Basarili mesaj veya hata mesaji
        """
        try:
            if olay not in self._hooks:
                return f"[HookDispatcher] '{olay}' icin hook bulunamadi."

            if fn in self._hooks[olay]:
                self._hooks[olay].remove(fn)
                logger.info(f"Hook kaldirildi: {olay} -> {fn.__name__}")
                return f"[HookDispatcher] '{olay}' icin {fn.__name__} kaldirildi."
            else:
                return f"[HookDispatcher] {fn.__name__} bu olayda kayitli degil."

        except Exception as e:
            logger.exception("Hook kaldirma hatasi")
            return f"[HookDispatcher] Kaldirma hatasi: {e}"

    def tetikle(self, olay, **data):
        """Bir olayi tetikle ve kayitli tum callback'leri calistir.

        Args:
            olay: Tetiklenecek olay adi
            **data: Callback'lere gonderilecek veri

        Returns:
            Sonuc metni veya hata mesaji
        """
        try:
            if not self._aktif:
                return "[HookDispatcher] Dagitic kapali."

            if olay not in self._hooks or not self._hooks[olay]:
                return f"[HookDispatcher] '{olay}' icin hook yok."

            fonsiyonlar = self._hooks[olay]
            self._istatistik[olay] += 1
            basarili = 0
            basarisiz = 0

            # Callback'leri paralel calistir
            futures = {}
            for fn in fonsiyonlar:
                try:
                    future = self._executor.submit(self._guvenli_calistir, fn, olay, data)
                    futures[future] = fn
                except Exception as e:
                    logger.error(f"{fn.__name__} baslatilamadi: {e}")
                    basarisiz += 1

            # Sonuclari topla
            for future in as_completed(futures, timeout=30):
                fn = futures[future]
                try:
                    sonuc = future.result(timeout=5)
                    if sonuc:
                        basarili += 1
                    else:
                        basarisiz += 1
                except Exception as e:
                    logger.error(f"{fn.__name__} sonuc hatasi: {e}")
                    basarisiz += 1

            return (
                f"[HookDispatcher] '{olay}' tetiklendi: "
                f"{basarili} basarili, {basarisiz} basarisiz"
            )

        except Exception as e:
            logger.exception("Tetikleme hatasi")
            return f"[HookDispatcher] Tetikleme hatasi: {e}"

    def _guvenli_calistir(self, fn, olay, data):
        """Bir callback'i try/except ile guvenli calistir.

        Args:
            fn: Callback fonksiyonu
            olay: Olay adi
            data: Veri sozlugu

        Returns:
            True basarili, False basarisiz
        """
        try:
            fn(olay=olay, **data)
            return True
        except Exception as e:
            logger.error(
                f"Hook hatasi [{olay}/{fn.__name__}]: {e}"
            )
            return False

    def listele(self, olay=None):
        """Kayitli hook'lari listele.

        Args:
            olay: Filtre olay adi (opsiyonel)

        Returns:
            Hook listesi metni
        """
        try:
            if olay:
                if olay not in self._hooks:
                    return f"[HookDispatcher] '{olay}' icin hook yok."
                olaylar = {olay: self._hooks[olay]}
            else:
                olaylar = dict(self._hooks)

            if not olaylar:
                return "[HookDispatcher] Kayitli hook yok."

            liste = []
            for o, fns in sorted(olaylar.items()):
                fn_isimleri = [fn.__name__ for fn in fns]
                istatistik = self._istatistik.get(o, 0)
                liste.append(
                    f"  {o} ({istatistik} tetikleme): {', '.join(fn_isimleri)}"
                )

            return "[HookDispatcher] Kayitli hooklar:\n" + "\n".join(liste)

        except Exception as e:
            logger.exception("Listeleme hatasi")
            return f"[HookDispatcher] Listeleme hatasi: {e}"

    def temizle(self, olay=None):
        """Hook'lari temizle.

        Args:
            olay: Belirli bir olayi temizle (None ise tumu)

        Returns:
            Basarili mesaj
        """
        try:
            if olay:
                adet = len(self._hooks.get(olay, []))
                self._hooks[olay] = []
                return f"[HookDispatcher] '{olay}' icin {adet} hook temizlendi."
            else:
                toplam = sum(len(v) for v in self._hooks.values())
                self._hooks.clear()
                return f"[HookDispatcher] {toplam} hook temizlendi."
        except Exception as e:
            return f"[HookDispatcher] Temizleme hatasi: {e}"

    def kapat(self):
        """Dagiticini kapat ve kaynaklari temizle.

        Returns:
            Basarili mesaj
        """
        try:
            self._aktif = False
            self._executor.shutdown(wait=False)
            return "[HookDispatcher] Dagitic kapatildi."
        except Exception as e:
            return f"[HookDispatcher] Kapatma hatasi: {e}"


# Motor uyumlulugu icin alias
AsynchronousHookDispatcher = HookDispatcher


def run(**kwargs):
    """HookDispatcher uzerinden islem yap.

    Args:
        islem: "kaydet", "kaldir", "tetikle", "listele"
        olay: Olay adi
        fn: Callback fonksiyonu (kaydet/kaldir icin)
        data: Tetikleme verisi (tetikle icin)

    Returns:
        Islem sonucu metni
    """
    try:
        dispatcher = HookDispatcher()
        islem = kwargs.get("islem", "listele")

        if islem == "kaydet":
            return dispatcher.kaydet(
                kwargs.get("olay", ""),
                kwargs.get("fn", None),
            )
        elif islem == "kaldir":
            return dispatcher.kaldir(
                kwargs.get("olay", ""),
                kwargs.get("fn", None),
            )
        elif islem == "tetikle":
            return dispatcher.tetikle(
                kwargs.get("olay", ""),
                **kwargs.get("data", {}),
            )
        else:
            return dispatcher.listele()

    except Exception as e:
        logger.exception("run hatasi")
        return f"[HookDispatcher] run hatasi: {e}"


if __name__ == "__main__":
    def ornek_hook(olay=None, **data):
        print(f"Hook calisti: {olay}, data={data}")

    d = HookDispatcher()
    d.kaydet("TEST", ornek_hook)
    print(d.listele())
    print(d.tetikle("TEST", mesaj="merhaba"))
