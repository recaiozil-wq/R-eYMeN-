# -*- coding: utf-8 -*-
"""model_metadata.py — Model Bilgileri ve Yetenekler.

Her modelin context penceresi, yetenekleri, fiyati ve
performans bilgilerini tutar.
"""

_MODEL_KATALOGU = {
    # Yerel modeller
    "cognitivecomputations.dolphin3.0-llama3.1-8b": {
        "provider": "lmstudio",
        "context": 8192,
        "vision": False,
        "fiyat": 0.0,
        "hiz": "orta",
        "dil": ["tr", "en"],
    },
    "llava-v1.6-mistral-7b": {
        "provider": "lmstudio",
        "context": 4096,
        "vision": True,
        "fiyat": 0.0,
        "hiz": "yavas",
        "dil": ["en"],
    },
    # DeepSeek
    "deepseek-chat": {
        "provider": "deepseek",
        "context": 65536,
        "vision": False,
        "fiyat": 0.14,
        "hiz": "hizli",
        "dil": ["tr", "en", "zh"],
    },
    "deepseek-reasoner": {
        "provider": "deepseek",
        "context": 65536,
        "vision": False,
        "fiyat": 0.55,
        "hiz": "orta",
        "dil": ["tr", "en", "zh"],
    },
    # OpenAI
    "gpt-4o-mini": {
        "provider": "openai",
        "context": 128000,
        "vision": True,
        "fiyat": 0.15,
        "hiz": "hizli",
        "dil": ["tr", "en"],
    },
    "gpt-4o": {
        "provider": "openai",
        "context": 128000,
        "vision": True,
        "fiyat": 2.50,
        "hiz": "hizli",
        "dil": ["tr", "en"],
    },
    # Anthropic
    "claude-haiku-4-5-20251001": {
        "provider": "anthropic",
        "context": 200000,
        "vision": True,
        "fiyat": 0.80,
        "hiz": "hizli",
        "dil": ["tr", "en"],
    },
    "claude-sonnet-4-20250514": {
        "provider": "anthropic",
        "context": 200000,
        "vision": True,
        "fiyat": 3.00,
        "hiz": "orta",
        "dil": ["tr", "en"],
    },
    # Groq
    "llama-3.1-8b-instant": {
        "provider": "groq",
        "context": 8192,
        "vision": False,
        "fiyat": 0.0,
        "hiz": "cok_hizli",
        "dil": ["en"],
    },
    "llama3-70b-8192": {
        "provider": "groq",
        "context": 8192,
        "vision": False,
        "fiyat": 0.0,
        "hiz": "cok_hizli",
        "dil": ["en"],
    },
}


def model_bilgisi(model_adi: str) -> dict:
    """Bir model hakkinda bilgi dondur.

    Args:
        model_adi: Model adi (tam veya alias)

    Returns:
        Model bilgileri sozlugu veya bos dict
    """
    return _MODEL_KATALOGU.get(model_adi, {})


def modele_gore_sec(istek: str, provider: str = "") -> list[str]:
    """Ihtiyaca gore model oner.

    Args:
        istek: Kullanici istegi
        provider: Provider filtresi (bos = tumu)

    Returns:
        Uygun model adlari listesi
    """
    vision_gerek = any(k in istek.lower() for k in ["gor", "resim", "foto", "gorsel", "screenshot"])
    turkce = any(k in istek.lower() for k in ["turkce", "turk"])
    uygun = []

    for ad, bilgi in _MODEL_KATALOGU.items():
        if provider and bilgi["provider"] != provider:
            continue
        if vision_gerek and not bilgi["vision"]:
            continue
        if turkce and "tr" not in bilgi.get("dil", []):
            continue
        uygun.append(ad)

    return uygun


def model_listele(provider: str = "") -> list[dict]:
    """Tum modelleri listele.

    Args:
        provider: Provider filtresi

    Returns:
        Model listesi
    """
    sonuc = []
    for ad, bilgi in _MODEL_KATALOGU.items():
        if provider and bilgi["provider"] != provider:
            continue
        sonuc.append({"ad": ad, **bilgi})
    return sonuc


def maliyet_hesapla(model_adi: str, token: int) -> float:
    """Bir model icin maliyet hesapla."""
    bilgi = model_bilgisi(model_adi)
    if not bilgi:
        return 0.0
    return bilgi.get("fiyat", 0) * (token / 1_000_000)


# Apache 2.0 — Hermes Agent'ten esinlenmistir
MINIMUM_CONTEXT_LENGTH = 4096


def get_model_context_length(model_id: str) -> int | None:
    """Model ID'sine gore context uzunlugunu dondur."""
    bilgi = _MODEL_KATALOGU.get(model_id, {})
    return bilgi.get("context") or None


if __name__ == "__main__":
    print("Tum modeller:")
    for m in model_listele():
        print(f"  {m['ad']}: {m['provider']}, {m['context']}ctx, ${m['fiyat']}/M, vision={m['vision']}")
    print(f"\nVision model onerisi: {modele_gore_sec('resim analiz et')}")
    print(f"Turkee model onerisi: {modele_gore_sec('turkce cevap ver')}")
