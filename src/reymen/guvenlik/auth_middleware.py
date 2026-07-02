# -*- coding: utf-8 -*-
"""
??? ReYMeN Auth Middleware ? Web UI i?in JWT tabanl? yetkilendirme.

Bu mod?l, ReYMeN'e ba?lanacak web aray?zleri i?in auth middleware
sa?lar. Hem FastAPI hem de Flask ile uyumlu ?ekilde tasarlanm??t?r.

Desteklenen Framework'ler:
    - FastAPI (tercih edilen)
    - Flask (uyumluluk modu)

Kullan?m (FastAPI):
    from reymen.guvenlik.auth_middleware import require_role, get_current_user
    from fastapi import FastAPI, Depends, HTTPException

    app = FastAPI()

    @app.get("/api/admin")
    async def admin_endpoint(user=Depends(require_role("admin"))):
        return {"message": "Yetkili eri?im", "user": user}

    @app.get("/api/me")
    async def me_endpoint(user=Depends(get_current_user)):
        return user

Kullan?m (Flask):
    from flask import Flask, jsonify, request
    from reymen.guvenlik.auth_middleware import flask_auth_middleware, FlaskAuth

    app = Flask(__name__)
    app.before_request(flask_auth_middleware)

    @app.route("/api/me")
    def me():
        auth = FlaskAuth(request)
        if not auth.authenticated:
            return jsonify({"error": "Yetkisiz"}), 401
        return jsonify(auth.user_info)
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Auth Headers / Token ??karma
# ═══════════════════════════════════════════════════════════════════════════════

def extract_token(headers: dict[str, str]) -> Optional[str]:
    """HTTP header'lardan Bearer token ??kar.

    S?ras?yla:
        1. Authorization: Bearer <token>
        2. X-API-Key: <token>
        3. X-Auth-Token: <token>
    """
    auth_header = headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]

    api_key = headers.get("X-API-Key", "")
    if api_key:
        return api_key

    auth_token = headers.get("X-Auth-Token", "")
    if auth_token:
        return auth_token

    return None


def extract_token_from_cookies(cookies: dict[str, str]) -> Optional[str]:
    """Cookie'lerden access_token ??kar."""
    return cookies.get("access_token") or cookies.get("token")


# ═══════════════════════════════════════════════════════════════════════════════
# Kullan?c? Bilgisi
# ═══════════════════════════════════════════════════════════════════════════════

def get_user_from_token(
    token: str,
    auth_manager_override: Any = None,
) -> Optional[dict[str, Any]]:
    """JWT token'dan kullanıcı bilgisini çıkar.

    Args:
        token: JWT token string
        auth_manager_override: İsteğe bağlı özel AuthManager (None = singleton)

    Returns:
        {
            "username": str,
            "role": str,
            "user_id": str,
            "is_authenticated": bool,
        }
        veya None (geçersiz token)
    """
    auth = auth_manager_override
    if auth is None:
        from reymen.guvenlik.reymen_auth import auth_manager as reymen_auth
        auth = reymen_auth
    payload = auth.verify_token(token)
    if payload is None:
        return None

    return {
        "username": payload.get("sub", ""),
        "role": payload.get("role", "guest"),
        "user_id": payload.get("uid", ""),
        "is_authenticated": True,
    }


def check_role_for_token(token: str, required_role: str) -> bool:
    """Token'daki kullan?c?n?n belirli bir role sahip olup olmad???n? kontrol et."""
    from reymen.guvenlik.reymen_auth import auth_manager
    return auth_manager.require_role(token, required_role)


# ═══════════════════════════════════════════════════════════════════════════════
# Yetkilendirme S?n?f?
# ═══════════════════════════════════════════════════════════════════════════════

class Authorization:
    """HTTP istekleri i?in yetkilendirme helper'?.

    ?zellikler:
        - Bearer token, API key ve cookie ile ?al???r
        - Rol bazl? eri?im kontrol?
        - Hata mesajlar? (HTTP yan?tlar? i?in)
    """

    def __init__(self, headers: dict[str, str],
                 cookies: Optional[dict[str, str]] = None,
                 auth_manager_override: Any = None):
        self.headers = headers
        self.cookies = cookies or {}
        self._auth_manager = auth_manager_override
        self._token: Optional[str] = None
        self._user: Optional[dict[str, Any]] = None
        self._resolve()

    def _resolve(self) -> None:
        self._token = extract_token(self.headers)
        if self._token is None:
            self._token = extract_token_from_cookies(self.cookies)
        if self._token:
            self._user = get_user_from_token(self._token, self._auth_manager)

    @property
    def token(self) -> Optional[str]:
        return self._token

    @property
    def authenticated(self) -> bool:
        return self._user is not None

    @property
    def user_info(self) -> Optional[dict[str, Any]]:
        return self._user

    @property
    def username(self) -> str:
        return (self._user or {}).get("username", "")

    @property
    def role(self) -> str:
        return (self._user or {}).get("role", "guest")

    @property
    def user_id(self) -> str:
        return (self._user or {}).get("user_id", "")

    def require_role(self, required_role: str) -> bool:
        """Belirli bir rol?n yeterli olup olmad???n? kontrol et.
        Yetki hiyerar?isi: guest < user < admin
        """
        hierarchy = {"guest": 0, "user": 1, "admin": 2}
        user_level = hierarchy.get(self.role, -1)
        required_level = hierarchy.get(required_role, 0)
        return user_level >= required_level

    def error_response(
        self, status_code: int = 401
    ) -> tuple[dict[str, Any], int]:
        """HTTP yan?t? olarak d?nd?r?lecek hata mesaj?."""
        messages = {
            401: "Yetkilendirme gerekli",
            403: "Bu i?lem i?in yetkiniz yok",
        }
        return {
            "error": True,
            "message": messages.get(status_code, "Eri?im reddedildi"),
            "status_code": status_code,
        }, status_code


# ═══════════════════════════════════════════════════════════════════════════════
# FastAPI Entegrasyonu
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from fastapi import Depends, HTTPException, Request
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

    _security = HTTPBearer(auto_error=False)

    async def get_current_user(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
    ) -> dict[str, Any]:
        # pylint: disable=unused-argument
        """FastAPI dependency: ge?erli kullan?c?y? d?nd?r?r."""
        headers = dict(request.headers)
        cookies = dict(request.cookies)

        auth = Authorization(headers, cookies)
        if not auth.authenticated:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": True,
                    "message": "Yetkilendirme gerekli",
                    "status_code": 401,
                },
            )
        return auth.user_info or {}

    def require_role(required_role: str):
        """FastAPI dependency: belirli bir rol gerektiren endpoint'ler i?in."""
        async def _dependency(
            user: dict[str, Any] = Depends(get_current_user),
        ) -> dict[str, Any]:
            hierarchy = {"guest": 0, "user": 1, "admin": 2}
            user_level = hierarchy.get(user.get("role", "guest"), -1)
            required_level = hierarchy.get(required_role, 0)

            if user_level < required_level:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": True,
                        "message": (
                            f"Bu i?lem i?in '{required_role}' yetkisi gerekli"
                        ),
                        "user_role": user.get("role"),
                        "required_role": required_role,
                        "status_code": 403,
                    },
                )
            return user

        return _dependency

    _FASTAPI_AVAILABLE = True

except ImportError:
    _FASTAPI_AVAILABLE = False

    async def get_current_user():
        """FastAPI kullan?lam?yor ? placeholder."""
        raise RuntimeError("FastAPI y?kl? de?il. Kurulum: pip install fastapi")

    def require_role(required_role: str):
        async def _dependency():
            raise RuntimeError("FastAPI y?kl? de?il")
        return _dependency


# ═══════════════════════════════════════════════════════════════════════════════
# Flask Entegrasyonu
# ═══════════════════════════════════════════════════════════════════════════════

class FlaskAuth:
    """Flask istekleri i?in auth helper."""

    def __init__(self, flask_request):
        headers = dict(flask_request.headers)
        cookies = dict(flask_request.cookies)
        self._auth = Authorization(headers, cookies)

    @property
    def token(self) -> Optional[str]:
        return self._auth.token

    @property
    def authenticated(self) -> bool:
        return self._auth.authenticated

    @property
    def user_info(self) -> Optional[dict[str, Any]]:
        return self._auth.user_info

    @property
    def username(self) -> str:
        return self._auth.username

    @property
    def role(self) -> str:
        return self._auth.role

    def require_role(self, required_role: str) -> bool:
        return self._auth.require_role(required_role)


def flask_auth_middleware():
    """Flask before_request middleware.

    Flask g nesnesine kullan?c? bilgisini ekler:
        g.current_user  -> dict veya None
        g.auth          -> FlaskAuth instance
    """
    try:
        from flask import g, request  # type: ignore
        auth = FlaskAuth(request)
        g.auth = auth  # type: ignore
        g.current_user = auth.user_info  # type: ignore
    except Exception as e:
        logger.debug("[AuthMiddleware] Flask init hatas?: %s", e)


# ═══════════════════════════════════════════════════════════════════════════════
# Dekorat?r Tabanl? Kullan?m (Framework Ba??ms?z)
# ═══════════════════════════════════════════════════════════════════════════════

from functools import wraps


def auth_required(func):
    """Genel auth dekorat?r? ? HTTP isteklerinde token zorunlulu?u."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            from flask import g, request as flask_request  # type: ignore
            auth = FlaskAuth(flask_request)
            if not auth.authenticated:
                return json.dumps({
                    "error": True,
                    "message": "Yetkilendirme gerekli",
                }), 401, {"Content-Type": "application/json"}
            g.auth = auth  # type: ignore
            g.current_user = auth.user_info  # type: ignore
        except ImportError:
            pass
        return func(*args, **kwargs)
    return wrapper


def role_required(required_role: str):
    """Rol bazl? eri?im dekorat?r?."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                from flask import g, request as flask_request  # type: ignore
                auth = FlaskAuth(flask_request)
                if not auth.authenticated:
                    return json.dumps({
                        "error": True,
                        "message": "Yetkilendirme gerekli",
                    }), 401, {"Content-Type": "application/json"}
                if not auth.require_role(required_role):
                    return json.dumps({
                        "error": True,
                        "message": (
                            f"Bu i?lem i?in '{required_role}' yetkisi gerekli"
                        ),
                        "user_role": auth.role,
                        "required_role": required_role,
                    }), 403, {"Content-Type": "application/json"}
                g.auth = auth  # type: ignore
                g.current_user = auth.user_info  # type: ignore
            except ImportError:
                pass
            return func(*args, **kwargs)
        return wrapper
    return decorator
