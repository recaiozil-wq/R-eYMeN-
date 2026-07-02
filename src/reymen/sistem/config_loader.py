# -*- coding: utf-8 -*-
"""
config_loader.py — ReYMeN Yapılandırma Yükleyici.

config.yaml dosyasını okur, main.py'deki CONFIG dict ile birleştirir.
Environment variable'lar her zaman önceliklidir.

Kullanım:
    from config_loader import load_config, config_to_dict
    cfg = load_config("config.yaml")
    CONFIG = config_to_dict(cfg)  # main.py CONFIG formatına dönüştür
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# --- YAML yükleyici (try/except ile) ---
try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False
    logger.warning("PyYAML kurulu degil. JSON fallback kullanilacak. pip install pyyaml")


def load_yaml_safe(path: Path) -> Optional[Dict[str, Any]]:
    """YAML dosyasını güvenli şekilde yükle. PyYAML yoksa None."""
    if not _YAML_AVAILABLE:
        return None
    if not path.exists():
        logger.warning(f"config.yaml bulunamadi: {path}")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            logger.warning(f"config.yaml gecersiz format: {type(data)}")
            return None
        return data
    except yaml.YAMLError as e:
        logger.error(f"config.yaml YAML hatasi: {e}")
        return None
    except Exception as e:
        logger.error(f"config.yaml okunamadi: {e}")
        return None


def _env_or(value: Any, env_key: str, default: Any = None) -> Any:
    """Environment variable varsa onu döndür, yoksa value."""
    env_val = os.environ.get(env_key)
    if env_val is not None and env_val.strip() and not env_val.startswith("***"):
        return env_val.strip()
    return value if value is not None else default


def _resolve_provider_api_key(provider_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Sağlayıcı yapılandırmasında env key varsa çözümle."""
    cfg = dict(provider_cfg)
    env_key = cfg.pop("api_key_env", None)
    if env_key:
        cfg["api_key"] = _env_or(cfg.get("api_key", ""), env_key, "")
    return cfg


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """config.yaml + env override ile birleşik yapılandırma döndür.

    Args:
        config_path: config.yaml yolu. None = proje kökü/config.yaml

    Returns:
        Birleşik yapılandırma dict'i (env override uygulanmış)
    """
    if config_path is None:
        # Proje kökünü bul (config_loader.py'nin bulunduğu dizin)
        config_path = str(Path(__file__).parent / "config.yaml")
    
    yaml_path = Path(config_path)
    yaml_cfg = load_yaml_safe(yaml_path) or {}

    # ── Genel ayarlar ──────────────────────────────────────────────
    general = yaml_cfg.get("general", {})
    result: Dict[str, Any] = {
        "default_model": _env_or(
            general.get("default_model"),
            "REYMEN_DEFAULT_MODEL",
            "cognitivecomputations.dolphin3.0-llama3.1-8b",
        ),
        "default_provider": _env_or(
            general.get("default_provider"),
            "REYMEN_DEFAULT_PROVIDER",
            "lmstudio",
        ),
        "max_turns": int(_env_or(
            str(general.get("max_turns", 15)),
            "REYMEN_MAX_TURNS",
            "15",
        )),
        "secure_binding": general.get("secure_binding", True),
        "memory_char_limit": int(_env_or(
            str(general.get("memory_char_limit", 50000)),
            "REYMEN_MEMORY_CHAR_LIMIT",
            "50000",
        )),
    }

    # ── Sağlayıcılar ───────────────────────────────────────────────
    providers = {}
    for name, pcfg in yaml_cfg.get("providers", {}).items():
        resolved = _resolve_provider_api_key(pcfg)
        # base_url'de env override
        env_url_key = f"{name.upper()}_BASE_URL".replace("-", "_")
        if env_url_key in os.environ and os.environ[env_url_key].strip():
            resolved["base_url"] = os.environ[env_url_key].strip()
        providers[name] = resolved
    result["providers"] = providers

    # ── Fallback model ─────────────────────────────────────────────
    fallback = yaml_cfg.get("fallback_model", {})
    if fallback:
        api_key = ""
        if fallback.get("api_key_env"):
            api_key = os.environ.get(fallback["api_key_env"], "")
        if api_key and not api_key.startswith("***"):
            result["fallback_model"] = {
                "provider": fallback.get("provider", "deepseek"),
                "model": fallback.get("model", "deepseek-chat"),
                "base_url": fallback.get("base_url", "https://api.deepseek.com"),
                "api_key": api_key,
            }
        else:
            result["fallback_model"] = None
    else:
        result["fallback_model"] = None

    # ── Yardımcı modeller ──────────────────────────────────────────
    aux = yaml_cfg.get("auxiliary", {})
    result["auxiliary"] = {}
    for modality, mcfg in aux.items():
        resolved = dict(mcfg)
        if "api_key_env" in resolved:
            resolved.pop("api_key_env")
        result["auxiliary"][modality] = resolved

    # ── Telegram ───────────────────────────────────────────────────
    tg = yaml_cfg.get("telegram", {})
    result["telegram"] = {
        "token": _env_or("", tg.get("token_env", "TELEGRAM_BOT_TOKEN")),
        "chat_id": _env_or(
            tg.get("default_chat_id", "6328823909"),
            tg.get("chat_id_env", "TELEGRAM_CHAT_ID"),
        ),
    }

    # ── State machine ──────────────────────────────────────────────
    sm = yaml_cfg.get("state_machine", {})
    result["state_machine"] = {
        "enabled": sm.get("enabled", True),
        "heartbeat_interval_sec": sm.get("heartbeat_interval_sec", 30),
        "stale_timeout_sec": sm.get("stale_timeout_sec", 120),
    }

    # ── Service bridge ─────────────────────────────────────────────
    sb = yaml_cfg.get("service_bridge", {})
    result["service_bridge"] = {
        "enabled": sb.get("enabled", True),
        "max_queue_size": sb.get("max_queue_size", 1000),
    }

    # ── Auto recovery ──────────────────────────────────────────────
    ar = yaml_cfg.get("auto_recovery", {})
    result["auto_recovery"] = {
        "enabled": ar.get("enabled", True),
        "check_interval_sec": ar.get("check_interval_sec", 15),
        "max_restart_attempts": ar.get("max_restart_attempts", 3),
        "cooldown_sec": ar.get("cooldown_sec", 60),
        "max_concurrent_failures": ar.get("max_concurrent_failures", 5),
    }
    result["auto_recovery_components"] = ar.get("components", {})

    # Skills
    skills_cfg = yaml_cfg.get("skills", {})
    result["skills_dir"] = skills_cfg.get("dir", ".ReYMeN/skills")

    # Logging
    log_cfg = yaml_cfg.get("logging", {})
    result["logging"] = log_cfg

    # ── Profil yukleme (multi-profile sistemi) ─────────────────────
    try:
        from reymen.sistem.profile_manager import get_profile_manager
        pm = get_profile_manager(str(yaml_path))
        aktif_profil = pm.aktif_profil_al()
        profil_bilgi = pm.aktif_profil_bilgisi()
        result["active_profile"] = aktif_profil

        # Profil override'larini uygula
        if profil_bilgi:
            if profil_bilgi.get("default_provider"):
                result["default_provider"] = profil_bilgi["default_provider"]
            if profil_bilgi.get("default_model"):
                result["default_model"] = profil_bilgi["default_model"]
            if profil_bilgi.get("max_turns"):
                result["max_turns"] = int(profil_bilgi["max_turns"])

            # Profil-specific provider override'lari
            profil_providers = profil_bilgi.get("providers", {})
            if profil_providers:
                for pname, pcfg in profil_providers.items():
                    if pname in result.get("providers", {}):
                        if isinstance(pcfg, dict):
                            result["providers"][pname].update(pcfg)
                    else:
                        result.setdefault("providers", {})[pname] = pcfg

        logger.info(f"Aktif profil: {aktif_profil}")
    except ImportError:
        result["active_profile"] = "reyment"
        logger.debug("profile_manager modulu bulunamadi, varsayilan profil kullaniliyor")
    except Exception as e:
        result["active_profile"] = "reyment"
        logger.warning(f"Profil yukleme hatasi: {e}")

    return result


def merge_with_existing(yaml_config: Dict[str, Any],
                        existing_config: Dict[str, Any]) -> Dict[str, Any]:
    """YAML config'i mevcut CONFIG dict ile birleştir.
    
    Mevcut dict'te olup YAML'da olmayan alanlar korunur.
    YAML değerleri sadece mevcut dict boşsa veya override edilecekse yazılır.
    """
    merged = dict(existing_config)

    # Genel
    for key in ("default_model", "default_provider", "secure_binding", "memory_char_limit",
                "skills_dir"):
        if key in yaml_config:
            merged[key] = yaml_config[key]

    # providers — yaml'daki provider'ları ekle/override et
    if "providers" in merged and "providers" in yaml_config:
        for pname, pcfg in yaml_config["providers"].items():
            if pname not in merged["providers"]:
                merged["providers"][pname] = pcfg
            else:
                # Sadece base_url ve api_key override et
                if pcfg.get("base_url"):
                    merged["providers"][pname]["base_url"] = pcfg["base_url"]
                if pcfg.get("api_key"):
                    merged["providers"][pname]["api_key"] = pcfg["api_key"]

    # Fallback
    if "fallback_model" in yaml_config:
        if yaml_config["fallback_model"] is None:
            merged.pop("fallback_model", None)
        else:
            merged["fallback_model"] = yaml_config["fallback_model"]

    # Telegram
    if "telegram" in yaml_config:
        if "telegram" not in merged:
            merged["telegram"] = yaml_config["telegram"]
        else:
            tg = merged["telegram"]
            for key in ("token", "chat_id"):
                if not tg.get(key):
                    tg[key] = yaml_config["telegram"].get(key, "")

    # Yeni config anahtarlari (main.py CONFIG'inde olmayanlar)
    for key in ("state_machine", "service_bridge", "auto_recovery",
                "auto_recovery_components", "logging"):
        if key in yaml_config:
            merged[key] = yaml_config[key]

    return merged


# ── Hızlı test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cfg = load_config()
    print("=== config.yaml yuklendi ===")
    print(f"Default model: {cfg.get('default_model')}")
    print(f"Default provider: {cfg.get('default_provider')}")
    print(f"Provider sayisi: {len(cfg.get('providers', {}))}")
    print(f"State machine: {cfg.get('state_machine', {})}")
    print(f"Auto recovery: {cfg.get('auto_recovery', {})}")
    print(f"Service bridge: {cfg.get('service_bridge', {})}")
    print("Tum testler GECTI")


def config_guncelle(anahtar: str, deger: str) -> str:
    """config.yaml'da bir anahtari guncelle. Basit metin degistirme."""
    import re
    yaml_path = Path(__file__).parent / "config.yaml"
    if not yaml_path.exists():
        return f"HATA: config.yaml bulunamadi: {yaml_path}"
    
    icerik = yaml_path.read_text(encoding="utf-8")
    
    if anahtar in ("model", "provider"):
        # model: xxx veya provider: xxx satirini bul (basta bosluk olabilir)
        yeni, sayi = re.subn(
            rf"^(\s*){anahtar}:\s*.+$",
            rf"\g<1>{anahtar}: {deger}",
            icerik,
            count=1,
            flags=re.MULTILINE
        )
        if sayi == 0:
            # Bulunamadiysa en basa ekle
            yeni = f"{anahtar}: {deger}\n" + icerik
        yaml_path.write_text(yeni, encoding="utf-8")
        return f"config.yaml -> {anahtar}: {deger}"
    
    return f"Bilinmeyen anahtar: {anahtar} (model/provider desteklenir)"
