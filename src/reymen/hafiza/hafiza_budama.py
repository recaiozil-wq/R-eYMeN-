# -*- coding: utf-8 -*-
"""
hafiza_budama.py — Otomatik Hafıza Budama ve Temizleme.

Ne yapar:
  1. ReYMeN MEMORY.md girişlerini tara
  2. Eski/tekrarlanan/gereksiz entry'leri temizle
  3. Benzer entry'leri birleştir
  4. ReYMeN SQLite hafızasındaki eski kayıtları temizle (TTL)
  5. .ReYMeN/memories/ içindeki 7+ günlük dosyaları temizle
  6. Cron job ile otomatik çalıştırma

Kullanim:
    python hafiza_budama.py              # Tam budama
    python hafiza_budama.py --dry-run    # Ne olacagini goster, uygulama
"""

import json
import logging
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# ── Ayarlar ──────────────────────────────────────────────────────────────

# MEMORY entry yaşam süreleri (gün)
GUNLUK_GOREV_TTL = 3          # Günlük görev entry'leri 3 gün sonra temizlenir
HAFIZA_ENTRY_TTL = 14         # Genel hafıza entry'leri 14 gün sonra temizlenir
KURAL_TTL = 90                # Kalıcı kurallar 90 gün sonra gözden geçirilir
DOSYA_TTL = 7                 # .ReYMeN/memories/ dosyaları 7 gün

# Budama eşikleri
MAX_ENTRY_KARAKTER = 200      # Bir entry max 200 karakter (fazlası kesilir)
MAX_BENZERLIK_ESIK = 0.6     # Benzerlik oranı > %60 ise birleştir
MIN_BOSLUK = 500              # Budama sonrası en az 500 karakter boşluk bırak

# Yollar
PROJE = Path(__file__).parent.resolve()
REYMEN_MEMORIES = Path("C:\\Users\\marko\\AppData\\Local\\hermes\\profiles\\reymen\\memories")
REYMEN_CONFIG = Path("C:\\Users\\marko\\AppData\\Local\\hermes\\config.yaml")
REYMEN_DB = Path(str(PROJE) + "\\.reymen_hafiza\\hafiza.db")

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════
# 1. REYMEN MEMORY BUDA
# ══════════════════════════════════════════════════════════════════════════

def reymen_memory_buda(dry_run: bool = False) -> dict:
    """ReYMeN MEMORY.md ve USER.md'deki entry'leri buda.

    Args:
        dry_run: True = sadece rapor, False = uygula

    Returns:
        dict: Budama raporu
    """
    rapor = {
        "memory": {"onceki": 0, "sonra": 0, "silinen": 0, "birlestirilen": 0},
        "user": {"onceki": 0, "sonra": 0, "silinen": 0},
        "toplam_kazanc": 0,
    }

    # MEMORY.md
    mem_path = REYMEN_MEMORIES / "MEMORY.md"
    if mem_path.exists():
        onceki, sonra = _memory_dosyasi_buda(mem_path, dry_run)
        rapor["memory"]["onceki"] = onceki
        rapor["memory"]["sonra"] = sonra
        rapor["memory"]["silinen"] = onceki - sonra

    # USER.md
    user_path = REYMEN_MEMORIES / "USER.md"
    if user_path.exists():
        onceki, sonra = _memory_dosyasi_buda(user_path, dry_run)
        rapor["user"]["onceki"] = onceki
        rapor["user"]["sonra"] = sonra
        rapor["user"]["silinen"] = onceki - sonra

    rapor["toplam_kazanc"] = (
        (rapor["memory"]["onceki"] - rapor["memory"]["sonra"]) +
        (rapor["user"]["onceki"] - rapor["user"]["sonra"])
    )
    return rapor


def _memory_dosyasi_buda(dosya_yolu: Path, dry_run: bool) -> tuple:
    """Bir memory dosyasini buda.

    Returns:
        (onceki_satir_sayisi, sonraki_satir_sayisi)
    """
    try:
        icerik = dosya_yolu.read_text(encoding="utf-8")
    except Exception:
        return 0, 0

    onceki_satir = len(icerik.split("\n"))
    onceki_char = len(icerik)

    # Entry'leri ayir (bos satirla ayrilmis bloklar)
    entryler = _entryleri_ayir(icerik)
    onceki_entry = len(entryler)

    # Temizleme
    yeni_entryler = _entryleri_temizle(entryler)

    # Birleştirme
    yeni_entryler = _entryleri_birlestir(yeni_entryler)

    # Yeni içerik (§ ile ayrilmis)
    yeni_icerik = ("\n§\n".join(yeni_entryler)).strip()
    if yeni_icerik:
        yeni_icerik += "\n"

    if not dry_run:
        try:
            dosya_yolu.write_text(yeni_icerik, encoding="utf-8")
        except Exception as e:
            logger.error("Yazma hatasi %s: %s", dosya_yolu, e)

    sonraki_char = len(yeni_icerik)
    print(f"  {dosya_yolu.name}: {onceki_entry} entry → {len(yeni_entryler)} entry"
          f" ({onceki_char} → {sonraki_char} karakter, {onceki_char - sonraki_char} kazanc)"
          + (" [DRY RUN]" if dry_run else ""))

    return onceki_entry, len(yeni_entryler)


def _entryleri_ayir(icerik: str) -> list[str]:
    """İçeriği ayrı entry'lere böl (§ ile ayrilmis)."""
    entryler = []
    for blok in icerik.strip().split("§"):
        blok = blok.strip()
        if blok and len(blok) > 5:  # Çok kısa entry'leri atla
            entryler.append(blok)
    return entryler


def _entryleri_temizle(entryler: list[str]) -> list[str]:
    """Eski/gereksiz entry'leri temizle, kısa olanları boyutlandır."""
    yeni = []
    for e in entryler:
        e = e.strip()
        if not e:
            continue

        # Çok kısa entry'leri atla (< 15 karakter)
        if len(e) < 15:
            continue

        # Sadece tarih/sayı entry'lerini atla
        if re.match(r'^[\d\s\-:./,]+$', e):
            continue

        # "test" veya "deneme" içeren çok kısa entry'leri atla
        if len(e) < 30 and re.search(r'test|deneme|örnek|ornek', e, re.IGNORECASE):
            continue

        # Eski tamamlanmış görev kayıtlarını temizle
        # (içinde "fix:", "düzeltildi", "tamamlandı", "görev bitti" varsa
        #  ve 200 karakterden kısaysa → atlanabilir)
        if len(e) < MAX_ENTRY_KARAKTER and _gorev_entry_mi(e):
            continue  # Eski görev entry'si, atla

        # Uzun entry'leri kısalt (fazla detayı kes)
        if len(e) > MAX_ENTRY_KARAKTER * 2:
            e = e[:MAX_ENTRY_KARAKTER * 2] + "..."

        yeni.append(e)

    return yeni


def _gorev_entry_mi(metin: str) -> bool:
    """Bir entry'nin eski bir görev kaydı olup olmadığını kontrol et."""
    gorev_isaretleri = [
        "fix:", "düzeltildi", "duzeltildi", "tamamlandi", "tamamlandı",
        "görev bitti", "gorev bitti", "cozuldu", "çözüldü",
        "eklendi", "kaldirildi", "kaldırıldı", "guncellendi", "güncellendi",
        "test gecti", "test geçti", "basarili", "başarılı",
        "gorev_id", "task_id", "commit", "push edildi", "merged",
    ]
    metin_lower = metin.lower()
    return any(isaret in metin_lower for isaret in gorev_isaretleri)


def _entryleri_birlestir(entryler: list[str]) -> list[str]:
    """Benzer entry'leri birleştir."""
    if len(entryler) < 2:
        return entryler

    yeni = []
    kullanilan = set()

    for i, e1 in enumerate(entryler):
        if i in kullanilan:
            continue

        benzerler = [e1]
        kullanilan.add(i)

        for j, e2 in enumerate(entryler):
            if j in kullanilan or j <= i:
                continue
            if _benzerlik_orani(e1, e2) > MAX_BENZERLIK_ESIK:
                benzerler.append(e2)
                kullanilan.add(j)

        if len(benzerler) > 1:
            # Birleştir: en kısa açıklamayı koru
            en_kisa = min(benzerler, key=len)
            # Kategori adını al (iki nokta üstüste öncesi)
            kategori = en_kisa.split(":")[0] if ":" in en_kisa else ""
            if kategori:
                # Tüm değerleri topla
                degerler = set()
                for b in benzerler:
                    if ":" in b:
                        degerler.add(b.split(":", 1)[1].strip())
                yeni.append(f"{kategori}: {'; '.join(sorted(degerler))}")
            else:
                yeni.append(en_kisa)
        else:
            yeni.append(e1)

    return yeni


def _benzerlik_orani(s1: str, s2: str) -> float:
    """İki string arasındaki benzerlik oranı (0.0 - 1.0)."""
    # Aynı kelimelerin oranı
    kelimeler1 = set(re.findall(r'\w+', s1.lower()))
    kelimeler2 = set(re.findall(r'\w+', s2.lower()))
    if not kelimeler1 or not kelimeler2:
        return 0.0
    kesisim = kelimeler1 & kelimeler2
    toplam = kelimeler1 | kelimeler2
    return len(kesisim) / len(toplam)


# ══════════════════════════════════════════════════════════════════════════
# 2. REYMEN SQLITE HAFIZA BUDA
# ══════════════════════════════════════════════════════════════════════════

def reymen_hafiza_buda(dry_run: bool = False) -> dict:
    """ReYMeN SQLite hafızasındaki eski kayıtları temizle.

    Args:
        dry_run: True = sadece rapor

    Returns:
        dict: Temizlik raporu
    """
    rapor = {"toplam": 0, "silinen": 0, "koleksiyonlar": {}}
    db_yolu = REYMEN_DB

    if not db_yolu.exists():
        print("  ReYMeN SQLite hafiza DB bulunamadi.")
        return rapor

    try:
        conn = sqlite3.connect(str(db_yolu))
        c = conn.cursor()

        # Koleksiyon bazında kayıt sayıları
        rows = c.execute("SELECT koleksiyon, COUNT(*) FROM kayitlar GROUP BY koleksiyon").fetchall()
        for koleksiyon, sayi in rows:
            rapor["toplam"] += sayi
            rapor["koleksiyonlar"][koleksiyon] = {"onceki": sayi, "silinen": 0}

        # 1. Expire zamanı geçmiş kayıtları sil
        simdi = time.time()
        c.execute("DELETE FROM kayitlar WHERE expire_zaman > 0 AND expire_zaman < ?", (simdi,))
        silinen_expire = c.rowcount

        # 2. Konuşma kayıtları: 14 günden eski olanları temizle (son 50 kayıt hariç)
        # Her session için son 50 mesajı koru, öncesini sil
        sessions = c.execute("SELECT DISTINCT session_id FROM kayitlar WHERE koleksiyon='konusmalar'").fetchall()
        session_based = 0
        for (sid,) in sessions:
            # Session'daki toplam kayıt
            toplam_session = c.execute(
                "SELECT COUNT(*) FROM kayitlar WHERE session_id=? AND koleksiyon='konusmalar'",
                (sid,)
            ).fetchone()[0]
            if toplam_session > 50:
                # Son 50 kaydın ID'sini bul
                c.execute(
                    """SELECT id FROM kayitlar
                       WHERE session_id=? AND koleksiyon='konusmalar'
                       ORDER BY id DESC LIMIT 50""",
                    (sid,)
                )
                korunacak = [row[0] for row in c.fetchall()]
                if korunacak:
                    placeholders = ",".join("?" for _ in korunacak)
                    c.execute(
                        f"""DELETE FROM kayitlar
                            WHERE session_id=? AND koleksiyon='konusmalar'
                            AND id NOT IN ({placeholders})""",
                        (sid, *korunacak)
                    )
                    session_based += c.rowcount

        # 3. Session kayıtlarını temizle (bitmiş ve 14+ günlük)
        eski_session = c.execute(
            """SELECT s.id FROM sessions s
               WHERE s.bitis > 0 AND s.bitis < ?""",
            (simdi - GUNLUK_GOREV_TTL * 86400,)
        ).fetchall()

        for (sid,) in eski_session:
            c.execute("DELETE FROM kayitlar WHERE session_id=?", (sid,))
            c.execute("DELETE FROM sessions WHERE id=?", (sid,))

        toplam_silinen = silinen_expire + session_based + len(eski_session)

        if not dry_run:
            conn.commit()

            # Koleksiyon bazında güncel sayılar
            rows = c.execute("SELECT koleksiyon, COUNT(*) FROM kayitlar GROUP BY koleksiyon").fetchall()
            for koleksiyon, sayi in rows:
                if koleksiyon in rapor["koleksiyonlar"]:
                    onceki = rapor["koleksiyonlar"][koleksiyon]["onceki"]
                    rapor["koleksiyonlar"][koleksiyon]["sonra"] = sayi
                    rapor["koleksiyonlar"][koleksiyon]["silinen"] = onceki - sayi

        conn.close()

        rapor["silinen"] = toplam_silinen
        print(f"  ReYMeN SQLite: {rapor['toplam']} kayit → {toplam_silinen} silindi"
              + (" [DRY RUN]" if dry_run else ""))

    except Exception as e:
        print(f"  SQLite budama hatasi: {e}")

    return rapor


# ══════════════════════════════════════════════════════════════════════════
# 3. MEMORY DOSYALARINI TEMIZLE
# ══════════════════════════════════════════════════════════════════════════

def memory_dosyalarini_temizle(dry_run: bool = False) -> dict:
    """.ReYMeN/memories/ içindeki eski dosyaları temizle.

    Args:
        dry_run: True = sadece rapor

    Returns:
        dict: Temizlik raporu
    """
    rapor = {"toplam": 0, "silinen": 0, "kb_kazanc": 0}
    mem_dizini = PROJE / ".ReYMeN" / "memories"

    if not mem_dizini.exists():
        return rapor

    simdi = time.time()
    kesme = simdi - DOSYA_TTL * 86400  # 7 gün

    for f in sorted(mem_dizini.glob("*")):
        if not f.is_file():
            continue
        rapor["toplam"] += 1

        # Gorev logları hariç her şeyi temizle (gorev_ = her zaman koru)
        if f.name.startswith("gorev_"):
            continue
        # session_20260620.md gibi ana session loglarını koru
        if f.name == "session_20260620.md":
            continue

        try:
            mtime = f.stat().st_mtime
            if mtime < kesme:
                boyut = f.stat().st_size
                rapor["kb_kazanc"] += boyut
                if not dry_run:
                    f.unlink()
                rapor["silinen"] += 1
        except OSError as _hafiza_b_e389:
            print(f"[UYARI] hafiza_budama.py:390 - {_hafiza_b_e389}")

    rapor["kb_kazanc"] = round(rapor["kb_kazanc"] / 1024, 1)
    print(f"  .ReYMeN/memories/: {rapor['toplam']} dosyadan {rapor['silinen']} silindi"
          f" ({rapor['kb_kazanc']} KB kazanc)"
          + (" [DRY RUN]" if dry_run else ""))
    return rapor


# ══════════════════════════════════════════════════════════════════════════
# 4. ANA BUDA FONKSIYONU
# ══════════════════════════════════════════════════════════════════════════

def buda(dry_run: bool = False) -> dict:
    """Tüm hafıza sistemlerini buda.

    Args:
        dry_run: True = sadece raporla, uygulama

    Returns:
        dict: Kapsamlı budama raporu
    """
    print(f"\n{'=' * 60}")
    print(f"  HAFIZA BUDA {'(DRY RUN - sadece rapor)' if dry_run else ''}")
    print(f"{'=' * 60}")
    print(f"  Baslama: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  TTL: gorev={GUNLUK_GOREV_TTL}g, hafiza={HAFIZA_ENTRY_TTL}g, dosya={DOSYA_TTL}g")

    baslama = time.time()

    # 1. ReYMeN memory
    print(f"\n[1/3] ReYMeN memory budama...")
    h_rapor = reymen_memory_buda(dry_run)

    # 2. ReYMeN SQLite
    print(f"\n[2/3] ReYMeN SQLite budama...")
    r_rapor = reymen_hafiza_buda(dry_run)

    # 3. .ReYMeN/memories/ dosyaları
    print(f"\n[3/3] Memory dosyasi temizleme...")
    d_rapor = memory_dosyalarini_temizle(dry_run)

    sure = round(time.time() - baslama, 2)
    toplam_kazanc = h_rapor.get("toplam_kazanc", 0) + r_rapor.get("silinen", 0) + d_rapor.get("silinen", 0)

    print(f"\n{'=' * 60}")
    print(f"  BUDA TAMAMLANDI ({sure}s)")
    print(f"  ReYMeN MEMORY: {h_rapor.get('memory', {}).get('silinen', 0)} entry temizlendi"
          f" ({h_rapor.get('toplam_kazanc', 0)} karakter kazanc)")
    print(f"  ReYMeN SQLite: {r_rapor.get('silinen', 0)} kayit temizlendi")
    print(f"  Eski dosyalar: {d_rapor.get('silinen', 0)} dosya temizlendi"
          f" ({d_rapor.get('kb_kazanc', 0)} KB)")
    print(f"  Toplam kazanc: {toplam_kazanc} birim")
    print(f"{'=' * 60}")

    return {
        "reymen": h_rapor,
        "reymen_sqlite": r_rapor,
        "dosyalar": d_rapor,
        "sure_sn": sure,
        "toplam_kazanc": toplam_kazanc,
    }


# ══════════════════════════════════════════════════════════════════════════
# 5. CRON ICIN ORNEK
# ══════════════════════════════════════════════════════════════════════════

def cron_budama_gorevi():
    """Cron job olarak çağrılmak üzere budama görevi.

    Bu fonksiyon her gün çalıştırılacak şekilde cronjob'a eklenebilir:
        cronjob(action='create', schedule='0 3 * * *',
                prompt='Hafiza budama cron gorevini calistir',
                skills=['reymen-gorev-hafiza'])
    """
    try:
        sonuc = buda(dry_run=False)
        print(f"[CRON] Hafiza budama tamam: {sonuc.get('toplam_kazanc', 0)} birim temizlendi")
        return sonuc
    except Exception as e:
        print(f"[CRON] Hafiza budama hatasi: {e}")
        return {"hata": str(e)}


# ══════════════════════════════════════════════════════════════════════════
# CALISTIRMA
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    cron_mode = "--cron" in sys.argv

    if cron_mode:
        cron_budama_gorevi()
    else:
        buda(dry_run=dry_run)
