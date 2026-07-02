# -*- coding: utf-8 -*-
"""
reymen/mcp/mcp_reconnect.py — MCP Bağlantı Testi ve Otomatik Yeniden Bağlanma Modülü.

Tüm MCP sunucu bağlantılarını periyodik olarak kontrol eder:
  - Her 30 saniyede bir heartbeat (tools/list) gönderir
  - Kopan bağlantıları exponential backoff ile yeniden bağlar (max 5 deneme)
  - Durumu raporlar

Kullanım:
    from reymen.mcp.mcp_reconnect import mcp_reconnect_baslat, mcp_reconnect_durdur

    # Arkaplanda heartbeat + reconnect başlat
    await mcp_reconnect_baslat()

    # Durum raporu
    rapor = mcp_reconnect_durum_raporu()
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from src.reymen.mcp.mcp_manager import mcp_manager, MCPServerBaglantisi

logger = logging.getLogger(__name__)

# ── Varsayılan ayarlar ───────────────────────────────────────────────────
HEARTBEAT_ARALIK_SN = 30  # Her N saniyede bir heartbeat
MAX_YENIDEN_DENEME = 5    # Maksimum yeniden bağlanma denemesi
MAX_BACKOFF_SN = 60       # Maksimum bekleme süresi (exponential backoff)

# ── Global state ─────────────────────────────────────────────────────────
_reconnect_gorev: Optional[asyncio.Task] = None
_durduruldu = False
_durum: dict[str, Any] = {
    "aktif": False,
    "heartbeat_sayisi": 0,
    "yeniden_baglanma_sayisi": 0,
    "hata_sayisi": 0,
    "baslangic_zamani": None,
    "sunucu_durumlari": {},
}


# ═══════════════════════════════════════════════════════════════════════════
# Heartbeat — Her MCP Sunucusuna Periyodik Sinyal
# ═══════════════════════════════════════════════════════════════════════════

async def _heartbeat_gonder(
    baglanti: MCPServerBaglantisi,
) -> bool:
    """Tek bir MCP sunucusuna heartbeat (tools/list) gönder.

    Returns:
        True = başarılı, False = başarısız / bağlantı koptu.
    """
    try:
        istek = {"jsonrpc": "2.0", "id": 0, "method": "tools/list"}
        sonuc = await baglanti._gonder(istek)
        if "error" in sonuc:
            logger.warning(
                "MCP Heartbeat [%s]: hata %s", baglanti.ad, sonuc["error"]
            )
            return False
        baglanti._baglandi = True
        return True
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.debug("MCP Heartbeat [%s]: %s", baglanti.ad, e)
        return False


# ═══════════════════════════════════════════════════════════════════════════
# Yeniden Bağlanma — Exponential Backoff ile
# ═══════════════════════════════════════════════════════════════════════════

async def _yeniden_baglan(
    baglanti: MCPServerBaglantisi,
    deneme: int,
) -> bool:
    """Exponential backoff ile bir MCP sunucusuna yeniden bağlan.

    Args:
        baglanti: Yeniden bağlanılacak MCP sunucu bağlantısı
        deneme: Mevcut deneme sayısı (0-indexed)

    Returns:
        True = başarılı, False = tüm denemeler başarısız
    """
    bekle_sn = min(2 ** (deneme + 1), MAX_BACKOFF_SN)
    logger.info(
        "MCP Yeniden Bağlanma [%s]: deneme %d/%d, %ds bekleniyor...",
        baglanti.ad, deneme + 1, MAX_YENIDEN_DENEME, bekle_sn,
    )
    try:
        await asyncio.sleep(bekle_sn)
    except asyncio.CancelledError:
        return False

    try:
        # tools/list ile keşif yap (bağlantıyı test et)
        istek = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        sonuc = await baglanti._gonder(istek)
        if "error" in sonuc:
            logger.warning(
                "MCP Yeniden Bağlanma [%s]: deneme %d başarısız: %s",
                baglanti.ad, deneme + 1, sonuc["error"],
            )
            return False

        # Başarılı → araç listesini güncelle
        tools = sonuc.get("result", {}).get("tools", [])
        baglanti._tools = tools
        baglanti._baglandi = True
        logger.info(
            "MCP Yeniden Bağlanma [%s]: başarılı (%d tool)",
            baglanti.ad, len(tools),
        )
        return True

    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.warning(
            "MCP Yeniden Bağlanma [%s]: deneme %d istisna: %s",
            baglanti.ad, deneme + 1, e,
        )
        return False


# ═══════════════════════════════════════════════════════════════════════════
# Ana Döngü — Heartbeat + Reconnect
# ═══════════════════════════════════════════════════════════════════════════

async def _reconnect_dongusu() -> None:
    """Heartbeat ve yeniden bağlanma ana döngüsü.

    Her HEARTBEAT_ARALIK_SN saniyede bir tüm MCP sunucularına heartbeat gönderir.
    Başarısız olanları exponential backoff ile yeniden bağlamayı dener.
    """
    global _durum

    mgr = mcp_manager()
    _durum["aktif"] = True
    _durum["baslangic_zamani"] = time.time()

    logger.info("MCP Reconnect: heartbeat döngüsü başladı (aralık: %ds)", HEARTBEAT_ARALIK_SN)

    try:
        while not _durduruldu:
            sunucu_listesi = list(mgr._sunucular.items())

            if not sunucu_listesi:
                await asyncio.sleep(HEARTBEAT_ARALIK_SN)
                continue

            for ad, baglanti in sunucu_listesi:
                if _durduruldu:
                    break

                # Sunucu durumunu izle
                if ad not in _durum["sunucu_durumlari"]:
                    _durum["sunucu_durumlari"][ad] = {
                        "bagli": False,
                        "son_heartbeat": None,
                        "son_hata": None,
                        "yeniden_baglanma_sayisi": 0,
                        "hata_sayisi": 0,
                    }

                sd = _durum["sunucu_durumlari"][ad]

                # Heartbeat gönder
                basarili = await _heartbeat_gonder(baglanti)
                _durum["heartbeat_sayisi"] += 1

                if basarili:
                    sd["bagli"] = True
                    sd["son_heartbeat"] = time.time()
                    sd["son_hata"] = None
                    # Yeniden bağlanma denemelerini sıfırla (başarılı heartbeat)
                    sd["yeniden_baglanma_sayisi"] = 0
                else:
                    sd["bagli"] = False
                    sd["son_hata"] = time.time()
                    sd["hata_sayisi"] += 1
                    _durum["hata_sayisi"] += 1

                    # Bağlantı koptu → exponential backoff ile yeniden bağlan
                    deneme = 0
                    while deneme < MAX_YENIDEN_DENEME and not _durduruldu:
                        basarili_mi = await _yeniden_baglan(baglanti, deneme)
                        if basarili_mi:
                            _durum["yeniden_baglanma_sayisi"] += 1
                            sd["yeniden_baglanma_sayisi"] += 1
                            sd["bagli"] = True
                            sd["son_hata"] = None
                            break
                        deneme += 1

                    if not sd["bagli"] and deneme >= MAX_YENIDEN_DENEME:
                        logger.error(
                            "MCP Reconnect [%s]: %d deneme sonunda bağlanamadı, "
                            "manuel müdahale gerekebilir",
                            ad, MAX_YENIDEN_DENEME,
                        )

            # Belirtilen aralık kadar bekle
            await asyncio.sleep(HEARTBEAT_ARALIK_SN)

    except asyncio.CancelledError:
        logger.info("MCP Reconnect: döngü iptal edildi")
    except Exception as e:
        logger.warning("MCP Reconnect: döngü hatası: %s", e)
    finally:
        _durum["aktif"] = False


# ═══════════════════════════════════════════════════════════════════════════
# Public API — Başlat / Durdur / Durum
# ═══════════════════════════════════════════════════════════════════════════

async def mcp_reconnect_baslat() -> bool:
    """Heartbeat + yeniden bağlanma döngüsünü başlat.

    Returns:
        True = başlatıldı, False = zaten çalışıyor.
    """
    global _reconnect_gorev, _durduruldu

    if _reconnect_gorev is not None and not _reconnect_gorev.done():
        logger.info("MCP Reconnect: zaten çalışıyor")
        return False

    _durduruldu = False
    _reconnect_gorev = asyncio.create_task(_reconnect_dongusu())
    logger.info("MCP Reconnect: başlatıldı")
    return True


def mcp_reconnect_durdur() -> None:
    """Heartbeat + yeniden bağlanma döngüsünü durdur."""
    global _durduruldu

    _durduruldu = True
    if _reconnect_gorev is not None and not _reconnect_gorev.done():
        _reconnect_gorev.cancel()
    _durum["aktif"] = False
    logger.info("MCP Reconnect: durduruldu")


def mcp_reconnect_durumu() -> dict[str, Any]:
    """Reconnect sisteminin mevcut durumunu döndür.

    Returns:
        {
            "aktif": bool,
            "heartbeat_sayisi": int,
            "yeniden_baglanma_sayisi": int,
            "hata_sayisi": int,
            "calisma_suresi_sn": float,
            "sunucular": {
                "sunucu_adi": {
                    "bagli": bool,
                    "son_heartbeat": float|None,
                    "son_hata": float|None,
                    "yeniden_baglanma_sayisi": int,
                    "hata_sayisi": int,
                }
            }
        }
    """
    global _durum
    su_an = time.time()
    baslangic = _durum.get("baslangic_zamani")
    calisma_suresi = su_an - baslangic if baslangic else 0.0

    return {
        "aktif": _durum.get("aktif", False),
        "heartbeat_sayisi": _durum.get("heartbeat_sayisi", 0),
        "yeniden_baglanma_sayisi": _durum.get("yeniden_baglanma_sayisi", 0),
        "hata_sayisi": _durum.get("hata_sayisi", 0),
        "calisma_suresi_sn": round(calisma_suresi, 1),
        "sunucular": dict(_durum.get("sunucu_durumlari", {})),
    }


def mcp_reconnect_durum_raporu() -> str:
    """İnsan-okunabilir reconnect durum raporu."""
    durum = mcp_reconnect_durumu()
    aktif_str = "🟢 Çalışıyor" if durum["aktif"] else "🔴 Durduruldu"
    sure_str = f"{durum['calisma_suresi_sn']:.0f}s" if durum["calisma_suresi_sn"] > 0 else "-"

    satirlar = [
        "[MCP Reconnect] Bağlantı İzleme Raporu",
        "=" * 50,
        f"  Durum: {aktif_str}",
        f"  Çalışma Süresi: {sure_str}",
        f"  Heartbeat: {durum['heartbeat_sayisi']}",
        f"  Yeniden Bağlanma: {durum['yeniden_baglanma_sayisi']}",
        f"  Hata: {durum['hata_sayisi']}",
        "",
        "  Sunucular:",
    ]

    if not durum["sunucular"]:
        satirlar.append("    (izlenen sunucu yok)")
    else:
        for ad, sd in durum["sunucular"].items():
            simge = "🟢" if sd["bagli"] else "🔴"
            son_hb = (
                f"{(time.time() - sd['son_heartbeat']):.0f}s önce"
                if sd["son_heartbeat"] else "hiç"
            )
            satirlar.append(
                f"    {simge} {ad}: son heartbeat {son_hb}, "
                f"yeniden bağlanma {sd['yeniden_baglanma_sayisi']}, "
                f"hata {sd['hata_sayisi']}"
            )

    return "\n".join(satirlar)


# ═══════════════════════════════════════════════════════════════════════════
# Motor Tool Kaydı
# ═══════════════════════════════════════════════════════════════════════════

def motor_kaydet(motor) -> None:
    """MCP_RECONNECT araçlarını Motor'a kaydet.

    Motor başlatılırken çağrılır.
    """
    if not hasattr(motor, "_plugin_arac_kaydet"):
        logger.warning("Motor'da _plugin_arac_kaydet metodu yok")
        return

    motor._plugin_arac_kaydet(
        "MCP_RECONNECT_BASLAT",
        _mcp_reconnect_baslat_sync,
        "MCP sunucularına periyodik heartbeat (30sn) göndermeyi ve "
        "kopan bağlantıları otomatik yeniden bağlamayı başlatır. "
        "Kullanım: MCP_RECONNECT_BASLAT()",
    )

    motor._plugin_arac_kaydet(
        "MCP_RECONNECT_DURDUR",
        mcp_reconnect_durdur,
        "MCP heartbeat/yeniden bağlanma döngüsünü durdurur. "
        "Kullanım: MCP_RECONNECT_DURDUR()",
    )

    motor._plugin_arac_kaydet(
        "MCP_RECONNECT_DURUM",
        mcp_reconnect_durum_raporu,
        "MCP bağlantı izleme sisteminin durum raporunu döndürür. "
        "Kullanım: MCP_RECONNECT_DURUM()",
    )


def _mcp_reconnect_baslat_sync() -> str:
    """Senkron wrapper for mcp_reconnect_baslat."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(mcp_reconnect_baslat())
            return "[MCP Reconnect] Başlatıldı"
        finally:
            loop.close()
    except Exception as e:
        return f"[MCP Reconnect] Hata: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# CLI Test
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import time

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("=== MCP Reconnect Test ===\n")

    async def test():
        # Önce keşif yap
        from reymen.mcp.mcp_discovery import mcp_kesfet
        eklenen = mcp_kesfet()
        print(f"Keşfedilen sunucu: {eklenen}")

        # Reconnect başlat
        baslatildi = await mcp_reconnect_baslat()
        print(f"Reconnect başlatıldı: {baslatildi}")

        # 5 saniye bekle (birkaç heartbeat)
        print("\n5 saniye bekleniyor...")
        await asyncio.sleep(5)

        # Durum raporu
        print(f"\n{mcp_reconnect_durum_raporu()}")

        # Durdur
        mcp_reconnect_durdur()
        print("\n→ Reconnect durduruldu")

    asyncio.run(test())
