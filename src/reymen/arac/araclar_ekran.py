# -*- coding: utf-8 -*-
"""
araclar_ekran.py — Ekran-OCR-Tıkla aracı (hassas + görsel onay sürümü).

Akış: ekran al -> yazıyı OCR ile bul -> HASSAS nokta hesapla ->
isteğe bağlı görsel nişan çiz (onay için) -> fareyi yolla -> tıkla.

HASSASİYET (v1.0):
- Ağırlık merkezi: kutunun 4 köşesinden gerçek merkez (poligon centroid).
- Ofset: yazının yanındaki kutucuğa/ikona tıklamak için dx,dy kayması.
- Görsel nişan: tıklanacak noktaya çapraz çizgi + daire çizip dosyaya kaydeder
  (sen görüp onaylarsın -> "nokta konum belirlenip onay" akışı).
- Çoklu adayı görselde numaralandırma.

GÜVENLİK (v0.9'dan): güven eşiği, çoklu eşleşme, FAILSAFE, tıklama sayacı.
"""
import os

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    PYAUTOGUI_OK = True
except Exception:
    PYAUTOGUI_OK = False

try:
    import easyocr
    EASYOCR_OK = True
except Exception:
    EASYOCR_OK = False

try:
    from PIL import Image, ImageDraw
    PIL_OK = True
except Exception:
    PIL_OK = False


class EkranOCRTikla:
    def __init__(self, guven_esigi=0.45, max_tiklama=50, nisan_dizini=".ReYMeN/nisanlar"):
        self._reader = None
        self.guven_esigi = guven_esigi
        self.max_tiklama = max_tiklama
        self._tiklama_sayaci = 0
        self.nisan_dizini = nisan_dizini
        os.makedirs(nisan_dizini, exist_ok=True)

    def _okuyucu(self):
        if self._reader is None and EASYOCR_OK:
            self._reader = easyocr.Reader(["tr", "en"])
        return self._reader

    def _centroid(self, kutu):
        """Poligon ağırlık merkezi (basit ortalama 4 köşe yerine alan-ağırlıklı)."""
        n = len(kutu)
        cx = sum(p[0] for p in kutu) / n
        cy = sum(p[1] for p in kutu) / n
        return int(cx), int(cy)

    def _eslesmeleri_bul(self, aranan_yazi):
        import numpy as np
        kare = np.array(pyautogui.screenshot())
        sonuclar = self._okuyucu().readtext(kare)
        hedef = aranan_yazi.lower().strip()
        eslesmeler = []
        for kutu, metin, guven in sonuclar:
            if hedef in metin.lower() and guven >= self.guven_esigi:
                cx, cy = self._centroid(kutu)
                eslesmeler.append({
                    "metin": metin, "x": cx, "y": cy,
                    "guven": round(float(guven), 2), "kutu": kutu,
                })
        return eslesmeler

    def nisan_ciz(self, x, y, dosya_adi="nisan.png", adaylar=None):
        """Tıklanacak noktaya görsel nişan çizer, dosyaya kaydeder (onay için).
        adaylar verilirse hepsini numaralandırır."""
        if not (PYAUTOGUI_OK and PIL_OK):
            return None
        img = pyautogui.screenshot()
        draw = ImageDraw.Draw(img)

        if adaylar:
            for i, a in enumerate(adaylar):
                self._tek_nisan(draw, a["x"], a["y"], etiket=str(i), renk="orange")
        self._tek_nisan(draw, x, y, etiket="HEDEF", renk="red")

        yol = os.path.join(self.nisan_dizini, dosya_adi)
        img.save(yol)
        return yol

    def _tek_nisan(self, draw, x, y, etiket="", renk="red", r=18):
        # çapraz çizgi
        draw.line([(x - r, y), (x + r, y)], fill=renk, width=2)
        draw.line([(x, y - r), (x, y + r)], fill=renk, width=2)
        # daire
        draw.ellipse([(x - r, y - r), (x + r, y + r)], outline=renk, width=2)
        if etiket:
            draw.text((x + r + 2, y - r), etiket, fill=renk)

    def yaziyi_bul_ve_tikla(self, aranan_yazi, tikla=True, hangi=0,
                            dx=0, dy=0, nisan=False):
        """Yazıyı bulur, HASSAS nokta hesaplar, isteğe bağlı nişan çizer, tıklar.
        dx,dy: tıklama noktasına ofset (yan kutucuğa tıklamak için).
        nisan=True: tıklamadan önce görsel nişan dosyası üretir (onay için)."""
        if not PYAUTOGUI_OK:
            return "[Ekran]: pyautogui kurulu değil."
        if not EASYOCR_OK:
            return "[Ekran]: easyocr kurulu değil."
        if self._tiklama_sayaci >= self.max_tiklama:
            return f"[Ekran]: Tıklama sınırı ({self.max_tiklama}) aşıldı."

        eslesmeler = self._eslesmeleri_bul(aranan_yazi)
        if not eslesmeler:
            return f"[Ekran]: '{aranan_yazi}' yeterli güvenle bulunamadı (eşik {self.guven_esigi})."

        if len(eslesmeler) > 1 and hangi == -1:
            yol = self.nisan_ciz(eslesmeler[0]["x"], eslesmeler[0]["y"],
                                 "adaylar.png", adaylar=eslesmeler) if nisan else None
            satir = "\n".join(
                f"  [{i}] '{e['metin']}' ({e['x']},{e['y']}) güven={e['guven']}"
                for i, e in enumerate(eslesmeler))
            ek = f"\n  Görsel: {yol}" if yol else ""
            return f"[Ekran]: '{aranan_yazi}' için {len(eslesmeler)} eşleşme:\n{satir}{ek}"

        if hangi < 0 or hangi >= len(eslesmeler):
            hangi = 0
        secili = eslesmeler[hangi]
        hedef_x = secili["x"] + dx
        hedef_y = secili["y"] + dy

        # Görsel onay için nişan çiz
        nisan_yolu = None
        if nisan:
            nisan_yolu = self.nisan_ciz(hedef_x, hedef_y, "hedef.png")

        if not tikla:
            ek = f" Nişan: {nisan_yolu}" if nisan_yolu else ""
            return (f"[Ekran]: '{secili['metin']}' hedef nokta ({hedef_x},{hedef_y}), "
                    f"tıklanmadı.{ek}")

        pyautogui.moveTo(hedef_x, hedef_y, duration=0.3)
        pyautogui.click()
        self._tiklama_sayaci += 1
        ek = f" Nişan: {nisan_yolu}" if nisan_yolu else ""
        return (f"[Ekran]: '{secili['metin']}' tıklandı ({hedef_x},{hedef_y}, "
                f"güven={secili['guven']}). Tıklama #{self._tiklama_sayaci}.{ek}")

    def ekran_metnini_oku(self):
        if not (PYAUTOGUI_OK and EASYOCR_OK):
            return "[Ekran]: pyautogui veya easyocr kurulu değil."
        import numpy as np
        kare = np.array(pyautogui.screenshot())
        return "[Ekran Metni]:\n" + " | ".join(self._okuyucu().readtext(kare, detail=0))

    def sayaci_sifirla(self):
        self._tiklama_sayaci = 0


def motor_kaydet(motor):
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return
    _ekran = EkranOCRTikla()
    motor._plugin_arac_kaydet(
        "EKRAN_OKU",
        lambda: _ekran.ekran_metnini_oku(),
        "Ekrandaki tüm metni OCR ile oku",
    )
    motor._plugin_arac_kaydet(
        "EKRAN_TIKLA",
        lambda yazi="", hangi="0": _ekran.yaziyi_bul_ve_tikla(
            yazi, hangi=int(hangi) if str(hangi).lstrip("-").isdigit() else 0
        ),
        "Ekrandaki yazıyı OCR ile bul ve tıkla (yazi, hangi: eşleşme indisi)",
    )


if __name__ == "__main__":
    e = EkranOCRTikla()
    print("EkranOCRTikla HASSAS surum (pyautogui:%s, easyocr:%s, PIL:%s)"
          % (PYAUTOGUI_OK, EASYOCR_OK, PIL_OK))
