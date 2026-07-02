# -*- coding: utf-8 -*-
"""backup.py — Yedekleme sistemi.

Proje dosyalarini ZIP ile yedekler.
"""

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

BACKUP_DIR = Path(__file__).parent / ".ReYMeN" / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

HARIC_TUT = {
    "venv", ".git", "__pycache__", ".ReYMeN/backups",
    ".ReYMeN/trajectories", ".ReYMeN/checkpoints",
    "logs", "output", "node_modules",
}


def yedekle(etiket: str = "") -> str:
    """Projeyi ZIP ile yedekle.

    Args:
        etiket: Yedek etiketi (bos = otomatik)

    Returns:
        Yedek dosyasi yolu
    """
    tarih = datetime.now().strftime("%Y%m%d_%H%M%S")
    etiket_k = f"_{etiket}" if etiket else ""
    dosya_adi = f"ReYMeN_backup_{tarih}{etiket_k}.zip"
    dosya_yolu = BACKUP_DIR / dosya_adi

    proje_kok = Path(__file__).parent

    with zipfile.ZipFile(dosya_yolu, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in proje_kok.rglob("*"):
            # Haric tutulanlari atla
            rel = f.relative_to(proje_kok)
            if any(str(rel).startswith(h) for h in HARIC_TUT):
                continue
            if f.is_file() and f.name != dosya_adi:
                zf.write(f, str(rel))

    return str(dosya_yolu)


def yedek_listele() -> list[dict]:
    """Mevcut yedekleri listele."""
    sonuc = []
    for f in sorted(BACKUP_DIR.glob("*.zip"), reverse=True):
        boyut = f.stat().st_size
        sonuc.append({
            "dosya": f.name,
            "boyut": f"{boyut / 1024:.1f}KB" if boyut < 1024 * 1024 else f"{boyut / 1024 / 1024:.1f}MB",
            "tarih": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
        })
    return sonuc


if __name__ == "__main__":
    yol = yedekle("test")
    print(f"Yedek: {yol}")
    print(f"Yedekler: {yedek_listele()}")
