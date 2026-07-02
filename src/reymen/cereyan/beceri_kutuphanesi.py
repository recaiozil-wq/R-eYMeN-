# -*- coding: utf-8 -*-
"""
beceri_kutuphanesi.py — FAZ 6: JSON sematik beceri kutuphanesi.

closed_learning_loop.py .md karti uretir; bu modul uzerine
yapilandirilmis JSON sablonlari ekler:
  - tetikleyici: hangi kelimeler bu beceliyi aktive eder
  - adimlar: basarili eylem dizisi
  - basari_kriteri: gozlemde ne aranir
  - kullanim_sayisi / basari_orani: performans metrigi
  - son_basari: YYYY-MM-DD

Kullanim:
    kb = BeceriKutuphanesi()
    # Yeni kaydet
    kb.kaydet("dosya_oku", ["dosya oku", "txt ac"], ["DOSYA_OKU"], "basari")
    # Benzer bulup rehber al
    sablon = kb.benzer_bul("bir metin dosyasi oku")
    if sablon:
        rehber = kb.rehber_metni(sablon)
"""

import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Optional
import logging
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.resolve()
KUTUPHANE_DOSYASI = ROOT / ".ReYMeN" / "beceri_kutuphanesi.json"
MAKS_BECERI = 500  # Kutuphane buyukluk siniri


class BeceriKutuphanesi:
    """JSON tabanli yapilandirilmis beceri sablon deposu."""

    def __init__(self, dosya_yolu: str = None):
        self._dosya = Path(dosya_yolu) if dosya_yolu else KUTUPHANE_DOSYASI
        self._dosya.parent.mkdir(parents=True, exist_ok=True)
        self._beceriler: dict[str, dict] = self._yukle()

    # ── Dosya I/O ────────────────────────────────────────────────────────────

    def _yukle(self) -> dict:
        if not self._dosya.exists():
            return {}
        try:
            return json.loads(self._dosya.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _kaydet_dosya(self):
        try:
            self._dosya.write_text(
                json.dumps(self._beceriler, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            print(f"[BeceriKutuphanesi] Yazma hatasi: {e}")

    # ── Kaydetme ─────────────────────────────────────────────────────────────

    def kaydet(
        self,
        beceri_adi: str,
        tetikleyiciler: list[str],
        adimlar: list[str],
        basari_kriteri: str = "",
        aciklama: str = "",
    ) -> str:
        """Yeni beceri sablon ekle ya da mevcutu guncelle.

        Args:
            beceri_adi:      Benzersiz beceri tanimlayici.
            tetikleyiciler:  Bu beceliyi aktive eden anahtar kelimeler.
            adimlar:         Eylem dizisi (ornek: ["DOSYA_OKU", "DOSYA_YAZ"]).
            basari_kriteri:  Gozlemde basariyi isaret eden kelime/kalip.
            aciklama:        Kisa insan okunabilir aciklama.

        Returns:
            Beceri adi (anahtar).
        """
        anahtar = self._normalize(beceri_adi)

        if anahtar in self._beceriler:
            # Guncelle — adim dizisini birlestir, kullanim sayisini artir
            mevcut = self._beceriler[anahtar]
            mevcut["kullanim_sayisi"] = mevcut.get("kullanim_sayisi", 1) + 1
            yeni_adimlar = mevcut.get("adimlar", [])
            for a in adimlar:
                if a not in yeni_adimlar:
                    yeni_adimlar.append(a)
            mevcut["adimlar"] = yeni_adimlar
            yeni_tetikleyiciler = list(
                set(mevcut.get("tetikleyiciler", [])) | set(tetikleyiciler)
            )
            mevcut["tetikleyiciler"] = yeni_tetikleyiciler
            mevcut["son_basari"] = str(date.today())
            print(f"[BeceriKutuphanesi] Guncellendi: {anahtar} "
                  f"(kullanim={mevcut['kullanim_sayisi']})")
        else:
            # Sinir kontrolu
            if len(self._beceriler) >= MAKS_BECERI:
                self._en_az_kullanilani_temizle()
            self._beceriler[anahtar] = {
                "ad": beceri_adi,
                "aciklama": aciklama or beceri_adi,
                "tetikleyiciler": list(set(tetikleyiciler)),
                "adimlar": adimlar,
                "basari_kriteri": basari_kriteri,
                "kullanim_sayisi": 1,
                "basari_orani": 1.0,
                "olusturma": str(date.today()),
                "son_basari": str(date.today()),
            }
            print(f"[BeceriKutuphanesi] Yeni beceri: {anahtar}")

        self._kaydet_dosya()
        return anahtar

    def basari_guncelle(self, beceri_adi: str, basarili: bool):
        """Gorev sonucuna gore basari oranini guncelle (EWMA)."""
        anahtar = self._normalize(beceri_adi)
        if anahtar not in self._beceriler:
            return
        mevcut = self._beceriler[anahtar]
        oran = mevcut.get("basari_orani", 1.0)
        # Agirlikli hareketli ortalama: a=0.3
        yeni_oran = 0.7 * oran + 0.3 * (1.0 if basarili else 0.0)
        mevcut["basari_orani"] = round(yeni_oran, 3)
        if basarili:
            mevcut["son_basari"] = str(date.today())
        self._kaydet_dosya()

    # ── Arama ────────────────────────────────────────────────────────────────

    def benzer_bul(self, sorgu: str, esik_skor: float = 0.15) -> Optional[dict]:
        """Sorguyla en cok eslesen beceliyi dondur.

        Kelime otusmasi skoru kullanir (basit, kütüphane gerektirmez).
        esik_skor altindaysa None doner.
        """
        if not self._beceriler:
            return None
        sorgu_kelimeler = set(self._tokenize(sorgu))
        en_iyi_skor = 0.0
        en_iyi: Optional[dict] = None

        for anahtar, beceri in self._beceriler.items():
            tetikleyici_kelimeler: set[str] = set()
            for t in beceri.get("tetikleyiciler", []):
                tetikleyici_kelimeler.update(self._tokenize(t))
            tetikleyici_kelimeler.update(self._tokenize(beceri.get("ad", "")))

            if not tetikleyici_kelimeler:
                continue

            kesisim = sorgu_kelimeler & tetikleyici_kelimeler
            birlesim = sorgu_kelimeler | tetikleyici_kelimeler
            jaccard = len(kesisim) / len(birlesim) if birlesim else 0.0

            # Basari oranina gore agirliklandir
            agirlik = beceri.get("basari_orani", 1.0)
            skor = jaccard * agirlik

            if skor > en_iyi_skor:
                en_iyi_skor = skor
                en_iyi = {**beceri, "_anahtar": anahtar, "_skor": round(skor, 3)}

        if en_iyi_skor < esik_skor:
            return None
        return en_iyi

    def rehber_metni(self, beceri: dict) -> str:
        """Bulunan beceriden sistem prompt'una enjekte edilecek kisa rehber uret."""
        adimlar_str = " -> ".join(beceri.get("adimlar", []))
        kriter = beceri.get("basari_kriteri", "")
        oran = beceri.get("basari_orani", 1.0)
        return (
            f"\n== GECMIS BECERI REHBERI ({beceri.get('ad', '?')}, "
            f"basari={oran:.0%}) ==\n"
            f"Adimlar: {adimlar_str}\n"
            + (f"Basari kriteri: {kriter}\n" if kriter else "")
        )

    # ── Yardimcilar ──────────────────────────────────────────────────────────

    @staticmethod
    def _normalize(ad: str) -> str:
        return re.sub(r"[^\w]", "_", ad.strip().lower())[:64]

    @staticmethod
    def _tokenize(metin: str) -> list[str]:
        return [t for t in re.split(r"\W+", metin.lower()) if len(t) > 2]

    def _en_az_kullanilani_temizle(self):
        """Sinire ulasinca en az kullanilan beceliyi sil."""
        anahtar = min(
            self._beceriler,
            key=lambda k: self._beceriler[k].get("kullanim_sayisi", 0),
        )
        del self._beceriler[anahtar]

    def toplam(self) -> int:
        return len(self._beceriler)

    def tumunu_listele(self) -> list[dict]:
        return list(self._beceriler.values())


# ── Kolaylik fonksiyonu ───────────────────────────────────────────────────────

_global_kb: Optional[BeceriKutuphanesi] = None


def global_beceri_kutuphanesi() -> BeceriKutuphanesi:
    global _global_kb
    if _global_kb is None:
        _global_kb = BeceriKutuphanesi()
    return _global_kb


# ── Test ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import tempfile

    print("=== beceri_kutuphanesi.py Test ===\n")
    with tempfile.TemporaryDirectory() as tmpdir:
        kb = BeceriKutuphanesi(dosya_yolu=os.path.join(tmpdir, "test_kb.json"))

        # Test 1: Yeni beceri ekle
        kb.kaydet(
            "dosya_oku_yaz",
            tetikleyiciler=["dosya oku", "metin ac", "txt yaz"],
            adimlar=["DOSYA_OKU", "BELLEK_KAYDET", "DOSYA_YAZ"],
            basari_kriteri="basariyla yazildi",
            aciklama="Bir dosyayi okuyup icerigi baskasina yazar",
        )
        print(f"[Test 1] Toplam: {kb.toplam()} (beklenen: 1)")

        # Test 2: Ayni beceriyi tekrar ekle -> guncelle
        kb.kaydet(
            "dosya_oku_yaz",
            tetikleyiciler=["kopyala", "dosya kopyala"],
            adimlar=["DOSYA_OKU", "DOSYA_YAZ"],
        )
        print(f"[Test 2] Toplam: {kb.toplam()} (beklenen: 1, guncelleme oldu)")

        # Test 3: Farkli beceri
        kb.kaydet(
            "web_ara_ozetle",
            tetikleyiciler=["internette ara", "web arama", "haber bul"],
            adimlar=["WEB_ARA", "PYTHON_CALISTIR"],
            basari_kriteri="sonuc bulundu",
        )
        print(f"[Test 3] Toplam: {kb.toplam()} (beklenen: 2)")

        # Test 4: Benzer bul
        bulunan = kb.benzer_bul("bir txt dosyasini oku ve baska yere yaz")
        if bulunan:
            print(f"[Test 4] Bulunan: {bulunan['ad']} (skor: {bulunan['_skor']})")
            print(kb.rehber_metni(bulunan))
        else:
            print("[Test 4] Eslesen beceri yok.")

        # Test 5: Eslesmemeyen sorgu
        yok = kb.benzer_bul("uyu ve dinlen")
        print(f"[Test 5] Yok = {yok is None} (beklenen: True)")

        # Test 6: Basari orani guncelle
        kb.basari_guncelle("dosya_oku_yaz", basarili=False)
        b = kb.benzer_bul("dosya oku")
        print(f"[Test 6] Basari orani dusus: {b.get('basari_orani', '?')}")

        print("\n[Testler] Tamamlandi.")
