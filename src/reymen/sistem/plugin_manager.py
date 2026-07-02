# -*- coding: utf-8 -*-
"""
plugin_manager.py — ReYMeN Plugin Yonetim Sistemi (ReYMeN-seviyesi).

Iki plugin kategorisi:
  1. Arac plugin'leri  — plugins/*.py icinde run() fonksiyonu
  2. Hafiza plugin'leri — plugins/memory/<ad>/__init__.py icinde
     AbstraktHafizaSaglayici alt sinifi + kaydet(ctx) fonksiyonu

YENI: PluginYoneticisi sinifi:
  - list_plugins()     → tum pluginleri listele (+ providers bilgisi)
  - plugin_info(adi)   → detayli plugin bilgisi (+ providers)
  - enable_plugin(adi) → plugin'i aktif et
  - disable_plugin(adi) → plugin'i devre disi birak
  - plugin_reload(adi) → plugin'i yeniden yukle (kaldir + yukle)
  - hot_reload(adi)    → plugin'i hot-reload ile yeniden yukle (importlib.reload)
  - get_providers(adi) → plugin'in destekledigi provider'lari listele
  - plugin_baslat(adi, provider=None) → plugin'i belirtilen provider ile baslat

Kullanim:
    pm = PluginManager("plugins")
    print(pm.list_plugins())
    print(pm.run("hello_tool", target="ReYMeN"))

    # Hafiza plugin'leri:
    pm.hafiza_pluginlerini_yukle(oturum_id="ses-001")
    aktif = pm.aktif_hafiza_saglayici()

    # Yeni yonetici:
    yonetici = PluginYoneticisi("plugins")
    yonetici.list_plugins()
    yonetici.plugin_info("kanban")
"""
from __future__ import annotations
import importlib
import importlib.util
import logging
import sys
import weakref
from pathlib import Path
from typing import Iterator, Callable, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from reymen.hafiza.memory_provider import AbstraktHafizaSaglayici, HafizaPluginKayit

logger = logging.getLogger(__name__)


class PluginManifest:
    """Lazy-loaded plugin metadata.

    Bir plugin dosyasini (veya modulunu) lazy olarak yukler.
    """

    __slots__ = ("name", "path", "_module_ref")

    def __init__(self, name: str, path: Path) -> None:
        self.name = name
        self.path = path
        self._module_ref: weakref.ref | None = None

    def load(self) -> object:
        if self._module_ref is not None:
            mod = self._module_ref()
            if mod is not None:
                return mod
        spec = importlib.util.spec_from_file_location(self.name, self.path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self._module_ref = weakref.ref(mod)
        return mod

    def get_run(self) -> Callable | None:
        mod = self.load()
        return getattr(mod, "run", None)


class PluginManager:
    """Disaridan yuklenebilir arac ve hafiza plugin sistemi (mevcut)."""

    def __init__(self, plugin_dir: str = "plugins") -> None:
        self._dir = Path(plugin_dir)
        self._registry: dict[str, PluginManifest] = {}
        self._hafiza_kayit: Optional["HafizaPluginKayit"] = None

    # ── Arac plugin'leri ──────────────────────────────────────────────────

    def discover(self) -> Iterator[str]:
        """plugins/ altindaki tum .py dosyalarini lazy tara."""
        if not self._dir.exists():
            return
        for path in self._dir.glob("*.py"):
            if path.stem.startswith("_") or path.stem == "__init__":
                continue
            name = path.stem
            if name not in self._registry:
                self._registry[name] = PluginManifest(name, path)
            yield name

    def get(self, name: str) -> Callable | None:
        if name not in self._registry:
            list(self.discover())
        manifest = self._registry.get(name)
        return manifest.get_run() if manifest else None

    def run(self, name: str, **kwargs) -> object:
        fn = self.get(name)
        if fn is None:
            raise KeyError(f"Plugin '{name}' bulunamadi veya run() yok.")
        return fn(**kwargs)

    def list_plugins(self) -> list[str]:
        list(self.discover())
        return list(self._registry.keys())

    # ── Hafiza plugin'leri ─────────────────────────────────────────────────

    def hafiza_pluginlerini_yukle(
        self,
        oturum_id: str = "varsayilan",
        tercih: Optional[str] = None,
        **baslat_kwargs,
    ) -> Optional["AbstraktHafizaSaglayici"]:
        """plugins/memory/<ad>/__init__.py icindeki hafiza plugin'lerini keşfet ve aktive et."""
        try:
            from reymen.hafiza.memory_provider import HafizaPluginKayit
        except ImportError:
            logger.warning("memory_provider modulu bulunamadi, hafiza pluginleri yuklenemedi.")
            return None

        if self._hafiza_kayit is None:
            self._hafiza_kayit = HafizaPluginKayit()

        hafiza_dizin = self._dir / "memory"
        if not hafiza_dizin.exists():
            logger.debug("plugins/memory/ dizini yok, hafiza plugin'i yok.")
            return None

        yuklenenler: list[str] = []
        for plugin_klasoru in sorted(hafiza_dizin.iterdir()):
            if not plugin_klasoru.is_dir():
                continue
            init_dosyasi = plugin_klasoru / "__init__.py"
            if not init_dosyasi.exists():
                continue
            plugin_adi = plugin_klasoru.name
            modul_adi = f"plugins.memory.{plugin_adi}"
            try:
                spec = importlib.util.spec_from_file_location(
                    modul_adi, str(init_dosyasi)
                )
                modul = importlib.util.module_from_spec(spec)
                sys.modules[modul_adi] = modul
                spec.loader.exec_module(modul)
                kaydet_fn = getattr(modul, "kaydet", None)
                if callable(kaydet_fn):
                    kaydet_fn(self._hafiza_kayit)
                    yuklenenler.append(plugin_adi)
                    logger.debug("Hafiza plugin yuklendi: %s", plugin_adi)
            except Exception as exc:
                logger.warning("Hafiza plugin yuklenemedi [%s]: %s", plugin_adi, exc)

        if not yuklenenler:
            return None

        # Tercih veya otomatik secim
        siralama = ([tercih] if tercih else []) + yuklenenler
        for ad in siralama:
            if self._hafiza_kayit.aktif_saglayici_sec(
                ad, oturum_id, **baslat_kwargs
            ):
                return self._hafiza_kayit.aktif_al()

        logger.info("Hic hafiza saglayici aktive edilemedi.")
        return None

    def aktif_hafiza_saglayici(self) -> Optional["AbstraktHafizaSaglayici"]:
        if self._hafiza_kayit is None:
            return None
        return self._hafiza_kayit.aktif_al()

    def hafiza_saglayici_listele(self) -> list[str]:
        if self._hafiza_kayit is None:
            return []
        return self._hafiza_kayit.saglayici_listele()

    def hafizayi_kapat(self) -> None:
        if self._hafiza_kayit:
            self._hafiza_kayit.hepsini_kapat()

    def __del__(self) -> None:
        self._registry.clear()
        try:
            self.hafizayi_kapat()
        except Exception as _plugin_m_e191:
            print(f"[UYARI] plugin_manager.py:192 - {_plugin_m_e191}")


class PluginYoneticisi:
    """ReYMeN Plugin Yoneticisi — plugin listeleme, aktif/devre disi, detay,
    hot-reload ve provider plugin destegi.

    PluginYukleyici ile birlikte calisir ve CLI komutlarina backend saglar.

    Kullanim:
        yonetici = PluginYoneticisi()
        yonetici.list_plugins()       # tum pluginleri getir (+ providers)
        yonetici.plugin_info("kanban")  # detayli bilgi (+ providers)
        yonetici.enable_plugin("kanban")
        yonetici.disable_plugin("kanban")
        yonetici.plugin_reload("kanban")
        yonetici.hot_reload("kanban")   # importlib.reload ile yerinde yeniden yukle
        yonetici.get_providers("kanban")  # provider listesi
        yonetici.plugin_baslat("kanban", provider="openai")  # provider secimi
    """

    def __init__(self, plugin_dir: Path | str | None = None):
        if plugin_dir is None:
            from reymen.sistem.plugin_loader import PLUGIN_DIZIN
            self._dizin = PLUGIN_DIZIN
        else:
            self._dizin = Path(plugin_dir)

        self._aktif_pluginler: dict[str, bool] = {}  # ad -> aktif mi?
        self._yukleyici = None
        self._yuklu_liste: list[str] = []

    @property
    def yukleyici(self):
        """Lazy-init PluginYukleyici."""
        if self._yukleyici is None:
            try:
                from reymen.sistem.plugin_loader import PluginYukleyici
                self._yukleyici = PluginYukleyici(dizin=self._dizin)
            except ImportError:
                logger.error("plugin_loader.PluginYukleyici bulunamadi.")
                return None
        return self._yukleyici

    def _aktif_durumlari_yukle(self) -> None:
        """Aktif/devre disi durumlarini plugin.yaml'den oku (cache)."""
        if self._aktif_pluginler:
            return
        for klasor in sorted(self._dizin.iterdir()):
            if not klasor.is_dir() or klasor.name.startswith("_"):
                continue
            yaml_dosya = klasor / "plugin.yaml"
            aktif = True  # varsayilan: aktif
            if yaml_dosya.exists():
                try:
                    import yaml
                    with open(yaml_dosya, "r", encoding="utf-8") as f:
                        veri = yaml.safe_load(f)
                    if isinstance(veri, dict):
                        aktif = veri.get("enabled", True)
                except Exception as _plugin_m_e248:
                    print(f"[UYARI] plugin_manager.py:249 - {_plugin_m_e248}")
            self._aktif_pluginler[klasor.name] = aktif

    def _tarayarak_yukle(self) -> list[str]:
        """PluginYukleyici ile backend + tool pluginlerini yukle."""
        yl = self.yukleyici
        if yl is None:
            return []
        if not self._yuklu_liste:
            self._yuklu_liste = yl.hepsini_yukle()
            self._yuklu_liste.extend(yl.tool_pluginlerini_yukle())
        return self._yuklu_liste

    def list_plugins(self) -> list[dict]:
        """Tum pluginlerin detayli listesini dondur.

        Returns:
            Her plugin icin sozluk: ad, versiyon, kind, aktif, aciklama, yuklu, arac_sayisi, providers
        """
        self._aktif_durumlari_yukle()
        self._tarayarak_yukle()  # plugin.yaml'lari parse et
        yl = self.yukleyici
        if yl is None:
            return []

        # PluginYukleyici'den tum plugin bilgisini al
        yl_tumu = yl.tum_pluginler()

        sonuc = []
        for p in yl_tumu:
            klasor_adi = p["klasor"]
            yaml_veri = yl.plugin_yaml_bilgisi(klasor_adi) or {}
            sonuc.append({
                "name": p["adi"],
                "version": p["versiyon"],
                "kind": p["kind"],
                "enabled": self._aktif_pluginler.get(klasor_adi, True),
                "description": p["aciklama"],
                "loaded": p["yuklu"],
                "tools": len(yl.plugin_bilgisi(klasor_adi).get("araclar", [])),
                "providers": yaml_veri.get("providers", []),
            })

        # PluginManager'dan .py pluginlerini de ekle
        try:
            mgr = PluginManager(str(self._dizin))
            for p_adi in mgr.list_plugins():
                if not any(s["name"] == p_adi for s in sonuc):
                    sonuc.append({
                        "name": p_adi,
                        "version": "",
                        "kind": "tool",
                        "enabled": True,
                        "description": "",
                        "loaded": True,
                        "tools": 1,
                        "providers": [],
                    })
        except Exception as _plugin_m_e303:
            print(f"[UYARI] plugin_manager.py:304 - {_plugin_m_e303}")

        return sonuc

    def plugin_info(self, ad: str) -> dict:
        """Bir pluginin detayli bilgisini dondur.

        Args:
            ad: Plugin adi (klasor adi).

        Returns:
            Detayli plugin bilgisi sozlugu.
        """
        self._tarayarak_yukle()  # yaml'lari parse et
        yl = self.yukleyici
        if yl is None:
            return {"adi": ad, "error": "PluginYukleyici mevcut degil"}

        # plugin.yaml'den oku
        yaml_veri = yl.plugin_yaml_bilgisi(ad) or {}
        
        # Plugin bilgisi
        bilgi = yl.plugin_bilgisi(ad)

        # Klasor kontrolu
        plugin_klasor = self._dizin / ad
        var_mi = plugin_klasor.exists() and plugin_klasor.is_dir()
        init_var_mi = (plugin_klasor / "__init__.py").exists()

        # Yetenekler
        yetenekler = []
        if init_var_mi:
            try:
                mod = yl._yuklu.get(ad)
                if mod is not None:
                    for attr in dir(mod):
                        if not attr.startswith("_"):
                            yetenekler.append(attr)
            except Exception as _plugin_m_e341:
                print(f"[UYARI] plugin_manager.py:342 - {_plugin_m_e341}")

        return {
            "adi": yaml_veri.get("name", ad),
            "klasor": ad,
            "versiyon": yaml_veri.get("version", bilgi.get("versiyon", "")),
            "aciklama": yaml_veri.get("description", bilgi.get("aciklama", "")),
            "kind": yaml_veri.get("kind", bilgi.get("kind", "unknown")),
            "yazar": yaml_veri.get("author", bilgi.get("yazar", "")),
            "aktif": self._aktif_pluginler.get(ad, True),
            "yuklu": bilgi.get("yuklu", False),
            "klasor_var": var_mi,
            "init_var": init_var_mi,
            "araclar": bilgi.get("araclar", yaml_veri.get("tools", [])),
            "yetenekler": yetenekler,
            "providers": yaml_veri.get("providers", []),
        }

    def enable_plugin(self, ad: str) -> bool:
        """Bir plugini aktif et. plugin.yaml'de enabled: true yazar."""
        yaml_dosya = self._dizin / ad / "plugin.yaml"
        if not yaml_dosya.exists():
            logger.warning("plugin.yaml bulunamadi: %s", ad)
            return False
        try:
            import yaml
            with open(yaml_dosya, "r", encoding="utf-8") as f:
                veri = yaml.safe_load(f) or {}
            veri["enabled"] = True
            with open(yaml_dosya, "w", encoding="utf-8") as f:
                yaml.dump(veri, f, default_flow_style=False, allow_unicode=True)
            self._aktif_pluginler[ad] = True
            logger.info("[Plugin] Etkin: %s", ad)
            return True
        except Exception as e:
            logger.error("[Plugin] Etkinlestirme hatasi [%s]: %s", ad, e)
            return False

    def disable_plugin(self, ad: str) -> bool:
        """Bir plugini devre disi birak. plugin.yaml'de enabled: false yazar."""
        yaml_dosya = self._dizin / ad / "plugin.yaml"
        if not yaml_dosya.exists():
            logger.warning("plugin.yaml bulunamadi: %s", ad)
            return False
        try:
            import yaml
            with open(yaml_dosya, "r", encoding="utf-8") as f:
                veri = yaml.safe_load(f) or {}
            veri["enabled"] = False
            with open(yaml_dosya, "w", encoding="utf-8") as f:
                yaml.dump(veri, f, default_flow_style=False, allow_unicode=True)
            self._aktif_pluginler[ad] = False
            # Modulu bellekten kaldir
            yl = self.yukleyici
            if yl:
                yl.plugin_kaldir(ad)
            logger.info("[Plugin] Devre disi: %s", ad)
            return True
        except Exception as e:
            logger.error("[Plugin] Devre disi birakma hatasi [%s]: %s", ad, e)
            return False

    def plugin_reload(self, ad: str) -> bool:
        """Bir plugini yeniden yukle (modulu yeniden import et)."""
        yl = self.yukleyici
        if yl is None:
            return False
        # once kaldir
        if sys.modules.get(f"plugins.{ad}") is not None:
            yl.plugin_kaldir(ad)
        # sonra yeniden yukle
        basari = yl.yeniden_yukle(ad)
        if basari:
            logger.info("[Plugin] Yeniden yuklendi: %s", ad)
        else:
            logger.warning("[Plugin] Yeniden yukleme basarisiz: %s", ad)
        return basari

    def hot_reload(self, ad: str) -> bool:
        """Bir plugini hot-reload ile yeniden yukle (importlib.reload).

        plugin_reload()'dan farki:
          - Modulu bellekten *kaldirmadan* importlib.reload() ile yerinde yeniden yukler.
          - Bu sayede plugin'e disaridan tutulan referanslar (motor kaydi vb.)
            gecersizlesmez.
          - Plugin'in aktif/pasif durumunu korur.
          - Bagimli plugin'leri de (kontrol edilebilen) yeniden yukler.

        Args:
            ad: Plugin adi (klasor adi).

        Returns:
            Basarili ise True.
        """
        yl = self.yukleyici
        if yl is None:
            return False

        modul = yl._yuklu.get(ad)
        if modul is None:
            # Plugin yuklu degil, normal yeniden yukleme dene
            logger.info("[Plugin] Hot-reload: '%s' yuklu degil, normal reload yapiliyor.", ad)
            return self.plugin_reload(ad)

        # Aktif durumunu koru
        was_active = self._aktif_pluginler.get(ad, True)

        try:
            # Modul adindan sys.modules uzerinden importlib.reload cagir
            modul_adi = f"plugins.{ad}"
            if modul_adi in sys.modules:
                importlib.reload(sys.modules[modul_adi])

            # plugin.yaml cache'ini guncelle
            if ad in yl._yaml_bilgisi:
                try:
                    klasor = self._dizin / ad
                    yeni_yaml = yl._yaml_yukle(klasor)
                    if yeni_yaml is not None:
                        yl._yaml_bilgisi[ad] = yeni_yaml
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                    )

            self._aktif_pluginler[ad] = was_active

            # Bagimli plugin'leri de yeniden yukle (kontrol edilebilenler)
            bagimlilar = self._bagimli_pluginler(ad)
            for dep_ad in bagimlilar:
                dep_mod_adi = f"plugins.{dep_ad}"
                if dep_mod_adi in sys.modules:
                    try:
                        importlib.reload(sys.modules[dep_mod_adi])
                        logger.debug("[Plugin] Hot-reload bagimli: %s", dep_ad)
                    except Exception as dep_e:
                        logger.warning(
                            "[Plugin] Bagimli hot-reload hatasi [%s]: %s",
                            dep_ad, dep_e,
                        )

            logger.info("[Plugin] Hot-reload: %s (aktif=%s)", ad, was_active)
            return True
        except Exception as e:
            logger.error("[Plugin] Hot-reload hatasi [%s]: %s", ad, e)
            return False

    def _bagimli_pluginler(self, ad: str) -> list[str]:
        """Bir plugin'e bagimli olan pluginleri bul (basit string taramasi).

        plugin_loader._yuklu'daki modullerin __init__.py dosyalarinda
        'from plugins.{ad}' veya 'import plugins.{ad}' gecenleri bulur.

        Args:
            ad: Plugin adi.

        Returns:
            Bagimli plugin adlari listesi.
        """
        yl = self.yukleyici
        if yl is None:
            return []
        bagimlilar = []
        arama_str_1 = f"plugins.{ad}"
        arama_str_2 = f"from plugins import {ad}"
        for dep_ad, dep_mod in yl._yuklu.items():
            if dep_ad == ad:
                continue
            try:
                dosya = getattr(dep_mod, "__file__", None)
                if dosya:
                    icerik = Path(dosya).read_text(encoding="utf-8", errors="ignore")
                    if arama_str_1 in icerik or arama_str_2 in icerik:
                        bagimlilar.append(dep_ad)
            except Exception as _e:
                __import__("logging").getLogger(__name__).warning(
                    "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                )
        return bagimlilar

    # ── Provider Plugin Destegi ─────────────────────────────────────────────

    def get_providers(self, ad: str) -> list[dict]:
        """Bir pluginin destekledigi provider'lari dondur.

        Plugin'in plugin.yaml dosyasindaki ``providers`` alanindan okunur.
        Her provider sozlugu su alanlari icerebilir:
          - name: Provider adi (ornek: "openai", "anthropic")
          - description: Provider aciklamasi
          - version: Provider versiyonu
          - default: Varsayilan provider mi? (bool)

        Args:
            ad: Plugin adi (klasor adi).

        Returns:
            Provider bilgisi listesi. Ornek:
            [{"name": "openai", "description": "OpenAI API", "version": "1.0", "default": True}]
        """
        yl = self.yukleyici
        if yl is None:
            return []
        yaml_veri = yl.plugin_yaml_bilgisi(ad)
        if not yaml_veri:
            return []
        return yaml_veri.get("providers", [])

    def _provider_base_baslat(
        self,
        modul: object,
        ad: str,
        secilen_provider: str | None,
    ) -> None:
        """Modul icinde ProviderPluginBase alt sinifi varsa baslat.

        Args:
            modul: Plugin modulu (yl._yuklu[ad]).
            ad: Plugin adi (sadece log icin).
            secilen_provider: Kullanici tarafindan secilen provider adi.
        """
        try:
            from reymen.sistem.provider_plugin_base import ProviderPluginBase
        except ImportError:
            return

        if modul is None:
            return

        # Modul icinde ProviderPluginBase alt siniflarini bul
        provider_instance = None
        for attr_name in dir(modul):
            attr = getattr(modul, attr_name, None)
            if (
                isinstance(attr, type)
                and issubclass(attr, ProviderPluginBase)
                and attr is not ProviderPluginBase
            ):
                try:
                    instance = attr()
                    # Provider listesini plugin.yaml'den oku
                    yl = self.yukleyici
                    if yl:
                        yaml_veri = yl.plugin_yaml_bilgisi(ad) or {}
                        provider_listesi = yaml_veri.get("providers", [])
                        instance._providers = [
                            p.get("name", p) if isinstance(p, dict) else p
                            for p in provider_listesi
                        ]

                    # Provider secimi yap
                    if secilen_provider:
                        instance.set_provider(secilen_provider)
                    elif instance._providers:
                        # Varsayilani bul veya ilk provider'i sec
                        default = None
                        yl = self.yukleyici
                        if yl:
                            yaml_veri = yl.plugin_yaml_bilgisi(ad) or {}
                            for p in yaml_veri.get("providers", []):
                                if isinstance(p, dict) and p.get("default"):
                                    default = p.get("name")
                                    break
                        if default and default in instance._providers:
                            instance.set_provider(default)
                        else:
                            instance.set_provider(instance._providers[0])

                    # Instance'i modul uzerinde sakla
                    setattr(modul, "_provider_instance", instance)

                    # init() cagir
                    instance.init()

                    logger.info(
                        "[Plugin] ProviderPluginBase baslatildi: %s -> %s (provider: %s)",
                        ad, instance.name, instance._active_provider,
                    )
                    provider_instance = instance
                except Exception as exc:
                    logger.error(
                        "[Plugin] ProviderPluginBase baslatma hatasi [%s]: %s",
                        ad, exc,
                    )

        if provider_instance is None:
            logger.debug("[Plugin] '%s' icin ProviderPluginBase alt sinifi bulunamadi.", ad)

    def plugin_baslat(self, ad: str, provider: str | None = None) -> bool:
        """Bir plugini belirtilen provider ile baslat.

        Provider secimi su sekilde calisir:
          1. Verilen provider adi plugin.yaml'deki ``providers`` listesinde
             aranir.
          2. Eslesen provider varsa plugin o provider ile baslatilir.
          3. Provider=None ise varsayilan (default=True) provider kullanilir,
             yoksa ilk provider kullanilir.
          4. Provider listesi bossa veya provider belirtilmemisse plugin
             normal sekilde baslatilir.

        Args:
            ad: Plugin adi (klasor adi).
            provider: Provider adi (None = varsayilan).

        Returns:
            Basarili ise True.
        """
        yl = self.yukleyici
        if yl is None:
            return False

        # plugin.yaml cache'ini doldur (henuz yuklenmemisse)
        if ad not in yl._yaml_bilgisi:
            klasor = self._dizin / ad
            if klasor.exists() and klasor.is_dir():
                yaml_veri = yl._yaml_yukle(klasor) or {}
                yl._yaml_bilgisi[ad] = yaml_veri

        # Provider dogrulama
        secilen_provider = provider
        if provider is not None:
            providers = self.get_providers(ad)
            provider_isimleri = [p.get("name") for p in providers if isinstance(p, dict)]
            if provider not in provider_isimleri:
                logger.warning(
                    "[Plugin] '%s' icin gecersiz provider: '%s'. "
                    "Gecerli provider'lar: %s",
                    ad, provider, provider_isimleri,
                )
                return False

        # Plugin zaten yuklu degilse yukle
        if ad not in yl._yuklu:
            basari = yl._yukle(ad)
            if not basari:
                logger.error("[Plugin] '%s' yuklenemedi (provider: %s)", ad, provider)
                return False

        # Aktif et
        self._aktif_pluginler[ad] = True

        # Provider bilgisini modul uzerinde sakla (plugin runtime'da kullanabilir)
        modul = yl._yuklu.get(ad)
        if modul is not None:
            setattr(modul, "_aktif_provider", secilen_provider)

        # ── ProviderPluginBase entegrasyonu ───────────────────────────────
        # Modul icinde ProviderPluginBase alt sinifi varsa, onu baslat
        self._provider_base_baslat(modul, ad, secilen_provider)

        if secilen_provider:
            logger.info("[Plugin] '%s' baslatildi (provider: %s)", ad, secilen_provider)
        else:
            logger.info("[Plugin] '%s' baslatildi (varsayilan provider)", ad)

        return True

    def plugin_sayisi(self) -> dict:
        """Plugin istatistikleri."""
        tumu = self.list_plugins()
        return {
            "toplam": len(tumu),
            "aktif": sum(1 for p in tumu if p["enabled"]),
            "devre_disi": sum(1 for p in tumu if not p["enabled"]),
            "yuklu": sum(1 for p in tumu if p["loaded"]),
            "backend": sum(1 for p in tumu if p["kind"] == "backend"),
            "tool": sum(1 for p in tumu if p["kind"] == "tool"),
        }

    # ── .reyplugin Export/Import ─────────────────────────────────────────

    def export_plugin(self, ad: str, cikti_yol: str | None = None) -> str:
        """Plugin'i .reyplugin paketine dışa aktar.

        Args:
            ad: Plugin klasör adı.
            cikti_yol: Çıktı dosya yolu (None = {ad}.reyplugin).

        Returns:
            Oluşturulan dosya yolu.
        """
        import json, zipfile, datetime

        plugin_klasor = self._dizin / ad
        if not plugin_klasor.exists() or not plugin_klasor.is_dir():
            return f"[HATA] Plugin '{ad}' bulunamadi: {plugin_klasor}"

        if cikti_yol is None:
            cikti_yol = f"{ad}.reyplugin"

        # Metadata
        metadata = {
            "export_tarih": datetime.datetime.now().isoformat(),
            "kaynak": "ReYMeN",
            "plugin_adi": ad,
            "dosyalar": [],
        }

        with zipfile.ZipFile(cikti_yol, "w", zipfile.ZIP_DEFLATED) as zf:
            for dosya in plugin_klasor.rglob("*"):
                if dosya.is_file() and "__pycache__" not in str(dosya):
                    arcname = str(dosya.relative_to(plugin_klasor.parent))
                    zf.write(dosya, arcname)
                    metadata["dosyalar"].append(arcname)

            # Metadata ekle
            zf.writestr("metadata.json", json.dumps(metadata, indent=2, ensure_ascii=False))

        return f"[OK] '{ad}' -> {cikti_yol} ({len(metadata['dosyalar'])} dosya)"

    def import_plugin(self, kaynak: str) -> str:
        """.reyplugin paketini içe aktar.

        Args:
            kaynak: .reyplugin dosya yolu.

        Returns:
            İşlem sonucu mesajı.
        """
        import zipfile, json, shutil

        dosya = Path(kaynak)
        if not dosya.exists():
            return f"[HATA] Dosya bulunamadi: {kaynak}"

        if dosya.suffix != ".reyplugin":
            return f"[HATA] Gecersiz format: {dosya.suffix}. .reyplugin bekleniyor."

        try:
            with zipfile.ZipFile(dosya, "r") as zf:
                # Metadata oku
                if "metadata.json" not in zf.namelist():
                    return "[HATA] metadata.json bulunamadi."

                metadata = json.loads(zf.read("metadata.json"))
                plugin_adi = metadata.get("plugin_adi", dosya.stem)

                # Hedef klasör
                hedef = self._dizin / plugin_adi
                if hedef.exists():
                    return f"[HATA] '{plugin_adi}' zaten mevcut. Once silin veya farkli bir isim verin."

                # Ayıkla
                hedef.mkdir(parents=True, exist_ok=True)
                for uye in zf.namelist():
                    if uye.endswith("/") or uye == "metadata.json":
                        continue
                    zf.extract(uye, self._dizin)

            # Cache'i temizle (yeniden yükleme için)
            yl = self.yukleyici
            if yl and plugin_adi in yl._yaml_bilgisi:
                del yl._yaml_bilgisi[plugin_adi]
            if yl and plugin_adi in yl._yuklu:
                yl.plugin_kaldir(plugin_adi)

            return f"[OK] '{plugin_adi}' iceri aktarildi ({len(metadata.get('dosyalar', []))} dosya)"

        except zipfile.BadZipFile:
            return f"[HATA] Gecersiz ZIP dosyasi: {kaynak}"
        except json.JSONDecodeError:
            return f"[HATA] metadata.json okunamadi."
        except Exception as e:
            return f"[HATA] Import hatasi: {e}"



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test PluginYoneticisi
    yonetici = PluginYoneticisi()
    
    # Tum pluginleri listele
    tumu = yonetici.list_plugins()
    print(f"\n=== Plugin Listesi ({len(tumu)} adet) ===")
    for p in tumu:
        durum = "✓" if p["enabled"] else "✗"
        yuklu = "Y" if p["loaded"] else "-"
        print(f"  {durum} [{yuklu}] {p['name']:25s} v{p['version']:8s} {p['kind']:8s} {p['description'][:50]}")

    # Istatistikler
    istatistik = yonetici.plugin_sayisi()
    print(f"\nIstatistik: {istatistik['toplam']} plugin, {istatistik['aktif']} aktif, {istatistik['devre_disi']} devre disi")

    # Detayli bilgi
    if tumu:
        ilk = tumu[0]["name"]
        print(f"\n=== Detay: {ilk} ===")
        detay = yonetici.plugin_info(ilk)
        for k, v in detay.items():
            print(f"  {k}: {v}")
