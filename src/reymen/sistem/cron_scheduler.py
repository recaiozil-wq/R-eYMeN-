# -*- coding: utf-8 -*-
"""
cron_scheduler.py — Zamanlanmış görev yöneticisi.

CronScheduler sinifi ile cron benzeri zamanlanmis gorevleri
yönetir. Cron expression parser ile zaman ifadelerini cozumler,
gorevleri belirtilen zamanlarda calistirir.
"""

import os
import re
import json
import time
import uuid
import threading
import calendar
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
import logging
logger = logging.getLogger(__name__)


class CronExpressionParser:
    """
    Cron ifadelerini cozumler.

    Desteklenen format: "dakika saat gun ay hafta_gunu"
    Ayrik degerler (1,2,3), aralik (1-5), yildiz (*), adim (*/2)
    ve karmasi (1-5,10-15) desteklenir.

    Ornekler:
        "* * * * *"     -> Her dakika
        "0 * * * *"     -> Her saat basi
        "0 9 * * 1-5"   -> Haftaici her gun 09:00
        "*/15 * * * *"  -> Her 15 dakikada bir
    """

    def __init__(self, ifade: str):
        """
        Cron ifadesini cozumler.

        Args:
            ifade: 5 alanli cron ifadesi (dakika saat gun ay hafta_gunu).

        Raises:
            ValueError: Gecersiz cron ifadesi.
        """
        self.ifade = ifade.strip()
        alanlar = self.ifade.split()
        if len(alanlar) != 5:
            raise ValueError(f"Gecersiz cron ifadesi: '{ifade}'. 5 alan gerekli (dakika saat gun ay hafta_gunu).")

        self.dakika = self._parse_alan(alanlar[0], 0, 59)
        self.saat = self._parse_alan(alanlar[1], 0, 23)
        self.gun = self._parse_alan(alanlar[2], 1, 31)
        self.ay = self._parse_alan(alanlar[3], 1, 12)
        self.hafta_gunu = self._parse_alan(alanlar[4], 0, 6)

    def _parse_alan(self, alan: str, min_val: int, max_val: int) -> set:
        """
        Cron alanini cozumler.

        Args:
            alan: Cron alani (*, 5, 1-5, */15, 1,3,5 seklinde).
            min_val: Alanin minimum degeri.
            max_val: Alanin maksimum degeri.

        Returns:
            Eslesen degerler seti.
        """
        degerler = set()
        if alan == "*":
            return set(range(min_val, max_val + 1))

        for parca in alan.split(","):
            parca = parca.strip()
            adim = 1
            if "/" in parca:
                parca, adim_str = parca.split("/", 1)
                adim = int(adim_str)

            if parca == "*":
                for d in range(min_val, max_val + 1, adim):
                    degerler.add(d)
            elif "-" in parca:
                bas, bit = parca.split("-", 1)
                for d in range(int(bas), int(bit) + 1, adim):
                    if min_val <= d <= max_val:
                        degerler.add(d)
            else:
                d = int(parca)
                if min_val <= d <= max_val:
                    degerler.add(d)

        return degerler

    def eslesiyor(self, an: Optional[datetime] = None) -> bool:
        """
        Verilen zamanin cron ifadesiyle eslesip eslesmedigini kontrol eder.

        Args:
            an: Kontrol edilecek zaman. None ise simdiki zaman kullanilir.

        Returns:
            Eslesiyor mu?
        """
        an = an or datetime.now()
        if an.minute not in self.dakika:
            return False
        if an.hour not in self.saat:
            return False
        if an.day not in self.gun:
            return False
        if an.month not in self.ay:
            return False
        hafta_gunu = an.weekday()  # 0=Pazartesi
        # Cron'da 0=Pazar, 6=Cumartesi
        cron_hafta_gunu = (hafta_gunu + 1) % 7
        if cron_hafta_gunu not in self.hafta_gunu:
            return False
        return True

    def __repr__(self) -> str:
        return f"CronExpression({self.ifade})"


class CronScheduler:
    """
    Zamanlanmis gorev yoneticisi.

    Gorevleri cron ifadelerine gore zamanlar, belirtilen
    zamanda fonksiyonlari calistirir. Ayri bir thread'de
    calisarak surekli zaman kontrolu yapar.

    Kullanim:
        scheduler = CronScheduler()
        scheduler.ekle("gunluk_rapor", "0 9 * * *", lambda: print("Rapor"))
        scheduler.baslat()
    """

    def __init__(self, json_yolu: Optional[str] = None):
        """
        CronScheduler baslatici.

        Args:
            json_yolu: Gorevleri JSON dosyasina kaydetmek icin yol.
                       None ise dosyaya kaydedilmez.
        """
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._thread: Optional[threading.Thread] = None
        self._durdu = threading.Event()
        self._kilit = threading.Lock()
        self._calisiyor = False
        self._json_yolu = json_yolu
        self._kontrol_araligi = 30  # saniye

        # Kaydedilmis gorevleri yukle
        if json_yolu and os.path.exists(json_yolu):
            try:
                with open(json_yolu, "r", encoding="utf-8") as f:
                    kayitli = json.load(f)
                for job_id, job_data in kayitli.items():
                    try:
                        job_data["parser"] = CronExpressionParser(job_data["cron"])
                        self._jobs[job_id] = job_data
                    except ValueError:
                        continue
            except Exception as _cron_sch_e165:
                print(f"[UYARI] cron_scheduler.py:166 - {_cron_sch_e165}")

    def ekle(self, job_id: str, zaman: str, fonk: Callable, args: Optional[tuple] = None,
             tek_seferlik: bool = False, aciklama: str = "") -> bool:
        """
        Yeni bir zamanlanmis gorev ekler.

        Args:
            job_id: Gorev kimligi (benzersiz).
            zaman: Cron ifadesi (ornek: "0 9 * * *").
            fonk: Calistirilacak fonksiyon.
            args: Fonksiyona gonderilecek argumanlar.
            tek_seferlik: True ise bir kez calisip silinir.
            aciklama: Gorev aciklamasi.

        Returns:
            Basarili mi?
        """
        try:
            with self._kilit:
                parser = CronExpressionParser(zaman)
                self._jobs[job_id] = {
                    "id": job_id,
                    "cron": zaman,
                    "parser": parser,
                    "fonk": fonk,
                    "args": args or (),
                    "tek_seferlik": tek_seferlik,
                    "aciklama": aciklama,
                    "eklenme": time.time(),
                    "son_calisma": None,
                    "calisma_sayisi": 0,
                }
                self._kaydet()
                return True
        except ValueError as e:
            print(f"[Cron] Gorev eklenemedi ({job_id}): {e}")
            return False
        except Exception as e:
            print(f"[Cron] Beklenmeyen hata: {e}")
            return False

    def sil(self, job_id: str) -> bool:
        """
        Bir zamanlanmis gorevi siler.

        Args:
            job_id: Silinecek gorevin kimligi.

        Returns:
            Basarili mi?
        """
        try:
            with self._kilit:
                if job_id in self._jobs:
                    del self._jobs[job_id]
                    self._kaydet()
                    return True
                return False
        except Exception as e:
            print(f"[Cron] Silme hatasi ({job_id}): {e}")
            return False

    def listele(self) -> List[Dict[str, Any]]:
        """
        Tum zamanlanmis gorevleri listeler.

        Returns:
            Gorev bilgileri listesi (parser objesi haric).
        """
        try:
            with self._kilit:
                liste = []
                for job_id, job in self._jobs.items():
                    liste.append({
                        "id": job["id"],
                        "cron": job["cron"],
                        "aciklama": job.get("aciklama", ""),
                        "tek_seferlik": job.get("tek_seferlik", False),
                        "eklenme": job.get("eklenme", 0),
                        "son_calisma": job.get("son_calisma"),
                        "calisma_sayisi": job.get("calisma_sayisi", 0),
                    })
                return liste
        except Exception as e:
            return [{"hata": str(e)}]

    def baslat(self) -> bool:
        """
        Zamanlayiciyi baslatir. Ayri bir thread'de calisir.

        Returns:
            Basarili mi?
        """
        try:
            if self._calisiyor:
                return False
            self._calisiyor = True
            self._durdu.clear()
            self._thread = threading.Thread(target=self._dongu, daemon=True)
            self._thread.start()
            return True
        except Exception as e:
            print(f"[Cron] Baslatma hatasi: {e}")
            return False

    def durdur(self) -> bool:
        """
        Zamanlayiciyi durdurur.

        Returns:
            Basarili mi?
        """
        try:
            if not self._calisiyor:
                return False
            self._durdu.set()
            self._calisiyor = False
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=5)
            return True
        except Exception as e:
            print(f"[Cron] Durdurma hatasi: {e}")
            return False

    def execute_tick_cycle(self) -> int:
        """Gateway tick loop'u icin: bir tikta calisacak gorevleri kontrol edip calistirir.
        
        Returns:
            Calistirilan gorev sayisi.
        """
        sayac = 0
        an = datetime.now()
        with self._kilit:
            jobs_copy = dict(self._jobs)
        for job_id, job in jobs_copy.items():
            try:
                if not job.get("aktif", True):
                    continue
                parser = CronExpressionParser(job["zaman"])
                if parser.eslesiyor(an):
                    self._gorev_calistir(job_id, job)
                    sayac += 1
            except Exception:
                continue
        return sayac

    def _dongu(self) -> None:
        """
        Ana zamanlayici dongusu. Her N saniyede bir gorevleri kontrol eder.
        """
        while not self._durdu.is_set():
            try:
                now = datetime.now()
                calistirilacak = []

                with self._kilit:
                    for job_id, job in list(self._jobs.items()):
                        try:
                            if job["parser"].eslesiyor(now):
                                calistirilacak.append((job_id, job))
                        except Exception:
                            continue

                # Gorevleri calistir
                for job_id, job in calistirilacak:
                    try:
                        threading.Thread(
                            target=self._gorev_calistir,
                            args=(job_id, job),
                            daemon=True
                        ).start()
                    except Exception as e:
                        print(f"[Cron] Gorev baslatma hatasi ({job_id}): {e}")

            except Exception as e:
                print(f"[Cron] Dongu hatasi: {e}")

            # Bekle (kontrol araligi kadar)
            self._durdu.wait(self._kontrol_araligi)

    def _gorev_calistir(self, job_id: str, job: Dict[str, Any]) -> None:
        """
        Bir gorevi calistirir ve durumunu gunceller.

        Args:
            job_id: Gorev kimligi.
            job: Gorev kaydi.
        """
        try:
            if callable(job.get("fonk")):
                job["fonk"](*job.get("args", ()))

            with self._kilit:
                job["son_calisma"] = time.time()
                job["calisma_sayisi"] = job.get("calisma_sayisi", 0) + 1

                if job.get("tek_seferlik"):
                    self._jobs.pop(job_id, None)

            self._kaydet()

        except Exception as e:
            print(f"[Cron] Gorev hatasi ({job_id}): {e}")

    def _kaydet(self) -> None:
        """Gorevleri JSON dosyasina kaydeder."""
        if not self._json_yolu:
            return
        try:
            os.makedirs(os.path.dirname(self._json_yolu), exist_ok=True)
            kayit = {}
            for job_id, job in self._jobs.items():
                kayit[job_id] = {
                    "id": job["id"],
                    "cron": job["cron"],
                    "aciklama": job.get("aciklama", ""),
                    "tek_seferlik": job.get("tek_seferlik", False),
                    "eklenme": job.get("eklenme", 0),
                    "son_calisma": job.get("son_calisma"),
                    "calisma_sayisi": job.get("calisma_sayisi", 0),
                }
            with open(self._json_yolu, "w", encoding="utf-8") as f:
                json.dump(kayit, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Cron] Kaydetme hatasi: {e}")

    def run(self, **kwargs) -> str:
        """
        Evrensel calistirma metodu.

        kwargs icinde:
            - action: "ekle", "sil", "listele", "baslat", "durdur"
            - Diger parametreler ilgili metoda yonlendirilir.

        Returns:
            JSON formatinda sonuc.
        """
        import json as json_mod
        try:
            action = kwargs.pop("action", "listele")
            if action == "ekle":
                basarili = self.ekle(**kwargs)
                return json_mod.dumps({"basarili": basarili}, ensure_ascii=False)
            elif action == "sil":
                basarili = self.sil(kwargs.get("job_id", ""))
                return json_mod.dumps({"basarili": basarili}, ensure_ascii=False)
            elif action == "listele":
                return json_mod.dumps(self.listele(), ensure_ascii=False, indent=2)
            elif action == "baslat":
                basarili = self.baslat()
                return json_mod.dumps({"basarili": basarili}, ensure_ascii=False)
            elif action == "durdur":
                basarili = self.durdur()
                return json_mod.dumps({"basarili": basarili}, ensure_ascii=False)
            else:
                return json_mod.dumps({"hata": f"Bilinmeyen action: {action}"}, ensure_ascii=False)
        except Exception as e:
            return json_mod.dumps({"hata": str(e)}, ensure_ascii=False)


if __name__ == "__main__":
    sched = CronScheduler()
    sched.ekle("test_job", "* * * * *", lambda: print("Her dakika calisir"))
    print("CronScheduler hazir.")
    print("Gorevler:", sched.listele())
    print("Cron test:", CronExpressionParser("0 9 * * *").eslesiyor())
