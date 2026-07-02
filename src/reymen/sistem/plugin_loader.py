# -*- coding: utf-8 -*-
"""
plugin_loader.py — ReYMeN Plugin Sistemi (ReYMeN-seviyesi).

İki plugin kategorisi:
  1. Araç plugin'leri — plugins/<ad>/__init__.py
       Arayüz: plugin_adi, plugin_aciklamasi, kaydet(motor)

  2. Hafıza plugin'leri — plugins/memory/<ad>/__init__.py
       Arayüz: AbstraktHafizaSaglayici alt sinifi + kaydet(ctx)
       ctx: HafizaPluginKayit nesnesi

ReYMeN UYUMLULUK:
  - plugin.yaml okuma ve parse etme
  - kind: backend  → otomatik yukle
  - kind: tool     → istege bagli yukle
  - register(ctx) fonksiyonu olan plugin'leri cagir
  - PluginYoneticisi ile tam uyum

Dizin yapisi:
  plugins/
    web_scraper/__init__.py     ← arac plugin (kind: tool)
    kanban/__init__.py          ← arac plugin (kind: tool)
    memory/
      sqlite_fts/__init__.py   ← hafiza plugin (kind: backend)

Kullanim:
  from plugin_loader import PluginYukleyici
  yukleyici = PluginYukleyici()
  yukleyici.hepsini_yukle()           # kind: backend olanlari otomatik yukle
  yukleyici.tool_pluginlerini_yukle() # kind: tool olanlari manuel yukle
  yukleyici.motora_kaydet(motor)
"""
from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from reymen.hafiza.memory_provider import AbstraktHafizaSaglayici

logger = logging.getLogger(__name__)

PLUGIN_DIZIN = Path(__file__).parent / "plugins"


class PluginYukleyici:
    """ReYMeN plugin yukleyici — ReYMeN seviyesinde plugin yonetimi.

    Ozellikler:
      - plugin.yaml dosyasini okuyup parse eder
      - kind: backend plugin'leri otomatik yukler
      - kind: tool plugin'leri istege bagli yukler
      - register(ctx) fonksiyonu olan plugin'leri cagirir
      - Hafiza plugin'leri ile tam uyumlu
    """

    def __init__(self, dizin: Path = PLUGIN_DIZIN):
        self.dizin = dizin
        self._yuklu: dict[str, object] = {}
        self._yaml_bilgisi: dict[str, dict] = {}  # plugin.yaml parse edilmis veri
        self._hafiza_yoneticisi = None  # PluginManager (hafiza discovery icin)
        self._ctx: Optional[Any] = None  # register(ctx) icin context nesnesi

    # ── Ana yukleme ─────────────────────────────────────────────────────────

    def hepsini_yukle(self) -> list[str]:
        """plugins/ altindaki tum kind: backend pluginleri yukle.

        Ayrica plugin.yaml dosyasini okuyup parse eder.
        kind: tool pluginlerini yuklemez (tool_pluginlerini_yukle() ile).

        Returns:
            Yuklenen plugin adlari listesi.
        """
        if not self.dizin.exists():
            return []
        yuklenenler = []

        # Tum plugin klasorlerini tara
        for klasor in self._butun_plugin_klasorleri():
            yaml_veri = self._yaml_yukle(klasor) or {}
            self._yaml_bilgisi[klasor.name] = yaml_veri
            kind = yaml_veri.get("kind", "backend")

            # kind: backend → otomatik yukle
            if kind == "backend" and (klasor / "__init__.py").exists():
                basari = self._yukle(klasor.name)
                if basari:
                    yuklenenler.append(klasor.name)

            # register(ctx) kontrolu
            if kind == "backend" and self._ctx is not None:
                self._register_cagir(klasor.name)

        return yuklenenler

    def tool_pluginlerini_yukle(self) -> list[str]:
        """Sadece kind: tool pluginlerini yukle (istege bagli)."""
        if not self.dizin.exists():
            return []
        yuklenenler = []
        for klasor in self._butun_plugin_klasorleri():
            yaml_veri = self._yaml_bilgisi.get(klasor.name) or self._yaml_yukle(klasor) or {}
            self._yaml_bilgisi[klasor.name] = yaml_veri
            kind = yaml_veri.get("kind", "backend")
            if kind == "tool" and (klasor / "__init__.py").exists():
                basari = self._yukle(klasor.name)
                if basari:
                    yuklenenler.append(klasor.name)
        return yuklenenler

    # ── plugin.yaml okuma ───────────────────────────────────────────────────

    def _yaml_yukle(self, klasor: Path) -> dict | None:
        """Bir plugin klasorundeki plugin.yaml dosyasini oku ve parse et.

        Returns:
            Sozluk (yaml verisi) veya None (dosya yok / hata).
        """
        yaml_dosya = klasor / "plugin.yaml"
        if not yaml_dosya.exists():
            return None
        try:
            import yaml
            with open(yaml_dosya, "r", encoding="utf-8") as f:
                veri = yaml.safe_load(f)
            return veri if isinstance(veri, dict) else {}
        except ImportError:
            # yaml kutuphanesi yok — basit satir bazli parse dene
            return self._yaml_basit_parse(yaml_dosya)
        except Exception as exc:
            logger.debug("plugin.yaml parse hatasi [%s]: %s", klasor.name, exc)
            return {}

    def _yaml_basit_parse(self, yaml_dosya: Path) -> dict:
        """yaml kutuphanesi yoksa basit metin parse et."""
        veri: dict = {}
        try:
            for satir in yaml_dosya.read_text(encoding="utf-8").splitlines():
                satir = satir.strip()
                if not satir or satir.startswith("#"):
                    continue
                if ":" in satir:
                    anahtar, _, deger = satir.partition(":")
                    anahtar = anahtar.strip()
                    deger = deger.strip().strip('"').strip("'")
                    if deger and deger not in ("true", "false"):
                        veri[anahtar] = deger
        except Exception as _plugin_l_e153:
            print(f"[UYARI] plugin_loader.py:154 - {_plugin_l_e153}")
        return veri

    def plugin_yaml_bilgisi(self, plugin_adi: str) -> dict:
        """Bir pluginin plugin.yaml verisini dondur."""
        return self._yaml_bilgisi.get(plugin_adi, {})

    # ── Modul yukleme ──────────────────────────────────────────────────────

    def _yukle(self, plugin_adi: str) -> bool:
        """Tek bir plugin modulunu yukle."""
        if plugin_adi in self._yuklu:
            return True  # zaten yuklu
        try:
            modul_yol = self.dizin / plugin_adi / "__init__.py"
            if not modul_yol.exists():
                return False
            spec = importlib.util.spec_from_file_location(
                f"plugins.{plugin_adi}", str(modul_yol)
            )
            modul = importlib.util.module_from_spec(spec)
            sys.modules[f"plugins.{plugin_adi}"] = modul
            spec.loader.exec_module(modul)
            self._yuklu[plugin_adi] = modul
            logger.info("[Plugin] Yuklendi: %s", plugin_adi)
            return True
        except Exception as e:
            logger.warning("[Plugin] '%s' yuklenemedi: %s", plugin_adi, e)
            return False

    # ── register(ctx) destegi ───────────────────────────────────────────────

    def ctx_ata(self, ctx: Any) -> None:
        """register(ctx) icin context nesnesini ata.

        Bu ctx, yuklu plugin'lerdeki register(ctx) fonksiyonuna parametre
        olarak gecer.
        """
        self._ctx = ctx

    def _register_cagir(self, plugin_adi: str) -> bool:
        """Yuklu bir pluginin register(ctx) fonksiyonunu cagir."""
        modul = self._yuklu.get(plugin_adi)
        if modul is None:
            return False
        register_fn = getattr(modul, "register", None)
        if callable(register_fn) and self._ctx is not None:
            try:
                register_fn(self._ctx)
                logger.debug("[Plugin] '%s'.register(ctx) cagrildi", plugin_adi)
                return True
            except Exception as e:
                logger.warning("[Plugin] '%s'.register(ctx) hatasi: %s", plugin_adi, e)
        return False

    # ── Motor kayit ─────────────────────────────────────────────────────────

    def motora_kaydet(self, motor) -> None:
        """Yuklu pluginlerin araclarini motor'a kaydet.

        Her plugin icin kaydet(motor) fonksiyonunu cagirir.
        """
        for adi, modul in self._yuklu.items():
            kaydet_fn = getattr(modul, "kaydet", None)
            if callable(kaydet_fn):
                try:
                    kaydet_fn(motor)
                    logger.info("[Plugin] '%s' motora kaydedildi", adi)
                except Exception as e:
                    logger.warning("[Plugin] '%s' kayit hatasi: %s", adi, e)

    # ── Plugin bilgisi / listeleme ─────────────────────────────────────────

    def plugin_bilgisi(self, plugin_adi: str) -> dict:
        """Bir pluginin meta bilgisini dondur."""
        modul = self._yuklu.get(plugin_adi)
        yaml_bilgi = self._yaml_bilgisi.get(plugin_adi, {})
        if not modul and not yaml_bilgi:
            return {}
        return {
            "adi": yaml_bilgi.get("name", plugin_adi),
            "aciklama": yaml_bilgi.get("description", getattr(modul, "plugin_aciklamasi", "") if modul else ""),
            "versiyon": yaml_bilgi.get("version", ""),
            "kind": yaml_bilgi.get("kind", "unknown"),
            "yazar": yaml_bilgi.get("author", ""),
            "yuklu": plugin_adi in self._yuklu,
            "araclar": getattr(modul, "plugin_araclar", []) if modul else [],
        }

    def yuklu_pluginler(self) -> list[str]:
        """Yuklu plugin adlarini listele."""
        return list(self._yuklu.keys())

    def tum_pluginler(self) -> list[dict]:
        """Tum pluginlerin ozet bilgisini listele (yuklu olmayanlar dahil)."""
        sonuc = []
        for klasor in self._butun_plugin_klasorleri():
            yaml_veri = self._yaml_bilgisi.get(klasor.name) or {}
            sonuc.append({
                "adi": yaml_veri.get("name", klasor.name),
                "klasor": klasor.name,
                "kind": yaml_veri.get("kind", "unknown"),
                "versiyon": yaml_veri.get("version", ""),
                "aciklama": yaml_veri.get("description", ""),
                "yuklu": klasor.name in self._yuklu,
            })
        return sonuc

    def plugin_kaldir(self, plugin_adi: str) -> bool:
        """Bir pluginin modulunu hafizadan kaldir."""
        if plugin_adi in self._yuklu:
            sys.modules.pop(f"plugins.{plugin_adi}", None)
            del self._yuklu[plugin_adi]
            logger.info("[Plugin] Kaldirildi: %s", plugin_adi)
            return True
        return False

    def yeniden_yukle(self, plugin_adi: str) -> bool:
        """Bir plugini yeniden yukle (once kaldir, sonra yukle)."""
        self.plugin_kaldir(plugin_adi)
        if plugin_adi in self._yaml_bilgisi:
            del self._yaml_bilgisi[plugin_adi]
        return self._yukle(plugin_adi)

    # ── Yardimcilar ────────────────────────────────────────────────────────

    def _butun_plugin_klasorleri(self) -> list[Path]:
        """plugins/ altindaki tum __init__.py + plugin.yaml iceren klasorleri bul (recursive).

        Hem 1. seviye (plugins/web_scraper/) hem de 2. seviye
        (plugins/model-providers/openai/) plugin klasorlerini bulur.
        """
        if not self.dizin.exists():
            return []
        klasorler = []
        gorulen: set[Path] = set()
        for entry in self.dizin.rglob("__init__.py"):
            parent = entry.parent
            if parent in gorulen or parent == self.dizin:
                continue
            if parent.name.startswith("_"):
                continue
            gorulen.add(parent)
            # Sadece __init__.py olanlari al
            klasorler.append(parent)
        return sorted(klasorler, key=lambda p: str(p.relative_to(self.dizin)))

    # ── Hafıza plugin'leri (geriye uyumluluk) ──────────────────────────────

    def hafiza_pluginlerini_yukle(
        self,
        oturum_id: str = "varsayilan",
        tercih: Optional[str] = None,
        **baslat_kwargs,
    ) -> Optional["AbstraktHafizaSaglayici"]:
        """plugins/memory/ altindaki hafiza plugin'lerini aktive et.

        PluginManager ile ayni semantik.
        """
        try:
            from reymen.sistem.plugin_manager import PluginManager
        except ImportError:
            logger.warning("plugin_manager modulu bulunamadi.")
            return None

        if self._hafiza_yoneticisi is None:
            self._hafiza_yoneticisi = PluginManager(str(self.dizin))

        return self._hafiza_yoneticisi.hafiza_pluginlerini_yukle(
            oturum_id=oturum_id,
            tercih=tercih,
            **baslat_kwargs,
        )

    def aktif_hafiza_saglayici(self) -> Optional["AbstraktHafizaSaglayici"]:
        if self._hafiza_yoneticisi is None:
            return None
        return self._hafiza_yoneticisi.aktif_hafiza_saglayici()

    def hafiza_saglayici_listele(self) -> list[str]:
        if self._hafiza_yoneticisi is None:
            return []
        return self._hafiza_yoneticisi.hafiza_saglayici_listele()

    def hafizayi_kapat(self) -> None:
        if self._hafiza_yoneticisi:
            self._hafiza_yoneticisi.hafizayi_kapat()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    yukleyici = PluginYukleyici()
    yuklenenler = yukleyici.hepsini_yukle()
    print(f"Yuklenen backend plugin sayisi: {len(yuklenenler)}")
    for p in yuklenenler:
        bilgi = yukleyici.plugin_bilgisi(p)
        print(f"  - {p}: v{bilgi['versiyon']} | {bilgi['kind']} | {bilgi['aciklama'][:60]}")

    tool_plugins = yukleyici.tool_pluginlerini_yukle()
    print(f"\nYuklenen tool plugin sayisi: {len(tool_plugins)}")
    for p in tool_plugins:
        print(f"  - {p}")

    tumu = yukleyici.tum_pluginler()
    print(f"\nToplam plugin sayisi: {len(tumu)}")

    aktif = yukleyici.hafiza_pluginlerini_yukle(oturum_id="test-001")
    if aktif:
        print(f"\nAktif hafiza saglayici: {aktif.ad}")
    else:
        print("\nHafiza saglayici bulunamadi.")
