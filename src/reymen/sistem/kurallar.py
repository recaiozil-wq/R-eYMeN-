# -*- coding: utf-8 -*-
"""kurallar.py — ReYMeN Kural/İzin Yönetim Motoru (Rules Engine).

Policy katmani: mevcut guvenlik/ modullerinin uzerine ek bir kontrol
katmani saglar. Her aksiyon (dosya erisimi, ag cagrisi, komut calistirma,
API cagrisi) oncesinde kurallar kontrol edilir.

Kullanim:
    from reymen.sistem.kurallar import RulesEngine
    engine = RulesEngine()
    engine.kontrol("dosya_erisim", {"yol": "/etc/passwd"})
    # => {"izin": False, "sebep": "Engellendi: kritik dosya", "kural": "..."}

Kural dosyasi: .ReYMeN/kurallar.yaml
Format:
    rules:
      - id: "ornek-1"
        kategori: dosya_erisim
        tip: engel          # izin / engel / uyari
        desen: "/etc/shadow"
        sebep: "Kritik sistem dosyasi"
        aktif: true

Komut satiri:
    reymen kural list
    reymen kural ekle <kategori> <tip> <desen> [--sebep "..." --id ID]
    reymen kural sil <id>
    reymen kural kontrol <kategori> <hedef>
"""

import json
import logging
import os
import re
import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Varsayilan kural dosyasi yolu
_PROJE_KOK = Path(__file__).resolve().parent.parent.parent.parent
_RULES_YOLU = _PROJE_KOK / ".ReYMeN" / "kurallar.yaml"

# Gecerli kategoriler
KATEGORILER = {"dosya_erisim", "ag", "komut", "api_cagrisi", "guvenlik"}

# Gecerli kural tipleri
KURAL_TIPLERI = {"izin", "engel", "uyari"}

# ── Varsayilan kurallar (built-in, her zaman aktif) ──────────────────
VARSAYILAN_KURALLAR = [
    {
        "id": "builtin-kritik-dosya",
        "kategori": "dosya_erisim",
        "tip": "engel",
        "desen": "**/etc/shadow",
        "sebep": "Kritik sistem dosyasi (shadow)",
        "aktif": True,
    },
    {
        "id": "builtin-kritik-dosya-passwd",
        "kategori": "dosya_erisim",
        "tip": "engel",
        "desen": "**/etc/passwd",
        "sebep": "Kritik sistem dosyasi (passwd)",
        "aktif": True,
    },
    {
        "id": "builtin-kritik-env",
        "kategori": "dosya_erisim",
        "tip": "engel",
        "desen": "**/.env",
        "sebep": ".env dosyasi API anahtarlari icerir",
        "aktif": True,
    },
    {
        "id": "builtin-silme-korumali",
        "kategori": "komut",
        "tip": "uyari",
        "desen": "rm -rf /",
        "sebep": "Tum sistemi silme komutu",
        "aktif": True,
    },
    {
        "id": "builtin-ag-disari",
        "kategori": "ag",
        "tip": "izin",
        "desen": "api.deepseek.com",
        "sebep": "DeepSeek API erisimi",
        "aktif": True,
    },
    {
        "id": "builtin-ag-openrouter",
        "kategori": "ag",
        "tip": "izin",
        "desen": "openrouter.ai",
        "sebep": "OpenRouter API erisimi",
        "aktif": True,
    },
]


def rules_yolu_bul() -> Path:
    """Kural dosyasinin yolunu don. Yoksa olustur."""
    _RULES_YOLU.parent.mkdir(parents=True, exist_ok=True)
    return _RULES_YOLU


def rules_yukle() -> List[Dict[str, Any]]:
    """Kural dosyasindaki kurallari yukle. Yoksa varsayilanlari olustur."""
    yol = rules_yolu_bul()
    if not yol.exists():
        # Varsayilan kurallari yaz
        import yaml
        with open(yol, "w", encoding="utf-8") as f:
            yaml.dump({"rules": VARSAYILAN_KURALLAR}, f, allow_unicode=True, default_flow_style=False)
        logger.info("[Kurallar] Varsayilan kurallar olusturuldu: %s", yol)
        return list(VARSAYILAN_KURALLAR)

    try:
        import yaml
        with open(yol, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        rules = data.get("rules", [])
        if not rules:
            rules = list(VARSAYILAN_KURALLAR)
            rules_kaydet(rules)
        return rules
    except Exception as e:
        logger.warning("[Kurallar] Yukleme hatasi: %s, varsayilanlar kullaniliyor", e)
        return list(VARSAYILAN_KURALLAR)


def rules_kaydet(kurallar: List[Dict[str, Any]]) -> bool:
    """Kurallari dosyaya kaydet."""
    try:
        yol = rules_yolu_bul()
        import yaml
        with open(yol, "w", encoding="utf-8") as f:
            yaml.dump({"rules": kurallar}, f, allow_unicode=True, default_flow_style=False)
        return True
    except Exception as e:
        logger.error("[Kurallar] Kaydetme hatasi: %s", e)
        return False


def desen_esles(desen: str, hedef: str) -> bool:
    """Bir desenin hedefle eslesip eslesmedigini kontrol et.
    
    Desteklenen desenler:
      - Tam eslesme: "/etc/passwd"
      - Wildcard: "**/etc/*", "*.exe"
      - Regex: "re:\\\\/etc\\\\/.*" (re: on eki ile)
    """
    if not desen or not hedef:
        return False

    # Regex deseni
    if desen.startswith("re:"):
        try:
            return bool(re.search(desen[3:], hedef))
        except re.error:
            return False

    # fnmatch (wildcard) — **/ for recursive matching
    if "**" in desen:
        # **/xxx -> herhangi bir dizinde xxx
        parts = desen.split("**/")
        if len(parts) == 2:
            return fnmatch.fnmatch(hedef, parts[1]) or fnmatch.fnmatch(hedef, "**/" + parts[1])
    
    # Standart fnmatch
    return fnmatch.fnmatch(hedef, desen)


class RulesEngine:
    """Kural/izin yonetim motoru.
    
    Mevcut guvenlik/ modullerinin uzerine policy katmani olarak calisir.
    """
    
    def __init__(self, rules_file: Optional[Path] = None):
        self._rules_file = rules_file or _RULES_YOLU
        self._rules: List[Dict[str, Any]] = []
        self._aktif = True
        self.yeniden_yukle()
    
    def yeniden_yukle(self) -> int:
        """Kurallari yeniden yukle. Kural sayisini don."""
        self._rules = rules_yukle()
        # Config'ten aktif/pasif durumunu kontrol et
        try:
            from reymen_launcher import _KOK
            config_yol = _KOK / "config.yaml"
            if config_yol.exists():
                import yaml
                with open(config_yol, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                rules_cfg = cfg.get("rules", {})
                if isinstance(rules_cfg, dict):
                    self._aktif = rules_cfg.get("enabled", True)
        except Exception:
            pass
        return len(self._rules)
    
    @property
    def kural_sayisi(self) -> int:
        return len(self._rules)
    
    @property
    def aktif(self) -> bool:
        return self._aktif
    
    def kural_bul(self, kural_id: str) -> Optional[Dict[str, Any]]:
        """ID'ye gore kural bul."""
        for k in self._rules:
            if k.get("id") == kural_id:
                return k
        return None
    
    def kural_ekle(self, kategori: str, tip: str, desen: str,
                   sebep: str = "", kural_id: Optional[str] = None) -> Tuple[bool, str]:
        """Yeni kural ekle.
        
        Returns:
            (basarili, mesaj)
        """
        # Dogrulama
        if kategori not in KATEGORILER:
            return False, f"Gecersiz kategori: {kategori}. Secenekler: {', '.join(sorted(KATEGORILER))}"
        if tip not in KURAL_TIPLERI:
            return False, f"Gecersiz tip: {tip}. Secenekler: {', '.join(sorted(KURAL_TIPLERI))}"
        if not desen or not desen.strip():
            return False, "Desen bos olamaz"
        
        # ID olustur
        if not kural_id:
            import uuid
            kural_id = f"kural-{str(uuid.uuid4())[:8]}"
        
        # Tekrar kontrol
        if self.kural_bul(kural_id):
            return False, f"Bu ID ile kural zaten var: {kural_id}"
        
        yeni_kural = {
            "id": kural_id,
            "kategori": kategori,
            "tip": tip,
            "desen": desen.strip(),
            "sebep": sebep or f"{tip}: {desen}",
            "aktif": True,
            "olusturma": datetime.now().isoformat(),
        }
        self._rules.append(yeni_kural)
        rules_kaydet(self._rules)
        logger.info("[Kurallar] Kural eklendi: %s (%s/%s)", kural_id, kategori, tip)
        return True, f"Kural eklendi: {kural_id} ({kategori}/{tip})"
    
    def kural_sil(self, kural_id: str) -> Tuple[bool, str]:
        """Kural sil (builtin korumali)."""
        kural = self.kural_bul(kural_id)
        if not kural:
            return False, f"Kural bulunamadi: {kural_id}"
        
        # Built-in kurallar silinemez
        if kural_id.startswith("builtin-"):
            return False, f"Built-in kural silinemez: {kural_id}"
        
        self._rules = [k for k in self._rules if k.get("id") != kural_id]
        rules_kaydet(self._rules)
        logger.info("[Kurallar] Kural silindi: %s", kural_id)
        return True, f"Kural silindi: {kural_id}"
    
    def kural_guncelle(self, kural_id: str, **kwargs) -> Tuple[bool, str]:
        """Kural guncelle (aktif/pasif, sebep vb.)."""
        kural = self.kural_bul(kural_id)
        if not kural:
            return False, f"Kural bulunamadi: {kural_id}"
        
        for anahtar, deger in kwargs.items():
            if anahtar in ("aktif", "sebep", "tip", "desen"):
                kural[anahtar] = deger
        
        rules_kaydet(self._rules)
        return True, f"Kural guncellendi: {kural_id}"
    
    def kontrol(self, kategori: str, hedef: Any = None,
                baglam: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Bir aksiyonu kurallara gore kontrol et.
        
        Args:
            kategori: Kural kategorisi (dosya_erisim, ag, komut, api_cagrisi, guvenlik)
            hedef: Kontrol edilecek hedef (string veya dict)
            baglam: Ek baglam bilgisi (opsiyonel)
        
        Returns:
            {
                "izin": True/False,
                "sebep": "...",
                "kural": "...",
                "tip": "izin"/"engel"/"uyari",
                "kural_id": "..."
            }
        """
        if not self._aktif:
            return {"izin": True, "sebep": "Kural motoru pasif", "kural": None, "tip": None, "kural_id": None}
        
        if kategori not in KATEGORILER:
            return {"izin": True, "sebep": f"Bilinmeyen kategori: {kategori}", "kural": None, "tip": None, "kural_id": None}
        
        # Hedefi string'e cevir
        hedef_str = str(hedef) if hedef is not None else ""
        
        # Tum aktif kurallari kontrol et
        for kural in self._rules:
            if not kural.get("aktif", True):
                continue
            if kural.get("kategori") != kategori:
                continue
            
            desen = kural.get("desen", "")
            if not desen_esles(desen, hedef_str):
                continue
            
            tip = kural.get("tip", "engel")
            kural_id = kural.get("id", "?")
            sebep = kural.get("sebep", f"Kural eslesmesi: {desen}")
            
            if tip == "engel":
                logger.info("[Kurallar] ENGEL: %s eslesti (%s) — %s", kural_id, desen, sebep)
                return {"izin": False, "sebep": f"Engellendi: {sebep}", "kural": desen, "tip": tip, "kural_id": kural_id}
            
            elif tip == "uyari":
                logger.info("[Kurallar] UYARI: %s eslesti (%s) — %s", kural_id, desen, sebep)
                return {"izin": True, "sebep": f"Uyari: {sebep}", "kural": desen, "tip": tip, "kural_id": kural_id}
            
            # tip == "izin": bu desene izin ver, ama diger kurallara bakmaya devam et
            # (izin kurallari "allowlist" gibi calisir - eslesirse bypass)
        
        return {"izin": True, "sebep": "Kural eslesmesi yok", "kural": None, "tip": None, "kural_id": None}
    
    def toplu_kontrol(self, kontroller: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Birden fazla kontrolu tek seferde yap."""
        return [self.kontrol(k.get("kategori", ""), k.get("hedef"), k.get("baglam")) for k in kontroller]
    
    def kategorileri_listele(self) -> Dict[str, List[Dict[str, Any]]]:
        """Kurallari kategorilere gore grupla."""
        gruplanmis: Dict[str, List[Dict[str, Any]]] = {k: [] for k in KATEGORILER}
        for kural in self._rules:
            kat = kural.get("kategori", "guvenlik")
            if kat in gruplanmis:
                gruplanmis[kat].append(kural)
            else:
                gruplanmis[kat] = [kural]
        return gruplanmis
    
    def kural_listele(self, kategori: Optional[str] = None,
                      tip: Optional[str] = None,
                      sadece_aktif: bool = False) -> List[Dict[str, Any]]:
        """Kurallari filtreleyerek listele."""
        sonuc = list(self._rules)
        if kategori and kategori in KATEGORILER:
            sonuc = [k for k in sonuc if k.get("kategori") == kategori]
        if tip and tip in KURAL_TIPLERI:
            sonuc = [k for k in sonuc if k.get("tip") == tip]
        if sadece_aktif:
            sonuc = [k for k in sonuc if k.get("aktif", True)]
        return sonuc


# ── Singleton ──────────────────────────────────────────────────────────
_ENGINE_INSTANCE: Optional[RulesEngine] = None


def engine_al() -> RulesEngine:
    """RulesEngine singleton'ini al."""
    global _ENGINE_INSTANCE
    if _ENGINE_INSTANCE is None:
        _ENGINE_INSTANCE = RulesEngine()
    return _ENGINE_INSTANCE


def engine_sifirla() -> None:
    """Singleton'i sifirla (test/tazeleme icin)."""
    global _ENGINE_INSTANCE
    _ENGINE_INSTANCE = None


# ── CLI Handler ────────────────────────────────────────────────────────
def cmd_kural(args) -> int:
    """'reymen kural' CLI komutu handler'i.
    
    Kullanim:
        reymen kural list [--kategori X] [--tip Y] [--aktif]
        reymen kural ekle <kategori> <tip> <desen> [--sebep S] [--id ID]
        reymen kural sil <id>
        reymen kural kontrol <kategori> <hedef>
    """
    engine = engine_al()
    alt = getattr(args, "kural_sub", None) or "list"
    
    _R = "\033[0m"
    _C = "\033[96m"
    _G = "\033[92m"
    _Y = "\033[93m"
    _D = "\033[2m"
    _RED = "\033[91m"
    
    if alt == "list":
        kategori = getattr(args, "kategori", None)
        tip = getattr(args, "tip", None)
        sadece_aktif = getattr(args, "aktif", False)
        
        kurallar = engine.kural_listele(kategori=kategori, tip=tip, sadece_aktif=sadece_aktif)
        
        if not kurallar:
            print(f"  {_Y}!{_R} Kural bulunamadi")
            return 0
        
        print(f"\n  {_C}ReYMeN Kurallar ({len(kurallar)} adet){_R}")
        print(f"  {_D}{'─'*60}{_R}")
        
        gruplu = sorted(kurallar, key=lambda k: (k.get("kategori", ""), k.get("tip", "")))
        for k in gruplu:
            aktif_str = f"{_G}AKTIF{_R}" if k.get("aktif", True) else f"{_D}PASIF{_R}"
            tip_str = {
                "engel": f"{_RED}ENGEL{_R}",
                "izin": f"{_G}IZIN{_R}",
                "uyari": f"{_Y}UYARI{_R}",
            }.get(k.get("tip", ""), k.get("tip", ""))
            
            print(f"  {_C}{k.get('id', '?'):<22}{_R} "
                  f"{k.get('kategori', ''):<14} "
                  f"{tip_str:<8} "
                  f"{aktif_str:<8} "
                  f"{_D}{k.get('desen', '')}{_R}")
            if k.get("sebep"):
                print(f"  {'':22} {_D}→ {k['sebep']}{_R}")
        print()
        return 0
    
    elif alt == "ekle":
        kategori = getattr(args, "kategori", None)
        tip = getattr(args, "tip", None)
        desen = getattr(args, "desen", None)
        sebep = getattr(args, "sebep", "")
        kural_id = getattr(args, "id", None)
        
        if not kategori or not tip or not desen:
            print(f"  {_RED}[HATA]{_R} Kategori, tip ve desen gerekli")
            return 1
        
        basarili, mesaj = engine.kural_ekle(kategori, tip, desen, sebep=sebep, kural_id=kural_id)
        if basarili:
            print(f"  {_G}✓{_R} {mesaj}")
            return 0
        else:
            print(f"  {_RED}[HATA]{_R} {mesaj}")
            return 1
    
    elif alt == "sil":
        kural_id = getattr(args, "kural_id", None)
        if not kural_id:
            print(f"  {_RED}[HATA]{_R} Kural ID'si gerekli")
            return 1
        
        basarili, mesaj = engine.kural_sil(kural_id)
        if basarili:
            print(f"  {_G}✓{_R} {mesaj}")
            return 0
        else:
            print(f"  {_RED}[HATA]{_R} {mesaj}")
            return 1
    
    elif alt == "kontrol":
        kategori = getattr(args, "kategori", None)
        hedef = getattr(args, "hedef", None)
        
        if not kategori or not hedef:
            print(f"  {_RED}[HATA]{_R} Kategori ve hedef gerekli")
            return 1
        
        sonuc = engine.kontrol(kategori, hedef)
        if sonuc.get("izin"):
            if sonuc.get("tip") == "uyari":
                print(f"  {_Y}⚠{_R} UYARI: {sonuc.get('sebep', '')}")
            else:
                print(f"  {_G}✓{_R} IZIN VERILDI ({sonuc.get('sebep', '')})")
        else:
            print(f"  {_RED}✗{_R} ENGELLENDI: {sonuc.get('sebep', '')}")
        if sonuc.get("kural_id"):
            print(f"  {_D}Kural: {sonuc['kural_id']} ({sonuc.get('kural', '')}){_R}")
        return 0
    
    else:
        print(f"  {_RED}[HATA]{_R} Bilinmeyen alt komut: {alt}")
        print(f"  Kullanim: reymen kural (list|ekle|sil|kontrol)")
        return 1
