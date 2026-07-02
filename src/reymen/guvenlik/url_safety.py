# -*- coding: utf-8 -*-
"""url_safety.py — URL Guvenlik Kontrolu.

Agent'in acacagi URL'leri guvenlik acisindan kontrol eder.
Zararli, phishing veya yasakli siteleri engeller.
"""

import re

# Yasakli protokoller
YASAKLI_PROTOKOLLER = [
    "file://",
    "ftp://",
    "smb://",
    "ldap://",
    "javascript:",
    "data:",
    "vbscript:",
]

# Guvenilmeyen TLD'ler (genelde kotu amacli)
RISKLI_TLD = [
    ".tk", ".ml", ".ga", ".cf", ".gq",  # ucretsiz TLD'ler
    ".xyz", ".top", ".loan", ".win", ".bid",
]

# Riskli anahtar kelimeler (URL icinde)
RISKLI_KELIMELER = [
    "login", "verify", "secure", "account",
    "update", "confirm", "banking", "password",
    "payment", "wallet", "recover", "2fa",
]


def url_guvenli_mi(url: str) -> tuple[bool, str]:
    """Bir URL'nin guvenli olup olmadigini kontrol et.

    Args:
        url: Kontrol edilecek URL

    Returns:
        (guvenli_mi, hata_mesaji)
    """
    url = url.strip().lower()

    # Protokol kontrolu
    for proto in YASAKLI_PROTOKOLLER:
        if url.startswith(proto):
            return False, f"Yasakli protokol: {proto}"

    # HTTP/HTTPS degilse engelle
    if not (url.startswith("http://") or url.startswith("https://")):
        return False, "Sadece HTTP/HTTPS protokollerine izin var."

    # Riskli TLD kontrolu
    for tld in RISKLI_TLD:
        if tld in url:
            return False, f"Guvenilmeyen TLD: {tld}"

    # Localhost'a izin var
    if "localhost" in url or "127.0.0.1" in url:
        return True, ""

    return True, ""


def url_temizle(url: str) -> str:
    """URL'den guvensiz parametreleri temizle."""
    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    if parsed.query:
        # Sadece guvenli parametrelere izin ver
        return urllib.parse.urlunparse(parsed._replace(query=""))
    return url


if __name__ == "__main__":
    testler = [
        "https://www.google.com",
        "file:///etc/passwd",
        "http://malicious.tk/login",
        "http://localhost:8080",
        "javascript:alert(1)",
    ]
    for t in testler:
        guvenli, mesaj = url_guvenli_mi(t)
        print(f"  {t}: {'GUVENLI' if guvenli else 'ENGELLENDI'} ({mesaj})")
