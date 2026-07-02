# -*- coding: utf-8 -*-
"""
dinamik_arac_uretici.py — FAZ 6: Dinamik Arac Uretimi (Code-As-A-Tool).

ReYMeN mevcut araclarla cozemedigi bir problemle karsilastiginda:
  1. LLM'den problemi cozen bir Python fonksiyonu uretmesini ister.
  2. guvenli_sandbox.py ile test eder.
  3. Basarili olursa araclar_dinamik/ klasorune kaydeder.
  4. motor.py ToolRegistry'e aninda yükler.
  5. closed_learning_loop'a beceri olarak kristallestirir.

Motor entegrasyonu:
    motor.py'de
        if arac == "ARAC_URET":
            from dinamik_arac_uretici import arac_uret_ve_calistir
import logging
logger = logging.getLogger(__name__)
            return arac_uret_ve_calistir(params[0], motor=self, provider=...)
"""

import importlib.util
import json
import os
import re
import uuid
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.resolve()
DINAMIK_ARAC_DIZINI = ROOT / "araclar_dinamik"

# Beklenen LLM cikti sablon kontrolu
_KOD_BLOGU_RE = re.compile(r"```python\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_FONK_ADI_RE = re.compile(r"def\s+([a-z_][a-z0-9_]*)\s*\(", re.IGNORECASE)


def _kod_cikar(llm_cikti: str) -> str:
    """LLM ciktisindaki ```python ... ``` blogunu ya da duz kodu cikar."""
    m = _KOD_BLOGU_RE.search(llm_cikti)
    if m:
        return m.group(1).strip()
    # Blok yoksa tum ciktidan kod satirlarini al
    satirlar = [s for s in llm_cikti.splitlines() if s.strip()]
    return "\n".join(satirlar)


def _fonksiyon_adi_bul(kod: str) -> Optional[str]:
    """Koddaki ilk fonksiyon adini dondur."""
    m = _FONK_ADI_RE.search(kod)
    return m.group(1) if m else None


def _arac_kodu_olustur(fonk_adi: str, problem: str) -> str:
    """Kaydedilecek araç Python dosyasının içerigini olustur."""
    return f'''# -*- coding: utf-8 -*-
"""
araclar_dinamik — Otomatik uretilen arac.
Problem: {problem[:120]}
"""

{{fonksiyon_kodu}}


def motor_kaydet(motor):
    """motor.py ToolRegistry kaydı."""
    motor._plugin_arac_kaydet(
        "{fonk_adi.upper()}",
        lambda *args: str({fonk_adi}(*args) if args else {fonk_adi}()),
        "Dinamik uretilmis arac — {problem[:60]}",
    )
'''


def _kaydet_arac_dosyasi(fonk_adi: str, fonksiyon_kodu: str, problem: str) -> str:
    """Arac kodunu araclar_dinamik/ altina kaydet. Dosya yolunu dondur."""
    DINAMIK_ARAC_DIZINI.mkdir(parents=True, exist_ok=True)
    dosya_adi = f"araclar_dyn_{fonk_adi}_{uuid.uuid4().hex[:6]}.py"
    dosya_yolu = DINAMIK_ARAC_DIZINI / dosya_adi
    sablon = _arac_kodu_olustur(fonk_adi, problem)
    tam_kod = sablon.replace("{fonksiyon_kodu}", fonksiyon_kodu).replace(
        "{fonk_adi}", fonk_adi
    )
    dosya_yolu.write_text(tam_kod, encoding="utf-8")
    return str(dosya_yolu)


def _dinamik_araci_motor_yukle(dosya_yolu: str, motor) -> bool:
    """Kaydedilen arac dosyasini motor ToolRegistry'e aninda yukle."""
    try:
        spec = importlib.util.spec_from_file_location("_dyn_arac", dosya_yolu)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "motor_kaydet"):
            mod.motor_kaydet(motor)
            return True
    except Exception as e:
        print(f"[DinAmikArac] Motor yukleme hatasi: {e}")
    return False


def _llm_arac_uret(problem: str, provider) -> str:
    """LLM'den problem icin Python fonksiyonu uret."""
    sistem = (
        "Sen bir Python uzmanisın. "
        "Kullanicının verdiği problemi cozen SADECE bir Python fonksiyonu yaz. "
        "Yanıtını mutlaka ```python ... ``` blogu icerisinde ver. "
        "Fonksiyon parametresiz veya tek string parametreli olabilir. "
        "os, subprocess, socket, requests gibi tehlikeli modülleri KULLANMA. "
        "Yalnizca standart kütüphane (math, re, json, datetime, pathlib, csv vb.) kullan."
    )
    mesajlar = [{"role": "user", "content": f"Problem: {problem}\n\nPython fonksiyonu yaz:"}]
    try:
        return provider.uret(sistem, mesajlar)
    except Exception as e:
        return f"[LLM Hatasi]: {e}"


# ── Ana API ───────────────────────────────────────────────────────────────────

def arac_uret_ve_calistir(
    problem: str,
    motor=None,
    provider=None,
    test_girdisi: str = "",
    max_deneme: int = 2,
) -> str:
    """Problemi cozen dinamik bir arac uret, test et ve kaydet.

    Args:
        problem:     Ne yapması gerektiğinin aciklamasi.
        motor:       motor.py Motor ornegi (kayit icin).
        provider:    beyin.py Beyin ornegi (LLM uretimi icin).
        test_girdisi: Araci test etmek icin ornek girdi.
        max_deneme:  Bozuk kodda yeniden uretim deneme sayisi.

    Returns:
        Sonuc mesaji (basari/hata).
    """
    if not provider:
        return "[DinAmikArac Hata]: Provider gerekli (beyin.py ornegi)."
    if not problem.strip():
        return "[DinAmikArac Hata]: Problem aciklamasi bos."

    from reymen.guvenlik.guvenli_sandbox import guvenli_calistir

    print(f"[DinAmikArac] Arac uretiliyor: {problem[:80]}...")

    for deneme in range(1, max_deneme + 1):
        llm_cikti = _llm_arac_uret(problem, provider)
        kod = _kod_cikar(llm_cikti)

        if not kod:
            print(f"[DinAmikArac] Deneme {deneme}: LLM gecerli kod uretmedi.")
            continue

        fonk_adi = _fonksiyon_adi_bul(kod)
        if not fonk_adi:
            print(f"[DinAmikArac] Deneme {deneme}: Fonksiyon adi bulunamadi.")
            continue

        # Sandbox'ta test et
        test_kodu = kod + f"\n\n# Test\nprint({fonk_adi}({repr(test_girdisi) if test_girdisi else ''}))"
        sonuc = guvenli_calistir(test_kodu, timeout=15)

        if "[Hata]" in sonuc or "[Guvenlik Reddi]" in sonuc:
            print(f"[DinAmikArac] Deneme {deneme}: Test basarisiz — {sonuc[:100]}")
            # LLM'e hatayı geri bildir (bir sonraki denemede)
            problem = f"{problem}\n[Onceki hata]: {sonuc[:150]}"
            continue

        # Basarili — kaydet
        dosya_yolu = _kaydet_arac_dosyasi(fonk_adi, kod, problem)
        print(f"[DinAmikArac] Kaydedildi: {dosya_yolu}")

        # Motor'a yukle
        if motor:
            yuklendi = _dinamik_araci_motor_yukle(dosya_yolu, motor)
            if yuklendi:
                print(f"[DinAmikArac] Motor'a yuklendi: {fonk_adi.upper()}")

        # Beceri olarak kristallestir
        try:
            from reymen.cereyan.closed_learning_loop import ClosedLearningLoop
            loop = ClosedLearningLoop()
            loop.beceri_kristallestir(
                f"dinamik_{fonk_adi}",
                f"Otomatik uretilmis arac: {problem[:80]}",
                f"ARAC_URET(\"{problem[:60]}\")\nFonksiyon: {fonk_adi}\nDosya: {dosya_yolu}",
            )
        except Exception as e:
            print(f"[DinAmikArac] Beceri kristallestirme hatasi: {e}")

        return (
            f"[DinAmikArac] Basarili!\n"
            f"Fonksiyon: {fonk_adi}\n"
            f"Arac adi: {fonk_adi.upper()}\n"
            f"Dosya: {dosya_yolu}\n"
            f"Test ciktisi:\n{sonuc}"
        )

    return f"[DinAmikArac Hata]: {max_deneme} denemede gecerli arac uretilemedi."


def mevcut_dinamik_araclari_yukle(motor) -> int:
    """Baslangicta araclar_dinamik/ altindaki tum araclari motor'a yukle."""
    if not DINAMIK_ARAC_DIZINI.exists():
        return 0
    yuklenen = 0
    for dosya in DINAMIK_ARAC_DIZINI.glob("araclar_dyn_*.py"):
        try:
            spec = importlib.util.spec_from_file_location(dosya.stem, dosya)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "motor_kaydet"):
                mod.motor_kaydet(motor)
                yuklenen += 1
        except Exception as e:
            print(f"[DinAmikArac] {dosya.name} yuklenemedi: {e}")
    if yuklenen:
        print(f"[DinAmikArac] {yuklenen} dinamik arac yuklendi.")
    return yuklenen


# ── Test ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import tempfile

    print("=== dinamik_arac_uretici.py Test ===\n")

    # Sahte provider (LLM olmadan test icin)
    class SahteProvider:
        def uret(self, sistem, mesajlar):
            return (
                "Bu arac verilen sayiyi tersine cevirir.\n\n"
                "```python\n"
                "def sayi_tersine_cevir(girdi: str) -> str:\n"
                "    return str(girdi)[::-1]\n"
                "```"
            )

    with tempfile.TemporaryDirectory() as tmpdir:
        import sys
        sys.path.insert(0, tmpdir)

        # Dinamik dizini gecici klasore yonlendir
        from reymen.cereyan import dinamik_arac_uretici as dau
        orijinal_dizin = dau.DINAMIK_ARAC_DIZINI
        dau.DINAMIK_ARAC_DIZINI = Path(tmpdir) / "araclar_dinamik"

        provider = SahteProvider()
        sonuc = dau.arac_uret_ve_calistir(
            problem="Verilen sayiyi tersine ceviren bir fonksiyon",
            motor=None,
            provider=provider,
            test_girdisi="12345",
        )
        print(sonuc)

        # Dosya kaydedildi mi?
        dosyalar = list((Path(tmpdir) / "araclar_dinamik").glob("araclar_dyn_*.py"))
        print(f"\n[Test] Kaydedilen dosya sayisi: {len(dosyalar)} (beklenen: 1)")
        if dosyalar:
            print(f"[Test] Dosya adi: {dosyalar[0].name}")

        dau.DINAMIK_ARAC_DIZINI = orijinal_dizin
