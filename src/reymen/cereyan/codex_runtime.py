# -*- coding: utf-8 -*-
"""codex_runtime.py — OpenAI Codex CLI Runtime Adaptoru.

Codex CLI'yi bir LLM provider olarak sarar. Codex'i
diger provider'larla ayni sekilde kullanmayi saglar.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class CodexRuntime:
    """Codex CLI runtime wrapper.

    Kullanim:
        rt = CodexRuntime()
        sonuc = rt.uret("Merhaba", [{"role": "user", "content": "2+2?"}])
    """

    def __init__(self, codex_yolu: Optional[Path] = None):
        self.codex_yolu = codex_yolu or self._codex_bul()
        self._hazir = self.codex_yolu is not None

    def _codex_bul(self) -> Optional[Path]:
        """Codex CLI binary'sini bul."""
        adaylar = [
            Path.home() / ".codex" / "bin" / "codex",
            Path.home() / "AppData" / "Local" / "codex" / "bin" / "codex.exe",
            Path("/usr/local/bin/codex"),
            Path("/usr/bin/codex"),
        ]
        for a in adaylar:
            if a.exists():
                return a
        # which ile dene
        try:
            r = subprocess.run(["where", "codex"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                return Path(r.stdout.strip().split("\n")[0])
        except Exception as _e:
            logger.warning("[CodexRuntime] except Exception (L45): %s", Exception)
            pass
        try:
            r = subprocess.run(["which", "codex"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                return Path(r.stdout.strip())
        except Exception as _e:
            logger.warning("[CodexRuntime] except Exception (L51): %s", Exception)
            pass
        return None

    @property
    def hazir_mi(self) -> bool:
        return self._hazir

    def ping(self) -> bool:
        """Codex CLI erisilebilir mi?"""
        if not self._hazir:
            return False
        try:
            r = subprocess.run(
                [str(self.codex_yolu), "--version"],
                capture_output=True, text=True, timeout=10,
            )
            return r.returncode == 0
        except Exception:
            return False

    def uret(self, sistem_prompt: str, mesajlar: list, timeout: int = 120) -> str:
        """Codex CLI ile yanit uret.

        Args:
            sistem_prompt: Sistem prompt'u
            mesajlar: Konusma mesajlari
            timeout: Zaman asimi (saniye)

        Returns:
            Yanit metni
        """
        if not self._hazir:
            return "[Codex]: Codex CLI bulunamadi."

        # Prompt'u birlestir
        prompt = sistem_prompt + "\n\n"
        for m in mesajlar:
            rol = m.get("role", "user")
            icerik = m.get("content", "")
            prompt += f"{rol}: {icerik}\n"

        try:
            r = subprocess.run(
                [str(self.codex_yolu), "--prompt", prompt],
                capture_output=True, text=True, timeout=timeout,
                cwd=str(Path.cwd()),
            )
            if r.returncode == 0:
                return r.stdout.strip()
            return f"[Codex]: Hata kodu {r.returncode}: {r.stderr[:200]}"
        except subprocess.TimeoutExpired:
            return "[Codex]: Zaman asimi."
        except Exception as e:
            return f"[Codex]: {e}"

    def modelleri_listele(self) -> list[str]:
        """Codex'in kullanabilecegi modelleri listele."""
        if not self._hazir:
            return []
        try:
            r = subprocess.run(
                [str(self.codex_yolu), "--list-models"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                return [m.strip() for m in r.stdout.strip().split("\n") if m.strip()]
        except Exception as _e:
            logger.warning("[CodexRuntime] except Exception (L118): %s", Exception)
            pass
        return []


if __name__ == "__main__":
    rt = CodexRuntime()
    print(f"Codex CLI: {'HAZIR' if rt.hazir_mi else 'BULUNAMADI'}")
    if rt.hazir_mi:
        print(f"  Yol: {rt.codex_yolu}")
        print(f"  Ping: {rt.ping()}")
        print(f"  Modeller: {rt.modelleri_listele()}")
