# -*- coding: utf-8 -*-
"""
oz_yansima.py — FAZ 6: Pasif Surec Refleksiyonu (Idle-Time Reflection).

main.py'nin interaktif dongusu kullanici input() beklerken
bir arka plan thread'i (daemon) su adimlari calistirir:

  1. session_db.hata_ozeti_cek() ile son hata oruntuleri cek.
  2. sistem_sinyalleri ile CPU/RAM kullanim raporunu al.
  3. LLM'e kisa bir analiz sorusu gonder (tek API cagrisi).
  4. Sonucu .ReYMeN/oz_yansima_log.md'ye ekle.
  5. Bildirim bayragi seti -> main.py bir sonraki prompt'ta
     "[Oz-Yansima] N oneri hazir — /yansima ile gor" yazar.

Kullanim (main.py'de):
    from oz_yansima import OzYansima
    _oz_yansima = OzYansima(session=self.session, provider=self.provider)
    # interaktif dongunun basinda:
    _oz_yansima.baslat_arkaplan()
    bildirim = _oz_yansima.bildirim_al()  # None veya string
"""

import threading
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.resolve()
LOG_DOSYASI = ROOT / ".ReYMeN" / "oz_yansima_log.md"
MINIMUM_ARALIK_SN = 300  # Ayni oturumda en erken tekrar ne zaman
MAKS_LLM_TOKEN = 800     # Yansima prompt ciktisi siniri


class OzYansima:
    """Arka planda idle-time yansima calistiran yoneticisi."""

    def __init__(self, session=None, provider=None):
        self._session = session
        self._provider = provider
        self._bildirim: Optional[str] = None
        self._kilitli = threading.Lock()
        self._son_calisma: float = 0.0
        self._calisiyorum = False
        LOG_DOSYASI.parent.mkdir(parents=True, exist_ok=True)

    # ── Dis API ──────────────────────────────────────────────────────────────

    def baslat_arkaplan(self, gecikme_sn: int = 2) -> bool:
        """Daemon thread olarak yansimay baslatir.

        Args:
            gecikme_sn: Thread baslamadan once beklenecek sure (sn).

        Returns:
            True: Thread baslatildi. False: Cok erken veya zaten calisiyor.
        """
        su_an = time.monotonic()
        if self._calisiyorum:
            return False
        if su_an - self._son_calisma < MINIMUM_ARALIK_SN:
            return False

        self._calisiyorum = True
        t = threading.Thread(
            target=self._calistir_yansima,
            args=(gecikme_sn,),
            daemon=True,
            name="OzYansima",
        )
        t.start()
        return True

    def bildirim_al(self) -> Optional[str]:
        """Yansima tamamlanmissa bildirimi dondur ve sifirla."""
        with self._kilitli:
            b = self._bildirim
            self._bildirim = None
            return b

    def log_oku(self, son_n_satir: int = 30) -> str:
        """Son yansima log satirlarini dondur (/yansima komutu icin)."""
        if not LOG_DOSYASI.exists():
            return "[Oz-Yansima] Henuz yansima kaydi yok."
        satirlar = LOG_DOSYASI.read_text(encoding="utf-8").splitlines()
        return "\n".join(satirlar[-son_n_satir:])

    # ── Ic mantik ────────────────────────────────────────────────────────────

    def _calistir_yansima(self, gecikme_sn: int):
        """Arka plan thread govdesi."""
        try:
            time.sleep(gecikme_sn)
            analiz = self._analiz_yap()
            if analiz:
                self._log_yaz(analiz)
                oneri_sayisi = analiz.get("oneri_sayisi", 0)
                if oneri_sayisi > 0:
                    with self._kilitli:
                        self._bildirim = None  # Kullanici istemedigi icin kapatildi
        except Exception as e:
            print(f"[OzYansima] Arka plan hatasi: {e}")
        finally:
            self._son_calisma = time.monotonic()
            self._calisiyorum = False

    def _analiz_yap(self) -> Optional[dict]:
        """Hata verisi + sistem metrigi + LLM analizi calistir."""
        # 1. Hata ozeti
        hata_verisi = {}
        if self._session:
            try:
                hata_verisi = self._session.hata_ozeti_cek(son_n=50)
            except Exception as _e:
                logger.warning("[OzYansima] Hata ozeti alinamadi: %s", _e)

        # 2. Sistem metrikleri
        sistem_metrigi = _sistem_metrigi_al()

        # 3. LLM analizi (provider yoksa ya da hata orani dusukse atla)
        hata_orani = hata_verisi.get("hata_orani", 0.0)
        oneriler = []

        if self._provider and (hata_orani > 0.1 or sistem_metrigi.get("bellek_yuzde", 0) > 80):
            oneriler = self._llm_analiz_et(hata_verisi, sistem_metrigi)

        # Hata orani yuksekse kural tabanli oneri ekle (LLM olmasa bile)
        if hata_orani > 0.3:
            en_cok = hata_verisi.get("en_cok_hata_veren_arac", "")
            kural_oneri = (
                f"'{en_cok}' araci en cok hataya sebep oluyor "
                f"(oran: {hata_orani:.0%}). "
                f"Parametre dogrulamasi veya fallback eklenmesi onerilir."
                if en_cok else
                f"Genel hata orani yuksek: {hata_orani:.0%}. "
                f"Circuit breaker esigi dusurulmesi onerilir."
            )
            oneriler.insert(0, kural_oneri)

        if not oneriler:
            return None

        return {
            "zaman": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "hata_orani": hata_orani,
            "hata_sayisi": hata_verisi.get("hata_sayisi", 0),
            "toplam_adim": hata_verisi.get("toplam", 0),
            "sistem": sistem_metrigi,
            "oneriler": oneriler,
            "oneri_sayisi": len(oneriler),
        }

    def _llm_analiz_et(self, hata_verisi: dict, sistem: dict) -> list[str]:
        """LLM'e kisa bir performans analizi sorusu sor."""
        ozet = (
            f"Hata orani: {hata_verisi.get('hata_orani', 0):.0%}, "
            f"En cok hata veren arac: {hata_verisi.get('en_cok_hata_veren_arac', '?')}, "
            f"Bellek kullanimi: {sistem.get('bellek_yuzde', '?')}%"
        )
        sistem_prompt = (
            "Sen bir yapay zeka ajan performans danismanisın. "
            "Kısa ve net iyilestirme onerileri ver. "
            "Maksimum 3 madde, her biri tek cumle."
        )
        mesajlar = [
            {"role": "user",
             "content": f"Ajan performans ozeti:\n{ozet}\n\nNe onerilirsin?"}
        ]
        try:
            yanit = self._provider.uret(sistem_prompt, mesajlar)
            # Maddeli listeyi ayristir
            oneriler = []
            for satir in yanit.splitlines():
                satir = satir.strip()
                if satir and (satir[0].isdigit() or satir.startswith("-")):
                    temiz = satir.lstrip("0123456789.-) ").strip()
                    if len(temiz) > 10:
                        oneriler.append(temiz)
            return oneriler[:3]
        except Exception:
            return []

    def _log_yaz(self, analiz: dict):
        """Analiz sonucunu log dosyasina ekle."""
        satirlar = [
            f"\n## {analiz['zaman']} — Oz-Yansima Raporu",
            f"- Hata orani: {analiz['hata_orani']:.0%} "
            f"({analiz['hata_sayisi']}/{analiz['toplam_adim']} adim)",
        ]
        if analiz["sistem"]:
            s = analiz["sistem"]
            satirlar.append(
                f"- Sistem: CPU %{s.get('cpu_yuzde', '?')}, "
                f"Bellek %{s.get('bellek_yuzde', '?')}"
            )
        satirlar.append("\n### Oneriler")
        for i, oneri in enumerate(analiz["oneriler"], 1):
            satirlar.append(f"{i}. {oneri}")

        try:
            with open(LOG_DOSYASI, "a", encoding="utf-8") as f:
                f.write("\n".join(satirlar) + "\n")
        except OSError as e:
            print(f"[OzYansima] Log yazma hatasi: {e}")


# ── Sistem metrigi ────────────────────────────────────────────────────────────

def _sistem_metrigi_al() -> dict:
    """psutil varsa CPU/RAM, yoksa bos dict don."""
    try:
        import psutil
        return {
            "cpu_yuzde": round(psutil.cpu_percent(interval=0.5), 1),
            "bellek_yuzde": round(psutil.virtual_memory().percent, 1),
        }
    except ImportError:
        return {}


# ── Test ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import tempfile
    import os

    print("=== oz_yansima.py Test ===\n")

    # Gecici log dosyasi
    with tempfile.TemporaryDirectory() as tmpdir:
        import oz_yansima as ozy
        ozy.LOG_DOSYASI = Path(tmpdir) / "test_log.md"
        ozy.MINIMUM_ARALIK_SN = 0  # Test icin aralik siniri kaldir

        # Sahte session
        class SahteSession:
            def hata_ozeti_cek(self, son_n=50):
                return {
                    "toplam": 20,
                    "hata_sayisi": 8,
                    "hata_orani": 0.40,
                    "en_cok_hata_veren_arac": "WEB_ARA",
                    "tekrarlayan_hatalar": [
                        {"arac": "WEB_ARA", "mesaj": "baglanti hatasi", "sayi": 5},
                    ],
                }

        oz = ozy.OzYansima(session=SahteSession(), provider=None)

        # Arkaplan baslatma testi
        baslatildi = oz.baslat_arkaplan(gecikme_sn=0)
        print(f"[Test 1] Baslatildi: {baslatildi} (beklenen: True)")

        time.sleep(1)

        # Bildirim kontrolu
        bildirim = oz.bildirim_al()
        print(f"[Test 2] Bildirim: {bildirim}")

        # Log okunabilir mi?
        log = oz.log_oku()
        print(f"[Test 3] Log icerik ({len(log)} karakter):")
        print(log[:300])

        # Tekrar baslatma engeli (aralik = 0 oldugu icin gecmeli ama calisiyorum=False)
        baslatildi2 = oz.baslat_arkaplan(gecikme_sn=0)
        time.sleep(0.5)
        print(f"\n[Test 4] Tekrar baslatildi: {baslatildi2} (beklenen: True, aralik=0)")

        print("\n[Testler] Tamamlandi.")
