# -*- coding: utf-8 -*-
"""trajectory_compressor.py — Gecmis Sikistirma.

Uzun oturumlarda eski adimlari LLM'e ozetleterek context
penceresini verimli kullanir. Her 5 turda bir calisir.
"""

import json
from pathlib import Path
from typing import Optional

OZET_DIZINI = Path(__file__).parent / ".ReYMeN" / "ozetler"
OZET_DIZINI.mkdir(parents=True, exist_ok=True)


class TrajectoryCompressor:
    def __init__(self, provider=None):
        self.provider = provider
        self._ozet_sayaci = 0

    def ozetle(self, adimlar: list[dict], baslangic_turu: int) -> Optional[str]:
        """Adimlari LLM ile ozetle. provider yoksa basit birlestirme yap."""
        if not adimlar:
            return None

        if self.provider:
            return self._llm_ozetle(adimlar)
        return self._basit_ozetle(adimlar, baslangic_turu)

    def _llm_ozetle(self, adimlar: list[dict]) -> str:
        satirlar = []
        for a in adimlar:
            satirlar.append(f"[{a.get('tur','?')}] {a.get('eylem','')[:80]} -> {a.get('gozlem','')[:80]}")
        prompt = (
            "Asagidaki ajan adimlarini 2-3 cumleyle ozetle:\n"
            + "\n".join(satirlar)
        )
        try:
            return self.provider.uret(prompt, [{"role": "user", "content": "Ozetle."}])
        except Exception:
            return self._basit_ozetle(adimlar, adimlar[0].get("tur", 0))

    def _basit_ozetle(self, adimlar: list[dict], baslangic_turu: int) -> str:
        basarili = sum(1 for a in adimlar if "[Hata]" not in a.get("gozlem", ""))
        toplam = len(adimlar)
        return f"[OZET: {baslangic_turu}-{baslangic_turu+toplam-1}. turlar] {basarili}/{toplam} adim basarili."

    def kaydet(self, hedef: str, ozet: str):
        self._ozet_sayaci += 1
        dosya = OZET_DIZINI / f"ozet_{self._ozet_sayaci}.json"
        dosya.write_text(
            json.dumps({"hedef": hedef[:50], "ozet": ozet}, ensure_ascii=False),
            encoding="utf-8",
        )


if __name__ == "__main__":
    c = TrajectoryCompressor()
    print(c.ozetle([
        {"tur": 1, "eylem": "DOSYA_OKU(\"test.txt\")", "gozlem": "[Tamam]"},
        {"tur": 2, "eylem": "DOSYA_YAZ(\"out.txt\", \"icirk\")", "gozlem": "[Tamam]"},
    ], 1))
