# -*- coding: utf-8 -*-
"""
surekli_ogrenme.py — Session''lar arası sürekli öğrenme (Continuous Learning).
"""

from __future__ import annotations
import json, logging, os, re
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger(__name__)
PROJE_KOK = Path(__file__).resolve().parent.parent.parent
OGRENME_DOSYASI = PROJE_KOK / ".ReYMeN" / "ogrenmeler.jsonl"
MAKS_KAYIT = 500

class Ogrenme:
    def __init__(self, alan: str, icerik: str, kaynak: str = "manuel", etiketler: list[str] = None):
        self.zaman = datetime.now().isoformat()
        self.alan = alan
        self.icerik = icerik
        self.kaynak = kaynak
        self.etiketler = etiketler or []
    def to_dict(self) -> dict:
        return {"zaman": self.zaman, "alan": self.alan, "icerik": self.icerik, "kaynak": self.kaynak, "etiketler": self.etiketler}
    @classmethod
    def from_dict(cls, d: dict) -> "Ogrenme":
        o = cls(d["alan"], d["icerik"], d.get("kaynak", "?"), d.get("etiketler", []))
        o.zaman = d.get("zaman", o.zaman)
        return o

class OgrenmeDeposu:
    def __init__(self, dosya: Path = None):
        self._dosya = dosya or OGRENME_DOSYASI
        self._dosya.parent.mkdir(parents=True, exist_ok=True)
    def kaydet(self, o: Ogrenme) -> bool:
        try:
            with open(self._dosya, "a", encoding="utf-8") as f:
                f.write(json.dumps(o.to_dict(), ensure_ascii=False) + "\n")
            self._temizle(); return True
        except: return False
    def hepsini_getir(self, alan: str = None, limit: int = 50) -> list:
        if not self._dosya.exists(): return []
        sonuc = []
        try:
            with open(self._dosya, "r", encoding="utf-8") as f:
                for satir in f:
                    s = satir.strip()
                    if not s: continue
                    try:
                        o = Ogrenme.from_dict(json.loads(s))
                        if alan and o.alan != alan: continue
                        sonuc.append(o)
                    except Exception:
                        logger.debug("[Ogrenme] Kayit cozulemedi, atlandi")
                        continue
        except Exception as e:
            logger.warning("[Ogrenme] hepsini_getir hatasi: %s", e)
        return sonuc[-limit:]
    def alan_listesi(self) -> list[str]:
        a = set()
        for o in self.hepsini_getir(limit=10000):
            if o.alan: a.add(o.alan)
        return sorted(a)
    def sayi(self) -> int:
        if not self._dosya.exists(): return 0
        try: return sum(1 for s in open(self._dosya, "r", encoding="utf-8") if s.strip())
        except Exception as e:
            logger.warning("[Ogrenme] sayi hatasi: %s", e)
            return 0
    def _temizle(self):
        if not self._dosya.exists(): return
        try:
            with open(self._dosya, "r", encoding="utf-8") as f:
                satirlar = [s for s in f.read().split("\n") if s.strip()]
            if len(satirlar) <= MAKS_KAYIT: return
            with open(self._dosya, "w", encoding="utf-8") as f:
                for s in satirlar[-MAKS_KAYIT:]: f.write(s + "\n")
        except Exception as e:
            logger.warning("[Ogrenme] _temizle hatasi: %s", e)

class SurekliOgrenmeYoneticisi:
    def __init__(self):
        self.depo = OgrenmeDeposu()
        self._adaptif = None
    @property
    def adaptif(self):
        if self._adaptif is None:
            try:
                from reymen.cereyan.adaptif_ogrenme import AdaptifOgrenme
                self._adaptif = AdaptifOgrenme()
            except Exception as e:
                logger.debug("[Ogrenme] Adaptif ogrenme yuklenemedi: %s", e)
        return self._adaptif
    def ogren(self, alan: str, icerik: str, kaynak: str = "manuel") -> str:
        o = Ogrenme(alan, icerik, kaynak)
        if self.depo.kaydet(o): return "[OGREN] %s kaydedildi. (%d kayit)" % (alan, self.depo.sayi())
        return "[OGREN] Basarisiz."
    def hatirla(self, alan: str = None) -> str:
        ogr = self.depo.hepsini_getir(alan=alan or None, limit=20)
        if not ogr: return "[OGREN] Kayit yok."
        satirlar = ["[Surekli Ogrenme - %s]" % (alan or "Tum Alanlar")]
        for o in ogr: satirlar.append(f"  [{o.alan}] {o.icerik}")
        return "\n".join(satirlar)
    def ozet(self) -> str:
        alanlar = self.depo.alan_listesi()
        satirlar = ["📚 Surekli Ogrenme", f"  Toplam: {self.depo.sayi()}", f"  Alan: {len(alanlar)}"]
        if alanlar:
            satirlar.append("  Alanlar:")
            for a in alanlar: satirlar.append(f"    {a}: {len(self.depo.hepsini_getir(alan=a, limit=10000))} kayit")
        if self.adaptif:
            try: satirlar.append(f"  Tercih: {self.adaptif.tercih_sayisi()} adet")
            except Exception as e:
                logger.debug("[Ogrenme] Tercih bilgisi alinamadi: %s", e)
        return "\n".join(satirlar)

_yonetici = None
def get_yonetici():
    global _yonetici
    if _yonetici is None: _yonetici = SurekliOgrenmeYoneticisi()
    return _yonetici

def ogren(alan: str, icerik: str, kaynak: str = "manuel") -> str:
    return get_yonetici().ogren(alan, icerik, kaynak)
def ogrenmeleri_getir(alan: str = "") -> str:
    return get_yonetici().hatirla(alan.strip() or None)
def ogrenme_ozeti() -> str:
    return get_yonetici().ozet()

def motor_kaydet(motor) -> None:
    if not hasattr(motor, "_plugin_arac_kaydet"): return
    try:
        y = get_yonetici()
        motor._plugin_arac_kaydet("OGREN", lambda ham="": (ogren(*_ayristir(ham)) if ham else ogrenme_ozeti()), "Ogrenme kaydet: OGREN(alan=..., icerik=...)")
        motor._plugin_arac_kaydet("OGRENMELERI_GETIR", lambda a="": ogrenmeleri_getir(a), "Gecmis ogrenmeler: OGRENMELERI_GETIR(alan=...)")
        motor._plugin_arac_kaydet("OGRENME_OZETI", lambda: ogrenme_ozeti(), "Istatistikler.")
        logger.info("[SurekliOgrenme] %d kayit", y.depo.sayi())
    except Exception as e:
        logger.warning("[SurekliOgrenme] Hata: %s", e)

def _ayristir(ham: str) -> tuple:
    alan = re.search(r"alan\\s*=\\*\"([^\"]*)\"", ham)
    icerik = re.search(r"icerik\\s*=\\*\"([^\"]*)\"", ham)
    return (alan.group(1) if alan else "genel", icerik.group(1) if icerik else (ham.strip().strip("\"") or "bos"), "tool")

if __name__ == "__main__":
    y = get_yonetici()
    print(y.ozet())
    y.ogren("test", "Bu bir test")
    print(y.hatirla("test"))
