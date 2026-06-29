# -*- coding: utf-8 -*-
"""
gateway_yonetici.py — Çoklu platform gateway yöneticisi.

GatewayManager ile birden çok platform gateway'ini ayni anda
yonetebilir, mesaj broadcast yapabilir, platform bazli routing
uygulayabilirsiniz.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from reymen.ag.gateway_temel import GatewayBase

logger = logging.getLogger(__name__)


class GatewayManager:
    """
    Çoklu platform gateway yöneticisi.

    Kullanim:
        yonetici = GatewayManager()
        await yonetici.kaydet("telegram", TelegramGateway())
        await yonetici.kaydet("cli", CLIGateway())
        await yonetici.hepsini_baslat()

        # Tum platformlara mesaj gonder
        await yonetici.broadcast("Merhaba dunya!")

        # Sadece Telegram'a gonder
        await yonetici.gonder("Sadece Telegram", platform="telegram")

        # Durum raporu
        durum = yonetici.durum_raporu()
    """

    def __init__(self):
        self._gw_havuzu: Dict[str, GatewayBase] = {}
        self._aktif_platformlar: Set[str] = set()
        self._kilit = asyncio.Lock()
        self._dinleme_gorevleri: Dict[str, asyncio.Task] = {}
        self._mesaj_callback: Optional[callable] = None

    # ── Kayit / Kaldirma ────────────────────────────────────────────

    async def kaydet(self, platform: str, gateway: GatewayBase) -> bool:
        """
        Yeni bir platform gateway'i kaydeder.

        Args:
            platform: Platform adi (ornek: "telegram", "cli", "web")
            gateway: GatewayBase implementasyonu

        Returns:
            Basarili mi?
        """
        async with self._kilit:
            if platform in self._gw_havuzu:
                logger.warning(f"[GatewayManager] '{platform}' zaten kayitli, degistiriliyor.")
                # Eskisini durdur
                eski = self._gw_havuzu[platform]
                if eski.calisiyor:
                    await eski.stop()

            self._gw_havuzu[platform] = gateway
            logger.info(f"[GatewayManager] '{platform}' kaydedildi ({type(gateway).__name__}).")
            return True

    async def kaldir(self, platform: str) -> Optional[GatewayBase]:
        """
        Bir platform gateway'ini kaldirir ve durdurur.

        Args:
            platform: Kaldirilacak platform adi

        Returns:
            Kaldirilan gateway veya None
        """
        async with self._kilit:
            gateway = self._gw_havuzu.pop(platform, None)

        if gateway:
            if gateway.calisiyor:
                await gateway.stop()
            self._aktif_platformlar.discard(platform)
            await self._dinleme_durdur(platform)
            logger.info(f"[GatewayManager] '{platform}' kaldirildi.")

        return gateway

    def get(self, platform: str) -> Optional[GatewayBase]:
        """Platform gateway'ini doner (senkron, lock yok)."""
        return self._gw_havuzu.get(platform)

    def platform_listele(self) -> List[str]:
        """Kayitli platformlari listeler."""
        return list(self._gw_havuzu.keys())

    # ── Yasam Dongusu ───────────────────────────────────────────────

    async def baslat(self, platform: str) -> bool:
        """
        Belirli bir platform gateway'ini baslatir.

        Args:
            platform: Baslatilacak platform adi

        Returns:
            Basarili mi?
        """
        gateway = self._gw_havuzu.get(platform)
        if not gateway:
            logger.error(f"[GatewayManager] '{platform}' bulunamadi.")
            return False

        sonuc = await gateway.start()
        if sonuc:
            self._aktif_platformlar.add(platform)
            logger.info(f"[GatewayManager] '{platform}' baslatildi.")
        else:
            hata = gateway.son_hata or "bilinmeyen hata"
            logger.error(f"[GatewayManager] '{platform}' baslatilamadi: {hata}")

        return sonuc

    async def durdur(self, platform: str) -> bool:
        """
        Belirli bir platform gateway'ini durdurur.

        Args:
            platform: Durdurulacak platform adi

        Returns:
            Basarili mi?
        """
        gateway = self._gw_havuzu.get(platform)
        if not gateway:
            return False

        sonuc = await gateway.stop()
        self._aktif_platformlar.discard(platform)
        await self._dinleme_durdur(platform)

        if sonuc:
            logger.info(f"[GatewayManager] '{platform}' durduruldu.")

        return sonuc

    async def hepsini_baslat(self) -> Dict[str, bool]:
        """
        Kayitli tum platformlari baslatir.

        Returns:
            Platform -> basari durumu
        """
        sonuclar = {}
        for platform in list(self._gw_havuzu.keys()):
            sonuclar[platform] = await self.baslat(platform)
        return sonuclar

    async def hepsini_durdur(self) -> Dict[str, bool]:
        """
        Tum aktif platformlari durdurur.

        Returns:
            Platform -> basari durumu
        """
        sonuclar = {}
        for platform in list(self._aktif_platformlar):
            sonuclar[platform] = await self.durdur(platform)
        return sonuclar

    # ── Mesaj Gonderimi ─────────────────────────────────────────────

    async def gonder(self, mesaj: str, platform: str,
                     hedef: Optional[str] = None,
                     meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Belirli bir platforma mesaj gonderir.

        Args:
            mesaj: Gonderilecek mesaj
            platform: Hedef platform adi
            hedef: Platforma ozel hedef (chat_id, kanal_id vb.)
            meta: Ek metadata

        Returns:
            Gonderim sonucu
        """
        gateway = self._gw_havuzu.get(platform)
        if not gateway:
            return {"basarili": False, "hata": f"'{platform}' platformu bulunamadi"}

        if not gateway.calisiyor:
            return {"basarili": False, "hata": f"'{platform}' calismiyor"}

        return await gateway.send(mesaj, hedef=hedef, meta=meta)

    async def broadcast(self, mesaj: str,
                        hedef: Optional[str] = None,
                        meta: Optional[Dict[str, Any]] = None,
                        platformlar: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Belirtilen (veya tum aktif) platformlara mesaj gonderir.

        Args:
            mesaj: Gonderilecek mesaj
            hedef: Platforma ozel hedef
            meta: Ek metadata
            platformlar: Hedef platform listesi (None = tum aktif)

        Returns:
            Platform -> gonderim sonucu
        """
        hedefler = platformlar or list(self._aktif_platformlar)
        sonuclar = {}

        for platform in hedefler:
            sonuc = await self.gonder(mesaj, platform, hedef=hedef, meta=meta)
            sonuclar[platform] = sonuc

        return sonuclar

    async def broadcast_paralel(self, mesaj: str,
                                 hedef: Optional[str] = None,
                                 meta: Optional[Dict[str, Any]] = None,
                                 platformlar: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Tum platformlara eszamanli (paralel) mesaj gonderir.

        Args:
            mesaj: Gonderilecek mesaj
            hedef: Platforma ozel hedef
            meta: Ek metadata
            platformlar: Hedef platform listesi

        Returns:
            Platform -> gonderim sonucu
        """
        hedefler = platformlar or list(self._aktif_platformlar)

        async def _gonder(platform: str) -> Tuple[str, Dict[str, Any]]:
            sonuc = await self.gonder(mesaj, platform, hedef=hedef, meta=meta)
            return platform, sonuc

        gorevler = [_gonder(p) for p in hedefler]
        sonuclar_liste = await asyncio.gather(*gorevler, return_exceptions=True)

        sonuclar = {}
        for item in sonuclar_liste:
            if isinstance(item, Exception):
                sonuclar["hata"] = str(item)
            else:
                platform, sonuc = item
                sonuclar[platform] = sonuc

        return sonuclar

    # ── Mesaj Dinleme ───────────────────────────────────────────────

    async def dinlemeye_basla(self, platform: str,
                               callback: Optional[callable] = None) -> bool:
        """
        Bir platformdan mesaj dinlemeye baslar.

        Args:
            platform: Dinlenecek platform
            callback: Her mesajda cagrilacak fonksiyon

        Returns:
            Basarili mi?
        """
        gateway = self._gw_havuzu.get(platform)
        if not gateway or not gateway.calisiyor:
            return False

        if platform in self._dinleme_gorevleri:
            logger.warning(f"[GatewayManager] '{platform}' zaten dinleniyor.")
            return True

        async def _dinle():
            while True:
                try:
                    mesaj = await gateway.receive(timeout=1.0)
                    if mesaj:
                        mesaj["platform"] = platform
                        if callback:
                            await callback(mesaj)
                        elif self._mesaj_callback:
                            await self._mesaj_callback(mesaj)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning(f"[GatewayManager] '{platform}' dinleme hatasi: {e}")
                    await asyncio.sleep(1)

        self._dinleme_gorevleri[platform] = asyncio.create_task(_dinle())
        logger.info(f"[GatewayManager] '{platform}' dinlenmeye baslandi.")
        return True

    async def dinlemeyi_durdur(self, platform: str) -> None:
        """Platform dinlemesini durdur."""
        await self._dinleme_durdur(platform)

    async def _dinleme_durdur(self, platform: str) -> None:
        """Ic: dinleme gorevini iptal et."""
        gorev = self._dinleme_gorevleri.pop(platform, None)
        if gorev and not gorev.done():
            gorev.cancel()
            try:
                await gorev
            except asyncio.CancelledError:
                pass

    def genel_callback_ayarla(self, callback: callable) -> None:
        """Tum platformlardan gelen mesajlar icin genel callback."""
        self._mesaj_callback = callback

    # ── Durum / Rapor ───────────────────────────────────────────────

    async def durum_raporu(self) -> Dict[str, Any]:
        """Tum platformlarin durum raporu."""
        rapor = {
            "zaman": time.time(),
            "aktif_platform_sayisi": len(self._aktif_platformlar),
            "kayitli_platform_sayisi": len(self._gw_havuzu),
            "aktif_platformlar": list(self._aktif_platformlar),
            "platformlar": {},
        }

        for platform, gateway in self._gw_havuzu.items():
            try:
                saglik = await gateway.health_check()
                rapor["platformlar"][platform] = {
                    "tip": type(gateway).__name__,
                    "durum_ozet": gateway.durum_raporu(),
                    "saglik": saglik,
                }
            except Exception as e:
                rapor["platformlar"][platform] = {
                    "tip": type(gateway).__name__,
                    "hata": str(e),
                }

        return rapor

    async def saglik_kontrolu(self) -> Dict[str, str]:
        """Hizli saglik kontrolu — her platform icin tek kelime."""
        sonuclar = {}
        for platform, gateway in self._gw_havuzu.items():
            try:
                saglik = await gateway.health_check()
                sonuclar[platform] = saglik.get("durum", "bilinmiyor")
            except Exception:
                sonuclar[platform] = "hata"
        return sonuclar

    # ── Yardimcilar ─────────────────────────────────────────────────

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.hepsini_durdur()

    def __repr__(self) -> str:
        return (f"<GatewayManager platform={len(self._gw_havuzu)} "
                f"aktif={len(self._aktif_platformlar)}>")


# ── Motor Kayit ─────────────────────────────────────────────────────

def motor_kaydet(motor) -> None:
    """Motor'a GatewayManager araçlarını kaydeder."""
    motor._plugin_arac_kaydet(
        "GATEWAY_YONETICI_OLUSTUR",
        lambda: "GatewayManager() — yeni bir gateway yoneticisi olusturur",
        "Yeni GatewayManager ornegi olusturur",
    )
    motor._plugin_arac_kaydet(
        "GATEWAY_YONETICI_DURUM",
        lambda: "GatewayManager.durum_raporu() — tum platform durumlarini gosterir",
        "GatewayManager durum raporu",
    )
    motor._plugin_arac_kaydet(
        "GATEWAY_BROADCAST",
        lambda mesaj="", platformlar="[]": f"GatewayManager.broadcast('{mesaj}', platformlar={platformlar})",
        "Tum platformlara (veya belirtilenlere) mesaj gonderir",
    )
