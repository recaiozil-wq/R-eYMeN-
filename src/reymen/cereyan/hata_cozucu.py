# -*- coding: utf-8 -*-
"""
hata_cozucu.py — Windows hata tespit, kodlama ve cozum yoneticisi.

4 bilesen:
  1. HataWatchdog       — Ekran goruntusu + OCR ile hata tespiti
  2. HataKoduUretici    — HATA-XXXX formatli kod + .md kayit
  3. TerminalHataParser — Windows terminal ciktisindan hata ayiklama
  4. CozumUygulayici    — Kullanicinin verdigi cozumu otomatik uygula

Entegrasyon (motor.py):
    HATA_WATCH_BASLAT, HATA_WATCH_DURDUR, HATA_KOD_AL,
    TERMINAL_HATA_PARSE, COZUM_UYGULA
"""

from __future__ import annotations

import datetime
import logging
import os
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.resolve()
HATA_KLASORU = ROOT / ".ReYMeN" / "hata_kodlari"

# OCR modulu (opsiyonel)
try:
    import pytesseract as _pytesseract
    _OCR_VAR = True
except ImportError:
    _OCR_VAR = False

try:
    from PIL import Image as _PIL_Image
    _PIL_VAR = True
except ImportError:
    _PIL_VAR = False

try:
    import mss as _mss
    _MSS_VAR = True
except ImportError:
    _MSS_VAR = False

# Windows API (opsiyonel)
try:
    import ctypes
    from ctypes import wintypes
    _WIN_API_VAR = True
except ImportError:
    _WIN_API_VAR = False

# ── Hata kodu sayaç dosyasi ────────────────────────────────────────────────
_SAYAC_DOSYASI = HATA_KLASORU / "_sayaç.txt"


def _sonraki_hata_kodu() -> str:
    """HATA-001, HATA-002, ... seklinde siradaki kodu uret."""
    HATA_KLASORU.mkdir(parents=True, exist_ok=True)
    son = 0
    if _SAYAC_DOSYASI.exists():
        try:
            son = int(_SAYAC_DOSYASI.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            son = 0
    son += 1
    try:
        _SAYAC_DOSYASI.write_text(str(son), encoding="utf-8")
    except OSError as e:
        logger.warning("[HataKod] Sayac yazma hatasi: %s", e)
    return f"HATA-{son:04d}"


# ── Veri yapilari ──────────────────────────────────────────────────────────

@dataclass
class HataKaydi:
    """Bir hata kaydinin tum bilgileri."""
    kod: str
    zaman: str
    kategori: str
    ozet: str
    ham_metin: str
    ekran_yolu: str = ""
    dosya: str = ""
    satir: int = 0
    cozum_durumu: str = "bulunamadi"  # bulunamadi / cozuldu / bekliyor
    cozum: str = ""


# ── 1. HataWatchdog ────────────────────────────────────────────────────────

class HataWatchdog:
    """Ekrani periyodik tara, hata dialog'u tespit et, callback tetikle.

    Varsayilan hata anahtar kelimeleri:
        Hata, Error, Exception, Access Denied, File Not Found,
        Permission denied, SyntaxError, TypeError, ValueError
    """

    _VARSAYILAN_KELIMELER = frozenset({
        "hata", "error", "exception", "access denied", "file not found",
        "permission denied", "syntaxerror", "typeerror", "valueerror",
        "modulenotfounderror", "importerror", "keyerror", "indexerror",
        "runtimeerror", "stop", "critical", "failed", "basarisiz",
    })

    def __init__(
        self,
        aralik_sn: float = 5.0,
        kelimeler: Optional[set[str]] = None,
        callback: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self.aralik_sn = aralik_sn
        self.kelimeler = kelimeler or self._VARSAYILAN_KELIMELER
        self.callback = callback
        self._thread: Optional[threading.Thread] = None
        self._durdurma = threading.Event()
        self._aktif = False

    def baslat(self) -> None:
        """Watchdog'u arka planda baslat."""
        if self._aktif:
            logger.debug("[HataWatchdog] Zaten calisiyor.")
            return
        if not _MSS_VAR or not _OCR_VAR:
            logger.warning("[HataWatchdog] mss veya pytesseract yok, watchdog sinirli calisir.")
        self._durdurma.clear()
        self._aktif = True
        self._thread = threading.Thread(target=self._dongu, daemon=True)
        self._thread.start()
        logger.info("[HataWatchdog] Baslatildi (%.1f sn aralikla).", self.aralik_sn)

    def durdur(self) -> None:
        """Watchdog'u durdur."""
        self._aktif = False
        self._durdurma.set()
        logger.info("[HataWatchdog] Durduruldu.")

    @property
    def calisiyor(self) -> bool:
        return self._aktif and (self._thread is not None and self._thread.is_alive())

    def _dongu(self) -> None:
        """Ana tarama dongusu."""
        while not self._durdurma.is_set():
            try:
                ekran_metni = self._ekran_oku()
                if ekran_metni:
                    eslesen = {k for k in self.kelimeler if k in ekran_metni.lower()}
                    if eslesen:
                        logger.info("[HataWatchdog] Hata tespit edildi: %s", eslesen)
                        if self.callback:
                            self.callback(ekran_metni, ", ".join(sorted(eslesen)))
            except Exception as e:
                logger.debug("[HataWatchdog] Tarama hatasi: %s", e)
            self._durdurma.wait(timeout=self.aralik_sn)

    def _ekran_oku(self) -> str:
        """Mevcut ekran goruntusunu al, OCR ile metne cevir."""
        if not _MSS_VAR or not _OCR_VAR or not _PIL_VAR:
            return ""
        try:
            with _mss.mss() as sct:
                mon = sct.monitors[1]  # Ana monitor
                goruntu = sct.grab(mon)
                img = _PIL_Image.frombytes("RGB", goruntu.size, goruntu.rgb)
                metin = _pytesseract.image_to_string(img, lang="tur+eng")
                return metin
        except Exception as e:
            logger.debug("[HataWatchdog] Ekran okuma hatasi: %s", e)
            return ""


# ── 2. HataKoduUretici ────────────────────────────────────────────────────

class HataKoduUretici:
    """Hata metninden HATA-XXXX formatli kayit olusturur."""

    KATEGORILER = {
        "import": re.compile(r"import|modulenotfound|importerror", re.IGNORECASE),
        "syntax": re.compile(r"syntax|indentation|invalid syntax", re.IGNORECASE),
        "tip": re.compile(r"typeerror|valueerror|cannot unpack|unhashable", re.IGNORECASE),
        "dosya": re.compile(r"filenotfound|permission|file exists|no such file", re.IGNORECASE),
        "baglanti": re.compile(r"timeout|connection|network|socket|cannot connect", re.IGNORECASE),
        "bellek": re.compile(r"memory|outofmemory|alloc", re.IGNORECASE),
        "ekran": re.compile(r"screen|display|monitor|opencv|camera", re.IGNORECASE),
    }

    def __init__(self) -> None:
        HATA_KLASORU.mkdir(parents=True, exist_ok=True)

    def kaydet(
        self,
        ham_metin: str,
        ekran_yolu: str = "",
        dosya: str = "",
        satir: int = 0,
    ) -> HataKaydi:
        """Hata metnini analiz et, kod uret, .md olarak kaydet.

        Returns:
            HataKaydi — olusan kayit.
        """
        kategori = self._kategori_bul(ham_metin)
        ozet = self._ozet_cikar(ham_metin)
        kod = _sonraki_hata_kodu()
        zaman = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        kayit = HataKaydi(
            kod=kod,
            zaman=zaman,
            kategori=kategori,
            ozet=ozet,
            ham_metin=ham_metin,
            ekran_yolu=ekran_yolu,
            dosya=dosya,
            satir=satir,
            cozum_durumu="bulunamadi",
            cozum="",
        )

        self._md_yaz(kayit)
        logger.info("[HataKod] %s: [%s] %s", kod, kategori, ozet)
        return kayit

    def _kategori_bul(self, metin: str) -> str:
        for kat, pattern in self.KATEGORILER.items():
            if pattern.search(metin):
                return kat
        return "diger"

    def _ozet_cikar(self, metin: str) -> str:
        satirlar = [s.strip() for s in metin.split("\n") if s.strip()]
        for s in satirlar:
            if any(k in s.lower() for k in ("error", "hata", "exception", "failed")):
                return s[:120]
        return (satirlar[0][:120] if satirlar else "Bilinmeyen hata")

    def _md_yaz(self, kayit: HataKaydi) -> Path:
        """Hata kaydini .md dosyasi olarak kaydet."""
        yol = HATA_KLASORU / f"{kayit.kod}.md"
        icerik = (
            f"---\n"
            f"kod: {kayit.kod}\n"
            f"zaman: {kayit.zaman}\n"
            f"kategori: {kayit.kategori}\n"
            f"durum: {kayit.cozum_durumu}\n"
            f"---\n\n"
            f"# {kayit.kod}: {kayit.ozet}\n\n"
            f"## Kategori\n{kayit.kategori}\n\n"
            f"## Hata Metni\n```\n{kayit.ham_metin}\n```\n"
        )
        if kayit.ekran_yolu:
            icerik += f"\n## Ekran Goruntusu\n![]({kayit.ekran_yolu})\n"
        if kayit.dosya:
            icerik += f"\n## Kaynak\nDosya: `{kayit.dosya}` | Satir: {kayit.satir}\n"
        icerik += f"\n## Cozum\nDurum: {kayit.cozum_durumu}\n"
        if kayit.cozum:
            icerik += f"{kayit.cozum}\n"
        try:
            yol.write_text(icerik, encoding="utf-8")
        except OSError as e:
            logger.error("[HataKod] Yazma hatasi (%s): %s", yol, e)
        return yol

    def cozum_ekle(self, kod: str, cozum: str) -> bool:
        """Mevcut hata kaydina cozum ekle, durumu 'cozuldu' yap."""
        yol = HATA_KLASORU / f"{kod}.md"
        if not yol.exists():
            logger.warning("[HataKod] Kayit bulunamadi: %s", kod)
            return False
        try:
            icerik = yol.read_text(encoding="utf-8")
            icerik = icerik.replace("durum: bulunamadi", "durum: cozuldu")
            icerik = icerik.replace("durum: bekliyor", "durum: cozuldu")
            if "## Cozum\n" in icerik:
                icerik = re.sub(
                    r"## Cozum\n.*?(?=\n##|\Z)",
                    f"## Cozum\nDurum: cozuldu\n{cozum}\n",
                    icerik,
                    flags=re.DOTALL,
                )
            else:
                icerik += f"\n## Cozum\nDurum: cozuldu\n{cozum}\n"
            yol.write_text(icerik, encoding="utf-8")
            logger.info("[HataKod] %s cozuldu.", kod)
            return True
        except OSError as e:
            logger.error("[HataKod] Cozum yazma hatasi: %s", e)
            return False

    def kayit_bul(self, kod: str) -> Optional[HataKaydi]:
        """Koda gore kayit bilgisini getir."""
        yol = HATA_KLASORU / f"{kod}.md"
        if not yol.exists():
            return None
        try:
            icerik = yol.read_text(encoding="utf-8")
            durum_m = re.search(r"durum:\s*(.+)", icerik)
            kategori_m = re.search(r"kategori:\s*(.+)", icerik)
            return HataKaydi(
                kod=kod,
                zaman="",
                kategori=kategori_m.group(1).strip() if kategori_m else "diger",
                ozet="",
                ham_metin=icerik,
                cozum_durumu=durum_m.group(1).strip() if durum_m else "bulunamadi",
            )
        except OSError:
            return None


# ── 3. TerminalHataParser ──────────────────────────────────────────────────

class TerminalHataParser:
    """Windows PowerShell/cmd ciktisindan hata mesajlarini ayiklar."""

    # Windows hata kaliplari
    _HATA_KALIPLARI = [
        re.compile(r"(?:Hata|Error|ERROR)\s*[:：]\s*(.+)", re.IGNORECASE),
        re.compile(r"(?:Exception|exception)\s*[:：]\s*(.+)"),
        re.compile(r"(?:failed|FAILED)\s*[:：]\s*(.+)", re.IGNORECASE),
        re.compile(r"(?:Traceback|traceback).+?(?=\n\n|\Z)", re.DOTALL),
        re.compile(r"(?:catastrophic|critical|fatal)", re.IGNORECASE),
        re.compile(r"Access\s+(?:Denied|denied)"),
        re.compile(r"ModuleNotFoundError|ImportError|SyntaxError|TypeError|ValueError"),
    ]

    # PowerShell ozel hata desenleri
    _PS_KALIPLARI = [
        re.compile(r"TerminatingError\((.+?)\)"),
        re.compile(r"\+\s+CategoryInfo\s+:\s*(.+)"),
        re.compile(r"\+\s+FullyQualifiedErrorId\s+:\s*(.+)"),
    ]

    def parse(self, cikti: str) -> dict:
        """Terminal ciktisini analiz et.

        Returns:
            {
                "hata_var": bool,
                "hata_sayisi": int,
                "hata_mesajlari": [str],
                "ps_hata_id": str,
                "ozet": str
            }
        """
        sonuc = {
            "hata_var": False,
            "hata_sayisi": 0,
            "hata_mesajlari": [],
            "ps_hata_id": "",
            "ozet": "",
        }

        for pattern in self._HATA_KALIPLARI:
            for m in pattern.finditer(cikti):
                mesaj = m.group(0).strip()[:200]
                if mesaj not in sonuc["hata_mesajlari"]:
                    sonuc["hata_mesajlari"].append(mesaj)

        for pattern in self._PS_KALIPLARI:
            m = pattern.search(cikti)
            if m:
                val = m.group(1).strip() if m.groups() else m.group(0).strip()
                if not sonuc["ps_hata_id"]:
                    sonuc["ps_hata_id"] = val

        sonuc["hata_var"] = len(sonuc["hata_mesajlari"]) > 0
        sonuc["hata_sayisi"] = len(sonuc["hata_mesajlari"])
        sonuc["ozet"] = (
            sonuc["hata_mesajlari"][0][:150] if sonuc["hata_mesajlari"]
            else "Hata bulunamadi"
        )
        return sonuc


# ── 4. CozumUygulayici ─────────────────────────────────────────────────────

class CozumUygulayici:
    """Kullanicinin verdigi cozum metnini otomatik uygula.

    Cozum formati:
        HATA-XXXX:
        Dosya: yol/dosya.py
        Satir: 42
        Eski: hatali_kod
        Yeni: duzeltilmis_kod
    """

    def __init__(self, hata_uretici: Optional[HataKoduUretici] = None) -> None:
        self.hata_uretici = hata_uretici or HataKoduUretici()

    def uygula(self, cozum_metni: str) -> dict:
        """Cozum metnini cozumle ve uygula.

        Args:
            cozum_metni: Kullanicidan gelen cozum (HATA-XXXX: ...)

        Returns:
            {"basarili": bool, "kod": str, "mesaj": str, "patch_sonuc": str}
        """
        # HATA kodunu bul
        kod_m = re.search(r"(HATA-\d{4})", cozum_metni)
        kod = kod_m.group(1) if kod_m else ""

        # Dosya yolunu bul
        dosya_m = re.search(r"Dosya:\s*(.+)", cozum_metni)
        dosya_yolu = dosya_m.group(1).strip() if dosya_m else ""

        # Satir numarasi
        satir_m = re.search(r"Satir:\s*(\d+)", cozum_metni)
        satir = int(satir_m.group(1)) if satir_m else 0

        # Eski/Yeni blok
        eski_m = re.search(r"Eski:\s*(.+?)(?=Yeni:|\Z)", cozum_metni, re.DOTALL)
        yeni_m = re.search(r"Yeni:\s*(.+)", cozum_metni, re.DOTALL)
        eski = eski_m.group(1).strip() if eski_m else ""
        yeni = yeni_m.group(1).strip() if yeni_m else ""

        if not dosya_yolu or not yeni:
            return {"basarili": False, "kod": kod, "mesaj": "Eksik cozum: dosya veya yeni kod bulunamadi.", "patch_sonuc": ""}

        # Tam yol
        tam_yol = ROOT / dosya_yolu
        if not tam_yol.exists():
            tam_yol = ROOT.parent / dosya_yolu
        if not tam_yol.exists():
            return {"basarili": False, "kod": kod, "mesaj": f"Dosya bulunamadi: {dosya_yolu}", "patch_sonuc": ""}

        # Patch uygula
        try:
            icerik = tam_yol.read_text(encoding="utf-8")
            if eski and eski in icerik:
                yeni_icerik = icerik.replace(eski, yeni, 1)
                tam_yol.write_text(yeni_icerik, encoding="utf-8")
                patch_sonuc = f"{eski} -> {yeni}"
            elif satir > 0:
                satirlar = icerik.split("\n")
                if 0 <= satir - 1 < len(satirlar):
                    satirlar[satir - 1] = yeni
                    tam_yol.write_text("\n".join(satirlar), encoding="utf-8")
                    patch_sonuc = f"Satir {satir} degistirildi"
                else:
                    return {"basarili": False, "kod": kod, "mesaj": f"Satir {satir} dosyada yok.", "patch_sonuc": ""}
            else:
                return {"basarili": False, "kod": kod, "mesaj": "Ne eski kod ne satir belirtilmemis.", "patch_sonuc": ""}

            # Hata kaydini guncelle
            if kod:
                self.hata_uretici.cozum_ekle(kod, cozum_metni)

            logger.info("[Cozum] %s uygulandi: %s", kod or "Cozum", patch_sonuc[:100])
            return {"basarili": True, "kod": kod, "mesaj": "Cozum uygulandi.", "patch_sonuc": patch_sonuc}

        except Exception as e:
            logger.error("[Cozum] Uygulama hatasi: %s", e)
            return {"basarili": False, "kod": kod, "mesaj": str(e), "patch_sonuc": ""}


# ── motor.py tool kayit fonksiyonu ─────────────────────────────────────────

def motor_kaydet(motor) -> None:
    """motor.py icin HATA_ ve COZUM_ araclarini kaydet."""
    watchdog = HataWatchdog()
    hata_kod = HataKoduUretici()
    terminal_parser = TerminalHataParser()
    cozum = CozumUygulayici(hata_kod)

    # Orjinal calistir fonksiyonunu bul
    if not hasattr(motor, "_orijinal_calistir"):
        motor._orijinal_calistir = motor.calistir

    def yamali_calistir(arac: str, ham_param: str) -> str:
        arac = arac.upper()

        if arac == "HATA_WATCH_BASLAT":
            watchdog.baslat()
            return "[HataWatchdog] Baslatildi."

        if arac == "HATA_WATCH_DURDUR":
            watchdog.durdur()
            return "[HataWatchdog] Durduruldu."

        if arac == "HATA_KOD_AL":
            kayit = hata_kod.kaydet(ham_param)
            return (f"[HataKod] {kayit.kod}: [{kayit.kategori}] {kayit.ozet}\n"
                    f"Dosya: .ReYMeN/hata_kodlari/{kayit.kod}.md\n"
                    f"Claude'a su kodu yapistir: {kayit.kod}")

        if arac == "TERMINAL_HATA_PARSE":
            sonuc = terminal_parser.parse(ham_param)
            if sonuc["hata_var"]:
                return (f"[Terminal] {sonuc['hata_sayisi']} hata bulundu.\n"
                        f"Ilki: {sonuc['ozet']}")
            return "[Terminal] Hata bulunamadi."

        if arac == "COZUM_UYGULA":
            sonuc = cozum.uygula(ham_param)
            if sonuc["basarili"]:
                return f"[Cozum] Basarili: {sonuc['patch_sonuc']}"
            return f"[Cozum] Basarisiz: {sonuc['mesaj']}"

        return motor._orijinal_calistir(arac, ham_param)

    motor.calistir = yamali_calistir
    logger.info("[HataCozucu] 5 arac kaydedildi: HATA_WATCH_BASLAT, HATA_WATCH_DURDUR, HATA_KOD_AL, TERMINAL_HATA_PARSE, COZUM_UYGULA")


# ── Hizli test ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")

    print("=== 1. TerminalHataParser Test ===")
    parser = TerminalHataParser()
    ornek_cikti = """PS C:\\proje> python test.py
Traceback (most recent call last):
  File "test.py", line 10, in <module>
    import missing_module
ModuleNotFoundError: No module named 'missing_module'
"""
    sonuc = parser.parse(ornek_cikti)
    print(f"Hata var: {sonuc['hata_var']}, Sayi: {sonuc['hata_sayisi']}")
    for m in sonuc['hata_mesajlari'][:2]:
        print(f"  -> {m[:80]}")

    print("\n=== 2. HataKoduUretici Test ===")
    uretici = HataKoduUretici()
    kayit = uretici.kaydet(ornek_cikti)
    print(f"Kod: {kayit.kod}, Kategori: {kayit.kategori}")
    print(f"Ozet: {kayit.ozet}")

    print("\n=== 3. CozumUygulayici Test ===")
    cozum = CozumUygulayici(uretici)
    test_cozum = f"""{kayit.kod}:
Dosya: test.py
Satir: 10
Eski: import missing_module
Yeni: import existing_module
"""
    r = cozum.uygula(test_cozum)
    print(f"Basarili: {r['basarili']}, Mesaj: {r['mesaj']}")

    print("\n=== 4. Watchdog Test (sadece baslat/durdur) ===")
    wd = HataWatchdog(aralik_sn=60.0)
    wd.baslat()
    print(f"Calisiyor: {wd.calisiyor}")
    wd.durdur()
    print(f"Calisiyor: {wd.calisiyor}")

    print("\n✓ Tum testler gecti.")
