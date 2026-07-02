# -*- coding: utf-8 -*-
"""security_audit.py — Guvenlik Denetimi.

Projedeki guvenlik aciklarini tarar, zafiyetleri raporlar
ve duzeltme onerileri sunar.
"""

import importlib
import os
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

PROJE_KOK = Path(__file__).parent.resolve()


class SecurityAudit:
    """Guvenlik denetim motoru."""

    def __init__(self):
        self._bulgular: list[dict] = []

    def _bulgu_ekle(self, seviye: str, kategori: str, mesaj: str, cozum: str = ""):
        self._bulgular.append({
            "seviye": seviye,
            "kategori": kategori,
            "mesaj": mesaj,
            "cozum": cozum,
        })

    def tarama_yap(self) -> list[dict]:
        """Tam guvenlik taramasi yap.

        Returns:
            Bulgu listesi
        """
        self._bulgular = []
        self._env_kontrol()
        self._guvenlik_modulu_kontrol()
        self._dosya_izni_kontrol()
        self._bilesen_kontrol()
        return self._bulgular

    def _env_kontrol(self):
        """.env dosyasinda acik anahtar kontrolu."""
        env_yolu = PROJE_KOK / ".env"
        if not env_yolu.exists():
            self._bulgu_ekle(
                "YUKSEK", "env",
                ".env dosyasi bulunamadi.",
                ".env.example dosyasini .env olarak kopyala ve API anahtarlarini gir.",
            )
            return

        icerik = env_yolu.read_text(encoding="utf-8")
        for satir in icerik.split("\n"):
            satir = satir.strip()
            if "=" in satir and not satir.startswith("#"):
                anahtar, deger = satir.split("=", 1)
                if "API_KEY" in anahtar or "TOKEN" in anahtar:
                    if "***" in deger or not deger.strip():
                        self._bulgu_ekle(
                            "ORTA", "env",
                            f"{anahtar} maskeli veya bos.",
                            f"Gecerli bir API anahtari gir: {anahtar}=<deger>",
                        )

    def _guvenlik_modulu_kontrol(self):
        """Guvenlik modullerinin varligini kontrol et."""
        gerekli = [
            "file_safety", "path_security", "url_safety",
            "redact", "threat_patterns",
        ]
        for mod in gerekli:
            try:
                importlib.import_module(mod)
            except ImportError:
                self._bulgu_ekle(
                    "YUKSEK", "guvenlik_modulu",
                    f"{mod}.py bulunamadi.",
                    f"Guvenlik modulu eksik. Ekle: {mod}.py",
                )

    def _dosya_izni_kontrol(self):
        """Kritik dosyalarin izinlerini kontrol et."""
        kritik_dosyalar = [
            ".env", ".ReYMeN/memories/MEMORY.md",
            ".ReYMeN/memories/USER.md", "merkez_db/session_reymen.db",
        ]
        for dosya in kritik_dosyalar:
            yol = PROJE_KOK / dosya
            if yol.exists():
                # Windows'ta herkes okuyabilir mi?
                try:
                    import stat
                    izin = os.stat(yol).st_mode
                    if izin & stat.S_IROTH:
                        self._bulgu_ekle(
                            "DUSUK", "dosya_izni",
                            f"{dosya} herkes tarafindan okunabilir.",
                            f"Dosya izinlerini kisitla: icacls {dosya} /inheritance:r",
                        )
                except Exception as _security_e100:
                    print(f"[UYARI] security_audit.py:101 - {_security_e100}")

    def _bilesen_kontrol(self):
        """Kritik bilesenlerin varligini kontrol et."""
        bilesenler = [
            ("motor.py", "Arac motoru"),
            ("beyin.py", "LLM katmani"),
            ("main.py", "Ana ReAct dongusu"),
            ("reyment.py", "CLI"),
            ("start.py", "Orkestrator"),
            ("iteration_budget.py", "Tur butcesi"),
            ("rate_limit_tracker.py", "Hiz sinirlama"),
        ]
        for dosya, aciklama in bilesenler:
            if not (PROJE_KOK / dosya).exists():
                self._bulgu_ekle(
                    "YUKSEK", "bilesen",
                    f"{aciklama} ({dosya}) bulunamadi.",
                    f"Eksik bilesen: {dosya}",
                )

    def rapor(self) -> str:
        """Denetim raporu metni."""
        if not self._bulgular:
            return "[SecurityAudit] Guvenlik denetimi: TEMIZ (0 bulgu)\n"

        yuksek = sum(1 for b in self._bulgular if b["seviye"] == "YUKSEK")
        orta = sum(1 for b in self._bulgular if b["seviye"] == "ORTA")
        dusuk = sum(1 for b in self._bulgular if b["seviye"] == "DUSUK")

        satirlar = [
            f"[SecurityAudit] Guvenlik Denetimi: {len(self._bulgular)} bulgu\n"
            f"  YUKSEK: {yuksek}, ORTA: {orta}, DUSUK: {dusuk}\n"
        ]

        for b in self._bulgular:
            satirlar.append(f"\n  [{b['seviye']}] [{b['kategori']}] {b['mesaj']}")
            if b["cozum"]:
                satirlar.append(f"    Cozum: {b['cozum']}")

        return "\n".join(satirlar)


if __name__ == "__main__":
    a = SecurityAudit()
    bulgular = a.tarama_yap()
    print(a.rapor())
