# -*- coding: utf-8 -*-
"""
gorev_once_kontrol.py — Görev Öncesi Hafıza Kontrolü + isle() API.

Her görev başlamadan ÖNCE çağrılır. 3 katmanlı sistem:

1. hafizada_ara(hedef, kategori) — Hafızada benzer görev/çözüm ara
   - kategori filtresi: "kali", "dron", "cad", "windows", "kali/network" vb.
   - guven_skoru < 0.5 ise "belirsiz" döndür
   - gecerlilik_tarihi < bugün ise "gecersiz" işareti ekle

2. isle(hedef, islev, kategori) — "HAFIZAYA BAK → VARSA KULLAN → YOKSA DENE → KAYDET"
   Örn:
     sonuc = isle("nmap port tara", lambda: terminal("nmap -sS 127.0.0.1"))
     → Hafızada varsa döndür
     → Yoksa çalıştır, kaydet, döndür

3. gorev_once_hafiza_kontrol(hedef) — Altta yatan 5 katmanlı kontrol
   Yeni: dönüşte guven_skoru, kategori, gecerlilik_tarihi alanları

4. kaydet_isle(hedef, kategori, sonuc_bilgisi, basarili) — Otomatik guven_skoru hesapla
"""

import json
import logging
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging
logger = logging.getLogger(__name__)

log = logging.getLogger(__name__)

# ── Sabitler ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.resolve()  # reymen/hafiza/
PROJE = ROOT.parent.parent              # hermes_projesi/

SOUL_PATH = PROJE / ".ReYMeN" / "SOUL.md"
MEMORIES_DIR = PROJE / ".ReYMeN" / "memories"
SKILLS_DIR = PROJE / ".ReYMeN" / "skills"
NOTES_SESSIONS = PROJE / ".ReYMeN" / "notes" / "sessions"

# Cross-agent destek: her ajan .AjanAdi/notes/ altına bakar
_CROSS_AGENT_DIRS: list = []

# Python session_search fonksiyonu (varsa)
try:
    from reymen.hafiza.session_db import AdvancedSessionStorage as _SessionStorage
    _SESSION_DB_AKTIF = True
except ImportError:
    _SessionStorage = None
    _SESSION_DB_AKTIF = False

# FTS5 tabanlı hafıza modülü (varsa)
try:
    from reymen.hafiza.hafiza_genislet import hafiza as _hafiza
    _HAFIZA_AKTIF = hasattr(_hafiza, '_hazir') and _hafiza._hazir
except ImportError:
    _hafiza = None
    _HAFIZA_AKTIF = False

# Gorev hafiza modülü (kaydetme + guven_skoru için)
try:
    from reymen.hafiza.gorev_hafiza import gorev_sonrasi_hafiza, guncelle_son_kullanim
    _GOREV_HAFIZA_AKTIF = True
except ImportError:
    gorev_sonrasi_hafiza = None
    guncelle_son_kullanim = None
    _GOREV_HAFIZA_AKTIF = False


# ══════════════════════════════════════════════════════════════════════════
# GÜVEN SKORU + GEÇERLİLİK YARDIMCILARI
# ══════════════════════════════════════════════════════════════════════════

def _guven_skoru(basari: int, hata: int) -> float:
    """Güven skoru: basari/(basari+hata), ikisi de 0 ise 0.5."""
    toplam = basari + hata
    return round(basari / toplam, 3) if toplam > 0 else 0.5


def _varsayilan_gecerlilik() -> str:
    """Bugünden +180 gün."""
    return (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d")


def _gecerlilik_kontrol(gecerlilik_tarihi: str) -> str:
    """Tarih kontrolü: 'gecerli', 'gecersiz', 'belirsiz'."""
    if not gecerlilik_tarihi:
        return "belirsiz"
    try:
        tarih = datetime.strptime(gecerlilik_tarihi[:10], "%Y-%m-%d")
        if tarih < datetime.now():
            return "gecersiz"
        return "gecerli"
    except (ValueError, TypeError):
        return "belirsiz"


# ══════════════════════════════════════════════════════════════════════════
# KATEGORİ YARDIMCILARI
# ══════════════════════════════════════════════════════════════════════════

def _kategori_eslesme(hedef: str) -> str:
    """Hedef metnine göre kategori tahmini yap.

    "nmap ile port tara" → "kali/network"
    "drone ucur" → "dron"
    "solidworks kur" → "cad"
    "ekran al" → "windows"
    """
    h = hedef.lower()

    # Kali
    if any(k in h for k in ["nmap", "metasploit", "burp", "sqlmap", "hydra",
                             "kali", "sızma", "penetration", "exploit",
                             "wireshark", "aircrack", "john", "hashcat"]):
        if any(n in h for n in ["network", "port", "scan", "tarama", "ip",
                                 "ağ", "ag"]):
            return "kali/network"
        if any(w in h for w in ["web", "http", "site", "sql", "xss"]):
            return "kali/web"
        return "kali/genel"

    # Dron
    if any(k in h for k in ["dron", "drone", "uav", "uçur", "ucur", "px4",
                             "ardupilot", "mission planner", "mavlink"]):
        return "dron"

    # CAD
    if any(k in h for k in ["cad", "solidworks", "autocad", "fusion",
                             "catia", "3d", "stl", "step", "iges"]):
        return "cad"

    # Windows
    if any(k in h for k in ["windows", "win10", "win11", "regedit", "powershell",
                             "cmd", "ekran", "screenshot", "mouse", "klavye"]):
        return "windows"

    return "genel"


# ══════════════════════════════════════════════════════════════════════════
# 1. HAFIZADA_ARA — kategori filtreli + güven skorlu ana fonksiyon
# ══════════════════════════════════════════════════════════════════════════

def hafizada_ara(hedef: str, kategori: str = "") -> dict:
    """Hafızada benzer görev ara, kategori + güven skoru filtresiyle.

    Parametre:
        hedef:   Görev metni ("nmap ile port tara")
        kategori: İsteğe bağlı kategori filtresi ("kali/network")

    Dönüş:
        {
            "bulundu": True/False,
            "guven_skoru": 0.0-1.0,      # 0.5'den düşükse "belirsiz"
            "guven_seviyesi": "yuksek"|"orta"|"dusuk"|"belirsiz",
            "kategori": "kali/network",
            "gecerlilik_tarihi": "2026-12-20",
            "gecerlilik_durumu": "gecerli"|"gecersiz"|"belirsiz",
            "icerik": "...",
            "kaynak": "memory_db",
            "kayit_id": 123,             # guncelleme için
        }
    """
    # 1. Altta yatan 5 katmanlı kontrol
    ham_sonuc = gorev_once_hafiza_kontrol(hedef, kategori)

    if not ham_sonuc or not ham_sonuc.get("bulundu"):
        # Kategori tahmini yap (bulunamasa bile)
        tahmin = kategori if kategori else _kategori_eslesme(hedef)
        return {
            "bulundu": False,
            "guven_skoru": 0.0,
            "guven_seviyesi": "belirsiz",
            "kategori": tahmin,
            "gecerlilik_tarihi": "",
            "gecerlilik_durumu": "belirsiz",
            "icerik": "",
            "kaynak": "",
            "kayit_id": None,
        }

    # 2. Metadata'dan guven_skoru + gecerlilik çek
    guven = float(ham_sonuc.get("guven_skoru", 0.5))
    gecerlilik = ham_sonuc.get("gecerlilik_tarihi", "")
    gec_durum = _gecerlilik_kontrol(gecerlilik)

    # 3. Güven seviyesi
    if guven >= 0.8:
        guven_seviye = "yuksek"
    elif guven >= 0.5:
        guven_seviye = "orta"
    elif guven > 0:
        guven_seviye = "dusuk"
    else:
        guven_seviye = "belirsiz"

    # 4. guven_skoru < 0.5 → belirsiz
    if guven < 0.5:
        guven_seviye = "belirsiz"

    return {
        "bulundu": True,
        "guven_skoru": guven,
        "guven_seviyesi": guven_seviye,
        "kategori": ham_sonuc.get("kategori", kategori or "genel"),
        "gecerlilik_tarihi": gecerlilik,
        "gecerlilik_durumu": gec_durum,
        "icerik": ham_sonuc.get("icerik", ""),
        "kaynak": ham_sonuc.get("kaynak", ""),
        "kayit_id": ham_sonuc.get("kayit_id", None),
    }


# ══════════════════════════════════════════════════════════════════════════
# 2. ISLE — HAFIZAYA BAK → VARSA KULLAN → YOKSA DENE → KAYDET
# ══════════════════════════════════════════════════════════════════════════

def isle(
    hedef: str,
    islev: Callable[[], Any],
    kategori: str = "",
    auto_kategori: bool = True,
) -> dict:
    """Ana API: Hafızaya bak, varsa döndür, yoksa çalıştır, kaydet, döndür.

    Kullanım:
        sonuc = isle("nmap ile port tara", lambda: terminal("nmap --help"))
        if sonuc["hafizada"]:
            print("Hafizadan geldi:", sonuc["icerik"])
        else:
            print("Yeni calisti:", sonuc["cikti"])

    Parametre:
        hedef:         Görev metni
        islev:         Çalıştırılacak fonksiyon (callable)
        kategori:      İsteğe bağlı kategori ("kali/network")
        auto_kategori: True ise metinden otomatik çıkar

    Dönüş:
        {
            "hafizada": True/False,
            "icerik": "...",          # hafizadan gelen içerik
            "cikti": "...",           # islev() çıktısı (hafizada=False ise)
            "kategori": "...",
            "guven_skoru": 0.0-1.0,
            "gecerlilik_durumu": "...",
            "basarili": True/False,
            "hata": "...",
        }
    """
    # Kategori belirle
    if not kategori and auto_kategori:
        kategori = _kategori_eslesme(hedef)
    elif not kategori:
        kategori = "genel"

    # 1. HAFIZAYA BAK
    hafiza_sonuc = hafizada_ara(hedef, kategori)

    if hafiza_sonuc["bulundu"] and hafiza_sonuc["guven_seviyesi"] != "belirsiz":
        # Kullanım sayısını güncelle
        kayit_id = hafiza_sonuc.get("kayit_id")
        if kayit_id and _HAFIZA_AKTIF and _hafiza and guncelle_son_kullanim is not None:
            try:
                guncelle_son_kullanim(kayit_id, kategori=kategori, basarili_mi=True)
            except Exception as _e:
                logger.warning("[GorevOnceKontrol] except Exception (L269): %s", Exception)
                pass

        return {
            "hafizada": True,
            "icerik": hafiza_sonuc["icerik"],
            "cikti": None,
            "kategori": hafiza_sonuc["kategori"],
            "guven_skoru": hafiza_sonuc["guven_skoru"],
            "gecerlilik_durumu": hafiza_sonuc["gecerlilik_durumu"],
            "basarili": True,
            "hata": None,
        }

    # 2. Bilgi yoksa DENE
    try:
        baslama = time.time()
        cikti = islev()
        sure = time.time() - baslama
        basarili = True
        hata = None
    except Exception as e:
        cikti = None
        sure = 0
        basarili = False
        hata = str(e)

    # 3. KAYDET
    if _GOREV_HAFIZA_AKTIF and gorev_sonrasi_hafiza:
        try:
            import uuid
            task_id = str(uuid.uuid4())[:8]
            sonuc_dict = {
                "basarili": basarili,
                "yanit": str(cikti)[:1000] if cikti else "",
                "hata": hata[:500] if hata else None,
                "sure": round(sure, 2),
                "turlar": 1,
                "kategori": kategori,
            }
            gorev_sonrasi_hafiza(task_id, hedef, sonuc_dict, kategori=kategori)
        except Exception as _e:
            logger.warning("[GorevOnceKontrol] except Exception (L310): %s", Exception)
            pass

    return {
        "hafizada": False,
        "icerik": None,
        "cikti": str(cikti)[:2000] if cikti else "",
        "kategori": kategori,
        "guven_skoru": _guven_skoru(1 if basarili else 0, 0 if basarili else 1),
        "gecerlilik_durumu": "belirsiz",
        "basarili": basarili,
        "hata": hata,
    }


# ══════════════════════════════════════════════════════════════════════════
# 3. ONERI_URET — belirsiz gorev icin hafiza tabanli oneri
# ══════════════════════════════════════════════════════════════════════════

def oneri_uret(hedef: str) -> dict:
    """Belirsiz bir görev için hafızaya dayalı en iyi tahmini üret.

    "Sistemi güvenli yap" geldiğinde:
      → hafizada nmap bilgisi var mı? → "Port taraması mı demek istiyorsun?"

    Parametre:
        hedef: Kullanıcının belirsiz görev metni.

    Dönüş:
        {
            "oneri_uretilen": True/False,
            "oneri": "Sanırım port taraması demek istiyorsun. nmap -sV bilgim var, ondan başlayalım mı?",
            "kategori": "kali/network/nmap",
            "icerik": "...nmap icerigi...",
            "guven_skoru": 0.7,
            "kaynak": "memory_db",
        }
        ya da hicbir eslesme yoksa:
        {
            "oneri_uretilen": False,
            "oneri": "",
        }
    """
    hedef_lower = hedef.strip().lower()

    # Selamlasma / anlamsiz girdi kontrolu
    selam_kelimeler = {"merhaba", "selam", "hey", "hi", "hello", "naber",
                       "nasılsın", "nasilsin", "iyi", "teşekkür", "tesekkur",
                       "sağol", "sagol", "bye", "görüşürüz", "gorusuruz"}
    kelimeler = set(hedef_lower.split())
    if len(kelimeler - selam_kelimeler) == 0 and len(kelimeler) <= 2:
        return {
            "oneri_uretilen": False,
            "oneri": "",
            "sebep": "selamlasma_tespit",
        }

    # ── Kategori tahmini ve genişletilmiş kelime seti ────────────────
    # "sistemi güvenli yap" → {kali/network/nmap, kali/web, ...}
    # Her kategori için tetikleyici kelimeler + hafizada ara
    kategori_agaci = [
        {
            "kategori": "kali/network/nmap",
            "tetikleyiciler": [
                "güvenli", "guvenli", "port", "tarama", "scan", "nmap",
                "ağ", "ag", "network", "ip", "servis", "açık", "acik",
                "sızma", "sizma", "pentest", "güvenlik", "guvenlik",
            ],
            "aciklama": "port taraması / servis tespiti",
        },
        {
            "kategori": "kali/web",
            "tetikleyiciler": [
                "web", "site", "http", "sql", "xss", "csrf", "burp",
                "güvenli", "guvenli", "güvenlik", "guvenlik",
            ],
            "aciklama": "web güvenlik testi",
        },
        {
            "kategori": "dron",
            "tetikleyiciler": [
                "dron", "drone", "uçur", "ucur", "px4", "uav",
                "uçuş", "ucus", "iha",
            ],
            "aciklama": "drone / IHA uçuşu",
        },
        {
            "kategori": "cad",
            "tetikleyiciler": [
                "cad", "solidworks", "çizim", "cizim", "3d", "model",
                "tasarım", "tasarim", "mekanik",
            ],
            "aciklama": "CAD tasarım / 3D modelleme",
        },
        {
            "kategori": "windows",
            "tetikleyiciler": [
                "windows", "masaüstü", "masaustu", "ekran", "mouse",
                "klavye", "otomasyon", "script",
            ],
            "aciklama": "Windows otomasyonu",
        },
    ]

    # 1. Hangi kategoriler tetikleniyor?
    tetiklenen = []
    for kat in kategori_agaci:
        eslesme_sayisi = sum(1 for t in kat["tetikleyiciler"] if t in hedef_lower)
        if eslesme_sayisi > 0:
            tetiklenen.append((kat, eslesme_sayisi))

    # Eslesme yoksa genel dene
    if not tetiklenen:
        tetiklenen = [(kategori_agaci[0], 0)]

    # 2. Her tetiklenen kategori icin hafizada ara
    en_iyi = None
    en_yuksek_puan = 0

    for kat, eslesme_sayisi in tetiklenen:
        s = hafizada_ara(hedef, kategori=kat["kategori"])
        if s["bulundu"]:
            # Puan: kategori eslesmesi + guven_skoru
            puan = eslesme_sayisi * 0.3 + float(s.get("guven_skoru", 0)) * 0.7
            if puan > en_yuksek_puan:
                en_yuksek_puan = puan
                en_iyi = (kat, s)

    # 3. Kelime eslesmesine gore puanla (hafizada bulunamadiysa)
    if not en_iyi and tetiklenen:
        kat0, es0 = tetiklenen[0]
        en_iyi = (kat0, None)
        en_yuksek_puan = es0 * 0.3

    if not en_iyi:
        return {"oneri_uretilen": False, "oneri": ""}

    kat, hafiza_sonuc = en_iyi

    # 4. Oneri metnini olustur
    if hafiza_sonuc and hafiza_sonuc.get("bulundu"):
        icerik = hafiza_sonuc.get("icerik", "")[:200]
        oneri_metni = (
            f"\"{hedef}\" dediniz.\n"
            f"Hafizamda en alakali kayit: **{kat['kategori']}**\n"
            f"({kat['aciklama']})\n"
            f"İcerik: {icerik}\n\n"
            f"Buna benzer bir sey mi yapmak istiyorsunuz?"
        )
        guven = 0.5 + min(hafiza_sonuc.get("guven_skoru", 0) * 0.5, 0.4)
    else:
        oneri_metni = (
            f"\"{hedef}\" dediniz.\n"
            f"**{kat['kategori']}** ile ilgili bir sey olabilir ({kat['aciklama']}).\n"
            f"Hafizamda bu konuda henuz kayit yok.\n"
            f"Denediğimizde otomatik kaydederim."
        )
        guven = 0.4 + eslesme_sayisi * 0.1

    return {
        "oneri_uretilen": True,
        "oneri": oneri_metni,
        "kategori": kat["kategori"],
        "aciklama": kat["aciklama"],
        "icerik": hafiza_sonuc.get("icerik", "") if hafiza_sonuc else "",
        "guven_skoru": round(min(guven, 0.95), 2),
        "kaynak": hafiza_sonuc.get("kaynak", "kategori_tahmini") if hafiza_sonuc else "kategori_tahmini",
    }


# ══════════════════════════════════════════════════════════════════════════
# 4. GOREV_ONCE_HAFIZA_KONTROL (güncellendi — yeni alanlar eklendi)
# ══════════════════════════════════════════════════════════════════════════

def gorev_once_hafiza_kontrol(hedef: str, kategori: str = "") -> Optional[dict]:
    """Görev başlamadan önce hafızada benzer çözüm ara (5 katman).

    Parametre:
        hedef:    Görev metni.
        kategori: Opsiyonel kategori filtresi ("kali", "dron", "cad").

    Dönüş:
        dict: {
            "bulundu": True,
            "kaynak": "SOUL.md" | "memory_db" | "notes" | "skills",
            "icerik": "...",
            "guven_skoru": 0.0-1.0,         # YENİ
            "kategori": "kali/network",      # YENİ
            "gecerlilik_tarihi": "2026-12-20", # YENİ
            "kayit_id": 123,                 # YENİ (guncelleme için)
            "detay": "...",
            "tarih": "2026-06-20",
        }
        None: Bulunamadı.
    """
    hedef_temiz = hedef.strip().lower()[:120]

    # 1. SOUL.md
    sonuc = _soul_kontrol(hedef_temiz)
    if sonuc and _kategori_uygun(sonuc, kategori):
        sonuc.setdefault("guven_skoru", 0.7)
        sonuc.setdefault("kategori", kategori or _kategori_eslesme(hedef))
        sonuc.setdefault("gecerlilik_tarihi", _varsayilan_gecerlilik())
        return sonuc

    # 2. Memory DB (FTS5)
    sonuc = _memory_db_kontrol(hedef_temiz, kategori)
    if sonuc and _kategori_uygun(sonuc, kategori):
        return sonuc

    # 3. sessions/
    sonuc = _notes_kontrol(hedef_temiz)
    if sonuc and _kategori_uygun(sonuc, kategori):
        sonuc.setdefault("guven_skoru", 0.6)
        sonuc.setdefault("kategori", kategori or "genel")
        sonuc.setdefault("gecerlilik_tarihi", _varsayilan_gecerlilik())
        return sonuc

    # 4. .ReYMeN/memories/
    sonuc = _memories_klasor_kontrol(hedef_temiz)
    if sonuc and _kategori_uygun(sonuc, kategori):
        sonuc.setdefault("guven_skoru", 0.6)
        sonuc.setdefault("kategori", kategori or "genel")
        sonuc.setdefault("gecerlilik_tarihi", _varsayilan_gecerlilik())
        return sonuc

    # 5. skills/
    sonuc = _skills_kontrol(hedef_temiz)
    if sonuc and _kategori_uygun(sonuc, kategori):
        sonuc.setdefault("guven_skoru", 0.8)
        sonuc.setdefault("kategori", kategori or "genel")
        sonuc.setdefault("gecerlilik_tarihi", _varsayilan_gecerlilik())
        return sonuc

    return None


def _kategori_uygun(sonuc: dict, kategori: str) -> bool:
    """Kategori filtresi: kategori boşsa her şey uygun, doluysa eşleşmeli."""
    if not kategori:
        return True
    kayit_kategori = (sonuc.get("kategori") or "").lower()
    return kategori.lower() in kayit_kategori or kayit_kategori in kategori.lower()


# ══════════════════════════════════════════════════════════════════════════
# 4. KAYDET_ISLE — otomatik guven_skoru hesaplamalı kaydetme
# ══════════════════════════════════════════════════════════════════════════

def kaydet_isle(
    hedef: str,
    kategori: str,
    sonuc_bilgisi: str,
    basarili: bool = True,
) -> dict:
    """Bir işlem sonucunu hafızaya kaydet, otomatik guven_skoru hesapla.

    Parametre:
        hedef:          Görev metni
        kategori:       Kategori ("kali/network")
        sonuc_bilgisi:  Ne yapıldı / sonuç özeti
        basarili:       Başarılı mı?

    Dönüş:
        {"durum": "kaydedildi", "guven_skoru": 0.85, ...}
    """
    if not _GOREV_HAFIZA_AKTIF or not gorev_sonrasi_hafiza:
        return {"durum": "pasif", "sebep": "gorev_hafiza modulu yok"}

    try:
        import uuid
        task_id = str(uuid.uuid4())[:8]
        sonuc_dict = {
            "basarili": basarili,
            "yanit": sonuc_bilgisi[:1000],
            "hata": None,
            "sure": 0,
            "turlar": 1,
            "kategori": kategori,
        }
        kayit = gorev_sonrasi_hafiza(task_id, hedef, sonuc_dict, kategori=kategori)
        return {
            "durum": "kaydedildi",
            "guven_skoru": _guven_skoru(1 if basarili else 0, 0 if basarili else 1),
            "task_id": task_id,
            "kategori": kategori,
        }
    except Exception as e:
        return {"durum": "hata", "sebep": str(e)}


# ══════════════════════════════════════════════════════════════════════════
# KONTROL STRATEJİLERİ (5 katman)
# ══════════════════════════════════════════════════════════════════════════

def _soul_kontrol(hedef: str) -> Optional[dict]:
    """1. SOUL.md → Öğrenilenler bölümünden eşleşme ara."""
    try:
        if not SOUL_PATH.exists():
            return None

        icerik = SOUL_PATH.read_text(encoding="utf-8", errors="replace")

        ogrenilenler_idx = icerik.find("## Öğrenilenler")
        if ogrenilenler_idx == -1:
            return None

        ogrenilenler = icerik[ogrenilenler_idx:]
        kelimeler = [k for k in hedef.split() if len(k) > 2]

        for satir in ogrenilenler.split("\n"):
            satir = satir.strip()
            if not satir.startswith("- ["):
                continue

            satir_lower = satir.lower()
            eslesme = sum(1 for k in kelimeler if k in satir_lower)
            esik = max(1, len(kelimeler) // 3)

            if eslesme >= esik:
                tarih = ""
                tarih_m = re.search(r"\[(\d{4}-\d{2}-\d{2})\]", satir)
                if tarih_m:
                    tarih = tarih_m.group(1)

                return {
                    "bulundu": True,
                    "kaynak": "SOUL.md",
                    "icerik": satir.strip(),
                    "detay": f"Daha önce işlenmiş ({eslesme}/{len(kelimeler)} kelime)",
                    "tarih": tarih,
                    "eslesme_orani": round(eslesme / max(len(kelimeler), 1), 2),
                }

        return None
    except Exception as e:
        log.warning("SOUL.md kontrol hatasi: %s", e)
        return None


def _memory_db_kontrol(hedef: str, kategori: str = "") -> Optional[dict]:
    """2. SQLite hafıza DB'sinden FTS5 ile eşleşme ara.
    
    Gelişmiş: metadata'dan guven_skoru, kategori, gecerlilik_tarihi çeker.
    """
    if not _HAFIZA_AKTIF or not _hafiza:
        return _session_db_kontrol(hedef, kategori)

    try:
        sonuclar = _hafiza.ara(
            sorgu=hedef[:200],
            koleksiyon="konusmalar",
            limit=10,
        )

        if not sonuclar:
            return None

        # Kategori filtresini metadata üzerinden uygula
        for doc in sonuclar:
            doc_kategori = (doc.get("kategori") or "").lower()

            # Kategori filtresi
            if kategori and kategori.lower() not in doc_kategori and doc_kategori not in kategori.lower():
                continue

            # gecerlilik kontrolü
            gec_tarih = doc.get("gecerlilik_tarihi", "")
            if gec_tarih:
                gec_durum = _gecerlilik_kontrol(gec_tarih)
                if gec_durum == "gecersiz":
                    continue  # güncel olmayan bilgiyi gösterme

            # guven_skoru
            guven = float(doc.get("guven_skoru", 0.5))
            if guven < 0.3:
                continue  # çok düşük güvenli bilgiyi es geç

            return {
                "bulundu": True,
                "kaynak": "memory_db",
                "icerik": str(doc.get("icerik", ""))[:300],
                "guven_skoru": guven,
                "kategori": doc.get("kategori", kategori or "genel"),
                "gecerlilik_tarihi": gec_tarih,
                "kayit_id": doc.get("id"),
                "detay": f"FTS5 eşleşmesi (guven: {guven})",
                "tarih": str(doc.get("zaman", ""))[:10],
            }

        return None

    except Exception as e:
        log.warning("Memory DB kontrol hatasi: %s", e)
        return None


def _session_db_kontrol(hedef: str, kategori: str = "") -> Optional[dict]:
    """Session DB (SQLite) üzerinden FTS5 arama."""
    if not _SESSION_DB_AKTIF or not _SessionStorage:
        return None

    try:
        storage = _SessionStorage()
        sonuclar = storage.ara(hedef[:200], limit=5)

        if not sonuclar:
            return None

        en_iyi = sonuclar[0]
        return {
            "bulundu": True,
            "kaynak": "session_db",
            "icerik": str(en_iyi.get("content", ""))[:300],
            "guven_skoru": 0.5,
            "kategori": kategori or "genel",
            "gecerlilik_tarihi": _varsayilan_gecerlilik(),
            "kayit_id": None,
            "detay": f"Session DB eşleşmesi (session: {en_iyi.get('session_id', '?')})",
            "tarih": str(en_iyi.get("created_at", ""))[:10],
        }

    except Exception as e:
        log.warning("Session DB kontrol hatasi: %s", e)
        return None


def _notes_kontrol(hedef: str) -> Optional[dict]:
    """.ReYMeN/notes/sessions/ dosyalarında eşleşme ara."""
    try:
        if not NOTES_SESSIONS.exists():
            return None

        kelimeler = [k for k in hedef.split() if len(k) > 2]
        dosyalar = sorted(NOTES_SESSIONS.glob("*.md"), reverse=True)[:30]

        en_iyi = None
        en_yuksek = 0

        for dosya in dosyalar:
            try:
                icerik = dosya.read_text(encoding="utf-8", errors="replace")
                baslik = ""
                baslik_m = re.search(r"\*\*Başlık:\*\*\s*(.+)", icerik)
                if baslik_m:
                    baslik = baslik_m.group(1).strip().lower()

                icerik_lower = icerik.lower()
                eslesme = sum(1 for k in kelimeler if k in icerik_lower)

                if eslesme > en_yuksek:
                    en_yuksek = eslesme
                    en_iyi = (dosya, baslik, icerik[:500])
            except Exception:
                continue

        esik = max(1, len(kelimeler) // 3)
        if en_iyi and en_yuksek >= esik:
            dosya, baslik, icerik_ilk = en_iyi
            return {
                "bulundu": True,
                "kaynak": f"notes/sessions/{dosya.name}",
                "icerik": f"**{baslik}** — {icerik_ilk[:200]}",
                "detay": f"Session dosyası eşleşmesi ({en_yuksek}/{len(kelimeler)} kelime)",
                "tarih": dosya.stem.split("_")[1][:8] if "_" in dosya.stem else "",
            }

        return None
    except Exception as e:
        log.warning("Notes kontrol hatasi: %s", e)
        return None


def _memories_klasor_kontrol(hedef: str) -> Optional[dict]:
    """.ReYMeN/memories/ klasöründe eşleşme ara."""
    try:
        if not MEMORIES_DIR.exists():
            return None

        kelimeler = [k for k in hedef.split() if len(k) > 2]
        dosyalar = sorted(MEMORIES_DIR.glob("*.md"), reverse=True)[:30]

        en_iyi = None
        en_yuksek = 0

        for dosya in dosyalar:
            try:
                icerik = dosya.read_text(encoding="utf-8", errors="replace")
                icerik_lower = icerik.lower()
                eslesme = sum(1 for k in kelimeler if k in icerik_lower)

                if eslesme > en_yuksek:
                    en_yuksek = eslesme
                    en_iyi = (dosya, icerik[:300])
            except Exception:
                continue

        esik = max(1, len(kelimeler) // 3)
        if en_iyi and en_yuksek >= esik:
            dosya, icerik = en_iyi
            return {
                "bulundu": True,
                "kaynak": f"memories/{dosya.name}",
                "icerik": icerik[:200],
                "detay": f"Memory dosyası eşleşmesi ({en_yuksek}/{len(kelimeler)} kelime)",
                "tarih": "",
            }

        return None
    except Exception as e:
        log.warning("Memories kontrol hatasi: %s", e)
        return None


def _skills_kontrol(hedef: str) -> Optional[dict]:
    """.ReYMeN/skills/ klasöründe eşleşme ara."""
    try:
        if not SKILLS_DIR.exists():
            return None

        kelimeler = [k for k in hedef.split() if len(k) > 2]
        dosyalar = sorted(SKILLS_DIR.glob("*.md"), reverse=True)[:30]

        en_iyi = None
        en_yuksek = 0

        for dosya in dosyalar:
            try:
                icerik = dosya.read_text(encoding="utf-8", errors="replace")
                icerik_lower = icerik.lower()
                eslesme = sum(1 for k in kelimeler if k in icerik_lower)

                if eslesme > en_yuksek:
                    en_yuksek = eslesme
                    en_iyi = (dosya, icerik[:300])
            except Exception:
                continue

        esik = max(1, len(kelimeler) // 2)
        if en_iyi and en_yuksek >= esik:
            dosya, icerik = en_iyi
            return {
                "bulundu": True,
                "kaynak": f"skills/{dosya.name}",
                "icerik": icerik[:200],
                "detay": f"Skill eşleşmesi ({en_yuksek}/{len(kelimeler)} kelime)",
                "tarih": "",
            }

        return None
    except Exception as e:
        log.warning("Skills kontrol hatasi: %s", e)
        return None


# ══════════════════════════════════════════════════════════════════════════
# CROSS-AGENT DESTEĞİ
# ══════════════════════════════════════════════════════════════════════════

def cross_agent_ekle(ajan_adi: str, proje_koku: str = ""):
    """Başka bir ajanın hafıza klasörünü taramaya ekle.

    Kullanım:
        cross_agent_ekle("Kali", "/home/kali/hermes_projesi")

    Her ajan kendi .AjanAdi/notes/ dizinine baksın.
    """
    if not ajan_adi:
        return

    if proje_koku:
        ajan_yolu = Path(proje_koku) / f".{ajan_adi}" / "notes" / "sessions"
    else:
        ajan_yolu = PROJE.parent / f".{ajan_adi}" / "notes" / "sessions"

    if ajan_yolu.exists():
        _CROSS_AGENT_DIRS.append((ajan_adi, ajan_yolu))
        log.info("Cross-agent eklendi: %s → %s", ajan_adi, ajan_yolu)
    else:
        log.warning("Cross-agent dizini bulunamadi: %s", ajan_yolu)


def cross_agent_tara(hedef: str) -> List[dict]:
    """Tüm eklenmiş cross-agent klasörlerinde ara."""
    sonuclar = []
    kelimeler = [k for k in hedef.split() if len(k) > 2]

    for ajan_adi, ajan_yolu in _CROSS_AGENT_DIRS:
        try:
            for dosya in sorted(ajan_yolu.glob("*.md"), reverse=True)[:10]:
                icerik = dosya.read_text(encoding="utf-8", errors="replace")
                eslesme = sum(1 for k in kelimeler if k in icerik.lower())
                if eslesme >= len(kelimeler) // 3:
                    sonuclar.append({
                        "ajan": ajan_adi,
                        "kaynak": f"{ajan_adi}/{dosya.name}",
                        "icerik": icerik[:300],
                        "eslesme": eslesme,
                    })
        except Exception:
            continue

    return sonuclar


# ══════════════════════════════════════════════════════════════════════════
# DURUM ÖZETİ
# ══════════════════════════════════════════════════════════════════════════

def hafiza_durum_ozet() -> dict:
    """Hafıza durum özeti."""
    durum: dict = {
        "SOUL.md": SOUL_PATH.exists() if SOUL_PATH else False,
        "memory_db": _HAFIZA_AKTIF,
        "session_db": _SESSION_DB_AKTIF,
        "notes_sessions": NOTES_SESSIONS.exists() if NOTES_SESSIONS else False,
        "memories_dir": MEMORIES_DIR.exists() if MEMORIES_DIR else False,
        "skills_dir": SKILLS_DIR.exists() if SKILLS_DIR else False,
        "cross_agent": len(_CROSS_AGENT_DIRS),
    }
    durum["api"] = {
        "isle": True,
        "hafizada_ara": True,
        "kaydet_isle": True,
        "cross_agent_tara": True,
    }
    durum["diger_bilgiler"] = (
        f"Hafiza {sum(1 for k, v in durum.items() if isinstance(v, bool) and v)}/6 aktif, "
        f"{durum['cross_agent']} cross-agent"
    )
    return durum
