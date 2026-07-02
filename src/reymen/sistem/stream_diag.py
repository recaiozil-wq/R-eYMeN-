# -*- coding: utf-8 -*-
"""
stream_diag.py — StreamDiagnostics.
Stream teshis ve performans izleme modulu.
ReYMeN kimligi: Turkce docstring, try/except, class-based.
"""

import time
import statistics
from datetime import datetime
from collections import deque
import logging
logger = logging.getLogger(__name__)


class StreamDiagnostics:
    """StreamDiagnostics: Stream performansini izler ve teshis eder.

    LLM stream yanitlarinin hizini, gecikmesini, paket kaybini
    olcer ve detayli raporlar uretir.
    """

    def __init__(self, max_kayit=100):
        """StreamDiagnostics baslat.

        Args:
            max_kayit: Tutulacak maksimum kayit sayisi
        """
        self._stream_kayitlari = {}
        self._olcum_gecmisi = deque(maxlen=max_kayit)
        self._hiz_verileri = deque(maxlen=max_kayit)
        self._gecikme_verileri = deque(maxlen=max_kayit)
        self._paket_kaybi_verileri = deque(maxlen=max_kayit)

    def izle(self, stream_id, stream_uretec=None):
        """Stream'i izlemeye basla.

        Args:
            stream_id: Stream tanimlayici
            stream_uretec: Stream yineleyicisi (None = sadece kayit)

        Returns:
            dict: Stream kayit bilgisi
        """
        try:
            kayit = {
                "stream_id": stream_id,
                "baslangic": datetime.now().isoformat(),
                "durum": "izleniyor",
                "token_sayisi": 0,
                "toplam_boyut": 0,
                "ilk_token_suresi": None,
                "toplam_sure": None,
            }

            if stream_id in self._stream_kayitlari:
                print(f"[StreamDiagnostics] Stream zaten izleniyor: {stream_id}")
                return self._stream_kayitlari[stream_id]

            if stream_uretec is not None:
                baslangic = time.time()
                ilk_token = None
                token_sayisi = 0
                toplam_boyut = 0

                try:
                    for i, chunk in enumerate(stream_uretec):
                        simdi = time.time()
                        if i == 0:
                            ilk_token = simdi - baslangic
                        token_sayisi += 1
                        chunk_str = str(chunk)
                        toplam_boyut += len(chunk_str)

                    toplam_sure = time.time() - baslangic

                    kayit.update({
                        "durum": "tamamlandi",
                        "token_sayisi": token_sayisi,
                        "toplam_boyut": toplam_boyut,
                        "ilk_token_suresi": round(ilk_token, 4) if ilk_token else 0,
                        "toplam_sure": round(toplam_sure, 4),
                        "bitis": datetime.now().isoformat(),
                    })

                    if token_sayisi > 0:
                        self._olcum_gecmisi.append(kayit)

                except Exception as stream_hata:
                    kayit.update({
                        "durum": "hata",
                        "hata": str(stream_hata),
                        "bitis": datetime.now().isoformat(),
                    })
                    print(f"[StreamDiagnostics] Stream hatasi ({stream_id}): {stream_hata}")

            self._stream_kayitlari[stream_id] = kayit
            return kayit

        except Exception as hata:
            print(f"[StreamDiagnostics] Izleme hatasi: {hata}")
            return {"stream_id": stream_id, "durum": "hata", "hata": str(hata)}

    def hiz_olc(self, stream_id=None):
        """Stream hizini olc (token/saniye).

        Args:
            stream_id: Belirli bir stream (None = son olcum)

        Returns:
            dict: Hiz bilgisi
        """
        try:
            if stream_id:
                kayit = self._stream_kayitlari.get(stream_id)
                if not kayit:
                    return {"hata": f"Stream bulunamadi: {stream_id}"}
                if not kayit.get("toplam_sure") or kayit.get("toplam_sure") == 0:
                    return {"hata": "Stream henuz tamamlanmadi"}
                hiz = kayit["token_sayisi"] / kayit["toplam_sure"]
                hiz_verisi = {
                    "stream_id": stream_id,
                    "token_sayisi": kayit["token_sayisi"],
                    "toplam_sure": kayit["toplam_sure"],
                    "hiz_token_sn": round(hiz, 2),
                }
                self._hiz_verileri.append(hiz_verisi)
                return hiz_verisi
            else:
                if not self._olcum_gecmisi:
                    return {"hata": "Henuz olcum yok"}
                son = self._olcum_gecmisi[-1]
                if son.get("toplam_sure", 0) > 0:
                    hiz = son["token_sayisi"] / son["toplam_sure"]
                    return {"hiz_token_sn": round(hiz, 2), "kaynak": "son_olcum"}
                return {"hata": "Son olcumde sure bilgisi yok"}

        except ZeroDivisionError:
            return {"hata": "Sifira bolme: sure henuz olculmedi"}
        except Exception as hata:
            print(f"[StreamDiagnostics] Hiz olcme hatasi: {hata}")
            return {"hata": str(hata)}

    def gecikme_olc(self, stream_id=None):
        """Stream gecikmesini olc (ms).

        Args:
            stream_id: Belirli bir stream (None = son)

        Returns:
            dict: Gecikme bilgisi
        """
        try:
            if stream_id:
                kayit = self._stream_kayitlari.get(stream_id)
                if not kayit:
                    return {"hata": f"Stream bulunamadi: {stream_id}"}
                ilk_token = kayit.get("ilk_token_suresi", 0)
                gecikme_ms = round(ilk_token * 1000, 2) if ilk_token else 0
                veri = {
                    "stream_id": stream_id,
                    "ilk_token_suresi_sn": ilk_token,
                    "gecikme_ms": gecikme_ms,
                }
                if gecikme_ms > 0:
                    self._gecikme_verileri.append(veri)
                return veri
            else:
                if not self._olcum_gecmisi:
                    return {"hata": "Henuz olcum yok"}
                son = self._olcum_gecmisi[-1]
                ilk = son.get("ilk_token_suresi", 0)
                return {
                    "gecikme_ms": round(ilk * 1000, 2) if ilk else 0,
                    "kaynak": "son_olcum",
                }

        except Exception as hata:
            print(f"[StreamDiagnostics] Gecikme olcme hatasi: {hata}")
            return {"hata": str(hata)}

    def paket_kaybi(self, stream_id=None):
        """Stream paket kaybini hesapla.

        Args:
            stream_id: Belirli bir stream (None = tumu)

        Returns:
            dict: Paket kaybi bilgisi
        """
        try:
            if stream_id:
                kayit = self._stream_kayitlari.get(stream_id)
                if not kayit:
                    return {"hata": f"Stream bulunamadi: {stream_id}"}
                beklenen = kayit.get("beklenen_token", kayit.get("token_sayisi", 0))
                alinan = kayit.get("token_sayisi", 0)
                kayip = max(0, beklenen - alinan)
                kayip_orani = round((kayip / max(beklenen, 1)) * 100, 2)
                veri = {
                    "stream_id": stream_id,
                    "beklenen_token": beklenen,
                    "alinan_token": alinan,
                    "kayip_token": kayip,
                    "kayip_orani": kayip_orani,
                }
                self._paket_kaybi_verileri.append(veri)
                return veri
            else:
                toplam_alindi = sum(
                    k.get("token_sayisi", 0) for k in self._olcum_gecmisi
                )
                toplam_beklenen = sum(
                    k.get("token_sayisi", 0) for k in self._olcum_gecmisi
                )
                return {
                    "toplam_stream": len(self._olcum_gecmisi),
                    "toplam_token": toplam_alindi,
                    "kayip_orani_ortalama": 0.0,
                }

        except Exception as hata:
            print(f"[StreamDiagnostics] Paket kaybi hesabi hatasi: {hata}")
            return {"hata": str(hata)}

    def raporla(self, stream_id=None):
        """Detayli stream raporu olustur.

        Args:
            stream_id: Belirli bir stream (None = tum istatistikler)

        Returns:
            dict: Rapor
        """
        try:
            if stream_id:
                kayit = self._stream_kayitlari.get(stream_id)
                if not kayit:
                    return {"hata": f"Stream bulunamadi: {stream_id}"}
                hiz = self.hiz_olc(stream_id)
                gecikme = self.gecikme_olc(stream_id)
                kayip = self.paket_kaybi(stream_id)
                return {
                    "stream_id": stream_id,
                    "kayit": kayit,
                    "hiz": hiz,
                    "gecikme": gecikme,
                    "paket_kaybi": kayip,
                }

            if not self._olcum_gecmisi:
                return {"hata": "Henuz olcum yok"}

            hizlar = [
                k["token_sayisi"] / k["toplam_sure"]
                for k in self._olcum_gecmisi
                if k.get("toplam_sure", 0) > 0
            ]
            gecikmeler = [
                k.get("ilk_token_suresi", 0) * 1000
                for k in self._olcum_gecmisi
                if k.get("ilk_token_suresi")
            ]

            rapor = {
                "toplam_stream": len(self._olcum_gecmisi),
                "ortalama_hiz_token_sn": round(statistics.mean(hizlar), 2) if hizlar else 0,
                "ortalama_gecikme_ms": round(statistics.mean(gecikmeler), 2) if gecikmeler else 0,
                "max_hiz_token_sn": round(max(hizlar), 2) if hizlar else 0,
                "min_hiz_token_sn": round(min(hizlar), 2) if hizlar else 0,
                "toplam_token": sum(k.get("token_sayisi", 0) for k in self._olcum_gecmisi),
            }
            return rapor

        except statistics.StatisticsError:
            return {"hata": "Istatistik hesaplama hatasi", "toplam_stream": len(self._olcum_gecmisi)}
        except Exception as hata:
            print(f"[StreamDiagnostics] Raporlama hatasi: {hata}")
            return {"hata": str(hata)}

    def stream_durum(self, stream_id):
        """Belirli bir stream'in durumunu sorgula.

        Args:
            stream_id: Stream tanimlayici

        Returns:
            dict: Durum bilgisi
        """
        try:
            kayit = self._stream_kayitlari.get(stream_id)
            if not kayit:
                return {"bulunamadi": True, "stream_id": stream_id}
            return kayit
        except Exception:
            return {"hata": "Sorgulama hatasi"}

    def tum_streamlar(self):
        """Izlenen tum streamleri listele.

        Returns:
            list: Stream ID listesi
        """
        return list(self._stream_kayitlari.keys())

    def temizle(self):
        """Tum verileri temizle.

        Returns:
            int: Temizlenen kayit sayisi
        """
        try:
            sayi = len(self._stream_kayitlari)
            self._stream_kayitlari.clear()
            self._olcum_gecmisi.clear()
            self._hiz_verileri.clear()
            self._gecikme_verileri.clear()
            self._paket_kaybi_verileri.clear()
            return sayi
        except Exception:
            return 0


if __name__ == "__main__":
    sd = StreamDiagnostics()

    def test_stream():
        for i in range(5):
            time.sleep(0.05)
            yield f"token_{i}"

    sd.izle("test_1", test_stream())
    print(f"Hiz: {sd.hiz_olc('test_1')}")
    print(f"Gecikme: {sd.gecikme_olc('test_1')}")
    print(f"Paket kaybi: {sd.paket_kaybi('test_1')}")
    print(f"Rapor: {sd.raporla()}")
