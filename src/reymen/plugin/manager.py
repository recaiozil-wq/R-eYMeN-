# -*- coding: utf-8 -*-
"""reymen.plugin.manager — PluginManager: plugin yükleme/kaldırma/hook dağıtma.

Kullanım:
    from reymen.plugin.manager import PluginManager

    pm = PluginManager()
    pm.config_yukle("config.yaml")          # plugins ayarlarını oku
    pm.tumunu_yukle()                       # plugins/ dizinindeki tüm .py'leri yükle
    pm.hook_cagir("on_session_start", session_id="...", user_id="...")
    pm.hook_cagir("on_message", message="merhaba", context={})
    pm.tumunu_kaldir()                      # kapatırken
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import yaml

from src.reymen.plugin import PluginBase

logger = logging.getLogger(__name__)


class PluginManager:
    """Plugin yöneticisi — yükleme, kaldırma, hook dağıtma.

    Özellikler:
        _pluginler:   {ad: PluginBase instance}
        _aktif:       Plugin sistemi aktif mi?
        _dizin:       Plugin dizini yolu (Path)
        _oto_yukle:   Başlangıçta otomatik yükleme
    """

    def __init__(self) -> None:
        self._pluginler: Dict[str, PluginBase] = {}
        self._aktif: bool = False
        self._dizin: Optional[Path] = None
        self._oto_yukle: bool = True
        self._aktif_liste: list = []
        self._context: Dict[str, dict] = {}  # plugin adı → context dict

    # ── Config ─────────────────────────────────────────────────────────

    def config_yukle(self, config_yolu: str = "config.yaml") -> None:
        """config.yaml'den plugins ayarlarını oku.

        Beklenen yapı:
            plugins:
              enabled: true
              directory: reymen/plugins
              auto_load: true
        """
        try:
            cfg_path = Path(config_yolu)
            if not cfg_path.exists():
                logger.info("[Plugin] config.yaml bulunamadi: %s", config_yolu)
                return

            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}

            plugin_cfg = cfg.get("plugins", {})
            if not isinstance(plugin_cfg, dict):
                plugin_cfg = {}

            self._aktif = bool(plugin_cfg.get("enabled", False))
            dizin_str = plugin_cfg.get("directory", "reymen/plugins")
            self._dizin = Path(dizin_str)
            self._oto_yukle = bool(plugin_cfg.get("auto_load", True))

            logger.info(
                "[Plugin] Config: aktif=%s, dizin=%s, oto_yukle=%s",
                self._aktif, self._dizin, self._oto_yukle,
            )

            # Aktif plugin listesini de oku (opsiyonel)
            self._aktif_liste: list = plugin_cfg.get("list", [])

        except Exception as e:
            logger.warning("[Plugin] Config yukleme hatasi: %s", e)
            self._aktif = False

    # ── Yükleme / Kaldırma ─────────────────────────────────────────────

    def plugin_yukle(self, ad: str, path: str) -> Optional[PluginBase]:
        """Tek bir plugin dosyasını yükle.

        Args:
            ad:   Plugin adı (ör. "ornek_plugin").
            path: .py dosyasının tam yolu.

        Returns:
            PluginBase instance veya hata durumunda None.
        """
        if not self._aktif:
            logger.debug("[Plugin] Plugin sistemi aktif degil, '%s' yuklenmedi", ad)
            return None

        if ad in self._pluginler:
            logger.debug("[Plugin] '%s' zaten yuklu, atlanıyor", ad)
            return self._pluginler[ad]

        try:
            spec = importlib.util.spec_from_file_location(ad, path)
            if spec is None or spec.loader is None:
                logger.warning("[Plugin] '%s' icin spec alinamadi: %s", ad, path)
                return None

            mod = importlib.util.module_from_spec(spec)
            # Modülü sys.modules'e ekle (tekrar yüklenmesin)
            sys.modules[ad] = mod
            spec.loader.exec_module(mod)

            # PluginBase alt sınıflarını bul
            instance = None
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, PluginBase)
                    and attr is not PluginBase
                ):
                    instance = attr()
                    break

            if instance is None:
                logger.warning(
                    "[Plugin] '%s' icinde PluginBase alt sinifi bulunamadi", ad
                )
                # sys.modules'ten temizle
                sys.modules.pop(ad, None)
                return None

            # on_load tetikle
            try:
                instance.on_load()
            except Exception as _e:
                logger.warning(
                    "[Plugin] '%s'.on_load() hatasi: %s", ad, _e
                )

            self._pluginler[ad] = instance
            self._context[ad] = {}
            logger.info("[Plugin] '%s' (%s) yuklendi", ad, instance.version)
            return instance

        except Exception as e:
            logger.error(
                "[Plugin] '%s' yukleme hatasi: %s\n%s",
                ad, e, traceback.format_exc(),
            )
            sys.modules.pop(ad, None)
            return None

    def plugin_kaldir(self, ad: str) -> None:
        """Tek bir plugin'i kaldır."""
        plugin = self._pluginler.pop(ad, None)
        self._context.pop(ad, None)
        if plugin is not None:
            try:
                plugin.on_unload()
            except Exception as _e:
                logger.warning("[Plugin] '%s'.on_unload() hatasi: %s", ad, _e)
            logger.info("[Plugin] '%s' kaldirildi", ad)

    def tumunu_yukle(self) -> int:
        """plugins/ dizinindeki tüm .py dosyalarını tara ve yükle.

        Returns:
            Başarıyla yüklenen plugin sayısı.
        """
        if not self._aktif:
            logger.info("[Plugin] Plugin sistemi aktif degil, yukleme yapilmadi")
            return 0

        if self._dizin is None:
            logger.warning("[Plugin] Plugin dizini belirtilmemis")
            return 0

        dizin = self._dizin
        if not dizin.is_absolute():
            # Proje köküne göre çöz
            for parent in [Path.cwd(), Path(__file__).resolve().parent.parent.parent]:
                deneme = parent / dizin
                if deneme.exists():
                    dizin = deneme
                    break

        if not dizin.exists():
            logger.warning("[Plugin] Plugin dizini bulunamadi: %s", dizin)
            return 0

        # __init__.py ve non-plugin dosyalarını atla
        yuklenen = 0
        for entry in sorted(dizin.iterdir()):
            if not entry.is_file() or not entry.suffix == ".py":
                continue
            if entry.name == "__init__.py":
                continue

            ad = entry.stem
            # Eğer config'de aktif liste varsa, sadece o listedekileri yükle
            if hasattr(self, "_aktif_liste") and self._aktif_liste:
                if ad not in self._aktif_liste:
                    logger.debug("[Plugin] '%s' aktif listede yok, atlandi", ad)
                    continue

            p = self.plugin_yukle(ad, str(entry))
            if p is not None:
                yuklenen += 1

        logger.info("[Plugin] Toplam %d plugin yuklendi", yuklenen)
        return yuklenen

    def tumunu_kaldir(self) -> None:
        """Tüm plugin'leri kaldır."""
        for ad in list(self._pluginler.keys()):
            self.plugin_kaldir(ad)

    # ── Hook Dağıtma ───────────────────────────────────────────────────

    def get_hook(self, hook_name: str) -> List[Callable]:
        """Belirtilen hook adını implemente eden tüm plugin metodlarını döndür.

        Args:
            hook_name: Metod adı (örn. "pre_llm_call").

        Returns:
            Çağrılabilir metodların listesi.
        """
        callables = []
        for ad, plugin in self._pluginler.items():
            metod = getattr(plugin, hook_name, None)
            if metod is not None and callable(metod):
                # PluginBase'in no-op implementasyonunu atla
                if getattr(type(plugin).__dict__.get(hook_name), "__func__", None) is getattr(
                    PluginBase.__dict__.get(hook_name), "__func__", None
                ):
                    # Metod override edilmemiş (PluginBase'deki no-op)
                    continue
                callables.append(metod)
        return callables

    def hook_cagir(
        self, hook_name: str, **kwargs: Any
    ) -> None:
        """Belirtilen hook'u tüm plugin'lerde çağır.

        Her plugin try/except ile izole çalıştırılır. Bir plugin'deki
        hata diğerlerini etkilemez.

        Args:
            hook_name: Çağrılacak metod adı.
            **kwargs:  Metoda aktarılacak keyword argümanları.
        """
        if not self._aktif:
            return

        for ad, plugin in self._pluginler.items():
            metod = getattr(plugin, hook_name, None)
            if metod is None or not callable(metod):
                continue

            # PluginBase no-op kontrolü
            base_metod = getattr(PluginBase, hook_name, None)
            if base_metod is not None:
                # Aynı fonksiyon referansı mı? (override edilmemiş)
                if getattr(metod, "__func__", None) is getattr(base_metod, "__func__", None):
                    continue

            try:
                metod(**kwargs)
            except Exception as e:
                logger.warning(
                    "[Plugin] '%s'.%s() hatasi: %s",
                    ad, hook_name, e,
                )

    def hook_cagir_mesaj(
        self, hook_name: str, message: str, context: dict
    ) -> str:
        """on_message türü hook'lar: mesaj döndürebilir."""
        if not self._aktif:
            return message

        guncel = message
        for ad, plugin in self._pluginler.items():
            metod = getattr(plugin, hook_name, None)
            if metod is None or not callable(metod):
                continue
            base_metod = getattr(PluginBase, hook_name, None)
            if base_metod is not None:
                if getattr(metod, "__func__", None) is getattr(base_metod, "__func__", None):
                    continue
            try:
                sonuc = metod(guncel, context)
                if isinstance(sonuc, str):
                    guncel = sonuc
            except Exception as e:
                logger.warning(
                    "[Plugin] '%s'.%s() hatasi: %s", ad, hook_name, e,
                )
        return guncel

    def hook_cagir_pre_llm(
        self, messages: list, context: dict
    ) -> Tuple[list, dict]:
        """pre_llm_call hook'larını zincirleme çağır."""
        if not self._aktif:
            return messages, context

        guncel_msgs = list(messages)
        guncel_ctx = dict(context)
        for ad, plugin in self._pluginler.items():
            metod = getattr(plugin, "pre_llm_call", None)
            if metod is None or not callable(metod):
                continue
            base_metod = getattr(PluginBase, "pre_llm_call", None)
            if base_metod is not None:
                if getattr(metod, "__func__", None) is getattr(base_metod, "__func__", None):
                    continue
            try:
                yeni_msgs, yeni_ctx = metod(guncel_msgs, guncel_ctx)
                if isinstance(yeni_msgs, list):
                    guncel_msgs = yeni_msgs
                if isinstance(yeni_ctx, dict):
                    guncel_ctx = yeni_ctx
            except Exception as e:
                logger.warning(
                    "[Plugin] '%s'.pre_llm_call() hatasi: %s", ad, e,
                )
        return guncel_msgs, guncel_ctx

    def hook_cagir_post_llm(
        self, response: dict, context: dict
    ) -> dict:
        """post_llm_call hook'larını zincirleme çağır."""
        if not self._aktif:
            return response

        guncel_resp = dict(response)
        for ad, plugin in self._pluginler.items():
            metod = getattr(plugin, "post_llm_call", None)
            if metod is None or not callable(metod):
                continue
            base_metod = getattr(PluginBase, "post_llm_call", None)
            if base_metod is not None:
                if getattr(metod, "__func__", None) is getattr(base_metod, "__func__", None):
                    continue
            try:
                sonuc = metod(guncel_resp, context)
                if isinstance(sonuc, dict):
                    guncel_resp = sonuc
            except Exception as e:
                logger.warning(
                    "[Plugin] '%s'.post_llm_call() hatasi: %s", ad, e,
                )
        return guncel_resp

    # ── Durum / Sorgulama ──────────────────────────────────────────────

    def plugin_listesi(self) -> List[Dict[str, str]]:
        """Yüklenmiş plugin'lerin listesi."""
        return [
            {"name": p.name, "version": p.version, "class": type(p).__name__}
            for p in self._pluginler.values()
        ]

    def plugin_al(self, ad: str) -> Optional[PluginBase]:
        """Adıyla plugin instance'ı döndür."""
        return self._pluginler.get(ad)

    @property
    def aktif(self) -> bool:
        return self._aktif

    @property
    def sayi(self) -> int:
        return len(self._pluginler)


# ── Singleton (global) ────────────────────────────────────────────────
_global_manager: Optional[PluginManager] = None


def plugin_manager_al() -> PluginManager:
    """Global PluginManager singleton'una eriş.

    İlk çağrıda otomatik oluşturur, config.yaml'yi okur ve
    auto_load=True ise plugin'leri yükler.
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = PluginManager()
        _global_manager.config_yukle()
        if _global_manager.aktif and _global_manager._oto_yukle:
            _global_manager.tumunu_yukle()
    return _global_manager


# ── Kısayol fonksiyonları ─────────────────────────────────────────────

def plugin_yukle(ad: str, path: str) -> Optional[PluginBase]:
    """Kısayol: singleton üzerinden plugin yükle."""
    return plugin_manager_al().plugin_yukle(ad, path)


def plugin_kaldir(ad: str) -> None:
    """Kısayol: singleton üzerinden plugin kaldır."""
    return plugin_manager_al().plugin_kaldir(ad)


def hook_cagir(hook_name: str, **kwargs: Any) -> None:
    """Kısayol: singleton üzerinden hook çağır."""
    return plugin_manager_al().hook_cagir(hook_name, **kwargs)


def plugin_listesi() -> List[Dict[str, str]]:
    """Kısayol: yüklenmiş plugin listesi."""
    return plugin_manager_al().plugin_listesi()


__all__ = [
    "PluginManager",
    "plugin_manager_al",
    "plugin_yukle",
    "plugin_kaldir",
    "hook_cagir",
    "plugin_listesi",
]
