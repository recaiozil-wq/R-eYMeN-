# -*- coding: utf-8 -*-
"""checkpoint_manager.py — Kontrol Noktasi (Checkpoint) Yoneticisi.

Agent'in mevcut durumunu kaydeder ve geri yukler.
Boylece yarida kesilen gorevler kaldigi yerden devam edebilir.
"""

import json
import os
import time
from pathlib import Path
from typing import Optional
import logging
logger = logging.getLogger(__name__)

CHECKPOINT_DIR = Path(__file__).parent / ".ReYMeN" / "checkpoints"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)


class CheckpointManager:
    def __init__(self):
        self._son_kayit: Optional[str] = None

    def kaydet(self, hedef: str, tur: int, durum: dict) -> str:
        """Mevcut durumu checkpoint olarak kaydet.

        Args:
            hedef: Gorev hedefi
            tur: Mevcut tur
            durum: Kaydedilecek durum sozlugu

        Returns:
            Checkpoint ID'si
        """
        checkpoint_id = f"ckpt_{int(time.time())}"
        dosya = CHECKPOINT_DIR / f"{checkpoint_id}.json"

        veri = {
            "id": checkpoint_id,
            "hedef": hedef,
            "tur": tur,
            "zaman": time.time(),
            "durum": durum,
        }

        dosya.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")
        self._son_kayit = checkpoint_id
        return checkpoint_id

    def yukle(self, checkpoint_id: str) -> Optional[dict]:
        """Bir checkpoint'i yukle.

        Args:
            checkpoint_id: Checkpoint ID'si

        Returns:
            Durum sozlugu veya None
        """
        dosya = CHECKPOINT_DIR / f"{checkpoint_id}.json"
        if not dosya.exists():
            return None
        try:
            return json.loads(dosya.read_text(encoding="utf-8"))
        except Exception:
            return None

    def son_chekpoint(self) -> Optional[dict]:
        """Son checkpoint'i yukle."""
        if self._son_kayit:
            return self.yukle(self._son_kayit)
        dosyalar = sorted(CHECKPOINT_DIR.glob("ckpt_*.json"))
        if not dosyalar:
            return None
        try:
            return json.loads(dosyalar[-1].read_text(encoding="utf-8"))
        except Exception:
            return None

    def listele(self) -> list[dict]:
        """Tum checkpoint'leri listele."""
        sonuc = []
        for d in sorted(CHECKPOINT_DIR.glob("ckpt_*.json")):
            try:
                veri = json.loads(d.read_text(encoding="utf-8"))
                sonuc.append({
                    "id": veri["id"],
                    "hedef": veri["hedef"][:50],
                    "tur": veri["tur"],
                    "zaman": time.strftime("%H:%M:%S", time.localtime(veri["zaman"])),
                })
            except Exception as _checkpoi_e88:
                print(f"[UYARI] checkpoint_manager.py:89 - {_checkpoi_e88}")
        return sonuc

    def temizle(self, saatten_eski: int = 24):
        """Eski checkpoint'leri temizle."""
        sinir = time.time() - (saatten_eski * 3600)
        for d in CHECKPOINT_DIR.glob("ckpt_*.json"):
            try:
                if d.stat().st_mtime < sinir:
                    d.unlink()
            except Exception as _checkpoi_e99:
                print(f"[UYARI] checkpoint_manager.py:100 - {_checkpoi_e99}")

    def devam_edebilir_mi(self, hedef: str) -> Optional[dict]:
        """Ayni hedef icin checkpoint var mi kontrol et."""
        for d in CHECKPOINT_DIR.glob("ckpt_*.json"):
            try:
                veri = json.loads(d.read_text(encoding="utf-8"))
                if veri.get("hedef") == hedef and veri.get("tur", 0) > 0:
                    return veri
            except Exception as _checkpoi_e109:
                print(f"[UYARI] checkpoint_manager.py:110 - {_checkpoi_e109}")
        return None


if __name__ == "__main__":
    c = CheckpointManager()
    c.kaydet("test gorevi", 5, {"adimlar": ["yapildi"]})
    print(f"Checkpoint'ler: {c.listele()}")
    son = c.son_chekpoint()
    if son:
        print(f"Son: {son['hedef']}, tur {son['tur']}")
