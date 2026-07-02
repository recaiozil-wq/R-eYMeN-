#!/usr/bin/env python3
"""
Matrix Gateway Connector — reymen/ag/gateway_matrix.py

Matrix odalarına mesaj göndermek için matrix-nio kütüphanesi ile
BasePlatformGateway implementasyonu.

Gerekli .env değişkenleri:
    MATRIX_HOMESERVER (örn: https://matrix.example.com)
    MATRIX_USER       (örn: @user:example.com)
    MATRIX_PASSWORD   (Matrix hesap şifresi)
    MATRIX_ACCESS_TOKEN (opsiyonel — varsa password yerine token kullanılır)
"""

import os
import logging
from typing import Optional

from nio import AsyncClient, RoomSendError, LoginError

from reymen.ag.gateway_manager import BasePlatformGateway

logger = logging.getLogger(__name__)


class MatrixGateway(BasePlatformGateway):
    """
    Matrix platformu için gateway.

    Config şeması:
        enabled: bool
        homeserver: str   (örn: "https://matrix.example.com")
        user: str         (örn: "@user:example.com")
        password: str     (Matrix hesap şifresi)
        access_token: str (opsiyonel — token varsa password atlanır)
        room: str         (varsayılan oda ID'si, örn: "!roomid:matrix.org")
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.homeserver = config.get("homeserver", "").rstrip("/")
        self.user = config.get("user", "")
        self.password = config.get("password", "")
        self.access_token = config.get(
            "access_token", os.environ.get("MATRIX_ACCESS_TOKEN", "")
        )
        self.default_room = config.get("room", "")
        self._client: Optional[AsyncClient] = None

    @staticmethod
    def required_env_vars() -> list[str]:
        return ["MATRIX_HOMESERVER", "MATRIX_USER", "MATRIX_PASSWORD"]

    # ------------------------------------------------------------------
    # AsyncClient lifecycle
    # ------------------------------------------------------------------

    async def _get_client(self) -> AsyncClient:
        """Bağlı bir AsyncClient döndürür — gerekirse login yapar."""
        if self._client is not None and self._client.logged_in:
            return self._client

        client = AsyncClient(self.homeserver, self.user)

        if self.access_token:
            # Token ile giriş (password gerekmez)
            client.access_token = self.access_token
            client.user_id = self.user
            logger.info("Matrix: access_token ile giriş yapıldı")
        else:
            # Klasik parola ile giriş
            try:
                resp = await client.login(self.password)
                if isinstance(resp, LoginError):
                    raise ConnectionError(
                        f"Matrix login hatası: {resp.message}"
                    )
                logger.info("Matrix: parola ile başarılı giriş")
            except Exception:
                await client.close()
                raise

        self._client = client
        return client

    async def _close_client(self):
        """Mevcut client'ı kapatır."""
        if self._client is not None:
            try:
                await self._client.close()
            except Exception:
                pass
            finally:
                self._client = None

    # ------------------------------------------------------------------
    # BasePlatformGateway interface
    # ------------------------------------------------------------------

    async def send_message(self, channel: str, message: str) -> dict:
        """
        Belirtilen Matrix odasına m.text mesajı gönderir.

        Args:
            channel: Oda ID'si (örn: "!abc123:matrix.org").
                     Boşsa config'deki default_room kullanılır.
            message: Gönderilecek mesaj metni.

        Returns:
            Başarılı:  {"ok": True, "event_id": "<event_id>"}
            Başarısız: {"error": "<hata mesajı>"}
        """
        room_id = channel or self.default_room
        if not room_id:
            return {"error": "Matrix: Oda ID'si belirtilmedi (channel veya config.room)"}

        try:
            client = await self._get_client()
            resp = await client.room_send(
                room_id=room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": message,
                },
            )
            if isinstance(resp, RoomSendError):
                return {"error": f"Matrix room_send hatası: {resp.message}"}

            logger.info("Matrix mesajı gönderildi → %s", room_id)
            return {"ok": True, "event_id": resp.event_id}

        except Exception as e:
            logger.exception("Matrix send_message başarısız: %s", e)
            return {"error": str(e)}

    async def health_check(self) -> bool:
        """
        Matrix sunucusuna bağlanmayı dener.

        Returns:
            True  — bağlantı başarılı
            False — bağlantı başarısız
        """
        try:
            client = await self._get_client()
            # Basit bir whoami çağrısı ile bağlantıyı doğrula
            resp = await client.whoami()
            if hasattr(resp, "user_id") and resp.user_id:
                logger.info("Matrix health_check ✅ — kullanıcı: %s", resp.user_id)
                return True
            logger.warning("Matrix health_check ❌ — whoami yanıtı beklenmedik")
            return False
        except Exception as e:
            logger.warning("Matrix health_check ❌ — %s", e)
            return False
        finally:
            # health_check sonrası client'ı kapat — her seferinde taze bağlantı
            await self._close_client()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def close(self):
        """Kaynakları temizle."""
        await self._close_client()

    def __repr__(self) -> str:
        return (
            f"MatrixGateway(enabled={self.enabled}, "
            f"homeserver={self.homeserver}, "
            f"user={self.user})"
        )
