# -*- coding: utf-8 -*-
"""
profile_manager.py — ReYMeN Çoklu Profil Yöneticisi.

config.yaml'daki profiles: bölümünü okur, profil değiştirme ve listeleme
işlemlerini yönetir. Her profil farklı providers/modeller kullanabilir.

Kullanım:
    from profile_manager import ProfileManager
    pm = ProfileManager("config.yaml")
    pm.profil_listele()
    pm.profil_degistir("dev")
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# --- YAML yükleyici ---
try:
    import yaml
    _YAML_MEVCUT = True
except ImportError:
    _YAML_MEVCUT = False
    logger.warning("PyYAML kurulu degil. pip install pyyaml")


class ProfileManager:
    """Profil yöneticisi — config.yaml'daki profilleri okur ve yönetir."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = str(Path(__file__).parent.parent.parent / "config.yaml")

        self._config_yolu = Path(config_path)
        self._aktif_profil: str = "reyment"
        self._profiller: Dict[str, Dict[str, Any]] = {}
        self._yukle()

    def _yukle(self) -> None:
        """Profilleri config.yaml'dan yükle."""
        if not _YAML_MEVCUT:
            logger.error("PyYAML kurulu degil, profil yuklemesi yapilamadi")
            return

        if not self._config_yolu.exists():
            logger.warning(f"config.yaml bulunamadi: {self._config_yolu}")
            return

        try:
            with open(self._config_yolu, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"config.yaml okunamadi: {e}")
            return

        if not isinstance(data, dict):
            logger.warning("config.yaml gecersiz format")
            return

        profiller = data.get("profiles", {})
        if not profiller:
            logger.info("config.yaml'da profiles: bolumu bulunamadi, varsayilan profil")
            self._profiller = {
                "reyment": {
                    "aciklama": "Ana ReYMeN profili",
                    "default_provider": data.get("general", {}).get("default_provider", "deepseek"),
                    "default_model": data.get("general", {}).get("default_model", "deepseek-v4-flash"),
                }
            }
            return

        self._profiller = {}
        for ad, pcfg in profiller.items():
            if isinstance(pcfg, dict):
                self._profiller[ad] = pcfg
            else:
                self._profiller[ad] = {"aciklama": str(pcfg)}

        if "reyment" in self._profiller:
            self._aktif_profil = "reyment"
        elif self._profiller:
            self._aktif_profil = list(self._profiller.keys())[0]
        else:
            self._aktif_profil = "reyment"

        logger.info(f"{len(self._profiller)} profil yuklendi. Aktif: {self._aktif_profil}")
        self._profil_override_yukle()

    def _profil_override_yukle(self) -> None:
        """Profil-specific config dosyasini yukle (config.reymen.yaml, config.dev.yaml vb.)"""
        override_dosyasi = self._config_yolu.parent / f"config.{self._aktif_profil}.yaml"
        if not override_dosyasi.exists():
            return
        if not _YAML_MEVCUT:
            return
        try:
            with open(override_dosyasi, "r", encoding="utf-8") as f:
                override_data = yaml.safe_load(f)
            if isinstance(override_data, dict) and self._aktif_profil in self._profiller:
                for anahtar, deger in override_data.items():
                    if isinstance(deger, dict) and isinstance(
                        self._profiller[self._aktif_profil].get(anahtar), dict
                    ):
                        self._profiller[self._aktif_profil][anahtar].update(deger)
                    else:
                        self._profiller[self._aktif_profil][anahtar] = deger
                logger.info(f"Profil override yuklendi: {override_dosyasi.name}")
        except Exception as e:
            logger.warning(f"Profil override yuklenemedi ({override_dosyasi.name}): {e}")

    def profil_degistir(self, ad: str) -> str:
        """Aktif profili değiştir.

        Args:
            ad: Profil adi (reyment, dev, test, prod)

        Returns:
            str: Başarılı/başarısız mesajı
        """
        ad = ad.strip().lower()
        if ad not in self._profiller:
            mevcut = ", ".join(self._profiller.keys())
            return f"[Profil] HATA: '{ad}' profili bulunamadi. Mevcut profiller: {mevcut}"

        eski_profil = self._aktif_profil
        self._aktif_profil = ad
        self._profil_override_yukle()

        profil_bilgi = self._profiller[ad]
        aciklama = profil_bilgi.get("aciklama", "")
        provider = profil_bilgi.get("default_provider", "varsayilan")
        model = profil_bilgi.get("default_model", "varsayilan")

        logger.info(f"Profil degisti: {eski_profil} -> {ad}")
        return (
            f"[Profil] BASARILI: '{ad}' profil'ine gecildi.\n"
            f"  Aciklama: {aciklama}\n"
            f"  Varsayilan Saglayici: {provider}\n"
            f"  Varsayilan Model: {model}"
        )

    def profil_listele(self) -> str:
        """Tüm profilleri listele."""
        if not self._profiller:
            return "[Profil] UYARI: Hicbir profil tanimlanmamis."

        satirlar = ["[Profil] Mevcut Profiller:\n"]
        for ad, pcfg in self._profiller.items():
            isaret = "=> " if ad == self._aktif_profil else "   "
            aciklama = pcfg.get("aciklama", "")
            provider = pcfg.get("default_provider", "-")
            model = pcfg.get("default_model", "-")
            satirlar.append(f"{isaret}{ad}")
            if aciklama:
                satirlar.append(f"     Aciklama: {aciklama}")
            satirlar.append(f"     Saglayici: {provider}")
            satirlar.append(f"     Model: {model}")
            satirlar.append("")
        return "\n".join(satirlar).strip()

    def aktif_profil_al(self) -> str:
        return self._aktif_profil

    def aktif_profil_bilgisi(self) -> Dict[str, Any]:
        return self._profiller.get(self._aktif_profil, {})

    def profil_bilgisi(self, ad: str) -> Optional[Dict[str, Any]]:
        return self._profiller.get(ad.strip().lower())

    def profil_sayisi(self) -> int:
        return len(self._profiller)

    def tum_profiller(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._profiller)

    def profil_ekle(self, ad: str, aciklama: str = "",
                    default_provider: str = "",
                    default_model: str = "",
                    overrides: Optional[Dict[str, Any]] = None) -> str:
        ad = ad.strip().lower()
        if not ad:
            return "[Profil] HATA: Profil adi bos olamaz."
        self._profiller[ad] = {
            "aciklama": aciklama,
            "default_provider": default_provider,
            "default_model": default_model,
        }
        if overrides:
            self._profiller[ad].update(overrides)
        logger.info(f"Profil eklendi: {ad}")
        return f"[Profil] BASARILI: '{ad}' profili eklendi."

    def profil_sil(self, ad: str) -> str:
        ad = ad.strip().lower()
        if ad not in self._profiller:
            return f"[Profil] HATA: '{ad}' profili bulunamadi."
        if len(self._profiller) <= 1:
            return "[Profil] HATA: Son profil silinemez."
        if ad == self._aktif_profil:
            yeni_profil = [p for p in self._profiller if p != ad][0]
            self._aktif_profil = yeni_profil
        del self._profiller[ad]
        logger.info(f"Profil silindi: {ad}")
        return f"[Profil] BASARILI: '{ad}' profili silindi."

    def config_override_uygula(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Aktif profilin override'larini verilen config dict'ine uygula."""
        profil = self.aktif_profil_bilgisi()
        if not profil:
            return config

        yeni_config = dict(config)
        if profil.get("default_provider"):
            yeni_config["default_provider"] = profil["default_provider"]
        if profil.get("default_model"):
            yeni_config["default_model"] = profil["default_model"]

        profil_providers = profil.get("providers", {})
        if profil_providers and "providers" in yeni_config:
            for pname, pcfg in profil_providers.items():
                if pname in yeni_config["providers"]:
                    if isinstance(pcfg, dict):
                        yeni_config["providers"][pname].update(pcfg)
                else:
                    yeni_config["providers"][pname] = pcfg

        for anahtar in ("max_turns", "memory_char_limit", "secure_binding",
                        "telegram", "voice", "web", "logging"):
            if anahtar in profil:
                yeni_config[anahtar] = profil[anahtar]
        return yeni_config


# Module-level singleton
_profil_yoneticisi: Optional[ProfileManager] = None


def get_profile_manager(config_path: Optional[str] = None) -> ProfileManager:
    global _profil_yoneticisi
    if _profil_yoneticisi is None:
        _profil_yoneticisi = ProfileManager(config_path)
    return _profil_yoneticisi


def profil_degistir(ad: str) -> str:
    pm = get_profile_manager()
    return pm.profil_degistir(ad)


def profil_listele() -> str:
    pm = get_profile_manager()
    return pm.profil_listele()


# Hizli test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    pm = ProfileManager()
    print(pm.profil_listele())
    print()
    print(pm.profil_degistir("dev"))
    print()
    print(pm.profil_listele())
