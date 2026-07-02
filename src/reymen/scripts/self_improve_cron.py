# -*- coding: utf-8 -*-
"""
self_improve_cron.py — Periyodik self-improvement dongusu.

Her calistiginda:
  1. Self-improve metriklerini topla
  2. Dusuk kaliteli alanlari tespit et
  3. Kod kalitesi taramasi yap (son 24 saat)
  4. Rapor olustur ve kaydet
  5. Raporu ~/.hermes/cron/output/ altina yaz

Kullanim:
    python -m reymen.scripts.self_improve_cron
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format="[SI_CRON] %(message)s")
log = logging.getLogger(__name__)

# Proje koku
ROOT = Path(__file__).resolve().parent.parent.parent
CIKTI_DIZINI = Path(os.environ.get("HERMES_CIKTI", str(ROOT / ".ReYMeN" / "self_improve")))
CIKTI_DIZINI.mkdir(parents=True, exist_ok=True)


def _metrik_topla() -> dict:
    """self_improve singleton'indan trend raporu al."""
    try:
        sys.path.insert(0, str(ROOT))
        from reymen.self_improve import report as si_report
        raw = si_report()
        # Map Turkish keys → English keys for cron template
        return {
            "total_steps": raw.get("toplam_adim", 0),
            "avg_score": raw.get("ortalama_skor", 0.0),
            "pass_rate": raw.get("gecme_orani", 0.0),
            "low_quality_steps": raw.get("dusuk_kalite", 0),
        }
    except Exception as e:
        log.warning("Metrik toplama hatasi: %s", e)
        return {"total_steps": 0, "avg_score": 0.0, "pass_rate": 0.0, "low_quality_steps": 0}


def _kod_tarama() -> list[dict]:
    """Son 24 saatte degisen dosyalarda kalite taramasi.

    Returns:
        [{"dosya": ..., "sorun": ..., "seviye": "uyari"|"kritik"}, ...]
    """
    bulgular = []

    try:
        # Son 24 saatte degisen .py dosyalari
        sonuc = subprocess.run(
            ["git", "diff", "--name-only", "@{1.day.ago}"],
            capture_output=True, text=True, timeout=30,
            cwd=str(ROOT),
        )
        if sonuc.returncode != 0:
            return [{"dosya": "git", "sorun": "git diff basarisiz", "seviye": "uyari"}]

        degisen_dosyalar = [f for f in sonuc.stdout.strip().split("\n")
                           if f.endswith(".py") and f.strip()]

        for dosya in degisen_dosyalar[:20]:  # Ilk 20 ile sinirla
            dosya_yolu = ROOT / dosya
            if not dosya_yolu.exists():
                continue

            icerik = dosya_yolu.read_text(encoding="utf-8")

            # Basit kalite kontrolleri
            satir_sayisi = len(icerik.split("\n"))
            if satir_sayisi > 800:
                bulgular.append({
                    "dosya": dosya, "sorun": f"Cok uzun dosya: {satir_sayisi} satir",
                    "seviye": "uyari",
                })

            if "except:" in icerik or "except :" in icerik:
                bulgular.append({
                    "dosya": dosya, "sorun": "Bare except (except: ) tespit edildi",
                    "seviye": "kritik",
                })

            if "import *" in icerik:
                bulgular.append({
                    "dosya": dosya, "sorun": "Wildcard import (import *)",
                    "seviye": "uyari",
                })

            if "TODO" in icerik or "FIXME" in icerik:
                todo_sayisi = icerik.count("TODO") + icerik.count("FIXME")
                if todo_sayisi > 3:
                    bulgular.append({
                        "dosya": dosya, "sorun": f"Cok fazla TODO/FIXME: {todo_sayisi} adet",
                        "seviye": "uyari",
                    })

    except Exception as e:
        log.warning("Kod tarama hatasi: %s", e)

    return bulgular


def _rapor_olustur(metrik: dict, bulgular: list[dict]) -> dict:
    """Rapor olustur."""
    rapor = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrikler": metrik,
        "kod_kalitesi": {
            "taranan_hata": len(bulgular),
            "kritik": sum(1 for b in bulgular if b.get("seviye") == "kritik"),
            "uyari": sum(1 for b in bulgular if b.get("seviye") == "uyari"),
            "bulgular": bulgular,
        },
        "iyilestirme": [],
    }

    # Metrik bazli iyilestirme onerileri
    if metrik.get("low_quality_steps", 0) > 0:
        rapor["iyilestirme"].append(
            f"{metrik['low_quality_steps']} dusuk kaliteli adim var — "
            f"SELF_IMPROVE_SUGGEST ile detayli oneri alinabilir"
        )
    if metrik.get("avg_score", 1.0) < 0.7:
        rapor["iyilestirme"].append(
            f"Ortalama kalite skoru dusuk ({metrik['avg_score']:.2f}) — "
            f"cozum adimlarinda hata yakalama ve dogrulama iyilestirilmeli"
        )
    if bulgular:
        kritik_sayisi = rapor["kod_kalitesi"]["kritik"]
        if kritik_sayisi > 0:
            rapor["iyilestirme"].append(
                f"{kritik_sayisi} kritik kod sorunu var — hemen duzeltilmeli"
            )

    if not rapor["iyilestirme"]:
        rapor["iyilestirme"].append("Tum metrikler normal — iyilestirme gerekmiyor")

    return rapor


def _rapor_kaydet(rapor: dict) -> Path:
    """Raporu JSON ve MD olarak kaydet."""
    # JSON
    json_yol = CIKTI_DIZINI / "self_improve_rapor.json"
    json_yol.write_text(json.dumps(rapor, indent=2, ensure_ascii=False), encoding="utf-8")

    # MD ozet
    md_yol = CIKTI_DIZINI / "self_improve_ozet.md"
    satirlar = [
        f"# Self-Improvement Raporu",
        f"**Tarih:** {rapor['timestamp'][:19]}",
        f"",
        f"## Metrikler",
        f"| Metrik | Deger |",
        f"|--------|-------|",
        f"| Toplam adim | {rapor['metrikler']['total_steps']} |",
        f"| Ortalama puan | {rapor['metrikler']['avg_score']:.2f} |",
        f"| Gecme orani | {rapor['metrikler']['pass_rate']:.0%} |",
        f"| Dusuk kaliteli adim | {rapor['metrikler']['low_quality_steps']} |",
        f"",
        f"## Kod Kalitesi",
        f"| Metrik | Deger |",
        f"|--------|-------|",
        f"| Bulgu sayisi | {rapor['kod_kalitesi']['taranan_hata']} |",
        f"| Kritik | {rapor['kod_kalitesi']['kritik']} |",
        f"| Uyari | {rapor['kod_kalitesi']['uyari']} |",
        f"",
    ]
    if rapor["kod_kalitesi"]["bulgular"]:
        satirlar.append("### Bulgular")
        for b in rapor["kod_kalitesi"]["bulgular"]:
            ikon = "🔴" if b["seviye"] == "kritik" else "🟡"
            satirlar.append(f"- {ikon} **{b['dosya']}**: {b['sorun']}")
        satirlar.append("")

    satirlar.append("## İyileştirme Önerileri")
    for o in rapor["iyilestirme"]:
        satirlar.append(f"- {o}")

    md_yol.write_text("\n".join(satirlar), encoding="utf-8")

    return json_yol


def main() -> str:
    """Ana dongu — raporu olustur ve dosyaya yaz.

    Returns:
        Kullaniciya gosterilecek ozet metin.
    """
    baslama = time.time()

    log.info("Self-improvement dongusu basladi...")

    # 1. Metrik topla
    metrik = _metrik_topla()
    log.info("Metrikler: %d adim, ortalama=%.2f", metrik["total_steps"], metrik["avg_score"])

    # 2. Kod tara
    bulgular = _kod_tarama()
    log.info("Kod tarama: %d bulgu", len(bulgular))

    # 3. Rapor olustur
    rapor = _rapor_olustur(metrik, bulgular)
    log.info("Rapor olusturuldu: %d iyilestirme onerisi", len(rapor["iyilestirme"]))

    # 4. Kaydet
    yol = _rapor_kaydet(rapor)
    gecen = time.time() - baslama

    ozet = (
        f"[SELF_IMPROVE] Dongu tamam ({gecen:.1f}s)\n"
        f"  Metrik: {metrik['total_steps']} adim, ortalama {metrik['avg_score']:.2f}, "
        f"{metrik['low_quality_steps']} dusuk kaliteli\n"
        f"  Kod: {len(bulgular)} bulgu ({rapor['kod_kalitesi']['kritik']} kritik, "
        f"{rapor['kod_kalitesi']['uyari']} uyari)\n"
        f"  Oneri: {len(rapor['iyilestirme'])} iyilestirme\n"
        f"  Rapor: {yol}"
    )
    log.info("\n%s", ozet)
    return ozet


if __name__ == "__main__":
    print(main())
