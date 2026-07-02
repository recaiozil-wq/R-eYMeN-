# -*- coding: utf-8 -*-
"""
provider_plugin_base.py — ReYMeN Provider Plugin Base.

Soyut temel sinif (ABC): `ProviderPluginBase`.

Provider plugin'leri, bir dis hizmete (API, veritabani, model,
donanim vb.) erisim saglayan eklentilerdir. Bu sinif, tum provider
plugin'lerinin uymasi gereken asgari ara yuzu (contract) tanimlar.

Kullanim:
    class MyProvider(ProviderPluginBase):
        name = "my_provider"
        version = "1.0.0"

        def init(self, config: dict | None = None) -> bool:
            ...
        def health_check(self) -> dict:
            ...
        def shutdown(self) -> None:
            ...
"""

from __future__ import annotations

import abc
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ProviderPluginBase(abc.ABC):
    """Provider plugin'leri icin soyut temel sinif.

    Tum provider plugin'leri bu siniftan turemelidir ve asagidaki
    ozellik/metotlari uygulamalidir.

    Attributes:
        name: Provider'in benzersiz adi (ornek: "openai", "postgresql").
        version: Provider surum numarasi.
        _providers: Desteklenen provider adlari (get_providers() tarafindan
                    donulur).
        _active_provider: Su an aktif olan provider adi.
    """

    # ── Zorunlu sinif ozellikleri (override edilmelidir) ──────────────────
    name: str = ""
    version: str = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Alt sinif olusturulurken name ve version kontrolu."""
        super().__init_subclass__(**kwargs)
        if not cls.name:
            raise TypeError(
                f"{cls.__name__} must define a non-empty 'name' class attribute."
            )
        if not cls.version:
            raise TypeError(
                f"{cls.__name__} must define a non-empty 'version' class attribute."
            )

    def __init__(self, config: dict | None = None) -> None:
        self._providers: list[str] = []
        self._active_provider: str | None = None

    # ── Zorunlu metotlar ──────────────────────────────────────────────────

    @abc.abstractmethod
    def init(self, config: dict | None = None) -> bool:
        """Provider'i baslat / yapilandir.

        Args:
            config: Yapilandirma sozlugu (API anahtari, URL, timeout vb.).

        Returns:
            Basarili ise True, basarisiz ise False.
        """
        ...

    @abc.abstractmethod
    def health_check(self) -> dict:
        """Provider'in saglik kontrolu.

        Returns:
            En az su anahtarlari iceren bir sozluk:
              - "status": "ok", "degraded" veya "down"
              - "latency_ms": Yanit suresi (milisaniye, mumkunse)
              - "message": Aciklama (opsiyonel)
        """
        ...

    @abc.abstractmethod
    def shutdown(self) -> None:
        """Provider'i guvenli sekilde kapat.

        Kaynaklari serbest birakir, baglantilari kapatir.
        """
        ...

    # ── Provider listesi ve secimi ─────────────────────────────────────────

    def get_providers(self) -> list[str]:
        """Desteklenen provider adlarini dondur.

        Returns:
            Provider adi listesi (ornek: ["varsayilan", "gelismis"]).
        """
        return list(self._providers)

    def set_provider(self, provider_name: str) -> bool:
        """Aktif provider'i ayarla.

        Args:
            provider_name: Aktif edilecek provider adi.
                          get_providers() tarafindan donulen adlardan biri
                          olmalidir.

        Returns:
            Basarili ise True, gecersiz ad ise False.
        """
        if provider_name in self._providers:
            self._active_provider = provider_name
            logger.debug(
                "[ProviderPluginBase] '%s' aktif provider: %s",
                self.name, provider_name,
            )
            return True
        logger.warning(
            "[ProviderPluginBase] '%s' icin gecersiz provider: '%s'. "
            "Secenekler: %s",
            self.name, provider_name, self._providers,
        )
        return False

    # ── Opsiyonel yardimci metotlar ───────────────────────────────────────

    def __repr__(self) -> str:
        active = self._active_provider or "(none)"
        return (
            f"<{self.__class__.__name__} name={self.name!r} "
            f"version={self.version!r} active_provider={active!r}>"
        )

    def __str__(self) -> str:
        active = self._active_provider or ""
        suffix = f" [{active}]" if active else ""
        return f"{self.name} v{self.version}{suffix}"
