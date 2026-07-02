#!/usr/bin/env python3
"""
cron_skill_sync.py — Skills → OnceHafiza DB senkronizasyonu.
Her 6 saatte bir çalışır.

- skills/ altındaki tüm .md dosyalarını tara
- skills_index.db (FTS5) + beceriler_meta tablosuyla karşılaştır
- Eksikleri ekle, değişenleri güncelle
- Rapor: kaç yeni, kaç güncellendi
"""

import hashlib
import logging
import sqlite3
import time
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("cron_skill_sync")

ROOT = Path(__file__).parent.resolve()
SKILLS_DIR = ROOT / "skills"
DB_PATH = ROOT / ".ReYMeN" / "skills_index.db"
DECISIONS_LOG = ROOT / ".ReYMeN" / "cron" / "skill_sync_log.md"


def dosya_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def db_baglan() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), timeout=30)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.executescript("""
        CREATE TABLE IF NOT EXISTS beceriler_meta (
            ad TEXT PRIMARY KEY,
            dosya_hash TEXT DEFAULT '',
            guncelleme TEXT DEFAULT (datetime('now'))
        );
    """)
    con.commit()
    return con


def normalize_path(p: str) -> str:
    return p.replace("\\", "/")


def tum_skills_dosyalari() -> list[dict]:
    dosyalar = []
    for p in sorted(SKILLS_DIR.rglob("*.md")):
        if not p.is_file():
            continue
        rel_path = normalize_path(str(p.relative_to(SKILLS_DIR)))
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            content = ""
        dosyalar.append({
            "ad": rel_path,
            "aciklama": rel_path,
            "icerik": content,
            "kaynak": str(p),
            "dosya_hash": dosya_hash(content),
        })
    return dosyalar


def existing_meta(con: sqlite3.Connection) -> dict[str, dict]:
    try:
        cur = con.execute("SELECT ad, dosya_hash, guncelleme FROM beceriler_meta")
        return {r[0]: {"ad": r[0], "dosya_hash": r[1] or "", "guncelleme": r[2] or ""}
                for r in cur.fetchall()}
    except Exception:
        return {}


def existing_fts5_ads(con: sqlite3.Connection) -> set[str]:
    try:
        cur = con.execute("SELECT ad FROM beceriler")
        return set(r[0] for r in cur.fetchall())
    except Exception:
        return set()


def log_kaydet(yeni: int, guncellenen: int, hata: int, detay: str):
    DECISIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"""
## Sync — {ts}

| Metrik | Değer |
|--------|-------|
| 🆕 Yeni | {yeni} |
| 🔄 Güncellenen | {guncellenen} |
| ❌ Hata | {hata} |

{detay}
"""
    if DECISIONS_LOG.exists():
        existing = DECISIONS_LOG.read_text(encoding="utf-8")
        lines = existing.split("\n## Sync")
        if len(lines) > 50:
            lines = lines[-50:]
        existing = "\n## Sync".join(lines)
        DECISIONS_LOG.write_text(existing + entry, encoding="utf-8")
    else:
        DECISIONS_LOG.write_text(entry, encoding="utf-8")


def main() -> dict:
    basla = time.time()
    logger.info("=== Skill Sync Başladı ===")
    logger.info("Skills: %s | DB: %s", SKILLS_DIR, DB_PATH)

    dosyalar = tum_skills_dosyalari()
    logger.info("Toplam .md dosyası: %d", len(dosyalar))

    if not dosyalar:
        logger.warning("Hiç .md dosyası bulunamadı!")
        return {"yeni": 0, "guncellenen": 0, "hata": 0, "toplam": 0}

    con = db_baglan()
    meta = existing_meta(con)
    fts5_ads = existing_fts5_ads(con)
    logger.info("Meta kayıt: %d | FTS5 kayıt: %d", len(meta), len(fts5_ads))

    yeni_say = 0
    guncel_say = 0
    hata_say = 0

    for dosya in dosyalar:
        ad = dosya["ad"]
        try:
            mevcut_hash = meta.get(ad, {}).get("dosya_hash", "")
            if dosya["dosya_hash"] == mevcut_hash:
                continue

            # FTS5 — DELETE + INSERT (FTS5 doesn't support UPDATE directly)
            if ad in fts5_ads:
                con.execute("DELETE FROM beceriler WHERE ad = ?", (ad,))
            con.execute(
                "INSERT INTO beceriler (ad, aciklama, icerik, kaynak) VALUES (?, ?, ?, ?)",
                (ad, dosya["aciklama"], dosya["icerik"], dosya["kaynak"]),
            )

            # Meta güncelle
            con.execute(
                "INSERT OR REPLACE INTO beceriler_meta (ad, dosya_hash, guncelleme) VALUES (?, ?, datetime('now'))",
                (ad, dosya["dosya_hash"]),
            )

            if ad in meta:
                guncel_say += 1
            else:
                yeni_say += 1

        except Exception as e:
            hata_say += 1
            logger.error("❌ Hata [%s]: %s", ad, e)

    con.commit()
    con.close()

    sure = time.time() - basla

    ozet = (
        f"- **İşlem süresi:** {sure:.1f}s\n"
        f"- **Toplam dosya:** {len(dosyalar)}\n"
        f"- **Meta kayıt (öncesi):** {len(meta)}\n"
        f"- **FTS5 kayıt (öncesi):** {len(fts5_ads)}\n"
        f"- **Yeni eklenen:** {yeni_say}\n"
        f"- **Güncellenen:** {guncel_say}\n"
        f"- **Hata:** {hata_say}\n"
    )
    log_kaydet(yeni_say, guncel_say, hata_say, ozet)

    logger.info("=== Tamamlandı: +%d yeni, ~%d güncel, %d hata (%.1fs) ===",
                yeni_say, guncel_say, hata_say, sure)

    return {
        "yeni": yeni_say,
        "guncellenen": guncel_say,
        "hata": hata_say,
        "toplam": len(dosyalar),
        "sure": round(sure, 1),
    }


if __name__ == "__main__":
    sonuc = main()
    print(f"\n📊 RAPOR: {sonuc['yeni']} yeni + {sonuc['guncellenen']} güncellendi "
          f"({sonuc['hata']} hata) — {sonuc['sure']}s")
