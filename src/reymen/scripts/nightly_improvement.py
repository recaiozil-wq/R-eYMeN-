# -*- coding: utf-8 -*-
"""
nightly_improvement.py — ReYMeN Gece Kendini Geliştirme Döngüsü.

Her gece 03:00'te çalışır. 6 aşamalı sessiz döngü:

  a) once_hafiza analizi (zayıf noktalar)
  b) Skill iyileştirme (düşük başarılı skill'ler)
  c) Memory compaction kontrolü
  d) Kod kalitesi (ruff/bandit hataları)
  e) Cron job'ların durumu
  f) 7 günlük trend raporu

Raporu durum.json'a yazar. Sessiz çalışır, sadece sorun varsa raporlar.

Kullanım:
    python -m reymen.scripts.nightly_improvement
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Proje Yolları ───────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent.parent.parent  # proje kökü
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

DURUM_JSON = ROOT / "durum.json"
CRON_DIZINI = ROOT / ".ReYMeN" / "cron"
JOBS_JSON = CRON_DIZINI / "jobs.json"
RAPOR_DIZINI = ROOT / ".ReYMeN" / "nightly"
RAPOR_DIZINI.mkdir(parents=True, exist_ok=True)


# ── Veri Yapıları ───────────────────────────────────────────────────

@dataclass
class AsamaSonucu:
    """Tek bir aşamanın sonucu."""
    ad: str
    basarili: bool
    sure_sn: float = 0.0
    mesaj: str = ""
    veri: dict[str, Any] = field(default_factory=dict)
    uyari: bool = False  # True = kullanıcıya bildirilecek


@dataclass
class NightlyRapor:
    """6 aşamalı gece raporunun tamamı."""
    timestamp: str = ""
    asamalar: list[dict[str, Any]] = field(default_factory=list)
    toplam_sure_sn: float = 0.0
    basarili_asama: int = 0
    toplam_asama: int = 0
    uyari_var: bool = False
    trend: dict[str, Any] = field(default_factory=dict)
    ozet: str = ""


# ═══════════════════════════════════════════════════════════════════════
#  Aşama 1: once_hafiza Analizi (Zayıf Noktalar)
# ═══════════════════════════════════════════════════════════════════════

def _asama_once_hafiza() -> AsamaSonucu:
    """once_hafiza'daki zayıf noktaları tespit et.

    - Düşük güven skorlu (< 0.4) kayıtlar
    - Hiç başarılı olmamış hedefler
    - Sık hata alınan hedefler (hata_sayisi >= 3)
    """
    basla = time.time()
    sonuc = AsamaSonucu(ad="once_hafiza_analizi", basarili=True)

    try:
        from reymen.sistem.once_hafiza import OnceHafiza
        oh = OnceHafiza()

        import sqlite3

        # Öğrenme DB'den analiz
        ogrenme_db = oh.ogrenme_db
        zayif_noktalar = []

        if Path(ogrenme_db).exists():
            con = sqlite3.connect(ogrenme_db)
            con.row_factory = sqlite3.Row
            cur = con.cursor()

            # Tablo var mı kontrol et
            tablolar = cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            tablo_isimleri = [r["name"] for r in tablolar]

            if "ogrenmeler" in tablo_isimleri:
                # Kategori bazlı dağılım
                kategoriler = cur.execute(
                    "SELECT kategori, COUNT(*) as adet FROM ogrenmeler "
                    "WHERE kategori != '' GROUP BY kategori ORDER BY adet DESC"
                ).fetchall()

                # Düşük güven skorlu kayıtlar
                dusuk_guven = cur.execute(
                    "SELECT hedef, guven_skoru, basari_sayisi, hata_sayisi "
                    "FROM ogrenmeler WHERE guven_skoru < 0.4 "
                    "ORDER BY guven_skoru ASC LIMIT 10"
                ).fetchall()

                # Sık hata alınan hedefler
                cok_hata = cur.execute(
                    "SELECT hedef, hata_sayisi, basari_sayisi, guven_skoru "
                    "FROM ogrenmeler WHERE hata_sayisi >= 3 "
                    "ORDER BY hata_sayisi DESC LIMIT 10"
                ).fetchall()

                # Hiç başarılı olmamış
                sifir_basari = cur.execute(
                    "SELECT hedef, hata_sayisi "
                    "FROM ogrenmeler WHERE basari_sayisi = 0 AND hata_sayisi > 0 "
                    "ORDER BY hata_sayisi DESC LIMIT 10"
                ).fetchall()

                zayif_noktalar = {
                    "dusuk_guven": [
                        {"hedef": row["hedef"], "guven": row["guven_skoru"],
                         "basarili": row["basari_sayisi"], "hata": row["hata_sayisi"]}
                        for row in dusuk_guven
                    ],
                    "cok_hata": [
                        {"hedef": row["hedef"], "hata_sayisi": row["hata_sayisi"],
                         "basarili": row["basari_sayisi"], "guven": row["guven_skoru"]}
                        for row in cok_hata
                    ],
                    "sifir_basari": [
                        {"hedef": row["hedef"], "hata": row["hata_sayisi"]}
                        for row in sifir_basari
                    ],
                    "kategori_dagilimi": {
                        r["kategori"]: r["adet"] for r in kategoriler
                    },
                }

            con.close()

            # Özet
            toplam_zayif = (
                len(zayif_noktalar.get("dusuk_guven", []))
                + len(zayif_noktalar.get("cok_hata", []))
                + len(zayif_noktalar.get("sifir_basari", []))
            )

            mesaj = f"{toplam_zayif} zayif nokta bulundu"
            uyari = toplam_zayif > 5

            sonuc.mesaj = mesaj
            sonuc.veri = {"zayif_noktalar": zayif_noktalar, "toplam": toplam_zayif}
            sonuc.uyari = uyari
        else:
            sonuc.mesaj = "once_hafiza veritabani bulunamadi"
            sonuc.veri = {"db_yok": True}

    except Exception as e:
        sonuc.basarili = False
        sonuc.mesaj = f"[HATA] {e}"
        logger.warning("[Nightly] once_hafiza analizi hatasi: %s", e)

    sonuc.sure_sn = round(time.time() - basla, 2)
    return sonuc


# ═══════════════════════════════════════════════════════════════════════
#  Aşama 2: Skill İyileştirme (Düşük Başarılı Skill'ler)
# ═══════════════════════════════════════════════════════════════════════

def _asama_skill_iyilestirme() -> AsamaSonucu:
    """Düşük başarılı skill'leri tespit et ve iyileştir."""
    basla = time.time()
    sonuc = AsamaSonucu(ad="skill_iyilestirme", basarili=True)

    try:
        from reymen.scripts.skill_iyilestirici import SkillIyilestirici

        iyilestirici = SkillIyilestirici()
        adaylar = iyilestirici.iyilestirme_adaylari_bul()

        if adaylar:
            # Öncelikli iyileştir (oncelik >= 7)
            acil_adaylar = [a for a in adaylar if a.get("oncelik", 0) >= 7]
            iyilestirilen = 0
            for aday in acil_adaylar[:5]:
                try:
                    sonuc_iyi = iyilestirici.otomatik_iyilestir()
                    if isinstance(sonuc_iyi, dict):
                        iyilestirilen += sonuc_iyi.get("iyilestirilen", 1)
                    elif sonuc_iyi:
                        iyilestirilen += 1
                except Exception:
                    pass

            # Rapor
            tur_dagilimi = {}
            for a in adaylar:
                t = a.get("tur", "bilinmiyor")
                tur_dagilimi[t] = tur_dagilimi.get(t, 0) + 1

            mesaj = (
                f"{len(adaylar)} aday, {len(acil_adaylar)} acil, "
                f"{iyilestirilen} iyilestirildi"
            )
            uyari = len(acil_adaylar) > 3

            sonuc.veri = {
                "aday_sayisi": len(adaylar),
                "acil_aday": len(acil_adaylar),
                "iyilestirilen": iyilestirilen,
                "tur_dagilimi": tur_dagilimi,
                "aday_detay": [
                    {"skill": a.get("skill_adi"), "tur": a.get("tur"),
                     "oncelik": a.get("oncelik")}
                    for a in adaylar[:20]
                ],
            }
            sonuc.mesaj = mesaj
            sonuc.uyari = uyari
        else:
            sonuc.mesaj = "Iyilestirme adayi bulunamadi"
            sonuc.veri = {"aday_sayisi": 0}

    except ImportError:
        sonuc.basarili = False
        sonuc.mesaj = "[ATLANDI] skill_iyilestirici modulu yok"
    except Exception as e:
        sonuc.basarili = False
        sonuc.mesaj = f"[HATA] {e}"
        logger.warning("[Nightly] skill iyilestirme hatasi: %s", e)

    sonuc.sure_sn = round(time.time() - basla, 2)
    return sonuc


# ═══════════════════════════════════════════════════════════════════════
#  Aşama 3: Memory Compaction Kontrolü
# ═══════════════════════════════════════════════════════════════════════

def _asama_memory_compaction() -> AsamaSonucu:
    """Hafıza compaction kontrolü yap."""
    basla = time.time()
    sonuc = AsamaSonucu(ad="memory_compaction", basarili=True)

    try:
        from reymen.cereyan.memory_compaction import (
            memory_compaction_check
        )

        rapor = memory_compaction_check(zorla=False)

        if isinstance(rapor, dict):
            compaction_gerekli = rapor.get("compaction_gerekli", False)
            mevcut_yuzde = rapor.get("mevcut_yuzde", 0)
            budanan = rapor.get("budanan", 0)

            if compaction_gerekli:
                # Zorla compaction yap
                rapor_zorla = memory_compaction_check(zorla=True)
                if isinstance(rapor_zorla, dict):
                    budanan = rapor_zorla.get("budanan", 0)
                    mevcut_yuzde = rapor_zorla.get("mevcut_yuzde", 0)

            mesaj = (
                f"Doluluk: %{mevcut_yuzde:.0f}, compaction: "
                f"{'gerekli' if compaction_gerekli else 'gerekli degil'}, "
                f"budanan: {budanan}"
            )
            sonuc.uyari = compaction_gerekli
            sonuc.veri = {
                "mevcut_yuzde": mevcut_yuzde,
                "compaction_gerekli": compaction_gerekli,
                "budanan": budanan,
                "detay": rapor,
            }
            sonuc.mesaj = mesaj
        else:
            sonuc.mesaj = "Compaction kontrolu tamam"
            sonuc.veri = {"ham_rapor": str(rapor)[:200]}

    except ImportError:
        sonuc.basarili = False
        sonuc.mesaj = "[ATLANDI] memory_compaction modulu yok"
    except Exception as e:
        sonuc.basarili = False
        sonuc.mesaj = f"[HATA] {e}"
        logger.warning("[Nightly] memory compaction hatasi: %s", e)

    sonuc.sure_sn = round(time.time() - basla, 2)
    return sonuc


# ═══════════════════════════════════════════════════════════════════════
#  Aşama 4: Kod Kalitesi (ruff/bandit)
# ═══════════════════════════════════════════════════════════════════════

def _asama_kod_kalitesi() -> AsamaSonucu:
    """ruff ve bandit ile kod kalitesi taraması."""
    basla = time.time()
    sonuc = AsamaSonucu(ad="kod_kalitesi", basarili=True)

    bulgular = {"ruff": [], "bandit": [], "el_kurallari": []}
    hata_sayisi = 0

    try:
        # ── ruff kontrolü ──
        try:
            r = subprocess.run(
                [sys.executable, "-m", "ruff", "check", "--select=E,F,W", "--statistics",
                 str(SRC / "reymen")],
                capture_output=True, text=True, timeout=60,
            )
            if r.returncode != 0:
                for satir in r.stdout.strip().split("\n"):
                    if satir.strip() and "error" in satir.lower() or "E" in satir:
                        bulgular["ruff"].append(satir.strip()[:150])
                        hata_sayisi += 1
                # Sayıyı standart çıktıdan al
                import re as _re
                sayi_match = _re.search(r"Found (\d+) error", r.stdout)
                if sayi_match:
                    hata_sayisi = int(sayi_match.group(1))
        except FileNotFoundError:
            bulgular["ruff"] = ["ruff kurulu degil"]

        # ── bandit güvenlik taraması ──
        try:
            r = subprocess.run(
                [sys.executable, "-m", "bandit", "-r", "-q", str(SRC / "reymen")],
                capture_output=True, text=True, timeout=60,
            )
            if r.returncode != 0:
                for satir in r.stdout.strip().split("\n"):
                    if satir.strip() and ">>" in satir:
                        bulgular["bandit"].append(satir.strip()[:150])
        except FileNotFoundError:
            bulgular["bandit"] = ["bandit kurulu degil"]

        # ── El kuralları ──
        py_dosyalar = list(Path(SRC / "reymen").rglob("*.py"))
        for dosya in py_dosyalar:
            try:
                icerik = dosya.read_text(encoding="utf-8", errors="replace")
                satir_sayisi = len(icerik.split("\n"))

                # Bare except kontrolü
                if "except:" in icerik or "except :" in icerik:
                    bulgular["el_kurallari"].append(
                        f"{dosya.relative_to(SRC)}: bare except"
                    )

                # Import *
                if "import *" in icerik:
                    bulgular["el_kurallari"].append(
                        f"{dosya.relative_to(SRC)}: wildcard import"
                    )

                # TODO/FIXME (sadece 5'ten fazlaysa)
                todo_say = icerik.count("TODO") + icerik.count("FIXME")
                if todo_say > 5:
                    bulgular["el_kurallari"].append(
                        f"{dosya.relative_to(SRC)}: {todo_say} TODO/FIXME"
                    )

                # >800 satır
                if satir_sayisi > 800:
                    bulgular["el_kurallari"].append(
                        f"{dosya.relative_to(SRC)}: {satir_sayisi} satir (>800)"
                    )

            except Exception:
                continue

        toplam_bulgu = (
            len(bulgular["ruff"])
            + len(bulgular["bandit"])
            + len(bulgular["el_kurallari"])
        )
        kritik_sayisi = hata_sayisi + len(bulgular["bandit"])

        mesaj = (
            f"{toplam_bulgu} bulgu "
            f"(ruff: {hata_sayisi}, bandit: {len(bulgular['bandit'])}, "
            f"el_kurallari: {len(bulgular['el_kurallari'])})"
        )
        sonuc.uyari = kritik_sayisi > 0
        sonuc.veri = bulgular
        sonuc.mesaj = mesaj

    except Exception as e:
        sonuc.basarili = False
        sonuc.mesaj = f"[HATA] {e}"
        logger.warning("[Nightly] kod kalitesi tarama hatasi: %s", e)

    sonuc.sure_sn = round(time.time() - basla, 2)
    return sonuc


# ═══════════════════════════════════════════════════════════════════════
#  Aşama 5: Cron Job'ların Durumu
# ═══════════════════════════════════════════════════════════════════════

def _asama_cron_durumu() -> AsamaSonucu:
    """Kayıtlı cron job'larının durumunu kontrol et."""
    basla = time.time()
    sonuc = AsamaSonucu(ad="cron_durumu", basarili=True)

    try:
        # Önce yerel .ReYMeN/cron/jobs.json
        yerel_isler = []
        hermes_isler = []

        if JOBS_JSON.exists():
            try:
                veri = json.loads(JOBS_JSON.read_text(encoding="utf-8") or "{}")
                if isinstance(veri, dict):
                    for job_id, job in veri.items():
                        if isinstance(job, dict):
                            yerel_isler.append({
                                "id": job_id,
                                "ad": job.get("ad", ""),
                                "cron": job.get("cron", ""),
                                "aktif": job.get("aktif", True),
                                "son_durum": job.get("son_durum", "?"),
                                "son_hata": job.get("son_hata"),
                            })
            except Exception:
                pass

        # Hermes-style cron (jobs.py)
        try:
            from reymen.cron.jobs import list_jobs
            h_jobs = list_jobs(include_disabled=True)
            for j in h_jobs:
                hermes_isler.append({
                    "id": j.get("id", "?"),
                    "name": j.get("name", ""),
                    "schedule": j.get("schedule_display", ""),
                    "enabled": j.get("enabled", True),
                    "last_status": j.get("last_status"),
                    "last_error": j.get("last_error"),
                })
        except Exception:
            pass

        # Sorunlu job'ları tespit et
        sorunlu = []
        for isler, kaynak in [(yerel_isler, "yerel"),
                               (hermes_isler, "hermes")]:
            for j in isler:
                if not j.get("aktif", j.get("enabled", True)):
                    continue
                son_durum = j.get("son_durum") or j.get("last_status") or ""
                son_hata = j.get("son_hata") or j.get("last_error") or ""
                if "failed" in son_durum or "error" in son_durum or son_hata:
                    sorunlu.append({**j, "kaynak": kaynak})

        toplam_is = len(yerel_isler) + len(hermes_isler)
        mesaj = (
            f"{toplam_is} is, {len(sorunlu)} sorunlu"
        )

        sonuc.uyari = len(sorunlu) > 0
        sonuc.veri = {
            "toplam_is": toplam_is,
            "yerel_isler": yerel_isler,
            "hermes_isler": hermes_isler,
            "sorunlu_isler": sorunlu,
        }
        sonuc.mesaj = mesaj

    except Exception as e:
        sonuc.basarili = False
        sonuc.mesaj = f"[HATA] {e}"
        logger.warning("[Nightly] cron durumu kontrol hatasi: %s", e)

    sonuc.sure_sn = round(time.time() - basla, 2)
    return sonuc


# ═══════════════════════════════════════════════════════════════════════
#  Aşama 6: 7 Günlük Trend Raporu
# ═══════════════════════════════════════════════════════════════════════

def _asama_trend_raporu() -> AsamaSonucu:
    """Son 7 günlük performans trendini hesapla."""
    basla = time.time()
    sonuc = AsamaSonucu(ad="trend_raporu", basarili=True)

    try:
        simdi = time.time()
        yedi_gun_once = simdi - (7 * 86400)

        trend = {
            "donem": "son_7_gun",
            "once_hafiza": {"toplam_kayit": 0, "yeni_kayit": 0},
            "skill": {"kullanim": 0, "basarili": 0, "basarisiz": 0},
            "gece_raporlari": [],
        }

        # once_hafiza trendi
        try:
            from reymen.sistem.once_hafiza import OnceHafiza
            oh = OnceHafiza()
            ogrenme_db = oh.ogrenme_db

            if Path(ogrenme_db).exists():
                import sqlite3
                con = sqlite3.connect(ogrenme_db)
                row = con.execute(
                    "SELECT COUNT(*) FROM ogrenmeler"
                ).fetchone()
                trend["once_hafiza"]["toplam_kayit"] = row[0] if row else 0

                # Son 7 günde eklenen
                row = con.execute(
                    "SELECT COUNT(*) FROM ogrenmeler WHERE olusturulma >= ?",
                    (datetime.fromtimestamp(yedi_gun_once).isoformat(),),
                ).fetchone()
                trend["once_hafiza"]["yeni_kayit"] = row[0] if row else 0
                con.close()
        except Exception:
            pass

        # Skill iyileştirme trendi
        try:
            from reymen.scripts.skill_iyilestirici import SkillIyilestirici
            si = SkillIyilestirici()

            import sqlite3
            db_yol = ROOT / "skills" / "improvements.db"
            if db_yol.exists():
                con = sqlite3.connect(str(db_yol))
                row = con.execute(
                    "SELECT COUNT(*), "
                    "COALESCE(SUM(basarili), 0), "
                    "COUNT(*) - COALESCE(SUM(basarili), 0) "
                    "FROM kullanim_gecmisi WHERE timestamp >= ?",
                    (yedi_gun_once,),
                ).fetchone()
                if row:
                    trend["skill"]["kullanim"] = row[0]
                    trend["skill"]["basarili"] = row[1]
                    trend["skill"]["basarisiz"] = row[2]

                # İyileştirme önerileri
                oneriler = con.execute(
                    "SELECT COUNT(*) FROM iyilestirme_onerileri WHERE olusturulma >= ?",
                    (yedi_gun_once,),
                ).fetchone()
                trend["skill"]["yeni_oneri"] = oneriler[0] if oneriler else 0
                con.close()
        except Exception:
            pass

        # Önceki gece raporlarını topla
        if RAPOR_DIZINI.exists():
            rapor_dosyalari = sorted(RAPOR_DIZINI.glob("nightly_*.json"),
                                     reverse=True)[:7]
            for rp in rapor_dosyalari:
                try:
                    veri = json.loads(rp.read_text(encoding="utf-8"))
                    trend["gece_raporlari"].append({
                        "tarih": veri.get("timestamp", "")[:10],
                        "basarili_asama": veri.get("basarili_asama", 0),
                        "toplam_asama": veri.get("toplam_asama", 6),
                        "uyari_var": veri.get("uyari_var", False),
                    })
                except Exception:
                    continue

        # Performans özeti
        trend_ozeti = []
        sk = trend["skill"]
        if sk["kullanim"] > 0:
            basari_orani = (sk["basarili"] / sk["kullanim"]) * 100
            trend_ozeti.append(
                f"Skill basari orani: %{basari_orani:.1f} "
                f"({sk['basarili']}/{sk['kullanim']})"
            )
            if basari_orani < 70:
                trend_ozeti.append("UYARI: Skill basari orani dusuk!")

        oh = trend["once_hafiza"]
        trend_ozeti.append(
            f"once_hafiza: {oh['toplam_kayit']} kayit "
            f"(+{oh['yeni_kayit']} yeni)"
        )

        gecmis = trend["gece_raporlari"]
        if gecmis:
            uyarili_gun = sum(1 for g in gecmis if g.get("uyari_var"))
            trend_ozeti.append(
                f"Son {len(gecmis)} gecede {uyarili_gun} gun uyari var"
            )

        mesaj = " | ".join(trend_ozeti) if trend_ozeti else "Yetersiz veri"
        sonuc.uyari = "UYARI" in mesaj
        sonuc.veri = trend
        sonuc.mesaj = mesaj

    except Exception as e:
        sonuc.basarili = False
        sonuc.mesaj = f"[HATA] {e}"
        logger.warning("[Nightly] trend raporu hatasi: %s", e)

    sonuc.sure_sn = round(time.time() - basla, 2)
    return sonuc


# ═══════════════════════════════════════════════════════════════════════
#  Rapor Yazma
# ═══════════════════════════════════════════════════════════════════════

def _rapor_kaydet(rapor: NightlyRapor) -> None:
    """Raporu durum.json ve .ReYMeN/nightly/ altına yaz."""

    # JSON formatı
    rapor_dict = {
        "timestamp": rapor.timestamp,
        "asamalar": rapor.asamalar,
        "toplam_sure_sn": rapor.toplam_sure_sn,
        "basarili_asama": rapor.basarili_asama,
        "toplam_asama": rapor.toplam_asama,
        "uyari_var": rapor.uyari_var,
        "trend": rapor.trend,
        "ozet": rapor.ozet,
    }

    # Gece raporu dosyası (tarihli)
    tarih = rapor.timestamp[:10]
    rapor_dosyasi = RAPOR_DIZINI / f"nightly_{tarih}.json"
    rapor_dosyasi.write_text(
        json.dumps(rapor_dict, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    # En son rapor
    son_dosya = RAPOR_DIZINI / "nightly_son.json"
    son_dosya.write_text(
        json.dumps(rapor_dict, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    # durum.json güncellemesi
    if DURUM_JSON.exists():
        try:
            durum = json.loads(DURUM_JSON.read_text(encoding="utf-8"))
        except Exception:
            durum = {}
    else:
        durum = {}

    durum["nightly_improvement"] = {
        "son_calisma": rapor.timestamp,
        "basarili_asama": rapor.basarili_asama,
        "toplam_asama": rapor.toplam_asama,
        "uyari_var": rapor.uyari_var,
        "ozet": rapor.ozet,
        "asamalar": {
            a["ad"]: {
                "basarili": a["basarili"],
                "mesaj": a["mesaj"],
                "uyari": a.get("uyari", False),
                "sure_sn": a["sure_sn"],
            }
            for a in rapor.asamalar
        },
    }

    DURUM_JSON.write_text(
        json.dumps(durum, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    logger.info(
        "[Nightly] Rapor kaydedildi: %s (durum.json + nightly_%s.json)",
        son_dosya, tarih,
    )


# ═══════════════════════════════════════════════════════════════════════
#  Ana Döngü
# ═══════════════════════════════════════════════════════════════════════

def main() -> str:
    """6 aşamalı gece kendini geliştirme döngüsünü çalıştır.

    Returns:
        Özet metin (sessiz modda sadece sorun varsa gösterilir).
    """
    baslama = time.time()
    logger.info("[Nightly] === Gece Kendini Gelistirme Dongusu basladi ===")

    # Aşamaları sırayla çalıştır
    asama_fonksiyonlari = [
        ("once_hafiza_analizi", _asama_once_hafiza),
        ("skill_iyilestirme", _asama_skill_iyilestirme),
        ("memory_compaction", _asama_memory_compaction),
        ("kod_kalitesi", _asama_kod_kalitesi),
        ("cron_durumu", _asama_cron_durumu),
        ("trend_raporu", _asama_trend_raporu),
    ]

    sonuclar = []
    basarili_asama = 0
    uyari_var = False

    for ad, fonk in asama_fonksiyonlari:
        logger.info("[Nightly] Asama: %s ...", ad)
        sonuc = fonk()
        sonuclar.append(asdict(sonuc))
        if sonuc.basarili:
            basarili_asama += 1
        if sonuc.uyari:
            uyari_var = True
        logger.info(
            "  %s: %s (%.1fs)%s",
            "OK" if sonuc.basarili else "FAIL",
            sonuc.mesaj[:80],
            sonuc.sure_sn,
            " ⚠️" if sonuc.uyari else "",
        )

    # Raporu oluştur
    toplam_sure = round(time.time() - baslama, 2)

    # Özet mesajı
    sorunlu_asamalar = [
        s["ad"] for s in sonuclar if s.get("uyari")
    ]
    basarisiz_asamalar = [
        s["ad"] for s in sonuclar if not s["basarili"]
    ]

    ozet_parcalari = []
    if sorunlu_asamalar:
        ozet_parcalari.append(
            f"⚠️ Uyari: {', '.join(sorunlu_asamalar)}"
        )
    if basarisiz_asamalar:
        ozet_parcalari.append(
            f"❌ Basarisiz: {', '.join(basarisiz_asamalar)}"
        )
    if not sorunlu_asamalar and not basarisiz_asamalar:
        ozet_parcalari.append("✅ Tum asamalar basarili, sorun yok")

    ozet_parcalari.append(
        f"({basarili_asama}/{len(asama_fonksiyonlari)} basarili, "
        f"{toplam_sure}s)"
    )
    ozet = " | ".join(ozet_parcalari)

    rapor = NightlyRapor(
        timestamp=datetime.now(timezone.utc).isoformat(),
        asamalar=sonuclar,
        toplam_sure_sn=toplam_sure,
        basarili_asama=basarili_asama,
        toplam_asama=len(asama_fonksiyonlari),
        uyari_var=uyari_var,
        ozet=ozet,
    )

    # Kaydet
    _rapor_kaydet(rapor)

    logger.info("[Nightly] === Dongu tamamlandi: %s ===", ozet)

    # Sessiz çalış: sadece sorun varsa kullanıcıya göster
    if uyari_var:
        return f"[NIGHTLY] {ozet}"
    return ""


# ═══════════════════════════════════════════════════════════════════════
#  CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="[NIGHTLY] %(message)s",
    )
    sonuc = main()
    if sonuc:
        print(sonuc)
