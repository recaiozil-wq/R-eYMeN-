# -*- coding: utf-8 -*-
"""
hata_analiz.py — Hata Sonrası Analiz ve Otomatik Düzeltme.

Görev hata verdiğinde conversation_loop.py tarafından çağrılır:
  1. Hata mesajını parse et
  2. Benzer hata geçmişini hafızada ara
  3. Çözüm önerisi üret
  4. Otomatik düzeltme dene (seçilen hata tipleri için)

Akış:
  Görev → HATA → analiz_et(hata, hedef)
    ├─ Hafızada benzer hata var mı?
    │  ├─ EVET → önceki çözümü uygula
    │  └─ HAYIR → çözüm önerisi üret
    ├─ Otomatik düzeltilebilir mi?
    │  ├─ EVET → düzelt ve tekrar dene
    │  └─ HAYIR → raporla
    └─ Kaydet (yeni hata + çözüm)
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
logger = logging.getLogger(__name__)

log = logging.getLogger(__name__)

# ── Sabitler ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.resolve()  # reymen/hafiza/
PROJE = ROOT.parent.parent              # hermes_projesi/

# Kaydedilmiş hata çözümleri (HATA_COZUM_DB)
HATA_DB_YOLU = PROJE / ".ReYMeN" / "hata_cozumleri.md"
SKILLS_DIR = PROJE / ".ReYMeN" / "skills"


# ══════════════════════════════════════════════════════════════════════════
# HATA SINIFLANDIRMA
# ══════════════════════════════════════════════════════════════════════════

class HataSinifi:
    """Hata türü ve düzeltme stratejisi."""
    MODUL_EKSIK = "modul_eksik"           # ImportError
    DOSYA_EKSIK = "dosya_eksik"           # FileNotFoundError
    IZIN_REDDI = "izin_reddi"             # PermissionError
    BAGLANTI_HATASI = "baglanti_hatasi"   # ConnectionError / timeout
    API_HATASI = "api_hatasi"             # API döndü hata
    SENTAKS_HATASI = "sentaks_hatasi"     # SyntaxError / lint
    TIP_HATASI = "tip_hatasi"             # TypeError
    DIGER = "diger"                       # Sınıflandırılamayan


HATA_SINIFLARI = {
    "modul_eksik": {
        "desen": r"(ImportError|ModuleNotFoundError|No module named)",
        "cozum": "pip install veya import kontrol",
        "otomatik": True,
    },
    "dosya_eksik": {
        "desen": r"(FileNotFoundError|No such file|dosya bulunamadı)",
        "cozum": "Dosya yolunu kontrol et, oluştur",
        "otomatik": True,
    },
    "izin_reddi": {
        "desen": r"(PermissionError|Access denied|EACCES)",
        "cozum": "Yetki kontrolü, admin modu",
        "otomatik": False,
    },
    "baglanti_hatasi": {
        "desen": r"(ConnectionError|Connection refused|timeout|TIMEOUT|network unreachable)",
        "cozum": "Bağlantı kontrolü, yeniden dene",
        "otomatik": True,
    },
    "api_hatasi": {
        "desen": r"(HTTPError|4\d{2}|5\d{2}|API hatası|rate limit)",
        "cozum": "API anahtarı / limit / endpoint kontrol",
        "otomatik": False,
    },
    "sentaks_hatasi": {
        "desen": r"(SyntaxError|invalid syntax|syntax error|lint hatası)",
        "cozum": "Kod düzeltme",
        "otomatik": True,
    },
    "tip_hatasi": {
        "desen": r"(TypeError|expected.*got|unsupported operand)",
        "cozum": "Tip dönüşümü, parametre kontrolü",
        "otomatik": True,
    },
}


def hata_siniflandir(hata_mesaji: str) -> Tuple[str, dict]:
    """Hata mesajını parse et ve sınıfını belirle.

    Args:
        hata_mesaji: Ham hata metni veya traceback.

    Returns:
        (sinif_adi, sinif_bilgisi): Örn. ("modul_eksik", {...})
    """
    if not hata_mesaji:
        return ("diger", HATA_SINIFLARI["diger"])

    for sinif_adi, sinif_bilgi in HATA_SINIFLARI.items():
        desen = sinif_bilgi.get("desen", "")
        if desen and re.search(desen, hata_mesaji, re.IGNORECASE):
            return (sinif_adi, sinif_bilgi)

    return ("diger", {"cozum": "Manuel analiz gerekli", "otomatik": False})


# ══════════════════════════════════════════════════════════════════════════
# HAFIZADA HATA ÇÖZÜMÜ ARA
# ══════════════════════════════════════════════════════════════════════════

def hata_cozumu_ara(hata_sinifi: str, hedef: str) -> Optional[str]:
    """Daha önce kaydedilmiş hata çözümlerini hafızada ara.

    Args:
        hata_sinifi: Hata sınıfı (örn. "modul_eksik")
        hedef: Görevin hedef metni

    Returns:
        str: Çözüm metni (varsa), None: bulunamadı
    """
    # 1. HATA_COZUM_DB'ye bak
    try:
        if HATA_DB_YOLU.exists():
            icerik = HATA_DB_YOLU.read_text(encoding="utf-8", errors="replace")

            # Hata sınıfına göre bölüme bak
            bolum_ici = icerik.find(f"## {hata_sinifi}")
            if bolum_ici != -1:
                bolum_sonu = icerik.find("\n## ", bolum_ici + 3)
                if bolum_sonu == -1:
                    bolum_sonu = len(icerik)
                bolum = icerik[bolum_ici:bolum_sonu]

                # Hedefle ilgili satır var mı?
                kelimeler = [k.lower() for k in hedef.split() if len(k) > 3]
                for satir in bolum.split("\n"):
                    satir_lower = satir.lower()
                    if sum(1 for k in kelimeler if k in satir_lower) >= len(kelimeler) // 2:
                        return satir.strip()

    except Exception as e:
        log.warning("Hata çözümü aranirken hata: %s", e)

    return None


# ══════════════════════════════════════════════════════════════════════════
# ÇÖZÜM KAYDET
# ══════════════════════════════════════════════════════════════════════════

def hata_cozumu_kaydet(hata_sinifi: str, hata_mesaji: str, cozum: str, hedef: str):
    """Bulunan/kullanılan hata çözümünü HATA_COZUM_DB'ye kaydet.

    Args:
        hata_sinifi: Hata sınıfı
        hata_mesaji: Orijinal hata mesajı
        cozum: Uygulanan çözüm
        hedef: Görevin hedefi
    """
    try:
        from datetime import datetime

        zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
        yeni_kayit = (
            f"- **{hedef[:80]}** ({zaman})\n"
            f"  - Hata: `{hata_mesaji[:200]}`\n"
            f"  - Cozum: {cozum[:200]}\n"
        )

        if HATA_DB_YOLU.exists():
            mevcut = HATA_DB_YOLU.read_text(encoding="utf-8", errors="replace")

            # Bölüm başlığı var mı?
            bolum_basligi = f"## {hata_sinifi}"
            if bolum_basligi in mevcut:
                mevcut = mevcut.replace(bolum_basligi, f"{bolum_basligi}\n{yeni_kayit}")
            else:
                mevcut += f"\n\n{bolum_basligi}\n{yeni_kayit}"

            HATA_DB_YOLU.write_text(mevcut, encoding="utf-8")
        else:
            HATA_DB_YOLU.parent.mkdir(parents=True, exist_ok=True)
            icerik = (
                f"# Hata Çözümleri — ReYMeN\n\n"
                f"_Otomatik kaydedilen hata-çözüm eşleşmeleri._\n\n"
                f"## {hata_sinifi}\n{yeni_kayit}\n"
            )
            HATA_DB_YOLU.write_text(icerik, encoding="utf-8")

        log.info("Hata çözümü kaydedildi: %s → %s", hata_sinifi, cozum[:60])

    except Exception as e:
        log.warning("Hata çözümü kaydedilirken hata: %s", e)


# ══════════════════════════════════════════════════════════════════════════
# ANA ANALİZ FONKSİYONU
# ══════════════════════════════════════════════════════════════════════════

def hata_analiz_et(hata_mesaji: str, hedef: str) -> dict:
    """Hata analizini yap, çözüm önerisi üret.

    Args:
        hata_mesaji: Hata mesajı (veya traceback)
        hedef: Görevin hedef metni

    Returns:
        dict: {
            "sinif": "modul_eksik",
            "otomatik": True/False,
            "cozum_onerisi": "...",
            "hafizada_var": True/False,
            "hafiza_cozumu": "...",
            "kaydedildi": True/False,
        }
    """
    # 1. Sınıflandır
    sinif_adi, sinif_bilgi = hata_siniflandir(hata_mesaji)

    # 2. Hafızada çözüm ara
    hafiza_cozum = hata_cozumu_ara(sinif_adi, hedef)

    # 3. Çözüm önerisi oluştur
    if hafiza_cozum:
        cozum_onerisi = hafiza_cozum
    else:
        cozum_onerisi = sinif_bilgi.get("cozum", "Bilinmeyen hata, manuel analiz gerekli")

    # 4. Kaydet (yeni hata olarak)
    if not hafiza_cozum:
        hata_cozumu_kaydet(sinif_adi, hata_mesaji, cozum_onerisi, hedef)

    return {
        "sinif": sinif_adi,
        "otomatik": sinif_bilgi.get("otomatik", False),
        "cozum_onerisi": cozum_onerisi,
        "hafizada_var": hafiza_cozum is not None,
        "hafiza_cozumu": hafiza_cozum,
        "kaydedildi": not hafiza_cozum,  # yeni hata = kaydedildi
    }
