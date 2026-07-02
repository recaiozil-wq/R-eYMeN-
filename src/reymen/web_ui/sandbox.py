"""🏖️ ReYMeN Sandbox — izole kod çalıştırma ortamı.

Her sandbox kendi temp dizininde çalışır, timeout'lu ve kontrollüdür.
Bağımlılık: yok (tempfile + subprocess + threading ile)
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SANDBOX_ANA_DIZIN = Path(tempfile.gettempdir()) / "reymen_sandbox"
AZAMI_SURE = 60  # saniye
AZAMI_CIKTI = 100_000  # byte


class Sandbox:
    """Tek bir sandbox oturumu."""

    def __init__(self, sandbox_id: str, dizin: Path) -> None:
        self.id = sandbox_id
        self.dizin = dizin
        self.baslama = time.time()
        self.bitis: Optional[float] = None
        self.durum = "hazir"  # hazir | calisiyor | basarili | hata | zamanasimi | iptal
        self.cikti: str = ""
        self.hata: str = ""
        self.exit_code: Optional[int] = None
        self._proc: Optional[subprocess.Popen] = None

    def calistir(self, komut: list[str], timeout: int = AZAMI_SURE, env: Optional[dict] = None) -> dict:
        """Sandbox'da komut çalıştır."""
        self.durum = "calisiyor"
        self.baslama = time.time()

        sandbox_env = os.environ.copy()
        if env:
            sandbox_env.update(env)
        sandbox_env["SANDBOX_ID"] = self.id
        sandbox_env["SANDBOX_DIR"] = str(self.dizin)
        sandbox_env["REYMEN_SANDBOX"] = "1"

        try:
            self._proc = subprocess.Popen(
                komut,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.dizin),
                env=sandbox_env,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )

            try:
                stdout, stderr = self._proc.communicate(timeout=timeout)
                self.cikti = stdout[:AZAMI_CIKTI]
                self.hata = stderr[:AZAMI_CIKTI]
                self.exit_code = self._proc.returncode
                self.durum = "basarili" if self.exit_code == 0 else "hata"
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()
                self.cikti = "(zaman aşımı)"
                self.hata = f"Komut {timeout}s içinde bitmedi"
                self.exit_code = -1
                self.durum = "zamanasimi"

        except Exception as e:
            self.hata = str(e)
            self.durum = "hata"
            self.exit_code = -1

        self.bitis = time.time()
        return self.rapor()

    def rapor(self) -> dict:
        """Sandbox oturum raporu."""
        sure = round((self.bitis or time.time()) - self.baslama, 2)
        return {
            "id": self.id,
            "durum": self.durum,
            "dizin": str(self.dizin),
            "exit_code": self.exit_code,
            "sure_sn": sure,
            "cikti_boyut": len(self.cikti) + len(self.hata),
            "cikti": self.cikti[-2000:] if len(self.cikti) > 2000 else self.cikti,
            "hata": self.hata[-500:] if len(self.hata) > 500 else self.hata,
            "baslama": datetime.fromtimestamp(self.baslama).isoformat(),
        }

    def dosya_yaz(self, ad: str, icerik: str) -> Path:
        """Sandbox dizinine dosya yaz."""
        yol = self.dizin / ad
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(icerik, encoding="utf-8")
        return yol

    def dosya_oku(self, ad: str) -> str:
        """Sandbox dizininden dosya oku."""
        yol = self.dizin / ad
        if yol.exists():
            return yol.read_text(encoding="utf-8", errors="replace")
        return ""

    def temizle(self) -> None:
        """Sandbox dizinini sil."""
        if self.dizin.exists():
            shutil.rmtree(self.dizin, ignore_errors=True)
            logger.info("Sandbox %s temizlendi: %s", self.id, self.dizin)


class SandboxYoneticisi:
    """Tüm sandbox'ları yönetir."""

    def __init__(self) -> None:
        self._sandboxlar: dict[str, Sandbox] = {}
        self._kilit = threading.Lock()

    def yeni(self) -> Sandbox:
        """Yeni sandbox oluştur."""
        sandbox_id = str(uuid.uuid4())[:8]
        dizin = SANDBOX_ANA_DIZIN / sandbox_id
        dizin.mkdir(parents=True, exist_ok=True)

        sb = Sandbox(sandbox_id, dizin)
        with self._kilit:
            self._sandboxlar[sandbox_id] = sb

        logger.info("Sandbox olusturuldu: %s -> %s", sandbox_id, dizin)
        return sb

    def get(self, sandbox_id: str) -> Optional[Sandbox]:
        with self._kilit:
            return self._sandboxlar.get(sandbox_id)

    def listele(self, limit: int = 20) -> list[dict]:
        with self._kilit:
            sb_list = list(self._sandboxlar.values())[-limit:]
            return [sb.rapor() for sb in sb_list]

    def temizle_hepsi(self) -> int:
        """Tüm sandbox'ları temizle."""
        say = 0
        with self._kilit:
            for sb in self._sandboxlar.values():
                sb.temizle()
                say += 1
            self._sandboxlar.clear()
        return say

    def temizle_eski(self, max_saat: int = 1) -> int:
        """Belirli saatten eski sandbox'ları temizle."""
        simdi = time.time()
        sure = max_saat * 3600
        silinen = 0
        with self._kilit:
            for sid, sb in list(self._sandboxlar.items()):
                if simdi - sb.baslama > sure:
                    sb.temizle()
                    del self._sandboxlar[sid]
                    silinen += 1
        return silinen


# Singleton
yonetici = SandboxYoneticisi()
