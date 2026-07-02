# -*- coding: utf-8 -*-
"""
araclar_makro.py — Makro kaydet/oynat (TinyTask mantığı).
"Beni takip et" -> fare/klavye olaylarını zaman damgasıyla kaydeder.
"Oynat" -> kaydı aynı sırayla tekrar eder.

Kayıtlar JSON olarak saklanır; her uygulama/proje için ayrı dosya.
Bağımlılık: pynput (kayıt için), pyautogui (oynatma için). Opsiyonel.

DİKKAT: Bu KÖR tekrardır — aynı koordinatlara aynı sırayla tıklar.
Pencere yeri/boyutu değişirse kayıt bozulabilir. Ekran-OCR-Tıkla daha dayanıklıdır.
"""
import json
import os
import time
import logging
logger = logging.getLogger(__name__)

try:
    from pynput import mouse, keyboard
    PYNPUT_OK = True
except Exception:
    PYNPUT_OK = False

try:
    import pyautogui
    PYAUTOGUI_OK = True
except Exception:
    PYAUTOGUI_OK = False


class MakroKaydedici:
    def __init__(self, kayit_dizini=".ReYMeN/makrolar"):
        self.kayit_dizini = kayit_dizini
        os.makedirs(kayit_dizini, exist_ok=True)
        self._olaylar = []
        self._baslangic = None
        self._mouse_listener = None
        self._kb_listener = None

    def kaydi_baslat(self):
        """Fare/klavye dinleyicilerini başlatır."""
        if not PYNPUT_OK:
            return "[Makro]: pynput kurulu değil (pip install pynput)."
        self._olaylar = []
        self._baslangic = time.time()

        def on_click(x, y, button, pressed):
            if pressed:
                self._olaylar.append({"t": time.time() - self._baslangic,
                                      "tip": "click", "x": x, "y": y, "buton": str(button)})

        def on_press(key):
            self._olaylar.append({"t": time.time() - self._baslangic,
                                  "tip": "tus", "key": str(key)})

        self._mouse_listener = mouse.Listener(on_click=on_click)
        self._kb_listener = keyboard.Listener(on_press=on_press)
        self._mouse_listener.start()
        self._kb_listener.start()
        return "[Makro]: Kayıt başladı. 'kaydi_durdur(ad)' ile bitir."

    def kayda_basla(self):
        """kaydi_baslat() icin kisayol alias."""
        return self.kaydi_baslat()

    def kaydi_durdur(self, makro_adi):
        """Dinleyicileri durdurur ve kaydı dosyaya yazar."""
        if self._mouse_listener:
            self._mouse_listener.stop()
        if self._kb_listener:
            self._kb_listener.stop()
        yol = os.path.join(self.kayit_dizini, f"{makro_adi}.json")
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(self._olaylar, f, ensure_ascii=False, indent=2)
        return f"[Makro]: '{makro_adi}' kaydedildi ({len(self._olaylar)} olay) -> {yol}"

    def oynat(self, makro_adi, hiz=1.0):
        """Kayıtlı makroyu aynı zamanlamayla tekrar eder."""
        if not PYAUTOGUI_OK:
            return "[Makro]: pyautogui kurulu değil."
        yol = os.path.join(self.kayit_dizini, f"{makro_adi}.json")
        if not os.path.exists(yol):
            return f"[Makro]: '{makro_adi}' bulunamadı."
        with open(yol, "r", encoding="utf-8") as f:
            olaylar = json.load(f)

        onceki_t = 0
        for olay in olaylar:
            bekle = (olay["t"] - onceki_t) / hiz
            if bekle > 0:
                time.sleep(min(bekle, 5))  # güvenlik: max 5sn bekleme
            onceki_t = olay["t"]
            if olay["tip"] == "click":
                pyautogui.click(olay["x"], olay["y"])
            elif olay["tip"] == "tus":
                tus = olay["key"].replace("'", "").replace("Key.", "")
                try:
                    pyautogui.press(tus)
                except Exception as _araclar__e97:
                    print(f"[UYARI] araclar_makro.py:98 - {_araclar__e97}")
        return f"[Makro]: '{makro_adi}' oynatıldı ({len(olaylar)} olay)."

    def makro_listesi(self):
        dosyalar = [f[:-5] for f in os.listdir(self.kayit_dizini) if f.endswith(".json")]
        return dosyalar


def motor_kaydet(motor):
    """Makro araçlarını motora kaydet."""
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return
    _mk = MakroKaydedici()
    motor._plugin_arac_kaydet(
        "MAKRO_OYNAT_ADI",
        lambda ad="": _mk.oynat(str(ad)),
        "Kayıtlı makroyu çalıştır (ad: makro adı)",
    )
    motor._plugin_arac_kaydet(
        "MAKRO_LISTESI",
        lambda: str(_mk.makro_listesi()),
        "Kayıtlı makro listesini göster",
    )


if __name__ == "__main__":
    m = MakroKaydedici(kayit_dizini="/tmp/ReYMeN_makro")
    print("MakroKaydedici hazir (pynput:%s, pyautogui:%s)" % (PYNPUT_OK, PYAUTOGUI_OK))
    print("Kayitli makrolar:", m.makro_listesi())
