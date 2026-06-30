"""🔐 ReYMeN Auth — Provider pattern + JWT cookie + roller.

ReYMeN dashboard_auth pattern'inin birebir kopyası:
  - AuthProvider ABC (ReYMeN'teki DashboardAuthProvider)
  - Session dataclass (user_id, display_name, role, provider, expires_at)
  - Provider registry (register_provider, get_provider, list_providers)
  - JWT cookie (reymen_session_at / reymen_session_rt)
  - Role bazlı izin sistemi
  - Audit logging

Kullanim:
    from reymen.web_ui.auth import (
        register_provider, get_provider, list_providers,
        user_manager, token_manager, Session,
    )
    
    # Kullanici yönetimi
    user_manager.kullanici_ekle("operator", "sifre", role="operator")
    
    # Provider registry
    from reymen.web_ui.auth import PasswordAuthProvider
    register_provider(PasswordAuthProvider())
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PROJE_KOK = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Roller
# ---------------------------------------------------------------------------

class Role(str, Enum):
    ADMIN = "admin"       # Tam yetki
    OPERATOR = "operator" # Araç kullanabilir, yapılandıramaz
    VIEWER = "viewer"     # Sadece görüntüleme

ROLE_PERMISSIONS = {
    Role.ADMIN: {
        "gateway.baslat", "gateway.durdur", "gateway.restart", "gateway.ayarlar",
        "plugin.aktif_et", "plugin.devre_disina_al",
        "user.ekle", "user.sil", "user.sifre_degistir",
        "system.yeniden_baslat", "system.guncelle",
        "log.goruntule", "log.temizle",
        "a2a.yonet", "a2a.mesaj_gonder",
        "maliyet.goruntule", "kalite.goruntule",
        "kanban.yonet",
    },
    Role.OPERATOR: {
        "gateway.baslat", "gateway.durdur",
        "plugin.aktif_et", "plugin.devre_disina_al",
        "log.goruntule",
        "a2a.mesaj_gonder",
        "maliyet.goruntule", "kalite.goruntule",
        "kanban.yonet",
    },
    Role.VIEWER: {
        "log.goruntule",
        "maliyet.goruntule", "kalite.goruntule",
    },
}

# ---------------------------------------------------------------------------
# Session (ReYMeN'teki Session dataclass'inin birebir karsiligi)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Session:
    """Dogrulanmis kullanici oturumu. ReYMeN'teki Session ile ayni desen.

    user_id:   kullanici adi
    role:      admin | operator | viewer
    provider:  hangi auth provider dogruladi
    expires_at: unix epoch saniye (access_token'in exp claim'i)
    access_token: JWT token
    refresh_token: refresh token (opsiyonel, bos string olabilir)
    """
    user_id: str
    display_name: str
    role: str
    provider: str
    expires_at: int
    access_token: str
    refresh_token: str = ""

# ---------------------------------------------------------------------------
# Hata siniflari (ReYMeN pattern)
# ---------------------------------------------------------------------------

class ProviderError(Exception):
    """Auth provider ulasilamaz / gecici hata -> HTTP 503"""

class InvalidCredentialsError(Exception):
    """Kullanici adi/sifre yanlis -> HTTP 401"""

# ---------------------------------------------------------------------------
# AuthProvider ABC (ReYMeN'teki DashboardAuthProvider)
# ---------------------------------------------------------------------------

class AuthProvider(ABC):
    """Auth saglayici arayuzu.

    Alt siniflar su alanlari tanimlamali:
      - name: str          (provider kimligi, orn: "password")
      - display_name: str  (kullaniciya gosterilen ad, orn: "Şifre ile Giriş")

    Metodlar:
      - verify_session(access_token) -> Session | None
      - refresh_session(refresh_token) -> Session
      - revoke_session(refresh_token) -> None
    """

    name: str = ""
    display_name: str = ""

    @abstractmethod
    def verify_session(self, *, access_token: str) -> Optional[Session]:
        """Token dogrula. Gecersiz/expired ise None don."""

    @abstractmethod
    def refresh_session(self, *, refresh_token: str) -> Session:
        """Refresh token ile yeni Session olustur."""

    @abstractmethod
    def revoke_session(self, *, refresh_token: str) -> None:
        """Session'i sonlandir (best-effort)."""

# ---------------------------------------------------------------------------
# Provider Registry (ReYMeN pattern)
# ---------------------------------------------------------------------------

_providers: dict[str, AuthProvider] = {}

def register_provider(provider: AuthProvider) -> None:
    """Auth provider kaydet. Ayni isimde provider varsa uzerine yazar."""
    if not provider.name:
        raise ValueError("AuthProvider.name bos olamaz")
    _providers[provider.name] = provider
    logger.info("Auth provider kaydedildi: %s (%s)", provider.name, provider.display_name)

def get_provider(name: str) -> Optional[AuthProvider]:
    """Isme gore provider getir."""
    return _providers.get(name)

def list_providers() -> list[AuthProvider]:
    """Kayitli tum provider'lari listele."""
    return list(_providers.values())

def clear_providers() -> None:
    """Test amaciyla tum provider'lari temizle."""
    _providers.clear()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class AuthConfig:
    secret: str = field(default_factory=lambda: os.getenv(
        "WEB_UI_SECRET",
        hashlib.sha256(f"ReYMeN-web-ui-{os.getpid()}-{time.time()}".encode()).hexdigest()[:32]
    ))
    token_expiry: int = 86400          # 24 saat (access token)
    refresh_expiry: int = 604800        # 7 gun (refresh token)
    cookie_name: str = "reymen_session_at"   # ReYMeN ile uyumlu
    cookie_rt_name: str = "reymen_session_rt"  # refresh token cookie
    users_file: Path = field(default_factory=lambda: PROJE_KOK / ".ReYMeN" / "web" / "users.json")
    password_provider: str = field(default_factory=lambda: os.getenv("AUTH_PROVIDER", "password"))

# ---------------------------------------------------------------------------
# Kullanici yonetimi
# ---------------------------------------------------------------------------

@dataclass
class UserData:
    password_hash: str
    role: str = Role.VIEWER.value
    created: float = field(default_factory=time.time)

class UserManager:
    """users.json ile kullanici yonetimi + roller."""

    def __init__(self, config: AuthConfig) -> None:
        self.config = config
        self._users: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        dosya = self.config.users_file
        if dosya.exists():
            try:
                data = json.loads(dosya.read_text(encoding="utf-8"))
                for k, v in data.items():
                    if isinstance(v, str):
                        self._users[k] = {"password_hash": v, "role": Role.ADMIN.value, "created": 0}
                    elif isinstance(v, dict):
                        if "role" not in v:
                            v["role"] = Role.ADMIN.value
                        self._users[k] = v
            except Exception as e:
                logger.warning("users.json okunamadi: %s", e)
                self._default_users()
        else:
            self._default_users()
            self._save()

    def _default_users(self) -> None:
        self._users = {
            "admin": {
                "password_hash": self._hash("reymen"),
                "role": Role.ADMIN.value,
                "created": time.time(),
            }
        }

    def _save(self) -> None:
        self.config.users_file.parent.mkdir(parents=True, exist_ok=True)
        self.config.users_file.write_text(
            json.dumps(self._users, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    @staticmethod
    def _hash(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def verify(self, username: str, password: str) -> bool:
        user = self._users.get(username)
        if not user:
            return False
        return hmac.compare_digest(user["password_hash"], self._hash(password))

    def kullanici_ekle(self, username: str, password: str,
                       role: str = Role.VIEWER.value) -> tuple[bool, str]:
        if username in self._users:
            return False, "Kullanici zaten var"
        try:
            Role(role)
        except ValueError:
            return False, f"Gecersiz rol: {role}. Gecerliler: {[r.value for r in Role]}"
        self._users[username] = {
            "password_hash": self._hash(password),
            "role": role,
            "created": time.time(),
        }
        self._save()
        return True, f"Kullanici eklendi: {username} ({role})"

    def kullanici_sil(self, username: str) -> tuple[bool, str]:
        if username not in self._users:
            return False, "Kullanici bulunamadi"
        if username == "admin":
            return False, "admin kullanicisi silinemez"
        del self._users[username]
        self._save()
        return True, f"Kullanici silindi: {username}"

    def set_password(self, username: str, password: str,
                     old_password: str | None = None) -> tuple[bool, str]:
        if username not in self._users:
            return False, "Kullanici bulunamadi"
        if old_password and not hmac.compare_digest(
            self._users[username]["password_hash"], self._hash(old_password)
        ):
            return False, "Eski sifre yanlis"
        self._users[username]["password_hash"] = self._hash(password)
        self._save()
        return True, "Sifre degistirildi"

    def set_role(self, username: str, role: str) -> tuple[bool, str]:
        if username not in self._users:
            return False, "Kullanici bulunamadi"
        try:
            Role(role)
        except ValueError:
            return False, f"Gecersiz rol: {role}"
        self._users[username]["role"] = role
        self._save()
        return True, f"Rol degistirildi: {username} -> {role}"

    def get_role(self, username: str) -> str | None:
        user = self._users.get(username)
        if user:
            return user.get("role", Role.VIEWER.value)
        return None

    def has_permission(self, username: str, permission: str) -> bool:
        role_str = self.get_role(username)
        if not role_str:
            return False
        try:
            role = Role(role_str)
        except ValueError:
            return False
        return permission in ROLE_PERMISSIONS.get(role, set())

    def list_users(self) -> list[dict]:
        return [
            {"username": k, "role": v.get("role", Role.VIEWER.value),
             "created": v.get("created", 0)}
            for k, v in self._users.items()
        ]

    def get_user_role(self, username: str) -> str | None:
        return self.get_role(username)

# ---------------------------------------------------------------------------
# JWT Token (HMAC-SHA256, ReYMeN cookie uyumlu)
# ---------------------------------------------------------------------------

class TokenManager:
    """HMAC-SHA256 JWT token + refresh token."""

    def __init__(self, config: AuthConfig) -> None:
        self.config = config

    def create(self, username: str, role: str = Role.VIEWER.value,
               provider: str = "password") -> str:
        """Access token olustur (kisa omurlu, cookie'de saklanir)."""
        payload = json.dumps({
            "user": username,
            "role": role,
            "provider": provider,
            "exp": int(time.time()) + self.config.token_expiry,
            "iat": int(time.time()),
        }, separators=(",", ":"))
        b64 = self._b64_encode(payload.encode())
        sig = self._sign(b64)
        return f"{b64}.{sig}"

    def create_refresh(self, username: str) -> str:
        """Refresh token olustur (uzun omurlu, cookie'de saklanir)."""
        payload = json.dumps({
            "user": username,
            "type": "refresh",
            "exp": int(time.time()) + self.config.refresh_expiry,
            "iat": int(time.time()),
        }, separators=(",", ":"))
        b64 = self._b64_encode(payload.encode())
        sig = self._sign(b64)
        return f"{b64}.{sig}"

    def verify(self, token: str) -> Optional[dict]:
        """Token dogrula, {user, role, provider, exp} dondur veya None."""
        try:
            parts = token.split(".")
            if len(parts) != 2:
                return None
            b64, sig = parts
            expected_sig = self._sign(b64)
            if not hmac.compare_digest(sig, expected_sig):
                return None
            payload = json.loads(self._b64_decode(b64))
            if payload.get("exp", 0) < time.time():
                return None
            return payload
        except Exception:
            return None

    def verify_refresh(self, token: str) -> Optional[str]:
        """Refresh token dogrula, kullanici adini dondur veya None."""
        data = self.verify(token)
        if not data or data.get("type") != "refresh":
            return None
        return data.get("user")

    def get_user(self, token: str) -> Optional[str]:
        data = self.verify(token)
        return data.get("user") if data else None

    def get_role(self, token: str) -> Optional[str]:
        data = self.verify(token)
        return data.get("role") if data else None

    def get_provider(self, token: str) -> str:
        data = self.verify(token)
        return data.get("provider", "password") if data else "password"

    def expires_in(self, token: str) -> int:
        """Token'in kalan omrunu saniye cinsinden dondur (min 60)."""
        data = self.verify(token)
        if not data:
            return 0
        return max(60, int(data.get("exp", 0)) - int(time.time()))

    def _sign(self, data: str) -> str:
        return hmac.new(
            self.config.secret.encode(), data.encode(), hashlib.sha256
        ).hexdigest()[:16]

    @staticmethod
    def _b64_encode(data: bytes) -> str:
        return data.hex()

    @staticmethod
    def _b64_decode(data: str) -> bytes:
        return bytes.fromhex(data)

# ---------------------------------------------------------------------------
# PasswordAuthProvider (ReYMeN'teki DashboardAuthProvider'in ReYMeN implementasyonu)
# ---------------------------------------------------------------------------

class PasswordAuthProvider(AuthProvider):
    """Kullanici adi/sifre ile giris yapan auth provider.

    ReYMeN'teki password provider pattern'inin birebir karsiligi:
      - supports_password = True
      - complete_password_login(username, password) -> Session
      - verify_session(access_token) -> Session | None
      - refresh_session(refresh_token) -> Session
    """

    name = "password"
    display_name = "Şifre ile Giriş"

    def __init__(self, user_manager: UserManager | None = None,
                 token_manager: TokenManager | None = None) -> None:
        # Lazy import to avoid circular dependency at module level
        self._um: UserManager | None = user_manager
        self._tm: TokenManager | None = token_manager

    @property
    def um(self) -> UserManager:
        if self._um is None:
            from reymen.web_ui.auth import user_manager
            self._um = user_manager
        return self._um

    @property
    def tm(self) -> TokenManager:
        if self._tm is None:
            from reymen.web_ui.auth import token_manager
            self._tm = token_manager
        return self._tm

    def complete_password_login(self, username: str, password: str) -> Session:
        """Kullanici adi/sifre dogrula, Session don.

        Raises:
            InvalidCredentialsError: yanlis kullanici adi veya sifre
        """
        if not self.um.verify(username, password):
            raise InvalidCredentialsError("Hatali kullanici adi veya sifre")

        role = self.um.get_user_role(username) or Role.VIEWER.value
        at = self.tm.create(username, role=role, provider="password")
        rt = self.tm.create_refresh(username)

        return Session(
            user_id=username,
            display_name=username,
            role=role,
            provider=self.name,
            expires_at=int(time.time()) + self.tm.config.token_expiry,
            access_token=at,
            refresh_token=rt,
        )

    def verify_session(self, *, access_token: str) -> Optional[Session]:
        """Access token dogrula."""
        data = self.tm.verify(access_token)
        if not data:
            return None
        return Session(
            user_id=data["user"],
            display_name=data["user"],
            role=data.get("role", Role.VIEWER.value),
            provider=data.get("provider", self.name),
            expires_at=data.get("exp", 0),
            access_token=access_token,
        )

    def refresh_session(self, *, refresh_token: str) -> Session:
        """Refresh token ile yeni access token olustur.

        Raises:
            ProviderError: refresh token gecersizse (ReYMeN pattern)
        """
        username = self.tm.verify_refresh(refresh_token)
        if not username:
            raise ProviderError("Refresh token gecersiz veya sureci dolmus")

        role = self.um.get_user_role(username) or Role.VIEWER.value
        new_at = self.tm.create(username, role=role, provider="password")
        new_rt = self.tm.create_refresh(username)

        return Session(
            user_id=username,
            display_name=username,
            role=role,
            provider=self.name,
            expires_at=int(time.time()) + self.tm.config.token_expiry,
            access_token=new_at,
            refresh_token=new_rt,
        )

    def revoke_session(self, *, refresh_token: str) -> None:
        """Session sonlandir. Best-effort (stateless JWT'de bir sey yapmaya gerek yok)."""
        pass

# ---------------------------------------------------------------------------
# Audit logging (ReYMeN'teki AuditEvent pattern)
# ---------------------------------------------------------------------------

class AuditEvent:
    LOGIN_SUCCESS = "login.success"
    LOGIN_FAILURE = "login.failure"
    LOGOUT = "logout"
    SESSION_REFRESH = "session.refresh"
    SESSION_REVOKE = "session.revoke"
    PASSWORD_CHANGE = "password.change"
    USER_CREATED = "user.created"
    USER_DELETED = "user.deleted"

def audit_log(event: str, *, provider: str = "", user_id: str = "",
              ip: str = "", reason: str = "", **extra) -> None:
    """ReYMeN audit_log islevi ile ayni desen."""
    entry = {
        "event": event,
        "timestamp": time.time(),
        "provider": provider or "password",
        "user_id": user_id or "",
        "ip": ip,
        "reason": reason,
    }
    entry.update(extra)
    logger.info("AUTH: %s — user=%s provider=%s ip=%s reason=%s",
                event, user_id, provider, ip, reason)

# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_config = AuthConfig()
user_manager = UserManager(_config)
token_manager = TokenManager(_config)

# Varsayilan provider'i kaydet
_password_provider = PasswordAuthProvider(user_manager, token_manager)
register_provider(_password_provider)
