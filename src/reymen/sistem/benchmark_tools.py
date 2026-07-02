# -*- coding: utf-8 -*-
"""model_tools.py — Model Benchmark ve Yönetim Araçları.

LLM sağlayıcılarını karşılaştırır: gecikme, token hızı, maliyet.
model_metadata.py ile entegre çalışır.
"""

import json
import time
from pathlib import Path
from typing import Optional
import logging
logger = logging.getLogger(__name__)

try:
    from reymen.sistem.model_metadata import MODELLER, model_bul  # type: ignore
except ImportError:
    MODELLER = {}
    model_bul = None

BENCHMARK_YOLU = Path(__file__).parent / ".ReYMeN" / "model_benchmarks.json"
BENCHMARK_YOLU.parent.mkdir(parents=True, exist_ok=True)

BENCHMARK_PROMPT = "Türkiye'nin başkenti neresidir? Kısa cevap ver."


class BenchmarkSonucu:
    def __init__(self, model: str, saglavici: str):
        self.model        = model
        self.saglavici    = saglavici
        self.gecikme_ms   = 0.0
        self.token_hizi   = 0.0
        self.token_sayisi = 0
        self.yanit        = ""
        self.hata         = ""
        self.basarili     = False

    def to_dict(self) -> dict:
        return {
            "model":        self.model,
            "saglavici":    self.saglavici,
            "gecikme_ms":   round(self.gecikme_ms, 1),
            "token_hizi":   round(self.token_hizi, 1),
            "token_sayisi": self.token_sayisi,
            "basarili":     self.basarili,
            "hata":         self.hata,
        }


def _token_say(metin: str) -> int:
    return max(1, len(metin) // 4)


def tek_model_benchmark(
    uret_fn,
    model: str,
    saglavici: str,
    prompt: str = BENCHMARK_PROMPT,
    sistem: str = "Sen yardımcı bir asistansın.",
) -> BenchmarkSonucu:
    """Tek model benchmark testi."""
    sonuc    = BenchmarkSonucu(model, saglavici)
    mesajlar = [{"role": "user", "content": prompt}]

    t0 = time.perf_counter()
    try:
        yanit = uret_fn(sistem, mesajlar)
        sonuc.gecikme_ms   = (time.perf_counter() - t0) * 1000
        sonuc.yanit        = yanit[:500]
        sonuc.token_sayisi = _token_say(yanit)
        sonuc.token_hizi   = sonuc.token_sayisi / max(sonuc.gecikme_ms / 1000, 0.001)
        sonuc.basarili     = bool(yanit) and "error" not in yanit.lower()[:20]
    except Exception as e:
        sonuc.gecikme_ms = (time.perf_counter() - t0) * 1000
        sonuc.hata       = str(e)[:200]

    return sonuc


def benchmark_kaydet(sonuclar: list):
    mevcut = []
    if BENCHMARK_YOLU.exists():
        try:
            mevcut = json.loads(BENCHMARK_YOLU.read_text(encoding="utf-8"))
        except Exception as _benchmar_e82:
            print(f"[UYARI] benchmark_tools.py:83 - {_benchmar_e82}")
    mevcut.append({
        "zaman":    time.strftime("%Y-%m-%dT%H:%M:%S"),
        "sonuclar": [s.to_dict() for s in sonuclar],
    })
    BENCHMARK_YOLU.write_text(
        json.dumps(mevcut[-50:], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def benchmark_raporu(sonuclar: list) -> str:
    sirali = sorted(sonuclar, key=lambda s: (not s.basarili, s.gecikme_ms))
    satirlar = ["Model                    Sağlayıcı            Gecikme(ms)  Token/sn  Durum",
                "-" * 80]
    for s in sirali:
        durum = "OK" if s.basarili else f"HATA:{s.hata[:15]}"
        satirlar.append(
            f"{s.model:<25} {s.saglavici:<20} "
            f"{s.gecikme_ms:>10.0f}  {s.token_hizi:>8.1f}  {durum}"
        )
    return "\n".join(satirlar)


def gecmis_oku(son_n: int = 5) -> str:
    if not BENCHMARK_YOLU.exists():
        return "Henüz benchmark yapılmamış."
    try:
        kayitlar = json.loads(BENCHMARK_YOLU.read_text(encoding="utf-8"))
        satirlar = []
        for k in kayitlar[-son_n:]:
            satirlar.append(f"\n=== {k['zaman']} ===")
            for s in k["sonuclar"]:
                satirlar.append(
                    f"  {'✓' if s['basarili'] else '✗'} "
                    f"{s['model']:<25} {s['gecikme_ms']:.0f}ms  {s['token_hizi']:.1f} tok/sn"
                )
        return "\n".join(satirlar) if satirlar else "Kayıt boş."
    except Exception as e:
        return f"[Benchmark]: {e}"


def motor_kaydet(motor):
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return

    motor._plugin_arac_kaydet(
        "MODEL_BENCHMARK_GECMIS",
        lambda son_n=5: gecmis_oku(int(son_n)),
        "Geçmiş model benchmark sonuçlarını göster",
    )

    if hasattr(motor, "beyin"):
        def _anlik():
            sonuc = tek_model_benchmark(
                motor.beyin.uret,
                model     = getattr(motor.beyin, "model", "birincil"),
                saglavici = "aktif",
            )
            benchmark_kaydet([sonuc])
            return benchmark_raporu([sonuc])

        motor._plugin_arac_kaydet(
            "MODEL_BENCHMARK_CALISTIR",
            lambda: _anlik(),
            "Aktif modelde anlık benchmark testi yap",
        )


if __name__ == "__main__":
    print(gecmis_oku())
