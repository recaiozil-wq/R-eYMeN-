# -*- coding: utf-8 -*-
"""API hata sınıflandırması — akıllı failover ve recovery için.

ReYMeN agent'ın error_classifier.py'sinden ReYMeN için adapte edilmiştir.
Tüm API hatalarını yapısal FailoverReason enum değerleriyle sınıflandırır;
retry loop doğrudan bu değerlere göre karar verir.
"""

from __future__ import annotations

import enum
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import logging
logger = logging.getLogger(__name__)

log = logging.getLogger("conversation_loop")


# ── Hata taksonomisi ────────────────────────────────────────────────────────

class FailoverNedeni(enum.Enum):
    """API çağrısının neden başarısız olduğu — recovery stratejisini belirler."""

    # Kimlik doğrulama / yetkilendirme
    auth = "auth"                           # Geçici auth (401/403) — yenile/döndür
    auth_kalici = "auth_kalici"             # Yenileme sonrası da auth hatası — durdur

    # Faturalama / kota
    faturalama = "faturalama"               # 402 veya kredi bitti — hemen döndür
    rate_limit = "rate_limit"               # 429 veya kota aşımı — bekle + döndür

    # Sunucu tarafı
    asiri_yuklu = "asiri_yuklu"             # 503/529 — backoff
    sunucu_hatasi = "sunucu_hatasi"         # 500/502 — yeniden dene

    # Transport
    zaman_asimi = "zaman_asimi"             # Bağlantı/okuma timeout — istemci yeniden kur

    # Context / payload
    context_tasma = "context_tasma"        # Context çok büyük — sıkıştır, failover değil
    payload_cok_buyuk = "payload_cok_buyuk"  # 413 — sıkıştır
    gorsel_cok_buyuk = "gorsel_cok_buyuk"   # Görselin sınırı aştı — küçült + yeniden dene

    # Model / provider politikası
    model_bulunamadi = "model_bulunamadi"   # 404 veya geçersiz model — fallback
    provider_politika_blok = "provider_politika_blok"  # Aggregatör blokları
    icerik_politika_blok = "icerik_politika_blok"      # Güvenlik filtresi — tekrar deneme yok

    # İstek formatı
    format_hatasi = "format_hatasi"         # 400 bad request — durdur veya düzelt + dene
    sifreli_icerik_gecersiz = "sifreli_icerik_gecersiz"  # Replay blobu reddedildi
    multimodal_arac_desteklenmiyor = "multimodal_arac_desteklenmiyor"  # Tool content liste türü reddedildi

    # Provider-specific
    dusunme_imzasi = "dusunme_imzasi"       # Anthropic thinking block imza hatası
    uzun_context_katmani = "uzun_context_katmani"  # Anthropic "extra usage" kapısı
    llama_cpp_gramer = "llama_cpp_gramer"   # llama.cpp json-schema-to-grammar pattern hatası

    # Catch-all
    bilinmiyor = "bilinmiyor"               # Sınıflandırılamadı — backoff ile yeniden dene


# Geriye uyumluluk: İngilizce isimler (ReYMeN kodlarıyla uyumlu)
class FailoverReason(enum.Enum):
    """ReYMeN API-uyumlu İngilizce alias'lar."""
    auth = "auth"
    auth_permanent = "auth_permanent"
    billing = "billing"
    rate_limit = "rate_limit"
    overloaded = "overloaded"
    server_error = "server_error"
    timeout = "timeout"
    context_overflow = "context_overflow"
    payload_too_large = "payload_too_large"
    image_too_large = "image_too_large"
    model_not_found = "model_not_found"
    provider_policy_blocked = "provider_policy_blocked"
    content_policy_blocked = "content_policy_blocked"
    format_error = "format_error"
    invalid_encrypted_content = "invalid_encrypted_content"
    multimodal_tool_content_unsupported = "multimodal_tool_content_unsupported"
    thinking_signature = "thinking_signature"
    long_context_tier = "long_context_tier"
    oauth_long_context_beta_forbidden = "oauth_long_context_beta_forbidden"
    llama_cpp_grammar_pattern = "llama_cpp_grammar_pattern"
    unknown = "unknown"


# ── Sınıflandırma sonucu ────────────────────────────────────────────────────

@dataclass
class SiniflandirilmisHata:
    """API hatasının yapısal sınıflandırması ve recovery önerileri."""

    neden: FailoverReason
    durum_kodu: Optional[int] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    mesaj: str = ""
    hata_baglami: Dict[str, Any] = field(default_factory=dict)

    # Recovery eylemi ipuçları
    yeniden_denenebilir: bool = True
    sikistirilmali: bool = False
    kimlik_dondurmeli: bool = False
    fallback_olmali: bool = False

    @property
    def is_auth(self) -> bool:
        return self.neden in {FailoverReason.auth, FailoverReason.auth_permanent}

    # ReYMeN API uyumluluğu için property'ler
    @property
    def reason(self) -> FailoverReason:
        return self.neden

    @property
    def retryable(self) -> bool:
        return self.yeniden_denenebilir

    @property
    def should_compress(self) -> bool:
        return self.sikistirilmali

    @property
    def should_rotate_credential(self) -> bool:
        return self.kimlik_dondurmeli

    @property
    def should_fallback(self) -> bool:
        return self.fallback_olmali


# ReYMeN uyumluluğu için alias
ClassifiedError = SiniflandirilmisHata


# ── Provider-specific örüntüler ─────────────────────────────────────────────

_FATURALAMA_ORNEKLERI = [
    "insufficient credits", "insufficient_quota", "insufficient balance",
    "credit balance", "credits exhausted", "credits have been exhausted",
    "no usable credits", "top up your credits", "payment required",
    "billing hard limit", "exceeded your current quota",
    "account is deactivated", "plan does not include",
    "out of funds", "run out of funds", "balance_depleted",
    "model_not_supported_on_free_tier", "not available on the free tier",
]

_RATE_LIMIT_ORNEKLERI = [
    "rate limit", "rate_limit", "too many requests", "throttled",
    "requests per minute", "tokens per minute", "requests per day",
    "try again in", "please retry after", "resource_exhausted",
    "rate increased too quickly", "throttlingexception",
    "too many concurrent requests", "servicequotaexceededexception",
]

_KULLANIM_LIMITI_ORNEKLERI = ["usage limit", "quota", "limit exceeded", "key limit exceeded"]

_KULLANIM_LIMITI_GECICI_SINYALLER = [
    "try again", "retry", "resets at", "reset in", "wait",
    "requests remaining", "periodic", "window",
]

_PAYLOAD_COK_BUYUK_ORNEKLERI = [
    "request entity too large", "payload too large", "error code: 413",
]

_GORSEL_COK_BUYUK_ORNEKLERI = [
    "image exceeds", "image too large", "image_too_large",
    "image size exceeds", "image dimensions exceed",
    "dimensions exceed max allowed size", "max allowed size: 8000",
]

_MULTIMODAL_ARAC_ORNEKLERI = [
    "text is not set", "tool message content must be a string",
    "tool content must be a string", "tool message must be a string",
    "expected string, got list", "expected string, got array",
    "tool_call.content must be string",
]

_CONTEXT_TASMA_ORNEKLERI = [
    "context length", "context size", "maximum context", "token limit",
    "too many tokens", "reduce the length", "exceeds the limit",
    "context window", "prompt is too long", "prompt exceeds max length",
    "max_tokens", "maximum number of tokens", "exceeds the max_model_len",
    "max_model_len", "prompt length", "input is too long",
    "maximum model length", "context length exceeded", "truncating input",
    "slot context", "n_ctx_slot", "超过最大长度", "上下文长度",
    "max input token", "input token", "exceeds the maximum number of input tokens",
]

_MODEL_BULUNAMADI_ORNEKLERI = [
    "is not a valid model", "invalid model", "model not found",
    "model_not_found", "does not exist", "no such model",
    "unknown model", "unsupported model",
]

_ISTEK_DOGRULAMA_ORNEKLERI = [
    "unknown parameter", "unsupported parameter",
    "unrecognized request argument", "invalid_request_error",
    "unknown_parameter", "unsupported_parameter",
]

_PROVIDER_POLITIKA_ORNEKLERI = [
    "no endpoints available matching your guardrail",
    "no endpoints available matching your data policy",
    "no endpoints found matching your data policy",
]

_ICERIK_POLITIKA_ORNEKLERI = [
    "flagged for possible cybersecurity risk", "trusted access for cyber",
    "violates our usage policies", "violates openai's usage policies",
    "your request was flagged by", "prompt was flagged by our safety",
    "responses cannot be generated due to safety",
    "content_filter", "responsibleaipolicyviolation",
]

_AUTH_ORNEKLERI = [
    "invalid api key", "invalid_api_key", "authentication",
    "unauthorized", "forbidden", "invalid token",
    "token expired", "token revoked", "access denied",
]

_ZAMAN_ASIMI_MESAJ_ORNEKLERI = [
    "timed out", "turn timed out", "request timed out",
    "deadline exceeded", "operation timed out", "upstream timed out",
]

_TRANSPORT_HATA_TIPLERI = frozenset({
    "ReadTimeout", "ConnectTimeout", "PoolTimeout",
    "ConnectError", "RemoteProtocolError",
    "ConnectionError", "ConnectionResetError",
    "ConnectionAbortedError", "BrokenPipeError",
    "TimeoutError", "ReadError", "ServerDisconnectedError",
    "SSLError", "SSLZeroReturnError", "SSLWantReadError",
    "SSLWantWriteError", "SSLEOFError", "SSLSyscallError",
    "APIConnectionError", "APITimeoutError",
})

_SUNUCU_BAGLANTI_KESILDI_ORNEKLERI = [
    "server disconnected", "peer closed connection",
    "connection reset by peer", "connection was closed",
    "network connection lost", "unexpected eof", "incomplete chunked read",
]

_SSL_GECICI_ORNEKLERI = [
    "bad record mac", "ssl alert", "tls alert", "ssl handshake failure",
    "tlsv1 alert", "sslv3 alert", "bad_record_mac", "ssl_alert",
    "tls_alert", "tls_alert_internal_error", "[ssl:",
]


# ── Sınıflandırma pipeline'ı ────────────────────────────────────────────────

def api_hatasini_siniflandir(
    hata: Exception,
    *,
    provider: str = "",
    model: str = "",
    yaklasik_token: int = 0,
    context_uzunlugu: int = 200_000,
    mesaj_sayisi: int = 0,
) -> SiniflandirilmisHata:
    """Bir API hatasını yapısal recovery önerisiyle sınıflandır.

    Öncelik sırası:
      1. Provider-specific özel durumlar (thinking imzaları, tier kapıları)
      2. HTTP durum kodu + mesaj bilinçli iyileştirme
      3. Hata kodu sınıflandırması (body'den)
      4. Mesaj örüntüsü eşleşmesi (faturalama vs rate_limit vs context vs auth)
      5. SSL/TLS geçici alert örüntüleri → timeout olarak yeniden dene
      6. Sunucu bağlantı kesilmesi + büyük oturum → context overflow
      7. Transport hata sezgiselleri
      8. Fallback: bilinmiyor (backoff ile yeniden dene)
    """
    durum_kodu = _durum_kodu_cikart(hata)
    hata_tipi = type(hata).__name__
    if durum_kodu is None and hata_tipi == "RateLimitError":
        durum_kodu = 429
    govde = _hata_govdesi_cikart(hata)
    hata_kodu = _hata_kodunu_cikart(govde)

    _ham_mesaj = str(hata).lower()
    _govde_mesaj = ""
    _metadata_mesaj = ""
    if isinstance(govde, dict):
        _hata_obj = govde.get("error", {})
        if isinstance(_hata_obj, dict):
            _govde_mesaj = str(_hata_obj.get("message") or "").lower()
            _metadata = _hata_obj.get("metadata", {})
            if isinstance(_metadata, dict):
                _ic_json = _metadata.get("raw") or ""
                if isinstance(_ic_json, str) and _ic_json.strip():
                    try:
                        _ic = json.loads(_ic_json)
                        if isinstance(_ic, dict):
                            _ic_hata = _ic.get("error", {})
                            if isinstance(_ic_hata, dict):
                                _metadata_mesaj = str(_ic_hata.get("message") or "").lower()
                    except (json.JSONDecodeError, TypeError) as _e:
                        logger.warning("[HataSiniflandirici] Tip hatasi (L302): %s", json.JSONDecodeError)
                        pass
        if not _govde_mesaj:
            _govde_mesaj = str(govde.get("message") or "").lower()

    parcalar = [_ham_mesaj]
    if _govde_mesaj and _govde_mesaj not in _ham_mesaj:
        parcalar.append(_govde_mesaj)
    if _metadata_mesaj and _metadata_mesaj not in _ham_mesaj and _metadata_mesaj not in _govde_mesaj:
        parcalar.append(_metadata_mesaj)
    hata_mesaj = " ".join(parcalar)

    def _sonuc(neden: FailoverReason, **gecisgeler) -> SiniflandirilmisHata:
        varsayilanlar = {
            "neden": neden,
            "durum_kodu": durum_kodu,
            "provider": provider,
            "model": model,
            "mesaj": _mesaj_cikart(hata, govde),
        }
        varsayilanlar.update(gecisgeler)
        return SiniflandirilmisHata(**varsayilanlar)

    # ── 1. Provider-specific özel durumlar ──────────────────────────────
    if any(p in hata_mesaj for p in _ICERIK_POLITIKA_ORNEKLERI):
        return _sonuc(FailoverReason.content_policy_blocked, yeniden_denenebilir=False, fallback_olmali=True)

    if (
        durum_kodu == 400 and "thinking" in hata_mesaj
        and ("signature" in hata_mesaj or "cannot be modified" in hata_mesaj
             or "must remain as they were" in hata_mesaj)
    ):
        return _sonuc(FailoverReason.thinking_signature, yeniden_denenebilir=True, sikistirilmali=False)

    if durum_kodu == 429 and "extra usage" in hata_mesaj and "long context" in hata_mesaj:
        return _sonuc(FailoverReason.long_context_tier, yeniden_denenebilir=True, sikistirilmali=True)

    if durum_kodu == 400 and "long context beta" in hata_mesaj and "not yet available" in hata_mesaj:
        return _sonuc(FailoverReason.oauth_long_context_beta_forbidden, yeniden_denenebilir=True)

    if (
        durum_kodu == 400
        and ("error parsing grammar" in hata_mesaj or "json-schema-to-grammar" in hata_mesaj
             or ("unable to generate parser" in hata_mesaj and "template" in hata_mesaj))
    ):
        return _sonuc(FailoverReason.llama_cpp_grammar_pattern, yeniden_denenebilir=True)

    if (
        "do not have an active grok subscription" in hata_mesaj
        or ("out of available resources" in hata_mesaj and "grok" in hata_mesaj)
    ):
        return _sonuc(FailoverReason.auth, yeniden_denenebilir=False, fallback_olmali=True)

    # ── 2. HTTP durum kodu sınıflandırması ──────────────────────────────
    if durum_kodu is not None:
        siniflandirilmis = _duruma_gore_siniflandir(
            durum_kodu, hata_mesaj, hata_kodu, govde,
            yaklasik_token=yaklasik_token, context_uzunlugu=context_uzunlugu,
            mesaj_sayisi=mesaj_sayisi, sonuc_fn=_sonuc,
        )
        if siniflandirilmis is not None:
            return siniflandirilmis

    # ── 3. Hata kodu sınıflandırması ────────────────────────────────────
    if hata_kodu:
        siniflandirilmis = _koda_gore_siniflandir(hata_kodu, hata_mesaj, _sonuc)
        if siniflandirilmis is not None:
            return siniflandirilmis

    # ── 4. Mesaj örüntüsü eşleşmesi ─────────────────────────────────────
    siniflandirilmis = _mesaja_gore_siniflandir(
        hata_mesaj, hata_tipi,
        yaklasik_token=yaklasik_token, context_uzunlugu=context_uzunlugu,
        sonuc_fn=_sonuc,
    )
    if siniflandirilmis is not None:
        return siniflandirilmis

    # ── 5. SSL/TLS geçici hatalar → timeout ─────────────────────────────
    if any(p in hata_mesaj for p in _SSL_GECICI_ORNEKLERI):
        return _sonuc(FailoverReason.timeout, yeniden_denenebilir=True)

    # ── 6. Sunucu bağlantı kesilmesi + büyük oturum → context overflow ──
    baglanti_kesildi = any(p in hata_mesaj for p in _SUNUCU_BAGLANTI_KESILDI_ORNEKLERI)
    if baglanti_kesildi and not durum_kodu:
        buyuk_oturum = yaklasik_token > context_uzunlugu * 0.6 or (
            context_uzunlugu <= 256_000 and (yaklasik_token > 120_000 or mesaj_sayisi > 200)
        )
        if buyuk_oturum:
            return _sonuc(FailoverReason.context_overflow, yeniden_denenebilir=True, sikistirilmali=True)
        return _sonuc(FailoverReason.timeout, yeniden_denenebilir=True)

    # ── 7. Transport / timeout sezgiselleri ─────────────────────────────
    if hata_tipi in _TRANSPORT_HATA_TIPLERI or isinstance(hata, (TimeoutError, ConnectionError, OSError)):
        return _sonuc(FailoverReason.timeout, yeniden_denenebilir=True)

    # ── 8. Fallback: bilinmiyor ──────────────────────────────────────────
    return _sonuc(FailoverReason.unknown, yeniden_denenebilir=True)


# ReYMeN uyumluluğu için İngilizce alias
classify_api_error = api_hatasini_siniflandir


# ── Durum koduna göre sınıflandırma ─────────────────────────────────────────

def _duruma_gore_siniflandir(
    durum_kodu: int, hata_mesaj: str, hata_kodu: str, govde: dict,
    *, yaklasik_token: int, context_uzunlugu: int, mesaj_sayisi: int = 0, sonuc_fn,
) -> Optional[SiniflandirilmisHata]:

    if durum_kodu == 401:
        return sonuc_fn(FailoverReason.auth, yeniden_denenebilir=False,
                        kimlik_dondurmeli=True, fallback_olmali=True)

    if durum_kodu == 403:
        if ("key limit exceeded" in hata_mesaj or "spending limit" in hata_mesaj
                or any(p in hata_mesaj for p in _FATURALAMA_ORNEKLERI)):
            return sonuc_fn(FailoverReason.billing, yeniden_denenebilir=False,
                            kimlik_dondurmeli=True, fallback_olmali=True)
        return sonuc_fn(FailoverReason.auth, yeniden_denenebilir=False, fallback_olmali=True)

    if durum_kodu == 402:
        return _402_siniflandir(hata_mesaj, sonuc_fn)

    if durum_kodu == 404:
        if any(p in hata_mesaj for p in _FATURALAMA_ORNEKLERI):
            return sonuc_fn(FailoverReason.billing, yeniden_denenebilir=False,
                            kimlik_dondurmeli=True, fallback_olmali=True)
        if any(p in hata_mesaj for p in _PROVIDER_POLITIKA_ORNEKLERI):
            return sonuc_fn(FailoverReason.provider_policy_blocked, yeniden_denenebilir=False)
        if any(p in hata_mesaj for p in _MODEL_BULUNAMADI_ORNEKLERI):
            return sonuc_fn(FailoverReason.model_not_found, yeniden_denenebilir=False, fallback_olmali=True)
        return sonuc_fn(FailoverReason.unknown, yeniden_denenebilir=True)

    if durum_kodu == 413:
        return sonuc_fn(FailoverReason.payload_too_large, yeniden_denenebilir=True, sikistirilmali=True)

    if durum_kodu == 429:
        return sonuc_fn(FailoverReason.rate_limit, yeniden_denenebilir=True,
                        kimlik_dondurmeli=True, fallback_olmali=True)

    if durum_kodu == 400:
        return _400_siniflandir(
            hata_mesaj, hata_kodu, govde,
            yaklasik_token=yaklasik_token, context_uzunlugu=context_uzunlugu,
            mesaj_sayisi=mesaj_sayisi, sonuc_fn=sonuc_fn,
        )

    if durum_kodu in {500, 502}:
        if (any(p in hata_mesaj for p in _ISTEK_DOGRULAMA_ORNEKLERI)
                or hata_kodu.lower() in {"invalid_request_error", "unknown_parameter", "unsupported_parameter"}):
            return sonuc_fn(FailoverReason.format_error, yeniden_denenebilir=False, fallback_olmali=True)
        return sonuc_fn(FailoverReason.server_error, yeniden_denenebilir=True)

    if durum_kodu in {503, 529}:
        return sonuc_fn(FailoverReason.overloaded, yeniden_denenebilir=True)

    if 400 <= durum_kodu < 500:
        return sonuc_fn(FailoverReason.format_error, yeniden_denenebilir=False, fallback_olmali=True)

    if 500 <= durum_kodu < 600:
        return sonuc_fn(FailoverReason.server_error, yeniden_denenebilir=True)

    return None


def _402_siniflandir(hata_mesaj: str, sonuc_fn) -> SiniflandirilmisHata:
    """402: faturalama bitişi vs geçici kullanım limiti."""
    kullanim_limiti_var = any(p in hata_mesaj for p in _KULLANIM_LIMITI_ORNEKLERI)
    gecici_sinyal_var = any(p in hata_mesaj for p in _KULLANIM_LIMITI_GECICI_SINYALLER)
    if kullanim_limiti_var and gecici_sinyal_var:
        return sonuc_fn(FailoverReason.rate_limit, yeniden_denenebilir=True,
                        kimlik_dondurmeli=True, fallback_olmali=True)
    return sonuc_fn(FailoverReason.billing, yeniden_denenebilir=False,
                    kimlik_dondurmeli=True, fallback_olmali=True)


def _400_siniflandir(
    hata_mesaj: str, hata_kodu: str, govde: dict,
    *, yaklasik_token: int, context_uzunlugu: int, mesaj_sayisi: int = 0, sonuc_fn,
) -> SiniflandirilmisHata:
    """400 Bad Request — context overflow, format hatası, veya genel."""

    if any(p in hata_mesaj for p in _MULTIMODAL_ARAC_ORNEKLERI):
        return sonuc_fn(FailoverReason.multimodal_tool_content_unsupported, yeniden_denenebilir=True)

    if any(p in hata_mesaj for p in _GORSEL_COK_BUYUK_ORNEKLERI):
        return sonuc_fn(FailoverReason.image_too_large, yeniden_denenebilir=True)

    hata_kodu_kucuk = (hata_kodu or "").lower()
    if (hata_kodu_kucuk == "invalid_encrypted_content"
            or "invalid_encrypted_content" in hata_mesaj
            or ("encrypted content for item" in hata_mesaj and "could not be verified" in hata_mesaj)):
        return sonuc_fn(FailoverReason.invalid_encrypted_content, yeniden_denenebilir=True, fallback_olmali=False)

    if (any(p in hata_mesaj for p in _ISTEK_DOGRULAMA_ORNEKLERI if p != "invalid_request_error")
            or hata_kodu_kucuk in {"unknown_parameter", "unsupported_parameter"}):
        return sonuc_fn(FailoverReason.format_error, yeniden_denenebilir=False, fallback_olmali=True)

    if any(p in hata_mesaj for p in _CONTEXT_TASMA_ORNEKLERI):
        return sonuc_fn(FailoverReason.context_overflow, yeniden_denenebilir=True, sikistirilmali=True)

    if any(p in hata_mesaj for p in _PROVIDER_POLITIKA_ORNEKLERI):
        return sonuc_fn(FailoverReason.provider_policy_blocked, yeniden_denenebilir=False)
    if any(p in hata_mesaj for p in _MODEL_BULUNAMADI_ORNEKLERI):
        return sonuc_fn(FailoverReason.model_not_found, yeniden_denenebilir=False, fallback_olmali=True)

    if any(p in hata_mesaj for p in _RATE_LIMIT_ORNEKLERI):
        return sonuc_fn(FailoverReason.rate_limit, yeniden_denenebilir=True,
                        kimlik_dondurmeli=True, fallback_olmali=True)
    if any(p in hata_mesaj for p in _FATURALAMA_ORNEKLERI):
        return sonuc_fn(FailoverReason.billing, yeniden_denenebilir=False,
                        kimlik_dondurmeli=True, fallback_olmali=True)

    # Genel 400 + büyük oturum → muhtemel context overflow
    govde_mesaj = ""
    if isinstance(govde, dict):
        _hata_obj = govde.get("error", {})
        if isinstance(_hata_obj, dict):
            govde_mesaj = str(_hata_obj.get("message") or "").strip().lower()
        if not govde_mesaj:
            govde_mesaj = str(govde.get("message") or "").strip().lower()

    genel = len(govde_mesaj) < 30 or govde_mesaj in {"error", ""}
    buyuk = yaklasik_token > context_uzunlugu * 0.4 or (
        context_uzunlugu <= 256_000 and (yaklasik_token > 80_000 or mesaj_sayisi > 80)
    )
    if genel and buyuk:
        return sonuc_fn(FailoverReason.context_overflow, yeniden_denenebilir=True, sikistirilmali=True)

    return sonuc_fn(FailoverReason.format_error, yeniden_denenebilir=False, fallback_olmali=True)


# ── Hata koduna göre sınıflandırma ──────────────────────────────────────────

def _koda_gore_siniflandir(hata_kodu: str, hata_mesaj: str, sonuc_fn) -> Optional[SiniflandirilmisHata]:
    kod = hata_kodu.lower()

    if kod in {"resource_exhausted", "throttled", "rate_limit_exceeded"}:
        return sonuc_fn(FailoverReason.rate_limit, yeniden_denenebilir=True, kimlik_dondurmeli=True)

    if kod in {"insufficient_quota", "billing_not_active", "payment_required",
               "insufficient_credits", "no_usable_credits", "balance_depleted",
               "model_not_supported_on_free_tier"}:
        return sonuc_fn(FailoverReason.billing, yeniden_denenebilir=False,
                        kimlik_dondurmeli=True, fallback_olmali=True)

    if kod in {"model_not_found", "model_not_available", "invalid_model"}:
        return sonuc_fn(FailoverReason.model_not_found, yeniden_denenebilir=False, fallback_olmali=True)

    if kod in {"context_length_exceeded", "max_tokens_exceeded"}:
        return sonuc_fn(FailoverReason.context_overflow, yeniden_denenebilir=True, sikistirilmali=True)

    if kod == "invalid_encrypted_content":
        return sonuc_fn(FailoverReason.invalid_encrypted_content, yeniden_denenebilir=True)

    return None


# ── Mesaja göre sınıflandırma ────────────────────────────────────────────────

def _mesaja_gore_siniflandir(
    hata_mesaj: str, hata_tipi: str,
    *, yaklasik_token: int, context_uzunlugu: int, sonuc_fn,
) -> Optional[SiniflandirilmisHata]:

    if any(p in hata_mesaj for p in _PAYLOAD_COK_BUYUK_ORNEKLERI):
        return sonuc_fn(FailoverReason.payload_too_large, yeniden_denenebilir=True, sikistirilmali=True)

    if any(p in hata_mesaj for p in _MULTIMODAL_ARAC_ORNEKLERI):
        return sonuc_fn(FailoverReason.multimodal_tool_content_unsupported, yeniden_denenebilir=True)

    if any(p in hata_mesaj for p in _GORSEL_COK_BUYUK_ORNEKLERI):
        return sonuc_fn(FailoverReason.image_too_large, yeniden_denenebilir=True)

    kullanim_limiti_var = any(p in hata_mesaj for p in _KULLANIM_LIMITI_ORNEKLERI)
    if kullanim_limiti_var:
        gecici = any(p in hata_mesaj for p in _KULLANIM_LIMITI_GECICI_SINYALLER)
        if gecici:
            return sonuc_fn(FailoverReason.rate_limit, yeniden_denenebilir=True,
                            kimlik_dondurmeli=True, fallback_olmali=True)
        return sonuc_fn(FailoverReason.billing, yeniden_denenebilir=False,
                        kimlik_dondurmeli=True, fallback_olmali=True)

    if any(p in hata_mesaj for p in _FATURALAMA_ORNEKLERI):
        return sonuc_fn(FailoverReason.billing, yeniden_denenebilir=False,
                        kimlik_dondurmeli=True, fallback_olmali=True)

    if any(p in hata_mesaj for p in _RATE_LIMIT_ORNEKLERI):
        return sonuc_fn(FailoverReason.rate_limit, yeniden_denenebilir=True,
                        kimlik_dondurmeli=True, fallback_olmali=True)

    if any(p in hata_mesaj for p in _CONTEXT_TASMA_ORNEKLERI):
        return sonuc_fn(FailoverReason.context_overflow, yeniden_denenebilir=True, sikistirilmali=True)

    if any(p in hata_mesaj for p in _AUTH_ORNEKLERI):
        return sonuc_fn(FailoverReason.auth, yeniden_denenebilir=False,
                        kimlik_dondurmeli=True, fallback_olmali=True)

    if any(p in hata_mesaj for p in _PROVIDER_POLITIKA_ORNEKLERI):
        return sonuc_fn(FailoverReason.provider_policy_blocked, yeniden_denenebilir=False)

    if any(p in hata_mesaj for p in _MODEL_BULUNAMADI_ORNEKLERI):
        return sonuc_fn(FailoverReason.model_not_found, yeniden_denenebilir=False, fallback_olmali=True)

    if any(p in hata_mesaj for p in _ZAMAN_ASIMI_MESAJ_ORNEKLERI):
        return sonuc_fn(FailoverReason.timeout, yeniden_denenebilir=True)

    return None


# ── Yardımcı fonksiyonlar ────────────────────────────────────────────────────

def _durum_kodu_cikart(hata: Exception) -> Optional[int]:
    """Hata zincirinde HTTP durum kodunu bul."""
    current = hata
    for _ in range(5):
        kod = getattr(current, "status_code", None)
        if isinstance(kod, int):
            return kod
        kod = getattr(current, "status", None)
        if isinstance(kod, int) and 100 <= kod < 600:
            return kod
        sebep = getattr(current, "__cause__", None) or getattr(current, "__context__", None)
        if sebep is None or sebep is current:
            break
        current = sebep
    return None


def _hata_govdesi_cikart(hata: Exception) -> dict:
    """SDK exception'dan yapısal hata gövdesi çıkart."""
    govde = getattr(hata, "body", None)
    if isinstance(govde, dict):
        return govde
    yanit = getattr(hata, "response", None)
    if yanit is not None:
        try:
            json_govde = yanit.json()
            if isinstance(json_govde, dict):
                return json_govde
        except Exception as _e:
            logger.warning("[HataSiniflandirici] except Exception (L644): %s", Exception)
            pass
    return {}


def _hata_kodunu_cikart(govde: dict) -> str:
    """Yanıt gövdesinden hata kodu string'i çıkart."""
    if not govde:
        return ""

    def _koddan_cikart(payload) -> str:
        if not isinstance(payload, dict):
            return ""
        payload_hata = payload.get("error", {})
        if isinstance(payload_hata, dict):
            ic = payload_hata.get("code") or payload_hata.get("type") or ""
            if isinstance(ic, str) and ic.strip() and ic.strip() != "400":
                return ic.strip()
        kod = payload.get("code") or payload.get("error_code") or ""
        if isinstance(kod, (str, int)):
            metin = str(kod).strip()
            if metin and metin != "400":
                return metin
        return ""

    hata_obj = govde.get("error", {})
    if isinstance(hata_obj, dict):
        kod = hata_obj.get("code") or hata_obj.get("type") or ""
        if isinstance(kod, str) and kod.strip() and kod.strip() != "400":
            return kod.strip()
        mesaj = hata_obj.get("message")
        if isinstance(mesaj, str) and mesaj.strip().startswith("{"):
            try:
                ic = json.loads(mesaj)
                ic_kod = _koddan_cikart(ic)
                if ic_kod:
                    return ic_kod
            except (json.JSONDecodeError, TypeError) as _e:
                logger.warning("[HataSiniflandirici] Tip hatasi (L681): %s", json.JSONDecodeError)
                pass

    kod = govde.get("code") or govde.get("error_code") or ""
    if isinstance(kod, (str, int)):
        metin = str(kod).strip()
        if metin and metin != "400":
            return metin
    return ""


def _mesaj_cikart(hata: Exception, govde: dict) -> str:
    """En bilgilendirici hata mesajını çıkart."""
    if govde:
        hata_obj = govde.get("error", {})
        if isinstance(hata_obj, dict):
            mesaj = hata_obj.get("message", "")
            if isinstance(mesaj, str) and mesaj.strip():
                return mesaj.strip()[:500]
        mesaj = govde.get("message", "")
        if isinstance(mesaj, str) and mesaj.strip():
            return mesaj.strip()[:500]
    return str(hata)[:500]
