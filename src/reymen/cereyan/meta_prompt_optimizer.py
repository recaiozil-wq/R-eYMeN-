# -*- coding: utf-8 -*-
"""
meta_prompt_optimizer.py — Automatic Prompt Engineering (APE, Zhou et al. 2022).

Buyuk LLM sistemlerinden ilham alinan ilke:
  "Sistem promptunu otomatik analiz et; tekrarlayan hatalara gore
   iyilestirmeler oner ve uygula."

Calisma mantigi:
  1. session_db'den son N turun basarisizlik/hata verisini cek.
  2. LLM'e: "Bu hatalar neden oluyor? Sistem talimati nasil iyilestirilmeli?"
  3. LLM onerilen eklentiyi uretir (diff degil, ek blok).
  4. main.py baslangicinda veya /optimize komutunda cagrilir.
  5. Oneri .ReYMeN/prompt_gelistirme_log.md'ye kaydedilir.
  6. Kullanici onaylarsa sistem talimati SYSTEM_EKLER alanina eklenir.

Entegrasyon (main.py):
    from meta_prompt_optimizer import MetaPromptOptimizer
import logging
logger = logging.getLogger(__name__)
    mpo = MetaPromptOptimizer(provider=self.provider, session_db=self.session)
    oneri = mpo.analiz_et_ve_oner()
    if oneri: self._sistem_ekle(oneri)
"""

import re
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.resolve()
ONERI_LOG = ROOT / ".ReYMeN" / "prompt_gelistirme_log.md"
SISTEM_EKLERI = ROOT / ".ReYMeN" / "sistem_ekleri.md"

# ── Promptlar ─────────────────────────────────────────────────────────────────

_ANALIZ_SISTEM = """Sen bir yapay zeka sistem mimarissin ve prompt mühendisisin.
Sana bir otonom ajandaki son hata kayitlari verilecek.
Bu hatalari analiz ederek sistem tarimantinin hangi alaninda iyilestirme
yapilmasi gerektigini belirle ve YENİ bir ek blok yaz.

ONEMLI KURALLAR:
- Mevcut talimatin uzerine yazma; SADECE eklenecek YENI bir blok yaz.
- Blok basligini "== [KONU] ==" formatinda tut.
- 3-7 madde halinde somut, uygulanabilir kural yaz.
- Hatalara ozgu; genel tavsiye verme.
- Turkce yaz.

Yanit formati:
BULGU: [tek cumle — hangi hata deseni tespit edildi]
ONERI_BLOK:
== [BASLIK] ==
- kural 1
- kural 2
...
/ONERI_BLOK
"""

_REVIZYON_SISTEM = """Sen bir teknik yazar ve prompt mühendisisin.
Sana iki sistem talimati blogu verilecek: MEVCUT ve ONERI.
Cakismalari tespit et ve MEVCUT blogu ONERI ile birlestirecek
FINAL blogu yaz. Muzikeri KALDIR; YENILERI EKLE.

YALNIZCA final blogu yaz, aciklama ekleme.
"""


class MetaPromptOptimizer:
    """Hata analizine dayali otomatik sistem talimati gelistirici."""

    def __init__(
        self,
        provider=None,
        session_db=None,
        aktif: bool = True,
        min_hata_sayisi: int = 3,
    ):
        self._provider = provider
        self._session = session_db
        self.aktif = aktif
        self.min_hata_sayisi = min_hata_sayisi
        ONERI_LOG.parent.mkdir(parents=True, exist_ok=True)

    # ── Ana API ──────────────────────────────────────────────────────────────

    def analiz_et_ve_oner(self) -> Optional[str]:
        """Hatalari analiz et, sistem talimatina ek blok oner.

        Returns:
            Onerilen ek blok metni (str) veya None (yeterli hata yoksa).
        """
        if not self.aktif or not self._provider:
            return None

        hata_ozeti = self._hatalari_topla()
        if not hata_ozeti or hata_ozeti.get("hata_sayisi", 0) < self.min_hata_sayisi:
            print(f"[APE] Yeterli hata yok ({hata_ozeti.get('hata_sayisi', 0)}/{self.min_hata_sayisi})")
            return None

        oneri = self._llm_analiz_et(hata_ozeti)
        if oneri:
            self._log_yaz(hata_ozeti, oneri)
            self._mevcut_eklere_kaydet(oneri)

        return oneri

    def mevcut_ekleri_yukle(self) -> str:
        """Daha once kaydedilen sistem eklerini oku.

        Returns:
            Sistem prompt ekleri (bos string eger dosya yoksa).
        """
        if SISTEM_EKLERI.exists():
            try:
                return SISTEM_EKLERI.read_text(encoding="utf-8").strip()
            except OSError:
                return ""
        return ""

    def ek_sil(self):
        """Kaydedilen sistem eklerini temizle (sifirla)."""
        if SISTEM_EKLERI.exists():
            SISTEM_EKLERI.unlink()

    def manuel_hata_analiz(self, hata_listesi: list[str]) -> Optional[str]:
        """Manuel verilen hata listesiyle analiz yap.

        Args:
            hata_listesi: String hata mesajlari listesi.

        Returns:
            Onerilen ek blok.
        """
        if not self._provider or not hata_listesi:
            return None

        ozet = {
            "toplam": len(hata_listesi),
            "hata_sayisi": len(hata_listesi),
            "tekrarlayan_hatalar": hata_listesi[:10],
            "en_cok_hata_veren_arac": "bilinmiyor",
        }
        return self._llm_analiz_et(ozet)

    # ── Ic yardimcilar ───────────────────────────────────────────────────────

    def _hatalari_topla(self) -> Optional[dict]:
        """session_db'den hata ozetini topla."""
        if self._session is None:
            return None
        try:
            return self._session.hata_ozeti_cek(son_n=50)
        except AttributeError:
            return None
        except Exception as e:
            print(f"[APE] Hata ozeti alinamadi: {e}")
            return None

    def _llm_analiz_et(self, hata_ozeti: dict) -> Optional[str]:
        """LLM ile hata ozeti analiz et ve iyilestirme onerisi uret."""
        tekrarlayan = hata_ozeti.get("tekrarlayan_hatalar", [])
        hata_str = "\n".join(f"- {h}" for h in tekrarlayan[:10])

        kullanici = (
            f"Toplam tur: {hata_ozeti.get('toplam', '?')}\n"
            f"Hata sayisi: {hata_ozeti.get('hata_sayisi', '?')}\n"
            f"Hata orani: {hata_ozeti.get('hata_orani', '?')}\n"
            f"En cok hata veren arac: {hata_ozeti.get('en_cok_hata_veren_arac', '?')}\n\n"
            f"Tekrarlayan hatalar:\n{hata_str if hata_str else '(veri yok)'}"
        )

        try:
            yanit = self._provider.uret(
                _ANALIZ_SISTEM,
                [{"role": "user", "content": kullanici}],
            )
            return self._oneri_ayristir(yanit)
        except Exception as e:
            print(f"[APE] LLM analiz hatasi: {e}")
            return None

    @staticmethod
    def _oneri_ayristir(yanit: str) -> Optional[str]:
        """LLM ciktisindaki ONERI_BLOK'u cikart."""
        # Blok araştır
        m = re.search(r"ONERI_BLOK:\s*(.+?)(?:/ONERI_BLOK|$)", yanit, re.DOTALL | re.IGNORECASE)
        if m:
            blok = m.group(1).strip()
            if blok and len(blok) > 10:
                return blok

        # Alternatif: == baslikli blok var mi
        m2 = re.search(r"(==\s*\[.+?\]\s*==.+?)(?:$)", yanit, re.DOTALL)
        if m2:
            return m2.group(1).strip()

        # Son care: tum yaniti don
        return yanit.strip() if len(yanit.strip()) > 20 else None

    def _log_yaz(self, hata_ozeti: dict, oneri: str):
        """Analiz sonucunu log dosyasina ekle."""
        try:
            zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
            giris = (
                f"\n## {zaman}\n"
                f"**Hata orani**: {hata_ozeti.get('hata_orani', '?')}\n"
                f"**En cok hata**: {hata_ozeti.get('en_cok_hata_veren_arac', '?')}\n\n"
                f"**Oneri**:\n```\n{oneri}\n```\n---\n"
            )
            with ONERI_LOG.open("a", encoding="utf-8") as f:
                f.write(giris)
        except OSError as e:
            print(f"[APE] Log yazma hatasi: {e}")

    def _mevcut_eklere_kaydet(self, yeni_blok: str):
        """Oneriyi sistem_ekleri.md dosyasina kalici olarak ekle."""
        try:
            mevcut = ""
            if SISTEM_EKLERI.exists():
                mevcut = SISTEM_EKLERI.read_text(encoding="utf-8").strip()

            if yeni_blok in mevcut:
                return  # Zaten var

            birlesik = (mevcut + "\n\n" + yeni_blok).strip()
            SISTEM_EKLERI.write_text(birlesik + "\n", encoding="utf-8")
            print(f"[APE] Sistem eklerine kaydedildi ({len(yeni_blok)} karakter)")
        except OSError as e:
            print(f"[APE] Sistem eki kayit hatasi: {e}")


# ── Test ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import tempfile

    print("=== meta_prompt_optimizer.py Test ===\n")

    class SahteProvider:
        def uret(self, sistem, mesajlar, **kwargs):
            return (
                "BULGU: PYTHON_CALISTIR araci timeout hatasi veriyor.\n"
                "ONERI_BLOK:\n"
                "== [PYTHON CALISTIRMA KURALLAR] ==\n"
                "- 30 saniyeden uzun surecek kodlari parcalara bol.\n"
                "- Buyuk veri setlerini direkt islemek yerine dosyaya yaz.\n"
                "- Her PYTHON_CALISTIR oncesinde timeout riskini degerlendır.\n"
                "/ONERI_BLOK"
            )

    class SahteSessionDB:
        def hata_ozeti_cek(self, son_n=50):
            return {
                "toplam": 20,
                "hata_sayisi": 5,
                "hata_orani": 0.25,
                "en_cok_hata_veren_arac": "PYTHON_CALISTIR",
                "tekrarlayan_hatalar": [
                    "PYTHON_CALISTIR timeout: 30s limit",
                    "PYTHON_CALISTIR timeout: 30s limit",
                    "WEB_ARA: connection refused",
                ],
            }

    with tempfile.TemporaryDirectory() as tmpdir:
        # Gecici log dizini
        import sys
        import meta_prompt_optimizer as mpm
        mpm.ONERI_LOG = Path(tmpdir) / "log.md"
        mpm.SISTEM_EKLERI = Path(tmpdir) / "ekler.md"

        optimizer = MetaPromptOptimizer(
            provider=SahteProvider(),
            session_db=SahteSessionDB(),
            min_hata_sayisi=3,
        )

        # Test 1: Analiz et ve oner
        oneri = optimizer.analiz_et_ve_oner()
        print(f"[Test 1] Oneri: {bool(oneri)} (beklenen: True)")
        if oneri:
            print(f"  Icerik: {oneri[:120]}")

        # Test 2: Mevcut ekleri yukle
        ekler = optimizer.mevcut_ekleri_yukle()
        print(f"\n[Test 2] Ekler yuklendi: {len(ekler)} karakter")

        # Test 3: Manuel analiz
        manuel = optimizer.manuel_hata_analiz(["timeout", "import error", "permission denied"])
        print(f"\n[Test 3] Manuel analiz: {bool(manuel)} (beklenen: True)")

    print("\n[Testler] Tamamlandi.")
