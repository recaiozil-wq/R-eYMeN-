# -*- coding: utf-8 -*-
"""db_config.py — Merkezi Veritabanı Yol Sabitleri.

DB_KONSOLIDASYON_RAPORU.md'de tespit edilen dağınıklığın (20+ DB dosyası,
7 kategori, ~230MB kopya) çözümü: tüm botların ve modüllerin tek bir
kaynaktan DB yolu okuması.

Kullanım:
    from reymen.sistem.db_config import DB

    conn = sqlite3.connect(DB["analitik"])

Not: Bu dosya sadece YOL tanımlar, bağlantı açmaz. Bağlantı açma/kapama
sorumluluğu çağıran modüldedir (özellikle thread/async ortamlarda
sqlite3 bağlantılarının paylaşılmaması gerekir).
"""

from pathlib import Path

# ── Tek merkez kök dizin (rapordaki "Önerilen Yapı" ile birebir) ──────
PROJE_KOK = Path(__file__).resolve().parents[2]  # reymen/sistem/ -> proje kökü
DB_KOK = PROJE_KOK / ".ReYMeN" / "db"
DB_KOK.mkdir(parents=True, exist_ok=True)

# ── Tüm botların (Pasa_38, Kiral38, ReYMeN_ReYMeNbot, DiscordBot) ─────
# ── ortak kullandığı tekil DB yolları ─────────────────────────────────
DB = {
    "session": DB_KOK / "session.db",
    "ogrenmeler": DB_KOK / "ogrenmeler.db",          # OnceHafiza
    "skills_index": DB_KOK / "skills_index.db",
    "hafiza": DB_KOK / "hafiza.db",
    "self_improve": DB_KOK / "self_improve.db",
    "continuous_learning": DB_KOK / "continuous_learning.db",
    "analitik": DB_KOK / "analitik.db",              # reasoning_loop kayıtları burada
    "karar": DB_KOK / "karar.db",
}


def db_yolu(anahtar: str) -> str:
    """Verilen mantıksal isim için DB dosya yolunu str olarak döner.

    Bilinmeyen bir anahtar istenirse KeyError fırlatır — sessizce yeni bir
    dosya türetmek, raporun tespit ettiği "kopya DB" sorununu tekrar
    üretir, bu yüzden burada kasıtlı olarak izin verilmiyor.
    """
    if anahtar not in DB:
        raise KeyError(
            f"'{anahtar}' tanımlı değil. Yeni bir DB kategorisi gerekiyorsa "
            f"önce DB_KONSOLIDASYON_RAPORU.md'yi ve bu dosyadaki DB sözlüğünü "
            f"güncelle, koddan doğrudan yol türetme."
        )
    return str(DB[anahtar])


__all__ = ["DB", "DB_KOK", "db_yolu"]
