#!/usr/bin/env python3
"""
cron_skill_sync_register.py — Skill sync cron job kaydi.

Bu script, cron_skill_sync.py'yi ReYMeN cron sistemine kaydeder:
- skills_index.db (FTS5) her 6 saatte bir otomatik guncellenir
- jobs.json dosyasina kayit eklenir
- Mevcut cronjob_tools API'si uzerinden calisir

Kullanim:
    python cron_skill_sync_register.py    # Kaydet
    python cron_skill_sync_register.py --remove  # Kaldir
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("cron_skill_sync_register")

ROOT = Path(__file__).parent.resolve()
JOBS_PATH = ROOT.parent / ".ReYMeN" / "cron" / "jobs.json"
JOB_ID = "skill_sync_periodic"


def _jobs_oku() -> dict:
    """jobs.json dosyasini oku."""
    if not JOBS_PATH.exists():
        return {}
    try:
        content = JOBS_PATH.read_text(encoding="utf-8").strip()
        return json.loads(content) if content else {}
    except (json.JSONDecodeError, Exception):
        return {}


def _jobs_yaz(joblar: dict) -> None:
    """jobs.json dosyasina yaz."""
    JOBS_PATH.parent.mkdir(parents=True, exist_ok=True)
    JOBS_PATH.write_text(
        json.dumps(joblar, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def kaydet() -> str:
    """Skill sync cron job'unu kaydet."""
    sync_script = str(ROOT / "cron_skill_sync.py")
    komut = f"{sys.executable} {sync_script}"

    joblar = _jobs_oku()
    joblar[JOB_ID] = {
        "komut": komut,
        "zaman": "every 6 hours",
        "cron": "0 */6 * * *",
        "aktif": True,
        "aciklama": "Skills FTS5 index senkronizasyonu",
        "kaynak": "cron_skill_sync.py",
        "olusturma": datetime.now().isoformat(),
    }
    _jobs_yaz(joblar)
    msg = f"[Cron] Skill sync job kaydedildi: {JOB_ID}"
    msg += f"\n  Komut: {komut}"
    msg += f"\n  Zaman: every 6 hours (0 */6 * * *)"
    logger.info(msg)
    return msg


def kaldir() -> str:
    """Skill sync cron job'unu kaldir."""
    joblar = _jobs_oku()
    if JOB_ID in joblar:
        del joblar[JOB_ID]
        _jobs_yaz(joblar)
        msg = f"[Cron] Skill sync job kaldirildi: {JOB_ID}"
        logger.info(msg)
        return msg
    return f"[Cron] Job bulunamadi: {JOB_ID}"


def durum() -> str:
    """Skill sync job durumunu goster."""
    joblar = _jobs_oku()
    job = joblar.get(JOB_ID)
    if not job:
        return f"[Cron] Skill sync job kayitli degil."
    aktif = "Aktif" if job.get("aktif", True) else "Pasif"
    return (
        f"[Cron] Skill sync job: {JOB_ID}\n"
        f"  Durum: {aktif}\n"
        f"  Komut: {job.get('komut', '?')}\n"
        f"  Zaman: {job.get('zaman', '?')}"
    )


# Cronjob tool API uyumlu arayuz
def cronjob(**kwargs) -> str:
    """cronjob_tools API'si ile uyumlu fonksiyon."""
    action = kwargs.get("action", "status")
    if action == "create" or action == "register":
        return kaydet()
    elif action == "remove" or action == "delete":
        return kaldir()
    else:
        return durum()


if __name__ == "__main__":
    if "--remove" in sys.argv or "--kaldir" in sys.argv:
        print(kaldir())
    elif "--status" in sys.argv or "--durum" in sys.argv:
        print(durum())
    else:
        print(kaydet())
