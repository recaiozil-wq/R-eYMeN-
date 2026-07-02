# -*- coding: utf-8 -*-
"""
rate_limiter.py — Provider basına rate limiting ve token bütçe yönetimi.

Özellikler:
  - Sliding-window rate limiter (istekler / dakika)
  - Token sayacı (tahmini): kelime * 1.3
  - Günlük / oturum token bütçesi (TOKEN_BUDGET_DAILY)
  - Otomatik bekleme + retry (RATE_LIMIT_RETRY=true)
  - provider_transport.py ile entegre olur (sarmalayıcı)

.env:
  RATE_LIMIT_RPM=60          # istekler / dakika (varsayılan 60)
  TOKEN_BUDGET_DAILY=500000  # günlük token sınırı (0 = sınırsız)
  RATE_LIMIT_RETRY=true      # limit aşılınca bekle
"""
import os
import threading
import time
from collections import deque
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent


def _env_int(key: str, varsayilan: int) -> int:
    try:
        v = os.environ.get(key, "").strip()
        return int(v) if v else varsayilan
    except Exception:
        return varsayilan


def _env_bool(key: str, varsayilan: bool = False) -> bool:
    return os.environ.get(key, str(varsayilan)).strip().lower() in ("1", "true", "yes")


# ── Sliding-window Rate Limiter ───────────────────────────────────────────────

class RateLimiter:
    """
    Sliding-window rate limiter.
    Ayni anda birden fazla provider destekler (her biri kendi penceresi).
    """

    def __init__(self, rpm: int = None, pencere: int = 60):
        self.rpm     = rpm or _env_int("RATE_LIMIT_RPM", 60)
        self.pencere = pencere         # saniye
        self._retry  = _env_bool("RATE_LIMIT_RETRY", True)
        self._penc: dict[str, deque] = {}   # provider -> timestamp deque
        self._kilit  = threading.Lock()
        self._bekleme_toplam = 0.0

    def _pencere_al(self, provider: str) -> deque:
        if provider not in self._penc:
            self._penc[provider] = deque()
        return self._penc[provider]

    def izin_var_mi(self, provider: str = "default") -> bool:
        with self._kilit:
            simdi = time.monotonic()
            p = self._pencere_al(provider)
            # Eski zaman damgalarini temizle
            while p and simdi - p[0] >= self.pencere:
                p.popleft()
            return len(p) < self.rpm

    def kaydet(self, provider: str = "default"):
        with self._kilit:
            self._pencere_al(provider).append(time.monotonic())

    def bekle_ve_kaydet(self, provider: str = "default"):
        """Gerekirse rpm sinirina kadar bekle, sonra kaydet."""
        while not self.izin_var_mi(provider):
            if not self._retry:
                raise RuntimeError(
                    f"[RateLimiter] {provider} rate limit asıldı ({self.rpm} rpm)."
                )
            bekleme = 2.0
            self._bekleme_toplam += bekleme
            print(f"[RateLimiter] {provider}: rate limit — {bekleme:.1f}s bekleniyor...")
            time.sleep(bekleme)
        self.kaydet(provider)

    def durum(self, provider: str = "default") -> dict:
        with self._kilit:
            simdi = time.monotonic()
            p = self._pencere_al(provider)
            while p and simdi - p[0] >= self.pencere:
                p.popleft()
            return {
                "provider":       provider,
                "kullanilan":     len(p),
                "sinir":          self.rpm,
                "bos":            self.rpm - len(p),
                "toplam_bekleme": round(self._bekleme_toplam, 1),
            }

    def tum_durum(self) -> list[dict]:
        return [self.durum(p) for p in list(self._penc.keys())]


# ── Token Sayacı ──────────────────────────────────────────────────────────────

class TokenBudget:
    """
    Günlük token bütçesi. Tahmini sayım: kelime * 1.3.
    Gün degisince otomatik sifirlanir.
    """

    def __init__(self, gunluk_sinir: int = None):
        self.sinir    = gunluk_sinir or _env_int("TOKEN_BUDGET_DAILY", 0)
        self._harcanan: dict[str, int] = {}   # provider -> token
        self._gun     = self._bugun()
        self._kilit   = threading.Lock()
        self._oturum_baslangic = time.monotonic()

    @staticmethod
    def _bugun() -> str:
        from datetime import date
        return date.today().isoformat()

    def _gun_kontrol(self):
        if self._bugun() != self._gun:
            self._harcanan.clear()
            self._gun = self._bugun()

    @staticmethod
    def token_tahmin(metin: str) -> int:
        """Kelime sayısı * 1.3 ile token tahmini."""
        return max(1, int(len(metin.split()) * 1.3))

    def kaydet(self, metin: str, provider: str = "default") -> int:
        adet = self.token_tahmin(metin)
        with self._kilit:
            self._gun_kontrol()
            self._harcanan[provider] = self._harcanan.get(provider, 0) + adet
        return adet

    def toplam(self) -> int:
        with self._kilit:
            self._gun_kontrol()
            return sum(self._harcanan.values())

    def kalan(self) -> int:
        if not self.sinir:
            return -1    # sinirsiz
        return max(0, self.sinir - self.toplam())

    def sinir_asildimi(self) -> bool:
        if not self.sinir:
            return False
        return self.toplam() >= self.sinir

    def durum(self) -> dict:
        with self._kilit:
            self._gun_kontrol()
            sure = round(time.monotonic() - self._oturum_baslangic, 0)
            return {
                "gun":            self._gun,
                "harcanan":       self.toplam(),
                "sinir":          self.sinir or "sinirsiz",
                "kalan":          self.kalan() if self.sinir else "sinirsiz",
                "oturum_sure_s":  sure,
                "providerlar":    dict(self._harcanan),
            }

    def rapor(self) -> str:
        d = self.durum()
        satirlar = [
            f"[TokenBudget] {d['gun']}",
            f"  Harcanan   : {d['harcanan']:,} token",
            f"  Sinir      : {d['sinir'] if isinstance(d['sinir'], str) else d['sinir']:,}",
            f"  Kalan      : {d['kalan'] if isinstance(d['kalan'], str) else d['kalan']:,}",
        ]
        for prov, tok in d["providerlar"].items():
            satirlar.append(f"    {prov:20s}: {tok:,}")
        return "\n".join(satirlar)


# ── Sarmalayici: provider_transport ile entegre ───────────────────────────────

class RateLimitedProvider:
    """
    Var olan provider'i sarmalar — her uret() cagrisi oncesinde
    rate limit kontrol eder ve token sayar.

    Kullanim:
        from rate_limiter import RateLimitedProvider
        provider = RateLimitedProvider(RuntimeProvider(config))
    """

    def __init__(self, provider, rpm: int = None, gunluk_token: int = None):
        self._provider     = provider
        self.rate_limiter  = RateLimiter(rpm)
        self.token_budget  = TokenBudget(gunluk_token)

    def uret(self, sistem: str, mesajlar: list, **kwargs) -> str:
        provider_adi = getattr(self._provider, "_aktif_provider", "default")

        # Token bütçe kontrolü
        if self.token_budget.sinir_asildimi():
            kalan = self.token_budget.kalan()
            raise RuntimeError(
                f"[TokenBudget] Günlük token limiti asildi "
                f"({self.token_budget.sinir:,}). Kalan: {kalan}"
            )

        # Rate limit kontrolü (bekleme dahil)
        self.rate_limiter.bekle_ve_kaydet(provider_adi)

        # Asil cagri
        cevap = self._provider.uret(sistem, mesajlar, **kwargs)

        # Token say: istek + cevap
        istek_metni = sistem + " ".join(
            m.get("content", "") for m in mesajlar
        )
        self.token_budget.kaydet(istek_metni, provider_adi)
        if cevap:
            self.token_budget.kaydet(cevap, provider_adi)

        return cevap

    def durum(self) -> dict:
        return {
            "rate":  self.rate_limiter.tum_durum(),
            "token": self.token_budget.durum(),
        }

    def rapor(self) -> str:
        s = self.token_budget.rapor()
        for d in self.rate_limiter.tum_durum():
            s += (
                f"\n[RateLimiter] {d['provider']}: "
                f"{d['kullanilan']}/{d['sinir']} rpm "
                f"(bekleme: {d['toplam_bekleme']}s)"
            )
        return s

    # Delegate kalan her sey
    def __getattr__(self, item):
        return getattr(self._provider, item)


# ── Motor araci ───────────────────────────────────────────────────────────────

def motor_kaydet(motor, rate_limited_provider=None) -> None:
    """Motor'a TOKEN_RAPOR araci ekle."""
    try:
        from plugins.kanban import _plugin_arac_kaydet
    except Exception:
        return


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    rl = RateLimiter(rpm=5, pencere=10)
    tb = TokenBudget(gunluk_sinir=1000)

    print("Rate limit testi (5 rpm / 10s):")
    for i in range(7):
        rl.bekle_ve_kaydet("test")
        tb.kaydet("Bu bir test mesajidir ornek token sayimi.", "test")
        print(f"  Istek {i+1}: {rl.durum('test')}")

    print("\nToken raporu:")
    print(tb.rapor())
