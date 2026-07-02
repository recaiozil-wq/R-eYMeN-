# -*- coding: utf-8 -*-
"""redact.py — PII temizleme fonksiyonlari.

Email, telefon, kredi karti, API key, TC kimlik numarasi gibi
hassas bilgileri regex ile bulur ve maskeler.
"""

import re

# 1. Email: standard email format
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# 2. Telefon: exactly 10 contiguous digits starting with 1 or 5 (Turkcell/Vodafone/Turk Telekom)
_TELEFON_RE = re.compile(r"\b[15]\d{9}\b")

# 3. Kredi karti: 13-16 digits, optionally separated by spaces or dashes
_KART_RE = re.compile(r"\b(\d[ -]?){13,16}\b")

# 4. API Key: KEY=VALUE pattern where KEY contains API_KEY, TOKEN, SECRET etc.
#    Also catches sk-... prefixed tokens, KEY=VALUE patterns
_API_KEY_RE = re.compile(
    r"\b([A-Z_]*?(?:API_?KEY|TOKEN|SECRET|PASSWORD|AUTH)[A-Z_]*?)\s*=\s*['\"]?(\S+?)['\"]?\b",
    re.IGNORECASE,
)

# 5. TC Kimlik: exactly 11 digits, first digit 1-9 (cannot start with 0)
_TC_RE = re.compile(r"\b[1-9]\d{10}\b")


def email_temizle(text: str) -> str:
    """Email adreslerini [EMAIL] ile degistir."""
    if not text:
        return text
    return _EMAIL_RE.sub("[EMAIL]", text)


def telefon_temizle(text: str) -> str:
    """10 haneli telefon numaralarini [TELEFON] ile degistir.
    9 haneli sayilar temizlenmez (sadece 10 hane kurali)."""
    if not text:
        return text
    return _TELEFON_RE.sub("[TELEFON]", text)


def kart_temizle(text: str) -> str:
    """Kredi karti numaralarini [KART_NO] ile degistir.
    Destekler: 1234567890123456, 1234-5678-9012-3456, 1234 5678 9012 3456"""
    if not text:
        return text
    return _KART_RE.sub("[KART_NO]", text)


def api_key_temizle(text: str) -> str:
    """API key/token degerlerini [GIZLI] ile degistir.
    KEY=VALUE formatindaki degerleri maskeler."""
    if not text:
        return text

    def _mask(m):
        key = m.group(1)
        return f"{key}= [GIZLI]"

    return _API_KEY_RE.sub(_mask, text)


def tc_temizle(text: str) -> str:
    """TC kimlik numaralarini [TC_KIMLIK] ile degistir.
    0 ile baslayan 11 haneli sayilar gecersiz TC'dir, temizlenmez."""
    if not text:
        return text
    return _TC_RE.sub("[TC_KIMLIK]", text)


def tam_temizle(text: str) -> str:
    """Tum PII'yi tek geciste temizle."""
    if not text:
        return text
    sonuc = email_temizle(text)
    sonuc = telefon_temizle(sonuc)
    sonuc = kart_temizle(sonuc)
    sonuc = api_key_temizle(sonuc)
    sonuc = tc_temizle(sonuc)
    return sonuc
