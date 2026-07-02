#!/usr/bin/env python3
"""
web_test_loop.py — WEB → UYGULA → PUANLA → KARAR döngüsü.

Ajan web'den yeni bilgi bulur, eski bilgiyle test eder,
puanlar ve hangisinin daha iyi olduğuna karar verir.

5 TETİKLEYİCİ:
1. Hafıza boş → anında web
2. Görev başarısız (2. hata) → web
3. Güven < 0.5 → web
4. Geçerlilik geçmiş → arka planda web
5. Çelişki → web
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable
from datetime import date

logger = logging.getLogger(__name__)


# ── Veri Yapıları ─────────────────────────────────────────────────────────

@dataclass
class TestSonucu:
    """Bir yöntemin test sonucu."""
    yontem_adi: str
    hiz_sn: float        # Kaç saniye sürdü? (düşük iyi)
    basari: bool          # Hata verdi mi? (True=başarılı)
    cikti_dogru: bool     # Çıktı doğru mu?
    guvenlik: float       # 0.0-1.0 (1.0=güvenli)
    kaynak_guven: float   # Kaynağın güvenilirliği (web veya hafıza)

    def puan(self) -> float:
        """Toplam puan [0.0, 1.0]"""
        p = 0.0
        # Hız: 1sn altı = 1.0, 60sn üstü = 0.0
        p += max(0, 1.0 - self.hiz_sn / 60.0) * 0.2
        # Başarı: hata yoksa 1.0
        p += (1.0 if self.basari else 0.0) * 0.3
        # Çıktı doğruluğu
        p += (1.0 if self.cikti_dogru else 0.0) * 0.2
        # Güvenlik
        p += self.guvenlik * 0.15
        # Kaynak güvenilirliği
        p += self.kaynak_guven * 0.15
        return round(p, 4)


# ── 5 Tetikleyici ─────────────────────────────────────────────────────────

TETIKLEYICI_TANIMLARI = {
    1: {
        "ad": "Hafiza Bos",
        "kosul": "once_hafiza.ara() → bulunamadi",
        "ne_zaman": "Aninda web'e git",
        "ornek": "Yeni tool soruldu, hic bilmiyoruz",
    },
    2: {
        "ad": "Guven Dusuk",
        "kosul": "guven_skoru < 0.5",
        "ne_zaman": "Web'den dogrula",
        "ornek": "1 basari, 3 hata → guven=0.25",
    },
    3: {
        "ad": "Gorev Basarisiz",
        "kosul": "2. hatadan sonra web'e git",
        "ne_zaman": "Retry 1 hata + Retry 2 hata → web",
        "ornek": "Komut calismadi, neden?",
    },
    4: {
        "ad": "Gecerlilik Suresi Doldu",
        "kosul": "gecerlilik_tarihi < bugun",
        "ne_zaman": "Arka planda web'den tazele",
        "ornek": "6 ay once ogrendik, tool guncellenmis olabilir",
    },
    5: {
        "ad": "Celiski",
        "kosul": "Video/kullanici hafizadakinden farkli sey soyledi",
        "ne_zaman": "Web'den hakem karar al",
        "ornek": "Eski bilgi ile yeni bilgi uyusmuyor",
    },
}

ONCELIK_SIRASI = [1, 3, 2, 4, 5]
# 1. Hafiza bos → aninda web
# 2. Gorev basarisiz (2. hata) → web
# 3. Guven < 0.5 → web
# 4. Gecerlilik gecmis → arka planda web
# 5. Celiski → web


def tetikleyici_kontrol(tetik_id: int, **kwargs) -> bool:
    """Belirtilen tetikleyicinin sartini kontrol et."""
    if tetik_id == 1:
        # Hafiza Boş: once_hafiza.ara() boş döndü mü?
        return kwargs.get("hafiza_bos", False)

    elif tetik_id == 2:
        # Güven Düşük: guven_skoru < 0.5
        return kwargs.get("guven_skoru", 1.0) < 0.5

    elif tetik_id == 3:
        # Görev Başarısız: 2. hatadan sonra
        return kwargs.get("basarisiz_deneme_sayisi", 0) >= 2

    elif tetik_id == 4:
        # Geçerlilik Süresi Doldu
        gecerlilik = kwargs.get("gecerlilik_tarihi")
        if gecerlilik:
            return str(gecerlilik) < str(date.today())
        return False

    elif tetik_id == 5:
        # Çelişki: iki farklı bilgi çakışıyor
        return kwargs.get("celiski_var", False)

    return False


def hangi_tetikleyici(
    hafiza_bos: bool = False,
    guven_skoru: float = 1.0,
    basarisiz_deneme_sayisi: int = 0,
    gecerlilik_tarihi: str | None = None,
    celiski_var: bool = False,
) -> tuple[int | None, dict]:
    """
    Hangi tetikleyicinin ateşlendiğini bul.

    Returns:
        (tetikleyici_id, tetikleyici_bilgisi) veya (None, {})
    """
    kwargs = {
        "hafiza_bos": hafiza_bos,
        "guven_skoru": guven_skoru,
        "basarisiz_deneme_sayisi": basarisiz_deneme_sayisi,
        "gecerlilik_tarihi": gecerlilik_tarihi,
        "celiski_var": celiski_var,
    }

    for tid in ONCELIK_SIRASI:
        if tetikleyici_kontrol(tid, **kwargs):
            return tid, TETIKLEYICI_TANIMLARI[tid]

    return None, {}


# ── Puanlama ──────────────────────────────────────────────────────────────

PUAN_KRITERLERI = {
    "hiz": {"agirlik": 0.2, "aciklama": "Kac saniyede tamamlandi?"},
    "basari": {"agirlik": 0.3, "aciklama": "Hata verdi mi?"},
    "cikti": {"agirlik": 0.2, "aciklama": "Cikti dogru mu?"},
    "guvenlik": {"agirlik": 0.15, "aciklama": "Guvenli mi?"},
    "kaynak": {"agirlik": 0.15, "aciklama": "Kaynagin guvenilirligi?"},
}


def puanla(
    yontem_adi: str,
    hiz_sn: float,
    basari: bool,
    cikti_dogru: bool,
    guvenlik: float,
    kaynak_guven: float,
) -> TestSonucu:
    """Bir yöntemi puanla ve TestSonucu döndür."""
    return TestSonucu(
        yontem_adi=yontem_adi,
        hiz_sn=hiz_sn,
        basari=basari,
        cikti_dogru=cikti_dogru,
        guvenlik=guvenlik,
        kaynak_guven=kaynak_guven,
    )


# ── Karar ─────────────────────────────────────────────────────────────────

@dataclass
class KararSonucu:
    kazanan: str
    kaybeden: str
    fark: float
    gerekce: str
    eski_korundu: bool


def karar_ver(eski: TestSonucu, yeni: TestSonucu) -> KararSonucu:
    """İki yöntemi karşılaştır ve hangisinin kazandığına karar ver."""
    eski_puan = eski.puan()
    yeni_puan = yeni.puan()
    fark = abs(eski_puan - yeni_puan)

    # Yeni başarısız → eski korunur
    if not yeni.basari or not yeni.cikti_dogru:
        return KararSonucu(
            kazanan=eski.yontem_adi,
            kaybeden=yeni.yontem_adi,
            fark=fark,
            gerekce=f"Yeni yontem basarisiz (basari={yeni.basari}, cikti={yeni.cikti_dogru}). Eski korunur.",
            eski_korundu=True,
        )

    # Eski başarısız, yeni başarılı → yeniye geç
    if (not eski.basari or not eski.cikti_dogru) and (yeni.basari and yeni.cikti_dogru):
        return KararSonucu(
            kazanan=yeni.yontem_adi,
            kaybeden=eski.yontem_adi,
            fark=fark,
            gerekce=f"Eski basarisiz, yeni basarili. Yeniye geciliyor.",
            eski_korundu=False,
        )

    # Yeni > Eski + 0.2 fark → yeniye geç
    if yeni_puan > eski_puan + 0.2:
        return KararSonucu(
            kazanan=yeni.yontem_adi,
            kaybeden=eski.yontem_adi,
            fark=fark,
            gerekce=f"Yeni yontem {fark:.2f} puan daha iyi. Yeniye geciliyor.",
            eski_korundu=False,
        )

    # Fark < 0.2 → eski korunur
    if fark < 0.2:
        return KararSonucu(
            kazanan=eski.yontem_adi,
            kaybeden=yeni.yontem_adi,
            fark=fark,
            gerekce=f"Fark {fark:.2f} < 0.2. Eski korunur (stable).",
            eski_korundu=True,
        )

    # Yeni daha iyi ama fark < 0.2 değil
    return KararSonucu(
        kazanan=yeni.yontem_adi,
        kaybeden=eski.yontem_adi,
        fark=fark,
        gerekce=f"Yeni yontem {fark:.2f} puan daha iyi. Geciliyor.",
        eski_korundu=False,
    )


# ── 5 Tetikleyici Simülasyonu ─────────────────────────────────────────────

SIMULASYON_SENARYOLARI = [
    {
        "ad": "TETIK 1 — Hafiza Bos",
        "hafiza_bos": True,
        "guven_skoru": 1.0,
        "basarisiz_deneme": 0,
        "gecerlilik": "2027-12-31",
        "celiski": False,
        "beklenen_tetik": 1,
    },
    {
        "ad": "TETIK 2 — Guven Dusuk",
        "hafiza_bos": False,
        "guven_skoru": 0.25,
        "basarisiz_deneme": 0,
        "gecerlilik": "2027-12-31",
        "celiski": False,
        "beklenen_tetik": 2,
    },
    {
        "ad": "TETIK 3 — Gorev Basarisiz",
        "hafiza_bos": False,
        "guven_skoru": 0.9,
        "basarisiz_deneme": 2,
        "gecerlilik": "2027-12-31",
        "celiski": False,
        "beklenen_tetik": 3,
    },
    {
        "ad": "TETIK 4 — Gecerlilik Doldu",
        "hafiza_bos": False,
        "guven_skoru": 0.9,
        "basarisiz_deneme": 0,
        "gecerlilik": "2025-01-01",
        "celiski": False,
        "beklenen_tetik": 4,
    },
    {
        "ad": "TETIK 5 — Celiski",
        "hafiza_bos": False,
        "guven_skoru": 0.9,
        "basarisiz_deneme": 0,
        "gecerlilik": "2027-12-31",
        "celiski": True,
        "beklenen_tetik": 5,
    },
]


def tetikleyici_simulasyonu() -> list[dict]:
    """5 tetikleyiciyi simüle et ve sonuçları döndür."""
    sonuclar = []
    for senaryo in SIMULASYON_SENARYOLARI:
        tid, bilgi = hangi_tetikleyici(
            hafiza_bos=senaryo["hafiza_bos"],
            guven_skoru=senaryo["guven_skoru"],
            basarisiz_deneme_sayisi=senaryo["basarisiz_deneme"],
            gecerlilik_tarihi=senaryo["gecerlilik"],
            celiski_var=senaryo["celiski"],
        )

        beklenen = senaryo["beklenen_tetik"]
        durum = "✅" if tid == beklenen else "❌"

        sonuclar.append({
            "senaryo": senaryo["ad"],
            "durum": durum,
            "ateslenen_tetik": tid,
            "beklenen_tetik": beklenen,
            "tetikleyici_adi": bilgi.get("ad", "YOK"),
            "kosul": bilgi.get("kosul", ""),
        })

    return sonuclar


# ── Tam Döngü ─────────────────────────────────────────────────────────────

def web_test_loop(
    konu: str,
    eski_yontem: Callable[[], TestSonucu],
    yeni_yontem: Callable[[], TestSonucu],
) -> dict[str, Any]:
    """
    WEB → UYGULA → PUANLA → KARAR tam döngüsü.

    Args:
        konu: Test edilen konu (örn. "nmap UDP tarama")
        eski_yontem: Eski yöntemi çalıştırıp TestSonucu döndüren fonksiyon
        yeni_yontem: Yeni yöntemi çalıştırıp TestSonucu döndüren fonksiyon

    Returns:
        {
            "konu": ...,
            "eski_puan": ...,
            "yeni_puan": ...,
            "karar": KararSonucu,
            "puan_tablosu": {...}
        }
    """
    # ADIM 2 — Uygula (sandbox'ta test et)
    eski_sonuc = eski_yontem()
    yeni_sonuc = yeni_yontem()

    # ADIM 3 — Puanla
    eski_puan = eski_sonuc.puan()
    yeni_puan = yeni_sonuc.puan()

    # ADIM 4 — Karar
    karar = karar_ver(eski_sonuc, yeni_sonuc)

    return {
        "konu": konu,
        "eski": {
            "yontem": eski_sonuc.yontem_adi,
            "puan": eski_puan,
            "detay": eski_sonuc,
        },
        "yeni": {
            "yontem": yeni_sonuc.yontem_adi,
            "puan": yeni_puan,
            "detay": yeni_sonuc,
        },
        "karar": {
            "kazanan": karar.kazanan,
            "kaybeden": karar.kaybeden,
            "fark": round(karar.fark, 2),
            "gerekce": karar.gerekce,
            "eski_korundu": karar.eski_korundu,
        },
        "puan_tablosu": {
            "kriterler": PUAN_KRITERLERI,
            "eski_kriter": {
                "hiz": eski_sonuc.hiz_sn,
                "basari": eski_sonuc.basari,
                "cikti": eski_sonuc.cikti_dogru,
                "guvenlik": eski_sonuc.guvenlik,
                "kaynak": eski_sonuc.kaynak_guven,
            },
            "yeni_kriter": {
                "hiz": yeni_sonuc.hiz_sn,
                "basari": yeni_sonuc.basari,
                "cikti": yeni_sonuc.cikti_dogru,
                "guvenlik": yeni_sonuc.guvenlik,
                "kaynak": yeni_sonuc.kaynak_guven,
            },
        },
    }


if __name__ == "__main__":
    # ── TEST: nmap UDP tarama ──────────────────────────────────────────
    print("=" * 65)
    print("TEST: nmap icin en hizli UDP tarama yontemi")
    print("=" * 65)

    # Eski yöntem: nmap -sU -p 1-1000 (tam UDP tarama, yavaş)
    eski_yontem = lambda: TestSonucu(
        yontem_adi="nmap -sU tam UDP tarama",
        hiz_sn=45.0,        # yavaş
        basari=True,
        cikti_dogru=True,
        guvenlik=1.0,       # nmap güvenli
        kaynak_guven=0.9,   # resmi doc
    )

    # Yeni yöntem (web'den bulunan): nmap -sU --top-ports 100 (hızlı)
    yeni_yontem = lambda: TestSonucu(
        yontem_adi="nmap -sU --top-ports 100",
        hiz_sn=5.0,          # çok hızlı
        basari=True,
        cikti_dogru=True,    # ilk 100 port yeterli
        guvenlik=1.0,
        kaynak_guven=0.7,    # stackoverflow
    )

    sonuc = web_test_loop(
        konu="nmap UDP tarama",
        eski_yontem=eski_yontem,
        yeni_yontem=yeni_yontem,
    )

    print(f"\nKonu: {sonuc['konu']}")
    print(f"\n--- Puan Tablosu ---")
    print(f"{'Kriter':<12} {'Eski':<8} {'Yeni':<8}")
    print("-" * 30)
    for kriter in PUAN_KRITERLERI:
        eski_val = sonuc['puan_tablosu']['eski_kriter'][kriter]
        yeni_val = sonuc['puan_tablosu']['yeni_kriter'][kriter]
        print(f"{kriter:<12} {str(eski_val):<8} {str(yeni_val):<8}")

    print(f"\nEski puan: {sonuc['eski']['puan']:.4f}")
    print(f"Yeni puan: {sonuc['yeni']['puan']:.4f}")
    print(f"\nKARAR: {sonuc['karar']['kazanan']}")
    print(f"Gerekce: {sonuc['karar']['gerekce']}")
    print(f"Fark: {sonuc['karar']['fark']}")
    print(f"Eski korundu: {sonuc['karar']['eski_korundu']}")

    # ── 5 Tetikleyici Test ─────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("5 TETIKLEYICI TESTI")
    print("=" * 65)
    tetik_sonuclari = tetikleyici_simulasyonu()
    for t in tetik_sonuclari:
        print(f"{t['durum']} {t['senaryo']}")
        print(f"   Ateslenen: #{t['ateslenen_tetik']} ({t['tetikleyici_adi']})")
        print(f"   Kosul: {t['kosul']}")

    # ── Puanlama testi: fark < 0.2 durumu ─────────────────────────────
    print("\n" + "=" * 65)
    print("TEST: Fark < 0.2 → Eski korunur")
    print("=" * 65)
    eski2 = TestSonucu("nmap -sU -p 1-100", 10.0, True, True, 1.0, 0.9)
    yeni2 = TestSonucu("nmap -sU --top-ports 50", 8.0, True, True, 1.0, 0.7)
    karar2 = karar_ver(eski2, yeni2)
    print(f"Eski: {eski2.puan():.4f}, Yeni: {yeni2.puan():.4f}")
    print(f"Karar: {karar2.kazanan}")
    print(f"Gerekce: {karar2.gerekce}")
