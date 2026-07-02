# -*- coding: utf-8 -*-
"""prompt_assembly.py — Sistem prompt'u tek noktadan topla.

Hedef yapi:
    system_prompt = config.yaml → SOUL.md → USER.md

conversation_loop ve diger moduller buradan okur, kendi icinde
sabit string tutmaz. SOUL.md ve USER.md diskten her defasinda
okunmaz — lru_cache ile bir kez yuklenir, bellekten servis edilir.

Yol bilgileri:
    SOUL.md  → ~/.hermes/profiles/<profil>/SOUL.md (oncelikli)
              veya proje kokundeki SOUL.md (fallback)
    USER.md  → reymen/hafiza/USER.md
    config   → proje kokundeki config.yaml
"""

import functools
import logging
import os
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# ── Varsayilan yollar ──────────────────────────────────────────────────
_PROJE_KOKU = Path(__file__).resolve().parent.parent.parent  # ReYMeN-Ajan/
_VARSAYILAN_USER_MD = _PROJE_KOKU / "reymen" / "hafiza" / "USER.md"
_VARSAYILAN_SOUL_MD = _PROJE_KOKU / "SOUL.md"
_VARSAYILAN_CONFIG = _PROJE_KOKU / "config.yaml"

# ReYMeN profil SOUL.md (varsa oncelikli)
_REYMEN_PROFIL = Path(os.environ.get("LOCALAPPDATA", "")) / "reymen" / "profiles" / "reymen" / "SOUL.md"


def _profil_soul_yolu() -> Path:
    """Profil SOUL.md yolunu dondur; yoksa proje kokundekini dene."""
    yol = Path(str(_REYMEN_PROFIL))
    if yol.exists():
        return yol
    if _VARSAYILAN_SOUL_MD.exists():
        return _VARSAYILAN_SOUL_MD
    return yol  # yoksa bile dondur, cagiran handle etsin


@functools.lru_cache(maxsize=1)
def _dosya_oku(yol: Path) -> str:
    """Dosyayi oku, yoksa bos string dondur. lru_cache ile bellekte tut."""
    try:
        if yol.exists():
            icerik = yol.read_text(encoding="utf-8").strip()
            log.debug("PromptAssembly: %s okundu (%d chars)", yol.name, len(icerik))
            return icerik
        else:
            log.debug("PromptAssembly: %s bulunamadi, atlaniyor", yol)
            return ""
    except Exception as e:
        log.warning("PromptAssembly: %s okuma hatasi: %s", yol, e)
        return ""


def _config_prompt_al() -> str:
    """config.yaml'dan agent.system_prompt veya general.default_system_prompt
    degerini oku. Yoksa bos string doner."""
    try:
        import yaml
        yol = _VARSAYILAN_CONFIG
        if yol.exists():
            with open(yol, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            if not cfg:
                return ""
            aranacak = [
                cfg.get("agent", {}).get("default_system_prompt"),
                cfg.get("general", {}).get("default_system_prompt"),
                cfg.get("personality", None),
            ]
            for val in aranacak:
                if val and isinstance(val, str) and val.strip():
                    return val.strip()
            # agent.personalities altinda 'default' key'i varsa
            personalities = cfg.get("agent", {}).get("personalities", {})
            if isinstance(personalities, dict):
                default_p = personalities.get("default", {})
                if isinstance(default_p, dict) and default_p.get("system_prompt"):
                    return default_p["system_prompt"].strip()
        return ""
    except ImportError:
        log.debug("PromptAssembly: yaml modulu yok, config atlandi")
        return ""
    except Exception as e:
        log.debug("PromptAssembly: config okuma hatasi (goz ardi): %s", e)
        return ""


def sistem_prompt_al(tema: Optional[str] = None, ek_bilgi: str = "") -> str:
    """Sistem prompt'unu config→SOUL.md→USER.md sirasiyla birlestir.

    Args:
        tema:    Opsiyonel tema/task bilgisi (en alta eklenir).
        ek_bilgi: Opsiyonel ek baglam metni.

    Returns:
        Birlestirilmis sistem prompt metni.
    """
    bolumler: list[str] = []

    # 1. Config prompt (varsa)
    config_prompt = _config_prompt_al()
    if config_prompt:
        bolumler.append(config_prompt)

    # 2. SOUL.md — kisilik/identity
    soul_yol = _profil_soul_yolu()
    soul = _dosya_oku(soul_yol)
    if soul:
        bolumler.append(soul)

    # 3. USER.md — kullanici profili
    user = _dosya_oku(_VARSAYILAN_USER_MD)
    if user:
        bolumler.append(f"## Kullanici Profili\n{user}")

    # 4. Tema (opsiyonel)
    if tema:
        bolumler.append(f"## Mevcut Gorev\n{tema}")

    # 5. Ek bilgi (opsiyonel)
    if ek_bilgi:
        bolumler.append(f"## Ek Baglam\n{ek_bilgi}")

    if not bolumler:
        # Hicbiri yoksa minimum fallback
        return "Sen ReYMeN, otonom bir yazilim ajanisin. Hedefe odaklan, araclari kullan, Turkce yaz."

    sonuc = "\n\n".join(bolumler)
    log.debug("PromptAssembly: sistem prompt olusturuldu (%d chars)", len(sonuc))
    return sonuc


class PromptAssemblyEngine:
    """PromptAssemblyEngine — `sistem_prompt_al` fonksiyonlarini class arayuzuyle saran katman.

    Kullanim:
        engine = PromptAssemblyEngine(bounded_memory=..., learning_loop=...)
        prompt = engine.sistem_prompt_al(tema="...")
        engine.cache_tazele()
    """

    def __init__(self, bounded_memory=None, learning_loop=None):
        self.bounded_memory = bounded_memory
        self.learning_loop = learning_loop
        log.debug("PromptAssemblyEngine baslatildi (bounded_memory=%s, learning_loop=%s)",
                  bounded_memory is not None, learning_loop is not None)

    def sistem_prompt_al(self, tema: Optional[str] = None, ek_bilgi: str = "") -> str:
        """sistem_prompt_al fonksiyonuna yonlendir."""
        return sistem_prompt_al(tema=tema, ek_bilgi=ek_bilgi)

    def cache_tazele(self) -> None:
        """Onbellekleri temizle."""
        cache_tazele()

    def kaynak_dosyalari(self) -> dict:
        """Debug icin kaynak dosya yollari."""
        return _kaynak_dosyalari()

    def insa_et(self, hedef: str, son_gozlem: str = "",
                 tur: int = 1, toplam_tur: int = 15,
                 ic_gozlem_modu: bool = False) -> str:
        """_sistem_promptu_insa_et fallback'i — prompt_assembly'den sistem prompt'u al.

        Bu fonksiyon `AIAgentOrchestrator._sistem_promptu_insa_et()` tarafindan
        PromptBuilder ve _sistem_talimati_fn yoksa cagrilir.
        """
        tema = hedef
        if son_gozlem:
            tema += f"\n\n[Son Gozlem]\n{son_gozlem[:500]}"
        ek = f"Tur {tur}/{toplam_tur}"
        if ic_gozlem_modu:
            ek += "\n[Ic Gozlem Modu]"
        return sistem_prompt_al(tema=tema, ek_bilgi=ek)


def cache_tazele() -> None:
    """SOUL.md/USER.md onbelleklerini sifirla (disk'ten tekrar okunur)."""
    _dosya_oku.cache_clear()
    log.info("PromptAssembly onbellekleri temizlendi")


def _kaynak_dosyalari() -> dict:
    """Debug icin: hangi dosyalardan okundugunu goster."""
    return {
        "config": str(_VARSAYILAN_CONFIG),
        "soul": str(_profil_soul_yolu()),
        "user": str(_VARSAYILAN_USER_MD),
    }
