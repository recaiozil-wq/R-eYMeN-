# -*- coding: utf-8 -*-
"""
batch_engine.py — Toplu işlem motoru.

BatchEngine sinifi ile gorevleri kuyruga ekleyip thread pool ile
paralel olarak calistirir. Gorev durumu takibi, iptal ve sonuc
toplama ozelliklerini saglar.
"""

import os
import json
import time
import uuid
import queue
import threading
import traceback
from typing import Optional, List, Dict, Any, Callable


class BatchEngine:
    """
    Toplu islem motoru.

    Gorevleri bir kuyruga ekler, belirtilen sayida paralel thread ile
    calistirir. Her gorevin durumunu izler, istenirse iptal eder ve
    sonuclari toplar.

    Kullanim:
        engine = BatchEngine()
        engine.ekle(gorev={"komut": "echo test"})
        engine.ekle(gorev={"komut": "echo deneme"})
        sonuclar = engine.calistir(paralel=2)
    """

    DURUM_BEKLIYOR = "bekliyor"
    DURUM_CALISIYOR = "calisiyor"
    DURUM_BASARILI = "basarili"
    DURUM_HATA = "hata"
    DURUM_IPTAL = "iptal"

    def __init__(self, max_kuyruk: int = 1000):
        """
        BatchEngine baslatici.

        Args:
            max_kuyruk: Kuyruk maksimum kapasitesi.
        """
        self._kuyruk: queue.Queue = queue.Queue(maxsize=max_kuyruk)
        self._gorevler: Dict[str, Dict[str, Any]] = {}
        self._sonuclar: Dict[str, Any] = {}
        self._thread_pool: List[threading.Thread] = []
        self._kilit = threading.Lock()
        self._durdu = threading.Event()
        self._calisiyor = False
        self._max_kuyruk = max_kuyruk

    def ekle(self, gorev: Any, gorev_id: Optional[str] = None, meta: Optional[Dict[str, Any]] = None) -> str:
        """
        Kuyruga yeni bir gorev ekler.

        Args:
            gorev: Calistirilacak gorev. Bir fonksiyon, dict veya string olabilir.
                   Fonksiyon ise cagrilir. Dict ise islenir. String ise komut olarak calistirilir.
            gorev_id: Opsiyonel gorev kimligi. Verilmezse UUID olusturulur.
            meta: Goreve ait metadata (etiketler, oncelik vb.).

        Returns:
            Gorev kimligi (str).

        Raises:
            queue.Full: Kuyruk doluysa.
        """
        kid = gorev_id or str(uuid.uuid4())
        with self._kilit:
            kayit = {
                "id": kid,
                "gorev": gorev,
                "meta": meta or {},
                "durum": self.DURUM_BEKLIYOR,
                "eklenme": time.time(),
                "baslama": None,
                "bitis": None,
                "hata": None,
            }
            self._gorevler[kid] = kayit
        self._kuyruk.put(kid, block=True)
        return kid

    def calistir(self, paralel: int = 3) -> Dict[str, List[Dict[str, Any]]]:
        """
        Kuyruktaki gorevleri thread pool ile paralel calistirir.

        Args:
            paralel: Ayni anda calisacak maksimum thread sayisi (1-20 arasi).

        Returns:
            Basarili ve hatali gorev sonuclarini iceren sozluk.
        """
        try:
            if self._calisiyor:
                return {"hata": "Motor zaten calisiyor."}

            paralel = max(1, min(paralel, 20))
            self._calisiyor = True
            self._durdu.clear()
            self._thread_pool = []
            self._sonuclar = {}

            baslangic = time.time()

            # Thread'leri baslat
            for i in range(paralel):
                t = threading.Thread(target=self._isci_thread, args=(i,), daemon=True)
                t.start()
                self._thread_pool.append(t)

            # Tüm görevler işlenene kadar bekle, sonra thread'leri durdur
            self._kuyruk.join()
            self._durdu.set()
            for t in self._thread_pool:
                t.join(timeout=5)

            self._calisiyor = False
            gecen_sure = time.time() - baslangic

            # Sonuclari grupla
            basarili = []
            hatali = []
            iptal = []
            for gorev_id, sonuc in self._sonuclar.items():
                if sonuc.get("durum") == self.DURUM_BASARILI:
                    basarili.append(sonuc)
                elif sonuc.get("durum") == self.DURUM_IPTAL:
                    iptal.append(sonuc)
                else:
                    hatali.append(sonuc)

            return {
                "basarili": basarili,
                "hatali": hatali,
                "iptal": iptal,
                "toplam": len(self._sonuclar),
                "gecen_sure": round(gecen_sure, 2),
            }

        except Exception as e:
            self._calisiyor = False
            return {"hata": f"Calistirma hatasi: {e}"}

    def _isci_thread(self, thread_no: int) -> None:
        """
        Thread calisani. Kuyruktan gorev alir ve calistirir.

        Args:
            thread_no: Thread numarasi (log icin).
        """
        while not self._durdu.is_set():
            try:
                gorev_id = self._kuyruk.get(block=True, timeout=1.0)
            except queue.Empty:
                continue

            if self._durdu.is_set():
                self._kuyruk.task_done()
                break

            with self._kilit:
                if gorev_id not in self._gorevler:
                    self._kuyruk.task_done()
                    continue
                kayit = self._gorevler[gorev_id]
                if kayit["durum"] == self.DURUM_IPTAL:
                    self._kuyruk.task_done()
                    continue
                kayit["durum"] = self.DURUM_CALISIYOR
                kayit["baslama"] = time.time()

            try:
                gorev_verisi = kayit["gorev"]
                sonuc = None

                # Gorev tipine gore calistir
                if callable(gorev_verisi):
                    sonuc = gorev_verisi()
                elif isinstance(gorev_verisi, dict):
                    sonuc = json.dumps(gorev_verisi, ensure_ascii=False)
                else:
                    sonuc = str(gorev_verisi)

                with self._kilit:
                    kayit["durum"] = self.DURUM_BASARILI
                    kayit["bitis"] = time.time()
                    self._sonuclar[gorev_id] = {
                        "id": gorev_id,
                        "durum": self.DURUM_BASARILI,
                        "sonuc": sonuc,
                        "thread": thread_no,
                    }

            except Exception as e:
                with self._kilit:
                    kayit["durum"] = self.DURUM_HATA
                    kayit["bitis"] = time.time()
                    kayit["hata"] = str(e)
                    self._sonuclar[gorev_id] = {
                        "id": gorev_id,
                        "durum": self.DURUM_HATA,
                        "hata": str(e),
                        "traceback": traceback.format_exc(),
                        "thread": thread_no,
                    }

            finally:
                self._kuyruk.task_done()

    def durum(self, gorev_id: str) -> Optional[Dict[str, Any]]:
        """
        Bir gorevin guncel durumunu dondurur.

        Args:
            gorev_id: Sorgulanacak gorevin kimligi.

        Returns:
            Gorev kaydi sozlugu veya None (gorev bulunamazsa).
        """
        with self._kilit:
            kayit = self._gorevler.get(gorev_id)
            if kayit:
                return dict(kayit)
            return None

    def iptal(self, gorev_id: Optional[str] = None) -> int:
        """
        Gorev veya gorevleri iptal eder.

        Args:
            gorev_id: Iptal edilecek gorev. None ise tum bekleyen gorevler iptal edilir.

        Returns:
            Iptal edilen gorev sayisi.
        """
        iptal_sayisi = 0
        with self._kilit:
            if gorev_id:
                kayit = self._gorevler.get(gorev_id)
                if kayit and kayit["durum"] in (self.DURUM_BEKLIYOR, self.DURUM_CALISIYOR):
                    kayit["durum"] = self.DURUM_IPTAL
                    self._sonuclar[gorev_id] = {
                        "id": gorev_id,
                        "durum": self.DURUM_IPTAL,
                        "sonuc": "Gorev iptal edildi",
                    }
                    iptal_sayisi = 1
            else:
                for kid, kayit in self._gorevler.items():
                    if kayit["durum"] in (self.DURUM_BEKLIYOR, self.DURUM_CALISIYOR):
                        kayit["durum"] = self.DURUM_IPTAL
                        self._sonuclar[kid] = {
                            "id": kid,
                            "durum": self.DURUM_IPTAL,
                            "sonuc": "Gorev iptal edildi",
                        }
                        iptal_sayisi += 1

        if iptal_sayisi > 0:
            self._durdu.set()
        return iptal_sayisi

    def sonuclar(self, durum_filtre: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Tamamlanan gorev sonuclarini dondurur.

        Args:
            durum_filtre: Opsiyonel durum filtresi ("basarili", "hata", "iptal").
                          None ise tum sonuclar.

        Returns:
            Sonuc listesi.
        """
        with self._kilit:
            if durum_filtre:
                return [
                    s for s in self._sonuclar.values()
                    if s.get("durum") == durum_filtre
                ]
            return list(self._sonuclar.values())

    def listele(self, durum: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Tum gorevleri listeler.

        Args:
            durum: Opsiyonel durum filtresi.

        Returns:
            Gorev kayitlari listesi.
        """
        with self._kilit:
            if durum:
                return [dict(k) for k in self._gorevler.values() if k["durum"] == durum]
            return [dict(k) for k in self._gorevler.values()]

    def temizle(self) -> int:
        """
        Tamamlanmis gorevleri ve sonuclari temizler.

        Returns:
            Temizlenen kayit sayisi.
        """
        with self._kilit:
            tamam_durumlar = {self.DURUM_BASARILI, self.DURUM_HATA, self.DURUM_IPTAL}
            silinecek = [
                kid for kid, kayit in self._gorevler.items()
                if kayit["durum"] in tamam_durumlar
            ]
            for kid in silinecek:
                del self._gorevler[kid]
                self._sonuclar.pop(kid, None)
            return len(silinecek)

    def run(self, **kwargs) -> str:
        """
        Evrensel calistirma metodu.

        kwargs icinde:
            - action: "ekle", "calistir", "durum", "iptal", "sonuclar", "listele"
            - Diger parametreler ilgili metoda yonlendirilir.

        Returns:
            JSON formatinda sonuc.
        """
        try:
            action = kwargs.pop("action", "calistir")
            if action == "ekle":
                gorev_id = self.ekle(**kwargs)
                return json.dumps({"gorev_id": gorev_id}, ensure_ascii=False)
            elif action == "calistir":
                paralel = kwargs.get("paralel", 3)
                sonuc = self.calistir(paralel=paralel)
                return json.dumps(sonuc, ensure_ascii=False, indent=2, default=str)
            elif action == "durum":
                gorev_id = kwargs.get("gorev_id", "")
                d = self.durum(gorev_id)
                return json.dumps(d, ensure_ascii=False, indent=2, default=str) if d else "Gorev bulunamadi"
            elif action == "iptal":
                gorev_id = kwargs.get("gorev_id")
                adet = self.iptal(gorev_id)
                return json.dumps({"iptal_edilen": adet}, ensure_ascii=False)
            elif action == "sonuclar":
                filtre = kwargs.get("durum_filtre")
                s = self.sonuclar(durum_filtre=filtre)
                return json.dumps(s, ensure_ascii=False, indent=2, default=str)
            elif action == "listele":
                durum_filtre = kwargs.get("durum")
                g = self.listele(durum=durum_filtre)
                return json.dumps(g, ensure_ascii=False, indent=2, default=str)
            else:
                return json.dumps({"hata": f"Bilinmeyen action: {action}"}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"hata": str(e)}, ensure_ascii=False)


_GLOBAL_ENGINE = BatchEngine()


def motor_kaydet(motor):
    """BatchEngine araçlarını motora kaydet."""
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return
    motor._plugin_arac_kaydet(
        "BATCH_EKLE",
        lambda gorev="": (
            _GLOBAL_ENGINE.ekle(gorev=str(gorev)),
        )[0],
        "Batch kuyruğuna görev ekle, gorev_id döndürür (gorev: çalıştırılacak metin/komut)",
    )
    motor._plugin_arac_kaydet(
        "BATCH_CALISTIR",
        lambda paralel="3": _GLOBAL_ENGINE.run(action="calistir", paralel=int(paralel)),
        "Kuyruktaki görevleri paralel çalıştır (paralel: thread sayısı 1-20)",
    )
    motor._plugin_arac_kaydet(
        "BATCH_LISTELE",
        lambda durum="": _GLOBAL_ENGINE.run(action="listele", durum=durum or None),
        "Batch kuyruğundaki görevleri listele (durum: bekliyor/calisiyor/basarili/hata/boş=hepsi)",
    )
    motor._plugin_arac_kaydet(
        "BATCH_DURUM",
        lambda gorev_id="": _GLOBAL_ENGINE.run(action="durum", gorev_id=str(gorev_id)),
        "Batch görevi durumunu sorgula (gorev_id)",
    )


if __name__ == "__main__":
    engine = BatchEngine()
    print("BatchEngine hazir.")

    # Test gorevleri
    def test_gorevi(isim: str):
        return f"{isim} tamamlandi"

    engine.ekle(gorev=lambda: test_gorevi("Gorev-1"), gorev_id="g1")
    engine.ekle(gorev=lambda: test_gorevi("Gorev-2"), gorev_id="g2")
    engine.ekle(gorev=lambda: test_gorevi("Gorev-3"), gorev_id="g3")

    sonuc = engine.calistir(paralel=2)
    print(f"Calistirma sonucu: {len(sonuc.get('basarili', []))} basarili, "
          f"{len(sonuc.get('hatali', []))} hatali")
    print("Durum g1:", engine.durum("g1"))
