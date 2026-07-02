# -*- coding: utf-8 -*-
"""
reymen/guvenlik/ — ReYMeN Güvenlik Paketi

Guardrails, sandbox, güvenlik denetimleri ve threat detection.
Auth sistemi (JWT, API key, rol yönetimi) ve OAuth2 entegrasyonu.
"""

# Auth sistemi
from reymen.guvenlik.reymen_auth import (
    AuthManager,
    AuthStorage,
    AccessToken,
    User,
    JWTManager,
    auth_manager,
    validate_api_key_format,
    detect_api_key_provider,
    create_token,
    verify_token,
    validate_key,
    check_role,
    API_KEY_PROVIDERS,
)

# Auth middleware (Web UI)
try:
    from reymen.guvenlik.auth_middleware import (
        Authorization,
        FlaskAuth,
        extract_token,
        get_user_from_token,
        auth_required,
        role_required,
    )
except ImportError:
    pass

# OAuth2 sistemi (mevcut)
from reymen.guvenlik.oauth2 import (
    OAuth2Manager,
    OAuth2Provider,
    OAuth2Token,
    OAuth2UserInfo,
    OAuth2Registry,
    OAuth2TokenStorage,
    GoogleOAuth2Provider,
    DiscordOAuth2Provider,
    OAuth2ProviderError,
    oauth2_manager,
    oauth2_registry,
)

__all__ = [
    # Auth
    "AuthManager",
    "AuthStorage",
    "AccessToken",
    "User",
    "JWTManager",
    "auth_manager",
    "validate_api_key_format",
    "detect_api_key_provider",
    "create_token",
    "verify_token",
    "validate_key",
    "check_role",
    "API_KEY_PROVIDERS",
    # Auth Middleware
    "Authorization",
    "FlaskAuth",
    "extract_token",
    "get_user_from_token",
    "auth_required",
    "role_required",
    # OAuth2
    "OAuth2Manager",
    "OAuth2Provider",
    "OAuth2Token",
    "OAuth2UserInfo",
    "OAuth2Registry",
    "OAuth2TokenStorage",
    "GoogleOAuth2Provider",
    "DiscordOAuth2Provider",
    "OAuth2ProviderError",
    "oauth2_manager",
    "oauth2_registry",
]
