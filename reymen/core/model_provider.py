# -*- coding: utf-8 -*-
"""
model_provider.py — ReYMeN Provider Sistemi (model routing, failover).

ModelProvider ABC + ProviderChain ile çoklu API sağlayıcı yönetimi.
Failover: 401/402/429/500 → sonraki provider'a otomatik geçiş.
Her adımda log + süre takibi.

Motor araçları:
  - PROVIDER_CALISTIR:  Bir zincirdeki provider'ları sırayla dene
  - PROVIDER_ZINCIR_DURUM: Zincir durum raporu

Kullanım:
    chain = ProviderChain()
    yanit, provider_adi = chain.calistir(messages, system_content)
"""

from __future__ import annotations

import abc
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# ── HTTP timeout ──────────────────────────────────────────────
_HTTP_TIMEOUT = 120.0


# ═══════════════════════════════════════════════════════════════
# ModelProvider — Soyut temel sinif
# ═══════════════════════════════════════════════════════════════

class ModelProvider(abc.ABC):
    """Tüm provider'ların uyması gereken soyut ara yüz.

    Class attributes (her alt sinif tanimlamali):
        ad:          Provider'in kisa adi (ornek: "deepseek")
        model:       Varsayilan model adi
        api_key_env: API anahtari icin environment variable adi
        base_url:    API temel URL'i

    Metotlar:
        hazir_mi()  → bool
        calistir()  → (yanit: str, hata: str | None)
    """

    ad: str = ""
    model: str = ""
    api_key_env: str = ""
    base_url: str = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not cls.ad:
            raise TypeError(f"{cls.__name__} must define 'ad' class attribute.")
        if not cls.model:
            raise TypeError(f"{cls.__name__} must define 'model' class attribute.")

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self._api_key = api_key or os.environ.get(self.api_key_env, "")
        self._model = model or self.model
        self._client = httpx.Client(timeout=_HTTP_TIMEOUT)

    @property
    def api_key(self) -> str:
        return self._api_key

    @property
    def model_adi(self) -> str:
        return self._model

    def hazir_mi(self) -> bool:
        """Provider'in kullanima hazir olup olmadigini kontrol eder."""
        if not self._api_key and self.api_key_env:
            # API anahtari gerekli ama yok
            logger.debug("[%s] API anahtari eksik (env: %s)", self.ad, self.api_key_env)
            return False
        return True

    @abc.abstractmethod
    def calistir(
        self,
        messages: list[dict],
        system_content: str = "",
        **kwargs: Any,
    ) -> tuple[str, Optional[str]]:
        """LLM'e istek gonderir.

        Args:
            messages:    Kullanici mesajlari listesi
            system_content: System prompt (opsiyonel)
            **kwargs:    Ek parametreler (temperature, max_tokens vb.)

        Returns:
            (yanit_metni, hata_mesaji)
            Basarili: (metin, None)
            Basarisiz: ("", hata_mesaji)
        """
        ...

    def kapat(self) -> None:
        """HTTP client'i kapat."""
        try:
            self._client.close()
        except Exception:
            pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} ad={self.ad!r} model={self._model!r}>"


# ═══════════════════════════════════════════════════════════════
# OpenAI uyumlu provider (DeepSeek, OpenRouter, xAI, Groq, ...)
# ═══════════════════════════════════════════════════════════════

class OpenAICompatibleProvider(ModelProvider):
    """OpenAI uyumlu /chat/completions endpoint'i icin provider.

    Model adi __init__'te verilir; class attribute placeholder'dir.
    """

    ad: str = "openai_compat"
    model: str = "__override_in_init__"
    api_key_env: str = ""
    base_url: str = ""

    def __init__(
        self,
        ad: str,
        model: str,
        api_key_env: str,
        base_url: str,
        api_key: Optional[str] = None,
    ):
        self.ad = ad
        self.api_key_env = api_key_env
        self.base_url = base_url.rstrip("/")
        super().__init__(api_key=api_key, model=model)

    def _api_url(self) -> str:
        """Chat completions endpoint URL'i."""
        if "/chat/completions" in self.base_url:
            return self.base_url
        return f"{self.base_url}/v1/chat/completions"

    def calistir(
        self,
        messages: list[dict],
        system_content: str = "",
        **kwargs: Any,
    ) -> tuple[str, Optional[str]]:
        if not self.hazir_mi():
            return "", f"{self.ad}: API anahtari eksik"

        full_messages = []
        if system_content:
            full_messages.append({"role": "system", "content": system_content})
        full_messages.extend(messages)

        payload = {
            "model": kwargs.get("model") or self.model_adi,
            "messages": full_messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        if "stop" in kwargs:
            payload["stop"] = kwargs["stop"]

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = self._client.post(self._api_url(), headers=headers, json=payload)
            status = resp.status_code

            # Failover tetikleyici hata kodlari
            if status in (401, 402, 429, 500):
                return "", f"{self.ad}: HTTP {status} — {resp.text[:200]}"

            resp.raise_for_status()
            data = resp.json()
            yanit = data["choices"][0]["message"]["content"]
            return yanit, None

        except httpx.HTTPStatusError as e:
            code = e.response.status_code if e.response else 0
            if code in (401, 402, 429, 500):
                return "", f"{self.ad}: HTTP {code}"
            return "", f"{self.ad}: HTTP hatasi — {e}"
        except httpx.TimeoutException:
            return "", f"{self.ad}: Zaman asimi"
        except Exception as e:
            return "", f"{self.ad}: {type(e).__name__}: {e}"


# ═══════════════════════════════════════════════════════════════
# MiniMax (xiaomi) provider — farkli API formatı
# ═══════════════════════════════════════════════════════════════

class MiniMaxProvider(ModelProvider):
    """MiniMax (xiaomi) API — /v1/text/chatcompletion_v2."""

    ad: str = "xiaomi"
    model: str = "MiniMax-Text-01"
    api_key_env: str = "XIAOMI_API_KEY"
    base_url: str = "https://api.minimax.chat/v1"

    def _api_url(self) -> str:
        return f"{self.base_url}/text/chatcompletion_v2"

    def calistir(
        self,
        messages: list[dict],
        system_content: str = "",
        **kwargs: Any,
    ) -> tuple[str, Optional[str]]:
        if not self.hazir_mi():
            return "", f"{self.ad}: API anahtari eksik"

        full_messages = []
        if system_content:
            full_messages.append({"role": "system", "content": system_content})
        full_messages.extend(messages)

        payload = {
            "model": kwargs.get("model") or self.model_adi,
            "messages": full_messages,
            "max_tokens": kwargs.get("max_tokens", 1500),
            "frequency_penalty": kwargs.get("frequency_penalty", 0.8),
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = self._client.post(self._api_url(), headers=headers, json=payload)
            status = resp.status_code
            if status in (401, 402, 429, 500):
                return "", f"{self.ad}: HTTP {status}"
            resp.raise_for_status()
            data = resp.json()
            yanit = data["choices"][0]["message"]["content"]
            return yanit, None
        except httpx.HTTPStatusError as e:
            code = e.response.status_code if e.response else 0
            if code in (401, 402, 429, 500):
                return "", f"{self.ad}: HTTP {code}"
            return "", f"{self.ad}: HTTP hatasi — {e}"
        except Exception as e:
            return "", f"{self.ad}: {type(e).__name__}: {e}"


# ═══════════════════════════════════════════════════════════════
# Provider Fabrikası
# ═══════════════════════════════════════════════════════════════

def _provider_fabrikasi(
    ad: str,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> ModelProvider:
    """Provider adina gore uygun instance olusturur.

    Desteklenen adlar: deepseek, openrouter, xai, groq, lmstudio, xiaomi
    """
    _providers = {
        "deepseek": {
            "cls": OpenAICompatibleProvider,
            "defaults": {
                "ad": "deepseek",
                "model": model or "deepseek-chat",
                "api_key_env": "DEEPSEEK_API_KEY",
                "base_url": base_url or "https://api.deepseek.com",
            },
        },
        "openrouter": {
            "cls": OpenAICompatibleProvider,
            "defaults": {
                "ad": "openrouter",
                "model": model or "openrouter/auto",
                "api_key_env": "OPENROUTER_API_KEY",
                "base_url": base_url or "https://openrouter.ai/api",
            },
        },
        "xai": {
            "cls": OpenAICompatibleProvider,
            "defaults": {
                "ad": "xai",
                "model": model or "grok-2-latest",
                "api_key_env": "XAI_API_KEY",
                "base_url": base_url or "https://api.x.ai",
            },
        },
        "groq": {
            "cls": OpenAICompatibleProvider,
            "defaults": {
                "ad": "groq",
                "model": model or "llama-3.3-70b-versatile",
                "api_key_env": "GROQ_API_KEY",
                "base_url": base_url or "https://api.groq.com/openai/v1",
            },
        },
        "lmstudio": {
            "cls": OpenAICompatibleProvider,
            "defaults": {
                "ad": "lmstudio",
                "model": model or "local-model",
                "api_key_env": "",
                "base_url": base_url or "http://localhost:1234",
            },
        },
        "xiaomi": {
            "cls": MiniMaxProvider,
            # MiniMax class attribute'lari zaten dogru, sadece api_key gerek
            "kwargs": {"api_key": api_key, "model": model},
        },
    }

    info = _providers.get(ad)
    if not info:
        raise ValueError(f"Bilinmeyen provider: {ad}. Secenekler: {list(_providers.keys())}")

    cls = info["cls"]
    if "kwargs" in info:
        # Provider kendi class attribute'larini kullanir
        kwargs = {k: v for k, v in info["kwargs"].items() if v is not None}
        return cls(**kwargs)
    else:
        defaults = dict(info["defaults"])
        defaults["api_key"] = api_key
        return cls(**defaults)


# ═══════════════════════════════════════════════════════════════
# ProviderChain — Failover zinciri
# ═══════════════════════════════════════════════════════════════

@dataclass
class ProviderKayit:
    """Zincirdeki bir provider'in kaydi."""
    ad: str
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None


@dataclass
class CalistirSonuc:
    """ProviderChain.calistir sonucu."""
    yanit: str = ""
    provider_adi: str = ""
    basarili: bool = False
    sure_ms: float = 0.0
    denenen_providerlar: list[dict] = field(default_factory=list)
    hata: str = ""


class ProviderChain:
    """Sirali provider listesi ile failover mantigi.

    Bir provider 401/402/429/500 donerse siradakine gecer.
    Her adimda log + sure takibi yapar.

    Varsayilan zincir: deepseek -> openrouter -> xai -> groq -> lmstudio
    """

    def __init__(
        self,
        provider_list: Optional[list[ProviderKayit]] = None,
    ):
        self._provider_list = provider_list or [
            ProviderKayit(ad="deepseek"),
            ProviderKayit(ad="openrouter"),
            ProviderKayit(ad="xai"),
            ProviderKayit(ad="groq"),
            ProviderKayit(ad="lmstudio"),
        ]
        self._instances: dict[str, ModelProvider] = {}

    @property
    def provider_list(self) -> list[ProviderKayit]:
        return list(self._provider_list)

    def ekle(self, ad: str, model: Optional[str] = None,
             api_key: Optional[str] = None, base_url: Optional[str] = None) -> None:
        """Zincirin sonuna provider ekle."""
        self._provider_list.append(
            ProviderKayit(ad=ad, model=model, api_key=api_key, base_url=base_url)
        )
        # Cache'i temizle (tekrar olusturulacak)
        self._instances.pop(ad, None)

    def _get_provider(self, kayit: ProviderKayit) -> Optional[ModelProvider]:
        """Provider instance'ini cache'den al veya olustur."""
        if kayit.ad in self._instances:
            return self._instances[kayit.ad]

        try:
            provider = _provider_fabrikasi(
                ad=kayit.ad,
                model=kayit.model,
                api_key=kayit.api_key,
                base_url=kayit.base_url,
            )
            self._instances[kayit.ad] = provider
            return provider
        except ValueError as e:
            logger.warning("[ProviderChain] Provider olusturulamadi (%s): %s", kayit.ad, e)
            return None

    def calistir(
        self,
        messages: list[dict],
        system_content: str = "",
        **kwargs: Any,
    ) -> CalistirSonuc:
        """Zincirdeki provider'lari sirayla dener.

        Args:
            messages:        Kullanici mesajlari
            system_content:  System prompt
            **kwargs:        Ek parametreler

        Returns:
            CalistirSonuc — yanit, provider adi, basari durumu, sure, detay
        """
        sonuc = CalistirSonuc()
        baslangic = time.time()

        for kayit in self._provider_list:
            provider = self._get_provider(kayit)
            if provider is None:
                sonuc.denenen_providerlar.append({
                    "ad": kayit.ad,
                    "durum": "atlandi",
                    "sebep": "olusturulamadi",
                    "sure_ms": 0,
                })
                continue

            if not provider.hazir_mi():
                sonuc.denenen_providerlar.append({
                    "ad": kayit.ad,
                    "durum": "atlandi",
                    "sebep": "api_anahtari_yok",
                    "sure_ms": 0,
                })
                logger.debug("[ProviderChain] %s atlandi (API anahtari yok)", kayit.ad)
                continue

            # Provider'a istek gonder
            prov_baslangic = time.time()
            yanit, hata = provider.calistir(messages, system_content, **kwargs)
            prov_sure = (time.time() - prov_baslangic) * 1000

            if hata is None:
                # Basarili
                sure = (time.time() - baslangic) * 1000
                sonuc.yanit = yanit
                sonuc.provider_adi = kayit.ad
                sonuc.basarili = True
                sonuc.sure_ms = sure
                sonuc.denenen_providerlar.append({
                    "ad": kayit.ad,
                    "durum": "basarili",
                    "sure_ms": round(prov_sure, 1),
                })
                logger.info(
                    "[ProviderChain] ✅ %s basarili (%.0f ms)",
                    kayit.ad, prov_sure,
                )
                return sonuc
            else:
                # Basarisiz — failover
                failover_kodlari = ("401", "402", "429", "500", "HTTP 401",
                                    "HTTP 402", "HTTP 429", "HTTP 500")
                failover = any(k in hata for k in failover_kodlari)
                durum = "failover" if failover else "hata"
                sonuc.denenen_providerlar.append({
                    "ad": kayit.ad,
                    "durum": durum,
                    "sebep": hata[:120],
                    "sure_ms": round(prov_sure, 1),
                })
                logger.warning(
                    "[ProviderChain] ✗ %s basarisiz (%s) — %s (%.0f ms)",
                    kayit.ad, durum, hata[:80], prov_sure,
                )

        # Tum provider'lar basarisiz
        toplam_sure = (time.time() - baslangic) * 1000
        sonuc.sure_ms = toplam_sure
        sonuc.hata = "Tum provider'lar basarisiz oldu"
        logger.error("[ProviderChain] Tum provider'lar basarisiz (%.0f ms)", toplam_sure)
        return sonuc

    def durum_raporu(self) -> dict:
        """Zincirin durum raporu."""
        providers = []
        for kayit in self._provider_list:
            provider = self._instances.get(kayit.ad)
            hazir = provider is not None and provider.hazir_mi()
            api_var = bool(provider and provider.api_key) if provider else False
            providers.append({
                "ad": kayit.ad,
                "model": kayit.model or "(varsayilan)",
                "hazir": hazir,
                "api_anahtari_var": api_var,
                "base_url": kayit.base_url or "(varsayilan)",
                "instance_var": provider is not None,
            })
        return {
            "provider_sayisi": len(self._provider_list),
            "providerlar": providers,
        }

    def kapat(self) -> None:
        """Tum provider instance'larini kapat."""
        for provider in self._instances.values():
            provider.kapat()
        self._instances.clear()


# ═══════════════════════════════════════════════════════════════
# Varsayilan zincir singleton
# ═══════════════════════════════════════════════════════════════

_varsayilan_zincir: Optional[ProviderChain] = None


def varsayilan_zincir() -> ProviderChain:
    """Varsayilan ProviderChain singleton."""
    global _varsayilan_zincir
    if _varsayilan_zincir is None:
        _varsayilan_zincir = ProviderChain()
    return _varsayilan_zincir


def zinciri_sifirla() -> None:
    """Varsayilan zinciri sifirla (provider instance'larini kapat)."""
    global _varsayilan_zincir
    if _varsayilan_zincir is not None:
        _varsayilan_zincir.kapat()
    _varsayilan_zincir = ProviderChain()


# ═══════════════════════════════════════════════════════════════
# Motor tool kayit (motor.py otomatik import eder)
# ═══════════════════════════════════════════════════════════════

def motor_kaydet(motor: Any) -> None:
    """Provider araçlarını Motor'a kaydeder.

    Motor, _plugin_moduller_yukle() icinde importlib.import_module
    ile bu modulu yukler ve motor_kaydet() fonksiyonunu cagirir.
    """
    import json as _json

    def _provider_calistir(
        mesaj: str = "",
        system: str = "",
        model: str = "",
        max_tokens: int = 4096,
    ) -> str:
        """PROVIDER_CALISTIR: Provider zincirinde LLM cagrisi yapar.

        Parametreler:
          mesaj:     Kullanici mesaji (zorunlu)
          system:    System prompt (opsiyonel)
          model:     Model adi (opsiyonel, varsayilan zincir modeli)
          max_tokens: Maksimum token sayisi

        Donus:
          JSON: {yanit, provider, basarili, sure_ms, denenenler, hata}
        """
        chain = varsayilan_zincir()
        messages_list = [{"role": "user", "content": mesaj}] if mesaj else []
        kwargs = {"max_tokens": max_tokens}
        if model:
            kwargs["model"] = model

        sonuc = chain.calistir(messages_list, system, **kwargs)
        return _json.dumps({
            "yanit": sonuc.yanit,
            "provider": sonuc.provider_adi,
            "basarili": sonuc.basarili,
            "sure_ms": round(sonuc.sure_ms, 1),
            "denenenler": sonuc.denenen_providerlar,
            "hata": sonuc.hata,
        }, ensure_ascii=False, indent=2)

    def _provider_zincir_durum() -> str:
        """PROVIDER_ZINCIR_DURUM: Provider zincirinin durum raporu.

        Donus:
          JSON: {provider_sayisi, providerlar: [{ad, model, hazir, ...}]}
        """
        chain = varsayilan_zincir()
        return _json.dumps(chain.durum_raporu(), ensure_ascii=False, indent=2)

    motor._plugin_arac_kaydet(
        "PROVIDER_CALISTIR",
        _provider_calistir,
        "Provider zincirinde LLM cagrisi yapar: mesaj, system, model, max_tokens",
    )
    motor._plugin_arac_kaydet(
        "PROVIDER_ZINCIR_DURUM",
        _provider_zincir_durum,
        "Provider zincirinin durum raporu: provider sayisi, her provider'in hazir durumu",
    )
    logger.info("[ModelProvider] Motor araclari kaydedildi: PROVIDER_CALISTIR, PROVIDER_ZINCIR_DURUM")
