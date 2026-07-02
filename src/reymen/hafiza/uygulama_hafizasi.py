# -*- coding: utf-8 -*-
"""
uygulama_hafizasi.py — Her uygulama için ayrı kalıcı hafıza.
"Photoshop'ta yeni proje şöyle açılır", "X uygulamasında kaydet şurada"
gibi uygulamaya özel işlem bilgilerini saklar ve geri çağırır.

Yapı: .ReYMeN/uygulama_hafizasi/<uygulama_adi>.json
Her uygulamanın: islemler (ad -> adımlar), makrolar (ad -> makro dosyası), notlar.
"""
import json
import os


class UygulamaHafizasi:
    def __init__(self, kok=".ReYMeN/uygulama_hafizasi"):
        self.kok = kok
        os.makedirs(kok, exist_ok=True)

    def _yol(self, uygulama):
        guvenli = "".join(c if c.isalnum() else "_" for c in uygulama.lower())
        return os.path.join(self.kok, f"{guvenli}.json")

    def _yukle(self, uygulama):
        yol = self._yol(uygulama)
        if os.path.exists(yol):
            with open(yol, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"uygulama": uygulama, "islemler": {}, "makrolar": {}, "notlar": []}

    def _kaydet(self, uygulama, veri):
        with open(self._yol(uygulama), "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)

    def islem_kaydet(self, uygulama, islem_adi, adimlar):
        """Bir uygulamadaki bir işlemin adımlarını kaydeder.
        Örn: islem_kaydet('TinyTask', 'yeni proje', ['Dosya menusu', 'Yeni', ...])"""
        veri = self._yukle(uygulama)
        veri["islemler"][islem_adi] = adimlar
        self._kaydet(uygulama, veri)
        return f"[UygHafıza]: '{uygulama}' için '{islem_adi}' kaydedildi."

    def islem_cagir(self, uygulama, islem_adi):
        """Kayıtlı işlemin adımlarını geri getirir."""
        veri = self._yukle(uygulama)
        if islem_adi in veri["islemler"]:
            return veri["islemler"][islem_adi]
        return None

    def makro_bagla(self, uygulama, islem_adi, makro_dosyasi):
        """Bir işleme kayıtlı bir makro dosyası bağlar."""
        veri = self._yukle(uygulama)
        veri["makrolar"][islem_adi] = makro_dosyasi
        self._kaydet(uygulama, veri)
        return f"[UygHafıza]: '{islem_adi}' makrosu '{uygulama}' altına bağlandı."

    def not_ekle(self, uygulama, metin):
        veri = self._yukle(uygulama)
        veri["notlar"].append(metin)
        self._kaydet(uygulama, veri)
        return "[UygHafıza]: Not eklendi."

    def ozet(self, uygulama):
        veri = self._yukle(uygulama)
        islemler = list(veri["islemler"].keys())
        return f"[{uygulama}] Bilinen işlemler: {', '.join(islemler) or 'yok'}"

    def tum_uygulamalar(self):
        return [f[:-5] for f in os.listdir(self.kok) if f.endswith(".json")]


if __name__ == "__main__":
    h = UygulamaHafizasi(kok="/tmp/ReYMeN_uyg")
    print(h.islem_kaydet("TinyTask", "yeni proje",
                         ["File menüsü aç", "Record'a bas", "işlemi yap", "Save"]))
    print(h.islem_cagir("TinyTask", "yeni proje"))
    print(h.ozet("TinyTask"))
