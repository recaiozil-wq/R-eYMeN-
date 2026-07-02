# -*- coding: utf-8 -*-
"""
guardrails.py — Hallucination filtreleme ve HITL sıkılaştırma.

İki bileşen:
  1. HallucinationFiltresi
       LLM yanıtında risk işaretlerini (belirsiz dil, doğrulanamaz iddia,
       yanlış sürüm referansı, öz-referans halüsinasyon) tespit eder.
       Yanıtı değiştirmez; yalnızca uyarı listesi üretir.

  2. HITLSikistirici
       motor.ekstra_riskli kümesini genişleterek ek araçları HITL onayına alır.
       geri_al() ile eski küme geri yüklenir.

Kullanım::

    from guardrails import HallucinationFiltresi, HITLSikistirici

    filtre = HallucinationFiltresi()
    _, uyarilar = filtre.filtrele(yanit, hedef="dosya oluştur")

    hitl = HITLSikistirici(motor)
    hitl.sikilas()          # RISKLI kümesine ek araçlar ekle
    hitl.geri_al()          # eski hale döndür
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ── Regex kalıpları ──────────────────────────────────────────────────────────

# Belirsiz / emin olmayan dil
_EMIN_OLMAYAN_KALIPLAR: list[str] = [
    r"\bsanır[ım|ız]?\b",
    r"\bgaliba\b",
    r"\btahmin\s+ediyorum\b",
    r"\bolabilir(?:im|siniz)?\b",
    r"\bbelki\b",
    r"\bdüşünüyorum\s+ki\b",
    r"\byüksek\s+ihtimalle?\b",
    r"\bmuhtemelen\b",
]

# Doğrulanamayan kesin iddia
_KESIN_IDDIA_KALIPLARI: list[str] = [
    r"\bkesinlikle\b",
    r"\bmutlaka\b",
    r"\bher\s+zaman\s+(?:çalışır|doğru|işe\s+yarar)\b",
    r"\basla\s+(?:hata\s+vermez|çökmez|başarısız\s+olmaz)\b",
    r"\b%100\b",
    r"\bgarantili\b",
]

# Eski / yanlış sürüm referansları
_YANLIS_SURUM_KALIPLARI: list[str] = [
    r"\bPython\s+[12]\.[0-9]\b",
    r"\bWindows\s+(?:3|9[58]|ME|XP)\b",
]

# LLM'in yapamayacağı eylemleri yaptığını iddia etmesi
_OZ_REFERANS_KALIPLARI: list[str] = [
    r"\binternetle\s+(?:kontrol\s+ettim|baktım)\b",
    r"\baz\s+önce\s+(?:indirdim|kurdum|yükledim)\b",
    r"\bdiskinizdeki\b",
]

# Derleme — tek seferlik, modül yüklenirken
_EMIN_OLMAYAN_RE  = re.compile("|".join(_EMIN_OLMAYAN_KALIPLAR),  re.IGNORECASE)
_KESIN_IDDIA_RE   = re.compile("|".join(_KESIN_IDDIA_KALIPLARI),  re.IGNORECASE)
_YANLIS_SURUM_RE  = re.compile("|".join(_YANLIS_SURUM_KALIPLARI), re.IGNORECASE)
_OZ_REFERANS_RE   = re.compile("|".join(_OZ_REFERANS_KALIPLARI),  re.IGNORECASE)

# Uzun yanıt eşiği (karakter)
_UZUN_YANIT_ESIGI: int = 2500


# ── Uyarı veri yapısı ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Uyari:
    """Tek bir hallucination uyarısı."""
    kod:   str    # Makine tarafından okunabilir tanımlayıcı (ör. "EMIN_OLMAYAN")
    mesaj: str    # İnsan için açıklama
    skor:  float  # Bu uyarının risk puanına katkısı

    def __str__(self) -> str:
        return f"[Guardrail:{self.kod}] {self.mesaj}"


# ── Hallucination filtresi ───────────────────────────────────────────────────

class HallucinationFiltresi:
    """LLM yanıtında hallucination işaretlerini tespit eder.

    Yanıtı değiştirmez — uyarı listesi üretir ve yanıtı olduğu gibi döndürür.
    ReAct döngüsü veya kullanıcı uyarıları göz önünde bulundurarak karar verebilir.

    Args:
        esik_skor: Toplam risk puanı bu eşiği geçerse yanıt "riskli" sayılır.
                   Varsayılan: 2.0
    """

    def __init__(self, esik_skor: float = 2.0) -> None:
        if esik_skor <= 0:
            raise ValueError(f"esik_skor pozitif olmalı, alınan: {esik_skor}")
        self.esik_skor = esik_skor
        self._toplam_kontrol: int = 0
        self._uyarili_yanit:  int = 0

    # ── Ana API ─────────────────────────────────────────────────────────────

    def filtrele(
        self,
        yanit: str,
        hedef: str = "",
    ) -> tuple[str, list[Uyari]]:
        """Yanıtı hallucination için tara.

        Args:
            yanit:  LLM'den gelen ham metin.
            hedef:  Kullanıcı görevinin kısa açıklaması (ilişki kontrolü için).

        Returns:
            (degistirilmemis_yanit, uyari_listesi)
            Uyarı listesi boşsa yanıt temiz kabul edilir.
        """
        self._toplam_kontrol += 1
        uyarilar: list[Uyari] = []

        uyarilar.extend(self._emin_olmayan_kontrol(yanit))
        uyarilar.extend(self._kesin_iddia_kontrol(yanit))
        uyarilar.extend(self._yanlis_surum_kontrol(yanit))
        uyarilar.extend(self._oz_referans_kontrol(yanit))
        uyarilar.extend(self._uzun_yanit_kontrol(yanit))
        uyarilar.extend(self._iliski_kontrol(yanit, hedef))

        toplam_skor = sum(u.skor for u in uyarilar)
        if toplam_skor > self.esik_skor:
            self._uyarili_yanit += 1
            logger.debug(
                "[HallucinationFiltresi] Riskli yanıt tespit edildi (skor=%.2f, eşik=%.2f).",
                toplam_skor, self.esik_skor,
            )

        return yanit, uyarilar

    def istatistik(self) -> dict[str, float | int]:
        """Birikimli kontrol istatistiklerini döndürür."""
        return {
            "toplam_kontrol": self._toplam_kontrol,
            "uyarili":        self._uyarili_yanit,
            "oran": round(
                self._uyarili_yanit / self._toplam_kontrol, 3
            ) if self._toplam_kontrol else 0.0,
        }

    # ── Kontrol yöntemleri ──────────────────────────────────────────────────

    def _emin_olmayan_kontrol(self, yanit: str) -> list[Uyari]:
        if _EMIN_OLMAYAN_RE.search(yanit):
            return [Uyari(
                kod="EMIN_OLMAYAN",
                mesaj="Yanıt belirsiz/emin olmayan dil içeriyor — doğrulama önerilir.",
                skor=0.5,
            )]
        return []

    def _kesin_iddia_kontrol(self, yanit: str) -> list[Uyari]:
        if _KESIN_IDDIA_RE.search(yanit):
            return [Uyari(
                kod="KESIN_IDDIA",
                mesaj="Yanıt doğrulanamaz kesin iddia içeriyor.",
                skor=1.0,
            )]
        return []

    def _yanlis_surum_kontrol(self, yanit: str) -> list[Uyari]:
        m = _YANLIS_SURUM_RE.search(yanit)
        if m:
            return [Uyari(
                kod="YANLIS_SURUM",
                mesaj=f"Eski/yanlış sürüm referansı: '{m.group()}'.",
                skor=1.5,
            )]
        return []

    def _oz_referans_kontrol(self, yanit: str) -> list[Uyari]:
        if _OZ_REFERANS_RE.search(yanit):
            return [Uyari(
                kod="OZ_REFERANS",
                mesaj="LLM internet/disk erişimi iddiası — muhtemel halüsinasyon.",
                skor=2.0,
            )]
        return []

    def _uzun_yanit_kontrol(self, yanit: str) -> list[Uyari]:
        if len(yanit) > _UZUN_YANIT_ESIGI:
            return [Uyari(
                kod="UZUN_YANIT",
                mesaj=f"Yanıt uzun ({len(yanit)} karakter) — baş/son kontrolü önerilir.",
                skor=0.3,
            )]
        return []

    def _iliski_kontrol(self, yanit: str, hedef: str) -> list[Uyari]:
        """Hedef kelimeleriyle yanıt arasındaki örtüşmeyi basitçe kontrol eder."""
        if len(hedef) <= 10 or len(yanit) <= 50:
            return []
        hedef_kelimeleri  = set(hedef.lower().split()[:5])
        yanit_kelimeleri  = set(yanit.lower().split())
        if hedef_kelimeleri and not hedef_kelimeleri & yanit_kelimeleri:
            return [Uyari(
                kod="ILISKISIZ",
                mesaj="Yanıt hedefe çok az atıf içeriyor.",
                skor=0.5,
            )]
        return []


# ── HITL Sıkılaştırma ───────────────────────────────────────────────────────

# Varsayılan ek riskli araçlar
_EK_RISKLI_ARACLAR: frozenset[str] = frozenset({
    "DOSYA_YAZ",        # Disk yazma
    "TARAYICI_AC",      # Tarayıcı açma
    "WEB_ARA",          # İnternet erişimi
    "TELEGRAM_GONDER",  # Dış mesaj gönderme
    "GORUNTU_ANALIZ",   # Görüntü → LLaVA
})


class HITLSikistirici:
    """HITL onay eşiğini yükseltip daha fazla aracı onaya tabi tutan yönetici.

    motor.ekstra_riskli kümesini genişleterek ek araçları HITL akışına alır.
    geri_al() çağrısıyla orijinal küme geri yüklenir.

    Args:
        motor:       ReAct motoru (calistir() metoduna sahip nesne).
        ek_araclar:  Onaya eklenecek araç adları kümesi.
                     None ise _EK_RISKLI_ARACLAR kullanılır.
    """

    def __init__(
        self,
        motor: Optional[object] = None,
        ek_araclar: Optional[frozenset[str]] = None,
    ) -> None:
        self._motor = motor
        self._ek_araclar: frozenset[str] = ek_araclar or _EK_RISKLI_ARACLAR
        self._orijinal_riskli: Optional[set[str]] = None
        self._aktif = False

    def sikilas(self) -> None:
        """RISKLI kümesini genişlet ve HITL eşiğini yükselt."""
        if self._aktif:
            logger.debug("[HITL] Zaten sıkılaştırılmış, tekrar çağrı görmezden gelindi.")
            return
        if not self._motor:
            logger.warning("[HITL] Motor tanımlı değil; sıkılaştırma atlandı.")
            return
        if not hasattr(self._motor, "calistir"):
            logger.warning("[HITL] Motor.calistir() yok; sıkılaştırma atlandı.")
            return

        # ekstra_riskli attr'u yoksa boş kümeyle başlat
        if not hasattr(self._motor, "ekstra_riskli"):
            self._motor.ekstra_riskli = set()  # type: ignore[union-attr]

        self._orijinal_riskli = set(self._motor.ekstra_riskli)  # type: ignore[union-attr]
        self._motor.ekstra_riskli |= self._ek_araclar             # type: ignore[union-attr]
        self._aktif = True
        logger.info("[HITL] Sıkılaştırıldı: %d araç onaya eklendi.", len(self._ek_araclar))

    def geri_al(self) -> None:
        """RISKLI kümesini eski haline getir."""
        if not self._aktif:
            return
        if self._motor and self._orijinal_riskli is not None:
            self._motor.ekstra_riskli = self._orijinal_riskli  # type: ignore[union-attr]
        self._aktif = False
        logger.info("[HITL] Sıkılaştırma geri alındı.")

    @property
    def aktif(self) -> bool:
        """Sıkılaştırma aktif mi?"""
        return self._aktif

    # Geriye dönük uyumluluk
    def aktif_mi(self) -> bool:  # noqa: D102
        return self._aktif


# ── Motor HITL yaması ─────────────────────────────────────────────────────────

def motor_hitl_yamasi_uygula(motor: object) -> None:
    """motor.calistir() metoduna ekstra_riskli desteği ekler (monkey-patch).

    Motor varsayılan olarak yalnızca sabit RISKLI kümesine bakar.
    Bu yama, motor.ekstra_riskli kümesini de kontrol etmesini sağlar.
    Yama yalnızca bir kez uygulanır; tekrar çağrılması güvenlidir.

    Args:
        motor: calistir(arac, ham_param) metoduna sahip nesne.
    """
    if hasattr(motor, "_orijinal_calistir"):
        return  # Zaten uygulandı

    motor._orijinal_calistir = motor.calistir  # type: ignore[union-attr]

    def _yamali_calistir(arac: str, ham_param: str) -> str:
        ekstra: frozenset[str] | set[str] = getattr(motor, "ekstra_riskli", frozenset())
        onay_fn = getattr(motor, "onay_fonksiyonu", None)

        if arac in ekstra and onay_fn is not None:
            ozet = ham_param[:120] if ham_param else ""
            if not onay_fn(arac, ozet):
                return f"[İptal]: Kullanıcı '{arac}' eylemini reddetti (HITL)."

        return motor._orijinal_calistir(arac, ham_param)  # type: ignore[union-attr]

    motor.calistir = _yamali_calistir  # type: ignore[union-attr]
    logger.info("[HITL] Motor yaması uygulandı.")


# ── Hızlı test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(level=_logging.DEBUG, format="%(levelname)s %(message)s")

    print("=== Hallucination Filtresi Testi ===")
    filtre = HallucinationFiltresi(esik_skor=1.5)

    testler: list[tuple[str, str]] = [
        ("Python 2.7 ile test.py dosyasını yazacağım.", "Python ile dosya yaz"),
        ("Dosyayı oluşturdum ve internet'ten kontrol ettim.", "dosya oluştur"),
        ("Bu işlevi çağırabilirsin.", "fonksiyon çağır"),
        ("Bu kesinlikle %100 çalışacak.", "güvenilir kod"),
        ("Belki galiba bu yöntem daha iyi olabilir.", "yöntem seç"),
    ]

    for yanit, hedef in testler:
        _, uyarilar = filtre.filtrele(yanit, hedef=hedef)
        etiket = "RİSKLİ" if uyarilar else "TEMİZ "
        print(f"[{etiket}] {yanit[:55]}")
        for u in uyarilar:
            print(f"         {u}")

    print(f"\nİstatistik: {filtre.istatistik()}")

    print("\n=== HITL Testi ===")
    hitl = HITLSikistirici()
    hitl.sikilas()
    print(f"Aktif mi: {hitl.aktif}")
    hitl.geri_al()
    print(f"Aktif mi: {hitl.aktif}")
