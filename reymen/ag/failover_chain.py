# -*- coding: utf-8 -*-
"""
failover_chain.py — Otomatik Provider Geçiş Sistemi

Ana provider hata verince, failover zincirindeki sıradaki provider'a
otomatik atlar. Circuit breaker + health check ile entegre çalışır.

Akış:
  1. Ana provider'a API çağrısı yap
  2. Hata alınırsa → hatayı sınıflandır
  3. Retry edilebilir hata → exponential backoff ile tekrar dene
  4. Retry edilemez / retry'ler tükendi → failover zincirinde sıradaki provider
  5. Zincirdeki tüm provider'lar başarısız → hata raporla
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from reymen.ag.provider_router import SaglayiciYonlendirici, yonlendirici_al

logger = logging.getLogger(__name__)


# ── Hata Sınıfları ──────────────────────────────────────────────────────────

class FailoverNedeni(Enum):
    """Failover'a neyin sebep olduğu."""
    HATA_LIMITI_ASILDI   = "hata_limit_asildi"
    ZAMAN_ASIMI          = "zaman_asimi"
    KIMLIK_DOGRULAMA     = "kimlik_dogrulama"
    FATURALAMA           = "faturalama"
    MODEL_BULUNAMADI     = "model_bulunamadi"
    IC_HATA              = "ic_hata"
    KOTA_ASIMI           = "kota_asimi"
    IZIN_YOK             = "izin_yok"
    BAGLANTI_HATASI      = "baglanti_hatasi"
    BILINMEYEN           = "bilinmeyen"


class FailoverAdimSonucu(Enum):
    """Failover adımının sonucu."""
    BASARILI             = "basarili"
    TEKRAR_DENE          = "tekrar_dene"
    PROVIDER_DEGISTIR    = "provider_degistir"
    DURDUR               = "durdur"


@dataclass
class FailoverRaporu:
    """Failover denemelerinin raporu."""
    basarili: bool = False
    kullanilan_provider: str = ""
    denenen_providerlar: list[str] = field(default_factory=list)
    toplam_deneme: int = 0
    toplam_sure_sn: float = 0.0
    son_hata: str = ""
    son_neden: str = ""


# ── Failover Zinciri ────────────────────────────────────────────────────────

class FailoverZinciri:
    """Provider failover zinciri yöneticisi.

    Bir API çağrısını zincirdeki sırayla dener.
    Her adımda circuit breaker + health check + exponential backoff
    kullanır.
    """

    def __init__(
        self,
        provider_zinciri: list[str],
        max_retry: int = 2,
        backoff_baslangic: float = 1.0,
        backoff_carpan: float = 2.0,
    ):
        """
        Args:
            provider_zinciri: Sıralı provider adları (örn: ["deepseek", "openai", "anthropic"])
            max_retry: Her provider için maksimum retry denemesi
            backoff_baslangic: İlk bekleme süresi (saniye)
            backoff_carpan: Her denemede bekleme çarpanı
        """
        self._zincir = provider_zinciri
        self._max_retry = max_retry
        self._backoff_baslangic = backoff_baslangic
        self._backoff_carpan = backoff_carpan
        self._yonlendirici = yonlendirici_al()
        self._lock = threading.Lock()

    # ── Ana Metot ───────────────────────────────────────────────────────

    def calistir(
        self,
        api_cagri: Callable[[str], Any],
        model: str = "",
        task_id: str = "",
    ) -> tuple[bool, Any, FailoverRaporu]:
        """Failover zincirini çalıştır.

        Args:
            api_cagri: Provider adını alıp API çağrısı yapan fonksiyon.
                       İmza: api_cagri(provider_adı) -> yanıt veya None/exception
            model: Kullanılan model adı (log için)
            task_id: Görev ID'si (log için)

        Returns:
            (basarili_mi, yanit_veya_hata, FailoverRaporu)
        """
        baslama = time.monotonic()
        rapor = FailoverRaporu()
        yanit = None

        for idx, provider in enumerate(self._zincir):
            rapor.denenen_providerlar.append(provider)

            # Circuit breaker: provider aktif mi?
            if not self._yonlendirici.aktif_mi(provider):
                logger.info(
                    "[Failover] %s kara listede, atlanıyor (%d/%d)",
                    provider, idx + 1, len(self._zincir),
                )
                continue

            # Provider'a retry ile dene
            basarili, yanit, neden = self._provider_dene(
                api_cagri, provider, idx, task_id, model,
            )

            if basarili:
                # Başarılı!
                self._yonlendirici.basari_bildir(provider)
                rapor.basarili = True
                rapor.kullanilan_provider = provider
                rapor.toplam_deneme = idx + 1
                rapor.toplam_sure_sn = time.monotonic() - baslama
                return True, yanit, rapor
            else:
                # Hata — provider'a bildir, zincirde devam et
                self._yonlendirici.hata_bildir(provider)
                rapor.son_hata = str(yanit) if yanit else "Bilinmeyen hata"
                rapor.son_neden = neden.value if isinstance(neden, FailoverNedeni) else str(neden)

                logger.warning(
                    "[Failover] %s başarısız: %s → sıradaki: %s",
                    provider, rapor.son_hata,
                    self._zincir[idx + 1] if idx + 1 < len(self._zincir) else "(zincir sonu)",
                )

        # Zincir bitti — başarısız
        rapor.basarili = False
        rapor.kullanilan_provider = ""
        rapor.toplam_deneme = len(self._zincir)
        rapor.toplam_sure_sn = time.monotonic() - baslama

        logger.error(
            "[Failover] Tüm %d provider başarısız! Son hata: %s",
            len(self._zincir), rapor.son_hata,
        )

        return False, rapor.son_hata, rapor

    def _provider_dene(
        self,
        api_cagri: Callable[[str], Any],
        provider: str,
        idx: int,
        task_id: str,
        model: str,
    ) -> tuple[bool, Any, FailoverNedeni]:
        """Tek bir provider'ı retry mekanizmasıyla dene."""
        for deneme in range(1, self._max_retry + 2):  # +2: ilk deneme + max_retry
            try:
                sonuc = api_cagri(provider)
                if sonuc is not None:
                    return True, sonuc, FailoverNedeni.BILINMEYEN
                # None döndüyse hata say
                raise RuntimeError("API yanıt vermedi (None)")
            except Exception as e:
                neden = self._hatayi_siniflandir(e)
                yeniden_denenebilir = self._yeniden_denenebilir_mi(neden)

                if yeniden_denenebilir and deneme <= self._max_retry:
                    # Backoff ile bekle ve tekrar dene
                    bekle = self._backoff_baslangic * (self._backoff_carpan ** (deneme - 1))
                    logger.info(
                        "[Failover] %s deneme %d/%d başarısız, %.1fs sonra tekrar "
                        "(model=%s, neden=%s)",
                        provider, deneme, self._max_retry + 1, bekle, model, neden.value,
                    )
                    time.sleep(bekle)
                else:
                    # Retry edilemez veya retry'ler tükendi
                    return False, e, neden

        return False, RuntimeError(f"{provider} tüm retry'ler başarısız"), FailoverNedeni.BILINMEYEN

    # ── Hata Sınıflandırma ──────────────────────────────────────────────

    def _hatayi_siniflandir(self, hata: Exception) -> FailoverNedeni:
        """API hatasını sınıflandır.

        Sıralama önemli: daha spesifik eşleşmeler önce kontrol edilir.
        """
        hata_str = str(hata).lower()

        # Önce spesifik bağlantı hataları
        if any(t in hata_str for t in (
            "connection refused", "econnrefused", "no route to host",
            "dns lookup failed", "cannot resolve", "resolve hostname",
        )):
            return FailoverNedeni.BAGLANTI_HATASI
        # Zaman aşımı (connection genel değil, spesifik timeout)
        if any(t in hata_str for t in ("timeout", "timed out", "connection timeout", "read timed out")):
            return FailoverNedeni.ZAMAN_ASIMI
        # Kimlik doğrulama
        if any(t in hata_str for t in ("401", "unauthorized", "auth", "api_key", "invalid key")):
            return FailoverNedeni.KIMLIK_DOGRULAMA
        # Faturalama
        if any(t in hata_str for t in ("402", "billing", "insufficient_quota", "payment", "quota")):
            return FailoverNedeni.FATURALAMA
        # İzin/erişim
        if any(t in hata_str for t in ("403", "forbidden", "access denied")):
            return FailoverNedeni.IZIN_YOK
        # Model bulunamadı
        if any(t in hata_str for t in ("404", "not found", "model not found", "model_not_found")):
            return FailoverNedeni.MODEL_BULUNAMADI
        # Kota aşımı
        if any(t in hata_str for t in ("429", "rate limit", "too many requests", "rate_limit")):
            return FailoverNedeni.KOTA_ASIMI
        # Sunucu iç hatası
        if any(t in hata_str for t in ("500", "502", "503", "internal server error", "overloaded", "server error", "bad gateway")):
            return FailoverNedeni.IC_HATA

        return FailoverNedeni.BILINMEYEN

    def _yeniden_denenebilir_mi(self, neden: FailoverNedeni) -> bool:
        """Bu hata türü yeniden denenebilir mi?"""
        return neden in {
            FailoverNedeni.ZAMAN_ASIMI,
            FailoverNedeni.KOTA_ASIMI,
            FailoverNedeni.IC_HATA,
            FailoverNedeni.BAGLANTI_HATASI,
            FailoverNedeni.BILINMEYEN,
        }

    # ── Provider Durum ──────────────────────────────────────────────────

    def zincir_durum(self) -> dict:
        """Zincirdeki tüm provider'ların durum raporu."""
        durumlar = {}
        for provider in self._zincir:
            durumlar[provider] = {
                "aktif": self._yonlendirici.aktif_mi(provider),
                "hata_sayisi": getattr(
                    self._yonlendirici._durumlar.get(provider), "hata_sayisi", 0
                ),
            }
        return {
            "zincir": self._zincir,
            "provider_durumlari": durumlar,
        }
