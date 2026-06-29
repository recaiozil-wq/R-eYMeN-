# -*- coding: utf-8 -*-
"""
config_manager.py — ReYMeN YAML Config / Profile Manager.

Hard-coded yollari (.ReYMeN/, ~/AppData/Local/hermes/) ortadan kaldirir.
Tum yollar config.yaml + .env override + varsayilan degerler uzerinden cekilir.

Profil sistemi: ~/.hermes/profiles/<ad>/config.yaml oku
Environment variable override: REYMEN_<ANAHTAR> veya config'deki env_key ile

Motor araclari:
  - CONFIG_GOSTER:  Config durumu goster
  - CONFIG_AYARLA:  Config anahtari degistir (runtime + dosya)

Kullanim:
    cfg = Config()
    model = cfg.get("general.default_model", "deepseek-chat")
    log_yolu = cfg.get_path("logging.file")
    api_key = cfg.get_env("DEEPSEEK_API_KEY")
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

# ── Sabitler ────────────────────────────────────────────────
_PROJE_KOKU = Path(__file__).resolve().parent.parent.parent  # reymen/core/ -> reymen/ -> projekt
_VARSAYILAN_CONFIG_YOLU = _PROJE_KOKU / "config.yaml"
_HERMES_PROFIL_DIZINI = Path.home() / ".hermes" / "profiles"

# Varsayilan degerler (hicbir config dosyasi bulunamazsa kullanilir)
_VARSAYILAN_DEGERLER: dict[str, Any] = {
    "general.agent_name": "ReYMeN",
    "general.default_model": "deepseek-v4-flash",
    "general.default_provider": "deepseek",
    "general.max_turns": 15,
    "general.secure_binding": True,
    "logging.level": "INFO",
    "logging.file": ".ReYMeN/logs/reymen.log",
    "logging.max_size_mb": 10,
    "logging.backup_count": 5,
    "skills.dir": ".ReYMeN/skills",
    "checkpoint.dir": ".ReYMeN/checkpoints",
    "checkpoint.enabled": True,
    "checkpoint.max_restore_attempts": 3,
    "telegram.default_chat_id": "",
    "state_machine.enabled": True,
    "service_bridge.enabled": True,
    "auto_recovery.enabled": True,
    "memory.max_records": 2000,
    "web.backend": "auto",
    "approvals.mode": "smart",
    "spotify.enabled": True,
}

# Environment variable key mapping (config anahtari -> env var)
_ENV_MAP: dict[str, str] = {
    "general.default_model": "DEFAULT_MODEL",
    "general.default_provider": "DEFAULT_PROVIDER",
}


# ═══════════════════════════════════════════════════════════════
# Config — Merkezi yapilandirma yoneticisi
# ═══════════════════════════════════════════════════════════════

@dataclass
class ProfilBilgisi:
    """Aktif profil bilgisi."""
    ad: str = "default"
    kaynak: str = "config.yaml"
    yuklendi: bool = False


class Config:
    """YAML + .env + varsayilan degerler ile merkezi config.

    Okuma sirasi (sonraki oncekinden once gelir):
      1. Varsayilan degerler (_VARSAYILAN_DEGERLER)
      2. Profil config dosyasi (~/.hermes/profiles/<ad>/config.yaml)
      3. Ana config dosyasi (proje config.yaml)
      4. Environment variable'lar (REYMEN_<ANAHTAR> veya _ENV_MAP)

    Kullanim:
        cfg = Config()
        cfg.get("general.default_model")       # -> "deepseek-v4-flash"
        cfg.get_path("logging.file")           # -> Path(...)
        cfg.get_env("DEEPSEEK_API_KEY")        # -> os.environ'dan
        cfg.get("providers.deepseek.base_url") # -> "https://api.deepseek.com"
    """

    def __init__(
        self,
        config_yolu: Optional[Path] = None,
        profil: Optional[str] = None,
    ):
        self._config_yolu = config_yolu or _VARSAYILAN_CONFIG_YOLU
        self._data: dict[str, Any] = {}
        self._profil = ProfilBilgisi()
        self._dirty: bool = False

        self._yukle(profil)

    # ── Yukleme ─────────────────────────────────────────────────

    def _yukle(self, profil: Optional[str] = None) -> None:
        """Config'i katmanli olarak yukler."""
        self._data = dict(_VARSAYILAN_DEGERLER)  # 1. varsayilanlar

        # 2. Profil config (varsa)
        if profil:
            self._profil_yukle(profil)

        # 3. Ana config dosyasi
        if self._config_yolu and self._config_yolu.exists():
            try:
                with open(self._config_yolu, "r", encoding="utf-8") as f:
                    dosya_data = yaml.safe_load(f) or {}
                self._dict_merge(self._data, dosya_data, prefix="")
                self._profil.kaynak = str(self._config_yolu)
                self._profil.yuklendi = True
                logger.info("[Config] Ana config yuklendi: %s", self._config_yolu)
            except Exception as e:
                logger.warning("[Config] Config dosyasi okunamadi: %s", e)

        # 4. Environment variable override (REYMEN_<KEY>)
        self._env_override()

    def _profil_yukle(self, profil_adi: str) -> None:
        """Profil config dosyasini yukler."""
        profil_yolu = _HERMES_PROFIL_DIZINI / profil_adi / "config.yaml"
        if profil_yolu.exists():
            try:
                with open(profil_yolu, "r", encoding="utf-8") as f:
                    profil_data = yaml.safe_load(f) or {}
                self._dict_merge(self._data, profil_data, prefix="")
                self._profil = ProfilBilgisi(
                    ad=profil_adi,
                    kaynak=str(profil_yolu),
                    yuklendi=True,
                )
                logger.info("[Config] Profil yuklendi: %s", profil_yolu)
            except Exception as e:
                logger.warning("[Config] Profil okunamadi: %s - %s", profil_yolu, e)

    def _env_override(self) -> None:
        """Environment variable'lari uygular.

        Oncelik sirasi:
          1. REYMEN_<ANAHTAR> (ornek: REYMEN_GENERAL_DEFAULT_MODEL)
          2. _ENV_MAP uzerinden (ornek: DEFAULT_MODEL -> general.default_model)
        """
        # REYMEN_ prefix
        reymen_prefix = "REYMEN_"
        for env_key, env_val in os.environ.items():
            if env_key.startswith(reymen_prefix):
                config_key = env_key[len(reymen_prefix):].lower().replace("_", ".")
                self._dict_set(self._data, config_key, env_val)

        # _ENV_MAP
        for config_key, env_key in _ENV_MAP.items():
            env_val = os.environ.get(env_key)
            if env_val is not None:
                self._dict_set(self._data, config_key, env_val)

    # ── Okuma ───────────────────────────────────────────────────

    def get(self, anahtar: str, varsayilan: Any = None) -> Any:
        """Config'den deger okur.

        Nokta notasyonu destegi: "general.default_model"
        """
        keys = anahtar.split(".")
        val = self._data
        try:
            for k in keys:
                val = val[k]
            return val
        except (KeyError, TypeError):
            return varsayilan

    def get_path(self, anahtar: str) -> Optional[Path]:
        """Config'den yol okur ve Path nesnesine cevirir.

        Eger deger relative path ise proje kokune gore cozer.
        """
        val = self.get(anahtar)
        if val is None:
            return None
        val_str = str(val)
        p = Path(val_str)
        if not p.is_absolute():
            p = _PROJE_KOKU / p
        return p.resolve()

    def get_env(self, anahtar: str) -> str:
        """Environment variable okur.

        Once dogrudan os.environ'a bakar, sonra config'deki
        api_key_env degerini kullanarak provider anahtarlarini
        cozer.
        """
        # Dogrudan env
        val = os.environ.get(anahtar)
        if val is not None:
            return val

        # Config icinde api_key_env olarak gecen bir field mi?
        # providers.X.api_key_env -> ilgili env var degerini don
        for provider_key, provider_val in self._data.get("providers", {}).items():
            if isinstance(provider_val, dict):
                if provider_val.get("api_key_env") == anahtar:
                    return os.environ.get(anahtar, "")

        return ""

    def get_provider(self, ad: str) -> Optional[dict]:
        """Provider yapilandirmasini doner.

        Args:
            ad: Provider adi (ornek: "deepseek", "openrouter")

        Returns:
            {base_url, api_key_env, api_key, ...} veya None
        """
        return self.get(f"providers.{ad}")

    def get_provider_chain(self) -> list[str]:
        """Varsayilan provider zincirini doner.

        Config'deki provider priority sirasina gore.
        Eger config'de priority yoksa, _VARSAYILAN_PROVIDER_SIRASI kullanilir.
        """
        providers = self.get("providers", {})
        if not isinstance(providers, dict):
            return _VARSAYILAN_PROVIDER_SIRASI

        sirali = sorted(
            [(ad, info.get("priority", 99)) for ad, info in providers.items()
             if isinstance(info, dict)],
            key=lambda x: x[1],
        )
        return [ad for ad, _ in sirali] if sirali else _VARSAYILAN_PROVIDER_SIRASI

    # ── Yazma ───────────────────────────────────────────────────

    def set(self, anahtar: str, deger: Any) -> bool:
        """Config degerini runtime'da degistirir.

        Not: Degisiklik sadece runtime icindir. Config dosyasina
        kaydetmek icin kaydet() cagrilmalidir.
        """
        self._dict_set(self._data, anahtar, deger)
        self._dirty = True
        return True

    def set_and_save(self, anahtar: str, deger: Any) -> bool:
        """Config degerini degistirir VE dosyaya kaydeder."""
        self.set(anahtar, deger)
        return self.kaydet()

    def kaydet(self) -> bool:
        """Config'i dosyaya kaydeder."""
        try:
            # Mevcut dosyayi oku, merge et, yaz
            mevcut = {}
            if self._config_yolu and self._config_yolu.exists():
                with open(self._config_yolu, "r", encoding="utf-8") as f:
                    mevcut = yaml.safe_load(f) or {}

            # Guncel data ile merge et
            self._dict_merge(mevcut, self._data, prefix="")

            with open(self._config_yolu, "w", encoding="utf-8") as f:
                yaml.dump(mevcut, f, allow_unicode=True, default_flow_style=False,
                         sort_keys=False, indent=2)

            self._dirty = False
            logger.info("[Config] Config kaydedildi: %s", self._config_yolu)
            return True
        except Exception as e:
            logger.error("[Config] Config kaydedilemedi: %s", e)
            return False

    # ── Durum ───────────────────────────────────────────────────

    def durum_raporu(self) -> dict:
        """Config durum raporu."""
        provider_bilgisi = []
        providers = self.get("providers", {})
        if isinstance(providers, dict):
            for ad, info in providers.items():
                if isinstance(info, dict):
                    api_key_env = info.get("api_key_env", "")
                    api_key_var = bool(os.environ.get(api_key_env)) if api_key_env else False
                    provider_bilgisi.append({
                        "ad": ad,
                        "base_url": info.get("base_url", ""),
                        "api_key_env": api_key_env,
                        "api_key_var": api_key_var,
                        "model": info.get("model", ""),
                    })

        return {
            "profil": {
                "ad": self._profil.ad,
                "kaynak": self._profil.kaynak,
                "yuklendi": self._profil.yuklendi,
            },
            "config_dosyasi": str(self._config_yolu) if self._config_yolu else "",
            "varsayilan_model": self.get("general.default_model", ""),
            "varsayilan_provider": self.get("general.default_provider", ""),
            "provider_sayisi": len(provider_bilgisi),
            "providerlar": provider_bilgisi,
            "anahtar_sayisi": sum(self._dict_anahtar_say(self._data)),
            "dirty": self._dirty,
        }

    # ── Yardimci metotlar ──────────────────────────────────────

    @staticmethod
    def _dict_merge(hedef: dict, kaynak: dict, prefix: str = "") -> None:
        """Iki sozlugu derinlemesine birlestirir (kaynak hedefe)."""
        for key, val in kaynak.items():
            if prefix:
                full_key = f"{prefix}.{key}"
            else:
                full_key = key

            if isinstance(val, dict) and key in hedef and isinstance(hedef[key], dict):
                Config._dict_merge(hedef[key], val, full_key)
            else:
                hedef[key] = val

    @staticmethod
    def _dict_set(d: dict, anahtar: str, deger: Any) -> None:
        """Nokta notasyonlu anahtari sozluge yazar."""
        keys = anahtar.split(".")
        for k in keys[:-1]:
            if k not in d or not isinstance(d[k], dict):
                d[k] = {}
            d = d[k]
        d[keys[-1]] = deger

    @staticmethod
    def _dict_anahtar_say(d: dict) -> list:
        """Sozlukteki yaprak anahtar sayisini verir."""
        count = []
        for val in d.values():
            if isinstance(val, dict):
                count.extend(Config._dict_anahtar_say(val))
            else:
                count.append(1)
        return count

    def __repr__(self) -> str:
        return (
            f"<Config profil={self._profil.ad!r} "
            f"kaynak={self._profil.kaynak!r} "
            f"anahtar_sayisi={sum(self._dict_anahtar_say(self._data))}>"
        )


# ── Varsayilan provider sirasi (config'de priority yoksa) ────
_VARSAYILAN_PROVIDER_SIRASI = [
    "deepseek", "openrouter", "xai", "groq", "lmstudio",
    "openai", "anthropic", "gemini",
]


# ═══════════════════════════════════════════════════════════════
# Varsayilan Config singleton
# ═══════════════════════════════════════════════════════════════

_varsayilan_config: Optional[Config] = None


def varsayilan_config() -> Config:
    """Varsayilan Config singleton."""
    global _varsayilan_config
    if _varsayilan_config is None:
        _varsayilan_config = Config()
    return _varsayilan_config


def config_yeniden_yukle(profil: Optional[str] = None) -> Config:
    """Config'i yeniden yukler (varsayilan singleton'i gunceller)."""
    global _varsayilan_config
    _varsayilan_config = Config(profil=profil)
    return _varsayilan_config


# ═══════════════════════════════════════════════════════════════
# Motor tool kayit
# ═══════════════════════════════════════════════════════════════

def motor_kaydet(motor: Any) -> None:
    """Config araçlarını Motor'a kaydeder."""
    import json as _json

    def _config_goster() -> str:
        """CONFIG_GOSTER: Config durum raporu.

        Donus:
          JSON: {profil, config_dosyasi, varsayilan_model,
                 providerlar, anahtar_sayisi, ...}
        """
        cfg = varsayilan_config()
        return _json.dumps(cfg.durum_raporu(), ensure_ascii=False, indent=2)

    def _config_ayarla(anahtar: str = "", deger: str = "") -> str:
        """CONFIG_AYARLA: Config anahtari degistir ve dosyaya kaydet.

        Parametreler:
          anahtar: Config anahtari (ornek: "general.default_model")
          deger:   Yeni deger

        Donus:
          Basari mesaji veya hata
        """
        if not anahtar:
            return "❌ Anahtar gerekli. Kullanim: CONFIG_AYARLA(anahtar='general.default_model', deger='deepseek-chat')"
        cfg = varsayilan_config()
        basarili = cfg.set_and_save(anahtar, deger)
        if basarili:
            return f"✅ {anahtar} -> {deger}"
        return f"❌ {anahtar} degistirilemedi"

    motor._plugin_arac_kaydet(
        "CONFIG_GOSTER",
        _config_goster,
        "Config durum raporu: profil, providerlar, anahtar sayisi",
    )
    motor._plugin_arac_kaydet(
        "CONFIG_AYARLA",
        _config_ayarla,
        "Config anahtari degistir ve kaydet: anahtar, deger",
    )
    logger.info("[ConfigManager] Motor araclari kaydedildi: CONFIG_GOSTER, CONFIG_AYARLA")
