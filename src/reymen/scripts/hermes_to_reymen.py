#!/usr/bin/env python3
"""
hermes_to_reymen.py — ReYMeN state.db → ReYMeN hafiza toplu import.

124 session, 9078 mesaj → ReYMeN's hafiza.db + notes/sessions/ + skills/
"""

import json
import logging
import sqlite3
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Yollar ──────────────────────────────────────────────────────────────
HERMES_DB = Path.home() / "AppData/Local/hermes/state.db"
PROJE = Path(r"C:\Users\marko\Desktop\Reymen Proje\hermes_projesi")
REYMEN_DB = PROJE / ".reymen_hafiza" / "hafiza.db"
NOTES_DIR = PROJE / ".ReYMeN" / "notes" / "sessions"
MEMORIES_DIR = PROJE / ".ReYMeN" / "memories"
SKILLS_DIR = PROJE / ".ReYMeN" / "skills"

NOTES_DIR.mkdir(parents=True, exist_ok=True)
MEMORIES_DIR.mkdir(parents=True, exist_ok=True)

# ── ReYMeN hafiza modulu ────────────────────────────────────────────────
sys.path.insert(0, str(PROJE))
try:
    from hafiza_genislet import hafiza as _hafiza
    from gorev_hafiza import gorev_sonrasi_hafiza
    HAZIR = True
except ImportError:
    try:
        from reymen.hafiza.hafiza_genislet import hafiza as _hafiza
        from reymen.hafiza.gorev_hafiza import gorev_sonrasi_hafiza
        HAZIR = True
    except ImportError as e:
        log.error("Import hatasi: %s", e)
        HAZIR = False
        _hafiza = None
        gorev_sonrasi_hafiza = None


def _guven_skoru(basari: int, hata: int) -> float:
    toplam = basari + hata
    return round(basari / toplam, 3) if toplam > 0 else 0.5


def kategori_bul(hedef: str, title: str = "") -> str:
    """Metinden kategori tespiti."""
    h = (hedef + " " + title).lower()
    if any(k in h for k in ["nmap", "kali", "metasploit", "port", "sızma"]):
        return "kali"
    if any(k in h for k in ["dron", "drone", "px4", "uav"]):
        return "dron"
    if any(k in h for k in ["cad", "solidworks", "autocad", "3d"]):
        return "cad"
    if any(k in h for k in ["windows", "ekran", "mouse", "klavye"]):
        return "windows"
    if any(k in h for k in ["power bi", "powerbi", "mcp"]):
        return "powerbi"
    if any(k in h for k in ["test", "pytest", "unittest"]):
        return "test"
    return "genel"


def session_notu_al(session, messages) -> str:
    """Session'dan kısa bir kazanım notu çıkar."""
    title = session.get("title") or ""
    source = session.get("source") or ""
    msg_count = len(messages)
    cost = session.get("estimated_cost_usd") or 0

    # Kullanıcı mesajlarını özetle
    user_msgs = [m["content"][:200] for m in messages if m["role"] == "user" and m.get("content")]

    satirlar = [
        f"# Session Kazanımı",
        f"**Başlık:** {title}",
        f"**Kaynak:** {source}",
        f"**Mesaj:** {msg_count} adet",
        f"**Maliyet:** ${cost:.4f}",
    ]

    if user_msgs:
        satirlar.append("\n## Kullanıcı Soruları")
        for i, m in enumerate(user_msgs[:5], 1):
            satirlar.append(f"{i}. {m[:100]}")

    return "\n".join(satirlar)


def ilerleme_goster(current, total, width=40):
    """İlerleme çubuğu."""
    done = int(width * current / total)
    bar = "█" * done + "░" * (width - done)
    sys.stdout.write(f"\r  [{bar}] {current}/{total} ({current*100//total}%)")
    sys.stdout.flush()


def main():
    if not HAZIR:
        log.error("ReYMeN hafiza modulleri yuklenemedi, cikiliyor.")
        return

    if not HERMES_DB.exists():
        log.error("ReYMeN DB bulunamadi: %s", HERMES_DB)
        return

    # ── 1. ReYMeN DB'den session'lari oku ────────────────────────────
    log.info("ReYMeN DB okunuyor: %s (%.0f MB)", HERMES_DB, HERMES_DB.stat().st_size / 1e6)

    conn = sqlite3.connect(str(HERMES_DB))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM sessions ORDER BY started_at ASC")
    sessions = [dict(row) for row in c.fetchall()]
    log.info("Toplam %d session bulundu", len(sessions))

    # ── 2. Zaten işlenmiş session ID'lerini çıkar ────────────────────
    _hafiza.initialize("hermes_import", baslik="ReYMeN→ReYMeN toplu import")
    islenmis = set()

    # ReYMeN DB'de kayitli session_id'leri tara
    try:
        conn2 = sqlite3.connect(str(REYMEN_DB))
        c2 = conn2.cursor()
        c2.execute("SELECT DISTINCT session_id FROM kayitlar WHERE session_id LIKE 'hermes_%'")
        islenmis = {row[0] for row in c2.fetchall()}
        conn2.close()
    except Exception:
        logger.warning("[fix_01_sessiz_except] Exception")

    log.info("Daha once islenmis: %d session", len(islenmis))

    # ── 3. Her session'u isle ────────────────────────────────────────
    islenen = 0
    atlanan = 0
    baslangic = time.time()

    for idx, session in enumerate(sessions):
        session_id = session.get("id", "")
        
        # Zaten islenmis mi?
        hermes_key = f"hermes_{session_id[:16]}"
        if hermes_key in islenmis:
            atlanan += 1
            continue

        # Mesajlari cek
        c.execute(
            "SELECT * FROM messages WHERE session_id=? AND active=1 ORDER BY timestamp ASC",
            (session_id,),
        )
        messages = [dict(row) for row in c.fetchall()]

        if not messages:
            atlanan += 1
            continue

        title = session.get("title") or "İsimsiz Session"
        source = session.get("source") or "ReYMeN"
        msg_count = len(messages)

        # ── Notes dosyasi yaz ────────────────────────────────────────
        dosya_adi = f"session_import_{idx:04d}_{session_id[:8]}.md"
        dosya_yolu = NOTES_DIR / dosya_adi

        user_hedefleri = []
        for m in messages:
            if m["role"] == "user" and m.get("content"):
                user_hedefleri.append(m["content"][:500])

        ana_hedef = user_hedefleri[0] if user_hedefleri else title
        kategori = kategori_bul(ana_hedef, title)

        # Kazanim notu
        kazanim = session_notu_al(session, messages)
        
        # Tum konusma
        konusma = ""
        for m in messages:
            role = m["role"]
            content = (m.get("content") or "")[:500]
            tool_name = m.get("tool_name") or ""
            
            if role == "user":
                konusma += f"\n### user\n{content}\n"
            elif role == "assistant":
                tc = m.get("tool_calls") or ""
                konusma += f"\n### assistant\n{content}\n"
                if tc:
                    konusma += f"*(tool_calls: {str(tc)[:200]})*\n"
            elif role == "tool":
                konusma += f"\n### tool ({tool_name})\n{str(content)[:300]}\n"

        dosya_icerik = f"""# Session: hermes_import_{idx:04d}_{session_id[:8]}

**Başlık:** {title}
**Kategori:** {kategori}
**Kaynak:** {source}
**Mesaj Sayısı:** {msg_count}
**Tarih:** {datetime.fromtimestamp(session.get("started_at", 0)).strftime("%Y-%m-%d %H:%M") if session.get("started_at") else "?"}

---

{kazanim}

---

## Konuşma
{konusma}
"""
        dosya_yolu.write_text(dosya_icerik, encoding="utf-8")

        # ── ReYMeN hafizasina kaydet ─────────────────────────────────
        for i, m in enumerate(messages):
            role = m["role"]
            content = (m.get("content") or "").strip()
            if not content:
                continue

            anahtar = f"hermes_{session_id[:8]}_{i:04d}"

            if role == "user":
                _hafiza.kaydet(
                    icerik=content[:1000],
                    koleksiyon="konusmalar",
                    anahtar=anahtar,
                    metadata={
                        "session_id": hermes_key,
                        "role": "user",
                        "kategori": kategori,
                        "guven_skoru": 0.5,
                        "son_kullanim": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "gecerlilik_tarihi": (
                            datetime.now().replace(year=datetime.now().year + 1)
                            .strftime("%Y-%m-%d")
                        ),
                        "kullanim_sayisi": 0,
                        "basari_sayisi": 0,
                        "hata_sayisi": 0,
                    },
                )
            elif role == "assistant" and content:
                _hafiza.kaydet(
                    icerik=content[:1000],
                    koleksiyon="konusmalar",
                    anahtar=anahtar,
                    metadata={
                        "session_id": hermes_key,
                        "role": "assistant",
                        "kategori": kategori,
                        "guven_skoru": 0.7,
                    },
                )

        # ── Beceri koleksiyonuna ekle (ilk kullanici hedefi) ──────────
        if user_hedefleri:
            _hafiza.kaydet(
                icerik=f"**{title}**: {user_hedefleri[0][:300]}",
                koleksiyon="beceriler",
                anahtar=f"skill_{session_id[:8]}",
                metadata={
                    "kategori": kategori,
                    "guven_skoru": 0.7,
                    "son_kullanim": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "gecerlilik_tarihi": (
                        datetime.now().replace(year=datetime.now().year + 1)
                        .strftime("%Y-%m-%d")
                    ),
                    "kullanim_sayisi": 0,
                    "basari_sayisi": 1,
                    "hata_sayisi": 0,
                },
            )

        islenen += 1
        ilerleme_goster(idx + 1, len(sessions))

    # ── 4. Session bitir ──────────────────────────────────────────────
    _hafiza.session_bitir(
        ozet=f"ReYMeN→ReYMeN import: {islenen} yeni + {atlanan} atlanan session"
    )

    # ── 5. Istatistik ────────────────────────────────────────────────
    sure = time.time() - baslangic
    print()
    log.info("=" * 60)
    log.info("IMPORT TAMAMLANDI")
    log.info("  Yeni islenen: %d session", islenen)
    log.info("  Atlanan (onceki): %d session", atlanan)
    log.info("  Toplam: %d session", len(sessions))
    log.info("  Sure: %.1f sn (%.1f sn/session)", sure, sure / max(islenen, 1))
    log.info("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
