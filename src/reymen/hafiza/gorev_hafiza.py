# -*- coding: utf-8 -*-
"""
gorev_hafiza.py — Görev Sonrası Hafıza Genişletme Mekanizması.

Her görev tamamlandığında conversation_loop.py tarafından çağrılır:
  1. Görev özetini ReYMeN hafızasına (SQLite+FTS5) kaydeder
  2. .ReYMeN/memories/ altına session log'u yazar
  3. SOUL.md'ye önemli kazanımları ekler
  4. Geçmiş konuşmaları ReYMeN session DB'den import eder

Entegrasyon:
    from gorev_hafiza import gorev_sonrasi_hafiza
import logging
logger = logging.getLogger(__name__)
    gorev_sonrasi_hafiza(task_id, hedef, sonuc)
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

# ── Sabitler ──────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.resolve()
REYMEN_MEMORIES = ROOT / ".ReYMeN" / "memories"
REYMEN_SKILLS = ROOT / ".ReYMeN" / "skills"
SOUL_PATH = ROOT / ".ReYMeN" / "SOUL.md"
HAFIZA_DB = ROOT / "merkez_db" / "hafiza.db"

# Dedup: daha önce kaydedilmiş içerik hash'leri (session boyunca)
_dedup_hash_set: set = set()
_dedup_dosya_set: set = set()
_dedup_kilit = threading.Lock()

# Hafıza genişletme modülü (opsiyonel)
try:
    from reymen.hafiza.hafiza_genislet import hafiza as _hafiza
    _HAFIZA_AKTIF = _hafiza._hazir if hasattr(_hafiza, '_hazir') else True
except ImportError:
    _hafiza = None
    _HAFIZA_AKTIF = False

# Session DB (ReYMeN'ten import için opsiyonel)
try:
    from reymen.hafiza.session_db import AdvancedSessionStorage as _SessionStorage
    _SESSION_IMPORT_AKTIF = True
except ImportError:
    _SessionStorage = None
    _SESSION_IMPORT_AKTIF = False


# ══════════════════════════════════════════════════════════════════════════
# DEDUP YARDIMCI
# ══════════════════════════════════════════════════════════════════════════

def _dedup_kontrol(kayit: dict, tur: str = "icerik") -> bool:
    """Aynı içerik daha önce kaydedilmiş mi kontrol et.

    Args:
        kayit: Görev kaydı dict'i
        tur: Kontrol türü ("icerik" = ozet hash'i, "dosya" = task_id + hedef)

    Returns:
        bool: True ise zaten kaydedilmiş (tekrar kaydetme)
    """
    with _dedup_kilit:
        try:
            if tur == "icerik":
                icerik = kayit.get("ozet", "") or kayit.get("hedef", "")
                icerik_hash = hash(icerik.strip()[:500])
                if icerik_hash in _dedup_hash_set:
                    return True
                _dedup_hash_set.add(icerik_hash)
                return False

            elif tur == "dosya":
                task_id = kayit.get("task_id", "")
                hedef = kayit.get("hedef", "")[:80]
                dosya_imza = f"{task_id}|{hedef}"
                if dosya_imza in _dedup_dosya_set:
                    return True
                _dedup_dosya_set.add(dosya_imza)
                return False

            return False

        except Exception:
            return False


# ══════════════════════════════════════════════════════════════════════════
# GÖREV SONRASI HAFIZA GENİŞLETME
# ══════════════════════════════════════════════════════════════════════════

def gorev_sonrasi_hafiza(
    task_id: str,
    hedef: str,
    sonuc: dict,
    session_id: Optional[str] = None,
    ozet: Optional[str] = None,
    kategori: str = "",
) -> dict:
    """Bir görevin tamamlanmasının ardından hafızayı genişlet.

    conversation_loop.py'de run_conversation() sonunda çağrılır.

    Args:
        task_id:    Görev ID'si
        hedef:      Kullanıcının hedef metni
        sonuc:      Görev sonucu dict'i (basarili, yanit, hata, sure, tur)
        session_id: Opsiyonel session ID (ReYMeN session)
        ozet:       Opsiyonel özet metni (yoksa otomatik oluşturulur)
        kategori:   "kali", "dron", "cad", "kali/network" vb. (opsiyonel)

    Returns:
        dict: Kayıt sonucu (kaydedildi, dosya_yolu vb.)
    """
    baslama = time.time()
    kayit = {
        "task_id": task_id,
        "zaman": datetime.now().isoformat(),
        "hedef": hedef[:200],
        "basarili": sonuc.get("basarili", False),
        "tur_sayisi": sonuc.get("turlar", 0),
        "sure_sn": sonuc.get("sure", 0),
        "session_id": session_id or sonuc.get("session_id", ""),
        "kategori": kategori[:100],
    }

    # Hata varsa ekle (ama çok uzun olmasın)
    hata = sonuc.get("hata")
    if hata:
        kayit["hata"] = str(hata)[:300]

    # Yanıt/çıktı varsa özetle
    yanit = sonuc.get("yanit") or sonuc.get("sonuc") or ""
    if yanit:
        kayit["yanit_ozeti"] = str(yanit)[:300]

    # Özet oluştur
    if not ozet:
        ozet = _ozet_olustur(kayit)
    kayit["ozet"] = ozet

    # 1. ReYMeN hafızasına kaydet
    hafiza_sonuc = _hafizaya_kaydet(kayit)

    # 2. .ReYMeN/memories/ altına session log'u
    dosya_sonuc = _memories_dosyaya_yaz(kayit)

    # 3. SOUL.md'ye önemli kazanım ekle (opsiyonel)
    soul_sonuc = _soul_guncelle(kayit)

    # 4. Beceri kristalleştir (sadece başarılı görevler)
    beceri_sonuc = {"durum": "atlandi", "sebep": "Basarisiz gorev"}
    if kayit.get("basarili"):
        kullanilan_araclar = sonuc.get("kullanilan_araclar", [])
        beceri_sonuc = beceri_kristallestir(
            gorev_adi=kayit.get("hedef", "Belirtilmemiş Görev")[:60],
            ozet=ozet[:300],
            kullanilan_araclar=kullanilan_araclar,
            ek_bilgiler={
                "sure_sn": kayit.get("sure_sn", 0),
                "tur_sayisi": kayit.get("tur_sayisi", 0),
                "task_id": kayit.get("task_id", ""),
            },
        )

    return {
        "task_id": task_id,
        "sure_sn": round(time.time() - baslama, 3),
        "hafiza": hafiza_sonuc,
        "dosya": dosya_sonuc,
        "soul": soul_sonuc,
        "beceri": beceri_sonuc,
        "ozet": ozet,
    }


def _ozet_olustur(kayit: dict) -> str:
    """Görev kaydından okunabilir özet oluştur."""
    durum = "✅ Başarılı" if kayit.get("basarili") else "❌ Hata"
    sure = kayit.get("sure_sn", 0)
    tur = kayit.get("tur_sayisi", 0)
    hedef = kayit.get("hedef", "")[:80]
    hata = kayit.get("hata", "")

    satirlar = [
        f"# {durum}: {hedef}",
        f"- Süre: {sure:.1f}s, Tur: {tur}",
    ]
    if hata:
        satirlar.append(f"- Hata: {hata[:200]}")
    return "\n".join(satirlar)


def _guven_skoru_hesapla(basarili_sayisi: int, hata_sayisi: int) -> float:
    """Güven skoru hesapla: basari/(basari+hata), bos=0.5."""
    toplam = basarili_sayisi + hata_sayisi
    if toplam == 0:
        return 0.5
    return round(basarili_sayisi / toplam, 3)


def _varsayilan_gecerlilik(baslangic_str: str = "") -> str:
    """6 aylık varsayılan geçerlilik tarihi döndür."""
    from datetime import timedelta
    baslangic = datetime.now()
    if baslangic_str:
        try:
            baslangic = datetime.fromisoformat(baslangic_str)
        except (ValueError, TypeError) as _e:
            logger.warning("[GorevHafiza] Gecersiz deger (L218): %s", ValueError)
            pass
    bitis = baslangic + timedelta(days=180)
    return bitis.strftime("%Y-%m-%d")


def guncelle_son_kullanim(kayit_id: int, kategori: str = "",
                          basarili_mi: bool = True):
    """Kaydın son_kullanim ve guven_skoru metadata'sını güncelle.

    Args:
        kayit_id: Hafıza DB'deki kayıt ID'si
        kategori: Opsiyonel kategori
        basarili_mi: Bu kullanım başarılı mı?
    """
    if not _HAFIZA_AKTIF or not _hafiza:
        return

    try:
        # Mevcut metadata'yı çek
        c = _hafiza._conn.cursor()
        c.execute("SELECT metadata FROM kayitlar WHERE id=?", (kayit_id,))
        row = c.fetchone()
        if not row:
            return

        meta = json.loads(row["metadata"]) if row["metadata"] else {}

        # son_kullanim
        meta["son_kullanim"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        # kullanım_sayisi
        meta["kullanim_sayisi"] = meta.get("kullanim_sayisi", 0) + 1

        # basari_sayisi / hata_sayisi
        if basarili_mi:
            meta["basari_sayisi"] = meta.get("basari_sayisi", 0) + 1
        else:
            meta["hata_sayisi"] = meta.get("hata_sayisi", 0) + 1

        # guven_skoru
        meta["guven_skoru"] = _guven_skoru_hesapla(
            meta.get("basari_sayisi", 0),
            meta.get("hata_sayisi", 0),
        )

        # kategori (eğer verildiyse)
        if kategori:
            meta["kategori"] = kategori

        # Güncelle
        _hafiza.kayit_guncelle(kayit_id, yeni_metadata=meta)

    except Exception as e:
        log.warning("Son kullanim guncelleme hatasi: %s", e)


def _hafizaya_kaydet(kayit: dict) -> dict:
    """ReYMeN SQLite hafızasına kaydet (FTS5 indexlenir). Dedup kontrollü."""
    if not _HAFIZA_AKTIF or not _hafiza:
        return {"durum": "pasif", "sebep": "hafiza_genislet modulu yok"}

    try:
        # ── Dedup: aynı içerik zaten kaydedildiyse atla ──
        if _dedup_kontrol(kayit, tur="icerik"):
            return {
                "durum": "atlandi",
                "sebep": "Aynı içerik zaten kaydedildi (dedup)",
                "session_id": kayit.get("session_id"),
            }

        session_id = kayit.get("session_id") or f"gorev_{kayit['task_id']}"

        # Session başlat
        _hafiza.initialize(session_id, baslik=kayit.get("hedef", "")[:100])

        # Görev kaydını konuşma koleksiyonuna ekle
        _hafiza.kaydet(
            icerik=kayit["ozet"],
            koleksiyon="konusmalar",
            anahtar=f"gorev_{kayit['task_id']}",
            metadata={
                "task_id": kayit["task_id"],
                "basarili": kayit.get("basarili"),
                "tur_sayisi": kayit.get("tur_sayisi"),
                "sure_sn": kayit.get("sure_sn"),
                "guven_skoru": _guven_skoru_hesapla(
                    1 if kayit.get("basarili") else 0,
                    0 if kayit.get("basarili") else 1,
                ),
                "son_kullanim": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "kategori": kayit.get("kategori", ""),
                "gecerlilik_tarihi": _varsayilan_gecerlilik(),
                "kullanim_sayisi": 1,
                "basari_sayisi": 1 if kayit.get("basarili") else 0,
                "hata_sayisi": 0 if kayit.get("basarili") else 1,
            },
        )

        # Hata varsa ayrı koleksiyon
        hata = kayit.get("hata")
        if hata:
            _hafiza.kaydet(
                icerik=hata,
                koleksiyon="notlar",
                anahtar=f"hata_{kayit['task_id']}",
                metadata={"task_id": kayit["task_id"]},
            )

        # Başarılı görevleri beceri koleksiyonuna
        if kayit.get("basarili"):
            _hafiza.kaydet(
                icerik=kayit["ozet"],
                koleksiyon="beceriler",
                anahtar=kayit.get("hedef", "")[:80],
                metadata={
                    "task_id": kayit["task_id"],
                    "tur": kayit.get("tur_sayisi", 0),
                    "sure": kayit.get("sure_sn", 0),
                    "guven_skoru": 0.8,  # yeni beceri: yüksek güven
                    "son_kullanim": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "kategori": kayit.get("kategori", ""),
                    "gecerlilik_tarihi": _varsayilan_gecerlilik(),
                    "kullanim_sayisi": 1,
                    "basari_sayisi": 1,
                    "hata_sayisi": 0,
                },
            )

        # Session'ı bitir
        _hafiza.session_bitir(ozet=kayit["ozet"][:500])

        return {"durum": "kaydedildi", "session_id": session_id}

    except Exception as e:
        log.warning("Hafiza kayit hatasi: %s", e)
        return {"durum": "hata", "sebep": str(e)}


def _memories_dosyaya_yaz(kayit: dict) -> dict:
    """.ReYMeN/memories/ altına session log dosyası yaz. Dedup kontrollü."""
    try:
        REYMEN_MEMORIES.mkdir(parents=True, exist_ok=True)

        # ── Dedup: aynı task_id + hedef için daha önce yazıldıysa atla ──
        if _dedup_kontrol(kayit, tur="dosya"):
            return {
                "durum": "atlandi",
                "sebep": "Aynı görev için dosya zaten yazildi (dedup)",
            }

        tarih = datetime.now().strftime("%Y%m%d_%H%M%S")
        dosya_adi = f"gorev_{kayit['task_id']}_{tarih}.md"
        dosya_yolu = REYMEN_MEMORIES / dosya_adi

        # Aynı ada sahip dosya varsa içerik karşılaştırması yap
        if dosya_yolu.exists():
            mevcut = dosya_yolu.read_text(encoding="utf-8", errors="replace")
            # Hedef ve task_id aynı mı kontrol et
            if kayit.get("hedef", "") in mevcut and kayit.get("task_id", "") in mevcut:
                return {
                    "durum": "atlandi",
                    "sebep": "Aynı içerikte dosya zaten mevcut",
                    "dosya": str(dosya_yolu),
                }

        icerik = f"""# Görev Kaydı: {kayit['task_id']}

**Tarih:** {kayit['zaman']}
**Hedef:** {kayit['hedef']}
**Durum:** {"✅ Başarılı" if kayit.get("basarili") else "❌ Hata"}
**Süre:** {kayit.get('sure_sn', 0):.1f}s
**Tur:** {kayit.get('tur_sayisi', 0)}

## Formatlı Özet
{gorev_ozeti_markdown(kayit)}

## Ham JSON
```json
{json.dumps({k: v for k, v in kayit.items() if k != 'ozet'}, ensure_ascii=False, indent=2)}
```
"""
        with open(dosya_yolu, "w", encoding="utf-8") as f:
            f.write(icerik)

        return {"durum": "yazildi", "dosya": str(dosya_yolu)}

    except Exception as e:
        log.warning("Dosya yazma hatasi: %s", e)
        return {"durum": "hata", "sebep": str(e)}


def _soul_guncelle(kayit: dict) -> dict:
    """SOUL.md'ye önemli kazanım ekle (sadece başarılı ve bilgi içerikli)."""
    if not kayit.get("basarili"):
        return {"durum": "atlandi", "sebep": "basarisiz gorev"}

    try:
        if not SOUL_PATH.exists():
            return {"durum": "atlandi", "sebep": "SOUL.md yok"}

        with open(SOUL_PATH, "r", encoding="utf-8") as f:
            mevcut = f.read()

        # Kısa bir kazanım satırı ekle
        kazanim = (
            f"\n  - [{kayit['zaman'][:10]}] {kayit['hedef'][:80]}"
            f" ({kayit.get('tur_sayisi', 0)} tur, {kayit.get('sure_sn', 0):.0f}s)"
        )

        # Sadece yeni satır varsa ekle
        if kazanim not in mevcut:
            # "## Öğrenilenler" bölümü varsa altına, yoksa sona ekle
            if "## Öğrenilenler" in mevcut:
                mevcut = mevcut.replace(
                    "## Öğrenilenler",
                    f"## Öğrenilenler{kazanim}",
                    1,
                )
            else:
                mevcut += f"\n## Öğrenilenler{kazanim}\n"

            with open(SOUL_PATH, "w", encoding="utf-8") as f:
                f.write(mevcut)

            return {"durum": "guncellendi"}

        return {"durum": "atlandi", "sebep": "zaten var"}

    except Exception as e:
        log.warning("SOUL guncelleme hatasi: %s", e)
        return {"durum": "hata", "sebep": str(e)}


# ══════════════════════════════════════════════════════════════════════════
# BECERİ KRISTALLEŞTİRME (SKILL.md)
# ══════════════════════════════════════════════════════════════════════════

def beceri_kristallestir(
    gorev_adi: str,
    ozet: str,
    kullanilan_araclar: Optional[list] = None,
    ek_bilgiler: Optional[dict] = None,
) -> dict:
    """Başarılı görevlerden otomatik SKILL.md oluştur.

    Görev adı + özet + kullanılan araçları alır, markdown formatında
    SKILL.md içeriği oluşturur ve .ReYMeN/skills/ altına kaydeder.

    Args:
        gorev_adi:      Görevin kısa adı (dosya adı olarak kullanılır)
        ozet:           Görevin özet metni
        kullanilan_araclar: Kullanılan araçların listesi (örn. ["terminal", "read_file"])
        ek_bilgiler:    Opsiyonel ek bilgiler (sure, tur, kategoriler vb.)

    Returns:
        dict: Kayıt sonucu (durum, dosya_yolu, hata)
    """
    try:
        # Dizin yoksa oluştur
        REYMEN_SKILLS.mkdir(parents=True, exist_ok=True)

        if kullanilan_araclar is None:
            kullanilan_araclar = []
        if ek_bilgiler is None:
            ek_bilgiler = {}

        # Dosya adı: gorev_adi boşluk/turkce -> guvenli slug
        slug = (
            gorev_adi.lower()
            .replace(" ", "_")
            .replace("ı", "i")
            .replace("ğ", "g")
            .replace("ü", "u")
            .replace("ş", "s")
            .replace("ö", "o")
            .replace("ç", "c")
            .replace("İ", "i")
            .replace("Ğ", "g")
            .replace("Ü", "u")
            .replace("Ş", "s")
            .replace("Ö", "o")
            .replace("Ç", "c")
        )
        # Alfanumerik olmayan karakterleri temizle
        slug = "".join(c for c in slug if c.isalnum() or c == "_")
        slug = slug[:60] or f"skill_{int(time.time())}"
        dosya_adi = f"{slug}.md"
        dosya_yolu = REYMEN_SKILLS / dosya_adi

        # Araç listesini markdown listesine çevir
        arac_liste = ""
        if kullanilan_araclar:
            arac_liste = "\n".join(f"- `{a}`" for a in kullanilan_araclar)
        else:
            arac_liste = "- *(belirtilmedi)*"

        # Ek bilgiler tablosu
        ek_tablo = ""
        if ek_bilgiler:
            satirlar = []
            for anahtar, deger in ek_bilgiler.items():
                baslik = anahtar.replace("_", " ").title()
                satirlar.append(f"| {baslik} | {deger} |")
            if satirlar:
                ek_tablo = "| **Özellik** | **Değer** |\n|---|---|\n" + "\n".join(satirlar)

        # Oturum içi dedup: aynı gorev_adi + ozet daha önce işlendiyse atla
        icerik_imza = f"{gorev_adi}|{ozet[:100]}"
        icerik_hash = hash(icerik_imza)
        with _dedup_kilit:
            zaten_var = icerik_hash in _dedup_hash_set
            if not zaten_var:
                _dedup_hash_set.add(icerik_hash)
        if zaten_var:
            return {
                "durum": "atlandi",
                "sebep": "Aynı beceri bu oturumda zaten kristallestirildi",
                "dosya": str(REYMEN_SKILLS / f"{slug}.md") if slug else "",
            }

        # SKILL.md içeriğini oluştur
        icerik = f"""# Beceri: {gorev_adi}

## Açıklama
{ozet}

## Kullanılan Araçlar
{arac_liste}

## Oluşturulma Tarihi
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        if ek_tablo:
            icerik += f"""
## Ek Bilgiler
{ek_tablo}
"""

        # Aynı isimde dosya varsa ve içerik aynıysa tekrar yazma (dedup)
        if dosya_yolu.exists():
            mevcut_icerik = dosya_yolu.read_text(encoding="utf-8", errors="replace")
            if mevcut_icerik.strip() == icerik.strip():
                return {
                    "durum": "atlandi",
                    "sebep": "Aynı içerik zaten mevcut",
                    "dosya": str(dosya_yolu),
                }

        # Dosyaya yaz
        dosya_yolu.write_text(icerik, encoding="utf-8")
        log.info("Beceri kristallesti: %s", dosya_yolu)

        return {
            "durum": "kaydedildi",
            "dosya": str(dosya_yolu),
            "slug": slug,
        }

    except Exception as e:
        log.warning("Beceri kristallestirme hatasi: %s", e)
        return {"durum": "hata", "sebep": str(e)}


def gorev_ozeti_markdown(kayit: dict) -> str:
    """Görev kaydını zengin markdown formatında formatla.

    Tablo, kod blokları ve emoji'lerle daha okunabilir bir özet üretir.

    Args:
        kayit: Görev kaydı dict'i (task_id, zaman, hedef, basarili, ...)

    Returns:
        str: Formatlanmış markdown metni
    """
    try:
        basarili = kayit.get("basarili", False)
        durum_emoji = "✅" if basarili else "❌"
        durum_yazi = "Başarılı" if basarili else "Başarısız"

        task_id = kayit.get("task_id", "?")
        zaman = kayit.get("zaman", datetime.now().isoformat())
        hedef = kayit.get("hedef", "Belirtilmemiş")
        sure = kayit.get("sure_sn", 0)
        tur = kayit.get("tur_sayisi", 0)
        hata = kayit.get("hata", "")
        yanit_ozeti = kayit.get("yanit_ozeti", "")
        ozet = kayit.get("ozet", "")

        satirlar = [
            f"# {durum_emoji} Görev Raporu: {task_id}",
            "",
            f"**Tarih:** {zaman}",
            "",
            "## 📋 Genel Bilgiler",
            "| **Alan** | **Değer** |",
            "|---|---|",
            f"| Görev ID | `{task_id}` |",
            f"| Hedef | {hedef} |",
            f"| Durum | {durum_emoji} {durum_yazi} |",
            f"| Süre | {sure:.1f} saniye |",
            f"| Tur Sayısı | {tur} |",
        ]

        if hata:
            satirlar.extend([
                "",
                "## ❌ Hata Detayı",
                "```",
                hata[:500],
                "```",
            ])

        if yanit_ozeti:
            satirlar.extend([
                "",
                "## 💬 Yanıt Özeti",
                "```text",
                yanit_ozeti[:500],
                "```",
            ])

        if ozet:
            satirlar.extend([
                "",
                "## 📝 Özet",
                ozet,
            ])

        # Ek JSON detaylar
        ek_detay = {k: v for k, v in kayit.items()
                    if k not in ("task_id", "zaman", "hedef", "basarili",
                                 "sure_sn", "tur_sayisi", "hata", "yanit_ozeti", "ozet")}
        if ek_detay:
            satirlar.extend([
                "",
                "## 🔍 Ek Detaylar",
                "```json",
                json.dumps(ek_detay, ensure_ascii=False, indent=2),
                "```",
            ])

        return "\n".join(satirlar)

    except Exception as e:
        log.warning("Markdown format hatasi: %s", e)
        return f"# Görev Raporu\n\n*Format hatası: {e}*"


# ══════════════════════════════════════════════════════════════════════════
# GEÇMİŞ KONUŞMALARI İMPORT ET
# ══════════════════════════════════════════════════════════════════════════

def gecmis_konusmalari_import_et(
    kaynak: str = "memory",
    limit: int = 50,
) -> dict:
    """Geçmiş konuşmaları ReYMeN session DB'den ReYMeN hafızasına import eder.

    Args:
        kaynak: "memory" → .ReYMeN/memories/, "session_db" → ReYMeN SQLite
        limit:  Maks import edilecek kayıt sayısı

    Returns:
        dict: İstatistik (import_edilen, atlanan, hatalar)
    """
    istatistik = {"import_edilen": 0, "atlanan": 0, "hatalar": 0}

    if kaynak == "memory":
        _memory_dizini_import_et(REYMEN_MEMORIES, istatistik, limit)
    elif kaynak == "session_db":
        _session_db_import_et(istatistik, limit)

    return istatistik


def _memory_dizini_import_et(
    dizin: Path,
    istatistik: dict,
    limit: int,
) -> None:
    """.ReYMeN/memories/ içindeki .md ve .json dosyalarını hafızaya ekle."""
    if not dizin.exists():
        istatistik["atlanan"] += 1
        return

    for f in sorted(dizin.glob("*"))[:limit]:
        try:
            icerik = f.read_text(encoding="utf-8", errors="replace")[:2000]
            if not icerik.strip():
                istatistik["atlanan"] += 1
                continue

            # Dosya türüne göre koleksiyon belirle
            if f.suffix == ".json":
                koleksiyon = "notlar"
                try:
                    data = json.loads(icerik)
                    icerik = json.dumps(data, ensure_ascii=False)[:2000]
                except json.JSONDecodeError as _gorev_ha_e624:
                    print(f"[UYARI] gorev_hafiza.py:625 - {_gorev_ha_e624}")
            else:
                koleksiyon = "konusmalar"

            if _hafiza and _HAFIZA_AKTIF:
                _hafiza.kaydet(
                    icerik=icerik[:1500],
                    koleksiyon=koleksiyon,
                    anahtar=f"import_{f.stem}",
                    metadata={"kaynak": str(f), "import_zamani": time.time()},
                )

            istatistik["import_edilen"] += 1

        except Exception as e:
            log.warning("Import hatasi (%s): %s", f.name, e)
            istatistik["hatalar"] += 1


def _session_db_import_et(istatistik: dict, limit: int) -> None:
    """ReYMeN session_db.py'den session'ları import et."""
    if not _SESSION_IMPORT_AKTIF:
        istatistik["atlanan"] += 1
        return

    try:
        storage = _SessionStorage()
        # session_list metodu varsa kullan
        if hasattr(storage, "session_list"):
            sessions = storage.session_list(limit=limit)
        else:
            sessions = []

        for s in sessions[:limit]:
            try:
                session_id = s.get("id", "") if isinstance(s, dict) else str(s)
                mesajlar = []
                if hasattr(storage, "session_mesajlari"):
                    mesajlar = storage.session_mesajlari(session_id)

                ozet = s.get("ozet", "") if isinstance(s, dict) else ""
                kaynak = s.get("source", "session_db") if isinstance(s, dict) else "session_db"

                icerik = f"""
## Session: {session_id}
**Kaynak:** {kaynak}
**Tarih:** {s.get("baslangic", "") if isinstance(s, dict) else ""}
**Mesaj Sayisi:** {len(mesajlar)}
**Özet:** {ozet}
"""

                if _hafiza and _HAFIZA_AKTIF:
                    _hafiza.kaydet(
                        icerik=icerik[:2000],
                        koleksiyon="konusmalar",
                        anahtar=f"session_import_{session_id}",
                        metadata={
                            "session_id": session_id,
                            "kaynak": kaynak,
                            "import_zamani": time.time(),
                        },
                    )

                istatistik["import_edilen"] += 1

            except Exception as e:
                log.warning("Session import hatasi: %s", e)
                istatistik["hatalar"] += 1

    except Exception as e:
        log.warning("Session DB import hatasi: %s", e)
        istatistik["hatalar"] += 1


# ══════════════════════════════════════════════════════════════════════════
# TOPLU GEÇMİŞ İMPORT
# ══════════════════════════════════════════════════════════════════════════

def tum_gecmisi_isle() -> dict:
    """Tüm geçmiş konuşmaları tek seferde işle.

    Hem .ReYMeN/memories/ içindeki dosyaları hem de ReYMeN session DB'yi
    tarar ve ReYMeN hafıza sistemine kaydeder.

    Returns:
        dict: İstatistik (memory_count, session_count, toplam)
    """
    sonuc = {"memory": {"import_edilen": 0}, "session_db": {"import_edilen": 0}}

    try:
        # 1. .ReYMeN/memories/ içindeki dosyalar
        mem_sonuc = gecmis_konusmalari_import_et(kaynak="memory", limit=100)
        sonuc["memory"] = mem_sonuc

        # 2. ReYMeN session DB
        db_sonuc = gecmis_konusmalari_import_et(kaynak="session_db", limit=50)
        sonuc["session_db"] = db_sonuc

        # 3. .alt_ajan_hafiza/ içindeki task log'ları
        alt_hafiza_dizini = ROOT / ".alt_ajan_hafiza"
        if alt_hafiza_dizini.exists():
            import_count = 0
            for f in alt_hafiza_dizini.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8", errors="replace"))
                    task_id = data.get("task_id", f.stem)
                    kayitlar = data.get("kayitlar", [])
                    for k in kayitlar[:20]:
                        icerik = json.dumps(k.get("veri", {}), ensure_ascii=False)
                        if _hafiza and _HAFIZA_AKTIF:
                            _hafiza.kaydet(
                                icerik=icerik[:1000],
                                koleksiyon="notlar",
                                anahtar=f"alt_ajan_{task_id}",
                                metadata={"task_id": task_id, "tur": k.get("tur")},
                            )
                    import_count += 1
                except Exception as _gorev_ha_e742:
                    print(f"[UYARI] gorev_hafiza.py:743 - {_gorev_ha_e742}")
            sonuc["alt_ajan_hafiza"] = {"import_edilen": import_count}

    except Exception as e:
        log.error("Toplu import hatasi: %s", e)
        sonuc["hata"] = str(e)

    return sonuc


# ══════════════════════════════════════════════════════════════════════════
# NESNe TABANLI ARAYÜZ
# ══════════════════════════════════════════════════════════════════════════

class GorevHafiza:
    """Görev hafıza sistemi için nesne tabanlı arayüz.

    Modülün fonksiyon tabanlı API'sini bir sınıf üzerinden sarmalar.
    """

    def kaydet(self, task_id: str, hedef: str, sonuc: dict) -> dict:
        return gorev_sonrasi_hafiza(task_id=task_id, hedef=hedef, sonuc=sonuc)

    def kristallestir(self, beceri: str, **kwargs) -> dict:
        return beceri_kristallestir(beceri, **kwargs)

    def ozet_markdown(self, task_id: str, **kwargs) -> str:
        return gorev_ozeti_markdown(task_id, **kwargs)

    def gecmisi_isle(self) -> dict:
        return tum_gecmisi_isle()


# ══════════════════════════════════════════════════════════════════════════
# DOĞRUDAN ÇALIŞTIRMA
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("  ReYMeN Görev Hafıza Sistemi")
    print("=" * 60)

    # Toplu import
    print("\n[1/2] Geçmiş konuşmalar import ediliyor...")
    sonuc = tum_gecmisi_isle()
    print(f"  Memory: {sonuc.get('memory', {}).get('import_edilen', 0)} kayit")
    print(f"  Session DB: {sonuc.get('session_db', {}).get('import_edilen', 0)} kayit")
    if "alt_ajan_hafiza" in sonuc:
        print(f"  Alt Ajan: {sonuc['alt_ajan_hafiza'].get('import_edilen', 0)} kayit")

    # Test kaydı
    print("\n[2/2] Test kaydi yapiliyor...")
    test_sonuc = gorev_sonrasi_hafiza(
        task_id=f"test_{uuid.uuid4().hex[:6]}",
        hedef="Hafiza genisletme mekanizmasi testi",
        sonuc={"basarili": True, "turlar": 3, "sure": 1.5, "yanit": "Test basarili"},
    )
    print(f"  Hafiza: {test_sonuc.get('hafiza', {}).get('durum', '?')}")
    print(f"  Dosya: {test_sonuc.get('dosya', {}).get('durum', '?')}")
    print(f"  SOUL: {test_sonuc.get('soul', {}).get('durum', '?')}")

    print(f"\n✅ Toplam sure: {test_sonuc.get('sure_sn', 0):.2f}s")
