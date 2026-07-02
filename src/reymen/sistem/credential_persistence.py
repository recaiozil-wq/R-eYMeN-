# -*- coding: utf-8 -*-
"""credential_persistence.py — Kimlik Kaliciligi.

API anahtarlarini Windows Credential Manager veya
sifrelenmis dosyada kalici olarak saklar.
"""

import os
from pathlib import Path

CRED_DOSYASI = Path(__file__).parent / ".ReYMeN" / "credentials.enc"


import logging

logger = logging.getLogger(__name__)


class CredentialPersistence:
    """Kimlik kalicilik yoneticisi.

    API anahtarlarini Windows Credential Manager'da
    veya sifrelenmis dosyada saklar.
    """

    def __init__(self):
        self._wcm_available = False
        self._wcm = None
        try:
            import win32cred
            self._wcm = win32cred
            self._wcm_available = True
        except ImportError:
            self._wcm_available = False

    def _basit_sifrele(self, veri: str) -> bytes:
        """Basit XOR sifreleme (guclu degil, sadece duz metin korumasi)."""
        anahtar = b"ReYMeN_SECRET_KEY_2026"
        return bytes(
            ord(c) ^ anahtar[i % len(anahtar)]
            for i, c in enumerate(veri)
        )

    def _basit_coz(self, veri: bytes) -> str:
        anahtar = b"ReYMeN_SECRET_KEY_2026"
        return "".join(
            chr(b ^ anahtar[i % len(anahtar)])
            for i, b in enumerate(veri)
        )

    def wcm_kaydet(self, anahtar: str, deger: str) -> bool:
        """Windows Credential Manager'a kaydet.

        Args:
            anahtar: Anahtar adi (ornek: DEEPSEEK_API_KEY)
            deger: Anahtar degeri

        Returns:
            Basarili mi?
        """
        if not self._wcm_available:
            return False
        try:
            import pywintypes
            cred_type = self._wcm.CRED_TYPE_GENERIC
            target = f"ReYMeN_{anahtar}"
            self._wcm.CredWrite(
                {
                    "Type": cred_type,
                    "TargetName": target,
                    "CredentialBlob": deger,
                    "Persist": self._wcm.CRED_PERSIST_LOCAL_MACHINE,
                },
                0,
            )
            return True
        except Exception:
            return False

    def wcm_oku(self, anahtar: str) -> str:
        """Windows Credential Manager'dan oku."""
        if not self._wcm_available:
            return ""
        try:
            target = f"ReYMeN_{anahtar}"
            cred = self._wcm.CredRead(target, self._wcm.CRED_TYPE_GENERIC, 0)
            return cred["CredentialBlob"].decode("utf-16").strip()
        except Exception as e:
            logger.debug("WCM'de %s bulunamadi (kod: %s)", anahtar, e)
            return ""

    def wcm_sil(self, anahtar: str) -> bool:
        """Windows Credential Manager'dan sil."""
        if not self._wcm_available:
            return False
        try:
            target = f"ReYMeN_{anahtar}"
            self._wcm.CredDelete(target, self._wcm.CRED_TYPE_GENERIC, 0)
            return True
        except Exception:
            return False

    def dosya_kaydet(self, anahtarlar: dict[str, str]) -> bool:
        """Anahtarlari sifrelenmis dosyaya kaydet.

        Args:
            anahtarlar: {anahtar_adi: deger} sozlugu

        Returns:
            Basarili mi?
        """
        try:
            import json
            veri = json.dumps(anahtarlar)
            sifreli = self._basit_sifrele(veri)
            CRED_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
            CRED_DOSYASI.write_bytes(sifreli)
            return True
        except Exception:
            return False

    def dosya_oku(self) -> dict[str, str]:
        """Sifrelenmis dosyadan anahtarlari oku."""
        if not CRED_DOSYASI.exists():
            return {}
        try:
            import json
            sifreli = CRED_DOSYASI.read_bytes()
            veri = self._basit_coz(sifreli)
            return json.loads(veri)
        except Exception:
            return {}

    def durum(self) -> str:
        """Kalicilik durumu."""
        wcm = "VAR" if self._wcm_available else "YOK"
        dosya = "VAR" if CRED_DOSYASI.exists() else "YOK"
        return f"[CredPersistence] WCM: {wcm}, Dosya: {dosya}"


if __name__ == "__main__":
    p = CredentialPersistence()
    print(p.durum())
    p.dosya_kaydet({"TEST_KEY": "test_value"})
    print(f"Dosyadan okunan: {p.dosya_oku()}")
