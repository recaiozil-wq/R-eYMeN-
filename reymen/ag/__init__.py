# -*- coding: utf-8 -*-
"""
reymen/ag — Gateway ve Arac Modulu.
"""

from reymen.ag.gateway_temel import GatewayBase
from reymen.ag.salted_gateway import (
    SaltedGateway,
    TelegramRateLimiter,
    AutoReconnector,
    SessionManager,
    CrashRecovery,
    TelegramGateway,
)
from reymen.ag.platform_gateways import CLIGateway, WebGateway, DiscordGateway
from reymen.ag.gateway_yonetici import GatewayManager
from reymen.ag.delegasyon import (
    DelegasyonSistemi,
    SubAgent,
    SubAgentCalistirici,
    GorevAyrıştırıcı,
    sistem_al,
    motor_kaydet as delegasyon_motor_kaydet,
    konusma_dongusu_hook_bul,
)

# Kolay erişim
delegasyon_sistemi_al = sistem_al

__all__ = [
    # Temel
    "GatewayBase",
    # Salted
    "SaltedGateway",
    "TelegramRateLimiter",
    "AutoReconnector",
    "SessionManager",
    "CrashRecovery",
    # Platform
    "TelegramGateway",
    "CLIGateway",
    "WebGateway",
    "DiscordGateway",
    # Yonetici
    "GatewayManager",
    # Delegasyon (P2)
    "DelegasyonSistemi",
    "SubAgent",
    "SubAgentCalistirici",
    "GorevAyrıştırıcı",
    "delegasyon_sistemi_al",
    "sistem_al",
    "delegasyon_motor_kaydet",
    "konusma_dongusu_hook_bul",
]
