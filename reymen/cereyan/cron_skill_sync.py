#!/usr/bin/env python3
"""
cron_skill_sync.py — Skills → OnceHafiza DB senkronizasyonu.
Her 6 saatte bir calisir (cron job).

- skills/ altindaki tum .md dosyalarini tara
- skills_index.db (FTS5) + beceriler_meta tablosuyla karsilastir
- Eksikleri ekle, degisenleri guncelle
- Rapor: kac yeni, kac guncellendi
"""

import hashlib
import json
import logging
import sqlite3
import sys
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
CRON_JOBS_PATH = ROOT.parent / ".ReYMeN" / "cron" / "jobs.json"


# Cron job kayit bilgisi
CRON_JOB_ID = "skill_sync_periodic"
CRON_SCHEDULE = "0 */6 * * *"
CRON_HUMAN = "every 6 hours"


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
    """Tum .md dosyalarini tara, icerik ve hash ile birlikte getir."""
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
    """Meta tablosundaki mevcut kayitlari al."""
    try:
        cur = con.execute("SELECT ad, dosya_hash, guncelleme FROM beceriler_meta")
        return {
            r[0]: {"ad": r[0], "dosya_hash": r[1] or "", "guncelleme": r[2] or ""}
            for r in cur.fetchall()
        }
    except Exception:
        return {}


def existing_fts5_ads(con: sqlite3.Connection) -> set[str]:
    """FTS5'teki mevcut ad'leri al."""
    try:
        cur = con.execute("SELECT ad FROM beceriler")
        return set(r[0] for r in cur.fetchall())
    except Exception:
        return set()


def log_kaydet(yeni: int, guncellenen: int, hata: int, detay: str):
    """Karar/log dosyasina kaydet, son 50 kaydi tut."""
    DECISIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"""
## Sync — {ts}

| Metrik | Deger |
|--------|-------|
| Yeni | {yeni} |
| Guncellenen | {guncellenen} |
| Hata | {hata} |

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
    logger.info("=== Skill Sync Basladi ===")
    logger.info("Skills: %s", SKILLS_DIR)
    logger.info("DB: %s", DB_PATH)

    dosyalar = tum_skills_dosyalari()
    logger.info("Toplam .md dosyasi: %d", len(dosyalar))

    if not dosyalar:
        logger.warning("Hic .md dosyasi bulunamadi!")
        return {"yeni": 0, "guncellenen": 0, "hata": 0, "toplam": 0}

    con = db_baglan()
    meta = existing_meta(con)
    fts5_ads = existing_fts5_ads(con)
    logger.info("Meta kayit: %d | FTS5 kayit: %d", len(meta), len(fts5_ads))

    yeni_say = 0
    guncel_say = 0
    hata_say = 0

    for dosya in dosyalar:
        ad = dosya["ad"]
        try:
            mevcut_hash = meta.get(ad, {}).get("dosya_hash", "")
            if dosya["dosya_hash"] == mevcut_hash:
                continue  # Degisiklik yok, atla

            # FTS5: DELETE + INSERT (FTS5 UPDATE desteklemez)
            if ad in fts5_ads:
                con.execute("DELETE FROM beceriler WHERE ad = ?", (ad,))
            con.execute(
                "INSERT INTO beceriler (ad, aciklama, icerik, kaynak) VALUES (?, ?, ?, ?)",
                (ad, dosya["aciklama"], dosya["icerik"], dosya["kaynak"]),
            )

            # Meta guncelle
            con.execute(
                "INSERT OR REPLACE INTO beceriler_meta (ad, dosya_hash, guncelleme) "
                "VALUES (?, ?, datetime('now'))",
                (ad, dosya["dosya_hash"]),
            )

            if ad in meta:
                guncel_say += 1
            else:
                yeni_say += 1

        except Exception as e:
            hata_say += 1
            logger.error("Hata [%s]: %s", ad, e)

    con.commit()
    con.close()

    sure = time.time() - basla

    ozet = (
        f"- Islem suresi: {sure:.1f}s\n"
        f"- Toplam dosya: {len(dosyalar)}\n"
        f"- Meta kayit (oncesi): {len(meta)}\n"
        f"- FTS5 kayit (oncesi): {len(fts5_ads)}\n"
        f"- Yeni eklenen: {yeni_say}\n"
        f"- Guncellenen: {guncel_say}\n"
        f"- Hata: {hata_say}\n"
    )
    log_kaydet(yeni_say, guncel_say, hata_say, ozet)

    logger.info("=== Tamamlandi: +%d yeni, ~%d guncel, %d hata (%.1fs) ===",
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
    print(f"\nRAPOR: {sonuc['yeni']} yeni + {sonuc['guncellenen']} guncellendi "
          f"({sonuc['hata']} hata) - {sonuc['sure']}s")


# ── Motor / Cron sistemine kayit ──────────────────────────────────────

def cron_job_kaydet() -> str:
    """Skill sync cron job'unu jobs.json'a kaydet."""
    import json
    sync_script = str(Path(__file__).resolve())
    komut = f"{sys.executable} {sync_script}"

    CRON_JOBS_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblar = {}
    if CRON_JOBS_PATH.exists():
        try:
            joblar = json.loads(CRON_JOBS_PATH.read_text(encoding="utf-8") or "{}")
        except (json.JSONDecodeError, Exception):
            joblar = {}

    joblar[CRON_JOB_ID] = {
        "komut": komut,
        "zaman": CRON_HUMAN,
        "cron": CRON_SCHEDULE,
        "aktif": True,
        "aciklama": "Skills FTS5 index senkronizasyonu",
        "kaynak": "cron_skill_sync.py",
        "olusturma": str(datetime.now()),
    }
    CRON_JOBS_PATH.write_text(
        json.dumps(joblar, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("[Cron] Skill sync job kaydedildi: %s (%s)", CRON_JOB_ID, CRON_HUMAN)
    return f"[Cron] Kaydedildi: {CRON_JOB_ID}"


def motor_kaydet(motor) -> bool:
    """Motor / plugin sistemi icin kayit fonksiyonu.
    
    Motor._plugin_moduller_yukle() tarafindan otomatik cagrilir.
    Skill sync cron job'unu kaydeder ve cron_skill_sync_register
    tool'unu motora ekler.
    """
    try:
        cron_job_kaydet()
        # Ayrica bir SKILL_SYNC tool'u ekle
        motor._plugin_arac_kaydet(
            "SKILL_INDEX_SYNC",
            lambda: cron_job_kaydet(),
            "Skills FTS5 index cron job'unu kaydet/goruntule",
        )
        return True
    except Exception as e:
        logger.warning("[Cron] motor_kaydet hatasi: %s", e)
        return False
