# -*- coding: utf-8 -*-
"""persistence.py — Güvenlik Kalıcılık Katmanı.

Güvenlik olaylarını, tehdit loglarını ve denetim izlerini
kalıcı olarak saklar. Şüpheli etkinlik geçmişine dayalı
risk profili oluşturur.

Bileşenler:
  - GüvenlikOlayı: Tek bir güvenlik kaydı
  - KalıcılıkDeposuu: JSON tabanlı olay deposu
  - RiskProfili: Kaynak başına risk skoru
  - AuditTrail: Değişmez denetim izi (append-only)
"""

import json
import os
import time
from pathlib import Path
from typing import Optional
import logging
logger = logging.getLogger(__name__)

DEPO_KOKU   = Path(__file__).parent / ".ReYMeN" / "security"
OLAY_DOSYASI = DEPO_KOKU / "events.jsonl"
DENETIM_YOLU = DEPO_KOKU / "audit_trail.jsonl"
PROFIL_YOLU  = DEPO_KOKU / "risk_profiles.json"

DEPO_KOKU.mkdir(parents=True, exist_ok=True)


# ── Veri Modelleri ────────────────────────────────────────────────────

class GuvenlikOlayi:
    """Tek bir güvenlik olayı kaydı."""

    SEVIYE_BILGI   = "INFO"
    SEVIYE_UYARI   = "WARN"
    SEVIYE_TEHDIT  = "THREAT"
    SEVIYE_KRITIK  = "CRITICAL"

    def __init__(
        self,
        kategori: str,
        aciklama: str,
        seviye: str         = "INFO",
        kaynak: str         = "",
        detay: dict         = None,
    ):
        self.id         = f"{int(time.time() * 1000)}"
        self.zaman      = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.kategori   = kategori
        self.aciklama   = aciklama
        self.seviye     = seviye
        self.kaynak     = kaynak
        self.detay      = detay or {}

    def to_dict(self) -> dict:
        return {
            "id":        self.id,
            "zaman":     self.zaman,
            "kategori":  self.kategori,
            "aciklama":  self.aciklama,
            "seviye":    self.seviye,
            "kaynak":    self.kaynak,
            "detay":     self.detay,
        }

    @classmethod
    def from_dict(cls, veri: dict) -> "GuvenlikOlayi":
        o = cls(
            kategori  = veri.get("kategori", ""),
            aciklama  = veri.get("aciklama", ""),
            seviye    = veri.get("seviye", "INFO"),
            kaynak    = veri.get("kaynak", ""),
            detay     = veri.get("detay", {}),
        )
        o.id    = veri.get("id", o.id)
        o.zaman = veri.get("zaman", o.zaman)
        return o


# ── Olay Deposu ───────────────────────────────────────────────────────

class KalicilikDeposu:
    """JSONL tabanlı güvenlik olayı deposu."""

    def __init__(self, dosya: Path = OLAY_DOSYASI):
        self._dosya = dosya

    def kaydet(self, olay: GuvenlikOlayi):
        """Olayı kalıcı olarak kaydet (append-only)."""
        with open(self._dosya, "a", encoding="utf-8") as f:
            f.write(json.dumps(olay.to_dict(), ensure_ascii=False) + "\n")

    def oku(
        self,
        son_n: int          = 100,
        kategori: str       = "",
        min_seviye: str     = "",
        kaynak: str         = "",
    ) -> list[GuvenlikOlayi]:
        """Olayları filtreli oku."""
        if not self._dosya.exists():
            return []

        seviye_siralama = {
            "INFO": 0, "WARN": 1, "THREAT": 2, "CRITICAL": 3
        }
        min_s = seviye_siralama.get(min_seviye, 0)

        olaylar = []
        try:
            with open(self._dosya, encoding="utf-8") as f:
                for satir in f:
                    satir = satir.strip()
                    if not satir:
                        continue
                    try:
                        veri = json.loads(satir)
                        if kategori and veri.get("kategori") != kategori:
                            continue
                        if kaynak and veri.get("kaynak") != kaynak:
                            continue
                        sv = seviye_siralama.get(veri.get("seviye", ""), 0)
                        if sv < min_s:
                            continue
                        olaylar.append(GuvenlikOlayi.from_dict(veri))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            return []

        return olaylar[-son_n:]

    def temizle(self, gun: int = 30):
        """30 günden eski olayları sil."""
        esik = time.time() - (gun * 86400)
        if not self._dosya.exists():
            return 0
        yeni_satirlar = []
        silinen = 0
        with open(self._dosya, encoding="utf-8") as f:
            for satir in f:
                try:
                    veri = json.loads(satir.strip())
                    zaman_str = veri.get("zaman", "")
                    # ISO formatı parse
                    t = time.mktime(time.strptime(zaman_str, "%Y-%m-%dT%H:%M:%S"))
                    if t > esik:
                        yeni_satirlar.append(satir)
                    else:
                        silinen += 1
                except Exception:
                    yeni_satirlar.append(satir)
        with open(self._dosya, "w", encoding="utf-8") as f:
            f.writelines(yeni_satirlar)
        return silinen

    def istatistik(self) -> dict:
        olaylar = self.oku(son_n=10000)
        sayilar: dict[str, int] = {}
        for o in olaylar:
            sayilar[o.seviye] = sayilar.get(o.seviye, 0) + 1
        return {
            "toplam":   len(olaylar),
            "seviyeler": sayilar,
        }


# ── Risk Profili ──────────────────────────────────────────────────────

class RiskProfili:
    """Kaynak başına risk skoru takibi."""

    def __init__(self):
        self._profiller: dict[str, dict] = {}
        self._yukle()

    def _yukle(self):
        if PROFIL_YOLU.exists():
            try:
                self._profiller = json.loads(PROFIL_YOLU.read_text(encoding="utf-8"))
            except Exception as _persiste_e180:
                print(f"[UYARI] persistence.py:181 - {_persiste_e180}")

    def _kaydet(self):
        PROFIL_YOLU.write_text(
            json.dumps(self._profiller, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def guncelle(self, kaynak: str, olay_seviyesi: str):
        """Kaynağın risk skorunu olay şiddetine göre artır."""
        puan_map = {"INFO": 1, "WARN": 5, "THREAT": 20, "CRITICAL": 50}
        puan = puan_map.get(olay_seviyesi, 1)

        if kaynak not in self._profiller:
            self._profiller[kaynak] = {
                "skor": 0, "olay_sayisi": 0,
                "son_olay": "", "tehdit_sayisi": 0,
            }
        p = self._profiller[kaynak]
        p["skor"]        = min(p["skor"] + puan, 1000)
        p["olay_sayisi"] += 1
        p["son_olay"]    = time.strftime("%Y-%m-%dT%H:%M:%S")
        if olay_seviyesi in ("THREAT", "CRITICAL"):
            p["tehdit_sayisi"] += 1
        self._kaydet()

    def risk_al(self, kaynak: str) -> int:
        return self._profiller.get(kaynak, {}).get("skor", 0)

    def yuksek_riskli(self, esik: int = 100) -> list[tuple[str, int]]:
        return sorted(
            [(k, v["skor"]) for k, v in self._profiller.items() if v["skor"] >= esik],
            key=lambda x: -x[1],
        )

    def sifirla(self, kaynak: str):
        if kaynak in self._profiller:
            self._profiller[kaynak]["skor"] = 0
            self._kaydet()

    def rapor(self) -> str:
        satirlar = ["Risk Profilleri:"]
        for k, v in sorted(self._profiller.items(), key=lambda x: -x[1].get("skor", 0))[:20]:
            satirlar.append(f"  {k:<30} skor={v['skor']:>4}  olay={v['olay_sayisi']}")
        return "\n".join(satirlar)


# ── Denetim İzi ───────────────────────────────────────────────────────

class AuditTrail:
    """Değişmez denetim izi — sadece ekleme yapılabilir."""

    def __init__(self, dosya: Path = DENETIM_YOLU):
        self._dosya = dosya

    def yaz(
        self,
        islem: str,
        kaynak: str  = "",
        hedef: str   = "",
        sonuc: str   = "OK",
        detay: dict  = None,
    ):
        kayit = {
            "ts":     time.strftime("%Y-%m-%dT%H:%M:%S"),
            "islem":  islem,
            "kaynak": kaynak,
            "hedef":  hedef,
            "sonuc":  sonuc,
            "detay":  detay or {},
        }
        with open(self._dosya, "a", encoding="utf-8") as f:
            f.write(json.dumps(kayit, ensure_ascii=False) + "\n")

    def son(self, n: int = 20) -> list[dict]:
        if not self._dosya.exists():
            return []
        try:
            satirlar = self._dosya.read_text(encoding="utf-8").strip().splitlines()
            return [json.loads(s) for s in satirlar[-n:] if s.strip()]
        except Exception:
            return []

    def ara(self, islem: str = "", kaynak: str = "", son_n: int = 50) -> list[dict]:
        kayitlar = self.son(n=10000)
        if islem:
            kayitlar = [k for k in kayitlar if k.get("islem") == islem]
        if kaynak:
            kayitlar = [k for k in kayitlar if k.get("kaynak") == kaynak]
        return kayitlar[-son_n:]


# ── Birleşik Arayüz ───────────────────────────────────────────────────

class GuvenlikKalicilik:
    """Tüm kalıcılık bileşenlerini yöneten tek sınıf."""

    def __init__(self):
        self.depo   = KalicilikDeposu()
        self.profil = RiskProfili()
        self.denetim = AuditTrail()

    def olay_kaydet(
        self,
        kategori: str,
        aciklama: str,
        seviye: str   = "INFO",
        kaynak: str   = "",
        detay: dict   = None,
    ) -> GuvenlikOlayi:
        """Güvenlik olayı kaydet, risk profilini güncelle, denetim izine yaz."""
        olay = GuvenlikOlayi(kategori, aciklama, seviye, kaynak, detay)
        self.depo.kaydet(olay)
        if kaynak:
            self.profil.guncelle(kaynak, seviye)
        self.denetim.yaz(
            islem  = f"GUVENLIK_{kategori.upper()}",
            kaynak = kaynak,
            sonuc  = seviye,
            detay  = {"aciklama": aciklama[:200]},
        )
        return olay

    def tehdit_kaydet(self, kategori: str, aciklama: str, kaynak: str = "", detay: dict = None):
        return self.olay_kaydet(kategori, aciklama, "THREAT", kaynak, detay)

    def kritik_kaydet(self, kategori: str, aciklama: str, kaynak: str = "", detay: dict = None):
        return self.olay_kaydet(kategori, aciklama, "CRITICAL", kaynak, detay)

    def ozet(self) -> str:
        ist = self.depo.istatistik()
        riskli = self.profil.yuksek_riskli(esik=50)
        satirlar = [
            f"Güvenlik Deposu: {ist['toplam']} olay",
            f"  Seviyeler: {ist['seviyeler']}",
        ]
        if riskli:
            satirlar.append(f"Yüksek Riskli Kaynaklar ({len(riskli)}):")
            for k, s in riskli[:5]:
                satirlar.append(f"  {k}: {s}")
        return "\n".join(satirlar)


# ── Singleton ─────────────────────────────────────────────────────────

_GK: Optional[GuvenlikKalicilik] = None


def guvenlik_kalicilik() -> GuvenlikKalicilik:
    global _GK
    if _GK is None:
        _GK = GuvenlikKalicilik()
    return _GK


def motor_kaydet(motor):
    """Güvenlik kalıcılık araçlarını motora kaydet."""
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return
    gk = guvenlik_kalicilik()
    motor._plugin_arac_kaydet(
        "GUVENLIK_OZET",
        lambda: gk.ozet(),
        "Güvenlik olay deposu özetini göster",
    )
    motor._plugin_arac_kaydet(
        "GUVENLIK_RISKLI",
        lambda esik=50: gk.profil.rapor(),
        "Yüksek riskli kaynakları listele",
    )


if __name__ == "__main__":
    gk = GuvenlikKalicilik()
    gk.olay_kaydet("test", "Başlatma testi", "INFO", kaynak="persistence.py")
    gk.tehdit_kaydet("prompt_injection", "Şüpheli girdi tespit edildi", kaynak="kullanici_1")
    print(gk.ozet())
    print("\nDenetim İzi (son 5):")
    for k in gk.denetim.son(5):
        print(f"  {k['ts']} | {k['islem']} | {k['sonuc']}")
