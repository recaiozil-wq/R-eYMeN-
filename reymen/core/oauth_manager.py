# -*- coding: utf-8 -*-
"""
oauth_manager.py — P2 OAuth 2.0: Google/GitHub/Discord entegrasyonu.

Mevcut OAuth sistemleri (reymen/guvenlik/oauth2.py, oauth_sistemi.py, oauth_servis.py)
üzerine kurulmuştur. ABC provider pattern ile Google, GitHub, Discord destegi.

Token yönetimi: refresh, expire kontrol, file cache.

Motor Tools:
    OAUTH_GIRIS(provider)  → Auth URL döndür
    OAUTH_DURUM(provider)  → Token durumunu göster
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PROJE_KOK = Path(__file__).resolve().parent.parent.parent

# ── Mevcut OAuth modüllerini dene ──────────────────────────────────────────────
try:
    from reymen.guvenlik.oauth2 import (  # type: ignore[import-untyped]
        OAuth2Manager as _OAuth2Manager,
        OAuth2Token as _OAuth2Token,
        OAuth2UserInfo as _OAuth2UserInfo,
        OAuth2Provider as _OAuth2Provider,
        OAuth2Registry as _OAuth2Registry,
        OAuth2TokenStorage as _OAuth2TokenStorage,
        GoogleOAuth2Provider as _GoogleOAuth2Provider,
        DiscordOAuth2Provider as _DiscordOAuth2Provider,
        OAuth2ProviderError,
        oauth2_manager as _varsayilan_oauth2,
        oauth2_registry as _oauth2_registry,
        token_storage as _oauth2_token_storage,
    )
    _OAUTH2_MEVCUT = True
except ImportError:
    _OAUTH2_MEVCUT = False
    _OAuth2Manager = None  # type: ignore
    _OAuth2Token = None  # type: ignore
    _OAuth2UserInfo = None  # type: ignore
    _oauth2_registry = None  # type: ignore
    _oauth2_token_storage = None  # type: ignore
    _varsayilan_oauth2 = None  # type: ignore

try:
    from reymen.guvenlik.oauth_sistemi import (  # type: ignore[import-untyped]
        OAuthSistemi as _OAuthSistemi,
        OAuthToken as _OAuthSistemiToken,
        OAuthError as _OAuthSistemiError,
        oauth_sistemi as _varsayilan_oauth_sistemi,
    )
    _OAUTH_SISTEMI_MEVCUT = True
except ImportError:
    _OAUTH_SISTEMI_MEVCUT = False
    _OAuthSistemi = None  # type: ignore
    _varsayilan_oauth_sistemi = None  # type: ignore


# ═══════════════════════════════════════════════════════════════════════════════
#  Veri Yapilari
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class OAuthToken:
    """Normallestirilmis OAuth token bilgisi."""
    access_token: str = ""
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_token: str = ""
    scope: str = ""
    provider: str = ""
    user_id: str = ""
    email: str = ""
    display_name: str = ""
    avatar_url: str = ""
    obtained_at: float = field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        return time.time() > self.obtained_at + self.expires_in - 60

    @property
    def expires_at(self) -> str:
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(self.obtained_at + self.expires_in, tz=timezone.utc)
        return dt.isoformat()


class OAuthError(Exception):
    """OAuth islemleri sirasinda olusan hata."""
    def __init__(self, message: str, provider: str = "", status_code: int = 0, code: str = "oauth_error"):
        self.provider = provider
        self.status_code = status_code
        self.code = code
        super().__init__(message)


# ═══════════════════════════════════════════════════════════════════════════════
#  OAuthProvider ABC
# ═══════════════════════════════════════════════════════════════════════════════


class OAuthProvider(ABC):
    """OAuth 2.0 saglayici temel sinifi (Authorization Code Flow).

    Alt siniflar:
        - provider_id: str
        - login_url(): Auth URL dondur
        - callback_handler(code): Authorization code ile token al
        - token_refresh(refresh_token): Token yenile
    """

    provider_id: str = ""

    @abstractmethod
    def login_url(self, state: str = "") -> str:
        """Kullaniciyi OAuth onay sayfasina yonlendirecek URL."""
        ...

    @abstractmethod
    def callback_handler(self, code: str, redirect_uri: str = "") -> OAuthToken:
        """Authorization code ile token al."""
        ...

    @abstractmethod
    def token_refresh(self, refresh_token: str) -> OAuthToken:
        """Refresh token ile yeni access token al."""
        ...

    @abstractmethod
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Access token ile kullanici bilgisi al."""
        ...

    @property
    def hazir(self) -> bool:
        return True


# ═══════════════════════════════════════════════════════════════════════════════
#  GoogleOAuthProvider
# ═══════════════════════════════════════════════════════════════════════════════


class GoogleOAuthProvider(OAuthProvider):
    """Google OAuth 2.0 saglayicisi.

    Gereken env vars: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
    Opsiyonel: GOOGLE_REDIRECT_URI
    """

    provider_id = "google"

    def __init__(self, redirect_uri: str = ""):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
        self.redirect_uri = redirect_uri or os.getenv(
            "GOOGLE_REDIRECT_URI",
            "http://localhost:5000/auth/callback/google",
        )
        self.scopes = ["openid", "email", "profile"]
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"

        if not self.client_id or not self.client_secret:
            logger.warning("[OAuth:Google] GOOGLE_CLIENT_ID/CLIENT_SECRET eksik")

    @property
    def hazir(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def login_url(self, state: str = "") -> str:
        if not state:
            state = secrets.token_urlsafe(16)
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        import urllib.parse
        return f"{self.auth_url}?{urllib.parse.urlencode(params)}"

    def callback_handler(self, code: str, redirect_uri: str = "") -> OAuthToken:
        if not redirect_uri:
            redirect_uri = self.redirect_uri
        raw = self._http_post(self.token_url, {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        })
        token = OAuthToken(
            access_token=raw.get("access_token", ""),
            token_type=raw.get("token_type", "Bearer"),
            expires_in=raw.get("expires_in", 3600),
            refresh_token=raw.get("refresh_token", ""),
            scope=raw.get("scope", " ".join(self.scopes)),
            provider="google",
        )
        # Kullanici bilgisini ekle
        try:
            user_raw = self.get_user_info(token.access_token)
            token.user_id = user_raw.get("id", user_raw.get("sub", ""))
            token.email = user_raw.get("email", "")
            token.display_name = user_raw.get("name", user_raw.get("given_name", ""))
            token.avatar_url = user_raw.get("picture", "")
        except Exception as e:
            logger.warning("[OAuth:Google] Kullanici bilgisi alinamadi: %s", e)
        return token

    def token_refresh(self, refresh_token: str) -> OAuthToken:
        raw = self._http_post(self.token_url, {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        })
        return OAuthToken(
            access_token=raw.get("access_token", ""),
            token_type=raw.get("token_type", "Bearer"),
            expires_in=raw.get("expires_in", 3600),
            refresh_token=raw.get("refresh_token", refresh_token),
            scope=raw.get("scope", ""),
            provider="google",
        )

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        return self._http_get(self.userinfo_url, access_token)

    def _http_post(self, url: str, data: Dict[str, str]) -> Dict[str, Any]:
        import urllib.request
        import urllib.parse
        encoded = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(url, data=encoded, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        req.add_header("Accept", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            raise OAuthError(f"HTTP {e.code}: {body[:200]}", provider="google", status_code=e.code)

    def _http_get(self, url: str, access_token: str) -> Dict[str, Any]:
        import urllib.request
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"}, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            raise OAuthError(f"HTTP {e.code}: {body[:200]}", provider="google", status_code=e.code)


# ═══════════════════════════════════════════════════════════════════════════════
#  GitHubOAuthProvider
# ═══════════════════════════════════════════════════════════════════════════════


class GitHubOAuthProvider(OAuthProvider):
    """GitHub OAuth 2.0 saglayicisi.

    Gereken env vars: GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET
    Not: GitHub'da refresh_token yoktur; token'lar sureklidir.
    """

    provider_id = "github"

    def __init__(self, redirect_uri: str = ""):
        self.client_id = os.getenv("GITHUB_CLIENT_ID", "")
        self.client_secret = os.getenv("GITHUB_CLIENT_SECRET", "")
        self.redirect_uri = redirect_uri or os.getenv(
            "GITHUB_REDIRECT_URI",
            "http://localhost:5000/auth/callback/github",
        )
        self.scopes = ["repo", "user", "workflow"]
        self.auth_url = "https://github.com/login/oauth/authorize"
        self.token_url = "https://github.com/login/oauth/access_token"
        self.userinfo_url = "https://api.github.com/user"

        if not self.client_id or not self.client_secret:
            logger.warning("[OAuth:GitHub] GITHUB_CLIENT_ID/CLIENT_SECRET eksik")

    @property
    def hazir(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def login_url(self, state: str = "") -> str:
        if not state:
            state = secrets.token_urlsafe(16)
        import urllib.parse
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": state,
        }
        return f"{self.auth_url}?{urllib.parse.urlencode(params)}"

    def callback_handler(self, code: str, redirect_uri: str = "") -> OAuthToken:
        import urllib.request
        import urllib.parse
        if not redirect_uri:
            redirect_uri = self.redirect_uri
        # GitHub token endpoint accepts URL-encoded, returns JSON or query string
        data = urllib.parse.urlencode({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }).encode("utf-8")
        req = urllib.request.Request(self.token_url, data=data, method="POST")
        req.add_header("Accept", "application/json")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            raise OAuthError(f"GitHub HTTP {e.code}: {body[:200]}", provider="github")

        token = OAuthToken(
            access_token=raw.get("access_token", ""),
            token_type=raw.get("token_type", "Bearer"),
            # GitHub token'ları süresiz
            expires_in=raw.get("expires_in", 31536000),  # ~1 yil
            scope=raw.get("scope", " ".join(self.scopes)),
            provider="github",
        )
        # Kullanici bilgisini ekle
        try:
            user_raw = self.get_user_info(token.access_token)
            token.user_id = str(user_raw.get("id", ""))
            token.email = user_raw.get("email", "")
            token.display_name = user_raw.get("name", user_raw.get("login", ""))
            token.avatar_url = user_raw.get("avatar_url", "")
        except Exception as e:
            logger.warning("[OAuth:GitHub] Kullanici bilgisi alinamadi: %s", e)
        return token

    def token_refresh(self, refresh_token: str) -> OAuthToken:
        # GitHub'da refresh_token yok
        raise OAuthError("GitHub token'lari süreklidir, refresh gerekmez.", provider="github")

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        import urllib.request
        import json
        req = urllib.request.Request(
            self.userinfo_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            raise OAuthError(f"GitHub userinfo HTTP {e.code}: {body[:200]}", provider="github")


# ═══════════════════════════════════════════════════════════════════════════════
#  DiscordOAuthProvider
# ═══════════════════════════════════════════════════════════════════════════════


class DiscordOAuthProvider(OAuthProvider):
    """Discord OAuth 2.0 saglayicisi.

    Gereken env vars: DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET
    """

    provider_id = "discord"

    def __init__(self, redirect_uri: str = ""):
        self.client_id = os.getenv("DISCORD_CLIENT_ID", "")
        self.client_secret = os.getenv("DISCORD_CLIENT_SECRET", "")
        self.redirect_uri = redirect_uri or os.getenv(
            "DISCORD_REDIRECT_URI",
            "http://localhost:5000/auth/callback/discord",
        )
        self.scopes = ["identify", "email"]
        self.auth_url = "https://discord.com/api/oauth2/authorize"
        self.token_url = "https://discord.com/api/oauth2/token"
        self.userinfo_url = "https://discord.com/api/users/@me"

        if not self.client_id or not self.client_secret:
            logger.warning("[OAuth:Discord] DISCORD_CLIENT_ID/CLIENT_SECRET eksik")

    @property
    def hazir(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def login_url(self, state: str = "") -> str:
        if not state:
            state = secrets.token_urlsafe(16)
        import urllib.parse
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": state,
            "prompt": "consent",
        }
        return f"{self.auth_url}?{urllib.parse.urlencode(params)}"

    def callback_handler(self, code: str, redirect_uri: str = "") -> OAuthToken:
        import urllib.request
        import urllib.parse
        if not redirect_uri:
            redirect_uri = self.redirect_uri

        # Discord Basic Auth gerektirir
        import base64
        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        data = urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }).encode("utf-8")
        req = urllib.request.Request(self.token_url, data=data, method="POST")
        req.add_header("Authorization", f"Basic {auth_header}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        req.add_header("Accept", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            raise OAuthError(f"Discord HTTP {e.code}: {body[:200]}", provider="discord")

        token = OAuthToken(
            access_token=raw.get("access_token", ""),
            token_type=raw.get("token_type", "Bearer"),
            expires_in=raw.get("expires_in", 3600),
            refresh_token=raw.get("refresh_token", ""),
            scope=raw.get("scope", " ".join(self.scopes)),
            provider="discord",
        )
        # Kullanici bilgisini ekle
        try:
            user_raw = self.get_user_info(token.access_token)
            token.user_id = str(user_raw.get("id", ""))
            token.email = user_raw.get("email", "")
            token.display_name = user_raw.get("global_name", "") or user_raw.get("username", "")
            avatar_hash = user_raw.get("avatar", "")
            if avatar_hash and token.user_id:
                ext = "gif" if avatar_hash.startswith("a_") else "png"
                token.avatar_url = f"https://cdn.discordapp.com/avatars/{token.user_id}/{avatar_hash}.{ext}"
        except Exception as e:
            logger.warning("[OAuth:Discord] Kullanici bilgisi alinamadi: %s", e)
        return token

    def token_refresh(self, refresh_token: str) -> OAuthToken:
        import urllib.request
        import urllib.parse
        import base64
        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        data = urllib.parse.urlencode({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }).encode("utf-8")
        req = urllib.request.Request(self.token_url, data=data, method="POST")
        req.add_header("Authorization", f"Basic {auth_header}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        req.add_header("Accept", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            raise OAuthError(f"Discord refresh HTTP {e.code}: {body[:200]}", provider="discord")

        return OAuthToken(
            access_token=raw.get("access_token", ""),
            token_type=raw.get("token_type", "Bearer"),
            expires_in=raw.get("expires_in", 3600),
            refresh_token=raw.get("refresh_token", refresh_token),
            scope=raw.get("scope", ""),
            provider="discord",
        )

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        import urllib.request
        import json
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
            raise OAuthError(f"Discord userinfo HTTP {e.code}: {body[:200]}", provider="discord")


# ═══════════════════════════════════════════════════════════════════════════════
#  Token Depolama (JSON file cache)
# ═══════════════════════════════════════════════════════════════════════════════


class OAuthTokenDeposu:
    """OAuth token'larini JSON dosyasinda saklar.

    Dizin: .ReYMeN/oauth/tokens_cache.json
    """

    def __init__(self, base_path: Optional[Path] = None):
        self._base = base_path or PROJE_KOK
        self._dosya = self._base / ".ReYMeN" / "oauth" / "tokens_cache.json"

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if self._dosya.exists():
            try:
                return json.loads(self._dosya.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("[OAuthTokenDeposu] Yukleme hatasi: %s", e)
                return {}
        return {}

    def _save(self, data: Dict[str, Any]) -> None:
        self._dosya.parent.mkdir(parents=True, exist_ok=True)
        self._dosya.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def kaydet(self, token: OAuthToken) -> None:
        """Token'i kaydet."""
        data = self._load()
        data[token.provider] = asdict(token)
        self._save(data)

    def yukle(self, provider: str) -> Optional[OAuthToken]:
        """Provider'a ait token'i yukle."""
        data = self._load()
        token_data = data.get(provider)
        if token_data:
            return OAuthToken(**token_data)
        return None

    def sil(self, provider: str) -> bool:
        """Provider'a ait token'i sil."""
        data = self._load()
        if provider in data:
            del data[provider]
            self._save(data)
            return True
        return False

    def listele(self) -> List[Dict[str, str]]:
        """Tum kayitli token'lari listele."""
        data = self._load()
        result = []
        for provider, token_data in data.items():
            t = OAuthToken(**token_data)
            result.append({
                "provider": provider,
                "user_id": t.user_id,
                "email": t.email,
                "display_name": t.display_name,
                "durum": "gecerli" if not t.is_expired else "suresi doldu",
                "expires_at": t.expires_at,
            })
        return result

    def var_mi(self, provider: str) -> bool:
        return provider in self._load()


# ═══════════════════════════════════════════════════════════════════════════════
#  OAuthManager Ana Sinif
# ═══════════════════════════════════════════════════════════════════════════════


class OAuthManager:
    """OAuth 2.0 akis yoneticisi.

    Provider'lari yonetir, login/callback/refresh/logout/durum islemlerini
    tek bir API'de birlestirir.

    Kullanim:
        manager = OAuthManager()
        url = manager.login("google")
        token = manager.callback("google", "auth_code")
        durum = manager.durum("google")
        yeni_token = manager.refresh("google")
    """

    def __init__(self, deposu: Optional[OAuthTokenDeposu] = None):
        self._depo = deposu or OAuthTokenDeposu()
        self._providerlar: Dict[str, OAuthProvider] = {}

        # Varsayilan provider'lari kaydet
        self._kaydet_google()
        self._kaydet_github()
        self._kaydet_discord()

        # Mevcut OAuth sistemiyle entegre ol
        self._mevcut_oauth2_entegre()

    def _kaydet_google(self):
        try:
            p = GoogleOAuthProvider()
            self._providerlar["google"] = p
        except Exception as e:
            logger.debug("[OAuthManager] Google provider kayit hatasi: %s", e)

    def _kaydet_github(self):
        try:
            p = GitHubOAuthProvider()
            self._providerlar["github"] = p
        except Exception as e:
            logger.debug("[OAuthManager] GitHub provider kayit hatasi: %s", e)

    def _kaydet_discord(self):
        try:
            p = DiscordOAuthProvider()
            self._providerlar["discord"] = p
        except Exception as e:
            logger.debug("[OAuthManager] Discord provider kayit hatasi: %s", e)

    def _mevcut_oauth2_entegre(self):
        """Mevcut oauth2.py'deki token'lari iceri aktar."""
        if not _OAUTH2_MEVCUT:
            return
        try:
            mevcut_tokenlar = _oauth2_token_storage.list_tokens()
            for t in mevcut_tokenlar:
                prov_id = t.get("provider", "")
                if prov_id and prov_id not in self._providerlar:
                    user_id = t.get("user_id", "default")
                    mevcut_token = _oauth2_token_storage.get_token(prov_id, user_id)
                    if mevcut_token:
                        self._depo.kaydet(OAuthToken(
                            access_token=mevcut_token.access_token,
                            token_type=mevcut_token.token_type,
                            expires_in=mevcut_token.expires_in,
                            refresh_token=mevcut_token.refresh_token,
                            scope=mevcut_token.scope,
                            provider=prov_id,
                            user_id=mevcut_token.user_id,
                        ))
        except Exception as e:
            logger.debug("[OAuthManager] Mevcut OAuth2 entegrasyon hatasi: %s", e)

    # ── Ana API ────────────────────────────────────────────────────────────

    def login(self, provider: str, state: str = "") -> str:
        """Provider'a giris yapmak icin auth URL'si dondur.

        Args:
            provider: "google", "github", "discord"
            state: Opsiyonel state parametresi

        Returns:
            Auth URL (kullanicinin tarayicida acmasi gereken URL)

        Raises:
            OAuthError: Provider bulunamazsa veya hazir degilse
        """
        p = self._providerlar.get(provider)
        if not p:
            raise OAuthError(
                f"Bilinmeyen OAuth provider: '{provider}'. "
                f"Secenekler: {', '.join(self._providerlar.keys())}",
                provider=provider,
            )
        if not p.hazir:
            raise OAuthError(
                f"[{provider.upper()}] OAuth yapilandirmasi eksik. "
                f".env dosyasina {provider.upper()}_CLIENT_ID ve "
                f"{provider.upper()}_CLIENT_SECRET ekleyin.",
                provider=provider, code="oauth_config_eksik",
            )
        return p.login_url(state=state)

    def callback(self, provider: str, code: str, redirect_uri: str = "") -> OAuthToken:
        """Authorization code ile token al ve kaydet.

        Args:
            provider: "google", "github", "discord"
            code: Authorization code
            redirect_uri: Opsiyonel redirect URI

        Returns:
            OAuthToken

        Raises:
            OAuthError: Token alinamazsa
        """
        p = self._providerlar.get(provider)
        if not p:
            raise OAuthError(f"Bilinmeyen OAuth provider: '{provider}'", provider=provider)

        token = p.callback_handler(code, redirect_uri=redirect_uri)
        self._depo.kaydet(token)
        return token

    def refresh(self, provider: str) -> OAuthToken:
        """Refresh token ile yeni access token al.

        Args:
            provider: "google", "github", "discord"

        Returns:
            Yeni OAuthToken

        Raises:
            OAuthError: Token yenilenemezse
        """
        p = self._providerlar.get(provider)
        if not p:
            raise OAuthError(f"Bilinmeyen OAuth provider: '{provider}'", provider=provider)

        mevcut = self._depo.yukle(provider)
        if not mevcut:
            raise OAuthError(
                f"[{provider.upper()}] Kayitli token bulunamadi. Once giris yapin.",
                provider=provider, code="oauth_token_yok",
            )

        if not mevcut.refresh_token:
            if provider == "github":
                raise OAuthError(
                    "[GITHUB] GitHub token'lari sureklidir, refresh gerekmez.",
                    provider=provider, code="github_no_refresh",
                )
            raise OAuthError(
                f"[{provider.upper()}] Refresh token yok. Tekrar giris yapin.",
                provider=provider, code="oauth_no_refresh",
            )

        yeni_token = p.token_refresh(mevcut.refresh_token)
        # Eski kullanici bilgilerini koru
        yeni_token.user_id = mevcut.user_id
        yeni_token.email = mevcut.email
        yeni_token.display_name = mevcut.display_name
        yeni_token.avatar_url = mevcut.avatar_url

        self._depo.kaydet(yeni_token)
        return yeni_token

    def logout(self, provider: str) -> bool:
        """Provider'dan cikis yap (token'i sil)."""
        return self._depo.sil(provider)

    def durum(self, provider: str) -> Dict[str, Any]:
        """Provider icin token durumunu dondur.

        Returns:
            {
                "provider": "...",
                "var_mi": True/False,
                "gecerli_mi": True/False,
                "email": "...",
                "display_name": "...",
                "expires_at": "...",
            }
        """
        token = self._depo.yukle(provider)
        if not token:
            return {
                "provider": provider,
                "var_mi": False,
                "gecerli_mi": False,
                "mesaj": "Kayitli token bulunamadi.",
            }

        return {
            "provider": provider,
            "var_mi": True,
            "gecerli_mi": not token.is_expired,
            "access_token_prefix": token.access_token[:10] + "..." if token.access_token else "",
            "refresh_token_var": bool(token.refresh_token),
            "email": token.email,
            "display_name": token.display_name,
            "user_id": token.user_id,
            "expires_at": token.expires_at,
            "scope": token.scope,
        }

    def listele(self) -> List[Dict[str, Any]]:
        """Tum kayitli token'lari listele."""
        return self._depo.listele()

    def gecerli_token(self, provider: str) -> Optional[OAuthToken]:
        """Gecerli (suresi dolmamis) OAuthToken dondur.

        Suresi dolmussa ve refresh_token varsa otomatik yeniler.
        """
        token = self._depo.yukle(provider)
        if not token:
            return None

        if not token.is_expired:
            return token

        # Suresi dolmus, refresh dene
        if token.refresh_token:
            try:
                return self.refresh(provider)
            except Exception as e:
                logger.warning("[OAuthManager] Token yenilenemedi: %s", e)
                return None

        return None

    def provider(self, provider_id: str) -> Optional[OAuthProvider]:
        """Provider instance'ini dondur."""
        return self._providerlar.get(provider_id)

    def provider_listesi(self) -> List[str]:
        """Kayitli provider ID'lerini listele."""
        return list(self._providerlar.keys())


# ═══════════════════════════════════════════════════════════════════════════════
#  Singleton
# ═══════════════════════════════════════════════════════════════════════════════

_oauth_manager_instance: Optional[OAuthManager] = None


def oauth_manager_al() -> OAuthManager:
    """Varsayilan OAuthManager singleton'ini al."""
    global _oauth_manager_instance
    if _oauth_manager_instance is None:
        _oauth_manager_instance = OAuthManager()
    return _oauth_manager_instance


# ═══════════════════════════════════════════════════════════════════════════════
#  Motor Tools
# ═══════════════════════════════════════════════════════════════════════════════


def motor_kaydet(motor) -> None:
    """Motor'a OAuth araclarini kaydeder.

    Kaydettigi araclar:
        - OAUTH_GIRIS: OAuth provider'a giris URL'si al
        - OAUTH_DURUM: OAuth token durumunu goster
    """
    manager = oauth_manager_al()

    motor._plugin_arac_kaydet(
        "OAUTH_GIRIS",
        _oauth_giris_tool,
        "OAUTH_GIRIS(provider) — OAuth provider'a giris URL'si al. "
        "Parametre: provider=google|github|discord. "
        "Ornek: OAUTH_GIRIS(provider='google')"
    )
    motor._plugin_arac_kaydet(
        "OAUTH_DURUM",
        _oauth_durum_tool,
        "OAUTH_DURUM(provider) — OAuth token durumunu goster. "
        "Parametre: provider=google|github|discord. "
        "Ornek: OAUTH_DURUM(provider='github')"
    )
    logger.info("[OAuthManager] Motor'a 2 arac kaydedildi (OAUTH_GIRIS, OAUTH_DURUM)")


def _oauth_giris_tool(**kw) -> str:
    """OAUTH_GIRIS aracı."""
    args = kw.get("args", [])
    provider = args[0] if args else kw.get("provider", "")

    if not provider:
        return "[HATA] OAUTH_GIRIS: provider parametresi zorunlu (google/github/discord)"

    manager = oauth_manager_al()
    try:
        url = manager.login(provider)
        return (
            f"[OAUTH] {provider.upper()} giris URL'si:\n"
            f"  {url}\n\n"
            f"Bu URL'yi tarayicida acin, yetkilendirme yapin ve "
            f"yonlendirilen callback URL'deki 'code' parametresini alin."
        )
    except OAuthError as e:
        return f"[HATA] {e}"


def _oauth_durum_tool(**kw) -> str:
    """OAUTH_DURUM aracı."""
    args = kw.get("args", [])
    provider = args[0] if args else kw.get("provider", "")

    manager = oauth_manager_al()

    if provider:
        durum = manager.durum(provider)
        if durum.get("var_mi"):
            return (
                f"[OAUTH] {provider.upper()} Token Durumu:\n"
                f"  Gecerli: {'✅' if durum['gecerli_mi'] else '❌'}\n"
                f"  Email: {durum.get('email', '-')}\n"
                f"  Kullanici: {durum.get('display_name', '-')}\n"
                f"  Bitis: {durum.get('expires_at', '-')}\n"
                f"  Scope: {durum.get('scope', '-')}\n"
                f"  Token: {durum.get('access_token_prefix', '-')}"
            )
        return f"[OAUTH] {provider.upper()}: Kayitli token bulunamadi."

    # Tum provider'larin durumu
    lines = [f"[OAUTH] Tum Provider Durumlari:"]
    for p in manager.provider_listesi():
        durum = manager.durum(p)
        ikon = "✅" if durum.get("gecerli_mi") else ("⚠️" if durum.get("var_mi") else "❌")
        email = durum.get("email", "-")
        lines.append(f"  {ikon} {p.upper():8s} | {email}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
#  Test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== OAuthManager Test ===")

    manager = oauth_manager_al()

    print(f"\nKayitli provider'lar: {manager.provider_listesi()}")

    for p in manager.provider_listesi():
        prov = manager.provider(p)
        hazir = prov.hazir if prov else False
        print(f"  {p.upper():10s} | Hazir: {'✅' if hazir else '❌'}")

    print(f"\nToken durumu:")
    for p in manager.provider_listesi():
        durum = manager.durum(p)
        print(f"  {p.upper():10s} | {durum}")

    print("\n✓ Test tamamlandi")
