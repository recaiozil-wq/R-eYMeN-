"""🔑 OAuth 2.0 Sistemi — Google + Discord Login.

Provider pattern:
    OAuth2Provider (ABC) → GoogleOAuth2Provider, DiscordOAuth2Provider
    OAuth2Registry (singleton) → register / get providers
    OAuth2Manager → flow: get_auth_url → exchange_code → get_user_info → refresh_token

Token storage:
    .ReYMeN/oauth/tokens.json  (JSON file)

All HTTP via urllib.request (no extra packages).
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

PROJE_KOK = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Veri yapıları
# ---------------------------------------------------------------------------

@dataclass
class OAuth2Token:
    """Bir OAuth2 provider'dan alınan token bilgisi."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_token: str = ""
    scope: str = ""
    provider: str = ""
    user_id: str = ""
    obtained_at: float = field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        return time.time() > self.obtained_at + self.expires_in - 60  # 60s grace


@dataclass
class OAuth2UserInfo:
    """Provider'dan dönen kullanıcı bilgisi (normalleştirilmiş)."""
    provider_id: str          # provider içindeki unique ID
    email: str = ""
    display_name: str = ""
    avatar_url: str = ""
    raw: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# OAuth2Provider ABC
# ---------------------------------------------------------------------------

class OAuth2Provider(ABC):
    """OAuth2 sağlayıcı temel sınıfı.

    Alt sınıflar şu alanları tanımlamalı:
      - provider_id: str  (örn: "google", "discord")
      - client_id, client_secret (genelde env var'dan okunur)
      - auth_url, token_url, userinfo_url
      - scopes: list[str]
    """

    provider_id: str = ""
    client_id: str = ""
    client_secret: str = ""
    auth_url: str = ""
    token_url: str = ""
    userinfo_url: str = ""
    scopes: list[str] = ["openid", "email", "profile"]
    redirect_uri: str = ""

    def get_auth_url(self, state: str = "", redirect_uri: str = "") -> str:
        """Kullanıcıyı OAuth2 onay sayfasına yönlendirecek URL."""
        if not redirect_uri:
            redirect_uri = self.redirect_uri
        if not state:
            state = secrets.token_urlsafe(16)
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{self.auth_url}?{urllib.parse.urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str = "") -> dict[str, Any]:
        """Authorization code ile token al."""
        if not redirect_uri:
            redirect_uri = self.redirect_uri
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        return self._http_post(self.token_url, data)

    def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh token ile yeni access token al."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        return self._http_post(self.token_url, data)

    def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Access token ile kullanıcı bilgisi al."""
        req = urllib.request.Request(
            self.userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            logger.error("[OAuth2] get_user_info HTTP %d: %s", e.code, body[:500])
            raise OAuth2ProviderError(
                f"Kullanıcı bilgisi alınamadı: HTTP {e.code}",
                provider=self.provider_id,
                status_code=e.code,
            ) from e
        except (urllib.error.URLError, OSError) as e:
            logger.error("[OAuth2] get_user_info bağlantı hatası: %s", e)
            raise OAuth2ProviderError(
                f"Kullanıcı bilgisi alınamadı: {e}",
                provider=self.provider_id,
            ) from e

    @abstractmethod
    def normalize_user_info(self, raw: dict[str, Any]) -> OAuth2UserInfo:
        """Provider'a özel raw yanıtı OAuth2UserInfo'ya dönüştür."""
        ...

    def _http_post(self, url: str, data: dict[str, Any]) -> dict[str, Any]:
        """application/x-www-form-urlencoded POST isteği."""
        encoded = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(url, data=encoded, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        req.add_header("Accept", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            logger.error("[OAuth2] POST %s HTTP %d: %s", url, e.code, body[:500])
            raise OAuth2ProviderError(
                f"Token alınamadı: HTTP {e.code}",
                provider=self.provider_id,
                status_code=e.code,
            ) from e
        except (urllib.error.URLError, OSError) as e:
            logger.error("[OAuth2] POST %s bağlantı hatası: %s", url, e)
            raise OAuth2ProviderError(
                f"Token alınamadı: {e}",
                provider=self.provider_id,
            ) from e


# ---------------------------------------------------------------------------
# Hata sınıfı
# ---------------------------------------------------------------------------

class OAuth2ProviderError(Exception):
    """OAuth2 işlemleri sırasında oluşan hata."""
    def __init__(self, message: str, provider: str = "",
                 status_code: int = 0):
        self.provider = provider
        self.status_code = status_code
        super().__init__(message)


# ---------------------------------------------------------------------------
# GoogleOAuth2Provider
# ---------------------------------------------------------------------------

class GoogleOAuth2Provider(OAuth2Provider):
    """Google OAuth2 sağlayıcısı.

    Gereken env vars:
      GOOGLE_CLIENT_ID
      GOOGLE_CLIENT_SECRET
    """

    provider_id = "google"
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"
    userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    scopes: list[str] = ["openid", "email", "profile"]

    def __init__(self, redirect_uri: str = ""):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
        if not self.client_id or not self.client_secret:
            logger.warning(
                "[OAuth2:Google] GOOGLE_CLIENT_ID veya GOOGLE_CLIENT_SECRET "
                "ortam değişkeni bulunamadı. Google girişi çalışmayacak."
            )
        self.redirect_uri = redirect_uri or os.getenv(
            "GOOGLE_REDIRECT_URI",
            "http://localhost:5000/auth/callback/google",
        )

    def normalize_user_info(self, raw: dict[str, Any]) -> OAuth2UserInfo:
        """Google userinfo yanıtını normalleştir."""
        return OAuth2UserInfo(
            provider_id=raw.get("id", raw.get("sub", "")),
            email=raw.get("email", ""),
            display_name=raw.get("name", raw.get("given_name", "")),
            avatar_url=raw.get("picture", ""),
            raw=raw,
        )


# ---------------------------------------------------------------------------
# DiscordOAuth2Provider
# ---------------------------------------------------------------------------

class DiscordOAuth2Provider(OAuth2Provider):
    """Discord OAuth2 sağlayıcısı.

    Gereken env vars:
      DISCORD_CLIENT_ID
      DISCORD_CLIENT_SECRET
    """

    provider_id = "discord"
    auth_url = "https://discord.com/api/oauth2/authorize"
    token_url = "https://discord.com/api/oauth2/token"
    userinfo_url = "https://discord.com/api/users/@me"
    scopes: list[str] = ["identify", "email"]

    def __init__(self, redirect_uri: str = ""):
        self.client_id = os.getenv("DISCORD_CLIENT_ID", "")
        self.client_secret = os.getenv("DISCORD_CLIENT_SECRET", "")
        if not self.client_id or not self.client_secret:
            logger.warning(
                "[OAuth2:Discord] DISCORD_CLIENT_ID veya DISCORD_CLIENT_SECRET "
                "ortam değişkeni bulunamadı. Discord girişi çalışmayacak."
            )
        self.redirect_uri = redirect_uri or os.getenv(
            "DISCORD_REDIRECT_URI",
            "http://localhost:5000/auth/callback/discord",
        )

    def normalize_user_info(self, raw: dict[str, Any]) -> OAuth2UserInfo:
        """Discord /users/@me yanıtını normalleştir."""
        avatar_hash = raw.get("avatar", "")
        user_id = raw.get("id", "")
        avatar_url = ""
        if avatar_hash and user_id:
            ext = "gif" if avatar_hash.startswith("a_") else "png"
            avatar_url = (
                f"https://cdn.discordapp.com/avatars/"
                f"{user_id}/{avatar_hash}.{ext}"
            )
        return OAuth2UserInfo(
            provider_id=user_id,
            email=raw.get("email", ""),
            display_name=raw.get("global_name")
                        or raw.get("username", ""),
            avatar_url=avatar_url,
            raw=raw,
        )


# ---------------------------------------------------------------------------
# OAuth2Registry (singleton)
# ---------------------------------------------------------------------------

class OAuth2Registry:
    """OAuth2 provider registry — singleton pattern."""

    _instance: Optional[OAuth2Registry] = None
    _providers: dict[str, OAuth2Provider]

    def __new__(cls) -> OAuth2Registry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._providers = {}
        return cls._instance

    def register(self, provider: OAuth2Provider) -> None:
        if not provider.provider_id:
            raise ValueError("OAuth2Provider.provider_id boş olamaz")
        self._providers[provider.provider_id] = provider
        logger.info(
            "[OAuth2Registry] Kaydedildi: %s", provider.provider_id
        )

    def get(self, provider_id: str) -> Optional[OAuth2Provider]:
        return self._providers.get(provider_id)

    def list(self) -> list[OAuth2Provider]:
        return list(self._providers.values())

    def list_ids(self) -> list[str]:
        return list(self._providers.keys())

    def clear(self) -> None:
        self._providers.clear()


# ---------------------------------------------------------------------------
# Token Storage — JSON file
# ---------------------------------------------------------------------------

class OAuth2TokenStorage:
    """OAuth2 token'larını .ReYMeN/oauth/tokens.json'da saklar."""

    def __init__(self, base_path: Path | None = None):
        self._base = base_path or PROJE_KOK
        self._dosya = self._base / ".ReYMeN" / "oauth" / "tokens.json"

    def _load(self) -> dict[str, Any]:
        if self._dosya.exists():
            try:
                return json.loads(self._dosya.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("[OAuth2TokenStorage] Yükleme hatası: %s", e)
                return {}
        return {}

    def _save(self, data: dict[str, Any]) -> None:
        self._dosya.parent.mkdir(parents=True, exist_ok=True)
        self._dosya.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get_token(self, provider_id: str, user_id: str = "default") -> Optional[OAuth2Token]:
        data = self._load()
        token_data = data.get(provider_id, {}).get(user_id)
        if token_data:
            return OAuth2Token(**token_data)
        return None

    def save_token(self, provider_id: str, token: OAuth2Token,
                   user_id: str = "default") -> None:
        data = self._load()
        if provider_id not in data:
            data[provider_id] = {}
        data[provider_id][user_id] = asdict(token)
        self._save(data)

    def delete_token(self, provider_id: str, user_id: str = "default") -> None:
        data = self._load()
        if provider_id in data and user_id in data[provider_id]:
            del data[provider_id][user_id]
            if not data[provider_id]:
                del data[provider_id]
            self._save(data)

    def list_tokens(self) -> list[dict[str, str]]:
        """Tüm kayıtlı token'ları listele (provider, user_id bazında)."""
        data = self._load()
        result = []
        for provider_id, users in data.items():
            for user_id in users:
                result.append({
                    "provider": provider_id,
                    "user_id": user_id,
                })
        return result


# ---------------------------------------------------------------------------
# OAuth2Manager — full flow
# ---------------------------------------------------------------------------

class OAuth2Manager:
    """OAuth2 akış yöneticisi.

    Kullanım:
        manager = OAuth2Manager()
        url = manager.get_auth_url("google")
        token = manager.exchange_code("google", "auth_code")
        user = manager.get_user_info("google", token.access_token)
        new_token = manager.refresh_token("google", token.refresh_token)
    """

    def __init__(self,
                 registry: OAuth2Registry | None = None,
                 storage: OAuth2TokenStorage | None = None):
        self.registry = registry or oauth2_registry
        self.storage = storage or token_storage

    def get_auth_url(self, provider_id: str,
                     state: str = "",
                     redirect_uri: str = "") -> str:
        """Kullanıcıyı OAuth2 onay sayfasına yönlendirecek URL."""
        provider = self.registry.get(provider_id)
        if not provider:
            raise OAuth2ProviderError(
                f"Bilinmeyen OAuth2 provider: {provider_id}",
                provider=provider_id,
            )
        return provider.get_auth_url(state=state, redirect_uri=redirect_uri)

    def exchange_code(self, provider_id: str, code: str,
                      redirect_uri: str = "") -> OAuth2Token:
        """Authorization code ile token al ve kaydet."""
        provider = self.registry.get(provider_id)
        if not provider:
            raise OAuth2ProviderError(
                f"Bilinmeyen OAuth2 provider: {provider_id}",
                provider=provider_id,
            )
        raw = provider.exchange_code(code, redirect_uri=redirect_uri)
        token = OAuth2Token(
            access_token=raw.get("access_token", ""),
            token_type=raw.get("token_type", "Bearer"),
            expires_in=raw.get("expires_in", 3600),
            refresh_token=raw.get("refresh_token", ""),
            scope=raw.get("scope", ""),
            provider=provider_id,
        )
        # Kullanıcı bilgisini al ve user_id'yi token'a ekle
        try:
            user_raw = provider.get_user_info(token.access_token)
            user_info = provider.normalize_user_info(user_raw)
            token.user_id = user_info.provider_id
        except Exception as e:
            logger.warning(
                "[OAuth2Manager] Kullanıcı bilgisi alınamadı: %s", e
            )
        # Token'ı kaydet
        self.storage.save_token(provider_id, token)
        return token

    def get_user_info(self, provider_id: str,
                      access_token: str) -> OAuth2UserInfo:
        """Access token ile kullanıcı bilgisi al."""
        provider = self.registry.get(provider_id)
        if not provider:
            raise OAuth2ProviderError(
                f"Bilinmeyen OAuth2 provider: {provider_id}",
                provider=provider_id,
            )
        raw = provider.get_user_info(access_token)
        return provider.normalize_user_info(raw)

    def refresh_token(self, provider_id: str,
                      refresh_token: str) -> OAuth2Token:
        """Refresh token ile yeni access token al ve kaydet."""
        provider = self.registry.get(provider_id)
        if not provider:
            raise OAuth2ProviderError(
                f"Bilinmeyen OAuth2 provider: {provider_id}",
                provider=provider_id,
            )
        raw = provider.refresh_access_token(refresh_token)
        token = OAuth2Token(
            access_token=raw.get("access_token", ""),
            token_type=raw.get("token_type", "Bearer"),
            expires_in=raw.get("expires_in", 3600),
            refresh_token=raw.get("refresh_token", refresh_token),
            scope=raw.get("scope", ""),
            provider=provider_id,
        )
        # Mevcut user_id'yi koru
        old = self.storage.get_token(provider_id)
        if old:
            token.user_id = old.user_id
        self.storage.save_token(provider_id, token)
        return token


# ---------------------------------------------------------------------------
# Singleton'lar
# ---------------------------------------------------------------------------

oauth2_registry = OAuth2Registry()
token_storage = OAuth2TokenStorage()
oauth2_manager = OAuth2Manager(oauth2_registry, token_storage)


def init_oauth2_providers(redirect_base: str = "") -> None:
    """Varsayılan OAuth2 provider'larını kaydet.

    Args:
        redirect_base: Callback URL base (örn: "http://localhost:5000")
                       Boşsa env var'daki redirect_uri'ler kullanılır.
    """
    google_redirect = ""
    discord_redirect = ""
    if redirect_base:
        google_redirect = f"{redirect_base.rstrip('/')}/auth/callback/google"
        discord_redirect = f"{redirect_base.rstrip('/')}/auth/callback/discord"

    google = GoogleOAuth2Provider(redirect_uri=google_redirect)
    discord = DiscordOAuth2Provider(redirect_uri=discord_redirect)

    oauth2_registry.register(google)
    oauth2_registry.register(discord)

    logger.info(
        "[OAuth2] Provider'lar kaydedildi: google=%s, discord=%s",
        bool(google.client_id),
        bool(discord.client_id),
    )
