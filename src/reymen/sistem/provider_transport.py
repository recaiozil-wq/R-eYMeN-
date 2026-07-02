# -*- coding: utf-8 -*-
"""provider_transport.py — Provider tasima katmani.
Farkli saglayicilara mesaj gonderir, baglanti yonetimi yapar.
ReYMeN kimligi: Turkce docstring, try/except, class-based.
"""

import json
import time
import socket
from datetime import datetime
import logging
logger = logging.getLogger(__name__)


class ProviderTransport:
    """ProviderTransport: Saglayicilar arasi iletisim katmani.

    Farkli LLM saglayicilarina (local, API, ozel) mesaj gonderir,
    baglanti durumunu yonetir ve saglayici kullanilabilirligini kontrol eder.
    """

    def __init__(self, config=None):
        """ProviderTransport baslat.

        Args:
            config: Saglayici yapilandirmalari (sozluk)
        """
        self._baglantilar = {}
        self._aktif_saglayicilar = set()
        self._mesaj_gecmisi = []
        self._config = config or {}
        self._zaman_asimi = self._config.get("zaman_asimi", 30)
        self._maks_deneme = self._config.get("maks_deneme", 3)

    def gonder(self, mesaj, provider="local"):
        """Belirtilen saglayiciya mesaj gonder.

        Args:
            mesaj: Gonderilecek mesaj (string veya dict)
            provider: Hedef saglayici adi

        Returns:
            dict: Yanit veya hata bilgisi
        """
        try:
            if provider not in self._baglantilar:
                raise ConnectionError(f"Saglayici baglantisi yok: {provider}")

            if isinstance(mesaj, dict):
                mesaj_str = json.dumps(mesaj, ensure_ascii=False)
            else:
                mesaj_str = str(mesaj)

            kayit = {
                "zaman": datetime.now().isoformat(),
                "provider": provider,
                "mesaj": mesaj_str[:200],
                "yontem": "gonder",
            }

            for deneme in range(self._maks_deneme):
                try:
                    yanit = self._baglantilar[provider]["kanal"](
                        mesaj_str, timeout=self._zaman_asimi
                    )
                    kayit["basari"] = True
                    kayit["deneme"] = deneme + 1
                    self._mesaj_gecmisi.append(kayit)
                    return {"basari": True, "yanit": yanit, "provider": provider}
                except TimeoutError:
                    if deneme == self._maks_deneme - 1:
                        raise
                    time.sleep(1)
                except Exception:
                    if deneme == self._maks_deneme - 1:
                        raise

            kayit["basari"] = False
            self._mesaj_gecmisi.append(kayit)
            return {"basari": False, "hata": "Tum denemeler basarisiz", "provider": provider}

        except ConnectionError as e:
            return {"basari": False, "hata": str(e), "provider": provider}
        except TimeoutError:
            return {"basari": False, "hata": "Zaman asimi", "provider": provider}
        except Exception as hata:
            print(f"[ProviderTransport] Gonderme hatasi ({provider}): {hata}")
            return {"basari": False, "hata": str(hata), "provider": provider}

    def al(self, provider="local"):
        """Belirtilen saglayicidan mesaj al.

        Args:
            provider: Kaynak saglayici adi

        Returns:
            dict: Alinan mesaj veya hata
        """
        try:
            if provider not in self._baglantilar:
                raise ConnectionError(f"Saglayici baglantisi yok: {provider}")

            kanal = self._baglantilar[provider].get("dinleyici")
            if not kanal:
                return {"basari": False, "hata": "Dinleyici bulunamadi", "provider": provider}

            mesaj = kanal(timeout=self._zaman_asimi)
            kayit = {
                "zaman": datetime.now().isoformat(),
                "provider": provider,
                "mesaj": str(mesaj)[:200] if mesaj else "",
                "yontem": "al",
                "basari": True,
            }
            self._mesaj_gecmisi.append(kayit)
            return {"basari": True, "mesaj": mesaj, "provider": provider}

        except ConnectionError as e:
            return {"basari": False, "hata": str(e), "provider": provider}
        except TimeoutError:
            return {"basari": False, "hata": "Alma zaman asimi", "provider": provider}
        except Exception as hata:
            print(f"[ProviderTransport] Alma hatasi ({provider}): {hata}")
            return {"basari": False, "hata": str(hata), "provider": provider}

    def baglan(self, provider, kanal=None, dinleyici=None, yapilandirma=None):
        """Bir saglayiciya baglan.

        Args:
            provider: Saglayici adi
            kanal: Gonderme kanali fonksiyonu
            dinleyici: Dinleme fonksiyonu
            yapilandirma: Ek yapilandirma

        Returns:
            bool: Basarili mi
        """
        try:
            if not provider:
                raise ValueError("Saglayici adi gerekli")

            self._baglantilar[provider] = {
                "kanal": kanal,
                "dinleyici": dinleyici,
                "yapilandirma": yapilandirma or {},
                "baglani_zamani": datetime.now().isoformat(),
                "durum": "bagli",
            }
            self._aktif_saglayicilar.add(provider)
            print(f"[ProviderTransport] Baglanti basarili: {provider}")
            return True

        except ValueError as e:
            print(f"[ProviderTransport] Baglanti hatasi: {e}")
            return False
        except Exception as hata:
            print(f"[ProviderTransport] Baglanti basarisiz ({provider}): {hata}")
            return False

    def koprus(self, provider):
        """Bir saglayiciyla baglantiyi kes.

        Args:
            provider: Saglayici adi

        Returns:
            bool: Basarili mi
        """
        try:
            if provider not in self._baglantilar:
                print(f"[ProviderTransport] Baglanti bulunamadi: {provider}")
                return False

            kapat = self._baglantilar[provider].get("kapat")
            if kapat:
                try:
                    kapat()
                except Exception as _provider_e175:
                    print(f"[UYARI] provider_transport.py:176 - {_provider_e175}")

            del self._baglantilar[provider]
            self._aktif_saglayicilar.discard(provider)
            print(f"[ProviderTransport] Baglanti kesildi: {provider}")
            return True

        except Exception as hata:
            print(f"[ProviderTransport] Kopma hatasi ({provider}): {hata}")
            return False

    def ping(self, provider=None):
        """Saglayici erisilebilir mi kontrol et.

        Args:
            provider: Saglayici adi (None = tumu)

        Returns:
            dict: Saglayici durumlari
        """
        try:
            if provider:
                if provider not in self._baglantilar:
                    return {provider: False}
                durum = True
                try:
                    kanal = self._baglantilar[provider].get("kanal")
                    if kanal:
                        kanal("ping", timeout=5)
                except Exception:
                    durum = False
                return {provider: durum}
            else:
                sonuc = {}
                for p in list(self._baglantilar.keys()):
                    try:
                        kanal = self._baglantilar[p].get("kanal")
                        if kanal:
                            kanal("ping", timeout=5)
                        sonuc[p] = True
                    except Exception:
                        sonuc[p] = False
                return sonuc

        except Exception as hata:
            print(f"[ProviderTransport] Ping hatasi: {hata}")
            return {provider: False} if provider else {}

    def aktif_saglayicilar(self):
        """Aktif saglayicilari listele.

        Returns:
            list: Aktif saglayici adlari
        """
        return list(self._aktif_saglayicilar)

    def tum_saglayicilar(self):
        """Tum kayitli saglayicilari listele.

        Returns:
            list: Kayitli saglayici adlari
        """
        return list(self._baglantilar.keys())

    def gecmisi_getir(self, limit=10):
        """Mesaj gecmisini getir.

        Args:
            limit: Son kac kayit

        Returns:
            list: Mesaj kayitlari
        """
        try:
            return self._mesaj_gecmisi[-limit:]
        except Exception:
            return []

    def gecmisi_temizle(self):
        """Mesaj gecmisini temizle.

        Returns:
            int: Temizlenen kayit sayisi
        """
        try:
            sayi = len(self._mesaj_gecmisi)
            self._mesaj_gecmisi.clear()
            return sayi
        except Exception:
            return 0

    def durum_raporu(self):
        """Saglayici durum raporu.

        Returns:
            dict: Durum bilgisi
        """
        try:
            return {
                "aktif_sayisi": len(self._aktif_saglayicilar),
                "kayitli_sayisi": len(self._baglantilar),
                "gecmis_sayisi": len(self._mesaj_gecmisi),
                "zaman_asimi": self._zaman_asimi,
                "saglayicilar": self.tum_saglayicilar(),
            }
        except Exception as hata:
            return {"hata": str(hata)}


if __name__ == "__main__":
    pt = ProviderTransport()

    def ornek_kanal(mesaj, timeout=30):
        return f"Yanit: {mesaj}"

    pt.baglan("local", kanal=ornek_kanal)
    pt.baglan("lmstudio", kanal=ornek_kanal)

    print(f"Aktif: {pt.aktif_saglayicilar()}")
    sonuc = pt.gonder("Merhaba dunya", "local")
    print(f"Gonderim: {sonuc}")
    print(f"Ping: {pt.ping()}")
    print(f"Durum: {pt.durum_raporu()}")
    pt.koprus("lmstudio")
    print(f"Kopma sonrasi: {pt.tum_saglayicilar()}")


# Eski ad uyumlulugu
RuntimeProviderEngine = ProviderTransport
