# -*- coding: utf-8 -*-
"""
oz_tutarlilik.py — Self-Consistency + LLM-as-Judge (Wang et al. 2022).

Buyuk LLM sistemlerinden ilham alinan ilke:
  "Tek cevap yerine N bagimsiz cevap uret, aralarinda en tutarli olani sec."
  + "LLM-as-Judge: ayri bir model/prompt ile cevaplari degerlendir."

Fark:
  - Self-Consistency: ayni cikti beklenir (deterministik)
  - Self-Consistency + Judge: LLM hangi cevap daha iyi oldugunu secer (juri)

Entegrasyon (main.py):
    from oz_tutarlilik import OzTutarlilikDenetci
import logging
logger = logging.getLogger(__name__)
    sc = OzTutarlilikDenetci(provider=self.provider)
    # Yuksek karmasiklikli gorevde planlama asamasinda:
    en_iyi = sc.en_iyi_plani_sec(hedef, sistem_prompt, mesajlar, n=3)
    if en_iyi: mesajlar[-1]["content"] = en_iyi  # plani guncelle
"""

import re
import json
from typing import Optional

# ── Judge prompt ──────────────────────────────────────────────────────────────

_JUDGE_SISTEM = """Sen bir uzman yapay zeka cevap degerlendiricisin.
Sana ayni hedefe uretilmis N farkli plan/cevap sunulacak.
En iyi cevabi asagidaki kriterlere gore degerlendir:
  1. Hedefle uyum (gorevle ilgili mi?)
  2. Mantiksal tutarlilik (adimlar mantikli mi?)
  3. Guvenlik (zarar verici eylem iceriyor mu? iceriyorsa elenmeli)
  4. Eksiksizlik (tum alt hedefleri kapsiyor mu?)
  5. Ozluluk (gereksiz adim/tekrar var mi?)

YALNIZCA EN_IYI: [numara] seklinde yanit ver, baska hicbir sey yazma.
Ornek: EN_IYI: 2
"""

_DEGERLENDIRME_SISTEM = """Sen bir yapay zeka cevap kalite degerlendiricisin.
Sana bir hedef ve bir cevap sunulacak.
Cevabi 1-10 arasi puan ver (10 = mukemmel).

YALNIZCA su formatta yanit ver:
PUAN: [sayi]
ACIKLAMA: [tek cumle]
"""

# ── Sinif ─────────────────────────────────────────────────────────────────────

class OzTutarlilikDenetci:
    """N bagimsiz cevap uretip en iyisini secen Self-Consistency + Judge sinifi."""

    def __init__(
        self,
        provider=None,
        varsayilan_n: int = 3,
        sicaklik_adimi: float = 0.15,
        aktif: bool = True,
    ):
        self._provider = provider
        self.varsayilan_n = varsayilan_n
        self.sicaklik_adimi = sicaklik_adimi  # Her ornek icin sicaklik biraz artirilir
        self.aktif = aktif
        self._toplam_sefer = 0
        self._judge_cagrisi = 0

    # ── Ana API ──────────────────────────────────────────────────────────────

    def en_iyi_plani_sec(
        self,
        hedef: str,
        sistem_prompt: str,
        mesajlar: list[dict],
        n: int = None,
    ) -> Optional[str]:
        """N bagimsiz plan uret ve LLM Judge ile en iyisini sec.

        Args:
            hedef:        Kullanicinin hedef metni (Judge'a kontekst verir).
            sistem_prompt: Provider'a gecilecek sistem talimati.
            mesajlar:      Mevcut mesaj gecmisi.
            n:             Uretilecek ornek sayisi (None -> varsayilan_n).

        Returns:
            En iyi plan metni (str) veya None (provider yoksa/N=1 ise).
        """
        if not self.aktif or not self._provider:
            return None

        n = n or self.varsayilan_n
        if n < 2:
            return None

        self._toplam_sefer += 1
        adaylar = self._n_cevap_uret(sistem_prompt, mesajlar, n)

        if not adaylar:
            return None

        if len(adaylar) == 1:
            return adaylar[0]

        secilen = self._judge_ile_sec(hedef, adaylar)
        return secilen

    def tek_cevap_puan(self, hedef: str, cevap: str) -> dict:
        """Tek cevabi 1-10 arasi puanla (LLM-as-Judge modu).

        Returns:
            {"puan": int, "aciklama": str}
        """
        if not self._provider:
            return {"puan": 5, "aciklama": "Provider yok, varsayilan puan"}

        kullanici = f"Hedef: {hedef}\n\nCevap:\n{cevap[:500]}"
        try:
            yanit = self._provider.uret(
                _DEGERLENDIRME_SISTEM,
                [{"role": "user", "content": kullanici}],
            )
            return self._puan_ayristir(yanit)
        except Exception as e:
            return {"puan": 5, "aciklama": f"Degerlendirme hatasi: {e}"}

    def coklu_oy_ver(self, adaylar: list[str]) -> str:
        """Metin benzerligi ile cogunluk oyu (LLM olmadan).

        Buyuk LLM sistemlerindeki klasik SC: identical cevaplari say.
        Burada: en cok benzer aday kazanir.

        Returns:
            Kazanan aday metni.
        """
        if not adaylar:
            return ""
        if len(adaylar) == 1:
            return adaylar[0]

        # Her adayin diger adaylarla Jaccard benzerligini topla
        skorlar = []
        for i, a in enumerate(adaylar):
            tok_a = set(a.lower().split())
            skor = sum(
                len(tok_a & set(adaylar[j].lower().split())) / max(len(tok_a | set(adaylar[j].lower().split())), 1)
                for j in range(len(adaylar)) if j != i
            )
            skorlar.append((skor, i))

        _, kazanan_idx = max(skorlar)
        return adaylar[kazanan_idx]

    def istatistik(self) -> dict:
        return {
            "toplam_sefer": self._toplam_sefer,
            "judge_cagrisi": self._judge_cagrisi,
        }

    # ── Ic yardimcilar ───────────────────────────────────────────────────────

    def _n_cevap_uret(self, sistem: str, mesajlar: list, n: int) -> list[str]:
        """Ayni sorguya N bagimsiz cevap uret."""
        sonuclar = []
        for i in range(n):
            try:
                # Farkli sicakliklar ile cevap cesitliligi sagla
                sicaklik = 0.7 + i * self.sicaklik_adimi
                cevap = self._provider.uret(
                    sistem,
                    mesajlar,
                    temperature=sicaklik,
                )
                if cevap and cevap.strip():
                    sonuclar.append(cevap.strip())
            except TypeError:
                # Provider temperature parametresi desteklemiyorsa
                try:
                    cevap = self._provider.uret(sistem, mesajlar)
                    if cevap and cevap.strip() and cevap not in sonuclar:
                        sonuclar.append(cevap.strip())
                except Exception as e:
                    print(f"[OzTutarlilik] Ornek {i+1} uretim hatasi: {e}")
            except Exception as e:
                print(f"[OzTutarlilik] Ornek {i+1} hatasi: {e}")

        return sonuclar

    def _judge_ile_sec(self, hedef: str, adaylar: list[str]) -> str:
        """LLM Judge ile en iyi adayi sec."""
        self._judge_cagrisi += 1

        numarali = "\n\n".join(
            f"=== CEVAP {i+1} ===\n{a[:400]}"
            for i, a in enumerate(adaylar)
        )
        kullanici = f"Hedef: {hedef}\n\n{numarali}"

        try:
            yanit = self._provider.uret(
                _JUDGE_SISTEM,
                [{"role": "user", "content": kullanici}],
            )
            secim = self._judge_ayristir(yanit, len(adaylar))
            print(f"[OzTutarlilik] Judge secimi: Cevap {secim + 1}/{len(adaylar)}")
            return adaylar[secim]
        except Exception as e:
            print(f"[OzTutarlilik] Judge hatasi: {e} — cogunluk oyuna geciliyor")
            return self.coklu_oy_ver(adaylar)

    @staticmethod
    def _judge_ayristir(yanit: str, n: int) -> int:
        """Judge ciktisindaki EN_IYI: N'i 0-bazli indekse cevir."""
        m = re.search(r"EN_IYI\s*:\s*(\d+)", yanit, re.IGNORECASE)
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < n:
                return idx
        return 0

    @staticmethod
    def _puan_ayristir(yanit: str) -> dict:
        m_puan = re.search(r"PUAN\s*:\s*(\d+)", yanit, re.IGNORECASE)
        m_ac = re.search(r"ACIKLAMA\s*:\s*(.+)", yanit, re.IGNORECASE)
        return {
            "puan": int(m_puan.group(1)) if m_puan else 5,
            "aciklama": m_ac.group(1).strip() if m_ac else "",
        }


# ── Test ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== oz_tutarlilik.py Test ===\n")

    CAGRI = [0]

    class SahteProvider:
        def uret(self, sistem, mesajlar, **kwargs):
            CAGRI[0] += 1
            sicaklik = kwargs.get("temperature", 0.7)
            # Judge modunda
            if "EN_IYI" in sistem or "degerlendirici" in sistem.lower():
                return "EN_IYI: 2"
            # Puan modunda
            if "PUAN" in sistem:
                return "PUAN: 8\nACIKLAMA: Mantikli ve eksiksiz plan."
            # Farkli cevaplar uret (sicaklik ile farklilas)
            planlar = [
                "Plan A: Once WEB_ARA, sonra DOSYA_YAZ ile kaydet.",
                "Plan B: PYTHON_CALISTIR ile veri cek, analiz et, raporla.",
                "Plan C: KOMUT_CALISTIR ile sistemi kontrol et, DOSYA_YAZ ile belgele.",
            ]
            return planlar[CAGRI[0] % 3]

    sc = OzTutarlilikDenetci(provider=SahteProvider(), varsayilan_n=3)

    # Test 1: 3 aday uret, judge ile sec
    mesajlar = [{"role": "user", "content": "Sistemi analiz et"}]
    en_iyi = sc.en_iyi_plani_sec(
        "Sistemi analiz et ve raporla",
        "Sen bir ajan sistemisin.",
        mesajlar,
        n=3,
    )
    print(f"[Test 1] En iyi plan: {en_iyi[:80]}")

    # Test 2: Cogunluk oyu
    adaylar = [
        "Dosyayi ac, icerigi oku, kaydet.",
        "Dosyayi ac, icerigi oku, kaydet.",
        "Web'e git, bilgi getir.",
    ]
    kazanan = sc.coklu_oy_ver(adaylar)
    print(f"\n[Test 2] Cogunluk oyu: {kazanan[:60]} (beklenen: oku/kaydet planı)")

    # Test 3: Puan
    puan = sc.tek_cevap_puan("Raporla", "Raporu olusturdum ve kaydettim.")
    print(f"\n[Test 3] Puan: {puan}")

    # Test 4: Istatistik
    print(f"\n[Test 4] Istatistik: {sc.istatistik()}")

    print("\n[Testler] Tamamlandi.")
