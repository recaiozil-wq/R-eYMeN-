# -*- coding: utf-8 -*-
"""
terminal_backends.py — TerminalBackend.
Terminal arka uclari: local, SSH ve Docker.
ReYMeN kimligi: Turkce docstring, try/except, class-based.
"""

import os
import subprocess
import time
import shlex
from datetime import datetime

try:
    from tools.environments.wsl import WSLEnvironment
except ImportError:
    class WSLEnvironment:
        """Stub — WSLEnvironment not available."""
        def __init__(self, dagitim=None):
            self.dagitim = dagitim
        def execute(self, komut, timeout=None):
            return {"basarili": False, "hata": "WSL not available", "donus_kodu": -1}
        @staticmethod
        def detect() -> bool:
            return False


class TerminalBackend:
    """TerminalBackend: Farkli ortamlarda komut calistirma.

    Local shell, SSH uzak baglanti ve Docker konteyner uzerinden
    komut calistirma destegi saglar. Zaman asimi, hata yonetimi
    ve cikti yakalama ozellikleri icerir.
    """

    def __init__(self, varsayilan_timeout=60, calisma_dizini=None):
        """TerminalBackend baslat.

        Args:
            varsayilan_timeout: Varsayilan zaman asimi (saniye)
            calisma_dizini: Calisma dizini (None = cwd)
        """
        self._varsayilan_timeout = varsayilan_timeout
        self._calisma_dizini = calisma_dizini or os.getcwd()
        self._ssh_baglantilari = {}
        self._calisma_gecmisi = []
        self._ortam_degiskenleri = {}

    def calistir(self, komut, timeout=None, ortam=None, shell=False):
        """Bir komutu calistir.

        Args:
            komut: Calistirilacak komut
            timeout: Zaman asimi (saniye)
            ortam: Ek ortam degiskenleri
            shell: Shell kullanilsin mi

        Returns:
            dict: Calistirma sonucu
        """
        try:
            baslangic = time.time()
            timeout = timeout or self._varsayilan_timeout

            env = os.environ.copy()
            if self._ortam_degiskenleri:
                env.update(self._ortam_degiskenleri)
            if ortam:
                env.update(ortam)

            if isinstance(komut, str) and shell:
                komut = shlex.split(komut, posix=(os.name != "nt"))
                shell = False
            elif isinstance(komut, list):
                shell = False

            sonuc = subprocess.run(  # nosec B603
                komut,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self._calisma_dizini,
                env=env,
                encoding="utf-8",
                errors="replace",
            )

            gecen_sure = time.time() - baslangic
            kayit = {
                "zaman": datetime.now().isoformat(),
                "komut": str(komut)[:200],
                "donus_kodu": sonuc.returncode,
                "gecen_sure": round(gecen_sure, 3),
                "cikti_boyut": len(sonuc.stdout or ""),
                "hata_boyut": len(sonuc.stderr or ""),
                "basarili": sonuc.returncode == 0,
            }
            self._calisma_gecmisi.append(kayit)

            return {
                "basarili": sonuc.returncode == 0,
                "cikti": sonuc.stdout or "",
                "hata": sonuc.stderr or "",
                "donus_kodu": sonuc.returncode,
                "gecen_sure": round(gecen_sure, 3),
            }

        except subprocess.TimeoutExpired:
            gecen_sure = time.time() - baslangic
            self._calisma_gecmisi.append({
                "zaman": datetime.now().isoformat(),
                "komut": str(komut)[:200],
                "hata": "zaman_asimi",
                "gecen_sure": round(gecen_sure, 3),
                "basarili": False,
            })
            return {
                "basarili": False,
                "cikti": "",
                "hata": f"Komut {timeout}s zaman asimina ugradi",
                "donus_kodu": -1,
                "gecen_sure": round(gecen_sure, 3),
            }

        except FileNotFoundError as e:
            return {
                "basarili": False,
                "cikti": "",
                "hata": f"Komut bulunamadi: {e}",
                "donus_kodu": -1,
                "gecen_sure": 0,
            }

        except Exception as hata:
            print(f"[TerminalBackend] Calistirma hatasi: {hata}")
            return {
                "basarili": False,
                "cikti": "",
                "hata": str(hata),
                "donus_kodu": -1,
                "gecen_sure": 0,
            }

    def local(self, komut, timeout=None):
        """Local ortamda komut calistir.

        Args:
            komut: Calistirilacak komut
            timeout: Zaman asimi

        Returns:
            dict: Sonuc
        """
        try:
            print(f"[TerminalBackend] Local: {str(komut)[:100]}")
            return self.calistir(komut, timeout=timeout)
        except Exception as hata:
            return {"basarili": False, "hata": str(hata)}

    def ssh(self, host, kullanici, komut=None, timeout=None, port=22):
        """SSH uzerinden uzak komut calistir.

        Args:
            host: Hedef sunucu
            kullanici: SSH kullanici adi
            komut: Calistirilacak komut (None = baglanti testi)
            timeout: Zaman asimi
            port: SSH portu

        Returns:
            dict: Sonuc
        """
        try:
            if komut:
                ssh_komut = (
                    f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "
                    f"-p {port} {kullanici}@{host} {shlex.quote(komut)}"
                )
                return self.calistir(ssh_komut, timeout=timeout)
            else:
                test_komut = (
                    f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "
                    f"-p {port} {kullanici}@{host} 'echo SSH_BAGLANTI_BASARILI'"
                )
                sonuc = self.calistir(test_komut, timeout=timeout or 15)
                if sonuc["basarili"] and "SSH_BAGLANTI_BASARILI" in (sonuc.get("cikti") or ""):
                    baglanti_id = f"{kullanici}@{host}:{port}"
                    self._ssh_baglantilari[baglanti_id] = {
                        "host": host,
                        "kullanici": kullanici,
                        "port": port,
                        "baglani_zamani": datetime.now().isoformat(),
                    }
                    return {"basarili": True, "mesaj": f"SSH baglantisi basarili: {baglanti_id}"}
                return {"basarili": False, "hata": "SSH baglantisi basarisiz", "detay": sonuc.get("hata", "")}

        except Exception as hata:
            print(f"[TerminalBackend] SSH hatasi: {hata}")
            return {"basarili": False, "hata": str(hata)}

    def docker(self, konteyner, komut=None, timeout=None):
        """Docker konteynerinda komut calistir.

        Args:
            konteyner: Konteyner adi veya ID
            komut: Calistirilacak komut (None = calisiyor mu kontrol)
            timeout: Zaman asimi

        Returns:
            dict: Sonuc
        """
        try:
            if komut:
                docker_komut = f"docker exec {konteyner} {komut}"
                return self.calistir(docker_komut, timeout=timeout)
            else:
                kontrol = self.calistir(
                    f"docker ps --filter name={konteyner} --format {{{{.Names}}}}",
                    timeout=10,
                )
                if kontrol["basarili"] and konteyner in (kontrol.get("cikti") or ""):
                    return {
                        "basarili": True,
                        "mesaj": f"Konteyner calisiyor: {konteyner}",
                        "cikti": kontrol.get("cikti", ""),
                    }
                return {
                    "basarili": False,
                    "mesaj": f"Konteyner calismiyor: {konteyner}",
                }

        except Exception as hata:
            print(f"[TerminalBackend] Docker hatasi: {hata}")
            return {"basarili": False, "hata": str(hata)}

    def docker_calistir(self, image, komut, volume=None, timeout=None):
        """Docker imajindan yeni konteyner olusturup calistir.

        Args:
            image: Docker imaj adi
            komut: Calistirilacak komut
            volume: Baglanti dizini (host:konteyner)
            timeout: Zaman asimi

        Returns:
            dict: Sonuc
        """
        try:
            docker_komut = f"docker run --rm"
            if volume:
                docker_komut += f" -v {volume}"
            docker_komut += f" {image} bash -c {shlex.quote(komut)}"
            return self.calistir(docker_komut, timeout=timeout or 120)
        except Exception as hata:
            return {"basarili": False, "hata": str(hata)}

    def wsl(self, komut, dagitim=None, timeout=None):
        """WSL (Windows Subsystem for Linux) icinde komut calistir.

        Args:
            komut: Calistirilacak komut
            dagitim: WSL dagitim adi (None = varsayilan)
            timeout: Zaman asimi

        Returns:
            dict: Sonuc
        """
        try:
            env = WSLEnvironment(dagitim=dagitim)
            sonuc = env.execute(komut, timeout=timeout or self._varsayilan_timeout)
            self._calisma_gecmisi.append({
                "zaman": datetime.now().isoformat(),
                "komut": f"wsl:{dagitim or 'varsayilan'} {str(komut)[:100]}",
                "donus_kodu": sonuc.get("donus_kodu", -1),
                "basarili": sonuc.get("basarili", False),
            })
            return sonuc
        except Exception as hata:
            return {"basarili": False, "hata": str(hata)}

    def ortam_ayarla(self, anahtar, deger):
        """Ortam degiskeni ayarla.

        Args:
            anahtar: Degisken adi
            deger: Degisken degeri
        """
        self._ortam_degiskenleri[anahtar] = str(deger)

    def calisma_dizini_degistir(self, yol):
        """Calisma dizinini degistir.

        Args:
            yol: Yeni calisma dizini
        """
        try:
            if os.path.isdir(yol):
                self._calisma_dizini = os.path.abspath(yol)
                return True
            return False
        except Exception:
            return False

    def gecmisi_getir(self, limit=10):
        """Calistirma gecmisini getir.

        Args:
            limit: Kac kayit

        Returns:
            list: Kayitlar
        """
        return self._calisma_gecmisi[-limit:]

    def gecmisi_temizle(self):
        """Gecmisi temizle.

        Returns:
            int: Temizlenen kayit sayisi
        """
        try:
            sayi = len(self._calisma_gecmisi)
            self._calisma_gecmisi.clear()
            return sayi
        except Exception:
            return 0

    def ssh_baglantilari_listele(self):
        """Aktif SSH baglantilarini listele.

        Returns:
            list: Baglanti bilgileri
        """
        return list(self._ssh_baglantilari.values())

    def durum(self):
        """TerminalBackend durum bilgisi.

        Returns:
            dict: Durum
        """
        return {
            "calisma_dizini": self._calisma_dizini,
            "varsayilan_timeout": self._varsayilan_timeout,
            "calisma_sayisi": len(self._calisma_gecmisi),
            "ssh_baglanti_sayisi": len(self._ssh_baglantilari),
            "ortam_degisken_sayisi": len(self._ortam_degiskenleri),
        }


class TerminalBackendDispatcher(TerminalBackend):
    """motor.py'nin beklediği string döndüren komut yürütücü.

    TerminalBackend'i sarmalar; calistir() dict yerine metin döndürür.
    mode='docker' verilirse Docker konteynerinde, 'local' verilirse
    yerel kabukta çalıştırır.
    """

    def __init__(self, mode="local", **kwargs):
        super().__init__(**kwargs)
        self._mode = mode

    def calistir(self, komut, **kwargs):
        """Komutu çalıştır ve okunabilir metin döndür."""
        sonuc = super().calistir(komut, **kwargs)
        cikti = (sonuc.get("cikti") or "").strip()
        hata  = (sonuc.get("hata")  or "").strip()
        if sonuc.get("basarili"):
            return f"[Tamam]:\n{cikti}" if cikti else "[Tamam]: Komut tamamlandi."
        return f"[Hata]: {hata}\n{cikti}".strip() or f"[Hata]: Komut basarisiz (kod {sonuc.get('donus_kodu','?')})."


if __name__ == "__main__":
    tb = TerminalBackend()
    sonuc = tb.local("echo Merhaba TerminalBackend")
    print(f"Local test: {sonuc['basarili']}")
    print(f"Cikti: {sonuc.get('cikti', '').strip()}")

    print(f"\nDocker kontrol:")
    docker_durum = tb.docker("test_konteyner")
    print(f"  {docker_durum['mesaj']}")

    print(f"\nGecmis:")
    for kayit in tb.gecmisi_getir(3):
        print(f"  [{kayit.get('zaman','?')[-8:]}] {kayit.get('komut','?')[:60]}")

    print(f"\nDurum: {tb.durum()}")
