# -*- coding: utf-8 -*-
"""
zamanlayici.py — Zamanlanmış görev yöneticisi (cron).
Belirli aralıklarla (dakika/saat/gün) alt ajan görevleri başlatır.
Thread tabanlı, non-daemon — bot restart yiyene kadar yaşar.
"""

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.resolve()

_CRON_FILE = ROOT / ".cron_jobs.json"
_CRON_LOG_DIR = ROOT / ".cron_logs"
_CRON_LOG_DIR.mkdir(parents=True, exist_ok=True)

# Tutulan işler: {job_id: {...}}
_jobs: dict = {}
_kilit = threading.Lock()
_scheduler_thread: Optional[threading.Thread] = None
_scheduler_calissin = threading.Event()
_scheduler_calissin.set()  # Başlangıçta çalışsın


# ── Job CRUD ──

def _kaydet():
    """Jobs JSON dosyasına yaz."""
    try:
        _CRON_FILE.write_text(
            json.dumps(_jobs, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8"
        )
    except Exception as _zamanlay_e37:
        print(f"[UYARI] zamanlayici.py:38 - {_zamanlay_e37}")


def _yukle():
    """Jobs JSON dosyasından oku."""
    global _jobs
    try:
        if _CRON_FILE.exists():
            _jobs = json.loads(_CRON_FILE.read_text(encoding="utf-8"))
    except Exception:
        _jobs = {}


def cron_ekle(job_id: str, gorev: str, aralik_saniye: int,
              baglam: str = "", max_adim: int = 5) -> str:
    """Yeni zamanlanmış görev ekle.

    Args:
        job_id: Benzersiz kimlik
        gorev: Alt ajana verilecek görev
        aralik_saniye: Çalışma aralığı (örn 1800 = 30dk)
        baglam: Opsiyonel bağlam bilgisi
        max_adim: Maksimum ReAct adımı

    Returns:
        str: Durum mesajı
    """
    with _kilit:
        if job_id in _jobs:
            return f"[Cron] '{job_id}' zaten var. Once cron_sil('{job_id}') yapin."
        _jobs[job_id] = {
            "gorev": gorev,
            "aralik_saniye": aralik_saniye,
            "baglam": baglam,
            "max_adim": max_adim,
            "son_ts": 0,  # Hiç çalışmadı
            "son_durum": "",
            "aktif": True,
            "olusma_ts": time.time(),
        }
        _kaydet()
    _scheduler_calissin.set()  # Scheduler'ı uyandır
    return f"[Cron] '{job_id}' eklendi (her {aralik_saniye}s)."


def cron_sil(job_id: str) -> str:
    """Zamanlanmış görevi sil."""
    with _kilit:
        if job_id not in _jobs:
            return f"[Cron] '{job_id}' bulunamadi."
        del _jobs[job_id]
        _kaydet()
    return f"[Cron] '{job_id}' silindi."


def cron_listele() -> list[dict]:
    """Tüm cron görevlerini listeler."""
    with _kilit:
        return [
            {
                "id": jid,
                "gorev": j["gorev"][:60],
                "aralik": j["aralik_saniye"],
                "aktif": j.get("aktif", True),
                "son_durum": j.get("son_durum", ""),
                "son_ts": j.get("son_ts", 0),
            }
            for jid, j in _jobs.items()
        ]


def cron_durdur(job_id: str) -> str:
    """Bir cron görevini duraklat."""
    with _kilit:
        if job_id not in _jobs:
            return f"[Cron] '{job_id}' bulunamadi."
        _jobs[job_id]["aktif"] = False
        _kaydet()
    return f"[Cron] '{job_id}' duraklatildi."


def cron_devam_et(job_id: str) -> str:
    """Duraklatılmış cron görevini devam ettir."""
    with _kilit:
        if job_id not in _jobs:
            return f"[Cron] '{job_id}' bulunamadi."
        _jobs[job_id]["aktif"] = True
        _kaydet()
    _scheduler_calissin.set()
    return f"[Cron] '{job_id}' devam ediyor."


def cron_calistir_simdi(job_id: str) -> str:
    """Bir cron görevini hemen çalıştır (sıradaki zamanı beklemeden)."""
    with _kilit:
        if job_id not in _jobs:
            return f"[Cron] '{job_id}' bulunamadi."
        _jobs[job_id]["son_ts"] = 0  # scheduler hemen alsın
        _kaydet()
    _scheduler_calissin.set()
    return f"[Cron] '{job_id}' siraya alindi."


# ── Scheduler Döngüsü ──

def _log_yaz(job_id: str, durum: str, detay: str = ""):
    """Her cron çalışmasını log dosyasına yazar."""
    log_file = _CRON_LOG_DIR / f"{job_id}.log"
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {durum}: {detay[:200]}\n")
    except Exception as _zamanlay_e149:
        print(f"[UYARI] zamanlayici.py:150 - {_zamanlay_e149}")


def _gorev_calistir(job_id: str, job: dict):
    """Bir cron görevini alt ajan ile çalıştırır."""
    try:
        from reymen.cereyan.alt_ajan import alt_ajan_yoneticisi

        tid = alt_ajan_yoneticisi.gorevlendir(
            gorev=job["gorev"],
            baglam=job.get("baglam", ""),
            max_adim=job.get("max_adim", 5),
        )
        _log_yaz(job_id, "baslatildi", f"task_id={tid}")

        # Sonucu bekle (timeout: max_adim * 30sn)
        timeout = job.get("max_adim", 5) * 30
        sonuc = alt_ajan_yoneticisi.sonuc_bekle(tid, timeout=timeout)

        if sonuc:
            durum = sonuc.durum
            ozet = (sonuc.sonuc or sonuc.hata or "")[:200]
        else:
            durum = "timeout"
            ozet = f"{timeout}s beklendi ama bitmedi"

        with _kilit:
            if job_id in _jobs:
                _jobs[job_id]["son_durum"] = f"{durum}: {ozet[:60]}"
                _jobs[job_id]["son_ts"] = time.time()
                _kaydet()

        _log_yaz(job_id, durum, ozet)

    except Exception as e:
        _log_yaz(job_id, "hata", str(e)[:200])
        with _kilit:
            if job_id in _jobs:
                _jobs[job_id]["son_durum"] = f"hata: {str(e)[:60]}"
                _jobs[job_id]["son_ts"] = time.time()
                _kaydet()


def _scheduler_dongusu():
    """Ana scheduler döngüsü — 30sn'de bir kontrol eder."""
    while _scheduler_calissin.is_set():
        try:
            simdi = time.time()
            with _kilit:
                adaylar = {
                    jid: j for jid, j in _jobs.items()
                    if j.get("aktif", True)
                    and (simdi - j.get("son_ts", 0)) >= j.get("aralik_saniye", 3600)
                }

            for jid, j in adaylar.items():
                threading.Thread(
                    target=_gorev_calistir,
                    args=(jid, j),
                    daemon=True,
                    name=f"cron-run-{jid}"
                ).start()
        except Exception as _zamanlay_e212:
            print(f"[UYARI] zamanlayici.py:213 - {_zamanlay_e212}")

        _scheduler_calissin.wait(timeout=30)


# ── Public API ──

def scheduler_baslat():
    """Scheduler thread'ini başlatır (non-daemon)."""
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        return "[Cron] Scheduler zaten calisiyor."

    _yukle()
    _scheduler_calissin.set()
    _scheduler_thread = threading.Thread(
        target=_scheduler_dongusu,
        daemon=False,  # Bot yaşadıkça yaşar
        name="cron-scheduler"
    )
    _scheduler_thread.start()
    job_sayisi = len(_jobs)
    return f"[Cron] Scheduler baslatildi ({job_sayisi} gorev yuklu)."


def scheduler_durdur():
    """Scheduler thread'ini durdurur."""
    _scheduler_calissin.clear()
    return "[Cron] Scheduler durduruldu."
