# -*- coding: utf-8 -*-
"""context_references.py — Referans Yonetimi.

Gecmis konusmalardan onemli referanslari cikarir, saklar ve
gerektiginde context'e ekler. Bellek tasarrufu icin kullanilir.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

REF_DIZINI = Path(__file__).parent / ".ReYMeN" / "references"
REF_DIZINI.mkdir(parents=True, exist_ok=True)
REF_DOSYASI = REF_DIZINI / "referanslar.json"


class ReferansYoneticisi:
    def __init__(self):
        self._referanslar: list[dict] = []
        self._yukle()

    def _yukle(self):
        if REF_DOSYASI.exists():
            try:
                self._referanslar = json.loads(REF_DOSYASI.read_text(encoding="utf-8"))
            except Exception:
                self._referanslar = []

    def _kaydet(self):
        REF_DOSYASI.write_text(
            json.dumps(self._referanslar[-100:], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def ekle(self, etiket: str, icerik: str, kaynak: str = ""):
        """Yeni referans ekle (en fazla 100)."""
        self._referanslar.append({
            "etiket": etiket,
            "icerik": icerik[:500],
            "kaynak": kaynak,
            "tarih": datetime.now().isoformat()[:10],
        })
        self._kaydet()

    def ara(self, sorgu: str) -> list[dict]:
        """Referanslarda metin ara."""
        sorgu = sorgu.lower()
        sonuc = []
        for r in self._referanslar:
            if sorgu in r["etiket"].lower() or sorgu in r["icerik"].lower():
                sonuc.append(r)
        return sonuc[:5]

    def context_ozeti(self, max_bas: int = 3) -> str:
        """Context'e eklenecek ozet metin."""
        if not self._referanslar:
            return ""
        son = self._referanslar[-max_bas:]
        satirlar = ["[Referanslar]"]
        for r in son:
            satirlar.append(f"  - {r['etiket']}: {r['icerik'][:100]}")
        return "\n".join(satirlar)

    def sifirla(self):
        self._referanslar = []
        self._kaydet()


def motor_kaydet(motor):
    """Referans araçlarını motora kaydet."""
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return
    _ry = ReferansYoneticisi()
    motor._plugin_arac_kaydet(
        "REFERANS_EKLE",
        lambda etiket="", icerik="", kaynak="": (
            _ry.ekle(str(etiket), str(icerik), str(kaynak)), "[Referans]: Eklendi"
        )[1],
        "Önemli bir bilgiyi referans olarak kaydet (etiket, icerik, kaynak)",
    )
    motor._plugin_arac_kaydet(
        "REFERANS_ARA",
        lambda sorgu="": str(_ry.ara(str(sorgu))) or "[Referans]: Sonuç yok",
        "Kaydedilmiş referanslarda metin ara",
    )
    motor._plugin_arac_kaydet(
        "REFERANS_OZET",
        lambda: _ry.context_ozeti() or "[Referans]: Kayıt yok",
        "Son referansların özetini göster",
    )


if __name__ == "__main__":
    r = ReferansYoneticisi()
    r.ekle("test", "ornek referans", "test")
    print(r.context_ozeti())
