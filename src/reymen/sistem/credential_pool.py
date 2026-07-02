# -*- coding: utf-8 -*-
"""credential_pool.py — Kimlik Havuzu.

Birden fazla kaynaktan (env, dosya, Windows Credential Manager)
API anahtarlarini toplar ve yonetir.
"""

import os
import re
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

PROJE_KOK = Path(__file__).parent.resolve()


def _platform_env_yolu() -> Path:
    """Platform-bagimsiz .env yolu. Windows: APPDATA/Local/ReYMeN; Linux: ~/.config/reymen"""
    import platform
    ev = Path.home()
    if platform.system() == "Windows":
        return ev / "AppData" / "Local" / "reymen" / ".env"
    return ev / ".config" / "reymen" / ".env"


ReYMeN_ENV = _platform_env_yolu()

# Hangi anahtarlarin hangi kaynaklardan alinacagi
_ANAHTAR_KAYNAKLARI = {
    "DEEPSEEK_API_KEY": ["ReYMeN_env", "ReYMeN_env", "wcm"],
    "OPENAI_API_KEY": ["ReYMeN_env", "ReYMeN_env", "wcm"],
    "ANTHROPIC_API_KEY": ["ReYMeN_env", "ReYMeN_env", "wcm"],
    "GROQ_API_KEY": ["ReYMeN_env", "ReYMeN_env", "wcm"],
    "TELEGRAM_BOT_TOKEN": ["ReYMeN_env", "ReYMeN_env"],
    "NOTION_API_TOKEN": ["ReYMeN_env"],
}


class CredentialPool:
    """Kimlik havuzu.

    Kullanim:
        pool = CredentialPool()
        anahtar = pool.al("DEEPSEEK_API_KEY")
        # "sk-xxx..." veya ""
    """

    def __init__(self):
        self._cache: dict[str, str] = {}
        self._kaynak_sirasi = ["ReYMeN_env", "ReYMeN_env", "wcm"]

    def _env_oku(self, dosya_yolu: Path) -> dict[str, str]:
        """Bir .env dosyasini oku ve sozluk olarak dondur."""
        sonuc = {}
        if not dosya_yolu.exists():
            return sonuc
        for satir in dosya_yolu.read_text(encoding="utf-8").split("\n"):
            satir = satir.strip()
            if not satir or satir.startswith("#") or "=" not in satir:
                continue
            anahtar, deger = satir.split("=", 1)
            deger = deger.strip().strip("\"'")
            if deger and not deger.startswith("***"):
                sonuc[anahtar.strip()] = deger
        return sonuc

    def _wcm_oku(self, anahtar: str) -> str:
        """Windows Credential Manager'dan anahtar oku."""
        try:
            import win32cred
            cred = win32cred.CredRead(f"ReYMeN_{anahtar}", win32cred.CRED_TYPE_GENERIC, 0)
            return cred["CredentialBlob"].decode("utf-16").strip()
        except Exception:
            return ""

    def al(self, anahtar: str) -> str:
        """Bir API anahtarini bul.

        Args:
            anahtar: Anahtar adi (DEEPSEEK_API_KEY vb.)

        Returns:
            Anahtar degeri veya ""
        """
        # Cache kontrol
        if anahtar in self._cache:
            return self._cache[anahtar]

        # WCM (Windows Credential Manager) once dene
        try:
            from reymen.sistem.credential_persistence import CredentialPersistence
            wcm = CredentialPersistence()
            wcm_val = wcm.wcm_oku(anahtar)
            if wcm_val:
                self._cache[anahtar] = wcm_val
                return wcm_val
        except Exception as _e:
            logger.warning("[CredentialPool] except Exception (L95): %s", Exception)
            pass

        # Once os.environ
        env_val = os.environ.get(anahtar, "")
        if env_val and not env_val.startswith("***"):
            self._cache[anahtar] = env_val
            return env_val

        # Kaynak sirasina gore dene
        for kaynak in _ANAHTAR_KAYNAKLARI.get(anahtar, []):
            deger = ""
            if kaynak == "ReYMeN_env":
                envler = self._env_oku(PROJE_KOK / ".env")
                deger = envler.get(anahtar, "")
            elif kaynak == "ReYMeN_env":
                envler = self._env_oku(ReYMeN_ENV)
                deger = envler.get(anahtar, "")
            elif kaynak == "wcm":
                deger = self._wcm_oku(anahtar)

            if deger:
                self._cache[anahtar] = deger
                return deger

        return ""

    def tum_anahtarlar(self) -> dict[str, str]:
        """Tum bilinen anahtarlari getir (maskeli)."""
        sonuc = {}
        for anahtar in _ANAHTAR_KAYNAKLARI:
            deger = self.al(anahtar)
            if deger:
                sonuc[anahtar] = deger[:6] + "***" if len(deger) > 6 else deger
            else:
                sonuc[anahtar] = "YOK"
        return sonuc

    def durum(self) -> str:
        """Kimlik havuzu durumu."""
        anahtarlar = self.tum_anahtarlar()
        gecerli = sum(1 for v in anahtarlar.values() if v != "YOK")
        satirlar = [f"[CredentialPool] {gecerli}/{len(anahtarlar)} anahtar gecerli:\n"]
        for k, v in anahtarlar.items():
            satirlar.append(f"  {k:<25} {v}")
        return "\n".join(satirlar)

    def temizle(self):
        """Cache'i temizle (yeni okuma zorla)."""
        self._cache = {}


# Global instance
_pool = CredentialPool()


def anahtar_al(anahtar: str) -> str:
    return _pool.al(anahtar)


if __name__ == "__main__":
    p = CredentialPool()
    print(p.durum())
    print(f"\nDeepSeek: {p.al('DEEPSEEK_API_KEY')[:10] or 'YOK'}")
