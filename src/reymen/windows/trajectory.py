# -*- coding: utf-8 -*-
"""trajectory.py — Adim Gecmisi (Trajectory).

Her turdaki dusunce, eylem ve gozlemi kaydeder.
Sonradan analiz, hata ayiklama ve ogrenme icin kullanilir.

Desteklenen formatlar:
  - ReYMeN ozel JSON (varsayilan)
  - ShareGPT JSONL (ReYMeN Agent / HuggingFace egitim veri formati)
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

TRAJ_DIZINI = Path(__file__).parent / ".ReYMeN" / "trajectories"
TRAJ_DIZINI.mkdir(parents=True, exist_ok=True)

SHAREGPT_TAMAMLANDI = TRAJ_DIZINI / "trajectory_samples.jsonl"
SHAREGPT_BASARISIZ  = TRAJ_DIZINI / "failed_trajectories.jsonl"


class Trajectory:
    def __init__(self, hedef: str, model: str = None):
        self.hedef = hedef
        self.model = model or "local"
        self.adimlar: list[dict] = []
        self._oturum_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._tamamlandi = False

    def adim_ekle(self, tur: int, dusunce: str, eylem: str, gozlem: str):
        self.adimlar.append({
            "tur": tur,
            "dusunce": dusunce,
            "eylem": eylem,
            "gozlem": gozlem[:500],
            "zaman": datetime.now().isoformat(),
        })

    def tamamla(self):
        """Gorev basarili bitti olarak isaretle."""
        self._tamamlandi = True

    def son_adim(self) -> Optional[dict]:
        return self.adimlar[-1] if self.adimlar else None

    def ozet(self, son_n: int = 3) -> str:
        """Son N adimi metin olarak dondur."""
        if not self.adimlar:
            return "(henuz adim yok)"
        satirlar = []
        for a in self.adimlar[-son_n:]:
            satirlar.append(f"[Tur {a['tur']}] {a['eylem'][:60]} -> {a['gozlem'][:60]}")
        return "\n".join(satirlar)

    def tool_istatistik(self) -> dict:
        """Araç kullanim istatistiklerini dondur (ShareGPT batch format uyumlu).

        Returns:
            {arac_adi: {count, success, failure}, ...}
        """
        sayac: dict = {}
        for adim in self.adimlar:
            eylem = adim.get("eylem", "")
            m = re.match(r"([A-Z_]+)\s*\(", eylem)
            if not m:
                continue
            arac = m.group(1)
            gozlem = adim.get("gozlem", "")
            basarili = "[Hata]" not in gozlem and "Hatasi]" not in gozlem

            if arac not in sayac:
                sayac[arac] = {"count": 0, "success": 0, "failure": 0}
            sayac[arac]["count"] += 1
            if basarili:
                sayac[arac]["success"] += 1
            else:
                sayac[arac]["failure"] += 1
        return sayac

    @staticmethod
    def _dosya_adi_temizle(metin: str, max_uzunluk: int = 40) -> str:
        """Windows/Linux icin gecersiz karakterleri kaldir."""
        import re
        temiz = re.sub(r'[\\/:*?"<>|]', "_", metin)
        temiz = re.sub(r"\s+", "_", temiz)
        return temiz[:max_uzunluk]

    def kaydet(self):
        """Ozel ReYMeN JSON formatinda kaydet."""
        dosya = TRAJ_DIZINI / f"{self._oturum_id}_{self._dosya_adi_temizle(self.hedef)}.json"
        dosya.write_text(
            json.dumps({
                "hedef": self.hedef,
                "model": self.model,
                "tamamlandi": self._tamamlandi,
                "adim_sayisi": len(self.adimlar),
                "adimlar": self.adimlar,
                "tool_istatistik": self.tool_istatistik(),
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def sharegpt_kaydet(self, sistem_prompt: str = ""):
        """ShareGPT JSONL formatinda kaydet (HuggingFace / ReYMeN egitim formati).

        Format:
            {
                "conversations": [
                    {"from": "system", "value": "..."},
                    {"from": "human",  "value": "..."},
                    {"from": "gpt",    "value": "..."},
                    {"from": "tool",   "value": "..."},
                ],
                "timestamp": "...",
                "model": "...",
                "completed": true/false,
                "tool_stats": {...},
                "tool_error_counts": {...}
            }
        """
        konusma = []

        if sistem_prompt:
            konusma.append({"from": "system", "value": sistem_prompt})

        konusma.append({"from": "human", "value": self.hedef})

        for adim in self.adimlar:
            # Dusunce + eylem → "gpt" rolu
            gpt_icerik = ""
            if adim.get("dusunce"):
                gpt_icerik += f"Dusunce: {adim['dusunce']}\n"
            if adim.get("eylem"):
                gpt_icerik += f"Eylem: {adim['eylem']}"
            if gpt_icerik:
                konusma.append({"from": "gpt", "value": gpt_icerik.strip()})

            # Gozlem → "tool" rolu
            if adim.get("gozlem"):
                konusma.append({"from": "tool", "value": adim["gozlem"]})

        tool_stats = self.tool_istatistik()
        tool_error_counts = {k: v["failure"] for k, v in tool_stats.items()}

        giris = {
            "conversations": konusma,
            "timestamp": datetime.now().isoformat(),
            "model": self.model,
            "completed": self._tamamlandi,
            "tool_stats": tool_stats,
            "tool_error_counts": tool_error_counts,
        }

        # Tamamlanan ve basarisizlar ayri dosyaya
        hedef_dosya = SHAREGPT_TAMAMLANDI if self._tamamlandi else SHAREGPT_BASARISIZ
        with hedef_dosya.open("a", encoding="utf-8") as f:
            f.write(json.dumps(giris, ensure_ascii=False) + "\n")

    @staticmethod
    def gecmisi_getir(limit: int = 5) -> list[dict]:
        """Son N trajectory dosyasini oku."""
        dosyalar = sorted(TRAJ_DIZINI.glob("*.json"))[-limit:]
        sonuc = []
        for d in dosyalar:
            try:
                sonuc.append(json.loads(d.read_text(encoding="utf-8")))
            except Exception as _e:
                logger.warning("[Trajectory] JSON yukleme: %s (%s)", d.name, _e)
        return sonuc

    @staticmethod
    def sharegpt_yukle(tamamlanan: bool = True) -> list[dict]:
        """ShareGPT JSONL dosyasini oku — egitim verisi olarak kullan."""
        hedef = SHAREGPT_TAMAMLANDI if tamamlanan else SHAREGPT_BASARISIZ
        if not hedef.exists():
            return []
        sonuc = []
        for satir in hedef.read_text(encoding="utf-8").splitlines():
            try:
                sonuc.append(json.loads(satir))
            except Exception as _e:
                logger.warning("[Trajectory] ShareGPT satir: %s", _e)
        return sonuc


if __name__ == "__main__":
    t = Trajectory("test gorevi", model="llama3.1:8b")
    t.adim_ekle(1, "Dosyayi okumaliyim", "DOSYA_OKU(\"test.txt\")", "Icerik: merhaba")
    t.adim_ekle(2, "Tamamlandi", "GOREV_BITTI(\"dosya okundu\")", "OK")
    t.tamamla()

    print("== Ozet ==")
    print(t.ozet())

    print("\n== Tool Istatistik ==")
    print(json.dumps(t.tool_istatistik(), ensure_ascii=False, indent=2))

    t.kaydet()
    t.sharegpt_kaydet(sistem_prompt="Sen bir ajan sistemisin.")
    print(f"\n== ShareGPT kayit: {SHAREGPT_TAMAMLANDI} ==")
    yuklu = Trajectory.sharegpt_yukle()
    print(f"   {len(yuklu)} giris yuklu, ilk konusma: {len(yuklu[0]['conversations'])} mesaj")
    print("\nTum testler basarili.")
