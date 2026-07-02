# -*- coding: utf-8 -*-
"""reymen/mcp/mcp_tool.py — MCP Araç Kaydı ve Çağrı Fonksiyonları.

ReYMeN Motor'una MCP_TOOL_LISTELE / MCP_TOOL_CAGIR fonksiyonlarını kaydeder.
reymen.arac.mcp_client_tool altyapısını kullanır (canlı stdio/HTTP MCP client).

Doğrudan da kullanılabilir:

    from reymen.mcp.mcp_tool import mcp_tool_cagir, mcp_tool_listele

    tools = mcp_tool_listele()
    sonuc = mcp_tool_cagir("github", "issues/list", {"repo": "user/repo"})
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from src.reymen.arac.mcp_client_tool import (
    mcp_client_baglan,
    mcp_client_arac_cagir,
    mcp_client,
)

logger = logging.getLogger(__name__)

# Bağlantı önbelleği — ilk çağrıda tüm config'deki sunuculara bağlanır
_initialized = False


def _ensure_connected():
    """Tüm config'deki MCP sunucularına bağlan (bir kere)."""
    global _initialized
    if _initialized:
        return
    yonetici = mcp_client()
    for ad in list(yonetici._konfig.keys()):
        try:
            yonetici._sunucu_al(ad)
        except Exception as e:
            logger.warning("MCP [%s] bağlanamadı: %s", ad, e)
    _initialized = True


def mcp_tool_listele(sunucu_ad: str = "") -> list[dict]:
    """Belirtilen sunucudaki veya tüm MCP araçlarını listele.

    Args:
        sunucu_ad: Boş = tüm sunucular, dolu = sadece o sunucu

    Returns:
        [{"sunucu", "name", "description"}, ...]
    """
    _ensure_connected()
    yonetici = mcp_client()
    tum = []
    for ad, araclar in yonetici.tum_araclar().items():
        for arac in araclar:
            tum.append({
                "sunucu": ad,
                "name": arac.get("name", "?"),
                "description": arac.get("description", ""),
                "inputSchema": arac.get("inputSchema", {}),
            })
    if sunucu_ad:
        tum = [a for a in tum if a["sunucu"] == sunucu_ad]
    return tum


def mcp_tool_cagir(
    sunucu: str, arac: str, args: Optional[dict] = None
) -> str:
    """MCP sunucusunda bir aracı çağır.

    Args:
        sunucu: MCP sunucu adı
        arac: Çağrılacak araç
        args: Parametreler

    Returns:
        Aracın döndürdüğü metin içerik
    """
    _ensure_connected()
    return mcp_client_arac_cagir(sunucu, arac, **(args or {}))


def motor_kaydet(motor) -> None:
    """MCP araçlarını Motor'a kaydet.

    Motor başlatılırken çağrılır.
    """
    _ensure_connected()
    if not hasattr(motor, "_plugin_arac_kaydet"):
        logger.warning("Motor'da _plugin_arac_kaydet metodu yok")
        return

    yonetici = mcp_client()
    yonetici.motor_kaydet(motor)

    # Ayrıca genel liste/çağrı fonksiyonlarını kaydet
    motor._plugin_arac_kaydet(
        "MCP_TOOL_LISTELE",
        mcp_tool_listele,
        "MCP sunucularındaki araçları listeler. "
        "Kullanım: MCP_TOOL_LISTELE(sunucu_ad='')",
    )
    motor._plugin_arac_kaydet(
        "MCP_TOOL_CAGIR",
        mcp_tool_cagir,
        "MCP sunucusunda araç çağırır. "
        "Kullanım: MCP_TOOL_CAGIR(sunucu='github', "
        "arac='issues/list', args={'repo': 'user/repo'})",
    )
