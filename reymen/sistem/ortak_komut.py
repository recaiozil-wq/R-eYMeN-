# -*- coding: utf-8 -*-
"""
ortak_komut.py — 3 bot + ReYMeN Agent ortak yetki/komut merkezi.
Her degisiklikte otomatik guncellenir. Tum botlar burayi okur.
"""

import json
import os
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

PROJE_KOK = Path(__file__).resolve().parent.parent.parent
HERMES_HOME = Path.home() / ".hermes"

# ── Bot Profil Yapilari ────────────────────────────────────────────────

BOTLAR = {
    "pasa_38": {
        "profil": "default",
        "bot_adi": "@Pasa_38_bot",
        "gateway": "aktif",
        "yetki": "tam",
        "browser": "acik",
        "terminal": "acik",
        "web": "firecrawl",
        "soul_boyut": 0,
        "tools": "tum",
    },
    "reymen": {
        "profil": "reymen",
        "bot_adi": "@ReYMeN_ReYMeNbot",
        "gateway": "aktif",
        "yetki": "tam",
        "browser": "acik",
        "terminal": "acik",
        "web": "firecrawl",
        "soul_boyut": 0,
        "tools": "tum",
    },
    "kiral38": {
        "profil": "kiral38",
        "bot_adi": "@Kiral38bot",
        "gateway": "aktif",
        "yetki": "tam",
        "browser": "acik",
        "terminal": "acik",
        "web": "firecrawl",
        "soul_boyut": 0,
        "tools": "tum",
    },
}

# ── Ortak Komutlar ─────────────────────────────────────────────────────

ORTAK_KOMUTLAR = {
    "cevap_formati": "emoji+baslik+tablo+yorum",
    "dil": "Turkce",
    "cave_modu": True,
    "no_goblins": True,
    "side_quest": "sub_agent'a yonlendir",
    "durum_oku_zorunlu": True,
    "kendi_bilgisiyle_cevap_yasak": True,
    "kaynak": "durum.json TEK KAYNAK",
    "reasoning_core_aktif": True,
}

# ── Dosya Yollari ──────────────────────────────────────────────────────

SOUL_DOSYALARI = {
    "default": HERMES_HOME / "profiles" / "default" / "SOUL.md",
    "reymen": HERMES_HOME / "profiles" / "reymen" / "SOUL.md",
    "kiral38": HERMES_HOME / "profiles" / "kiral38" / "SOUL.md",
}

CONFIG_DOSYALARI = {
    "default": HERMES_HOME / "profiles" / "default" / "config.yaml",
    "reymen": HERMES_HOME / "profiles" / "reymen" / "config.yaml",
    "kiral38": HERMES_HOME / "profiles" / "kiral38" / "config.yaml",
}

DURUM_JSON = PROJE_KOK / "durum.json"


# ── Tarama Fonksiyonu ──────────────────────────────────────────────────

def tara_profil(profil: str) -> dict:
    """Bir profilin guncel durumunu tara."""
    sonuc = {"soul_boyut": 0, "browser": "?", "terminal_cwd": "?"}

    # SOUL.md boyutu
    soul_yol = SOUL_DOSYALARI.get(profil)
    if soul_yol and soul_yol.exists():
        sonuc["soul_boyut"] = soul_yol.stat().st_size

    # Config'den browser/terminal bilgisi
    config_yol = CONFIG_DOSYALARI.get(profil)
    if config_yol and config_yol.exists():
        icerik = config_yol.read_text(encoding="utf-8")
        # Browser durumu: disabled_toolsets listesinde "browser" var mi?
        import re as _re
        dt_match = _re.search(r'disabled_toolsets\s*:\s*\[(.*?)\]', icerik, _re.DOTALL)
        if dt_match:
            tools = [t.strip().strip("'\"") for t in dt_match.group(1).split(",") if t.strip()]
            sonuc["browser"] = "kapali" if "browser" in tools else "acik"
        else:
            sonuc["browser"] = "acik"
        # Terminal cwd
        for satir in icerik.split("\n"):
            if "cwd:" in satir:
                sonuc["terminal_cwd"] = satir.split("cwd:")[-1].strip().strip("'\"")
                break

    return sonuc


def guncelle() -> dict:
    """Tum profilleri tara, BOTLAR'i guncelle, durum.json'a yaz.
    
    Dinamik olarak eklenen botlari (yeni kullanicinin kendi botu gibi)
    korur — sadece hardcoded BOTLAR'daki botlari degil, durum.json'da
    zaten kayitli olan tum botlari muhafaza eder.
    """
    # Mevcut durum.json'u oku (dinamik botlari korumak icin)
    mevcut_botlar = {}
    if DURUM_JSON.exists():
        try:
            mevcut = json.loads(DURUM_JSON.read_text(encoding="utf-8"))
            mevcut_botlar = mevcut.get("botlar", {})
        except Exception:
            mevcut_botlar = {}

    # Hardcoded BOTLAR'i guncelle (profil durumlarini tara)
    for ad, bot in BOTLAR.items():
        durum = tara_profil(bot["profil"])
        bot["soul_boyut"] = durum["soul_boyut"]
        bot["browser"] = durum["browser"]

    # Hardcoded ve dinamik botlari birlestir
    # Hardcoded botlar kendi ayarlarini korur
    # Dinamik botlar (hardcoded'da olmayan) oldugu gibi kalir
    birlesik_botlar = dict(BOTLAR)  # hardcoded'lar
    for anahtar, deger in mevcut_botlar.items():
        if anahtar not in birlesik_botlar:
            birlesik_botlar[anahtar] = deger  # dinamik botlari ekle

    # durum.json'u guncelle
    yeni_durum = {
        "proje": "ReYMeN Agent",
        "surum": "2026-06-30",
        "botlar": birlesik_botlar,
        "ortak_komutlar": ORTAK_KOMUTLAR,
        "reasoning_core": {
            "durum": "entegre",
            "merkezi_db": "analitik.db",
            "tablo": "reasoning_log",
            "provider_config": "config.yaml > fallback_providers > reasoning-core-*",
            "model_local": "Ornith-1.0-9B (LM Studio)",
            "model_openrouter": "deepreinforce-ai/ornith-1.0-397b",
            "durum_oku_zorunlulugu": "evet",
        },
        "esit_mi": _butun_botlar_esit_mi(),
    }

    DURUM_JSON.write_text(
        json.dumps(yeni_durum, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    return yeni_durum


def _butun_botlar_esit_mi() -> dict:
    """Tum botlarin (hardcoded + dinamik) ayni yetkide olup olmadigini kontrol et.
    Sadece permission/settings alanlarini karsilastir (profil/bot_adi haric).
    soul_boyut: 50 byte'dan az fark esit sayilir (bot ismi uzunlugu)."""
    karsilastirilacak_alanlar = [
        "gateway", "yetki", "browser", "terminal",
        "web", "tools",
    ]
    # Mevcut durum.json'daki tum botlari al (hardcoded + dinamik)
    butun_botlar = dict(BOTLAR)
    if DURUM_JSON.exists():
        try:
            mevcut = json.loads(DURUM_JSON.read_text(encoding="utf-8"))
            for anahtar, deger in mevcut.get("botlar", {}).items():
                if anahtar not in butun_botlar:
                    butun_botlar[anahtar] = deger
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")
    yetkiler = [
        [b.get(alan, "") for alan in karsilastirilacak_alanlar]
        for b in butun_botlar.values()
    ]
    if not yetkiler:
        return {"esit": True, "aciklama": "Henuz bot yok"}
    ilk = yetkiler[0]
    esit = all(y == ilk for y in yetkiler)
    # Ayrica soul_boyut farki 50 bayti gecmemeli
    boyutlar = [b.get("soul_boyut", 0) for b in butun_botlar.values()]
    if esit and boyutlar:
        min_boyut = min(boyutlar)
        max_boyut = max(boyutlar)
        if max_boyut - min_boyut > 50:
            esit = False
    return {
        "esit": esit,
        "aciklama": "Tum botlar esit" if esit else "Fark var! (soul_boyut farki > 50 bayt veya yetki farki)",
    }


# ── CLI ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "tara":
        for ad in BOTLAR:
            d = tara_profil(BOTLAR[ad]["profil"])
            print(f"{ad}: SOUL={d['soul_boyut']}b, Browser={d['browser']}, CWD={d['terminal_cwd']}")
    elif len(sys.argv) > 1 and sys.argv[1] == "guncelle":
        sonuc = guncelle()
        print(f"✅ durum.json guncellendi. Botlar esit mi: {sonuc['esit_mi']['esit']}")
    else:
        print("Kullanim: python ortak_komut.py [tara|guncelle]")
# ════════════════════════════════════════════════════════════════════
# AŞAĞIDAKİ BLOK reymen/sistem/ortak_komut.py DOSYASININ SONUNA EKLENECEK
# ════════════════════════════════════════════════════════════════════
#
# NOT: ortak_komut.py'nin mevcut içeriği elimde değildi (zip'te yoktu),
# bu yüzden bu blok var olan importlarla çakışmayacak şekilde kendi
# import'larını kendi taşıyor. Dosyayı elle eklerken proje kökünde
# zaten tanımlıysa aşağıdaki tekrar eden import'ları (json, sqlite3,
# time, logging, requests) silip dosyanın başındaki mevcut bloğa
# taşıyabilirsin — davranış değişmez.

import json
import logging
import sqlite3
import time
from datetime import datetime, timezone

import requests

from reymen.sistem.db_config import DB

logger = logging.getLogger(__name__)

# ── Reasoning-Core sağlayıcı seçimi config.yaml > fallback_providers'tan
#    okunur; burada sabit kodlanmıyor ki tek kaynak config.yaml kalsın.
_REASONING_PROVIDER_ADI = "reasoning-core"


def _analitik_db_hazirla() -> None:
    """analitik.db'de reasoning_log tablosu yoksa oluşturur (idempotent)."""
    with sqlite3.connect(DB["analitik"]) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reasoning_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zaman TEXT NOT NULL,
                bot_adi TEXT,
                tetikleyen_hata TEXT,
                durum_ozeti TEXT,
                dusunce_zinciri TEXT,
                cozum TEXT,
                model TEXT,
                sure_sn REAL
            )
            """
        )
        conn.commit()


def _reasoning_core_cagir(prompt: str, fallback_providers: list[dict], timeout: int = 60) -> dict:
    """config.yaml > fallback_providers içindeki 'reasoning-core' girdisini
    bulup OpenAI-uyumlu chat/completions isteği atar.

    Ornith-1.0 ailesi (bkz. deep-reinforce.com/ornith_1_0.html) yanıtı
    <think>...</think> bloğuyla açar ve sunucu tarafında reasoning-parser
    açıksa bunu ayrı bir `reasoning_content` alanında döner. Bu fonksiyon
    her iki durumu da (ayrı alan / metin içi <think>) destekler.
    """
    provider_cfg = next(
        (p for p in fallback_providers if p.get("provider", "").startswith(_REASONING_PROVIDER_ADI)),
        None,
    )
    if provider_cfg is None:
        raise RuntimeError(
            "config.yaml > fallback_providers içinde 'reasoning-core*' ile "
            "başlayan bir sağlayıcı bulunamadı. Önce config.yaml'ı güncelle."
        )

    base_url = provider_cfg["base_url"].rstrip("/")
    model = provider_cfg["model"]
    api_key = provider_cfg.get("api_key", "not-needed")  # yerel sunucuda genelde gerekmez

    t0 = time.time()
    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.6,   # Ornith-1.0 önerilen sampling (bkz. HF model kartı)
            "top_p": 0.95,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    veri = resp.json()
    sure = time.time() - t0

    mesaj = veri["choices"][0]["message"]
    dusunce = mesaj.get("reasoning_content")
    icerik = mesaj.get("content", "")

    if not dusunce and "<think>" in icerik:
        # Sunucu reasoning-parser'sız çalışıyorsa <think> bloğu content
        # içine gömülü gelir; burada ayıklanıyor.
        try:
            dusunce = icerik.split("<think>", 1)[1].split("</think>", 1)[0].strip()
            icerik = icerik.split("</think>", 1)[1].strip()
        except IndexError:
            dusunce = None

    return {"cozum": icerik, "dusunce_zinciri": dusunce, "model": model, "sure_sn": round(sure, 2)}


def reasoning_loop(
    hata_metni: str,
    durum_ozeti: str,
    bot_adi: str,
    fallback_providers: list[dict],
) -> dict:
    """Bir hata oluştuğunda çağrılan otonom akış:

        1) durum_ozeti (DURUM_OKU() çıktısı) + hata_metni birlikte
           Reasoning-Core'a gönderilir.
        2) Dönen düşünce zinciri (CoT) ve çözüm ayrıştırılır.
        3) Sonuç analitik.db > reasoning_log tablosuna yazılır.

    SOUL.md > 'DURUM_OKU() ZORUNLULUĞU' kuralı gereği bu fonksiyon
    durum_ozeti'ni KENDİSİ üretmez — çağıran taraf (ör. hata yakalama
    handler'ı) önce DURUM_OKU() çağırıp sonucu buraya parametre olarak
    geçirmelidir. Bu fonksiyon durum_ozeti boşsa çalışmayı reddeder,
    aksi halde kural ihlal edilmiş olur.
    """
    if not durum_ozeti or not durum_ozeti.strip():
        raise ValueError(
            "reasoning_loop çağrılmadan önce DURUM_OKU() çalıştırılmalı ve "
            "sonucu durum_ozeti parametresine verilmeli (SOUL.md kuralı)."
        )

    _analitik_db_hazirla()

    prompt = (
        "Aşağıda bir yazılım sisteminde oluşan hata ve mevcut sistem "
        "durumu veriliyor. Kök nedeni adım adım analiz et, sonra somut "
        "bir çözüm öner.\n\n"
        f"--- SİSTEM DURUMU (DURUM_OKU) ---\n{durum_ozeti}\n\n"
        f"--- HATA ---\n{hata_metni}\n"
    )

    try:
        sonuc = _reasoning_core_cagir(prompt, fallback_providers)
    except Exception as exc:  # noqa: BLE001 — burada geniş yakalama kasıtlı:
        # Reasoning-Core ulaşılamaz olsa bile ana bot akışı çökmemeli,
        # config.yaml > fallback_providers zaten bir sonraki sağlayıcıya
        # düşecek şekilde tasarlanmıştı; burada sadece logluyoruz.
        logger.warning("reasoning_loop: Reasoning-Core çağrısı başarısız: %s", exc)
        return {"basarili": False, "hata": str(exc)}

    kayit = {
        "zaman": datetime.now(timezone.utc).isoformat(),
        "bot_adi": bot_adi,
        "tetikleyen_hata": hata_metni,
        "durum_ozeti": durum_ozeti,
        "dusunce_zinciri": sonuc["dusunce_zinciri"],
        "cozum": sonuc["cozum"],
        "model": sonuc["model"],
        "sure_sn": sonuc["sure_sn"],
    }

    with sqlite3.connect(DB["analitik"]) as conn:
        conn.execute(
            """
            INSERT INTO reasoning_log
                (zaman, bot_adi, tetikleyen_hata, durum_ozeti,
                 dusunce_zinciri, cozum, model, sure_sn)
            VALUES (:zaman, :bot_adi, :tetikleyen_hata, :durum_ozeti,
                    :dusunce_zinciri, :cozum, :model, :sure_sn)
            """,
            kayit,
        )
        conn.commit()

    logger.info(
        "reasoning_loop: %s botunda hata çözümü %ss içinde analitik.db'ye kaydedildi.",
        bot_adi, kayit["sure_sn"],
    )
    return {"basarili": True, **kayit}
