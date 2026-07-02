# -*- coding: utf-8 -*-
"""
ajan_suru.py — FAZ 6: Coklu Alt-Ajan Orkestrasyonu (Swarm).

Her "ajan" ayni beyin.py provider'ina farkli rol promptuyla
gonderilen ayri bir LLM cagrisıdır — ek LLM baglantisi gerekmez.

Roller:
  MimarAjan    — Problemi 3 farkli yaklasim stratejisine bol.
  GelistiriciAjan — En iyi stratejiyi somut eylem planina donustur.
  DenetciAjan  — Plani elestir, zayif noktaları bul. Maksimum 2 tur.
  OrkestratörAjan — Uc rolu koordine eder, sonucu tek string dondurur.

Aktivasyon (main.py):
    karmasiklik >= 4 ise su sekilde kullan:
        from ajan_suru import AjanSurusu
        suru = AjanSurusu(provider=self.provider)
        genis_plan = suru.calistir(hedef, mevcut_arac_listesi)
        # genis_plan -> sistem_prompt'a enjekte et veya dogrudan tur olarak kullan
"""

import re
from typing import Optional

# ─── Rol promptlari ──────────────────────────────────────────────────────────

_MIMAR_SISTEM = """Sen bir yazilim mimarisisın. Sana verilen problemi analiz et
ve birbirinden farkli 3 cozum stratejisi one cik. Her strateji icin:
  - Strateji adi (kisa)
  - Temel adimlar (en fazla 4 madde)
  - Avantaj ve dezavantaj (tek cumle)

Yaniti SADECE su formatta ver (baska aciklama ekleme):
### Strateji 1: [AD]
Adimlar: [madde1] | [madde2] | [madde3]
Avantaj: [tek cumle]
Dezavantaj: [tek cumle]

### Strateji 2: ...
### Strateji 3: ...
"""

_GELISTIRICI_SISTEM = """Sen bir uzman yazilim gelistiricisisin.
Sana bir problem ve secilen strateji verilecek.
Bu stratejiye gore somut, adim adim EYLEM PLANI olustur.
Her adim ReYMeN ajaninin kullanabilecegi bir eylem olmali:
WEB_ARA, DOSYA_OKU, DOSYA_YAZ, PYTHON_CALISTIR, KOMUT_CALISTIR vb.

Yaniti su formatta ver:
EYLEM 1: [ARAC_ADI]("[parametre aciklamasi")
EYLEM 2: ...
...
BEKLENEN_SONUC: [tek cumle]
"""

_DENETCI_SISTEM = """Sen kati bir kalite denetcisisin.
Sana bir eylem plani verilecek. Plani elestir:
  - Guvensiz veya yanlis eylemler var mi?
  - Eksik adimlar var mi?
  - Daha basit veya daha guvenilir bir yol var mi?

Eger plan kabul edilebilirse yaniti SADECE sunlarla baslat:
ONAY: Plan yeterli.

Eger plan duzeltilmesi gerekiyorsa yaniti sunlarla baslat:
RED: [kisa neden]
DUZELTME: [somut degisiklik onerileri, madde madde]
"""

_ORKESTRATOR_SISTEM = """Sen bir ajan orkestratorusun.
Asagidaki bilgileri kullanarak kullaniciya sunulmak uzere temiz, kisa bir eylem ozeti hazirla.
Ozet, ajanin hemen uygulayabilecegi adimlardan olusmali.
Mimar, Gelistirici ve Denetci ciktilari sana verilecek; en iyi sentezi yap.
Yaniti Turkce yaz. Maks 10 eylem maddesi.
"""


# ─── Yardimci: LLM cagrisi ───────────────────────────────────────────────────

def _rol_cagrisi(provider, sistem_prompt: str, kullanici_mesaji: str,
                  max_token: int = 1200) -> str:
    """Provider'i belirli bir rol promptuyla cagir."""
    try:
        return provider.uret(
            sistem_prompt,
            [{"role": "user", "content": kullanici_mesaji}],
        )
    except Exception as e:
        return f"[Rol Hatasi]: {e}"


# ─── Rol sinifları ───────────────────────────────────────────────────────────

class MimarAjan:
    """Problemi 3 farkli stratejiyle analiz eder."""

    def __init__(self, provider):
        self._provider = provider

    def analiz_et(self, hedef: str) -> str:
        print("[Mimar] 3 strateji analiz ediliyor...")
        yanit = _rol_cagrisi(self._provider, _MIMAR_SISTEM, hedef)
        return yanit

    @staticmethod
    def en_iyi_stratejiyi_sec(mimar_ciktisi: str) -> str:
        """Mimar ciktisinden ilk (veya en az dezavantajli) stratejiyi sec."""
        m = re.search(r"### Strateji 1:(.*?)(?=### Strateji 2:|$)", mimar_ciktisi, re.DOTALL)
        if m:
            return m.group(1).strip()
        # Tum ciktiyi don
        return mimar_ciktisi[:600]


class GelistiriciAjan:
    """Seçilen stratejiyi somut eylem planina donusturur."""

    def __init__(self, provider):
        self._provider = provider

    def plan_olustur(self, hedef: str, strateji: str) -> str:
        print("[Gelistirici] Eylem plani olusturuluyor...")
        kullanici_msg = (
            f"Problem: {hedef}\n\n"
            f"Secilen Strateji:\n{strateji}\n\n"
            "Bu stratejiye gore eylem plani olustur."
        )
        return _rol_cagrisi(self._provider, _GELISTIRICI_SISTEM, kullanici_msg)


class DenetciAjan:
    """Eylem planini elestirip onay/red kararı verir."""

    def __init__(self, provider, maks_tur: int = 2):
        self._provider = provider
        self._maks_tur = maks_tur

    def denetle(self, hedef: str, plan: str, gelistirici: GelistiriciAjan,
                 strateji: str) -> tuple[str, bool]:
        """Plani denetle; gerekirse gelistiriciyi yeniden cagir.

        Returns:
            (son_plan, onaylandi_mi)
        """
        mevcut_plan = plan
        for tur in range(1, self._maks_tur + 1):
            print(f"[Denetci] Tur {tur}/{self._maks_tur} — plan inceleniyor...")
            kullanici_msg = (
                f"Problem: {hedef}\n\nEylem Plani:\n{mevcut_plan}"
            )
            yanit = _rol_cagrisi(self._provider, _DENETCI_SISTEM, kullanici_msg)

            if yanit.strip().startswith("ONAY"):
                print("[Denetci] Plan onaylandi.")
                return mevcut_plan, True

            # RED: duzelttir
            print(f"[Denetci] Plan reddedildi (tur {tur}), duzelttiriliyor...")
            duzeltme_m = re.search(r"DUZELTME:(.*?)$", yanit, re.DOTALL)
            duzeltme_ipucu = duzeltme_m.group(1).strip() if duzeltme_m else yanit

            yeni_strateji = f"{strateji}\n\n[Denetci Duzeltme Onerileri]:\n{duzeltme_ipucu[:400]}"
            mevcut_plan = gelistirici.plan_olustur(hedef, yeni_strateji)

        print("[Denetci] Maks tur asildi, son plan kabul ediliyor.")
        return mevcut_plan, False


class AjanSurusu:
    """Mimar, Gelistirici ve Denetci'yi koordine eden orkestrator."""

    def __init__(self, provider):
        self._provider = provider
        self.mimar = MimarAjan(provider)
        self.denetci = None  # provider lazim, asagida

    def calistir(self, hedef: str, mevcut_araclar: str = "") -> str:
        """Tam swarm akisini calistir ve sentez eylem ozeti dondur.

        Args:
            hedef:          Kullanicinin orijinal hedefi.
            mevcut_araclar: Kullanilabilir arac listesi (opsiyonel ipucu).

        Returns:
            Orkestrator tarafindan sentezlenmis eylem ozeti.
        """
        hedef_tam = hedef
        if mevcut_araclar:
            hedef_tam = f"{hedef}\n\n[Mevcut Araclar]: {mevcut_araclar[:300]}"

        # 1. Mimar: 3 strateji
        mimar_ciktisi = self.mimar.analiz_et(hedef_tam)
        en_iyi = MimarAjan.en_iyi_stratejiyi_sec(mimar_ciktisi)

        # 2. Gelistirici: eylem plani
        gelistirici = GelistiriciAjan(self._provider)
        ilk_plan = gelistirici.plan_olustur(hedef, en_iyi)

        # 3. Denetci: elestiri + duzeltme
        denetci = DenetciAjan(self._provider, maks_tur=2)
        son_plan, onaylandi = denetci.denetle(hedef, ilk_plan, gelistirici, en_iyi)

        # 4. Orkestrator: sentez
        print("[Orkestrator] Sentez hazirlaniyor...")
        onay_durumu = "ONAYLANDI" if onaylandi else "KISMI ONAY"
        orkestrator_msg = (
            f"Problem: {hedef}\n\n"
            f"Mimar Analizi (ozet):\n{mimar_ciktisi[:400]}\n\n"
            f"Gelistirici Son Plani ({onay_durumu}):\n{son_plan[:600]}\n\n"
            "Yukaridaki bilgileri sentezleyerek kullaniciya sunulacak temiz eylem ozetini hazirla."
        )
        sentez = _rol_cagrisi(self._provider, _ORKESTRATOR_SISTEM, orkestrator_msg)

        # Baslik ekle
        durum_etiketi = "ONAYLANDI" if onaylandi else "UYARI: kismi onay"
        return (
            f"[Suru Analizi — {durum_etiketi}]\n\n"
            f"{sentez}\n\n"
            f"---\n[Denetci Durumu]: {'Tam onay' if onaylandi else 'Maks tur asimi'}"
        )


# ── Test ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== ajan_suru.py Test ===\n")

    CAGRI_SAYACI = [0]

    class SahteProvider:
        """Sirayla farkli rol cevaplari donduren sahte provider."""

        def uret(self, sistem, mesajlar):
            CAGRI_SAYACI[0] += 1
            n = CAGRI_SAYACI[0]

            if "mimar" in sistem.lower() or "strateji" in sistem.lower():
                return (
                    "### Strateji 1: Dogrudan Okuma\n"
                    "Adimlar: DOSYA_OKU | PYTHON_CALISTIR | DOSYA_YAZ\n"
                    "Avantaj: Basit ve hizli.\n"
                    "Dezavantaj: Buyuk dosyalarda yavas.\n\n"
                    "### Strateji 2: Akis Isleme\n"
                    "Adimlar: DOSYA_OKU(akis) | PYTHON_CALISTIR | DOSYA_YAZ\n"
                    "Avantaj: Dusuk bellek.\n"
                    "Dezavantaj: Daha karmasik.\n\n"
                    "### Strateji 3: Paralel\n"
                    "Adimlar: PARALLEL_CALISTIR | DOSYA_YAZ\n"
                    "Avantaj: Hizli.\n"
                    "Dezavantaj: Thread guvenlik riski."
                )
            if "gelistirici" in sistem.lower() or "eylem plani" in sistem.lower():
                return (
                    "EYLEM 1: DOSYA_OKU(\"kaynak.txt\")\n"
                    "EYLEM 2: PYTHON_CALISTIR(\"veri_isle()\")\n"
                    "EYLEM 3: DOSYA_YAZ(\"sonuc.txt\")\n"
                    "BEKLENEN_SONUC: Dosya islendi ve kaydedildi."
                )
            if "denetci" in sistem.lower() or "kalite" in sistem.lower():
                if n <= 4:
                    return "ONAY: Plan yeterli. Guvenli ve eksiksiz."
                return "RED: Hata yakalama eksik.\nDUZELTME: try/except blogu eklenmeli."
            if "orkestrator" in sistem.lower() or "sentez" in sistem.lower():
                return (
                    "1. DOSYA_OKU ile kaynak dosyayi oku.\n"
                    "2. PYTHON_CALISTIR ile veriyi isle.\n"
                    "3. DOSYA_YAZ ile sonucu kaydet.\n"
                )
            return f"[Sahte yanit #{n}]"

    suru = AjanSurusu(provider=SahteProvider())
    hedef = "Buyuk bir CSV dosyasini okuyup isaretli satirlari ayri dosyaya kaydet"
    sonuc = suru.calistir(hedef, mevcut_araclar="DOSYA_OKU, PYTHON_CALISTIR, DOSYA_YAZ")

    print("\n--- Suru Sonucu ---")
    print(sonuc)
    print(f"\n[Test] Toplam LLM cagrisi: {CAGRI_SAYACI[0]} (beklenen: 3-5)")
    print("[Test] Tamamlandi.")
