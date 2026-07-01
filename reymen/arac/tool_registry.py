# -*- coding: utf-8 -*-
"""tool_registry.py — Gelismis ToolRegistry + check_fn TTL cache + ToolsetManager.

tools/ klasorundeki tum araclari otomatik bulur, kaydeder.
Motor ve sistem_talimati tarafindan kullanilir.

Ozellikler (ReYMeN Agent seviyesi):
  - tools/ otomatik discovery
  - check_fn: TTL cache (30sn), env check
  - ToolsetManager: toolset gruplari yonetimi
  - Dynamic schema overrides
  - Alias sistemi (eski -> yeni ad)
"""

import functools
import importlib
import os
import time
from pathlib import Path
from typing import Any, Callable, Optional
import logging
logger = logging.getLogger(__name__)

TOOLS_DIR = Path(__file__).parent / "tools"

# ── TTL cache yardimcisi ─────────────────────────────────────────────
_CHECK_FN_TTL = 30.0  # saniye


def _ttl_cache(ttl: float = _CHECK_FN_TTL) -> Callable:
    """Basit TTL cache dekoratoru — check_fn sonucunu 30sn cache'ler."""
    def decorator(fn):
        _cache = {"sonuc": None, "zaman": 0.0}
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            now = time.time()
            if _cache["zaman"] > 0 and (now - _cache["zaman"]) < ttl:
                return _cache["sonuc"]
            try:
                _cache["sonuc"] = bool(fn(*args, **kwargs))
            except Exception:
                _cache["sonuc"] = False
            _cache["zaman"] = now
            return _cache["sonuc"]
        wrapper.ttl_tazele = lambda: _cache.update({"zaman": 0.0})  # type: ignore[attr-defined]
        return wrapper
    return decorator


# ── ToolsetManager ────────────────────────────────────────────────────
class ToolsetManager:
    """Toolset gruplari yonetimi — bir arac birden cok toolset'te olabilir.

    Kullanim:
        tm = ToolsetManager()
        tm.toolset_olustur("web", {"WEB_ARA", "TARAYICI_AC"})
        tm.toolset_ekle("web", "URL_FETCHER")
        araclar = tm.toolset_araclari("web")  # {"WEB_ARA", "TARAYICI_AC", "URL_FETCHER"}
    """

    def __init__(self) -> None:
        self._toolsets: dict[str, set[str]] = {}

    def toolset_olustur(self, ad: str, araclar: Optional[set[str]] = None) -> bool:
        """Yeni toolset olustur."""
        if ad in self._toolsets:
            return False
        self._toolsets[ad] = set(araclar or set())
        return True

    def toolset_sil(self, ad: str) -> bool:
        """Toolset'i sil."""
        return self._toolsets.pop(ad, None) is not None

    def toolset_listele(self) -> list[str]:
        """Tum toolset adlarini listele."""
        return sorted(self._toolsets.keys())

    def toolset_ekle(self, ts_ad: str, arac_adi: str) -> bool:
        """Bir araci toolset'e ekle."""
        if ts_ad not in self._toolsets:
            return False
        self._toolsets[ts_ad].add(arac_adi)
        return True

    def toolset_cikar(self, ts_ad: str, arac_adi: str) -> bool:
        """Bir araci toolset'ten cikar."""
        if ts_ad not in self._toolsets:
            return False
        self._toolsets[ts_ad].discard(arac_adi)
        return True

    def toolset_araclari(self, ts_ad: str) -> set[str]:
        """Toolset'teki araclari getir (bos set, toolset yoksa)."""
        return self._toolsets.get(ts_ad, set()).copy()

    def arac_toolsetleri(self, arac_adi: str) -> list[str]:
        """Bir aracin hangi toolset'lerde oldugunu bul."""
        return [ts for ts, araclar in self._toolsets.items() if arac_adi in araclar]

    def toolset_ozet(self) -> dict[str, int]:
        """Toolset ozeti: {ad: arac_sayisi}."""
        return {ad: len(araclar) for ad, araclar in sorted(self._toolsets.items())}


# ── AracMeta (eski veri yapisi, testler icin korunuyor) ──────────────
class AracMeta:
    """Arac meta veri yapisi — backward compatibility icin korunuyor.

    Kullanim:
        meta = AracMeta("TEST", lambda: "ok")
        meta = AracMeta("TEST", lambda: "ok", check_fn=lambda: True)
        meta = AracMeta("TEST", lambda x: x, aciklama="test", risk_seviyesi=2, kategori="test")
    """

    def __init__(
        self,
        ad: str,
        fonk: Callable,
        check_fn: Optional[Callable[[], bool]] = None,
        aciklama: str = "",
        risk_seviyesi: int = 0,
        kategori: str = "",
    ) -> None:
        self.ad = ad
        self.fonk = fonk
        self.check_fn = check_fn
        self.aciklama = aciklama
        self.risk_seviyesi = risk_seviyesi
        self.kategori = kategori

    def musait_mi(self) -> bool:
        """check_fn yoksa her zaman musait, varsa degerlendir."""
        if self.check_fn is None:
            return True
        try:
            return bool(self.check_fn())
        except Exception:
            return False

    def ozet(self) -> dict[str, Any]:
        """Metadata ozet dict'i."""
        return {
            "ad": self.ad,
            "aciklama": self.aciklama,
            "risk": self.risk_seviyesi,
            "kategori": self.kategori,
        }


# ── Ana Registry ─────────────────────────────────────────────────────
class ToolRegistry:
    """Arac kayit defteri — check_fn + TTL cache + toolset + schema.

    Kullanim:
        reg = ToolRegistry()
        reg.kaydet("WEB_ARA", fonk)
        reg.check_fn_ekle("WEB_ARA", lambda: bool(os.environ.get("API_KEY")))
        reg.check_fn_ekle_env("BROWSER", "PLAYWRIGHT_BROWSERS_PATH")

        # Toolset
        reg.toolset_olustur("web", {"WEB_ARA", "URL_FETCHER"})

        # Schema override
        reg.schema_guncelle("WEB_ARA", {"parametreler": [...]})

        # Calistir
        sonuc = reg.calistir("WEB_ARA", "sorgu")
    """

    def __init__(self) -> None:
        self._tools: dict[str, Callable] = {}
        self._aliases: dict[str, str] = {}
        self._check_fns: dict[str, Callable[[], bool]] = {}
        self._meta: dict[str, dict] = {}          # arac_adi -> metadata
        self._schemas: dict[str, dict] = {}       # arac_adi -> schema override
        self.toolset = ToolsetManager()

        # Alias: ReYMeN araclari.
        # Onemli: _plugin_arac_kaydet ile kayitli araclar _tools'ta
        # oldugu icin alias gerektirmez. Bu liste sadece dogrudan
        # import gereken ReYMeN modulleri icindir.
        # ReYMeN tools/ modullerine yonlendiren tum alias'lar
        # kaldirildi — dispatch _fallback_calistir'a duser.
        self._aliases: dict[str, str] = {}
        self._yukle()

    def _yukle(self) -> None:
        """Tools/ klasorundeki tum .py dosyalarini yukle."""
        if not TOOLS_DIR.exists():
            return
        import importlib.util
        for f in sorted(TOOLS_DIR.glob("*.py")):
            if f.name.startswith("_") or f.name == "__init__.py":
                continue
            try:
                mod_name = f"tools_{f.stem}"
                spec = importlib.util.spec_from_file_location(mod_name, f)
                if spec is None or spec.loader is None:
                    continue
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "run"):
                    self._tools[f.stem.upper()] = getattr(mod, "run")
                    # TOOL_META varsa meta'ya ekle
                    if hasattr(mod, "TOOL_META"):
                        self._meta[f.stem.upper()] = getattr(mod, "TOOL_META")
                    # check_fn varsa ekle
                    if hasattr(mod, "check_fn"):
                        self._check_fns[f.stem.upper()] = _ttl_cache()(getattr(mod, "check_fn"))
            except Exception as _tool_reg_e237:
                print(f"[UYARI] tool_registry.py:238 - {_tool_reg_e237}")

    # ── Kayit ──────────────────────────────────────────────────────────

    def kaydet(self, ad: str, fonk: Callable, aciklama: str = "",
               parametreler: Optional[list] = None, kategori: str = "",
               check_fn: Optional[Callable[[], bool]] = None,
               risk_seviyesi: int = 0) -> None:
        """Bir araci dogrudan kaydet (metadata ile)."""
        self._tools[ad] = fonk
        if check_fn is not None:
            self._check_fns[ad] = _ttl_cache()(check_fn)
        meta: dict[str, Any] = {}
        if aciklama:
            meta["aciklama"] = aciklama
        if parametreler:
            meta["parametreler"] = parametreler
        if kategori:
            meta["kategori"] = kategori
        if risk_seviyesi:
            meta["risk"] = risk_seviyesi
        if meta:
            self._meta[ad] = meta

    # ── check_fn ─────────────────────────────────────────────────────

    def check_fn_ekle(self, arac_adi: str, fn: Callable[[], bool]) -> None:
        """Bir araca TTL cache'li check_fn ekle.

        Sonuc 30 saniye cache'lenir. fn her cagrildiginda degil,
        cache suresi dolunca yeniden degerlendirilir.
        """
        self._check_fns[arac_adi] = _ttl_cache()(fn)

    def check_fn_ekle_env(self, arac_adi: str, env_var: str) -> None:
        """Bir aracin kullanilabilirligini env var'a bagla.

        env_var (API anahtari vb.) bos/tanimli degilse arac kullanilamaz.
        ReYMeN Agent'in requires_env pattern'i ile ayni.

        Args:
            arac_adi: Arac adi (ornek: WEB_ARA)
            env_var: .env'deki degisken adi (ornek: OPENROUTER_API_KEY)
        """
        def _env_check() -> bool:
            return bool(os.environ.get(env_var, "").strip())
        self._check_fns[arac_adi] = _ttl_cache()(_env_check)

    def check_fn_kaldir(self, arac_adi: str) -> None:
        """Bir aracin check_fn'ini kaldir (her zaman musait yap)."""
        self._check_fns.pop(arac_adi, None)

    def check_fn_tazele(self, arac_adi: Optional[str] = None) -> None:
        """Bir veya tum check_fn TTL cache'lerini sifirla.

        Args:
            arac_adi: None = tumunu tazele, belirli ad = sadece onu
        """
        if arac_adi:
            fn = self._check_fns.get(arac_adi)
            if fn and hasattr(fn, "ttl_tazele"):
                fn.ttl_tazele()
        else:
            for fn in self._check_fns.values():
                if hasattr(fn, "ttl_tazele"):
                    fn.ttl_tazele()

    def check_fn_kontrol_et(self, arac_adi: str) -> bool:
        """Bir aracin kullanilabilir olup olmadigini kontrol et (TTL cache'li).

        Returns:
            True: kullanilabilir (check_fn yok veya True dondu)
            False: kullanilamaz (check_fn False dondu)
        """
        fn = self._check_fns.get(arac_adi)
        if fn is None:
            return True
        try:
            return bool(fn())
        except Exception:
            return False

    def musait_tools(self) -> dict[str, bool]:
        """Tum araclarin kullanilabilirlik durumunu dondur.

        Returns:
            {arac_adi: True/False}
        """
        durum = {}
        for ad in self._tools:
            durum[ad] = self.check_fn_kontrol_et(ad)
        for alias_ad in self._aliases:
            if alias_ad not in durum:
                durum[alias_ad] = self.check_fn_kontrol_et(alias_ad)
        return durum

    # ── Schema Override ───────────────────────────────────────────────

    def schema_guncelle(self, arac_adi: str, yeni_sema: dict[str, Any]) -> None:
        """Bir aracin parametre semasini calisma zamaninda degistir.

        Args:
            arac_adi: Arac adi
            yeni_sema: Yeni sema dict'i (ornek: {"parametreler": [...], "ornek": "..."})
        """
        self._schemas[arac_adi] = yeni_sema

    def schema_al(self, arac_adi: str) -> Optional[dict]:
        """Bir aracin gecerli semasini getir (override varsa onu, yoksa meta)."""
        if arac_adi in self._schemas:
            return self._schemas[arac_adi]
        return self._meta.get(arac_adi)

    def schema_temizle(self, arac_adi: str) -> None:
        """Schema override'ini kaldir (varsayilana don)."""
        self._schemas.pop(arac_adi, None)

    # ── Calistirma ──────────────────────────────────────────────────────

    def calistir(self, ad: str, *args, **kwargs) -> str:
        """Bir araci adina gore calistir.

        Args:
            ad: Arac adi (WEB_ARA, DOSYA_OKU vb.)
            *args, **kwargs: Araca parametreler

        Returns:
            Sonuc metni
        """
        # 0. check_fn kontrolu
        if not self.check_fn_kontrol_et(ad):
            return f"[KULLANILAMIYOR] '{ad}' araci su an kullanilamiyor."

        # 1. Dogrudan tools/ icinde
        if ad in self._tools:
            try:
                sonuc = self._tools[ad](*args, **kwargs)
                return str(sonuc) if sonuc is not None else "[Tamam]"
            except Exception as e:
                return f"[Hata]: {e}"

        # 2. Alias'tan dene
        alias = self._aliases.get(ad, "")
        if alias:
            parts = alias.split(".")
            try:
                if len(parts) == 2:
                    mod = importlib.import_module(f"tools.{parts[0]}")
                    fonk = getattr(mod, parts[1], None)
                else:
                    mod = importlib.import_module(f"tools.{alias}")
                    fonk = getattr(mod, "run", None)
                    if fonk is None:
                        fonk = self._moduldeki_ilk_callable(alias)
                if fonk:
                    sonuc = fonk(*args, **kwargs)
                    return str(sonuc) if sonuc is not None else "[Tamam]"
            except Exception as e:
                return f"[Hata]: {e}"

        return f"[Bilinmeyen arac] '{ad}'."

    # ── Listeleme ─────────────────────────────────────────────────────

    def liste(self, sadece_musait: bool = False) -> list[str]:
        """Kayitli tum araclari listele.

        Args:
            sadece_musait: True ise sadece check_fn gecenler
        """
        tools = set(self._tools.keys())
        tools.update(self._aliases.keys())
        if sadece_musait:
            return sorted(ad for ad in tools if self.check_fn_kontrol_et(ad))
        return sorted(tools)

    # ── Toolset proxy ────────────────────────────────────────────────

    def toolset_olustur(self, ad: str, araclar: Optional[set[str]] = None) -> bool:
        return self.toolset.toolset_olustur(ad, araclar)

    def toolset_araclari(self, ad: str) -> set[str]:
        return self.toolset.toolset_araclari(ad)

    # ── Yardimci ─────────────────────────────────────────────────────

    def _moduldeki_ilk_callable(self, mod_name: str) -> Optional[Callable]:
        try:
            mod = importlib.import_module(f"tools.{mod_name}")
        except Exception:
            return None
        for candidate in ("ping", "run"):
            if hasattr(mod, candidate):
                return getattr(mod, candidate)
        funcs = [getattr(mod, n) for n in dir(mod)
                 if callable(getattr(mod, n)) and not n.startswith("_")]
        return funcs[0] if funcs else None

    def resolve(self, ad: str) -> Optional[dict[str, str]]:
        """Arac adini gercek modul/cagriya cevir."""
        if not ad:
            return None
        anahtar = ad.strip().upper()
        if anahtar in self._tools:
            fonk = self._tools[anahtar]
            return {"module": anahtar.lower(), "callable": "run", "fonk": fonk.__name__ if hasattr(fonk, "__name__") else "run"}
        alias = self._aliases.get(anahtar)
        if alias:
            parts = alias.split(".")
            if len(parts) == 2:
                return {"module": parts[0], "callable": parts[1], "fonk": parts[1]}
            callable_name = self._moduldeki_ilk_callable(alias)
            fn_name = callable_name.__name__ if callable_name else "run"
            return {"module": alias, "callable": fn_name, "fonk": fn_name}
        mod_name = ad.strip().lower()
        if (TOOLS_DIR / f"{mod_name}.py").exists():
            callable_name = self._moduldeki_ilk_callable(mod_name)
            fn_name = callable_name.__name__ if callable_name else "run"
            return {"module": mod_name, "callable": fn_name, "fonk": fn_name}
        return None

    def durum(self) -> str:
        """Registry durum raporu."""
        yuklu = len(self._tools)
        alias_sayisi = len(self._aliases)
        check_count = len(self._check_fns)
        toolset_sayisi = len(self.toolset.toolset_listele())
        musait = sum(1 for v in self.musait_tools().values() if v)
        return (
            f"[Registry] {yuklu} arac, {alias_sayisi} alias, "
            f"{check_count} check_fn, {toolset_sayisi} toolset = "
            f"{yuklu + alias_sayisi} toplam ({musait} musait)"
        )

    # ── Backward-compat metodlar (eski AracMeta/test API) ────────────

    def musait_mi(self, arac_adi: str) -> bool:
        """Bir aracin kullanilabilir olup olmadigini kontrol et.

        Test ve eski API uyumlulugu icin. check_fn_kontrol_et'e delegasyon.
        """
        return self.check_fn_kontrol_et(arac_adi)

    def musait_araclar(self, kategori: Optional[str] = None) -> list[str]:
        """Kullanilabilir araclari listele, istege bagli kategori filtresiyle.

        Args:
            kategori: Sadece bu kategorideki araclari getir (None = tumu)

        Returns:
            Musait arac adlarinin listesi
        """
        sonuc: list[str] = []
        for ad in self._tools:
            if not self.check_fn_kontrol_et(ad):
                continue
            if kategori:
                meta = self._meta.get(ad, {})
                if isinstance(meta, dict) and meta.get("kategori") != kategori:
                    continue
            sonuc.append(ad)
        return sorted(sonuc)

    def arac_meta(self, arac_adi: str) -> Optional[dict[str, Any]]:
        """Bir aracin metadata dict'ini getir.

        Returns:
            {"ad": ..., "musait": ..., ...} veya None
        """
        if arac_adi not in self._tools:
            return None
        meta = self._meta.get(arac_adi, {}).copy()
        if not isinstance(meta, dict):
            meta = {}
        meta["ad"] = arac_adi
        meta["musait"] = self.check_fn_kontrol_et(arac_adi)
        return meta

    def listele_kategori(self) -> dict[str, list[str]]:
        """Araclari kategorilerine gre grupla.

        Returns:
            {kategori_adi: [arac_adi, ...], ...}
        """
        gruplar: dict[str, list[str]] = {}
        for ad in self._tools:
            meta = self._meta.get(ad, {})
            kat = meta.get("kategori", "") if isinstance(meta, dict) else ""
            if not kat:
                kat = "diger"
            gruplar.setdefault(kat, []).append(ad)
        return gruplar

    def detayli_liste(self) -> list[dict[str, Any]]:
        """Tum araclarin detayli metadata listesi.

        Returns:
            [{"ad": ..., "aciklama": ..., "risk": ..., "musait": ...}, ...]
        """
        sonuc: list[dict[str, Any]] = []
        for ad in sorted(self._tools):
            meta = self._meta.get(ad, {})
            if not isinstance(meta, dict):
                meta = {}
            sonuc.append({
                "ad": ad,
                "aciklama": meta.get("aciklama", ""),
                "risk": meta.get("risk", 0),
                "musait": self.check_fn_kontrol_et(ad),
            })
        return sonuc


if __name__ == "__main__":
    r = ToolRegistry()
    print("=== ToolRegistry Test ===")
    print(r.durum())
    print(f"Tools: {len(r.liste())}")
    print(f"Musait: {sum(1 for v in r.musait_tools().values() if v)}")

    # TTL cache test
    call_sayisi = [0]
    def test_check():
        call_sayisi[0] += 1
        return True
    r.kaydet("TTL_TESTCACHE", lambda: "ok")
    r.check_fn_ekle("TTL_TESTCACHE", test_check)
    r.check_fn_kontrol_et("TTL_TESTCACHE")  # 1. cagri
    r.check_fn_kontrol_et("TTL_TESTCACHE")  # cached
    assert call_sayisi[0] == 1, f"TTL cache calismadi: {call_sayisi[0]}"
    r.check_fn_tazele("TTL_TESTCACHE")
    r.check_fn_kontrol_et("TTL_TESTCACHE")  # 2. cagri (cache temiz)
    assert call_sayisi[0] == 2, f"TTL tazeleme calismadi: {call_sayisi[0]}"
    print("[OK] TTL Cache calisiyor")

    # Toolset test
    ts = r.toolset_olustur("test_toolset", {"TTL_TESTCACHE"})
    assert ts, "toolset_olustur basarisiz"
    assert "TTL_TESTCACHE" in r.toolset_araclari("test_toolset")
    print("[OK] ToolsetManager calisiyor")

    # Schema override test
    r.schema_guncelle("TTL_TESTCACHE", {"custom": "schema", "parametreler": []})
    sema = r.schema_al("TTL_TESTCACHE")
    assert sema == {"custom": "schema", "parametreler": []}, f"Schema override basarisiz: {sema}"
    print("[OK] Schema Override calisiyor")

    # Env check test
    os.environ["TEST_REYMEN_KEY"] = "value123"
    r.check_fn_ekle_env("TTL_TESTCACHE", "TEST_REYMEN_KEY")
    assert r.check_fn_kontrol_et("TTL_TESTCACHE"), "Env check: var varken True olmali"
    del os.environ["TEST_REYMEN_KEY"]
    r.check_fn_tazele("TTL_TESTCACHE")
    assert not r.check_fn_kontrol_et("TTL_TESTCACHE"), "Env check: yokken False olmali"
    os.environ["TEST_REYMEN_KEY"] = "value123"  # restore
    print("[OK] Env Check calisiyor")

    print(f"\n{r.durum()}")
    print("[OK] Tum testler gecti!")

# Singleton
tool_registry = ToolRegistry()
