# -*- coding: utf-8 -*-
"""
delegate_task_tool.py — ThreadPoolExecutor tabanlı paralel sub-agent delegasyonu.

Hermes Agent'teki paralel task delegasyon sisteminden esinlenilmiştir.
Alt ajanları ThreadPoolExecutor ile paralel çalıştırır, her birine ayrı
Beyin instance'ı verir, sonuçları toplayıp özetler.

Kullanım:
    DELEGATE_TASK(
        "görev_tanımları_json",
        "bağlam",
        max_paralel=3,
        timeout=60
    )

    görev_tanımları_json = [
        {"gorev": "Dosya oku ve özetle", "baglam": "dosya: test.py"},
        {"gorev": "Web'de ara", "baglam": "konu: yapay zeka"},
    ]

Bağımlılıklar:
    - concurrent.futures.ThreadPoolExecutor (standart kütüphane)
    - reymen.cereyan.beyin.Beyin
"""

from __future__ import annotations

import json
import logging
import os
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Varsayılan yapılandırma ────────────────────────────────────────────
_MAX_PARALEL = int(os.environ.get("DELEGATE_MAX_PARALEL", "5"))
_TIMEOUT = int(os.environ.get("DELEGATE_TIMEOUT", "120"))
_MAX_ADIM = int(os.environ.get("DELEGATE_MAX_ADIM", "10"))

# Proje kökü → config.yaml yükleme
_PROJE_KOK = Path(__file__).resolve().parent.parent.parent
_CONFIG_YOLU = _PROJE_KOK / "config.yaml"


def _config_yukle() -> dict:
    """Proje config.yaml'ini yükle, yoksa boş dict döndür."""
    try:
        import yaml
        if _CONFIG_YOLU.exists():
            with open(_CONFIG_YOLU, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    except Exception:
        pass
    return {"default_provider": "lmstudio", "default_model": "cognitivecomputations.dolphin3.0-llama3.1-8b"}


_DELEGATE_CONFIG = _config_yukle()


@dataclass
class AltGorevSonuc:
    """Tek bir alt görevin sonucunu tutar."""
    gorev: str
    task_id: str
    basarili: bool
    sonuc: str = ""
    hata: str = ""
    sure_sn: float = 0.0
    adim_sayisi: int = 0


@dataclass
class DelegasyonSonuc:
    """Tüm delegasyonun toplu sonucu."""
    parent_task_id: str
    toplam_gorev: int
    basarili: int
    basarisiz: int
    sonuclar: List[AltGorevSonuc] = field(default_factory=list)
    toplam_sure_sn: float = 0.0
    ozet: str = ""


def _alt_gorev_calistir(
    gorev: str,
    baglam: str,
    task_id: str,
    timeout: float,
    max_adim: int,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> AltGorevSonuc:
    """Tek bir alt görevi çalıştır (ThreadPoolExecutor worker'ı).

    Her alt görev:
    - Kendi Beyin instance'ını alır (ana ajandan bağımsız)
    - Kendi ReAct döngüsünü çalıştırır
    - Sonucu döndürür

    Zaman aşımı ve hata durumlarını yönetir.
    """
    baslangic = time.time()
    sonuc = AltGorevSonuc(
        gorev=gorev,
        task_id=task_id,
        basarili=False,
    )

    try:
        # Lazy import — sadece gerektiğinde yüklenir
        from reymen.cereyan.beyin import Beyin

        # Alt ajan için ayrı Beyin (proje config'inden)
        beyin = Beyin(config=_DELEGATE_CONFIG)

        # Sistem promptu: alt ajan için kısa ReAct talimatı
        sistem_prompt = (
            f"Sen {task_id} ID'li bir ALT AJANSIN. "
            f"Görevi tamamlamak için kısa ve öz cevap ver.\n\n"
            f"GÖREV: {gorev}\n"
            f"BAĞLAM: {baglam or '(verilmedi)'}\n\n"
            f"KURALLAR:\n"
            f"- Doğrudan cevap yaz, araç kullanmana gerek yok.\n"
            f"- Türkçe cevap ver.\n"
            f"- En fazla {max_adim} adımın var.\n"
            f"- GOREV_BITTI ile bitir.\n"
        )

        mesajlar = [
            {"role": "system", "content": sistem_prompt},
            {"role": "user", "content": f"Görev: {gorev}\nBağlam: {baglam}"},
        ]

        adim = 0
        while adim < max_adim:
            adim += 1
            gecen = time.time() - baslangic
            if gecen > timeout:
                sonuc.sonuc = f"(zaman_aşımı={timeout}s)"
                break

            # LLM çağrısı
            yanit = beyin.uret(sistem_prompt[:500], mesajlar)
            if not yanit:
                sonuc.sonuc = "(boş_yanıt)"
                break

            mesajlar.append({"role": "assistant", "content": yanit})

            # GOREV_BITTI kontrolü
            if "GOREV_BITTI" in yanit:
                import re
                m = re.search(r'GOREV_BITTI\s*\(\s*"([^"]*)"\s*\)', yanit)
                sonuc.sonuc = m.group(1) if m else yanit
                break

            # BITTI: kontrolü
            if yanit.strip().startswith("BITTI:"):
                sonuc.sonuc = yanit.split("BITTI:", 1)[1].strip()
                break

            # Son adımda yanıtı sonuç olarak al
            if adim >= max_adim:
                sonuc.sonuc = yanit[:1000]

            # Devam mesajı
            mesajlar.append({
                "role": "user",
                "content": "Devam et. Hedefe ulaştıysan GOREV_BITTI(\"cevap\") yaz."
            })

        sonuc.basarili = True
        sonuc.adim_sayisi = adim

    except Exception as e:
        sonuc.hata = f"{type(e).__name__}: {e}"
        logger.warning("[delegate_task] Alt görev hatası (%s): %s", task_id, e)

    finally:
        sonuc.sure_sn = round(time.time() - baslangic, 2)

    return sonuc


def _delegate_task_impl(
    gorev_listesi: List[Dict[str, str]],
    baglam_genel: str = "",
    max_paralel: int = _MAX_PARALEL,
    timeout: float = _TIMEOUT,
    max_adim: int = _MAX_ADIM,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> DelegasyonSonuc:
    """ThreadPoolExecutor ile alt görevleri paralel çalıştır.

    Args:
        gorev_listesi: Her biri {"gorev": str, "baglam": str} olan dict listesi.
        baglam_genel: Tüm alt görevlere eklenecek genel bağlam.
        max_paralel: Aynı anda çalışacak maksimum alt ajan sayısı.
        timeout: Her alt görev için maksimum süre (saniye).
        max_adim: Her alt görev için maksimum adım sayısı.
        provider: Alt ajanlar için provider (opsiyonel).
        model: Alt ajanlar için model (opsiyonel).

    Returns:
        DelegasyonSonuc — tüm sonuçları ve özeti içerir.
    """
    parent_id = str(uuid.uuid4())[:8]
    baslangic = time.time()

    if not gorev_listesi:
        return DelegasyonSonuc(
            parent_task_id=parent_id,
            toplam_gorev=0,
            basarili=0,
            basarisiz=0,
            ozet="Hiç görev tanımlanmamış.",
        )

    sonuc = DelegasyonSonuc(
        parent_task_id=parent_id,
        toplam_gorev=len(gorev_listesi),
        basarili=0,
        basarisiz=0,
    )

    # ThreadPoolExecutor ile paralel çalıştır
    with ThreadPoolExecutor(max_workers=max_paralel) as executor:
        future_map = {}
        for i, g in enumerate(gorev_listesi):
            gorev = g.get("gorev", "").strip()
            baglam = g.get("baglam", "").strip()
            if not gorev:
                continue

            # Genel bağlamı ekle
            if baglam_genel:
                baglam = f"{baglam_genel} | {baglam}" if baglam else baglam_genel

            task_id = f"{parent_id}-{i:03d}"

            future = executor.submit(
                _alt_gorev_calistir,
                gorev=gorev,
                baglam=baglam,
                task_id=task_id,
                timeout=timeout,
                max_adim=max_adim,
                provider=provider,
                model=model,
            )
            future_map[future] = task_id

        # Sonuçları topla
        for future in as_completed(future_map, timeout=timeout + 10):
            task_id = future_map[future]
            try:
                alt_sonuc = future.result(timeout=5)
                sonuc.sonuclar.append(alt_sonuc)
                if alt_sonuc.basarili:
                    sonuc.basarili += 1
                else:
                    sonuc.basarisiz += 1
            except Exception as e:
                sonuc.basarisiz += 1
                sonuc.sonuclar.append(AltGorevSonuc(
                    gorev="(bilinmiyor)",
                    task_id=task_id,
                    basarili=False,
                    hata=f"Future hatası: {e}",
                ))

    sonuc.toplam_sure_sn = round(time.time() - baslangic, 2)

    # Özet oluştur
    sonuc.ozet = _ozet_olustur(sonuc)
    return sonuc


def _ozet_olustur(ds: DelegasyonSonuc) -> str:
    """Delegasyon sonucundan okunabilir bir özet oluştur."""
    basarili_yuzde = round(
        (ds.basarili / ds.toplam_gorev * 100) if ds.toplam_gorev > 0 else 0
    )

    satirlar = [
        f"📋 DELEGASYON ÖZETİ (ID: {ds.parent_task_id})",
        f"  ⏱  Süre: {ds.toplam_sure_sn:.1f}s",
        f"  📊 Toplam: {ds.toplam_gorev} görev",
        f"  ✅ Başarılı: {ds.basarili} ({basarili_yuzde}%)",
        f"  ❌ Başarısız: {ds.basarisiz}",
        "",
    ]

    if ds.sonuclar:
        satirlar.append("Görev Sonuçları:")
        for s in ds.sonuclar:
            ikon = "✅" if s.basarili else "❌"
            sonuc_ozet = (s.sonuc or s.hata or "-")[:150]
            satirlar.append(f"  {ikon} [{s.task_id}] {s.gorev[:60]}")
            satirlar.append(f"     → {sonuc_ozet}")
            satirlar.append(f"     ⏱ {s.sure_sn}s / {s.adim_sayisi} adım")

    return "\n".join(satirlar)


# ── Ana fonksiyon: LLM'den çağrılır ──────────────────────────────────

def delegate_task(
    gorev_tanimlari: str,
    baglam_genel: str = "",
    max_paralel: int = _MAX_PARALEL,
    timeout: int = _TIMEOUT,
    max_adim: int = _MAX_ADIM,
) -> str:
    """Alt ajanları ThreadPoolExecutor ile paralel çalıştırır.

    Her alt ajan kendi Beyin instance'ını kullanır, ayrı bir conversation
    bağlamında çalışır. Tüm sonuçlar toplanır ve özetlenir.

    Args:
        gorev_tanimlari: JSON string. Her biri {"gorev": "...", "baglam": "..."}
                         olan bir dizi. Örnek:
                         [{"gorev": "Dosya oku", "baglam": "test.py"},
                          {"gorev": "Web ara", "baglam": "yapay zeka"}]
        baglam_genel: Tüm alt görevlere eklenecek genel bağlam (opsiyonel).
        max_paralel: Aynı anda çalışacak maksimum alt ajan sayısı (varsayılan: 5).
        timeout: Her alt görev için maksimum süre, saniye (varsayılan: 120).
        max_adim: Her alt görev için maksimum adım sayısı (varsayılan: 10).

    Returns:
        Özet metin — tüm alt ajan sonuçlarının okunabilir özeti.
    """
    try:
        # JSON parse
        if isinstance(gorev_tanimlari, str):
            gorev_listesi = json.loads(gorev_tanimlari)
        else:
            gorev_listesi = gorev_tanimlari

        if not isinstance(gorev_listesi, list):
            return "❌ HATA: gorev_tanimlari bir JSON dizi olmalı."

        # Delegasyonu çalıştır
        ds = _delegate_task_impl(
            gorev_listesi=gorev_listesi,
            baglam_genel=baglam_genel,
            max_paralel=max_paralel,
            timeout=timeout,
            max_adim=max_adim,
        )

        return ds.ozet

    except json.JSONDecodeError as e:
        return f"❌ HATA: Geçersiz JSON formatı — {e}"
    except Exception as e:
        logger.error("[delegate_task] Beklenmeyen hata: %s", e)
        logger.error(traceback.format_exc())
        return f"❌ HATA: {type(e).__name__}: {e}"


# ── Motor entegrasyonu ───────────────────────────────────────────────

def motor_kaydet(motor) -> None:
    """Motor'a DELEGATE_TASK aracını kaydet.

    Bu fonksiyon, motor.py'nin _plugin_moduller_yukle() metodu tarafından
    otomatik çağrılır. Tool tanımını ve fonksiyonunu motor'a bildirir.
    """
    motor._plugin_arac_kaydet(
        "DELEGATE_TASK",
        delegate_task,
        (
            "Alt ajanları paralel çalıştırır. "
            "Paralel alt-ajan sistemi: Görevleri ThreadPoolExecutor ile paralel çalıştırır. "
            "Her alt ajan kendi Beyin instance'ını kullanır, ayrı bir conversation bağlamında çalışır. "
            "Tüm sonuçlar toplanır ve özetlenir.\n\n"
            "Parametreler:\n"
            "  gorev_tanimlari (str, ZORUNLU): JSON string. "
            "Her biri {\"gorev\": \"...\", \"baglam\": \"...\"} olan bir dizi.\n"
            "  baglam_genel (str, opsiyonel): Tüm alt görevlere eklenecek genel bağlam.\n"
            "  max_paralel (int, opsiyonel): Aynı anda çalışacak maksimum alt ajan sayısı (varsayılan: 5).\n"
            "  timeout (int, opsiyonel): Her alt görev için maksimum süre (varsayılan: 120s).\n"
            "  max_adim (int, opsiyonel): Her alt görev için maksimum adım (varsayılan: 10).\n\n"
            "Örnek:\n"
            "  DELEGATE_TASK('[{\"gorev\":\"Dosyayı oku ve özetle\",\"baglam\":\"test.py\"},"
            "{\"gorev\":\"Web ara\",\"baglam\":\"yapay zeka\"}]')"
        ),
    )


# ── Doğrudan çalıştırma testi ─────────────────────────────────────────

if __name__ == "__main__":
    # Test: basit delegasyon
    test_gorevler = json.dumps([
        {"gorev": "Merhaba dünya yaz", "baglam": ""},
        {"gorev": "2+2 kaç eder?", "baglam": "matematik"},
    ])
    sonuc = delegate_task(test_gorevler, max_paralel=2, timeout=30, max_adim=3)
    print(sonuc)
