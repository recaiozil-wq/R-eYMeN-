# -*- coding: utf-8 -*-
"""
batch_runner.py — ReYMeN Paralel Toplu Gorev Isleme.

Birden cok hedefi sirali veya paralel olarak calistirir.
Checkpoint destegi ile yarida kalan toplu islemlere devam eder.
Sonuclari JSONL dosyasina yazar.

Calistirma:
    python batch_runner.py --dosya hedefler.txt
    python batch_runner.py --hedefler "hedef1" "hedef2" "hedef3"
    python batch_runner.py --dosya hedefler.jsonl --paralel 3
"""
import argparse
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue
import logging
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

CIKTI_DIZIN = ROOT / "logs" / "batch"
CIKTI_DIZIN.mkdir(parents=True, exist_ok=True)


# ── Sonuc Yoneticisi ─────────────────────────────────────────────────

class SonucYoneticisi:
    def __init__(self, cikti_dosyasi: Path):
        self.dosya = cikti_dosyasi
        self._kilit = threading.Lock()
        self._tamamlanan = 0
        self._basarisiz = 0
        self._sonuclar: list[dict] = []
        self._checkpoint = cikti_dosyasi.with_suffix(".checkpoint.json")
        self._tamamlanan_idler: set[str] = set()
        self._checkpoint_yukle()

    def _checkpoint_yukle(self):
        if self._checkpoint.exists():
            try:
                data = json.loads(self._checkpoint.read_text(encoding="utf-8"))
                self._tamamlanan_idler = set(data.get("tamamlanan", []))
                print(f"[Batch] Checkpoint yuklendi: {len(self._tamamlanan_idler)} tamamlanmis")
            except Exception as _batch_ru_e49:
                print(f"[UYARI] batch_runner.py:50 - {_batch_ru_e49}")

    def _checkpoint_kaydet(self):
        try:
            self._checkpoint.write_text(
                json.dumps({"tamamlanan": list(self._tamamlanan_idler)}, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as _batch_ru_e58:
            print(f"[UYARI] batch_runner.py:59 - {_batch_ru_e58}")

    def zaten_tamamlandi_mi(self, gorev_id: str) -> bool:
        return gorev_id in self._tamamlanan_idler

    def kaydet(self, gorev_id: str, hedef: str, sonuc: str | None, sure: float):
        kayit = {
            "id": gorev_id,
            "hedef": hedef,
            "sonuc": sonuc,
            "basarili": sonuc is not None,
            "sure_saniye": round(sure, 2),
            "zaman": datetime.now(timezone.utc).isoformat(),
        }
        with self._kilit:
            self._sonuclar.append(kayit)
            if sonuc is not None:
                self._tamamlanan += 1
                self._tamamlanan_idler.add(gorev_id)
            else:
                self._basarisiz += 1
            with open(self.dosya, "a", encoding="utf-8") as f:
                f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
            self._checkpoint_kaydet()

    def ozet(self) -> dict:
        with self._kilit:
            return {
                "toplam": len(self._sonuclar),
                "basarili": self._tamamlanan,
                "basarisiz": self._basarisiz,
            }


# ── Gorev Isleyici ───────────────────────────────────────────────────

def gorev_isle(gorev_id: str, hedef: str, sonuc_yoneticisi: SonucYoneticisi,
               verbose: bool = True):
    """Tek bir gorevi calistir."""
    if sonuc_yoneticisi.zaten_tamamlandi_mi(gorev_id):
        if verbose:
            print(f"[Batch] Atlandi (checkpoint): {gorev_id}")
        return

    if verbose:
        print(f"\n[Batch] Basliyor: {gorev_id} — {hedef[:60]}")

    t0 = time.time()
    sonuc = None
    try:
        from reymen.sistem.main import AIAgentOrchestrator, CONFIG
        agent = AIAgentOrchestrator(config=CONFIG, max_tur=10, onay_iste=False)
        sonuc = agent.run_conversation(hedef)
    except Exception as e:
        if verbose:
            print(f"[Batch] Hata ({gorev_id}): {e}")

    sure = time.time() - t0
    sonuc_yoneticisi.kaydet(gorev_id, hedef, sonuc, sure)

    if verbose:
        durum = "OK" if sonuc else "BASARISIZ"
        print(f"[Batch] {durum} ({sure:.1f}s): {gorev_id}")


def hedefleri_yukle(dosya: Path) -> list[dict]:
    """Dosyadan hedef listesi yukle (.txt veya .jsonl)."""
    hedefler = []
    with open(dosya, encoding="utf-8") as f:
        for i, satir in enumerate(f):
            satir = satir.strip()
            if not satir or satir.startswith("#"):
                continue
            if satir.startswith("{"):
                try:
                    obj = json.loads(satir)
                    hedefler.append({
                        "id": obj.get("id", f"gorev-{i}"),
                        "hedef": obj.get("hedef") or obj.get("goal") or obj.get("prompt", ""),
                    })
                except json.JSONDecodeError as _batch_ru_e139:
                    print(f"[UYARI] batch_runner.py:140 - {_batch_ru_e139}")
            else:
                hedefler.append({"id": f"gorev-{i}", "hedef": satir})
    return hedefler


def paralel_calistir(hedefler: list[dict], max_is: int,
                      sonuc_yoneticisi: SonucYoneticisi, verbose: bool = True):
    """Hedefleri thread havuzuyla paralel calistir."""
    kuyruk: Queue = Queue()
    for h in hedefler:
        kuyruk.put(h)

    def worker():
        while True:
            try:
                gorev = kuyruk.get_nowait()
            except Exception:
                break
            gorev_isle(gorev["id"], gorev["hedef"], sonuc_yoneticisi, verbose)
            kuyruk.task_done()

    threadler = [
        threading.Thread(target=worker, daemon=True)
        for _ in range(min(max_is, len(hedefler)))
    ]
    for t in threadler:
        t.start()
    for t in threadler:
        t.join()


# ── CLI ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ReYMeN Batch Runner")
    parser.add_argument("--dosya", type=Path, help="Hedef listesi (.txt veya .jsonl)")
    parser.add_argument("--hedefler", nargs="+", help="Dogrudan hedefler (space-seperated)")
    parser.add_argument("--paralel", type=int, default=1, help="Paralel is sayisi (default: 1)")
    parser.add_argument("--cikti", type=Path, default=None, help="Cikti JSONL dosyasi")
    parser.add_argument("--sessiz", action="store_true", help="Detayli log gizle")
    args = parser.parse_args()

    hedefler = []
    if args.dosya:
        hedefler = hedefleri_yukle(args.dosya)
    elif args.hedefler:
        hedefler = [{"id": f"gorev-{i}", "hedef": h}
                    for i, h in enumerate(args.hedefler)]
    else:
        parser.print_help()
        return

    zaman = datetime.now().strftime("%Y%m%d_%H%M%S")
    cikti = args.cikti or CIKTI_DIZIN / f"batch_{zaman}.jsonl"
    sonuc_yoneticisi = SonucYoneticisi(cikti)

    print(f"[Batch] {len(hedefler)} hedef, {args.paralel} paralel is")
    print(f"[Batch] Cikti: {cikti}")

    t0 = time.time()
    if args.paralel > 1:
        paralel_calistir(hedefler, args.paralel, sonuc_yoneticisi, not args.sessiz)
    else:
        for h in hedefler:
            gorev_isle(h["id"], h["hedef"], sonuc_yoneticisi, not args.sessiz)

    ozet = sonuc_yoneticisi.ozet()
    print(f"\n[Batch] Bitti — {time.time()-t0:.1f}s")
    print(f"  Toplam: {ozet['toplam']} | Basarili: {ozet['basarili']} | Basarisiz: {ozet['basarisiz']}")
    print(f"  Sonuclar: {cikti}")


def motor_kaydet(motor):
    """Batch runner araçlarını motora kaydet."""
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return
    import subprocess, sys as _sys
    motor._plugin_arac_kaydet(
        "BATCH_CALISTIR",
        lambda dosya="", paralel="1": subprocess.run(
            [_sys.executable, __file__, "--dosya", dosya, "--paralel", paralel],
            capture_output=True, text=True, timeout=300
        ).stdout[:500] or "[Batch]: Çalıştırıldı",
        "Toplu görev dosyasını çalıştır (dosya: jsonl yolu, paralel: iş sayısı)",
    )


if __name__ == "__main__":
    main()

