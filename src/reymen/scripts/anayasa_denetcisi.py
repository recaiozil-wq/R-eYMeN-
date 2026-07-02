# -*- coding: utf-8 -*-
"""
anayasa_denetcisi.py — Turkish content moderation / filtering module.

Exports:
    kural_varmi(text) -> (blocked: bool, reason: str)
    mesaj_guvenli_mi(text) -> bool
    _KESIN_GEC              — frozenset of safe Turkish words
    _ENGELLI_DESENLER       — list of compiled regex patterns for blocked content
    _KIBAR_IFADELER         — compiled regex matching polite Turkish phrases
"""

import re

# ---------------------------------------------------------------------------
# Safe words that are always allowed (kesin geçiş listesi)
# ---------------------------------------------------------------------------
_KESIN_GEC: frozenset = frozenset({
    "merhaba", "selam", "teşekkür", "teşekkürler", "günaydın",
    "iyi geceler", "lütfen", "rica", "yardım",
})

# ---------------------------------------------------------------------------
# Blocked content patterns (engelli desenler)
# ---------------------------------------------------------------------------
_ENGELLI_DESENLER: list = [
    # Turkish swear / profanity words (no trailing \b — catches substrings like siktir)
    re.compile(
        r"(?:\bamına\s*koyayım|"
        r"\bamk\b|"
        r"\bananı\s*sik|"
        r"\borospu\s*[çc]o[cç]u[ğg]u|"
        r"\borošpu|"
        r"\boroşpu|"
        r"\bsik(?:tir|ik|)\b|"
        r"\bpiç\b|"
        r"\bibne\b|"
        r"\byavşak\b|"
        r"\baptal\s*herif|"
        r"\bmal\s*mal\b)",
        re.IGNORECASE,
    ),
    # Bomb / explosive / malware / harmful instructions
    re.compile(
        r"(?:\bbomba\s*yap|"
        r"\bpatlayıcı\s*yap|"
        r"\btnt\s*yap|"
        r"\bmolotof|"
        r"\bnapalm\b|"
        r"\bbomb\s*making|"
        r"\bexplosive\s*device|"
        r"\bzararl[ıi]\s*yazılım|"
        r"\bnasıl\s*öldür|"
        r"\bcinayet\s*işle|"
        r"\badam\s*öldür|"
        r"\böldürmek\s*için)",
        re.IGNORECASE,
    ),
    # Three or more consecutive URLs (with OR without spaces between them)
    re.compile(
        r"(?:https?://[^\s<>\"]+|www\.[^\s<>\"]+)"
        r"(?:\s*(?:https?://[^\s<>\"]+|www\.[^\s<>\"]+)){2,}",
        re.IGNORECASE,
    ),
]

# ---------------------------------------------------------------------------
# Polite Turkish phrase patterns (kibar ifadeler)
# ---------------------------------------------------------------------------
_KIBAR_IFADELER: re.Pattern = re.compile(
    r"\b(?:"
    r"lütfen|teşekkür\s*ederim|teşekkürler|rica\s*ederim|"
    r"afferin|sağ\s*ol|sağol|ellerine\s*sağlık|"
    r"memnun\s*oldum|kusura\s*bakma|özür\s*dilerim|"
    r"pardon|afedersiniz|yardımcı\s*olabilir|"
    r"iyi\s*çalışmalar|kolay\s*gelsin|hayırlı\s*işler"
    r")\b",
    re.IGNORECASE,
)


def _desen_tarama(text: str) -> tuple:
    """Check text against blocked patterns. Returns (blocked, reason)."""
    for pat in _ENGELLI_DESENLER:
        m = pat.search(text)
        if m:
            return (True, f"Uygunsuz içerik tespit edildi: '{m.group()}'")
    return (False, "")


def kural_varmi(text) -> tuple:
    """Check whether *text* violates any content rule.

    Returns:
        (blocked: bool, reason: str)
    """
    if not isinstance(text, str):
        return (False, "")

    text_stripped = text.strip()
    if not text_stripped:
        return (False, "")

    # Blocked patterns — checked before all exemptions
    blocked, reason = _desen_tarama(text_stripped)
    if blocked:
        return (blocked, reason)

    # Short-message exemption: <= 5 words = auto-pass
    word_count = len(text_stripped.split())
    if word_count <= 5:
        return (False, "")

    # Safe-word exemption: all tokens are known safe words
    tokens = set(tok.lower() for tok in text_stripped.split())
    if tokens.issubset(_KESIN_GEC):
        return (False, "")

    # Polite phrase filter: if >= 50% of tokens are polite, let it pass
    kibars = _KIBAR_IFADELER.findall(text_stripped)
    if kibars and (len(kibars) / word_count) >= 0.5:
        return (False, "")

    return (False, "")


def mesaj_guvenli_mi(text: str) -> bool:
    """Return True if the message is safe to forward."""
    blocked, _ = kural_varmi(text)
    return not blocked
