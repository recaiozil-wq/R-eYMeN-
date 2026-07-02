# -*- coding: utf-8 -*-
"""
anayasa_denetci.py — Constitutional AI Oz-Denetim (Anthropic, 2022).

Buyuk LLM sistemlerindeki ilke:
  "Cevap uretmeden once anayasal ilkelere karsi oz-elestiri yap,
   sonra ilkelere uygun sekilde revize et."

10 Anayasal Ilke (Turkce):
  1. Dogru ve dogrulanabilir bilgi
  2. Zarar vermeme
  3. Kullanici hedefine sadakat
  4. Aciklama ve seffaflik
  5. Verimlilik (gereksiz adim yok)
  6. Guvenlik (sistem zarar gormez)
  7. Tamamlanabilirlik (yari bitmis is yok)
  8. Geri donulebilirlik (geri alinamaz adimlardan kacin)
  9. En az yetki (gereksiz erisim isteme)
  10. Kullaniciya saygi (onay istenmesi gereken yerde sor)

Entegrasyon (main.py):
    from anayasa_denetci import AnayasaDenetci
    ad = AnayasaDenetci(provider=self.provider)
    # GOREV_BITTI oncesi:
    onaylandi, revize = ad.denetle(hedef, ozet, adim_gecmisi)
    if not onaylandi:
        mesajlar.append({"role":"user","content":f"[Anayasa Rev]: {revize}"})
"""

import re
from typing import Optional

# ── Anayasal ilkeler ─────────────────────────────────────────────────────────

ANAYASAL_ILKELER = [
    "Yanit DOGRU ve dogrulanabilir bilgi icermeli; uydurma, tahmin veya hallucination olmamali.",
    "Yanit insanlara veya sistemlere ZARAR VERMEMELI; tehlikeli kod, komut veya eylem icermemeli.",
    "Yanit kullanicinin OZGUL HEDEFINE sadik olmali; cevap konu disina cikmamali.",
    "Yapilan islemler ACIK ve ANLASILIR olmali; karmasik adimlar aciklanmali.",
    "Gereksiz adim, tekrar veya dolasikliktan KACINILMALI; sade ve verimli cevap verilmeli.",
    "SISTEM GUVENLIGI korunmali; kritik dosyalar, registry veya sistem ayarlari izinsiz degistirilmemeli.",
    "Is TAMAMLANDI ise tam olmali; yari bitmis veya eksik sonuc 'bitti' olarak sunulmamali.",
    "GERI DONULEMEZ islemlerden (silme, kalici degisiklik) kacinilmali veya onay istenmeli.",
    "EN AZ YETKI ilkesi: ihtiyac duyulmayan dosya/ag erisimi, sudo vb. istenmemeli.",
    "Riskli eylemler icin KULLANICI ONAYI istenmeli; varsayilan olarak guclu adim atilmamali.",
]

# ── Promptlar ─────────────────────────────────────────────────────────────────

_ELESTIRI_SISTEM = """Sen bir yapay zeka guvenligi ve kalite uzmanisın.
Sana bir ajan gorevi ve bu gorev icin uretilen cevap/sonuc sunulacak.
Cevabi asagidaki anayasal ilkelere gore degerlendirip oz-elestiri yap:

{ilkeler}

Degerlendirmeni KISA tut. Su formatta yanit ver:
IHLAL_VAR: [evet/hayir]
IHLAL_EDILEN_ILKE: [numara ve aciklama, ihlal yoksa "yok"]
KISA_ELESTIRI: [tek cumle, ihlal yoksa "Tum ilkeler karsilandi."]
"""

_REVIZYON_SISTEM = """Sen bir yapay zeka yardimcisisin.
Asagidaki gorevi tamamlamaya calisiyorsun.
Anayasal elestiri aldin. Bu elestiriyi dikkate alarak
YALNIZCA REVIZE EDILMIS CEVABI ver — baska aciklama yapma.
"""


class AnayasaDenetci:
    """Constitutional AI oz-denetim ve revizyon sinifi."""

    def __init__(self, provider=None, ilkeler: list[str] = None, aktif: bool = True):
        self._provider = provider
        self._ilkeler = ilkeler or ANAYASAL_ILKELER
        self.aktif = aktif
        self._elestiri_sayisi = 0
        self._revizyon_sayisi = 0

    # ── Ana API ──────────────────────────────────────────────────────────────

    def denetle(
        self,
        hedef: str,
        cevap: str,
        adim_gecmisi: list[str] = None,
        revize_et: bool = True,
    ) -> tuple[bool, str]:
        """Cevabi anayasal ilkelere gore denetle; gerekirse revize et.

        Args:
            hedef:         Kullanicinin orijinal hedefi.
            cevap:         GOREV_BITTI'deki sonuc veya denetlenecek metin.
            adim_gecmisi:  Yapilan adimlar (ek baglam icin).
            revize_et:     True → ihlal bulunursa LLM'e revize ettir.

        Returns:
            (onaylandi: bool, sonuc: str)
            - onaylandi=True, sonuc=cevap → Gecti
            - onaylandi=False, sonuc=elestiri_veya_revizyon → Uyari/revizyon
        """
        if not self.aktif or not self._provider:
            return True, cevap

        elestiri = self._elestir(hedef, cevap, adim_gecmisi or [])
        self._elestiri_sayisi += 1

        if not elestiri.get("ihlal_var"):
            return True, cevap

        print(f"[AnayasaDenetci] Ihlal: {elestiri.get('ihlal_edilen', 'belirsiz')[:80]}")

        if revize_et:
            revizyon = self._revize_et(hedef, cevap, elestiri)
            if revizyon and revizyon != cevap:
                self._revizyon_sayisi += 1
                return False, revizyon

        return False, f"[Anayasa Uyarisi]: {elestiri.get('kisa_elestiri', '')}\nOrijinal: {cevap}"

    def hizli_kontrol(self, cevap: str) -> tuple[bool, str]:
        """LLM olmadan kural tabanli hizli guvenlik kontrolu.

        Sadece en acik ihlalleri yakalar.
        Returns: (guvenli, uyari)
        """
        kontroller = [
            (r"\brm\s+-rf\b", "Tehlikeli silme komutu (rm -rf)"),
            (r"\bdel\s+/[sq]\b", "Tehlikeli silme komutu (del /s/q)"),
            (r"\bformat\s+[a-z]:", "Disk formatlama komutu"),
            (r"DROP\s+TABLE", "SQL tablo silme"),
            (r"DELETE\s+FROM.*WHERE\s+1\s*=\s*1", "Tum satir silme SQL"),
            (r"os\.system\s*\(\s*['\"]", "Kabuk komutu cagirisi"),
            (r"subprocess\..*shell\s*=\s*True", "Tehlikeli shell=True"),
            (r"__import__\s*\(", "Dinamik import tespit edildi"),
        ]
        cevap_lower = cevap.lower()
        for kalip, aciklama in kontroller:
            if re.search(kalip, cevap, re.IGNORECASE):
                return False, f"[AnayasaDenetci]: Kural ihlali — {aciklama}"
        return True, ""

    def istatistik(self) -> dict:
        return {
            "elestiri_sayisi": self._elestiri_sayisi,
            "revizyon_sayisi": self._revizyon_sayisi,
            "revizyon_orani": (
                round(self._revizyon_sayisi / self._elestiri_sayisi, 3)
                if self._elestiri_sayisi else 0.0
            ),
        }

    # ── Ic yardimcilar ───────────────────────────────────────────────────────

    def _elestir(self, hedef: str, cevap: str, adimlar: list) -> dict:
        """LLM ile anayasal elestiri yap."""
        ilkeler_str = "\n".join(f"{i+1}. {ilke}" for i, ilke in enumerate(self._ilkeler))
        sistem = _ELESTIRI_SISTEM.format(ilkeler=ilkeler_str)

        adim_str = ("\nYapilan adimlar:\n" + "\n".join(f"- {a}" for a in adimlar[-5:])) if adimlar else ""
        kullanici = (
            f"Kullanici Hedefi: {hedef}\n\n"
            f"Uretilen Sonuc/Cevap:\n{cevap[:600]}"
            f"{adim_str}"
        )

        try:
            yanit = self._provider.uret(sistem, [{"role": "user", "content": kullanici}])
            return self._yanit_ayristir(yanit)
        except Exception as e:
            print(f"[AnayasaDenetci] LLM hatasi: {e}")
            return {"ihlal_var": False}

    def _revize_et(self, hedef: str, cevap: str, elestiri: dict) -> str:
        """Ihlal bulunan cevabi revize ettir."""
        kullanici = (
            f"Hedef: {hedef}\n\n"
            f"Onceki cevap: {cevap[:400]}\n\n"
            f"Anayasal elestiri: {elestiri.get('kisa_elestiri', '')}\n"
            f"Ihlal edilen ilke: {elestiri.get('ihlal_edilen', '')}\n\n"
            "Anayasal ilkelere uygun sekilde revize et:"
        )
        try:
            return self._provider.uret(_REVIZYON_SISTEM, [{"role": "user", "content": kullanici}])
        except Exception:
            return ""

    @staticmethod
    def _yanit_ayristir(yanit: str) -> dict:
        m_ihlal = re.search(r"IHLAL_VAR:\s*(evet|hayir)", yanit, re.IGNORECASE)
        m_ilke = re.search(r"IHLAL_EDILEN_ILKE:\s*(.+)", yanit, re.IGNORECASE)
        m_elestiri = re.search(r"KISA_ELESTIRI:\s*(.+)", yanit, re.IGNORECASE)

        ihlal_var = (m_ihlal.group(1).lower() == "evet") if m_ihlal else False
        return {
            "ihlal_var": ihlal_var,
            "ihlal_edilen": m_ilke.group(1).strip() if m_ilke else "",
            "kisa_elestiri": m_elestiri.group(1).strip() if m_elestiri else "",
        }


# ── Test ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== anayasa_denetci.py Test ===\n")

    CAGRI = [0]

    class SahteProvider:
        def uret(self, sistem, mesajlar):
            CAGRI[0] += 1
            icindekiler = mesajlar[0]["content"].lower()
            if "ihlal_var" in sistem.lower() or "degerlendirme" in sistem.lower():
                if "rm -rf" in icindekiler or "sil" in icindekiler:
                    return (
                        "IHLAL_VAR: evet\n"
                        "IHLAL_EDILEN_ILKE: 8. Geri donulemez islem — dosya silme komutu\n"
                        "KISA_ELESTIRI: rm -rf komutu geri alinamaz ve onay gerektirir."
                    )
                return (
                    "IHLAL_VAR: hayir\n"
                    "IHLAL_EDILEN_ILKE: yok\n"
                    "KISA_ELESTIRI: Tum ilkeler karsilandi."
                )
            return "Revize edilmis: Dosyalari silmek yerine yedek aldi."

    ad = AnayasaDenetci(provider=SahteProvider())

    # Test 1: Guvenli cevap
    onaylandi, sonuc = ad.denetle(
        "Dosyalari listele",
        "ls -la komutu ile dosyalar listelendi.",
    )
    print(f"[Test 1] Guvenli: onaylandi={onaylandi} (beklenen: True)")

    # Test 2: Tehlikeli cevap
    onaylandi2, sonuc2 = ad.denetle(
        "Gecici dosyalari temizle",
        "rm -rf /tmp/* komutu calistirildi, tum gecici dosyalar silindi.",
        revize_et=True,
    )
    print(f"[Test 2] Tehlikeli: onaylandi={onaylandi2} (beklenen: False)")
    print(f"  Revizyon: {sonuc2[:100]}")

    # Test 3: Hizli kontrol (LLM olmadan)
    guvenli, uyari = ad.hizli_kontrol("rm -rf /important/files")
    print(f"\n[Test 3] Hizli kontrol: guvenli={guvenli} (beklenen: False)")
    print(f"  Uyari: {uyari}")

    # Test 4: Istatistik
    stats = ad.istatistik()
    print(f"\n[Test 4] Istatistik: {stats}")

    print("\n[Testler] Tamamlandi.")
