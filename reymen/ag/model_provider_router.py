# -*- coding: utf-8 -*-
"""
model_provider_router.py — Model→Provider yönlendirici

Model adından provider'a, failover zincirinden sağlık kontrolüne
kadar tüm model routing mantığını barındırır.

Özellikler:
  - Model→Provider statik haritası (config.yaml + built-in fallback)
  - Failover zinciri: bir provider hata verince sıradakine atla
  - Model bazlı provider doğrulama
  - Thread-safe singleton
"""

from __future__ import annotations

import logging
import threading
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from reymen.ag.provider_router import (
    SaglayiciYonlendirici,
    SaglayiciDurum,
    yonlendirici_al,
)

logger = logging.getLogger(__name__)


# ── Varsayılan Model→Provider Haritası ──────────────────────────────────────
# config.yaml'da model_providers: yoksa kullanılır
VARSAYILAN_MODEL_PROVIDER_MAP: dict[str, str] = {
    # DeepSeek
    "deepseek-v4-flash":          "deepseek",
    "deepseek-v3":                "deepseek",
    "deepseek-chat":              "deepseek",
    "deepseek-reasoner":          "deepseek",
    "deepseek-r1":                "deepseek",
    # OpenAI
    "gpt-4o":                     "openai",
    "gpt-4o-mini":                "openai",
    "gpt-4-turbo":                "openai",
    "gpt-3.5-turbo":              "openai",
    "o1":                         "openai",
    "o3-mini":                    "openai",
    # Anthropic
    "claude-sonnet-4":            "anthropic",
    "claude-sonnet-4-20250514":   "anthropic",
    "claude-3-5-sonnet":          "anthropic",
    "claude-3-opus":              "anthropic",
    "claude-3-haiku":             "anthropic",
    # OpenRouter
    "openrouter/auto":            "openrouter",
    "openrouter/deepseek":        "openrouter",
    "openrouter/llama":           "openrouter",
    "openrouter/mistral":         "openrouter",
    # Groq
    "groq/llama3":                "groq",
    "groq/mixtral":               "groq",
    "groq/deepseek":              "groq",
    "groq/gemma":                 "groq",
    # Azure OpenAI
    "azure/gpt-4o":               "azure",
    "azure/gpt-4":                "azure",
    # Gemini
    "gemini-pro":                 "gemini",
    "gemini-1.5-pro":             "gemini",
    "gemini-1.5-flash":           "gemini",
    # LM Studio (yerel)
    "lm-studio/default":          "lmstudio",
    "local-model":                "lmstudio",
    # Amazon Bedrock
    "bedrock/claude":             "bedrock",
    "bedrock/llama":              "bedrock",
}

# Provider→failover sırası (varsayılan)
VARSAYILAN_FAILOVER_ZINCIRI: list[list[str]] = [
    # Birinci tercih: local provider
    ["lmstudio"],
    # İkinci tercih: ana API provider'ları
    ["deepseek", "openrouter"],
    # Üçüncü tercih: alternatif API'ler
    ["openai", "anthropic"],
    # Son çare
    ["groq", "gemini"],
]

# Provider tipi → API uyumluluğu
PROVIDER_API_TIPI: dict[str, str] = {
    "openrouter":   "openai",
    "openai":       "openai",
    "deepseek":     "openai",
    "groq":         "openai",
    "azure":        "openai",
    "gemini":       "openai",
    "anthropic":    "anthropic",
    "bedrock":      "bedrock",
    "lmstudio":     "openai",
}

# Provider → varsayılan model
PROVIDER_VARSAYILAN_MODEL: dict[str, str] = {
    "deepseek":     "deepseek-v4-flash",
    "openai":       "gpt-4o",
    "anthropic":    "claude-sonnet-4-20250514",
    "openrouter":   "openrouter/auto",
    "groq":         "groq/llama3",
    "azure":        "azure/gpt-4o",
    "gemini":       "gemini-1.5-pro",
    "bedrock":      "bedrock/claude",
    "lmstudio":     "lm-studio/default",
}


# ── Veri Yapıları ───────────────────────────────────────────────────────────

@dataclass
class ModelYonlendirmeKarari:
    """Model yönlendirme kararı — hangi provider'a, hangi model adıyla gidilecek."""
    model: str                          # LLM'e gönderilecek model adı
    provider: str                       # Provider adı (deepseek, openai vb.)
    api_tipi: str                       # API uyumluluk tipi (openai/anthropic/bedrock)
    base_url: str                       # Provider base URL
    api_key: str                        # API anahtarı
    failover_zinciri: list[str] = field(default_factory=list)  # Yedek provider listesi
    orijinal_model: str = ""            # İstenen orijinal model adı

    def __post_init__(self):
        if not self.orijinal_model:
            self.orijinal_model = self.model


# ── Ana Sınıf ───────────────────────────────────────────────────────────────

class ModelProviderRouter:
    """Model→Provider yönlendirme + failover zinciri yönetimi.

    config.yaml'daki model_providers: bölümünü okur, varsayılan harita
    ile birleştirir. Bir model hangi provider'da çalışır, hata alınırsa
    hangi sırayla diğer provider'lara geçilir — tüm bu mantık buradadır.
    """

    def __init__(
        self,
        config_yolu: Optional[str] = None,
        model_provider_map: Optional[dict[str, str]] = None,
        failover_zinciri: Optional[list[list[str]]] = None,
    ):
        self._lock = threading.Lock()
        self._yonlendirici: SaglayiciYonlendirici = yonlendirici_al()

        # Haritalar
        self._model_provider_map: dict[str, str] = {}
        self._failover_zinciri: list[list[str]] = []
        self._provider_yapisi: dict[str, dict] = {}  # providers: config.yaml'daki yapı

        # Config'den yükle
        self._config_yolu = config_yolu
        self._config_yukle(config_yolu)

        # Parametre override'ları
        if model_provider_map:
            self._model_provider_map.update(model_provider_map)
        if failover_zinciri:
            self._failover_zinciri = failover_zinciri

        # Provider'ları yönlendiriciye kaydet
        for ad in list(self._model_provider_map.values()) + [
            p for zincir in self._failover_zinciri for p in zincir
        ]:
            self._yonlendirici.kaydet(ad)

        logger.info(
            "[ModelRouter] %d model→provider eşlemesi, %d failover adımı yüklendi",
            len(self._model_provider_map),
            len(self._failover_zinciri),
        )

    # ── Config Yükleme ───────────────────────────────────────────────────

    def _config_yukle(self, config_yolu: Optional[str] = None) -> None:
        """config.yaml'dan model_providers: ve providers: bölümlerini oku."""
        yollar = []
        if config_yolu:
            yollar.append(Path(config_yolu))
        yollar.extend([
            Path.cwd() / "config.yaml",
            Path(__file__).resolve().parent.parent.parent / "config.yaml",
        ])

        for y in yollar:
            if y.exists():
                try:
                    with open(y, "r", encoding="utf-8") as f:
                        cfg = yaml.safe_load(f) or {}

                    # model_providers: bölümü
                    mp = cfg.get("model_providers", {})
                    if isinstance(mp, dict):
                        self._model_provider_map.update(mp)

                    # providers: bölümü (base_url, api_key bilgisi)
                    prov = cfg.get("providers", {})
                    if isinstance(prov, dict):
                        self._provider_yapisi = prov
                        # Her provider'ı yönlendiriciye kaydet
                        for ad in prov:
                            self._yonlendirici.kaydet(ad)

                    # failover_zinciri: bölümü (opsiyonel)
                    fz = cfg.get("failover_zinciri")
                    if isinstance(fz, list):
                        self._failover_zinciri = fz

                    logger.info("[ModelRouter] Config yüklendi: %s", y)
                    return
                except Exception as e:
                    logger.warning("[ModelRouter] Config okuma hatası (%s): %s", y, e)

        # Config bulunamadı — varsayılan haritayı kullan
        self._model_provider_map = dict(VARSAYILAN_MODEL_PROVIDER_MAP)
        self._failover_zinciri = list(VARSAYILAN_FAILOVER_ZINCIRI)
        logger.info("[ModelRouter] Config bulunamadı, varsayılan harita kullanılıyor")

    # ── Model Yönlendirme ────────────────────────────────────────────────

    def model_route(self, model: str, provider_override: Optional[str] = None) -> ModelYonlendirmeKarari:
        """Bir model adını çözümle: hangi provider, hangi API tipi, hangi URL.

        Args:
            model: İstenen model adı (örn: "deepseek-v4-flash")
            provider_override: Provider'ı zorla (örn: "openrouter")

        Returns:
            ModelYonlendirmeKarari — yönlendirme kararı
        """
        model_adi = model.strip()

        with self._lock:
            # Provider override varsa onu kullan
            if provider_override:
                    provider = provider_override
            else:
                # Model→Provider haritasında ara
                provider = self._model_provider_map.get(model_adi)

            if not provider:
                # Hello? fallback: model adının ilk kısmını provider olarak dene
                # Örn: "deepseek-v4-flash" → "deepseek"
                prefix = model_adi.split("-")[0].split("/")[0].split(".")[0]
                if prefix in self._model_provider_map.values():
                    provider = prefix
                elif prefix in PROVIDER_API_TIPI:
                    provider = prefix
                else:
                    # Hiçbir şey bulunamadı — varsayılan provider'a yönlendir
                    provider = "deepseek"
                    logger.warning(
                        "[ModelRouter] '%s' modeli için provider bulunamadı, "
                        "varsayılan: %s", model_adi, provider,
                    )

            # Provider yapılandırmasını al
            prov_yapi = self._provider_yapisi.get(provider, {})
            base_url = prov_yapi.get("base_url", "")
            api_key = prov_yapi.get("api_key", "")
            api_key_env = prov_yapi.get("api_key_env", "")
            if not api_key and api_key_env:
                import os
                api_key = os.environ.get(api_key_env, "")

            # API tipini belirle
            api_tipi = PROVIDER_API_TIPI.get(provider, "openai")

            # Failover zinciri oluştur
            failover_zinciri = self._failover_zincir_olustur(provider)

            return ModelYonlendirmeKarari(
                model=model_adi,
                provider=provider,
                api_tipi=api_tipi,
                base_url=base_url,
                api_key=api_key,
                failover_zinciri=failover_zinciri,
                orijinal_model=model_adi,
            )

    def _failover_zincir_olustur(self, baslangic_provider: str) -> list[str]:
        """Bir provider'dan başlayarak failover zinciri oluştur.

        Varsayılan failover zincirindeki grupları tara, başlangıç
        provider'ını bul, ondan sonraki tüm provider'ları zincire ekle.

        Örn: baslangic="anthropic" → ["anthropic", "groq", "gemini"]
        """
        bulundu = False
        zincir = []
        for grup in self._failover_zinciri:
            for p in grup:
                if bulundu:
                    zincir.append(p)
                elif p == baslangic_provider:
                    zincir.append(p)
                    bulundu = True
                    # Aynı gruptaki diğer provider'ları da ekle
                    for diger in grup:
                        if diger != p:
                            zincir.append(diger)

        if not bulundu:
            # Provider failover zincirinde bulunamadı — sadece kendisi
            zincir = [baslangic_provider]

        return zincir

    # ── Provider Sağlık Kontrolü ────────────────────────────────────────

    def tum_provider_saglik(self) -> dict[str, bool]:
        """Tüm provider'ların sağlık kontrolünü yap.

        Returns:
            {provider_adi: canli_mi} sözlüğü
        """
        provider_list = []
        for ad, yapi in self._provider_yapisi.items():
            base_url = yapi.get("base_url", "")
            api_key = yapi.get("api_key", "")
            api_key_env = yapi.get("api_key_env", "")
            if not api_key and api_key_env:
                import os
                api_key = os.environ.get(api_key_env, "")
            if base_url:
                provider_list.append((ad, base_url, api_key))

        return self._yonlendirici.saglik_kontrolu(provider_list)

    def provider_durum(self, provider: Optional[str] = None) -> dict:
        """Provider durum raporu.

        Args:
            provider: Provider adı (None = tümü)

        Returns:
            Durum bilgisi dict
        """
        if provider:
            aktif = self._yonlendirici.aktif_mi(provider)
            return {
                "provider": provider,
                "aktif": aktif,
                "durum_ozeti": self._yonlendirici.durum_ozeti(),
            }

        return {
            "provider_sayisi": len(self._provider_yapisi),
            "model_sayisi": len(self._model_provider_map),
            "failover_adim_sayisi": len(self._failover_zinciri),
            "provider_durumlari": self._yonlendirici.durum_ozeti(),
        }

    # ── Provider Hata/Başarı Bildirimi ──────────────────────────────────

    def hata_bildir(self, provider: str):
        """Provider hata bildirimi — circuit breaker tetiklenebilir."""
        self._yonlendirici.hata_bildir(provider)

    def basari_bildir(self, provider: str):
        """Provider başarı bildirimi — hata sayacı sıfırlanır."""
        self._yonlendirici.basari_bildir(provider)

    def aktif_mi(self, provider: str) -> bool:
        """Provider kullanılabilir durumda mı?"""
        return self._yonlendirici.aktif_mi(provider)

    # ── Model Listesi ───────────────────────────────────────────────────

    def modelleri_listele(self, provider_filtre: Optional[str] = None) -> list[dict]:
        """Tüm bilinen modelleri listele.

        Args:
            provider_filtre: Sadece belirli bir provider'daki modeller

        Returns:
            [{"model": ..., "provider": ..., "api_tipi": ...}, ...]
        """
        sonuc = []
        for model_adi, provider_adi in self._model_provider_map.items():
            if provider_filtre and provider_adi != provider_filtre:
                continue
            api_tipi = PROVIDER_API_TIPI.get(provider_adi, "openai")
            sonuc.append({
                "model": model_adi,
                "provider": provider_adi,
                "api_tipi": api_tipi,
            })
        return sonuc

    def provider_modelleri(self, provider: str) -> list[str]:
        """Bir provider'daki tüm modelleri listele."""
        return [
            m for m, p in self._model_provider_map.items() if p == provider
        ]


# ── Singleton ────────────────────────────────────────────────────────────────

_router: Optional[ModelProviderRouter] = None
_router_lock = threading.Lock()


def router_al(
    config_yolu: Optional[str] = None,
    model_provider_map: Optional[dict[str, str]] = None,
    failover_zinciri: Optional[list[list[str]]] = None,
) -> ModelProviderRouter:
    """Thread-safe singleton erişimi."""
    global _router
    if _router is None:
        with _router_lock:
            if _router is None:
                _router = ModelProviderRouter(
                    config_yolu=config_yolu,
                    model_provider_map=model_provider_map,
                    failover_zinciri=failover_zinciri,
                )
    elif config_yolu or model_provider_map or failover_zinciri:
        # İlk kurulumdan sonra parametre değişikliği — log uyar
        logger.warning("[ModelRouter] router_al() parametreleri singleton sonrası yok sayıldı")
    return _router
