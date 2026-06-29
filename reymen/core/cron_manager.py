# -*- coding: utf-8 -*-
"""
cron_manager.py — Cron/Scheduler + Watchdog Sistemi.

Per-job ozellikleri:
  - Schedule override (her is icin ayri zamanlama)
  - Timeout (is belirli surede bitmezse otomatik durdur)
  - Retry (basarisiz islerde otomatik tekrar deneme)
  - Watchdog (is donarsa uyari + restart)
  - Model override (her is icin ayri model/provider)
  - Deliver hedefi (sonuc nereye gonderilecek)
  - Skills (isin kullanacagi yetenekler)

Mevcut cron islerini (.ReYMeN/cron/) okur + yeni yapiyla birlestirir.

Motor tools:
  - CRON_LISTE:  Kayitli cron islerini listele
  - CRON_EKLE:  Yeni cron isi ekle (override ile)
  - CRON_SIL:   Cron isini sil
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# ── Sabitler ─────────────────────────────────────────────────────────
PROJE_KOKU = Path(__file__).resolve().parent.parent.parent  # projekt
CRON_DIZINI = PROJE_KOKU / ".ReYMeN" / "cron"
JOBS_JSON_YOLU = CRON_DIZINI / "jobs.json"
WATCHDOG_LOG = CRON_DIZINI / "watchdog.log"


# ═══════════════════════════════════════════════════════════════════════
#  Veri Modelleri
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class CronJob:
    """Bir cron isinin tum ozellikleri."""
    id: str = ""
    ad: str = ""
    komut: str = ""           # Shell komutu
    script: str = ""          # .py script yolu (komut yerine)
    prompt: str = ""          # LLM prompt (agent modunda)
    cron_ifade: str = ""      # Cron expression (ornek: "0 */6 * * *")
    zaman_aciklama: str = ""  # Insan okunabilir zaman ("every 6 hours")
    aktif: bool = True
    durum: str = "idle"       # idle, running, success, failed, timeout
    timeout_saniye: int = 300 # Varsayilan 5 dk
    max_retry: int = 3
    retry_sayisi: int = 0
    model: Optional[str] = None       # Model override
    provider: Optional[str] = None    # Provider override
    base_url: Optional[str] = None    # Base URL override
    skills: list[str] = field(default_factory=list)
    deliver: str = "origin"           # "origin", "telegram", "discord", "cli", "none"
    deliver_hedef: Optional[str] = None
    aciklama: str = ""
    kaynak: str = ""
    olusturma: str = ""
    son_calisma: Optional[str] = None
    son_durum: Optional[str] = None
    son_hata: Optional[str] = None
    siraki_calisma: Optional[str] = None
    pid: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ad": self.ad,
            "komut": self.komut,
            "script": self.script,
            "prompt": self.prompt,
            "cron": self.cron_ifade,
            "zaman": self.zaman_aciklama,
            "aktif": self.aktif,
            "durum": self.durum,
            "timeout": self.timeout_saniye,
            "max_retry": self.max_retry,
            "retry_sayisi": self.retry_sayisi,
            "model": self.model,
            "provider": self.provider,
            "base_url": self.base_url,
            "skills": self.skills,
            "deliver": self.deliver,
            "deliver_hedef": self.deliver_hedef,
            "aciklama": self.aciklama,
            "kaynak": self.kaynak,
            "olusturma": self.olusturma,
            "son_calisma": self.son_calisma,
            "son_durum": self.son_durum,
            "son_hata": self.son_hata,
            "siraki_calisma": self.siraki_calisma,
            "pid": self.pid,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CronJob":
        return cls(
            id=data.get("id", ""),
            ad=data.get("ad", ""),
            komut=data.get("komut", ""),
            script=data.get("script", ""),
            prompt=data.get("prompt", ""),
            cron_ifade=data.get("cron", ""),
            zaman_aciklama=data.get("zaman", ""),
            aktif=data.get("aktif", True),
            durum=data.get("durum", "idle"),
            timeout_saniye=data.get("timeout", 300),
            max_retry=data.get("max_retry", 3),
            retry_sayisi=data.get("retry_sayisi", 0),
            model=data.get("model"),
            provider=data.get("provider"),
            base_url=data.get("base_url"),
            skills=data.get("skills", []),
            deliver=data.get("deliver", "origin"),
            deliver_hedef=data.get("deliver_hedef"),
            aciklama=data.get("aciklama", ""),
            kaynak=data.get("kaynak", ""),
            olusturma=data.get("olusturma", ""),
            son_calisma=data.get("son_calisma"),
            son_durum=data.get("son_durum"),
            son_hata=data.get("son_hata"),
            siraki_calisma=data.get("siraki_calisma"),
            pid=data.get("pid"),
        )


# ═══════════════════════════════════════════════════════════════════════
#  JSON Depolama
# ═══════════════════════════════════════════════════════════════════════

def _json_oku() -> dict[str, Any]:
    """jobs.json'u oku."""
    if not JOBS_JSON_YOLU.exists():
        return {}
    try:
        return json.loads(JOBS_JSON_YOLU.read_text(encoding="utf-8") or "{}")
    except (json.JSONDecodeError, Exception):
        logger.warning("[Cron] jobs.json bozuk, sifirlaniyor.")
        return {}


def _json_yaz(veri: dict[str, Any]) -> None:
    """jobs.json'a yaz."""
    JOBS_JSON_YOLU.parent.mkdir(parents=True, exist_ok=True)
    JOBS_JSON_YOLU.write_text(
        json.dumps(veri, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def _watchdog_log(mesaj: str) -> None:
    """Watchdog log dosyasina yaz."""
    WATCHDOG_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(str(WATCHDOG_LOG), "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {mesaj}\n")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════
#  Cron Scheduler
# ═══════════════════════════════════════════════════════════════════════

class CronManager:
    """Merkezi Cron/Scheduler yoneticisi.

    Kullanim:
        yonetici = CronManager()
        yonetici.baslat()  # Arkaplan scheduler'i baslat
        yonetici.ekle(...) # Yeni is ekle
        yonetici.liste()   # Isleri listele
    """

    def __init__(self):
        self._isler: dict[str, CronJob] = {}
        self._calisan_isler: dict[str, dict] = {}  # id -> {"process": ..., "start": ..., "timer": ...}
        self._scheduler_task: Optional[asyncio.Task] = None
        self._watchdog_task: Optional[asyncio.Task] = None
        self._calisiyor = False

    # ── Baslat / Durdur ─────────────────────────────────────────────

    def baslat(self) -> bool:
        """Scheduler ve watchdog'u baslat."""
        try:
            self._mevcut_isleri_yukle()

            # Thread'de scheduler + watchdog calistir
            threading.Thread(target=self._scheduler_dongusu, daemon=True).start()
            threading.Thread(target=self._watchdog_dongusu, daemon=True).start()

            self._calisiyor = True
            logger.info("[CronManager] Scheduler + Watchdog baslatildi (%d is yuklu).", len(self._isler))
            return True
        except Exception as e:
            logger.error("[CronManager] Baslatma hatasi: %s", e)
            return False

    def durdur(self) -> bool:
        """Tum isleri durdur, scheduler'i kapat."""
        self._calisiyor = False
        for job_id in list(self._calisan_isler.keys()):
            self._is_durdur(job_id)
        logger.info("[CronManager] Durduruldu.")
        return True

    # ── Is Yonetimi ─────────────────────────────────────────────────

    def liste(self, aktif_mi: Optional[bool] = None) -> list[dict[str, Any]]:
        """Tum isleri listele.

        Args:
            aktif_mi: True=sadece aktif, False=sadece pasif, None=hepsi

        Returns:
            Is listesi (dict)
        """
        isler = []
        for job in self._isler.values():
            if aktif_mi is not None and job.aktif != aktif_mi:
                continue
            isler.append(job.to_dict())
        return isler

    def ekle(
        self,
        ad: str,
        komut: str = "",
        script: str = "",
        prompt: str = "",
        cron_ifade: str = "",
        zaman_aciklama: str = "",
        aktif: bool = True,
        timeout_saniye: int = 300,
        max_retry: int = 3,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        base_url: Optional[str] = None,
        skills: Optional[list[str]] = None,
        deliver: str = "origin",
        deliver_hedef: Optional[str] = None,
        aciklama: str = "",
        kaynak: str = "cron_manager",
    ) -> dict[str, Any]:
        """Yeni cron isi ekle (override ile).

        Args:
            ad: Is adi
            komut: Shell komutu
            script: Script yolu
            prompt: LLM prompt
            cron_ifade: Cron expression
            zaman_aciklama: Insan okunabilir zaman
            aktif: Aktif mi
            timeout_saniye: Timeout (saniye)
            max_retry: Maks tekrar deneme
            model: Model override
            provider: Provider override
            base_url: Base URL override
            skills: Kullanilacak skill'ler
            deliver: Teslimat hedefi
            deliver_hedef: Teslimat adresi
            aciklama: Aciklama
            kaynak: Kaynak modul

        Returns:
            {"id": job_id, "basarili": True}
        """
        job_id = str(uuid.uuid4())[:12]
        now = datetime.now(timezone.utc).isoformat()

        job = CronJob(
            id=job_id,
            ad=ad,
            komut=komut,
            script=script,
            prompt=prompt,
            cron_ifade=cron_ifade,
            zaman_aciklama=zaman_aciklama,
            aktif=aktif,
            timeout_saniye=timeout_saniye,
            max_retry=max_retry,
            model=model,
            provider=provider,
            base_url=base_url,
            skills=skills or [],
            deliver=deliver,
            deliver_hedef=deliver_hedef,
            aciklama=aciklama or ad,
            kaynak=kaynak,
            olusturma=now,
        )

        self._isler[job_id] = job
        self._json_kaydet()
        logger.info("[CronManager] Is eklendi: %s (id=%s)", ad, job_id)
        return {"id": job_id, "basarili": True}

    def sil(self, job_id: str) -> dict[str, Any]:
        """Cron isini sil.

        Args:
            job_id: Silinecek is ID

        Returns:
            {"basarili": True/False, "hata": "..."}
        """
        if job_id not in self._isler:
            return {"basarili": False, "hata": f"Is bulunamadi: {job_id}"}

        self._is_durdur(job_id)
        del self._isler[job_id]
        self._json_kaydet()
        logger.info("[CronManager] Is silindi: %s", job_id)
        return {"basarili": True}

    def calistir(self, job_id: str) -> dict[str, Any]:
        """Bir isi hemen calistir.

        Args:
            job_id: Calistirilacak is ID

        Returns:
            {"basarili": True/False}
        """
        job = self._isler.get(job_id)
        if not job:
            return {"basarili": False, "hata": f"Is bulunamadi: {job_id}"}

        threading.Thread(target=self._is_calistir, args=(job_id,), daemon=True).start()
        return {"basarili": True, "mesaj": f"{job.ad} baslatildi"}

    # ── Ic Mekanizmalar ─────────────────────────────────────────────

    def _mevcut_isleri_yukle(self) -> int:
        """Mevcut jobs.json ve cron/ dizinindeki isleri yukle."""
        veri = _json_oku()

        # jobs.json formatinda isler
        if "jobs" in veri:
            for job_dict in veri["jobs"]:
                job = CronJob.from_dict(job_dict)
                if job.id:
                    self._isler[job.id] = job

        # Duzyapi (id -> job)
        for kid, job_dict in veri.items():
            if kid == "jobs" or kid == "updated_at":
                continue
            if isinstance(job_dict, dict):
                job = CronJob.from_dict(job_dict)
                if job.id:
                    self._isler[job.id] = job

        # cron/ dizinindeki .json dosyalarini da tara
        if CRON_DIZINI.exists():
            for p in sorted(CRON_DIZINI.glob("*.json")):
                if p.name == "jobs.json" or p.name == "watchdog.log":
                    continue
                try:
                    ek_veri = json.loads(p.read_text(encoding="utf-8"))
                    if isinstance(ek_veri, dict):
                        job = CronJob.from_dict(ek_veri)
                        if job.id and job.id not in self._isler:
                            self._isler[job.id] = job
                except Exception:
                    pass

        return len(self._isler)

    def _json_kaydet(self) -> None:
        """Tum isleri jobs.json'a kaydet."""
        isler_listesi = [job.to_dict() for job in self._isler.values()]
        _json_yaz({"jobs": isler_listesi, "updated_at": datetime.now(timezone.utc).isoformat()})

    def _scheduler_dongusu(self) -> None:
        """Arkaplan scheduler dongusu — her 30 saniyede bir kontrol."""
        while self._calisiyor:
            try:
                now = datetime.now(timezone.utc)
                for job_id, job in list(self._isler.items()):
                    if not job.aktif:
                        continue
                    if job.durum == "running":
                        continue
                    if self._vakit_geldi_mi(job, now):
                        self._is_calistir(job_id)
                time.sleep(30)
            except Exception as e:
                logger.warning("[Cron] Scheduler hatasi: %s", e)
                time.sleep(60)

    def _watchdog_dongusu(self) -> None:
        """Watchdog dongusu — her 10 saniyede bir calisan isleri kontrol et.

        Bir is timeout suresini asarsa uyari ver + otomatik restart.
        """
        while self._calisiyor:
            try:
                now = time.time()
                for job_id, info in list(self._calisan_isler.items()):
                    job = self._isler.get(job_id)
                    if not job:
                        continue

                    calisma_suresi = now - info["start"]
                    if calisma_suresi > job.timeout_saniye:
                        _watchdog_log(
                            f"WATCHDOG: {job.ad} ({job_id}) timeout! "
                            f"{calisma_suresi:.0f}s > {job.timeout_saniye}s limit"
                        )
                        logger.warning(
                            "[Cron] Watchdog: %s timeout (%ds > %ds)",
                            job.ad, calisma_suresi, job.timeout_saniye,
                        )
                        self._is_durdur(job_id)

                        # Otomatik restart
                        if job.retry_sayisi < job.max_retry:
                            job.retry_sayisi += 1
                            _watchdog_log(
                                f"WATCHDOG: {job.ad} yeniden baslatiliyor "
                                f"(deneme {job.retry_sayisi}/{job.max_retry})"
                            )
                            self._is_calistir(job_id)
                        else:
                            job.durum = "timeout"
                            job.son_hata = f"Timeout ({job.timeout_saniye}s) — {job.max_retry} deneme tukendi"
                            _watchdog_log(
                                f"WATCHDOG: {job.ad} — {job.max_retry} deneme tukendi, durduruldu"
                            )
                            self._json_kaydet()

                time.sleep(10)
            except Exception as e:
                logger.warning("[Cron] Watchdog hatasi: %s", e)
                time.sleep(30)

    def _vakit_geldi_mi(self, job: CronJob, now: datetime) -> bool:
        """Cron ifadesine gore isin calisma zamani gelmis mi?"""
        if not job.cron_ifade:
            return False

        try:
            # Basit cron parser — dakika ve saat kontrolu
            # Format: "dakika saat gun ay gun_haftasi"
            parts = job.cron_ifade.split()
            if len(parts) < 2:
                return False

            dakika_ifade = parts[0]
            saat_ifade = parts[1]

            dakika_eslesir = (
                dakika_ifade == "*"
                or str(now.minute) == dakika_ifade
                or (dakika_ifade.startswith("*/") and now.minute % int(dakika_ifade[2:]) == 0)
            )
            saat_eslesir = (
                saat_ifade == "*"
                or str(now.hour) == saat_ifade
                or (saat_ifade.startswith("*/") and now.hour % int(saat_ifade[2:]) == 0)
            )

            return dakika_eslesir and saat_eslesir
        except Exception:
            return False

    def _is_calistir(self, job_id: str) -> None:
        """Bir isi arkaplanda calistir."""
        job = self._isler.get(job_id)
        if not job:
            return

        if job_id in self._calisan_isler:
            logger.debug("[Cron] %s zaten calisiyor, atlaniyor.", job.ad)
            return

        komut = job.komut or ""
        if job.script:
            script_yolu = Path(job.script)
            if not script_yolu.is_absolute():
                script_yolu = PROJE_KOKU / job.script
            komut = f"{sys.executable} {script_yolu}"

        if not komut:
            logger.warning("[Cron] %s: komut veya script belirtilmemis.", job.ad)
            return

        job.durum = "running"
        job.retry_sayisi = 0
        now = datetime.now(timezone.utc).isoformat()
        job.son_calisma = now

        try:
            process = subprocess.Popen(
                komut,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(PROJE_KOKU),
            )

            self._calisan_isler[job_id] = {
                "process": process,
                "start": time.time(),
                "job_id": job_id,
            }
            job.pid = process.pid

            # Sonucu bekle (ayri thread)
            threading.Thread(
                target=self._is_sonucu_bekle,
                args=(job_id, process),
                daemon=True,
            ).start()

            _watchdog_log(f"BASLATILDI: {job.ad} (pid={process.pid}, timeout={job.timeout_saniye}s)")
            logger.info("[Cron] Is baslatildi: %s (pid=%d, timeout=%ds)", job.ad, process.pid, job.timeout_saniye)
            self._json_kaydet()

        except Exception as e:
            job.durum = "failed"
            job.son_hata = str(e)
            _watchdog_log(f"HATA: {job.ad} — {e}")
            logger.error("[Cron] Is baslatma hatasi: %s: %s", job.ad, e)
            self._json_kaydet()

    def _is_sonucu_bekle(self, job_id: str, process: subprocess.Popen) -> None:
        """Isin bitmesini ve timeout'u yonet."""
        job = self._isler.get(job_id)
        if not job:
            return

        try:
            stdout, stderr = process.communicate(timeout=job.timeout_saniye)
            returncode = process.returncode

            if returncode == 0:
                job.durum = "success"
                job.son_durum = "ok"
                job.son_hata = None
                _watchdog_log(f"BASARILI: {job.ad} (exit={returncode})")
            else:
                job.durum = "failed"
                job.son_durum = "error"
                hata_detay = stderr[-500:] if stderr else f"exit={returncode}"
                job.son_hata = hata_detay
                _watchdog_log(f"HATA: {job.ad} — exit={returncode}")
                logger.error("[Cron] Is basarisiz: %s (exit=%d)", job.ad, returncode)

            logger.info("[Cron] Is tamamlandi: %s (exit=%d, %.1fs)", job.ad, returncode, time.time() - (
                self._calisan_isler.get(job_id, {}).get("start", time.time())
            ))

        except subprocess.TimeoutExpired:
            job.durum = "timeout"
            job.son_hata = f"Timeout ({job.timeout_saniye}s)"
            process.kill()
            _watchdog_log(f"TIMEOUT: {job.ad} — {job.timeout_saniye}s")
        except Exception as e:
            job.durum = "failed"
            job.son_hata = str(e)

        finally:
            self._calisan_isler.pop(job_id, None)
            job.pid = None
            self._json_kaydet()

    def _is_durdur(self, job_id: str) -> bool:
        """Calisan bir isi durdur."""
        info = self._calisan_isler.pop(job_id, None)
        if info and "process" in info:
            try:
                info["process"].kill()
                _watchdog_log(f"DURDURULDU: {self._isler.get(job_id, CronJob()).ad}")
                return True
            except Exception:
                pass
        return False


# ═══════════════════════════════════════════════════════════════════════
#  Tekil Ornek
# ═══════════════════════════════════════════════════════════════════════

_cron_yonetici: Optional[CronManager] = None


def get_cron_manager() -> CronManager:
    """Tekil CronManager ornegini doner."""
    global _cron_yonetici
    if _cron_yonetici is None:
        _cron_yonetici = CronManager()
    return _cron_yonetici


# ═══════════════════════════════════════════════════════════════════════
#  Motor Tool'lari
# ═══════════════════════════════════════════════════════════════════════

def _cron_liste(aktif_mi: str = "") -> str:
    """Motor tool: Kayitli cron islerini listele.

    Kullanim:
        CRON_LISTE()
        CRON_LISTE(aktif_mi="true")
        CRON_LISTE(aktif_mi="false")

    Args:
        aktif_mi: "true", "false" veya bos (hepsi)

    Returns:
        JSON formatinda is listesi
    """
    yonetici = get_cron_manager()
    if aktif_mi == "true":
        isler = yonetici.liste(aktif_mi=True)
    elif aktif_mi == "false":
        isler = yonetici.liste(aktif_mi=False)
    else:
        isler = yonetici.liste()

    if not isler:
        return "[] — hic cron isi bulunamadi"

    return json.dumps(isler, indent=2, ensure_ascii=False, default=str)


def _cron_ekle(
    ad: str = "",
    komut: str = "",
    script: str = "",
    cron_ifade: str = "",
    aktif: bool = True,
    timeout_saniye: int = 300,
    max_retry: int = 3,
    model: str = "",
    aciklama: str = "",
) -> str:
    """Motor tool: Yeni cron isi ekle (override ile).

    Kullanim:
        CRON_EKLE(ad="skill_sync", komut="python3 reymen/cereyan/cron_skill_sync.py",
                   cron_ifade="0 */6 * * *", aciklama="Skill index sync")

    Args:
        ad: Is adi
        komut: Shell komutu
        script: Script yolu
        cron_ifade: Cron expression (ornek: "0 */6 * * *")
        aktif: Aktif mi
        timeout_saniye: Timeout (saniye, varsayilan 300)
        max_retry: Maks tekrar deneme (varsayilan 3)
        model: Model override (bos = varsayilan)
        aciklama: Aciklama

    Returns:
        JSON formatinda sonuc
    """
    if not ad:
        return '{"hata": "Is adi zorunlu"}'

    yonetici = get_cron_manager()
    sonuc = yonetici.ekle(
        ad=ad,
        komut=komut,
        script=script,
        cron_ifade=cron_ifade,
        aktif=aktif,
        timeout_saniye=timeout_saniye,
        max_retry=max_retry,
        model=model if model else None,
        aciklama=aciklama or ad,
    )
    return json.dumps(sonuc, indent=2, ensure_ascii=False, default=str)


def _cron_sil(job_id: str = "") -> str:
    """Motor tool: Cron isini sil.

    Kullanim:
        CRON_SIL(job_id="abc123")

    Args:
        job_id: Silinecek is ID

    Returns:
        JSON formatinda sonuc
    """
    if not job_id:
        return '{"hata": "job_id zorunlu"}'

    yonetici = get_cron_manager()
    sonuc = yonetici.sil(job_id)
    return json.dumps(sonuc, indent=2, ensure_ascii=False, default=str)


# ── Motor Kayit ─────────────────────────────────────────────────────

def motor_kaydet(motor) -> None:
    """Motor'a cron/scheduler araçlarını kaydeder."""
    motor._plugin_arac_kaydet(
        "CRON_LISTE",
        _cron_liste,
        "Kayitli cron islerini listele. "
        "Parametre: aktif_mi (str, opsiyonel: 'true'/'false' bos=hepsi).",
    )
    motor._plugin_arac_kaydet(
        "CRON_EKLE",
        _cron_ekle,
        "Yeni cron isi ekle (override ile). "
        "Parametreler: ad (str, zorunlu), komut (str), script (str), "
        "cron_ifade (str, ornek: '0 */6 * * *'), aktif (bool, varsayilan True), "
        "timeout_saniye (int, varsayilan 300), max_retry (int, varsayilan 3), "
        "model (str, opsiyonel), aciklama (str).",
    )
    motor._plugin_arac_kaydet(
        "CRON_SIL",
        _cron_sil,
        "Cron isini sil. "
        "Parametre: job_id (str, zorunlu).",
    )
    logger.info("[CronManager] Motor araclari kaydedildi: CRON_LISTE, CRON_EKLE, CRON_SIL")
