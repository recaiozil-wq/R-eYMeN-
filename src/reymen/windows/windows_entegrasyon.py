# -*- coding: utf-8 -*-
"""
windows_entegrasyon.py — ReYMeN Windows Otomasyon Entegrasyonu

Tum Windows modullerini event bus uzerinden birbirine baglar.
Tek cagri: windows_entegrasyonu_baslat()
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def windows_entegrasyonu_baslat():
    """Windows modullerini event bus ile birbirine bagla.

    Baglanti Semasi:
        tor_otomasyonu.py ──tor_hata──→ hata_cozucu.py
        tor_otomasyonu.py ──tor_basarili──→ akilli_yonlendirici.py
        araclar_nisan.py  ──nisan──→ tor_otomasyonu.py
        hata_cozucu.py    ──cozum_uygulandi──→ motor.py (log)
        motor.py          ──hata──→ cokus_raporlayici.py
        cokus_raporlayici.py ──cokus──→ kullanici (bildirim)
    """
    try:
        from reymen.windows.windows_events import event_bus_al, OLAY_HATA, OLAY_NISAN, \
            OLAY_TOR_HATA, OLAY_COKUS, OLAY_TOR_BASARILI, OLAY_COZUM_UYGULANDI

        bus = event_bus_al()
        baglanti_sayisi = 0

        # 1. tor_otomasyonu hata → hata_cozucu
        try:
            from reymen.cereyan.hata_cozucu import CozumUygulayici
            cozum = CozumUygulayici()
            bus.dinle(OLAY_TOR_HATA, lambda v: _tor_hatasini_coz(v, cozum))
            baglanti_sayisi += 1
        except ImportError as _e:
            logger.warning("[WindowsEntegrasyon] Modul yuklenemedi (L40): %s", ImportError)
            pass

        # 2. nisan bulundu → tor_otomasyonu
        try:
            from reymen.windows.tor_otomasyonu import TorNavigator
            tor = TorNavigator()
            bus.dinle(OLAY_NISAN, lambda v: _nisana_git(v, tor))
            baglanti_sayisi += 1
        except ImportError as _e:
            logger.warning("[WindowsEntegrasyon] Modul yuklenemedi (L49): %s", ImportError)
            pass

        # 3. hata → cokus raporu (son cares)
        try:
            from reymen.cereyan.cokus_raporlayici import cokus_raporu_uret
            bus.dinle(OLAY_HATA, lambda v: _cokus_kontrol(v, cokus_raporu_uret))
            baglanti_sayisi += 1
        except ImportError as _e:
            logger.warning("[WindowsEntegrasyon] Modul yuklenemedi (L57): %s", ImportError)
            pass

        # 4. tor basarili → akilli_yonlendirici (istenirse sec)
        try:
            from reymen.cereyan.akilli_yonlendirici import gorev_icin_model_sec
            bus.dinle(OLAY_TOR_BASARILI, lambda v: _basarili_log(v))
            baglanti_sayisi += 1
        except ImportError as _e:
            logger.warning("[WindowsEntegrasyon] Modul yuklenemedi (L65): %s", ImportError)
            pass

        # 5. Cozum uygulandi log
        bus.dinle(OLAY_COZUM_UYGULANDI, lambda v: _cozum_log(v))
        baglanti_sayisi += 1

        if baglanti_sayisi > 0:
            print(f"[WindowsEnt] {baglanti_sayisi} baglanti kuruldu")
        else:
            print("[WindowsEnt] Windows modulleri yuklu degil")

        return bus

    except ImportError as e:
        if "windows_events" not in str(e):
            logger.warning("[WindowsEnt] Modul yukleme hatasi: %s", e)
        return None
    except Exception as e:
        logger.error("[WindowsEnt] Baslatma hatasi: %s", e)
        return None


def _tor_hatasini_coz(veri, cozum):
    """Tor hatasi algilandiginda CozumUygulayici'yi cagir."""
    hata = veri.get("mesaj", "") or veri.get("hata", "")
    kaynak = veri.get("kaynak", "tor")
    print(f"[WindowsEnt] 🔧 Tor hatasi cozuluyor: {hata[:80]}")
    try:
        sonuc = cozum.cozum_uygula(hata, kaynak=kaynak)
        if sonuc:
            print(f"[WindowsEnt] ✅ Cozum uygulandi: {sonuc[:100]}")
    except Exception as e:
        logger.error("[WindowsEnt] Cozum hatasi: %s", e)


def _nisana_git(veri, tor):
    """Nisan bulundugunda Tor navigator'una git komutu ver."""
    hedef = veri.get("hedef", "") or veri.get("url", "")
    print(f"[WindowsEnt] 🎯 Nisana gidiliyor: {hedef[:80]}")
    try:
        tor.git(hedef)
    except Exception as e:
        logger.error("[WindowsEnt] Navigator hatasi: %s", e)


def _cokus_kontrol(veri, cokus_fn):
    """Cokme durumunda rapor hazirla."""
    hata_sayisi = veri.get("hata_sayisi", 0)
    if hata_sayisi >= 3:
        rapor = cokus_fn(
            gorev=veri.get("gorev", "Bilinmeyen"),
            deneme_sayisi=hata_sayisi,
        )
        if rapor:
            print(f"[WindowsEnt] 💥 Cokus raporu: {rapor[:100]}...")


def _basarili_log(veri):
    """Basarili islemi logla."""
    adim = veri.get("adim", "")
    sure = veri.get("sure_sn", 0)
    print(f"[WindowsEnt] ✅ {adim} basarili ({sure:.1f}s)")


def _cozum_log(veri):
    """Cozum uygulandigini logla."""
    cozum_adi = veri.get("cozum", "")
    print(f"[WindowsEnt] 🔧 Cozum uygulandi: {cozum_adi[:60]}")
