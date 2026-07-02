# -*- coding: utf-8 -*-
"""
adaptif_ogrenme.py — Adaptif öğrenme ve self-correction modülü.

İki işlev:
  1. Kullanıcı tercihleri: "hayır, böyle yap" gibi düzeltmeleri kaydeder.
     Kaydedilen tercihler sonraki oturumlarda sistem promptuna enjekte edilir.

  2. Self-correction: Bir sonraki modül tarafından kullanılmak üzere
     Python kodu test sonucu + otomatik düzeltme döngüsü API'si.

Kullanim::

    ao = AdaptifOgrenme()

    # Tercih tespiti (main.py'deki ReAct döngüsünde kullanılır)
    ao.kullanici_mesaji_isle("hayır, dosyaları UTF-8 ile yaz her zaman")

    # Sistem prompt enjeksiyonu
    tercihler = ao.tercih_blogu_al()

    # Python self-correction
    sonuc = ao.python_duzelt_ve_calistir(kod, motor, max_deneme=2)
"""

import json
import os
import re
import time
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.resolve()
TERCIH_DOSYASI = ROOT / ".ReYMeN" / "kullanici_tercihleri.json"
MAKS_TERCIH = 50  # En fazla bu kadar tercih saklanır

# Kullanıcı düzeltme sinyalleri
_DUZELTME_SINYALLERI = [
    r"\bhay[ıi]r\b",
    r"\bdeğil\b",
    r"\byapma\b",
    r"\bstop\b",
    r"\bher\s+zaman\b",
    r"\bhiç(?:bir\s+zaman)?\b",
    r"\bböyle\s+(?:yapma|yap)\b",
    r"\b(?:şöyle|bu\s+şekilde)\s+yap\b",
    r"\bkullanma\b",
    r"\bnot:\b",
    r"\bhatırl[ae]\b",
    r"\blütfen\s+(?:bir\s+daha)?\s*yapma\b",
    r"\bgeleceğe\s+not\b",
]

_DUZELTME_RE = re.compile("|".join(_DUZELTME_SINYALLERI), re.IGNORECASE)


class AdaptifOgrenme:
    """Kullanıcı tercihlerini kaydeden ve self-correction sağlayan sınıf."""

    def __init__(self, tercih_dosyasi: str = None):
        self._dosya = Path(tercih_dosyasi) if tercih_dosyasi else TERCIH_DOSYASI
        self._dosya.parent.mkdir(parents=True, exist_ok=True)
        self._tercihler: list = self._yukle()

    # ── Tercih yönetimi ───────────────────────────────────────────────────────

    def _yukle(self) -> list:
        if self._dosya.exists():
            try:
                return json.loads(self._dosya.read_text(encoding="utf-8"))
            except Exception as _e:
                logger.warning("[AdaptifOgrenme] except Exception (L70): %s", Exception)
                pass
        return []

    def _kaydet(self):
        try:
            self._dosya.write_text(
                json.dumps(self._tercihler, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"[Adaptif]: Tercih kaydetme hatası: {e}")

    def tercih_ekle(self, metin: str, kaynak: str = "kullanici") -> bool:
        """Yeni tercih ekle. Aynı metin zaten varsa eklemez.

        Returns:
            True: eklendi, False: zaten mevcut
        """
        metin = metin.strip()[:300]
        if not metin:
            return False
        mevcut_metinler = {t["metin"] for t in self._tercihler}
        if metin in mevcut_metinler:
            return False
        self._tercihler.append({
            "metin": metin,
            "kaynak": kaynak,
            "zaman": time.strftime("%Y-%m-%d %H:%M"),
        })
        # Kapasite sınırı
        if len(self._tercihler) > MAKS_TERCIH:
            self._tercihler = self._tercihler[-MAKS_TERCIH:]
        self._kaydet()
        print(f"[Adaptif]: Tercih kaydedildi -> {metin[:60]}")
        return True

    def kullanici_mesaji_isle(self, mesaj: str) -> bool:
        """Kullanıcı mesajında düzeltme sinyali varsa tercihe çevir.

        Returns:
            True: düzeltme sinyali bulundu ve kaydedildi
        """
        if _DUZELTME_RE.search(mesaj):
            return self.tercih_ekle(mesaj, kaynak="kullanici_duzeltme")
        return False

    def tercih_blogu_al(self, limit: int = 10) -> str:
        """Son N tercihi sistem promptuna enjekte edilecek format olarak döndürür."""
        if not self._tercihler:
            return ""
        son = self._tercihler[-limit:]
        satirlar = "\n".join(f"- {t['metin']}" for t in son)
        return f"\n== KULLANICI TERCİHLERİ (bunlara uy) ==\n{satirlar}\n"

    def tercih_sayisi(self) -> int:
        return len(self._tercihler)

    def tum_tercihler(self) -> list:
        return list(self._tercihler)

    def tercih_sil(self, indeks: int) -> bool:
        if 0 <= indeks < len(self._tercihler):
            silinen = self._tercihler.pop(indeks)
            self._kaydet()
            print(f"[Adaptif]: Tercih silindi: {silinen['metin'][:50]}")
            return True
        return False

    def tercihleri_temizle(self):
        self._tercihler.clear()
        self._kaydet()

    # ── Self-correction ───────────────────────────────────────────────────────

    def python_duzelt_ve_calistir(
        self,
        kod: str,
        motor,
        provider=None,
        max_deneme: int = 2,
    ) -> str:
        """Python kodu çalıştır, hata varsa LLM ile düzelt ve yeniden dene.

        Args:
            kod:        Çalıştırılacak Python kodu.
            motor:      Motor örneği (PYTHON_CALISTIR için).
            provider:   LLM provider (Beyin örneği). None ise sadece hata döner.
            max_deneme: Kaç kere düzeltme denemesi yapılacak.

        Returns:
            Çalışan kodun çıktısı veya son hata mesajı.
        """
        mevcut_kod = kod
        son_hata = ""

        for deneme in range(max_deneme + 1):
            sonuc = motor.calistir("PYTHON_CALISTIR", f'"{mevcut_kod}"')
            if "[Hata]" not in sonuc and "Error" not in sonuc and "Traceback" not in sonuc:
                if deneme > 0:
                    print(f"[Self-correction]: {deneme}. denemede düzeldi.")
                return sonuc

            son_hata = sonuc
            if deneme >= max_deneme or provider is None:
                break

            # LLM'den düzeltme iste
            duzeltme_promptu = (
                f"Aşağıdaki Python kodu şu hatayı verdi:\n\n"
                f"KOD:\n```python\n{mevcut_kod}\n```\n\n"
                f"HATA:\n{son_hata[:500]}\n\n"
                f"Kodu düzelt ve SADECE düzeltilmiş kodu yaz. Açıklama ekleme."
            )
            try:
                yanit = provider.uret(
                    "Sen bir Python kod düzeltici asistanısın.",
                    [{"role": "user", "content": duzeltme_promptu}],
                )
                # Kod bloğunu çıkar
                m = re.search(r"```(?:python)?\s*\n(.+?)```", yanit, re.DOTALL)
                if m:
                    mevcut_kod = m.group(1).strip()
                else:
                    mevcut_kod = yanit.strip()
                print(f"[Self-correction]: Deneme {deneme + 1}, kod düzeltildi.")
            except Exception as e:
                print(f"[Self-correction]: LLM hatası: {e}")
                break

        return f"[Self-correction]: {max_deneme} denemede düzeltilemedi.\nSon hata: {son_hata[:300]}"


# ── Motor entegrasyon yardımcısı ──────────────────────────────────────────────

def adaptif_ogrenme_sistemi_kur() -> AdaptifOgrenme:
    """Global AdaptifOgrenme örneği oluştur."""
    return AdaptifOgrenme()


if __name__ == "__main__":
    ao = AdaptifOgrenme()

    # Düzeltme tespiti testi
    testler = [
        "hayır, her zaman UTF-8 kullan",
        "tamam harika",
        "bunu bir daha yapma lütfen",
        "dosya oluştur",
        "hatırla: API key'i asla yazdırma",
    ]
    print("=== Düzeltme Tespiti ===")
    for t in testler:
        tespit = ao.kullanici_mesaji_isle(t)
        print(f"{'[KAYDEDILDI]' if tespit else '[normal]  '} {t}")

    print(f"\nToplam tercih: {ao.tercih_sayisi()}")
    print(ao.tercih_blogu_al())
