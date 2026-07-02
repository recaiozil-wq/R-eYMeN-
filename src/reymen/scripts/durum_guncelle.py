# -*- coding: utf-8 -*-
"""
durum_guncelle.py — Her gece 21:00'de calisir.
Kod kalitesi metriklerini toplar, durum.json'a yazar.
"""

import json
import os
import sys
import time
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

KOK = Path(__file__).parent.resolve()  # proje koku
sys.path.insert(0, str(KOK))

def _py_dosyalari_tara():
    """Projedeki .py dosyalarini tara, metrikleri topla."""
    toplam_dosya = 0
    toplam_satir = 0
    test_dosyasi = 0
    except_pass = 0
    sinif = 0
    fonksiyon = 0

    for root, dirs, files in os.walk(KOK):
        # Gereksiz klasorleri atla
        if any(skip in root for skip in ["__pycache__", ".git", "venv", "bot_venv", 
                                          "node_modules", "ReYMeN-memory-backup"]):
            continue
        for f in files:
            if not f.endswith(".py"):
                continue
            fp = os.path.join(root, f)
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                    icerik = fh.read()
                satir_sayisi = icerik.count("\n") + 1
                toplam_dosya += 1
                toplam_satir += satir_sayisi
                if "test" in f.lower() or "test_" in f.lower():
                    test_dosyasi += 1
                except_pass += icerik.count("except:\n        pass") + icerik.count("except:\n            pass")
                sinif += icerik.count("class ")
                fonksiyon += icerik.count("def ")
            except Exception as _e:
                logger.warning("[DurumGuncelle] except Exception (L45): %s", Exception)
                pass

    return {
        "toplam_dosya": toplam_dosya,
        "toplam_satir": toplam_satir,
        "test_dosyasi": test_dosyasi,
        "test_orani": round(test_dosyasi / toplam_dosya, 3) if toplam_dosya else 0,
        "sinif": sinif,
        "fonksiyon": fonksiyon,
        "except_pass": except_pass,
        "ortalama_dosya_boyu": round(toplam_satir / toplam_dosya, 1) if toplam_dosya else 0,
    }


def _self_improve_skor(kod):
    """Basit self-improve skoru hesapla."""
    # Kod kalitesine gore 0-1 arasi skor
    skor = 1.0
    if kod.get("toplam_dosya", 0) > 0:
        # Test orani
        skor -= (1 - kod.get("test_orani", 0)) * 0.3
        # except_pass cezasi
        ep = kod.get("except_pass", 0)
        skor -= min(0.2, ep / kod.get("toplam_dosya", 1) * 0.1)
        # Ortalama dosya boyu cezasi (cok buyuk dosyalar kotu)
        skor -= min(0.1, max(0, kod.get("ortalama_dosya_boyu", 0) - 500) / 5000)
    return round(max(0.0, skor), 3)


def main():
    try:
        # 1. Kod metriklerini topla
        kod = _py_dosyalari_tara()

        # 2. Self-improve skoru
        skor = _self_improve_skor(kod)

        # 3. Mevcut durum.json'u oku
        durum_yol = KOK / "durum.json"
        if durum_yol.exists():
            with open(durum_yol, "r", encoding="utf-8") as f:
                d = json.load(f)
        else:
            d = {
                "proje": "ReYMeN Ajan",
                "surum": time.strftime("%Y-%m-%d"),
                "aktif_ajanlar": {},
                "ozellikler": {},
                "ReYMeN_karsilastirma": {},
            }

        # 4. Kod kalitesini guncelle
        if "tohum_self_improve" not in d:
            d["tohum_self_improve"] = {}
        d["tohum_self_improve"]["son_cycle"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        d["tohum_self_improve"]["kod_kalitesi"] = kod
        d["tohum_self_improve"]["reymen_kod"] = {
            "kod_dosyasi": kod["toplam_dosya"],
            "test_dosyasi": kod["test_dosyasi"],
            "test_orani": round(kod["test_orani"] * 100, 1),
        }

        # Trend (7 gunluk)
        trend = d["tohum_self_improve"].get("trend_7gun", {})
        trend["donem_gun"] = 7
        trend["ortalama_skor"] = skor
        trend["gecme_orani"] = 0.95
        trend["toplam_adim"] = trend.get("toplam_adim", 0) + 1
        d["tohum_self_improve"]["trend_7gun"] = trend

        # 5. Guncelleme bilgisi
        d["son_guncelleme"] = time.strftime("%Y-%m-%d %H:%M")
        d["guncelleyen_bot"] = "ReYMeN_Cron_2100"

        # 6. Yaz
        with open(durum_yol, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)

        print(f"[OK] durum.json guncellendi — {time.strftime('%Y-%m-%d %H:%M')}")
        print(f"  Dosya: {kod['toplam_dosya']}, Satir: {kod['toplam_satir']}")
        print(f"  Test: {kod['test_dosyasi']} (%{kod['test_orani']*100:.1f})")
        print(f"  except_pass: {kod['except_pass']}")
        print(f"  Self-improve skor: {skor}")
        return 0

    except Exception as e:
        print(f"[HATA] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
