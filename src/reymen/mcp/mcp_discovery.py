# -*- coding: utf-8 -*-
"""
reymen/mcp/mcp_discovery.py — MCP Sunucu Otomatik Keşif Modülü.

MCP sunucularını birden fazla kaynaktan otomatik keşfeder:
  1. config.yaml → mcp_servers: bölümü (proje + .ReYMeN/)
  2. ~/.hermes/profiles/reymen/config.yaml → mcp_servers: bölümü (Hermes profili)
  3. .env → MCP_* / MCP_SERVER_* / MCP_SUNUCU_* prefixli değişkenler
  4. OS environment → MCP_* / MCP_SERVER_* / MCP_SUNUCU_* prefixli değişkenler

Keşfedilen sunucuları mcp_manager'a kaydeder ve Motor'a MCP_DISCOVERY aracı olarak ekler.
Motor başlatılırken (reymen.mcp import edildiğinde) otomatik keşif çalıştırılır.

Kullanım:
    from reymen.mcp.mcp_discovery import mcp_kesfet, motor_kaydet
    yeni_sayisi = mcp_kesfet()
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Varsayılan config/env yolları ────────────────────────────────────────
PROJE_KOK = Path(__file__).parent.parent.parent
HERMES_PROFIL_KOK = Path.home() / ".ReYMeN" / "profiles" / "reymen"

CONFIG_YOLLARI = [
    PROJE_KOK / "config.yaml",
    PROJE_KOK / ".ReYMeN" / "config.yaml",
    HERMES_PROFIL_KOK / "config.yaml",
]
ENV_YOLLARI = [
    PROJE_KOK / ".env",
    PROJE_KOK / ".ReYMeN" / ".env",
    Path.home() / ".ReYMeN" / ".env",
    HERMES_PROFIL_KOK / ".env",
]


# ═══════════════════════════════════════════════════════════════════════════
# .env'den MCP Sunucu Keşfi
# ═══════════════════════════════════════════════════════════════════════════

# .env'de desteklenen değişken şablonları:
#   MCP_SUNUCU_ADI_KOMUT = "npx"
#   MCP_SUNUCU_ADI_ARGS  = "-y @modelcontextprotocol/server-github"
#   MCP_SUNUCU_ADI_URL   = "https://mcp.example.com/mcp"
#   MCP_SUNUCU_ADI_TRANSPORT = "stdio"  (stdio / http varsayılan: stdio)
#   MCP_SUNUCU_ADI_TIMEOUT = "30"
#   MCP_SUNUCU_ADI_ENV_KEY = "value"
#
# Ayrıca İngilizce/Türkçe varyantları da desteklenir:
#   MCP_SERVER_NAME_COMMAND = "npx"          (MCP_SERVER_*)
#   MCP_SUNUCU_ADI_KOMUT   = "npx"          (MCP_SUNUCU_*)
#
# NOT: MCP_SERVER_* ve MCP_SUNUCU_* aynı anda varsa, MCP_SERVER_* önceliklidir.
_MCP_ENV_RE = re.compile(r"^MCP_([A-Z0-9_]+)_(.+)$")
_MCP_SERVER_ENV_RE = re.compile(r"^MCP_SERVER_([A-Z0-9_]+)_(.+)$")
_MCP_SUNUCU_ENV_RE = re.compile(r"^MCP_SUNUCU_([A-Z0-9_]+)_(.+)$")


def _env_ad_ve_anahtar(env_ad: str) -> Optional[tuple[str, str]]:
    """MCP_* / MCP_SERVER_* / MCP_SUNUCU_* değişken adını (sunucu_adi, anahtar) çiftine dönüştür.

    Örn: MCP_GITHUB_KOMUT → ("github", "komut")
         MCP_REMOTE_API_URL → ("remote_api", "url")
         MCP_SERVER_GITHUB_COMMAND → ("github", "command")
         MCP_SUNUCU_GITHUB_KOMUT → ("github", "komut")
         MCP_GITHUB_ENV_GITHUB_TOKEN → ("github", "env_GITHUB_TOKEN")

    Öncelik sırası: MCP_SERVER_* > MCP_SUNUCU_* > MCP_*
    """
    # 1. MCP_SERVER_* (en spesifik, en yüksek öncelik)
    m = _MCP_SERVER_ENV_RE.match(env_ad)
    if m:
        sunucu_raw, anahtar_raw = m.group(1), m.group(2)
        return _parse_env_match(sunucu_raw, anahtar_raw)

    # 2. MCP_SUNUCU_* (Türkçe)
    m = _MCP_SUNUCU_ENV_RE.match(env_ad)
    if m:
        sunucu_raw, anahtar_raw = m.group(1), m.group(2)
        return _parse_env_match(sunucu_raw, anahtar_raw)

    # 3. MCP_* (genel, eski format)
    m = _MCP_ENV_RE.match(env_ad)
    if not m:
        return None
    return _parse_env_match(m.group(1), m.group(2))


def _parse_env_match(sunucu_raw: str, anahtar_raw: str) -> tuple[str, str]:
    """Env regex match gruplarını (sunucu_adi, anahtar) çiftine dönüştür.

    _env_ad_ve_anahtar için yardımcı: regex greedy matching'den kaynaklanan
    belirsizlikleri çözer (örn. ENV_GITHUB_TOKEN gibi alt çizgi içeren anahtarlar).
    """
    sunucu_adi = sunucu_raw.lower()
    anahtar = anahtar_raw.lower()

    # Regex greedy: group1 çok yakalamış olabilir (ENV_* durumu)
    # Örn: MCP_GITHUB_ENV_GITHUB_TOKEN
    #   greedy: group1=GITHUB_ENV_GITHUB, group2=TOKEN
    #   group1'de _ENV_ varsa, ENV_'den öncesi sunucu adı
    if "_ENV_" in sunucu_raw:
        # group1: GITHUB_ENV_GITHUB → sunucu=GITHUB, kalan=ENV_GITHUB
        idx = sunucu_raw.index("_ENV_")
        sunucu_adi = sunucu_raw[:idx].lower()
        env_key = sunucu_raw[idx + 5:] + "_" + anahtar_raw  # "GITHUB" + "_" + "TOKEN"
        if env_key.startswith("_"):
            env_key = env_key[1:]
        return (sunucu_adi, f"env_{env_key}")

    # Örn: MCP_GITHUB_ENV_TOKEN (ENV_KEY tek kelime)
    #   greedy: group1=GITHUB_ENV, group2=TOKEN
    #   group1 _ENV ile bitiyor (trailing underscore yok)
    if sunucu_raw.endswith("_ENV"):
        sunucu_adi = sunucu_raw[:-4].lower()
        return (sunucu_adi, f"env_{anahtar_raw}")

    # ENV_* anahtarı: MCP_SERVER formatında group2 ENV_ ile başlıyorsa
    # Örn: MCP_SERVER_GITHUB_ENV_GITHUB_TOKEN
    #   regex MCP_SERVER_: group1=GITHUB, group2=ENV_GITHUB_TOKEN
    if anahtar_raw.startswith("ENV_"):
        env_key = anahtar_raw[4:]  # "GITHUB_TOKEN"
        return (sunucu_adi, f"env_{env_key}")

    return (sunucu_adi, anahtar)


def _env_oku() -> dict[str, dict]:
    """.env dosyalarından MCP_* / MCP_SERVER_* / MCP_SUNUCU_* prefixli değişkenleri oku.

    Kaynak sırası (sonraki öncekini ezer):
      1. .env dosyaları (proje, .ReYMeN, ~/.hermes, ~/.hermes/profiles/reymen)
      2. OS environment (env var'lar dosyadakileri ezer)

    Returns:
        {sunucu_adi: {anahtar: deger}, ...}
    """
    env_vars: dict[str, str] = {}

    # 1. Dosyalardan oku
    for yol in ENV_YOLLARI:
        if not yol.exists():
            continue
        try:
            for satir in yol.read_text(encoding="utf-8", errors="ignore").splitlines():
                satir = satir.strip()
                if not satir or satir.startswith("#") or "=" not in satir:
                    continue
                anahtar, _, deger = satir.partition("=")
                anahtar = anahtar.strip()
                deger = deger.strip().strip("\"'")
                if (anahtar.startswith("MCP_")
                        or anahtar.startswith("MCP_SERVER_")
                        or anahtar.startswith("MCP_SUNUCU_")):
                    env_vars[anahtar] = deger
        except Exception as e:
            logger.debug(".env okuma hatası %s: %s", yol, e)

    # 2. OS environment'dan da oku (öncelikli)
    for anahtar, deger in os.environ.items():
        if (anahtar.startswith("MCP_")
                or anahtar.startswith("MCP_SERVER_")
                or anahtar.startswith("MCP_SUNUCU_")):
            env_vars[anahtar] = deger

    if not env_vars:
        return {}

    # Değişkenleri sunucu bazında grupla
    sunucular: dict[str, dict] = {}
    for env_ad, deger in env_vars.items():
        parsed = _env_ad_ve_anahtar(env_ad)
        if not parsed:
            continue
        sunucu_adi, anahtar = parsed
        if sunucu_adi not in sunucular:
            sunucular[sunucu_adi] = {"_kaynak": ".env"}
        sunucular[sunucu_adi][anahtar] = deger

    return sunucular


# ═══════════════════════════════════════════════════════════════════════════
# config.yaml'dan MCP Sunucu Keşfi
# ═══════════════════════════════════════════════════════════════════════════

def _config_oku() -> dict[str, dict]:
    """config.yaml dosyalarından mcp_servers: bölümünü oku.

    Tüm config dosyalarını sırayla tara, sonraki dosyalar öncekileri ezer.
    Sıra: proje/config.yaml → .ReYMeN/config.yaml → ~/.hermes/profiles/reymen/config.yaml

    Returns:
        {sunucu_adi: {anahtar: deger}, ...}
    """
    import yaml
    birlesik: dict[str, dict] = {}

    for yol in CONFIG_YOLLARI:
        if not yol.exists():
            continue
        try:
            with open(yol, encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            servers_raw = cfg.get("mcp_servers", {})
            if not servers_raw:
                continue
            for ad, ayar in servers_raw.items():
                if not isinstance(ayar, dict):
                    continue
                kayit = dict(ayar)
                kayit["_kaynak"] = str(yol)
                # command: "npx" + args: [...] → command: ["npx", ...]
                if isinstance(kayit.get("command"), str) and "args" in kayit:
                    kayit["command"] = [kayit["command"]] + kayit.get("args", [])
                    kayit.pop("args", None)
                elif isinstance(kayit.get("command"), str):
                    kayit["command"] = [kayit["command"]]
                kayit.setdefault("transport", "stdio")
                birlesik[ad] = kayit  # sonraki dosya öncekini ezer
        except ImportError:
            logger.debug("PyYAML yok, config.yaml yüklenemedi")
        except Exception as e:
            logger.debug("Config okuma hatası %s: %s", yol, e)

    return birlesik


# ═══════════════════════════════════════════════════════════════════════════
# .env → mcp_manager formatına dönüşüm
# ═══════════════════════════════════════════════════════════════════════════

def _env_sunucuyu_cfg_cevir(sunucu_adi: str, env_ayar: dict) -> dict:
    """.env'den okunan MCP sunucu ayarlarını mcp_manager formatına çevir.

    MCP_GITHUB_KOMUT = "npx"
    MCP_GITHUB_ARGS = "-y @modelcontextprotocol/server-github"
    MCP_GITHUB_TRANSPORT = "stdio"
    MCP_GITHUB_TIMEOUT = "30"
    MCP_GITHUB_ENV_GITHUB_TOKEN = "ghp_xxx"

    ↓

    {"command": ["npx", "-y", "@modelcontextprotocol/server-github"],
     "transport": "stdio", "timeout": 30, "env": {"GITHUB_TOKEN": "ghp_xxx"}}
    """
    cfg: dict = {}
    cfg["transport"] = env_ayar.get("transport", "stdio")
    cfg["_kaynak"] = env_ayar.get("_kaynak", ".env")

    # Komut + argümanlar
    komut = env_ayar.get("komut")
    args_raw = env_ayar.get("args", "")
    if komut:
        if args_raw:
            # args: string → liste (boşlukla ayrılmış, tırnaklar saygılı değil basit)
            args_list = args_raw.split()
            cfg["command"] = [komut] + args_list
        else:
            cfg["command"] = [komut]

    # URL (HTTP transport)
    url = env_ayar.get("url")
    if url:
        cfg["url"] = url
        cfg["transport"] = "http"

    # Host/Port (TCP transport)
    host = env_ayar.get("host")
    if host:
        cfg["host"] = host
    port = env_ayar.get("port")
    if port:
        try:
            cfg["port"] = int(port)
        except ValueError:
            cfg["port"] = port

    # Timeout
    to = env_ayar.get("timeout")
    if to:
        try:
            cfg["timeout"] = int(to)
        except ValueError:
            cfg["timeout"] = 30

    # env: {KEY: val} — MCP_SUNUCU_ENV_KEY=val şeklindeki değişkenler
    env_dict = {}
    for k, v in env_ayar.items():
        if k.startswith("env_"):
            env_key = k[4:]  # "GITHUB_TOKEN"
            # Environment variable reference çözümle: ${VAR} veya direk değer
            if v.startswith("${") and v.endswith("}"):
                env_val = os.environ.get(v[2:-1], "")
            else:
                env_val = v
            env_dict[env_key] = env_val
    if env_dict:
        cfg["env"] = env_dict

    return cfg


# ═══════════════════════════════════════════════════════════════════════════
# Ana Keşif Fonksiyonu
# ═══════════════════════════════════════════════════════════════════════════

def mcp_kesfet(geri_bildirim: bool = True) -> int:
    """Tüm kaynaklardan MCP sunucularını keşfet ve mcp_manager'a kaydet.

    Keşif sırası (sonraki öncekini ezer):
      1. config.yaml → mcp_servers: (proje + .ReYMeN/)
      2. ~/.hermes/profiles/reymen/config.yaml → mcp_servers:
      3. .env → MCP_* / MCP_SERVER_* / MCP_SUNUCU_* değişkenleri
         (dosyalar: proje/.env, .ReYMeN/.env, ~/.hermes/.env, ~/.hermes/profiles/reymen/.env)
      4. OS environment → MCP_* / MCP_SERVER_* / MCP_SUNUCU_* değişkenleri

    Args:
        geri_bildirim: Keşif sonucunu logla (varsayılan: True)

    Returns:
        Yeni eklenen MCP sunucu sayısı.
    """
    from reymen.mcp.mcp_manager import mcp_manager

    # 1. config.yaml'dan oku
    config_sunucular = _config_oku()

    # 2. .env'den oku
    env_sunucular_raw = _env_oku()
    env_sunucular = {}
    for ad, ayar in env_sunucular_raw.items():
        env_sunucular[ad] = _env_sunucuyu_cfg_cevir(ad, ayar)

    # 3. Birleştir (config → env; env öncelikli)
    birlesik = dict(config_sunucular)
    for ad, ayar in env_sunucular.items():
        if ad in birlesik:
            # .env ayarları config'deki varsayılanları ezer
            birlesik[ad].update(ayar)
            birlesik[ad]["_kaynak"] = "config.yaml + .env"
        else:
            birlesik[ad] = ayar

    if not birlesik:
        if geri_bildirim:
            logger.info("MCP Keşif: config.yaml veya .env'de MCP sunucu bulunamadı")
        return 0

    # 4. mcp_manager'a kaydet
    mgr = mcp_manager()
    yeni_sayisi = 0
    for ad, cfg in birlesik.items():
        # Zaten kayıtlıysa atla
        if ad in mgr._sunucular:
            continue
        # Kaydet
        mgr.ekle(ad, cfg)
        yeni_sayisi += 1
        logger.debug(
            "MCP Keşif: '%s' eklendi (kaynak: %s, transport: %s)",
            ad, cfg.get("_kaynak", "?"), cfg.get("transport", "stdio"),
        )

    if geri_bildirim and yeni_sayisi > 0:
        logger.info(
            "MCP Keşif: %d yeni sunucu bulundu, toplam %d",
            yeni_sayisi, len(mgr._sunucular),
        )

    return yeni_sayisi


def mcp_kesif_durumu() -> dict[str, Any]:
    """Keşfedilen tüm MCP sunucularının durumunu döndür.

    Returns:
        {
            "toplam": 3,
            "sunucular": [
                {"ad": "...", "transport": "...", "kaynak": "...", "bagli": bool},
                ...
            ]
        }
    """
    from reymen.mcp.mcp_manager import mcp_manager

    mgr = mcp_manager()
    sunucular = []
    for ad, baglanti in mgr._sunucular.items():
        cfg = baglanti.cfg
        sunucular.append({
            "ad": ad,
            "transport": cfg.get("transport", "stdio"),
            "kaynak": cfg.get("_kaynak", "?"),
            "tool_sayisi": len(baglanti._tools),
            "bagli": baglanti.baglandi,
        })

    return {
        "toplam": len(sunucular),
        "sunucular": sunucular,
    }


def mcp_kesif_izle_baslat(interval_sn: int = 120) -> bool:
    """MCP konfig dosyalarini periyodik kontrol et (arkaplan thread).

    Her N saniyede bir config.yaml ve .env dosyalarini kontrol eder,
    yeni MCP sunuculari eklenmis mi diye bakar. Yeni sunucu bulursa
    otomatik baglanir.

    Args:
        interval_sn: Kontrol araligi (saniye). Varsayilan: 120sn (2dk)

    Returns:
        True = baslatildi, False = zaten calisiyor
    """
    global _izleme_aktif, _izleme_thread
    if _izleme_aktif:
        return False

    _izleme_aktif = True
    _izleme_thread = threading.Thread(
        target=_izleme_dongusu,
        args=(interval_sn,),
        daemon=True,
        name="mcp-watcher",
    )
    _izleme_thread.start()
    logger.info("[MCP] Konfig izleme baslatildi (aralik: %ds)", interval_sn)
    return True


def mcp_kesif_izle_durdur() -> None:
    """Konfig izleme dongusunu durdur."""
    global _izleme_aktif
    _izleme_aktif = False
    logger.info("[MCP] Konfig izleme durduruldu")


# Module-level state variables
_izleme_aktif = False
_izleme_thread: Optional[threading.Thread] = None
_son_mcp_imzasi: Optional[str] = None


def _izle_baslat_wrapper(sn: int = 120) -> str:
    """Wrapper for lambda in motor_kaydet."""
    if mcp_kesif_izle_baslat(interval_sn=sn):
        return f"[MCP] Konfig izleme baslatildi (aralik: {sn}s)"
    return "[MCP] Konfig izleme zaten calisiyor"


def _izleme_dongusu(interval_sn: int) -> None:
    """Konfig dosyalarini periyodik kontrol eden dongu."""
    global _son_mcp_imzasi
    import hashlib

    while _izleme_aktif:
        try:
            # Config dosyalarinin hash'ini hesapla
            imzalar = []
            for yol in CONFIG_YOLLARI + ENV_YOLLARI:
                if yol.exists():
                    imzalar.append(f"{yol}:{yol.stat().st_mtime}:{yol.stat().st_size}")
            yeni_imza = hashlib.md5("|".join(imzalar).encode()).hexdigest()

            if _son_mcp_imzasi is not None and _son_mcp_imzasi != yeni_imza:
                # Degisiklik var - yeniden kesif yap
                logger.info("[MCP] Konfig degismis, yeniden kesif yapiliyor...")
                yeni = mcp_kesfet(geri_bildirim=True)
                if yeni > 0:
                    logger.info("[MCP] Runtime kesif: %d yeni sunucu bulundu", yeni)

            _son_mcp_imzasi = yeni_imza
        except Exception as e:
            logger.debug("[MCP] Izleme hatasi (onemsiz): %s", e)

        time.sleep(interval_sn)


def mcp_kesif_raporu() -> str:
    """İnsan-okunabilir keşif durum raporu."""
    durum = mcp_kesif_durumu()
    if durum["toplam"] == 0:
        return "[MCP Keşif] Hiçbir MCP sunucusu bulunamadı."

    satirlar = [
        "[MCP Keşif] Otomatik Keşfedilen Sunucular:",
        "=" * 55,
    ]
    for s in durum["sunucular"]:
                    simge = "🟢" if s["bagli"] else "🔴"
                    satirlar.append(
                        f"  {s['ad']} ({s['transport']}): {simge} "
                        f"{s['tool_sayisi']} tool — kaynak: {s['kaynak']}"
                    )
    satirlar.append(f"\nToplam: {durum['toplam']} sunucu")
    return "\n".join(satirlar)


# ═══════════════════════════════════════════════════════════════════════════
# Motor Tool Kaydı
# ═══════════════════════════════════════════════════════════════════════════

def motor_kaydet(motor) -> None:
    """MCP_DISCOVERY aracını Motor'a kaydet.

    Motor başlatılırken çağrılır.
    """
    if not hasattr(motor, "_plugin_arac_kaydet"):
        logger.warning("Motor'da _plugin_arac_kaydet metodu yok")
        return

    motor._plugin_arac_kaydet(
        "MCP_DISCOVERY",
        mcp_kesfet,
        "MCP sunucularını config.yaml ve .env'den otomatik keşfeder. "
        "Kullanım: MCP_DISCOVERY() — keşif yapar ve mcp_manager'a kaydeder.",
    )

    motor._plugin_arac_kaydet(
        "MCP_DISCOVERY_DURUM",
        mcp_kesif_raporu,
        "Keşfedilen MCP sunucularının durum raporunu döndürür. "
        "Kullanım: MCP_DISCOVERY_DURUM() — durum raporu.",
    )

    motor._plugin_arac_kaydet(
        "MCP_DISCOVERY_IZLE_BASLAT",
        lambda sn=120: _izle_baslat_wrapper(sn),
        "MCP konfig dosyalarini periyodik kontrol eder (arkaplan). "
        "Yeni MCP sunucusu eklenirse otomatik baglanir. "
        "Parametre: sn (kontrol araligi, varsayilan 120s). "
        "Kullanım: MCP_DISCOVERY_IZLE_BASLAT(sn=120)",
    )

    motor._plugin_arac_kaydet(
        "MCP_DISCOVERY_IZLE_DURDUR",
        mcp_kesif_izle_durdur,
        "MCP konfig izleme dongusunu durdurur. "
        "Kullanım: MCP_DISCOVERY_IZLE_DURDUR()",
    )


# ═══════════════════════════════════════════════════════════════════════════
# CLI Test
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("=== MCP Otomatik Keşif Testi ===\n")

    # config.yaml'dan oku
    cfg_sunucular = _config_oku()
    print(f"config.yaml'dan {len(cfg_sunucular)} sunucu:")
    for ad in cfg_sunucular:
        print(f"  - {ad}: {cfg_sunucular[ad].get('transport', '?')}")

    # .env'den oku
    env_sunucular_raw = _env_oku()
    print(f"\n.env'den {len(env_sunucular_raw)} sunucu:")
    for ad, ayar in env_sunucular_raw.items():
        print(f"  - {ad}: {ayar}")

    # Keşif yap
    yeni = mcp_kesfet()
    print(f"\n→ {yeni} yeni sunucu eklendi")

    # Durum
    print(f"\n{mcp_kesif_raporu()}")
