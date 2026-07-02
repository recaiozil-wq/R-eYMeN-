# -*- coding: utf-8 -*-
"""
reymen/mcp/__init__.py — ReYMeN MCP İstemci Paketi.

Model Context Protocol (MCP) sunucularına bağlanma, tool keşfetme ve çağırma.

Alt Modüller:
  mcp_manager      — Async MCP yöneticisi (singleton)
  mcp_tool         — Motor araç kaydı (MCP_TOOL_LISTELE / MCP_TOOL_CAGIR)
  mcp_catalog      — Önceden tanımlı MCP sunucu kataloğu
  mcp_discovery    — config.yaml + .env'den otomatik keşif (MCP_DISCOVERY)
  mcp_reconnect    — Heartbeat + otomatik yeniden bağlanma (MCP_RECONNECT_*)

Kullanım:
    from reymen.mcp.mcp_manager import mcp_manager
    from reymen.mcp.mcp_discovery import mcp_kesfet
    from reymen.mcp.mcp_reconnect import mcp_reconnect_baslat

    # Otomatik keşif
    yeni = mcp_kesfet()

    # Başlat ve keşfet
    await mcp_manager().baslat()

    # Heartbeat + reconnect başlat
    await mcp_reconnect_baslat()

    # Tool çağır
    sonuc = await mcp_manager().cagir("github", "issues/list", {"repo": "user/repo"})

    # Tüm tool'ları listele
    tools = mcp_manager().tum_araclari_getir()
"""

import asyncio
import logging
import sys

from src.reymen.mcp.mcp_tool import motor_kaydet as mcp_tool_kaydet
from src.reymen.mcp.mcp_discovery import motor_kaydet as mcp_discovery_kaydet
from src.reymen.mcp.mcp_reconnect import motor_kaydet as mcp_reconnect_kaydet
from src.reymen.mcp.mcp_discovery import mcp_kesfet
from src.reymen.mcp.mcp_reconnect import mcp_reconnect_baslat, mcp_reconnect_durumu

logger = logging.getLogger(__name__)

__all__ = [
    "mcp_tool_kaydet",
    "mcp_discovery_kaydet",
    "mcp_reconnect_kaydet",
    "baslangicta_baslat",
    "otomatik_kesif_yap",
    "_cift_mcp_uyar",
]


# ═══════════════════════════════════════════════════════════════════════════
# Modül seviyesinde otomatik keşif (motor._plugin_moduller_yukle() sırasında)
# ═══════════════════════════════════════════════════════════════════════════

def otomatik_kesif_yap() -> int:
    """Modül import edildiğinde MCP sunucularını otomatik keşfeder.

    Motor._plugin_moduller_yukle() akışına entegredir:
      "reymen.mcp" import edildiğinde bu fonksiyon çağrılır,
      config.yaml + .env + ReYMeN profilinden MCP sunucularını bulur
      ve mcp_manager'a otomatik kaydeder.

    Returns:
        Yeni bulunan MCP sunucu sayısı
    """
    try:
        yeni = mcp_kesfet(geri_bildirim=True)
        if yeni > 0:
            logger.info("[MCP] Otomatik keşif: %d yeni sunucu bulundu (modül import)", yeni)
        return yeni
    except Exception as e:
        logger.debug("[MCP] Otomatik keşif hatası (modül import): %s", e)
        return 0


# Modül import edildiğinde otomatik keşif çalıştır
_otomatik_kesif_sonuc = otomatik_kesif_yap()


def _cift_mcp_uyar() -> None:
    """reymen.arac.native_mcp_client import edilmisse uyar (çift MCP client)."""
    try:
        if "reymen.arac.native_mcp_client" in sys.modules:
            logger.warning(
                "[MCP] ⚠️ Çift MCP client tespit edildi! "
                "reymen.mcp ve reymen.arac.native_mcp_client paralel çalışıyor. "
                "Yeni geliştirmeler için reymen.mcp paketini kullanın."
            )
    except Exception as _e:
        __import__("logging").getLogger(__name__).warning(
            "[SessizExcept] %%s: %%s", type(_e).__name__, _e
        )


def baslangicta_baslat() -> None:
    """Motor yüklenirken otomatik MCP keşif ve reconnect başlat.

    Motor başlatılırken motor_kaydet() içinden çağrılır:
      1. config.yaml + .env'den MCP sunucularını keşfeder
      2. Heartbeat + otomatik yeniden bağlanma döngüsünü başlatır

    Hata varsa sessizce logla, crash yapma. Halihazırda reconnect
    çalışıyorsa ikinci kez başlatma yapılmaz.
    """
    try:
        # Halihazırda reconnect çalışıyorsa atla
        if mcp_reconnect_durumu().get("aktif", False):
            logger.debug("[MCP] baslangicta_baslat: reconnect zaten çalışıyor")
            return

        # 1. MCP sunucularını keşfet
        yeni = mcp_kesfet(geri_bildirim=True)
        if yeni > 0:
            logger.info("[MCP] Baslangicta kesif: %d yeni sunucu bulundu", yeni)

        # 2. Reconnect başlat
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(mcp_reconnect_baslat())
                logger.info("[MCP] Baslangicta reconnect baslatildi")
            finally:
                loop.close()
        except Exception as e:
            logger.warning(
                "[MCP] Baslangicta reconnect baslatma hatasi (onemsiz): %s", e
            )
    except Exception as e:
        logger.warning("[MCP] Baslangicta baslatma hatasi (onemsiz): %s", e)


def motor_kaydet(motor) -> None:
    """Tüm MCP araçlarını Motor'a kaydet.

    Motor başlatılırken çağrılır. Sırasıyla:
      1. Çift MCP client uyarısı (_cift_mcp_uyar)
      2. MCP_TOOL_LISTELE / MCP_TOOL_CAGIR (mcp_tool)
      3. MCP_DISCOVERY / MCP_DISCOVERY_DURUM (mcp_discovery)
      4. MCP_RECONNECT_BASLAT / MCP_RECONNECT_DURDUR / MCP_RECONNECT_DURUM (mcp_reconnect)
      5. MCP_OTOMATIK_BASLAT — keşif + reconnect'i tek adımda başlatır
    """
    # Çift MCP client uyarısı
    _cift_mcp_uyar()

    # Alt modül araçlarını kaydet
    mcp_tool_kaydet(motor)
    mcp_discovery_kaydet(motor)
    mcp_reconnect_kaydet(motor)

    # MCP_OTOMATIK_BASLAT — motor başlangıcında çağrılacak auto-start tool
    if hasattr(motor, "_plugin_arac_kaydet"):
        motor._plugin_arac_kaydet(
            "MCP_OTOMATIK_BASLAT",
            baslangicta_baslat,
            "MCP sunucularını otomatik keşfeder, heartbeat + yeniden bağlanma "
            "döngüsünü başlatır. Motor başlangıcında otomatik çağrılır. "
            "Kullanım: MCP_OTOMATIK_BASLAT() — keşif + reconnect tek adımda.",
        )
