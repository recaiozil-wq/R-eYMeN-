# -*- coding: utf-8 -*-
"""
hafiza.py — Katman 1: Kalıcı Görev Hafızası

Her alt ajan adımının JSON dosyasına kaydedilmesi.
Process crash olsa bile task sonuçları kaybolmaz.

Kullanım:
    from hafiza import alt_ajan_hafiza
    alt_ajan_hafiza.kaydet("task_123", "adim", {"adim_no": 1, "cevap": "..."})
    gecmis = alt_ajan_hafiza.yukle("task_123")
"""

import json
import os
import threading
import time
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# ── Sabitler ──────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.resolve()
HAFIZA_DIZINI = ROOT / ".alt_ajan_hafiza"
MAX_JSON_BOYUT = 10 * 1024 * 1024  # 10MB — dizin temizleme limiti
MAX_DOSYA_YAS_SAAT = 72  # 72 saatten eski task dosyalari temizlenir

# Thread-safe yazma için kilit
_yazma_kilit = threading.Lock()


# ── Yardımcılar ───────────────────────────────────────────────────────────────

def _task_yolu(task_id: str) -> Path:
    """task_id'ye ait JSON dosya yolunu döndürür."""
    return HAFIZA_DIZINI / f"{task_id}.json"


def _dizin_temizle():
    """72 saatten eski task dosyalarını temizle (disk şişmesini önle)."""
    if not HAFIZA_DIZINI.exists():
        return
    simdi = time.time()
    for f in HAFIZA_DIZINI.glob("*.json"):
        try:
            if simdi - f.stat().st_mtime > MAX_DOSYA_YAS_SAAT * 3600:
                f.unlink(missing_ok=True)
        except OSError as _hafiza_e46:
            print(f"[UYARI] hafiza.py:47 - {_hafiza_e46}")


# ── Ana Sınıf ─────────────────────────────────────────────────────────────────

class AltAjanHafiza:
    """Task ID bazlı kalıcı JSON hafızası.
    
    Her task için tek bir JSON dosyası. Her kayıt append değil,
    dosyayı oku → güncelle → yaz şeklinde (küçük task'lar için ideal).
    """

    def __init__(self):
        HAFIZA_DIZINI.mkdir(parents=True, exist_ok=True)
        _dizin_temizle()

    def kaydet(self, task_id: str, tur: str, veri: dict) -> None:
        """Bir adım/sonuç/hata kaydını task JSON'una ekler.
        
        Args:
            task_id: Alt ajan task ID'si
            tur: "adim" | "sonuc" | "hata" | "gozlem"
            veri: Kaydedilecek sözlük
        """
        if not task_id or not tur:
            return

        dosya = _task_yolu(task_id)
        with _yazma_kilit:
            try:
                # Mevcut kaydı oku
                if dosya.exists():
                    with open(dosya, "r", encoding="utf-8") as f:
                        kayit = json.load(f)
                else:
                    kayit = {"task_id": task_id, "kayitlar": []}

                # Yeni kaydı ekle
                kayit["kayitlar"].append({
                    "tur": tur,
                    "ts": time.time(),
                    "veri": veri,
                })
                kayit["son_guncelleme"] = time.time()

                # Yaz
                with open(dosya, "w", encoding="utf-8") as f:
                    json.dump(kayit, f, ensure_ascii=False, indent=2)

            except (OSError, json.JSONDecodeError) as e:
                # Bozuk dosya varsa sıfırdan başla
                try:
                    with open(dosya, "w", encoding="utf-8") as f:
                        json.dump({
                            "task_id": task_id,
                            "kayitlar": [{"tur": tur, "ts": time.time(), "veri": veri}],
                            "son_guncelleme": time.time(),
                        }, f, ensure_ascii=False, indent=2)
                except OSError as _e:
                    pass  # Sessiz geç — disk dolmuş olabilir

    def yukle(self, task_id: str) -> dict | None:
        """Task'ın tüm kayıtlarını yükler.
        
        Returns:
            Kayıt sözlüğü veya None (dosya yoksa / bozuksa)
        """
        dosya = _task_yolu(task_id)
        if not dosya.exists():
            return None
        try:
            with open(dosya, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def son_kayit(self, task_id: str) -> dict | None:
        """Task'ın son kaydını döndürür (hızlı sorgu için)."""
        kayit = self.yukle(task_id)
        if kayit and kayit.get("kayitlar"):
            return kayit["kayitlar"][-1]
        return None

    def task_listele(self, limit: int = 20) -> list[dict]:
        """Son N task'ın özetini listeler."""
        if not HAFIZA_DIZINI.exists():
            return []
        dosyalar = sorted(
            HAFIZA_DIZINI.glob("*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )[:limit]
        sonuclar = []
        for f in dosyalar:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                sonuclar.append({
                    "task_id": data.get("task_id", f.stem),
                    "kayit_sayisi": len(data.get("kayitlar", [])),
                    "son_guncelleme": data.get("son_guncelleme", 0),
                    "son_tur": data["kayitlar"][-1]["tur"] if data.get("kayitlar") else None,
                })
            except (OSError, json.JSONDecodeError) as _hafiza_e150:
                print(f"[UYARI] hafiza.py:151 - {_hafiza_e150}")
        return sonuclar

    def temizle(self, task_id: str) -> bool:
        """Belirli bir task'ın hafızasını sil."""
        dosya = _task_yolu(task_id)
        try:
            dosya.unlink(missing_ok=True)
            return True
        except OSError:
            return False

    def temizle_hepsi(self) -> int:
        """Tüm alt ajan hafızasını temizle. Silinen dosya sayısını döndür."""
        if not HAFIZA_DIZINI.exists():
            return 0
        sayac = 0
        for f in HAFIZA_DIZINI.glob("*.json"):
            try:
                f.unlink()
                sayac += 1
            except OSError as _hafiza_e172:
                print(f"[UYARI] hafiza.py:173 - {_hafiza_e172}")
        return sayac


# ── Singleton ─────────────────────────────────────────────────────────────────

alt_ajan_hafiza = AltAjanHafiza()


# ── Test ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    TEST_ID = "test_hafiza_001"
    alt_ajan_hafiza.kaydet(TEST_ID, "adim", {"adim_no": 1, "cevap": "test"})
    alt_ajan_hafiza.kaydet(TEST_ID, "sonuc", {"sonuc": "bitti", "adim_sayisi": 1})
    data = alt_ajan_hafiza.yukle(TEST_ID)
    assert data and len(data["kayitlar"]) == 2, "Kayit sayisi 2 olmali"
    print(f"[OK] Hafiza testi gecti: {len(data['kayitlar'])} kayit")
    alt_ajan_hafiza.temizle(TEST_ID)
    assert alt_ajan_hafiza.yukle(TEST_ID) is None, "Temizlik sonrasi None olmali"
    print("[OK] Hafiza temizlik testi gecti")
    print(f"[OK] Toplam task: {len(alt_ajan_hafiza.task_listele())}")
