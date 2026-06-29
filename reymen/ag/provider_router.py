# -*- coding: utf-8 -*-
"""
provider_router.py — Akıllı sağlayıcı yönlendirici

Özellikler:
  - Circuit breaker: hata veren provider'ı geçici kara listeye al
  - Sağlık kontrolü: başlangıçta tüm provider'ları pingle
  - Skorlama: yerel (hızlı) → uzak (yavaş) sıralaması
  - Thread-safe: threading.Lock ile korumalı
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ── Yapılandırma ──────────────────────────────────────────────────────────────

_BREAKER_HATA_LIMITI: int = 2        # Kaç hata sonra kara listeye alınsın?
_BREAKER_BEKLEME_SN: int = 120       # Kara listede kaç saniye kalsın?
_PING_TIMEOUT_SN: int = 5            # Ping zaman aşımı
_LOCAL_PROVIDERS: frozenset = frozenset({
    "lmstudio", "lmstudio_reasoning", "ollama",
})
_KARMA_PROVIDERS: frozenset = frozenset({
    "groq", "moonshot", "gemini",
})


# ── Veri yapıları ─────────────────────────────────────────────────────────────

@dataclass
class SaglayiciDurum:
    ad: str
    hata_sayisi: int = 0
    kara_liste_saati: float = 0.0     # time.monotonic()
    ping_canli: Optional[bool] = None  # None = henüz pinglenmedi
    ping_suresi_sn: float = 0.0        # 0 = hiç pinglenmedi / başarısız

    @property
    def aktif(self) -> bool:
        """Provider şu an kullanılabilir mi?"""
        if self.kara_liste_saati == 0:
            return True
        return (time.monotonic() - self.kara_liste_saati) > _BREAKER_BEKLEME_SN

    def hata_kaydet(self):
        self.hata_sayisi += 1
        if self.hata_sayisi >= _BREAKER_HATA_LIMITI:
            self.kara_liste_saati = time.monotonic()
            logger.warning(
                "[Router] ⛔ %s kara listeye alındı (%d hata, %ds bekleme)",
                self.ad, self.hata_sayisi, _BREAKER_BEKLEME_SN,
            )

    def basari_kaydet(self):
        """Başarılı çağrı → hata sayacını sıfırla"""
        self.hata_sayisi = 0
        self.kara_liste_saati = 0


# ── Ana sınıf ─────────────────────────────────────────────────────────────────

class SaglayiciYonlendirici:
    """Provider'ları yönetir, sıralar, kara listeye alır."""

    def __init__(self):
        self._durumlar: dict[str, SaglayiciDurum] = {}
        self._lock = threading.Lock()

    # ── Durum yönetimi ─────────────────────────────────────────────────────

    def kaydet(self, ad: str) -> SaglayiciDurum:
        """Provider'ı takip listesine ekle (eğer yoksa)."""
        with self._lock:
            if ad not in self._durumlar:
                self._durumlar[ad] = SaglayiciDurum(ad=ad)
            return self._durumlar[ad]

    def hata_bildir(self, ad: str):
        """Provider hata verdi → hata sayacını artır, gerekirse kara listele."""
        with self._lock:
            durum = self._durumlar.get(ad)
            if durum:
                durum.hata_kaydet()

    def basari_bildir(self, ad: str):
        """Provider başarılı → hata sayacını sıfırla."""
        with self._lock:
            durum = self._durumlar.get(ad)
            if durum:
                durum.basari_kaydet()

    def aktif_mi(self, ad: str) -> bool:
        """Provider şu an kullanılabilir mi? (kara listede değil mi?)"""
        with self._lock:
            durum = self._durumlar.get(ad)
            if durum is None:
                return True  # bilinmeyen provider'a izin ver
            return durum.aktif

    def durum_ozeti(self) -> str:
        """Tüm provider'ların durum özeti (debug için)."""
        with self._lock:
            if not self._durumlar:
                return "  (kayıtlı provider yok)"
            satirlar = []
            for ad, d in sorted(self._durumlar.items()):
                ikon = "✅" if d.aktif else "⛔"
                canli = f"ping:{'✅' if d.ping_canli else '❌'}" if d.ping_canli is not None else ""
                kara = f" kara:{d.kara_liste_saati>0}" if d.kara_liste_saati > 0 else ""
                hata = f" hata:{d.hata_sayisi}" if d.hata_sayisi > 0 else ""
                sure = f" {d.ping_suresi_sn:.1f}s" if d.ping_suresi_sn > 0 else ""
                satirlar.append(f"  {ikon} {ad}{canli}{kara}{hata}{sure}")
            return "\n".join(satirlar)

    # ── Sağlık kontrolü ────────────────────────────────────────────────────

    def saglik_kontrolu(
        self,
        provider_list: list[tuple[str, str, str]],  # (ad, base_url, api_key)
    ) -> dict[str, bool]:
        """Tüm provider'ları paralel pingle, canlılık raporu döndür.

        Args:
            provider_list: (provider_adi, base_url, api_key) tuple listesi

        Returns:
            {provider_adi: canli_mi} sözlüğü
        """
        import requests
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _ping(ad: str, base_url: str, api_key: str) -> tuple[str, bool, float]:
            """Tek provider'ı pingle — basit bir GET isteği."""
            t0 = time.monotonic()
            try:
                if "localhost" in base_url or "127.0.0.1" in base_url:
                    # Local provider'lar için basit model listesi sorgusu
                    url = f"{base_url.rstrip('/')}/v1/models"
                    resp = requests.get(url, timeout=_PING_TIMEOUT_SN)
                    canli = resp.status_code == 200
                elif api_key and api_key != "not-needed":
                    # API provider'ları için basit bir ping
                    # Sadece URL erişilebilir mi kontrol et
                    url = f"{base_url.rstrip('/')}/v1/models"
                    headers = {"Authorization": f"Bearer {api_key}"}
                    resp = requests.get(url, timeout=_PING_TIMEOUT_SN, headers=headers)
                    canli = resp.status_code in (200, 401, 403)  # 401/403 = API canlı ama yetki yok
                else:
                    canli = False
                sure = time.monotonic() - t0
                return ad, canli, sure
            except Exception:
                return ad, False, 0.0

        sonuclar = {}
        with ThreadPoolExecutor(max_workers=6) as havuz:
            futures = []
            for ad, base_url, api_key in provider_list:
                if not base_url or (api_key in ("", "not-needed") and ad != "lmstudio"):
                    # Anahtarı olmayanı pingleme
                    with self._lock:
                        durum = self._durumlar.get(ad)
                        if durum:
                            durum.ping_canli = False
                            durum.ping_suresi_sn = 0.0
                    sonuclar[ad] = False
                    continue
                futures.append(havuz.submit(_ping, ad, base_url, api_key))

            for f in as_completed(futures):
                ad, canli, sure = f.result()
                with self._lock:
                    durum = self._durumlar.get(ad)
                    if durum:
                        durum.ping_canli = canli
                        durum.ping_suresi_sn = sure
                sonuclar[ad] = canli

        return sonuclar

    # ── Provider sıralama ──────────────────────────────────────────────────

    def sirala(
        self,
        zincir: list,
        ad_al=None,
    ) -> list:
        """Provider zincirini akıllıca sırala:
        1. Kara listede olmayanlar önce
        2. Yerel (LM Studio, Ollama) önce
        3. Ping canlı olanlar önce
        4. Hızlı ping süresine göre
        """
        def skor(adim) -> float:
            ad = ad_al(adim) if ad_al else (adim.provider if hasattr(adim, "provider") else adim)
            with self._lock:
                durum = self._durumlar.get(ad)

            if durum is None:
                return 100.0  # bilinmeyen = en düşük öncelik

            # Kara listedeyse en sona at
            if not durum.aktif:
                return 999.0

            s = 0.0

            # Yerel provider çok hızlı
            if ad in _LOCAL_PROVIDERS:
                s += 10.0
            elif ad in _KARMA_PROVIDERS:
                s += 5.0

            # Ping canlıysa bonus
            if durum.ping_canli:
                s += 15.0
            elif durum.ping_canli is False:
                s -= 10.0  # ping başarısız = düşük öncelik

            # Hızlı ping süresi bonus
            if durum.ping_suresi_sn > 0:
                s += max(0, 5.0 - durum.ping_suresi_sn)

            return -s  # küçük skor = önce

        return sorted(zincir, key=skor)

    # ── CLI/Uyumluluk arayüzü ──────────────────────────────────────────────

    def saglayici_listele(self) -> list[str]:
        """Kayıtlı tüm provider adlarını döndür."""
        with self._lock:
            return list(self._durumlar.keys())

    def kara_listede_mi(self, ad: str) -> bool:
        """Provider kara listede mi? (Circuit breaker aktif mi?)

        Args:
            ad: Provider adı

        Returns:
            True = kara listede (kullanılamaz), False = kullanılabilir
        """
        with self._lock:
            durum = self._durumlar.get(ad)
            if durum is None:
                return False  # bilinmeyen provider kara listede sayılmaz
            if durum.kara_liste_saati == 0:
                return False
            # Kara listedeyse süre dolmuş mu kontrol et
            return (time.monotonic() - durum.kara_liste_saati) <= _BREAKER_BEKLEME_SN

    def liste(self) -> list[str]:
        """CLI uyumlu: kayıtlı provider listesi (saglayici_listele alias)."""
        return self.saglayici_listele()

    def aktif_sayisi(self) -> int:
        """CLI uyumlu: şu an kullanılabilir (kara listede olmayan) kaç provider var?"""
        sayi = 0
        with self._lock:
            for durum in self._durumlar.values():
                if durum.aktif:
                    sayi += 1
        return sayi

    def failover_chain(self) -> list[str]:
        """CLI uyumlu: kayıtlı provider'ların failover sırası (skorlama bazlı).

        Provider'ları sirala() mantığına göre sıralar — önce yerel,
        sonra API provider'ları, kara listedekiler en sona atılır.
        """
        with self._lock:
            adlar = list(self._durumlar.keys())

        # Skorlama: önce yerel, sonra API, kara listedekiler en son
        def _siralama_skoru(ad: str) -> float:
            durum = self._durumlar.get(ad)
            if durum is None:
                return 100.0
            if not durum.aktif:
                return 999.0  # kara listede = en son
            s = 0.0
            if ad in _LOCAL_PROVIDERS:
                s += 10.0
            if durum.ping_canli:
                s += 15.0
            return -s

        return sorted(adlar, key=_siralama_skoru)


# ── Singleton ──────────────────────────────────────────────────────────────────

_yonlendirici: Optional[SaglayiciYonlendirici] = None
_yonlendirici_lock = threading.Lock()


def yonlendirici_al() -> SaglayiciYonlendirici:
    """Thread-safe singleton."""
    global _yonlendirici
    if _yonlendirici is None:
        with _yonlendirici_lock:
            if _yonlendirici is None:
                _yonlendirici = SaglayiciYonlendirici()
    return _yonlendirici
