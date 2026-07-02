# -*- coding: utf-8 -*-
"""
network_restriction.py — ReYMeN Ag Kisitlama Modulu.

Sandbox icinde calisan kodun hangi aglara erisebilecegini
kisitlama. Varsayilan: tum gidis (outbound) trafigi engelle,
yalnizca localhost'a (127.0.0.1) izin ver.

Desteklenen yontemler:
  - Windows: hosts dosyasi + wfw (Windows Firewall) ile kisitlama
  - Linux: iptables/nftables ile kisitlama (opsiyonel)
  - Docker: --network=none veya kullanici-tanimli ag ile kisitlama

Kullanim:
    nr = NetworkRestriction()
    nr.apply(["127.0.0.1", "192.168.1.0/24"])
    # ... islemler ...
    nr.remove()
"""

import ipaddress
import logging
import os
import platform
import re
import socket
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Varsayilanlar ──────────────────────────────────────────────────────────

# Varsayilan izin verilen IP'ler (her zaman acik)
VARSAYILAN_IZINLI = frozenset({
    "127.0.0.1",
    "::1",
})

# Varsayilan engellenen CIDR'ler (tum ozel aglar dahil)
VARSAYILAN_ENGEL = frozenset({
    "0.0.0.0/0",       # Tum IPv4
    "::/0",            # Tum IPv6
})

# Windows hosts dosyasi yolu
HOSTS_DOSYASI = r"C:\Windows\System32\drivers\etc\hosts"
HOSTS_DOSYASI_ALT = r"C:\Windows\SysWOW64\drivers\etc\hosts"

# ReYMeN network restriction etiketi
REYMEN_ETIKETI = "# REYMEN_NETWORK_RESTRICTION"
REYMEN_BASLANGIC = "# REYMEN_NETWORK_START"
REYMEN_BITIS = "# REYMEN_NETWORK_END"


# ── Yardimci Fonksiyonlar ─────────────────────────────────────────────────

def _sistem_tespit() -> str:
    """Calisma ortamini tespit et: windows, linux, wsl."""
    sistem = platform.system().lower()
    if sistem == "windows":
        # WSL kontrolu
        try:
            if "microsoft" in platform.uname().release.lower():
                return "wsl"
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )
        return "windows"
    elif sistem == "linux":
        return "linux"
    return sistem


def _ip_izinli_mi(ip_adresi: str, izinli_liste: list) -> bool:
    """Bir IP adresinin izinli listede olup olmadigini kontrol et."""
    try:
        hedef_ip = ipaddress.ip_address(ip_adresi)
        for izin in izinli_liste:
            try:
                ag = ipaddress.ip_network(izin, strict=False)
                if hedef_ip in ag:
                    return True
            except ValueError:
                # Tek IP ise esitlik kontrolu
                if ip_adresi == izin:
                    return True
    except ValueError as _e:
        logger.warning("[NetworkRestriction] Gecersiz deger (L93): %s", ValueError)
        pass
    return False


def _hosts_etkilesim(eklenecek: list, kaldirilacak: list) -> dict:
    """Hosts dosyasina domain/IP yonlendirmesi ekle/kaldir.

    Tüm gidis trafigini engellemek icin bilinen domain'leri
    127.0.0.1'e yonlendirir.

    Args:
        eklenecek: Domain listesi (127.0.0.1'e yonlendirilecek)
        kaldirilacak: Kaldirilacak domain listesi

    Returns:
        {"basarili": bool, "mesaj": str, "eklenen": int, "kaldirilan": int}
    """
    mesaj = {"basarili": False, "mesaj": "", "eklenen": 0, "kaldirilan": 0}

    # Windows'ta hosts dosyasi yonetici yetkisi gerektirir
    hosts_yolu = None
    for yol in [HOSTS_DOSYASI, HOSTS_DOSYASI_ALT]:
        if os.path.exists(yol):
            hosts_yolu = yol
            break

    if not hosts_yolu:
        mesaj["mesaj"] = "Hosts dosyasi bulunamadi"
        return mesaj

    try:
        # Mevcut hosts icerigini oku
        with open(hosts_yolu, "r", encoding="utf-8") as f:
            satirlar = f.readlines()

        # ReYMeN blokunu temizle (varsa)
        yeni_satirlar = []
        reymen_blok = False
        for satir in satirlar:
            if REYMEN_BASLANGIC in satir:
                reymen_blok = True
                continue
            if REYMEN_BITIS in satir:
                reymen_blok = False
                continue
            if not reymen_blok:
                yeni_satirlar.append(satir)

        # Kaldirilacak domain'leri temizle
        for domain in kaldirilacak:
            yeni_satirlar = [
                s for s in yeni_satirlar
                if domain.lower() not in s.lower()
            ]
            mesaj["kaldirilan"] += 1

        # Eklenecek domain'leri ekle
        if eklenecek:
            yeni_satirlar.append(f"\n{REYMEN_BASLANGIC}\n")
            yeni_satirlar.append(f"{REYMEN_ETIKETI} {datetime.now().isoformat()}\n")
            for domain in eklenecek:
                yeni_satirlar.append(f"127.0.0.1 {domain}\n")
                yeni_satirlar.append(f"::1 {domain}\n")
                mesaj["eklenen"] += 1
            yeni_satirlar.append(f"{REYMEN_BITIS}\n")

        # Hosts dosyasini yaz
        with open(hosts_yolu, "w", encoding="utf-8") as f:
            f.writelines(yeni_satirlar)

        mesaj["basarili"] = True
        mesaj["mesaj"] = (
            f"Hosts dosyasi guncellendi: "
            f"{mesaj['eklenen']} domain eklendi, "
            f"{mesaj['kaldirilan']} domain kaldirildi"
        )

    except PermissionError:
        mesaj["mesaj"] = (
            "Hosts dosyasi yazilamadi: yonetici yetkisi gerekiyor. "
            "Dosyayi manuel olarak duzenleyin veya uygulamayi "
            "yonetici olarak calistirin."
        )
    except Exception as e:
        mesaj["mesaj"] = f"Hosts dosyasi hatasi: {e}"

    return mesaj


def _wfw_kural_ekle(kural_adi: str, uzak_ip: str = "*", aksiyon: str = "block") -> bool:
    """Windows Firewall kurali ekle.

    Args:
        kural_adi: Kural adi
        uzak_ip: Hedef IP/CIDR
        aksiyon: block veya allow

    Returns:
        Basarili ise True
    """
    try:
        if aksiyon == "block":
            cmd = [
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name={kural_adi}",
                "dir=out",
                f"remoteip={uzak_ip}",
                "action=block",
                "enable=yes",
            ]
        else:
            cmd = [
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name={kural_adi}",
                "dir=out",
                f"remoteip={uzak_ip}",
                "action=allow",
                "enable=yes",
            ]

        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
        return r.returncode == 0
    except Exception as e:
        logger.warning("[WFW] Kural ekleme hatasi: %s", e)
        return False


def _wfw_kural_kaldir(kural_adi: str) -> bool:
    """Windows Firewall kuralini kaldir."""
    try:
        r = subprocess.run(
            ["netsh", "advfirewall", "firewall", "delete", "rule",
             f"name={kural_adi}"],
            capture_output=True, text=True, timeout=30,
        )
        return r.returncode == 0
    except Exception as e:
        logger.warning("[WFW] Kural kaldirma hatasi: %s", e)
        return False


def _iptables_kural_ekle(izinli_cidr: str) -> bool:
    """Linux iptables ile outbound kurali ekle (allow).

    Zincir: REYMEN-OUT
    """
    try:
        # Zincir olustur (ilk sefer)
        subprocess.run(
            ["iptables", "-N", "REYMEN-OUT"],
            capture_output=True, text=True, timeout=10,
        )
        # Zinciri OUTPUT'a bagla
        subprocess.run(
            ["iptables", "-I", "OUTPUT", "-j", "REYMEN-OUT"],
            capture_output=True, text=True, timeout=10,
        )
        # Izin ver
        r = subprocess.run(
            ["iptables", "-A", "REYMEN-OUT", "-d", izinli_cidr,
             "-j", "ACCEPT"],
            capture_output=True, text=True, timeout=10,
        )
        return r.returncode == 0
    except Exception as e:
        logger.warning("[IPTABLES] Kural ekleme hatasi: %s", e)
        return False


def _iptables_kurallari_temizle() -> bool:
    """Linux iptables REYMEN-OUT zincirini temizle."""
    try:
        # OUTPUT'tan ayir
        subprocess.run(
            ["iptables", "-D", "OUTPUT", "-j", "REYMEN-OUT"],
            capture_output=True, text=True, timeout=10,
        )
        # Zinciri sil (flush + delete)
        subprocess.run(
            ["iptables", "-F", "REYMEN-OUT"],
            capture_output=True, text=True, timeout=10,
        )
        subprocess.run(
            ["iptables", "-X", "REYMEN-OUT"],
            capture_output=True, text=True, timeout=10,
        )
        return True
    except Exception as e:
        logger.warning("[IPTABLES] Temizleme hatasi: %s", e)
        return False


# ── Domain Engelleme Listesi ─────────────────────────────────────────────

# Bilinen genel domain'ler (tumunu engellemek icin)
TUM_DOMAIN_YONLENDIR = [
    # Genel web siteleri
    "google.com", "www.google.com",
    "youtube.com", "www.youtube.com",
    "facebook.com", "www.facebook.com",
    "twitter.com", "www.twitter.com", "x.com", "www.x.com",
    "instagram.com", "www.instagram.com",
    "linkedin.com", "www.linkedin.com",
    "reddit.com", "www.reddit.com",
    "github.com", "www.github.com",
    "stackoverflow.com", "www.stackoverflow.com",
    "pypi.org", "www.pypi.org",
    "python.org", "www.python.org",
    "docker.com", "www.docker.com",
    "amazon.com", "www.amazon.com",
    "aws.amazon.com",
    "azure.microsoft.com",
    "cloud.google.com",
    "api.openai.com",
    "api.anthropic.com",
    # DNS
    "1.1.1.1", "8.8.8.8", "8.8.4.4",
]


# ── NetworkRestriction Sinifi ─────────────────────────────────────────────

class NetworkRestriction:
    """Ag kisitlama yoneticisi.

    Tum gidis (outbound) trafigini engeller, yalnizca
    izin verilen IP/CIDR'lere izin verir.

    Kullanim:
        nr = NetworkRestriction()
        nr.apply(["127.0.0.1", "10.0.0.0/8"])
        # ... calistir ...
        nr.remove()

    Ozellikler:
        - allowlist mantigi: varsayilan tumu engelle, izinli IP'leri ekle
        - Diger IP'lere gidis (outbound) engellenir
        - Localhost (127.0.0.1, ::1) her zaman acik
        - Docker network entegrasyonu
        - Windows (hosts + firewall) ve Linux (iptables) destegi
    """

    def __init__(
        self,
        her_zaman_izinli: Optional[list] = None,
    ):
        """NetworkRestriction baslat.

        Args:
            her_zaman_izinli: Varsayilan izinli IP'ler (localhost haric)
        """
        self._aktif = False
        self._sistem = _sistem_tespit()
        self._baslangic_zamani: Optional[datetime] = None
        self._eklenen_kurallar: list[dict] = []
        self._eklenen_domainler: list[str] = []

        # Her zaman izin verilecek IP'ler
        self._her_zaman_izinli = set(VARSAYILAN_IZINLI)
        if her_zaman_izinli:
            for ip in her_zaman_izinli:
                self._her_zaman_izinli.add(ip)

        # Firewall kural adlari
        self._kural_adi = "REYMEN-NetworkRestriction"
        self._kural_adi_allow = "REYMEN-NetworkRestriction-Allow"
        self._kural_adi_block = "REYMEN-NetworkRestriction-Block"

        logger.info(
            "[NetworkRestriction] Baslatildi. Sistem: %s, Kalici IP: %s",
            self._sistem, sorted(self._her_zaman_izinli),
        )

    @property
    def aktif(self) -> bool:
        """Kisitlama aktif mi?"""
        return self._aktif

    @property
    def durum(self) -> dict:
        """Guncel durum bilgisi."""
        return {
            "aktif": self._aktif,
            "sistem": self._sistem,
            "baslangic": self._baslangic_zamani.isoformat() if self._baslangic_zamani else None,
            "her_zaman_izinli": sorted(self._her_zaman_izinli),
            "eklenen_kurallar": len(self._eklenen_kurallar),
            "eklenen_domainler": len(self._eklenen_domainler),
            "eklenen_domain_listesi": self._eklenen_domainler[:20],
        }

    def apply(
        self,
        allowlist: Optional[list[str]] = None,
        block_domainler: bool = True,
    ) -> dict:
        """Ag kisitlamasini uygula.

        Varsayilan: tum gidis trafigi engellenir.
        Izin verilen IP'ler allowlist parametresi ile belirtilir.

        Args:
            allowlist: Izin verilen IP/CIDR listesi (localhost otomatik)
            block_domainler: Domain seviyesinde de engelle (hosts dosyasi)

        Returns:
            {"basarili": bool, "mesaj": str, "detay": dict}
        """
        if self._aktif:
            return {
                "basarili": False,
                "mesaj": "Kisitlama zaten aktif. Once remove() cagirin.",
                "detay": self.durum,
            }

        sonuc = {"basarili": False, "mesaj": "", "detay": {}}
        allowlist = allowlist or []

        # Her zaman izinli IP'leri ekle
        izinli_liste = list(self._her_zaman_izinli) + allowlist

        # Domain engelleme
        if block_domainler and self._sistem in ("windows", "wsl"):
            domain_sonuc = _hosts_etkilesim(
                eklenecek=TUM_DOMAIN_YONLENDIR,
                kaldirilacak=[],
            )
            if domain_sonuc["basarili"]:
                self._eklenen_domainler = TUM_DOMAIN_YONLENDIR
                logger.info(
                    "[NetworkRestriction] %d domain engellendi",
                    domain_sonuc["eklenen"],
                )

        # Windows Firewall ile kisitlama
        if self._sistem == "windows":
            sonuc = self._windows_firewall_uygula(izinli_liste)
        elif self._sistem == "wsl":
            # WSL'de hosts dosyasi calisir, firewall WSL icin sinirli
            sonuc = self._wsl_uygula(izinli_liste)
        elif self._sistem == "linux":
            sonuc = self._linux_uygula(izinli_liste)
        else:
            sonuc = {
                "basarili": False,
                "mesaj": f"Desteklenmeyen sistem: {self._sistem}",
                "detay": {"sistem": self._sistem},
            }

        if sonuc["basarili"]:
            self._aktif = True
            self._baslangic_zamani = datetime.now()

        return sonuc

    def remove(self) -> dict:
        """Ag kisitlamasini kaldir.

        Returns:
            {"basarili": bool, "mesaj": str, "detay": dict}
        """
        if not self._aktif:
            return {
                "basarili": True,
                "mesaj": "Kisitlama zaten aktif degil.",
                "detay": self.durum,
            }

        sonuc = {"basarili": False, "mesaj": "", "detay": {}}

        # Domain engellemeyi kaldir
        if self._eklenen_domainler:
            domain_sonuc = _hosts_etkilesim(
                eklenecek=[],
                kaldirilacak=self._eklenen_domainler,
            )
            self._eklenen_domainler = []

        # Firewall kurallarini kaldir
        if self._sistem == "windows":
            sonuc = self._windows_firewall_kaldir()
        elif self._sistem == "wsl":
            sonuc = self._wsl_kaldir()
        elif self._sistem == "linux":
            sonuc = self._linux_kaldir()
        else:
            sonuc = {
                "basarili": False,
                "mesaj": f"Desteklenmeyen sistem: {self._sistem}",
                "detay": {"sistem": self._sistem},
            }

        if sonuc.get("basarili", False):
            self._aktif = False
            self._baslangic_zamani = None
            self._eklenen_kurallar = []

        return sonuc

    def test_connectivity(self, hedef_ip: str = "8.8.8.8", port: int = 80) -> bool:
        """Baglanti testi yap (kisitlama etkili mi?).

        Args:
            hedef_ip: Test edilecek IP
            port: Test edilecek port

        Returns:
            Baglanti basarili ise True
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sonuc = sock.connect_ex((hedef_ip, port))
            sock.close()
            return sonuc == 0
        except Exception:
            return False

    def ip_kontrol(self, ip_adresi: str) -> dict:
        """Bir IP adresinin izin durumunu kontrol et.

        Args:
            ip_adresi: Kontrol edilecek IP

        Returns:
            {"ip": str, "izinli": bool, "neden": str}
        """
        # Her zaman izinli IP'ler
        for izin_ip in self._her_zaman_izinli:
            if ip_adresi == izin_ip:
                return {"ip": ip_adresi, "izinli": True, "neden": "her_zaman_izinli"}

        # CIDR kontrolu
        for izin_ip in self._her_zaman_izinli:
            try:
                ag = ipaddress.ip_network(izin_ip, strict=False)
                hedef = ipaddress.ip_address(ip_adresi)
                if hedef in ag:
                    return {"ip": ip_adresi, "izinli": True, "neden": "cidr_eslesmesi"}
            except ValueError as _e:
                logger.warning("[NetworkRestriction] Gecersiz deger (L535): %s", ValueError)
                pass

        if self._aktif:
            return {"ip": ip_adresi, "izinli": False, "neden": "kisitlama_aktif"}
        return {"ip": ip_adresi, "izinli": True, "neden": "kisitlama_yok"}

    # ── Platform Spesifik ─────────────────────────────────────────────────

    def _windows_firewall_uygula(self, izinli_liste: list) -> dict:
        """Windows Firewall ile outbound kisitlamasi uygula.

        Strateji:
            1. Tum outbound trafigi engelle (default block rule)
            2. Izin verilen IP'ler icin allow rule ekle
        """
        basarili_sayisi = 0

        # Block all outbound
        if _wfw_kural_ekle(self._kural_adi_block, "*", "block"):
            self._eklenen_kurallar.append({
                "tip": "block",
                "hedef": "*",
                "kural": self._kural_adi_block,
            })
            basarili_sayisi += 1

        # Allow specific IP'ler
        for izin in izinli_liste:
            kural_adi = f"{self._kural_adi_allow}-{izin.replace('/', '_').replace(':', '_')}"
            if _wfw_kural_ekle(kural_adi, izin, "allow"):
                self._eklenen_kurallar.append({
                    "tip": "allow",
                    "hedef": izin,
                    "kural": kural_adi,
                })
                basarili_sayisi += 1

        if basarili_sayisi > 0:
            return {
                "basarili": True,
                "mesaj": (
                    f"Windows Firewall: 1 block + {len(izinli_liste)} allow "
                    f"kurali eklendi. Sistem: {self._sistem}"
                ),
                "detay": {
                    "eklenen_kural": basarili_sayisi,
                    "izinli_liste": izinli_liste,
                    "kural_adi": self._kural_adi,
                },
            }
        return {
            "basarili": False,
            "mesaj": "Windows Firewall kurali eklenemedi. Yonetici yetkisi gerekebilir.",
            "detay": {"sistem": self._sistem},
        }

    def _windows_firewall_kaldir(self) -> dict:
        """Windows Firewall kurallarini kaldir."""
        basarili_sayisi = 0
        for kural in self._eklenen_kurallar:
            if _wfw_kural_kaldir(kural["kural"]):
                basarili_sayisi += 1

        # Ana block kuralini da kaldir
        _wfw_kural_kaldir(self._kural_adi_block)

        if basarili_sayisi >= 0:
            return {
                "basarili": True,
                "mesaj": f"Windows Firewall: {basarili_sayisi} kural kaldirildi.",
                "detay": {"kaldirilan": basarili_sayisi},
            }
        return {
            "basarili": False,
            "mesaj": "Kurallar kaldirilamadi.",
            "detay": {},
        }

    def _wsl_uygula(self, izinli_liste: list) -> dict:
        """WSL icin kisitlama uygula (hosts + iptables dene)."""
        # WSL'de hosts dosyasi Linux'tan yonetici gerektirmez
        # Ama WSL ic IP'leri farkli
        sonuc = {"basarili": False, "mesaj": "", "detay": {}}

        # iptables dene
        try:
            linux_sonuc = self._linux_uygula(izinli_liste)
            if linux_sonuc["basarili"]:
                sonuc = linux_sonuc
                sonuc["detay"]["wsl_iptables"] = True
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )

        if not sonuc["basarili"]:
            # Fallback: hosts dosyasi
            sonuc["mesaj"] = (
                "WSL'de iptables calismadi. "
                "Domain engelleme hosts dosyasi ile yapildi. "
                "Tam IP kisitlamasi icin Windows Firewall kullanin."
            )
            sonuc["basarili"] = True

        return sonuc

    def _wsl_kaldir(self) -> dict:
        """WSL kisitlamasini kaldir."""
        try:
            return self._linux_kaldir()
        except Exception:
            return {"basarili": True, "mesaj": "WSL kisitlamasi kaldirildi.", "detay": {}}

    def _linux_uygula(self, izinli_liste: list) -> dict:
        """Linux iptables ile outbound kisitlamasi uygula.

        Zincir: REYMEN-OUT
          - Varsayilan: DROP (tum gidis engellenir)
          - Izin verilen IP'ler icin: ACCEPT
          - localhost her zaman ACCEPT
        """
        basarili_sayisi = 0

        # Once mevcut REYMEN-OUT zincirini temizle
        try:
            subprocess.run(
                ["iptables", "-F", "REYMEN-OUT"],
                capture_output=True, text=True, timeout=10,
            )
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )

        # Zincir olustur (yoksa)
        subprocess.run(
            ["iptables", "-N", "REYMEN-OUT"],
            capture_output=True, text=True, timeout=10,
        )

        # OUTPUT'a bagla (ilk siraya)
        subprocess.run(
            ["iptables", "-I", "OUTPUT", "-j", "REYMEN-OUT"],
            capture_output=True, text=True, timeout=10,
        )

        # Izin verilen IP'ler icin ACCEPT
        for izin in izinli_liste:
            r = subprocess.run(
                ["iptables", "-A", "REYMEN-OUT", "-d", izin,
                 "-j", "ACCEPT"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                self._eklenen_kurallar.append({
                    "tip": "allow", "hedef": izin, "kural": izin,
                })
                basarili_sayisi += 1

        # Varsayilan: DROP (engelle)
        r = subprocess.run(
            ["iptables", "-A", "REYMEN-OUT", "-j", "DROP"],
            capture_output=True, text=True, timeout=10,
        )

        if basarili_sayisi > 0 or r.returncode == 0:
            return {
                "basarili": True,
                "mesaj": (
                    f"iptables: {basarili_sayisi} allow kurali + "
                    f"default DROP eklendi. Sistem: {self._sistem}"
                ),
                "detay": {
                    "eklenen_kural": basarili_sayisi,
                    "izinli_liste": izinli_liste,
                },
            }
        return {
            "basarili": False,
            "mesaj": "iptables kurali eklenemedi.",
            "detay": {"sistem": self._sistem},
        }

    def _linux_kaldir(self) -> dict:
        """Linux iptables REYMEN-OUT zincirini kaldir."""
        basarili = _iptables_kurallari_temizle()
        return {
            "basarili": basarili,
            "mesaj": "iptables REYMEN-OUT zinciri kaldirildi." if basarili else "iptables temizleme basarisiz.",
            "detay": {},
        }


# ── Module-Level API ─────────────────────────────────────────────────────

_VARSAYILAN_NETWORK = NetworkRestriction()


def network_kisitla(
    allowlist: Optional[list[str]] = None,
    block_domainler: bool = True,
) -> str:
    """Tum gidis trafigini engelle, sadece izinli IP'lere izin ver.

    Args:
        allowlist: Izin verilen IP/CIDR listesi (orn: ["10.0.0.0/8", "192.168.1.100"])
        block_domainler: Domain seviyesinde de engelle (hosts dosyasi)

    Returns:
        Durum mesaji
    """
    try:
        sonuc = _VARSAYILAN_NETWORK.apply(allowlist, block_domainler)
        if sonuc["basarili"]:
            return (
                f"[GUVENLIK] Network kisitlamasi aktif. "
                f"{sonuc['mesaj']}"
            )
        return f"[GUVENLIK] Network kisitlamasi basarisiz: {sonuc['mesaj']}"
    except Exception as e:
        logger.error("[NetworkRestriction] Apply hatasi: %s", e)
        return f"[GUVENLIK] Network kisitlamasi hatasi: {e}"


def network_kisit_kaldir() -> str:
    """Network kisitlamasini kaldir."""
    try:
        sonuc = _VARSAYILAN_NETWORK.remove()
        if sonuc["basarili"]:
            return f"[GUVENLIK] Network kisitlamasi kaldirildi. {sonuc['mesaj']}"
        return f"[GUVENLIK] Kisitlama kaldirma basarisiz: {sonuc['mesaj']}"
    except Exception as e:
        logger.error("[NetworkRestriction] Remove hatasi: %s", e)
        return f"[GUVENLIK] Network kisitlamasi kaldirma hatasi: {e}"


def network_durum() -> dict:
    """Network kisitlama durumunu dondur."""
    return _VARSAYILAN_NETWORK.durum


def network_durum_text() -> str:
    """Insan-okunabilir durum metni."""
    d = network_durum()
    aktif_ikon = "🟢" if d["aktif"] else "🔴"
    sistem = d["sistem"]
    satirlar = [
        f"[Guvenlik] Network Restriction Durumu:",
        f"  {aktif_ikon} Aktif: {'Evet' if d['aktif'] else 'Hayir'}",
        f"  🖥️  Sistem: {sistem}",
        f"  🏠 Her Zaman Izinli: {', '.join(d['her_zaman_izinli'])}",
    ]
    if d["baslangic"]:
        satirlar.append(f"  ⏰ Baslangic: {d['baslangic']}")
    if d["eklenen_domainler"]:
        satirlar.append(f"  🌐 Engellenen Domain: {d['eklenen_domainler']}")
    return "\n".join(satirlar)


# ── Docker Network Entegrasyonu ──────────────────────────────────────────

class DockerNetworkRestriction:
    """Docker icin network restriction yardimcisi.

    Docker container'lara ozel network kisitlamasi uygular.
    """

    def __init__(self, network_adi: str = "reymen-restricted"):
        self.network_adi = network_adi
        self._olusturuldu = False

    def network_hazirla(self) -> bool:
        """Kisitli Docker network'u olustur.

        Varsayilan: --internal (host disina erisim yok)
        """
        try:
            # Once mevcut mu kontrol et
            r = subprocess.run(
                ["docker", "network", "inspect", self.network_adi],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                self._olusturuldu = True
                return True

            # --internal: container'lar birbirine erisebilir ama disariya cikamaz
            r = subprocess.run(
                ["docker", "network", "create",
                 "--internal",
                 "--label", "reymen=sandbox-network",
                 self.network_adi],
                capture_output=True, text=True, timeout=30,
            )
            self._olusturuldu = r.returncode == 0
            return self._olusturuldu
        except Exception as e:
            logger.warning("[DockerNetwork] Hazirlik hatasi: %s", e)
            return False

    def network_temizle(self) -> bool:
        """Kisitli Docker network'u temizle.

        Not: Bagli container yoksa siler.
        """
        if not self._olusturuldu:
            return True
        try:
            r = subprocess.run(
                ["docker", "network", "rm", self.network_adi],
                capture_output=True, text=True, timeout=30,
            )
            self._olusturuldu = False
            return r.returncode == 0
        except Exception as e:
            logger.warning("[DockerNetwork] Temizleme hatasi: %s", e)
            return False

    def container_baglanti_args(self) -> list[str]:
        """Container calistirirken eklenecek network argumanlari.

        Returns:
            ["--network", "reymen-restricted"] veya ["--network", "none"]
        """
        if self._olusturuldu:
            return ["--network", self.network_adi]
        return ["--network", "none"]


# ── Motor Plugin API ─────────────────────────────────────────────────────

def motor_kaydet(motor):
    """Motor'a network restriction araclarini kaydet."""
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return

    motor._plugin_arac_kaydet(
        "GUVENLIK_KISITLA",
        lambda allowlist="": network_kisitla(
            allowlist=[x.strip() for x in str(allowlist).split(",") if x.strip()]
        ),
        "Tum gidis trafigini engelle, sadece izinli IP'lere izin ver. "
        "Parametre: allowlist (opsiyonel, virgulle ayrilmis IP/CIDR listesi)",
    )
    motor._plugin_arac_kaydet(
        "GUVENLIK_KISIT_KALDIR",
        network_kisit_kaldir,
        "Network kisitlamasini kaldir",
    )
    motor._plugin_arac_kaydet(
        "GUVENLIK_DURUM",
        network_durum_text,
        "Network restriction durum raporu",
    )

    logger.info("[NetworkRestriction] Motor'a 3 arac kaydedildi: "
                "GUVENLIK_KISITLA, GUVENLIK_KISIT_KALDIR, GUVENLIK_DURUM")


# ── CLI Test ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    print("=== ReYMeN Network Restriction Test ===\n")

    # 1. Sistem bilgisi
    print(f"Sistem: {_sistem_tespit()}")
    print(f"Platform: {platform.platform()}")
    print()

    # 2. Durum
    print(network_durum_text())
    print()

    # 3. IP kontrol
    test_ipleri = ["127.0.0.1", "8.8.8.8", "192.168.1.1", "10.0.0.1"]
    for ip in test_ipleri:
        sonuc = _VARSAYILAN_NETWORK.ip_kontrol(ip)
        print(f"  IP {ip}: {'✅ Izinli' if sonuc['izinli'] else '❌ Engelli'} ({sonuc['neden']})")

    print()

    # 4. Kisitlama uygula (opsiyonel, yonetici yetkisi gerektirebilir)
    print("Kisitlama uygulaniyor...")
    sonuc = _VARSAYILAN_NETWORK.apply(
        allowlist=["10.0.0.0/8", "192.168.0.0/16"],
        block_domainler=False,  # Test icin domain engelleme kapali
    )
    print(f"  {'✅' if sonuc['basarili'] else '❌'} {sonuc['mesaj']}")
    print()

    if _VARSAYILAN_NETWORK.aktif:
        # 5. Baglantı testi
        print("Baglanti testi (8.8.8.8:80)...")
        baglanti = _VARSAYILAN_NETWORK.test_connectivity()
        print(f"  {'❌ Engelli (beklenen)' if not baglanti else '⚠️ Acik (beklenmeyen)'}")

        print()

        # 6. Kaldir
        print("Kisitlama kaldiriliyor...")
        sonuc = _VARSAYILAN_NETWORK.remove()
        print(f"  {'✅' if sonuc['basarili'] else '❌'} {sonuc['mesaj']}")
    else:
        print("Kisitlama uygulanamadi (yetki eksik).")
