# -*- coding: utf-8 -*-
"""
memory_compaction.py — MEMORY.md / USER.md 50K Compaction Sistemi.

ReYMeN'de Hermes'teki MEMORY.md/USER.md 50K compaction'inin benzerini uygular.
Hafiza budama (hafiza_budama.py) TTL bazli calisirken bu modul KARAKTER LIMITI
bazli compaction yapar — dosya 50.000 karaktere yaklasinca otomatik budar.

Ne yapar:
  1. MEMORY.md ve USER.md'yi tara (reymen/hafiza/ altinda)
  2. 50.000 karakter limitine yaklasinca (>%80 = 40K) otomatik compaction
  3. En eski/dusuk oncelikli entry'leri arsivle (reymen/hafiza/arsiv/)
  4. Onem sirasina gore budama: dusuk oncelikli entry'leri sil
  5. @lru_cache temizleme (cache_tazele())
  6. Hafif kontrol (konusma sonrasi hizli check)

Kullanim:
    from reymen.cereyan.memory_compaction import memory_compaction_check
    rapor = memory_compaction_check()           # Hafif kontrol
    rapor = memory_compaction_check(zorla=True) # Zorla compaction

    from reymen.cereyan.memory_compaction import cache_tazele
    cache_tazele()  # prompt_assembly lru_cache'lerini temizle
"""

import functools
import json
import logging
import os
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Sabitler ──────────────────────────────────────────────────────────────

# Karakter limitleri (memory_manager.py ile uyumlu)
MEMORY_LIMIT_CHARS = 50000
USER_LIMIT_CHARS = 50000

# Compaction esikleri
COMPACTION_ESIK_YUZDE = 80       # %80 dolulukta otomatik compaction baslat
COMPACTION_HEDEF_YUZDE = 60     # Compaction sonrasi hedef %60 doluluk
ARCIV_MAX_ENTRY = 200            # Arsiv dosyasi basina max entry

# Onem siralamasi (yuksek = korunur)
ONEM_ETIKETLERI = {
    "ZORUNLU KURAL": 100,        # Kalici kurallar — en yuksek onem
    "KALICI KURAL": 95,
    "KURAL": 90,
    "ZORUNLU": 85,
    "HICBIR ZAMAN": 85,
    "ASLA": 85,
    "KESINLIKLE": 85,
    "ONCELIKLI": 80,
    "ONEMLI": 80,
    "CRITICAL": 80,
    "IMPORTANT": 75,
    "KALICI": 75,
    "OGRENILEN": 70,
    "OGRENME": 65,
    "TERCIH": 60,
    "PREFERENCE": 60,
    "BILGI": 50,
    "NOT": 40,
    "HATIRLATMA": 30,
    "GOREV": 20,
    "TASK": 20,
    "LOG": 10,
}

# Varsayilan onem puani (etiketsiz entry'ler icin)
VARSAYILAN_ONEM = 30

# Entry yas sinirlari (gun)
GUNLUK_ESKI_ESIK = 14    # 14 gun + onceki seviye
HAFTALIK_ESKI_ESIK = 90  # 90 gun = cok eski

# Yollar
_PROJE_KOKU = Path(__file__).resolve().parent.parent.parent  # ReYMeN-Ajan/
_HAFIZA_DIZINI = _PROJE_KOKU / "reymen" / "hafiza"
_ARSIV_DIZINI = _HAFIZA_DIZINI / "arsiv"
_MEMORY_YOLU = _HAFIZA_DIZINI / "MEMORY.md"
_USER_YOLU = _HAFIZA_DIZINI / "USER.md"

# ── Yardimci Fonksiyonlar ────────────────────────────────────────────────

def _entryleri_parcala(icerik: str) -> List[Dict[str, Any]]:
    """MEMORY.md/USER.md icerigini entry'lere ayir ve metadata cikar.

    Format: Entry'ler '§' isareti ile ayrilmistir.

    Returns:
        [{"metin": str, "satir_no": int, "karakter": int,
          "onem_puani": int, "tarih": str, "etiket": str}, ...]
    """
    if not icerik or not icerik.strip():
        return []

    entryler = []
    bloklar = icerik.strip().split("§")

    for i, blok in enumerate(bloklar):
        metin = blok.strip()
        if not metin:
            continue

        # Entry analizi
        onem_puani = _onem_puanla(metin)
        etiket = _etiket_bul(metin)
        tarih = _tarih_bul(metin)

        entryler.append({
            "metin": metin,
            "sira": i,
            "karakter": len(metin),
            "onem_puani": onem_puani,
            "tarih": tarih,
            "etiket": etiket,
            "eski_mi": _eski_mi(tarih) if tarih else False,
        })

    return entryler


def _onem_puanla(metin: str) -> int:
    """Entry'nin onem puanini hesapla (0-100)."""
    # Ilk satirdaki/basligindaki etikete bak
    ilk_satir = metin.split("\n")[0].strip().upper()

    # En yuksek eslesen etiketi bul
    en_yuksek = VARSAYILAN_ONEM
    for etiket, puan in ONEM_ETIKETLERI.items():
        if etiket in ilk_satir or etiket in metin.upper()[:200]:
            if puan > en_yuksek:
                en_yuksek = puan

    # Uzunluk bonusu (cok kisa entry'ler daha az onemli)
    if len(metin) < 30:
        en_yuksek = max(0, en_yuksek - 20)
    elif len(metin) > 500:
        en_yuksek = min(100, en_yuksek + 5)  # Detayli entry'ler daha degerli

    # Gorev/log entry'leri dusuk onem
    gorev_isaretleri = [
        "fix:", "duzeltildi", "tamamlandi", "gorev bitti",
        "eklendi", "kaldirildi", "guncellendi", "test gecti",
        "gorev_id", "task_id", "commit",
    ]
    if any(isaret in metin.lower() for isaret in gorev_isaretleri):
        en_yuksek = min(en_yuksek, 20)

    return en_yuksek


def _etiket_bul(metin: str) -> str:
    """Entry'nin etiketini bul."""
    ilk_satir = metin.split("\n")[0].strip().upper()
    for etiket in sorted(ONEM_ETIKETLERI.keys(), key=len, reverse=True):
        if etiket in ilk_satir[:100]:
            return etiket
    # Ilk 3 kelimeye bak
    kelimeler = ilk_satir.split()[:3]
    for k in kelimeler:
        k_clean = k.strip(":-").upper()
        if k_clean in ONEM_ETIKETLERI:
            return k_clean
    return "GENEL"


def _tarih_bul(metin: str) -> Optional[str]:
    """Entry icinde bir tarih varsa bul (YYYY-MM-DD veya benzeri)."""
    # YYYY-MM-DD
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', metin)
    if m:
        return m.group(0)
    # DD.MM.YYYY
    m = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', metin)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    # DD/MM/YYYY
    m = re.search(r'(\d{2})/(\d{2})/(\d{4})', metin)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return None


def _eski_mi(tarih_str: str) -> bool:
    """Tarih string'ine bakarak entry'nin eski olup olmadigini kontrol et."""
    try:
        tarih = datetime.strptime(tarih_str, "%Y-%m-%d")
        fark = (datetime.now() - tarih).days
        return fark > GUNLUK_ESKI_ESIK
    except (ValueError, TypeError):
        return False


def _dosya_boyut_kontrol(dosya_yolu: Path, limit: int) -> Tuple[int, float]:
    """Dosyanin karakter sayisini ve doluluk yuzdesini dondur."""
    if not dosya_yolu.exists():
        return 0, 0.0
    try:
        icerik = dosya_yolu.read_text(encoding="utf-8")
        boyut = len(icerik)
        yuzde = (boyut / limit) * 100
        return boyut, yuzde
    except Exception:
        return 0, 0.0


# ── Ana Compaction Fonksiyonlari ─────────────────────────────────────────

def _compaction_yap(icerik: str, dosya_adi: str, limit: int,
                    zorla: bool = False) -> Tuple[str, Dict[str, Any]]:
    """Bir memory dosyasinda compaction yap.

    Args:
        icerik: Dosya icerigi
        dosya_adi: Dosya adi (log icin)
        limit: Karakter limiti
        zorla: True = esigi beklemeden compaction yap

    Returns:
        (yeni_icerik, rapor)
    """
    rapor = {
        "dosya": dosya_adi,
        "onceki_karakter": len(icerik),
        "sonraki_karakter": 0,
        "onceki_entry": 0,
        "sonraki_entry": 0,
        "silinen_entry": 0,
        "arsivlenen_entry": 0,
        "budanan_karakter": 0,
        "compaction_yapildi": False,
    }

    if not icerik or not icerik.strip():
        rapor["sonraki_karakter"] = 0
        return icerik, rapor

    # Entry'lere ayir
    entryler = _entryleri_parcala(icerik)
    rapor["onceki_entry"] = len(entryler)

    # Doluluk kontrolu
    boyut = len(icerik)
    yuzde = (boyut / limit) * 100
    hedef_boyut = int(limit * COMPACTION_HEDEF_YUZDE / 100)

    if not zorla and yuzde < COMPACTION_ESIK_YUZDE:
        # Compaction gerekmiyor
        rapor["sonraki_karakter"] = boyut
        rapor["sonraki_entry"] = len(entryler)
        return icerik, rapor

    # --- COMPACTION BASLA ---
    rapor["compaction_yapildi"] = True
    logger.info("[Compaction] %s: %d/%d karakter (%d%%) — compaction basliyor",
                dosya_adi, boyut, limit, int(yuzde))

    # 1. Entry'leri onem puanina ve yasina gore sirala
    #    (dusuk onemli + eski entry'ler once silinir)
    sirali = sorted(
        entryler,
        key=lambda e: (e["onem_puani"], 0 if e["eski_mi"] else 1)
    )

    # 2. Arsivlenecek ve silinecek entry'leri belirle
    korunanlar = []
    arsivlenecekler = []
    silinecekler = []

    # Yeterli alan kalana kadar dusuk onemli entry'leri cikar
    simdiki_boyut = boyut

    for e in sorted(entryler, key=lambda x: (x["onem_puani"], x["sira"])):
        if simdiki_boyut <= hedef_boyut:
            break

        # ZORUNLU KURAL ve yuksek onemli (>=80) entry'leri koru
        if e["onem_puani"] >= 80:
            continue

        # Cok eski ve dusuk onemli -> sil
        if e["eski_mi"] and e["onem_puani"] < 40:
            silinecekler.append(e)
            simdiki_boyut -= e["karakter"]
            continue

        # Orta onemli veya eski ama kayda deger -> arsivle
        if e["onem_puani"] < 60 or e["eski_mi"]:
            arsivlenecekler.append(e)
            simdiki_boyut -= e["karakter"]
            continue

    # 3. Kalanlari koru
    korunan_idler = {e["sira"] for e in entryler} - \
                    {e["sira"] for e in silinecekler} - \
                    {e["sira"] for e in arsivlenecekler}
    korunanlar = [e for e in entryler if e["sira"] in korunan_idler]

    # 4. Silinenleri raporla
    for e in silinecekler:
        logger.debug("[Compaction] SILINDI [onem=%d]: %.60s",
                     e["onem_puani"], e["metin"][:60])

    # 5. Arsivle
    if arsivlenecekler:
        _arsive_kaydet(dosya_adi, arsivlenecekler)

    # 6. Yeni icerik olustur (onem sirasina gore sirala)
    #    Korunanlari orijinal sirada tut
    korunanlar.sort(key=lambda e: e["sira"])
    yeni_entry_metinleri = [e["metin"] for e in korunanlar]
    yeni_icerik = ("\n§\n".join(yeni_entry_metinleri)).strip()
    if yeni_icerik:
        yeni_icerik += "\n"

    # Final rapor
    rapor["sonraki_karakter"] = len(yeni_icerik)
    rapor["sonraki_entry"] = len(korunanlar)
    rapor["silinen_entry"] = len(silinecekler)
    rapor["arsivlenen_entry"] = len(arsivlenecekler)
    rapor["budanan_karakter"] = boyut - len(yeni_icerik)

    logger.info("[Compaction] %s: %d entry -> %d entry (%d silindi, %d arsivlendi, %d karakter budandi)",
                dosya_adi,
                rapor["onceki_entry"], rapor["sonraki_entry"],
                rapor["silinen_entry"], rapor["arsivlenen_entry"],
                rapor["budanan_karakter"])

    return yeni_icerik, rapor


def _arsive_kaydet(dosya_adi: str, entryler: List[Dict[str, Any]]) -> bool:
    """Entry'leri arsiv dosyasina kaydet.

    Arsiv formati: arsiv/<dosya_adi>_<tarih>.md
    """
    try:
        _ARSIV_DIZINI.mkdir(parents=True, exist_ok=True)

        # Arsiv dosyasi adi: MEMORY_2026-07-02_001.md
        bugun = datetime.now().strftime("%Y-%m-%d")
        # Mevcut arsiv dosyalarini say
        mevcut = list(_ARSIV_DIZINI.glob(f"{dosya_adi.replace('.md', '')}_{bugun}_*.md"))
        sira = len(mevcut) + 1
        arsiv_yolu = _ARSIV_DIZINI / f"{dosya_adi.replace('.md', '')}_{bugun}_{sira:03d}.md"

        # Arsiv icerigi
        arsiv_satirlar = [
            f"# Arsiv: {dosya_adi} — {bugun}",
            f"",
            f"> Bu dosya {bugun} tarihinde otomatik compaction ile arsivlenmistir.",
            f"> Toplam {len(entryler)} entry, {sum(e['karakter'] for e in entryler)} karakter.",
            f"",
        ]

        for e in entryler:
            arsiv_satirlar.append(f"## Entry #{e['sira']+1} (onem={e['onem_puani']}, etiket={e['etiket']})")
            if e["tarih"]:
                arsiv_satirlar.append(f"**Tarih:** {e['tarih']}")
            if e["eski_mi"]:
                arsiv_satirlar.append(f"**Durum:** Eski")
            arsiv_satirlar.append("")
            arsiv_satirlar.append(e["metin"])
            arsiv_satirlar.append("")
            arsiv_satirlar.append("---")
            arsiv_satirlar.append("")

        _ARSIV_DIZINI.mkdir(parents=True, exist_ok=True)
        arsiv_yolu.write_text("\n".join(arsiv_satirlar), encoding="utf-8")

        logger.info("[Compaction] Arsivlendi: %s (%d entry)", arsiv_yolu.name, len(entryler))
        return True

    except Exception as e:
        logger.error("[Compaction] Arsivleme hatasi: %s", e)
        return False


# ── Cache Temizleme ──────────────────────────────────────────────────────

def cache_tazele() -> Dict[str, Any]:
    """@lru_cache ile cache'lenmis fonksiyonlari temizle.

    prompt_assembly.py'deki _dosya_oku() lru_cache'ini temizler.
    Boylece SOUL.md, USER.md, config.yaml en guncel halleriyle okunur.

    Returns:
        {"temizlenen": int, "moduller": [str, ...]}
    """
    temizlenen = 0
    moduller = []

    # 1. prompt_assembly._dosya_oku
    try:
        from reymen.cereyan import prompt_assembly
        prompt_assembly._dosya_oku.cache_clear()
        temizlenen += 1
        moduller.append("prompt_assembly._dosya_oku")
        logger.debug("[Cache] prompt_assembly._dosya_oku cache temizlendi")
    except (ImportError, AttributeError) as e:
        logger.debug("[Cache] prompt_assembly cache temizlenemedi: %s", e)

    # 2. prompt_assembly'deki diger lru_cache'ler
    try:
        for attr_name in dir(prompt_assembly):
            attr = getattr(prompt_assembly, attr_name)
            if isinstance(attr, functools._lru_cache_wrapper):
                attr.cache_clear()
                temizlenen += 1
                moduller.append(f"prompt_assembly.{attr_name}")
    except (ImportError, NameError):
        pass

    # 3. Kendi cache'lerimiz (ileride eklenirse)
    # (placeholder)

    if temizlenen > 0:
        logger.info("[Cache] %d cache fonksiyon temizlendi: %s",
                    temizlenen, ", ".join(moduller))

    return {"temizlenen": temizlenen, "moduller": moduller}


# ── Ana Compaction Fonksiyonu ────────────────────────────────────────────

def memory_compaction_check(zorla: bool = False) -> Dict[str, Any]:
    """MEMORY.md ve USER.md'de compaction kontrolu yap.

    Args:
        zorla: True ise esigi beklemeden compaction yap

    Returns:
        Kapsamli compaction raporu
    """
    baslama = time.time()
    rapor = {
        "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "zorla": zorla,
        "dosyalar": {},
        "cache": None,
        "sure_sn": 0,
        "toplam_budanan_karakter": 0,
        "toplam_silinen_entry": 0,
        "toplam_arsivlenen_entry": 0,
        "durum": "tamam",
    }

    logger.info("[Compaction] ===== BASLADI (zorla=%s) =====", zorla)

    # Dosyalari kontrol et
    for dosya_yolu, dosya_adi, limit in [
        (_MEMORY_YOLU, "MEMORY.md", MEMORY_LIMIT_CHARS),
        (_USER_YOLU, "USER.md", USER_LIMIT_CHARS),
    ]:
        if not dosya_yolu.exists():
            rapor["dosyalar"][dosya_adi] = {
                "durum": "yok",
                "mesaj": f"Dosya bulunamadi: {dosya_yolu}"
            }
            logger.debug("[Compaction] %s bulunamadi: %s", dosya_adi, dosya_yolu)
            continue

        try:
            icerik = dosya_yolu.read_text(encoding="utf-8")
            yeni_icerik, dosya_raporu = _compaction_yap(icerik, dosya_adi, limit, zorla)

            # Degisiklik varsa yaz
            if dosya_raporu["compaction_yapildi"] and yeni_icerik != icerik:
                dosya_yolu.write_text(yeni_icerik, encoding="utf-8")
                logger.info("[Compaction] %s guncellendi: %d -> %d karakter",
                            dosya_adi, dosya_raporu["onceki_karakter"],
                            dosya_raporu["sonraki_karakter"])

            rapor["dosyalar"][dosya_adi] = dosya_raporu
            rapor["toplam_budanan_karakter"] += dosya_raporu.get("budanan_karakter", 0)
            rapor["toplam_silinen_entry"] += dosya_raporu.get("silinen_entry", 0)
            rapor["toplam_arsivlenen_entry"] += dosya_raporu.get("arsivlenen_entry", 0)

        except Exception as e:
            rapor["dosyalar"][dosya_adi] = {
                "durum": "hata",
                "hata": str(e),
            }
            logger.error("[Compaction] %s hatasi: %s", dosya_adi, e)

    # Cache temizle (compaction yapildiysa)
    if rapor["toplam_budanan_karakter"] > 0 or rapor["toplam_silinen_entry"] > 0:
        rapor["cache"] = cache_tazele()

    rapor["sure_sn"] = round(time.time() - baslama, 2)

    logger.info("[Compaction] ===== TAMAMLANDI: %d karakter budandi, "
                "%d entry silindi, %d entry arsivlendi (%.2fs) =====",
                rapor["toplam_budanan_karakter"],
                rapor["toplam_silinen_entry"],
                rapor["toplam_arsivlenen_entry"],
                rapor["sure_sn"])

    return rapor


def hafif_compaction_kontrol() -> Dict[str, Any]:
    """Konusma sonrasi hafif kontrol — hizli calisir, sadece gerekirse compaction yapar.

    Sadece dosya boyutuna bakar, %80 esigini gecerse compaction baslatir.
    Gecmezse bos rapor dondurur.
    """
    rapor = {"kontrol_edildi": True, "islem_yapildi": False, "detay": {}}

    for dosya_yolu, dosya_adi, limit in [
        (_MEMORY_YOLU, "MEMORY.md", MEMORY_LIMIT_CHARS),
        (_USER_YOLU, "USER.md", USER_LIMIT_CHARS),
    ]:
        if not dosya_yolu.exists():
            continue

        boyut, yuzde = _dosya_boyut_kontrol(dosya_yolu, limit)
        rapor["detay"][dosya_adi] = {
            "karakter": boyut,
            "limit": limit,
            "doluluk": round(yuzde, 1),
        }

        if yuzde >= COMPACTION_ESIK_YUZDE:
            rapor["islem_yapildi"] = True
            logger.info("[Compaction] Hafif kontrol: %s %d%% dolu — compaction basliyor",
                        dosya_adi, int(yuzde))

    if rapor["islem_yapildi"]:
        comp_rapor = memory_compaction_check(zorla=True)
        rapor["compaction"] = comp_rapor

    return rapor


# ── Cron Gorevi ──────────────────────────────────────────────────────────

def cron_compaction_gorevi() -> Dict[str, Any]:
    """Cron job olarak cagrilmak uzere compaction gorevi.

    Gunde 1 kez calistirilir. Zorla compaction yapar,
    cache'i temizler, rapor dondurur.

    Kullanimi (cron_scheduler'a ekleme):
        scheduler.ekle(
            "memory_compaction",
            "0 5 * * *",  # Her gun 05:00
            cron_compaction_gorevi,
            aciklama="MEMORY.md/USER.md 50K compaction — gunluk bakim",
        )

    veya jobs.json'a kaydetme:
        {
            "memory_compaction_daily": {
                "komut": "python -c \"from reymen.cereyan.memory_compaction import cron_compaction_gorevi; cron_compaction_gorevi()\"",
                "zaman": "0 5 * * *",
                "aktif": true,
                "aciklama": "MEMORY.md/USER.md 50K compaction — gunluk bakim"
            }
        }
    """
    try:
        logger.info("[Cron-Compaction] Gunluk compaction gorevi basladi")
        sonuc = memory_compaction_check(zorla=True)

        # Cache temizle (her gun)
        cache_sonuc = cache_tazele()
        sonuc["cache_temizlendi"] = cache_sonuc

        if sonuc.get("toplam_budanan_karakter", 0) > 0:
            seviye = logging.INFO
            mesaj = (f"[Cron-Compaction] Basarili: "
                     f"{sonuc['toplam_budanan_karakter']} karakter budandi, "
                     f"{sonuc['toplam_silinen_entry']} entry silindi, "
                     f"{sonuc['toplam_arsivlenen_entry']} entry arsivlendi")
        else:
            seviye = logging.DEBUG
            mesaj = "[Cron-Compaction] Compaction gerektiren dosya bulunamadi"

        logger.log(seviye, "%s", mesaj)
        return sonuc

    except Exception as e:
        logger.error("[Cron-Compaction] Hata: %s", e)
        return {"durum": "hata", "hata": str(e)}


# ── Compaction Ozeti ─────────────────────────────────────────────────────

def compaction_ozet() -> str:
    """MEMORY.md ve USER.md'nin guncel doluluk ozetini dondur."""
    satirlar = ["📊 Hafiza Compaction Ozeti", ""]

    for dosya_yolu, dosya_adi, limit in [
        (_MEMORY_YOLU, "MEMORY.md", MEMORY_LIMIT_CHARS),
        (_USER_YOLU, "USER.md", USER_LIMIT_CHARS),
    ]:
        if not dosya_yolu.exists():
            satirlar.append(f"❌ {dosya_adi}: Bulunamadi")
            continue

        boyut, yuzde = _dosya_boyut_kontrol(dosya_yolu, limit)
        esik = COMPACTION_ESIK_YUZDE

        # Doluluk gostergesi
        if yuzde >= esik:
            durum = "🔴 CRITICAL"
        elif yuzde >= esik * 0.8:
            durum = "🟡 YUKSEK"
        elif yuzde >= esik * 0.5:
            durum = "🟢 NORMAL"
        else:
            durum = "⚪ DUSUK"

        satirlar.append(
            f"{durum} {dosya_adi}: {boyut:,}/{limit:,} karakter "
            f"(%{yuzde:.1f})"
        )

    # Arsiv bilgisi
    if _ARSIV_DIZINI.exists():
        arsiv_sayisi = len(list(_ARSIV_DIZINI.glob("*.md")))
        arsiv_boyut = sum(
            f.stat().st_size for f in _ARSIV_DIZINI.glob("*.md")
        )
        satirlar.append(f"")
        satirlar.append(f"📦 Arsiv: {arsiv_sayisi} dosya, {arsiv_boyut // 1024} KB")

    return "\n".join(satirlar)


# ── Dogrudan Calistirma ──────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if "--cron" in sys.argv:
        print("[Compaction] Cron mode...")
        sonuc = cron_compaction_gorevi()
        print(json.dumps(sonuc, indent=2, ensure_ascii=False))

    elif "--zorla" in sys.argv or "--force" in sys.argv:
        print("[Compaction] Force compaction...")
        sonuc = memory_compaction_check(zorla=True)
        print(json.dumps(sonuc, indent=2, ensure_ascii=False))

    elif "--ozet" in sys.argv or "--summary" in sys.argv:
        print(compaction_ozet())

    elif "--cache-tazele" in sys.argv:
        print("[Compaction] Cache tazeleme...")
        sonuc = cache_tazele()
        print(json.dumps(sonuc, indent=2, ensure_ascii=False))

    else:
        print("[Compaction] Hafif kontrol...")
        sonuc = hafif_compaction_kontrol()
        print(json.dumps(sonuc, indent=2, ensure_ascii=False))
        print()
        print(compaction_ozet())
