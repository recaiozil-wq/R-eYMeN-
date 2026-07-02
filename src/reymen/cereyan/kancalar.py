# -*- coding: utf-8 -*-
"""
kancalar.py — Katman 4: Eylem Öncesi Kural Denetimi (Hook/Guard)

Her eylem çalıştırılmadan önce belirlenen kurallara göre denetlenir.
Kural ihlali varsa eylem çalıştırılmaz, hata mesajı döner.

Desteklenen kural tipleri:
    - Aynı eylem N kere art arda → dur
    - Yasaklı araç çağrısı
    - Aşırı hızlı döngü (rate limit)
    - Task başına maksimum eylem sayısı
    - Derinlik sınırı ihlali

Kullanım:
    from kancalar import kanca_motoru
    hata = kanca_motoru.denetle(task_id, "KOMUT_CALISTIR")
    if hata:
        # Eylem çalıştırılmaz
    else:
        # Eylem çalıştırılır
"""

import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional


# ── Sabitler ──────────────────────────────────────────────────────────────────

VARSAYILAN_MAKS_ART_ARDA = 4        # Aynı eylem kaç kez üst üste?
VARSAYILAN_MAKS_EYLEM = 30          # Task başına toplam eylem limiti
VARSAYILAN_MIN_ARALIK = 0.5         # İki eylem arası minimum saniye
DANGLING_DERINLIK_UYARISI = 3       # Derinlik > 3 ise 3'ten sonraki her adım uyarır
ENGELLENEN_ARACLAR = frozenset({
    "ALT_AJAN_GOREVLENDIR",         # Zincir koruması
    "SIL_DOSYA", "BICAKLA",          # Tehlikeli araçlar
})


# ── Veri Yapıları ─────────────────────────────────────────────────────────────

@dataclass
class TaskKancaDurumu:
    """Bir task'ın kanca durumu."""
    son_eylem: Optional[str] = None
    art_arda_sayac: int = 0
    toplam_eylem: int = 0
    son_ts: float = 0.0
    bloke: bool = False
    bloke_nedeni: str = ""


class KancaMotoru:
    """Eylem öncesi kural denetimi yapar.
    
    Thread-safe: defaultdict + lock ile farklı task'lar birbirini etkilemez.
    """

    def __init__(self):
        self._durum: dict[str, TaskKancaDurumu] = defaultdict(TaskKancaDurumu)
        self._kilit = threading.Lock()

    def denetle(
        self,
        task_id: str,
        arac: str,
        derinlik: int = 1,
        maks_art_arda: int = VARSAYILAN_MAKS_ART_ARDA,
        maks_eylem: int = VARSAYILAN_MAKS_EYLEM,
        min_aralik: float = VARSAYILAN_MIN_ARALIK,
    ) -> Optional[str]:
        """Bir eylemi kural denetiminden geçirir.
        
        Args:
            task_id: Alt ajan task ID'si
            arac: Çalıştırılacak araç adı (örn. "KOMUT_CALISTIR")
            derinlik: Alt ajan derinliği (1 = ana ajan, 2+ = alt ajan)
            maks_art_arda: Üst üste aynı eylem limiti
            maks_eylem: Task başına toplam eylem limiti
            min_aralik: İki eylem arası minimum süre (saniye)
        
        Returns:
            None = kural ihlali yok (eylem çalıştırılabilir)
            str = kural ihlali mesajı (eylem çalıştırılmaz)
        """
        with self._kilit:
            durum = self._durum[task_id]

            # Bloke kontrolü
            if durum.bloke:
                return f"[KANCA] Task {task_id} bloke: {durum.bloke_nedeni}"

            # Yasaklı araç kontrolü
            if arac in ENGELLENEN_ARACLAR:
                durum.bloke = True
                durum.bloke_nedeni = f"'{arac}' yasaklı araç"
                return f"[KANCA] '{arac}' yasaklı. Task bloke edildi."

            # Derinlik uyarısı
            if derinlik > DANGLING_DERINLIK_UYARISI:
                return (
                    f"[KANCA] UYARI: Derinlik {derinlik} (limit: {DANGLING_DERINLIK_UYARISI}). "
                    f"Çok derin alt ajan zinciri — GOREV_BITTI ile sonlandır."
                )

            # Aynı eylem art arda kontrolü
            if arac == durum.son_eylem:
                durum.art_arda_sayac += 1
                if durum.art_arda_sayac >= maks_art_arda:
                    durum.bloke = True
                    durum.bloke_nedeni = f"'{arac}' {maks_art_arda}kere art arda"
                    return (
                        f"[KANCA] '{arac}' {maks_art_arda} kere art arda çağrıldı. "
                        f"Muhtemel döngü — task bloke edildi."
                    )
            else:
                durum.art_arda_sayac = 1
            durum.son_eylem = arac

            # Toplam eylem limiti
            durum.toplam_eylem += 1
            if durum.toplam_eylem > maks_eylem:
                durum.bloke = True
                durum.bloke_nedeni = f"Toplam {maks_eylem} eylem limiti aşıldı"
                return (
                    f"[KANCA] Task {task_id}: {maks_eylem} eylem limiti aşıldı. "
                    f"Task bloke edildi."
                )

            # Hızlı döngü kontrolü
            simdi = time.time()
            if durum.son_ts > 0 and (simdi - durum.son_ts) < min_aralik:
                return f"[KANCA] Çok hızlı: {(simdi - durum.son_ts):.2f}s < {min_aralik}s"
            durum.son_ts = simdi

        return None  # İhlal yok

    def bloke_coz(self, task_id: str) -> bool:
        """Bloke edilmiş bir task'ın blokesini kaldır."""
        with self._kilit:
            if task_id in self._durum:
                self._durum[task_id].bloke = False
                self._durum[task_id].bloke_nedeni = ""
                return True
            return False

    def task_durum(self, task_id: str) -> dict:
        """Bir task'ın kanca durumunu döndürür."""
        with self._kilit:
            d = self._durum.get(task_id)
            if d:
                return {
                    "son_eylem": d.son_eylem,
                    "art_arda_sayac": d.art_arda_sayac,
                    "toplam_eylem": d.toplam_eylem,
                    "bloke": d.bloke,
                    "bloke_nedeni": d.bloke_nedeni,
                }
            return {"bloke": False}

    def task_temizle(self, task_id: str):
        """Task bitince durumu temizle."""
        with self._kilit:
            self._durum.pop(task_id, None)

    def istatistik(self) -> dict:
        """Tüm aktif task'ların kanca istatistikleri."""
        with self._kilit:
            toplam = len(self._durum)
            blokeli = sum(1 for d in self._durum.values() if d.bloke)
            return {"aktif_task": toplam, "blokeli_task": blokeli}


# ── Singleton ─────────────────────────────────────────────────────────────────

kanca_motoru = KancaMotoru()


# ── Test ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test 1: Normal eylem — ihlal yok
    hata = kanca_motoru.denetle("test_001", "DOSYA_OKU")
    assert hata is None, "Normal eylem ihlal vermemeli"
    print("[OK] Normal eylem — ihlal yok")

    # Test 2: Aynı eylem 4 kere art arda → bloke
    for i in range(5):
        hata = kanca_motoru.denetle("test_002", "WEB_ARA")
    assert hata is not None, "5. ayni eylem bloke etmeli"
    assert "bloke" in hata.lower(), "Bloke mesaji icermeli"
    print(f"[OK] Art arda ayni eylem blokesi: {hata[:50]}...")

    # Test 3: Yasaklı araç
    hata = kanca_motoru.denetle("test_003", "ALT_AJAN_GOREVLENDIR")
    assert hata is not None, "Yasakli arac bloke etmeli"
    print(f"[OK] Yasakli arac blokesi: {hata[:50]}...")

    # Test 4: Bloke çözme
    assert kanca_motoru.bloke_coz("test_002"), "Bloke cozulebilmeli"
    durum = kanca_motoru.task_durum("test_002")
    assert not durum["bloke"], "Cozum sonrasi bloke=False olmali"
    print("[OK] Bloke cozme basarili")

    # Test 5: İstatistik
    istat = kanca_motoru.istatistik()
    print(f"[OK] Istatistik: {istat}")

    # Temizlik
    kanca_motoru.task_temizle("test_001")
    kanca_motoru.task_temizle("test_002")
    kanca_motoru.task_temizle("test_003")
    print("[OK] Tum testler gecti")
