#!/usr/bin/env python3
"""
ReYMeN Signal Gateway Connector — reymen/ag/gateway_signal.py

signal-cli (REST API veya direkt CLI) ile Signal üzerinden mesaj gönderir.

İki mod:
  1. REST API (varsayılan): signal-cli dbus/rest modunda çalışırken
     http://localhost:8080/v1/send endpoint'ine POST
  2. CLI: subprocess ile signal-cli binary'ini direkt çağırır

Config:
    platforms:
      signal:
        enabled: false
        number: "${SIGNAL_NUMBER}"
        mode: rest           # rest veya cli
        api_url: "http://localhost:8080"
        cli_path: "${SIGNAL_CLI_PATH}"

Env:
    SIGNAL_NUMBER    — Signal kayıtlı telefon numarası (+905551234567)
    SIGNAL_CLI_PATH  — signal-cli binary yol (opsiyonel, varsayılan: signal-cli)
    SIGNAL_API_URL   — REST API base URL (opsiyonel, varsayılan: http://localhost:8080)
"""

import os
import re
import json
import asyncio
import logging
import subprocess
from typing import Optional
from urllib.parse import urljoin

import aiohttp

from reymen.ag.gateway_manager import BasePlatformGateway

logger = logging.getLogger(__name__)


class SignalGateway(BasePlatformGateway):
    """Signal platformu için gateway — signal-cli REST API veya CLI modu."""

    def __init__(self, config: dict):
        super().__init__(config)

        # Numara (zorunlu)
        raw_number = config.get("number", "") or ""
        self.number = self._resolve_env_var(raw_number)

        # Mod: rest (varsayılan) veya cli
        self.mode = (config.get("mode") or "rest").strip().lower()

        # REST API ayarları
        raw_api_url = config.get("api_url", "") or ""
        self.api_url = self._resolve_env_var(raw_api_url)
        if not self.api_url and self.mode == "rest":
            self.api_url = os.environ.get("SIGNAL_API_URL", "http://localhost:8080")
        self.api_url = self.api_url.rstrip("/")

        # CLI ayarları
        raw_cli_path = config.get("cli_path", "") or ""
        self.cli_path = self._resolve_env_var(raw_cli_path)
        if not self.cli_path:
            self.cli_path = os.environ.get("SIGNAL_CLI_PATH", "signal-cli")

    # ── env var çözümleme ──────────────────────────────────────────────

    @staticmethod
    def _resolve_env_var(value: str) -> str:
        """${ENV_VAR} veya $ENV_VAR desenlerini ortam değişkeninden çözümle."""
        if not value:
            return ""
        match = re.match(r"^\$\{(\w+)\}$", value.strip())
        if match:
            return os.environ.get(match.group(1), "")
        match = re.match(r"^\$(\w+)$", value.strip())
        if match:
            return os.environ.get(match.group(1), "")
        return value

    # ── REST API ile mesaj gönderme ────────────────────────────────────

    async def _send_rest(self, channel: str, message: str) -> dict:
        """
        signal-cli REST API'ye POST isteği gönder.

        Endpoint: POST {api_url}/v1/send
        Body:
            {
                "message": "...",
                "number": "...",
                "recipients": ["..."]
            }

        Args:
            channel: Alıcı grup ID'si veya telefon numarası
            message: Gönderilecek mesaj metni

        Returns:
            dict: {"ok": True} veya {"error": "..."}
        """
        if not self.number:
            return {"error": "SIGNAL_NUMBER tanımlı değil"}
        if not channel:
            return {"error": "Signal: alıcı (channel) belirtilmedi"}

        url = urljoin(self.api_url + "/", "/v1/send")
        payload = {
            "message": message,
            "number": self.number,
            "recipients": [channel],
        }
        headers = {"Content-Type": "application/json"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    data=json.dumps(payload),
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    body = await resp.text()
                    if resp.status == 201 or resp.status == 200:
                        logger.info(
                            "✅ Signal REST mesaj gönderildi -> %s (status=%d)",
                            channel, resp.status,
                        )
                        return {"ok": True, "status": resp.status}
                    else:
                        logger.error(
                            "❌ Signal REST hata: HTTP %d - %s",
                            resp.status, body,
                        )
                        return {"error": f"HTTP {resp.status}: {body}"}
        except asyncio.TimeoutError:
            logger.error("❌ Signal REST timeout: %s", self.api_url)
            return {"error": "Signal REST API timeout"}
        except aiohttp.ClientError as e:
            logger.error("❌ Signal REST bağlantı hatası: %s", e)
            return {"error": str(e)}
        except Exception as e:
            logger.exception("❌ Signal REST beklenmeyen hata")
            return {"error": str(e)}

    # ── CLI ile mesaj gönderme ──────────────────────────────────────────

    async def _send_cli(self, channel: str, message: str) -> dict:
        """
        signal-cli binary ile direkt CLI çağrısı.

        Komut:
            signal-cli -u NUMBER send -g GROUP_ID -m "MESAJ"

        Args:
            channel: Grup ID'si (signal-cli -g parametresi)
            message: Gönderilecek mesaj metni

        Returns:
            dict: {"ok": True} veya {"error": "..."}
        """
        if not self.number:
            return {"error": "SIGNAL_NUMBER tanımlı değil"}
        if not channel:
            return {"error": "Signal: alıcı (channel/grup ID) belirtilmedi"}

        cmd = [
            self.cli_path,
            "-u", self.number,
            "send",
            "-g", channel,
            "-m", message,
        ]

        loop = asyncio.get_running_loop()

        def _run():
            """subprocess.run — blocking, run in executor."""
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return result
            except subprocess.TimeoutExpired:
                logger.error("❌ Signal CLI timeout (30s): %s", cmd)
                return subprocess.CompletedProcess(
                    cmd, -1, "", "CLI timeout"
                )

        try:
            result = await loop.run_in_executor(None, _run)
            if result.returncode == 0:
                logger.info(
                    "✅ Signal CLI mesaj gönderildi -> %s (group)",
                    channel,
                )
                return {"ok": True, "returncode": 0}
            else:
                stderr = (result.stderr or "").strip()
                logger.error(
                    "❌ Signal CLI hata (exit=%d): %s",
                    result.returncode, stderr,
                )
                return {
                    "error": f"CLI exit={result.returncode}: {stderr}",
                    "returncode": result.returncode,
                }
        except Exception as e:
            logger.exception("❌ Signal CLI beklenmeyen hata")
            return {"error": str(e)}

    # ── BasePlatformGateway arayüzü ────────────────────────────────────

    async def send_message(self, channel: str, message: str) -> dict:
        """
        Signal üzerinden mesaj gönder.

        Mode 'rest' (varsayılan): signal-cli REST API endpoint'ine POST.
        Mode 'cli':              signal-cli binary ile subprocess.

        Args:
            channel: Alıcı — grup ID veya telefon numarası
            message: Gönderilecek mesaj metni

        Returns:
            dict: {"ok": True, ...} veya {"error": "..."}
        """
        if self.mode == "cli":
            return await self._send_cli(channel, message)
        return await self._send_rest(channel, message)

    async def health_check(self) -> bool:
        """
        Bağlantı kontrolü — moda göre:

        REST modu:
          - API URL boş değil mi?
          - Geçerli URL formatı var mı?
          - HEAD / GET ile endpoint canlı mı?

        CLI modu:
          - signal-cli binary mevcut ve çalıştırılabilir mi?
          - --version ile yanıt alınabiliyor mu?

        Returns:
            True: sağlıklı
            False: sorun var
        """
        if self.mode == "cli":
            return await self._health_check_cli()
        return await self._health_check_rest()

    async def _health_check_rest(self) -> bool:
        """REST API sağlık kontrolü."""
        if not self.api_url:
            logger.warning("⚠️ Signal health_check: api_url boş")
            return False

        # URL formatı
        from urllib.parse import urlparse
        parsed = urlparse(self.api_url)
        if not parsed.scheme or not parsed.netloc:
            logger.warning("⚠️ Signal health_check: geçersiz API URL formatı")
            return False

        # HTTP bağlantı testi
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.api_url,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    logger.info(
                        "✅ Signal REST sunucu yanıt veriyor (HTTP %d)",
                        resp.status,
                    )
                    return True
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            logger.warning(
                "⚠️ Signal health_check: REST sunucuya erişilemiyor - %s", e
            )
            return False
        except Exception as e:
            logger.warning(
                "⚠️ Signal health_check: beklenmeyen hata - %s", e
            )
            return False

    async def _health_check_cli(self) -> bool:
        """CLI binary sağlık kontrolü."""
        cmd = [self.cli_path, "--version"]

        loop = asyncio.get_running_loop()

        def _run():
            try:
                return subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            except FileNotFoundError:
                logger.error(
                    "❌ Signal CLI bulunamadı: %s", self.cli_path
                )
                return subprocess.CompletedProcess(cmd, -2, "", "FileNotFoundError")
            except subprocess.TimeoutExpired:
                logger.error("❌ Signal CLI --version timeout")
                return subprocess.CompletedProcess(cmd, -1, "", "timeout")

        try:
            result = await loop.run_in_executor(None, _run)
            if result.returncode == 0:
                version = (result.stdout or "").strip()
                logger.info(
                    "✅ Signal CLI mevcut (version: %s)",
                    version or "(bilinmiyor)",
                )
                return True
            else:
                stderr = (result.stderr or "").strip()
                logger.warning(
                    "⚠️ Signal CLI --version başarısız (exit=%d): %s",
                    result.returncode, stderr,
                )
                return False
        except Exception as e:
            logger.warning(
                "⚠️ Signal health_check: CLI hatası - %s", e
            )
            return False

    @staticmethod
    def required_env_vars() -> list[str]:
        """Gerekli çevre değişkenleri."""
        return ["SIGNAL_NUMBER", "SIGNAL_CLI_PATH"]

    def __repr__(self) -> str:
        return (
            f"SignalGateway(enabled={self.enabled}, "
            f"mode={self.mode}, "
            f"number={self.number})"
        )


# ── Doğrudan test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def test():
        # Önce REST modu test
        gw_rest = SignalGateway({
            "enabled": True,
            "number": "${SIGNAL_NUMBER}",
            "mode": "rest",
            "api_url": "http://localhost:8080",
            "cli_path": "${SIGNAL_CLI_PATH}",
        })

        print("═══════ Signal Gateway Test (REST mod) ═══════")
        print(f"Name:        {gw_rest.name}")
        print(f"Enabled:     {gw_rest.enabled}")
        print(f"Mode:        {gw_rest.mode}")
        print(f"Number:      {gw_rest.number or '(boş)'}")
        print(f"API URL:     {gw_rest.api_url or '(boş)'}")
        print(f"CLI Path:    {gw_rest.cli_path or '(boş)'}")
        print(f"Env vars:    {SignalGateway.required_env_vars()}")
        print()

        health_rest = await gw_rest.health_check()
        print(f"Health Check (REST): {'✅' if health_rest else '❌'}")

        # CLI modu test
        gw_cli = SignalGateway({
            "enabled": True,
            "number": "${SIGNAL_NUMBER}",
            "mode": "cli",
            "api_url": "http://localhost:8080",
            "cli_path": "${SIGNAL_CLI_PATH}",
        })

        print()
        print("═══════ Signal Gateway Test (CLI mod) ═══════")
        print(f"Name:        {gw_cli.name}")
        print(f"Enabled:     {gw_cli.enabled}")
        print(f"Mode:        {gw_cli.mode}")
        print(f"Number:      {gw_cli.number or '(boş)'}")
        print(f"API URL:     {gw_cli.api_url or '(boş)'}")
        print(f"CLI Path:    {gw_cli.cli_path or '(boş)'}")
        print()

        health_cli = await gw_cli.health_check()
        print(f"Health Check (CLI): {'✅' if health_cli else '❌'}")

        # Repr test
        print()
        print("repr(REST):", repr(gw_rest))
        print("repr(CLI): ", repr(gw_cli))

    asyncio.run(test())
