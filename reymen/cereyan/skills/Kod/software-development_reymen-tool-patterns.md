---
name: reymen-tool-patterns
category: software-development
version: 1.0.0
description: R>eYMeN projesinde tool gelistirme pattern'leri ve kritik kod yapilari
tags: [skill, hermes, reymen, patterns, tools]
---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | R>eYMeN projesinde tool gelistirme pattern'leri ve kritik kod yapilari |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# reymen-tool-patterns

R>eYMeN projesine yeni tool eklerken kullanilacak pattern'ler.

## Ozet Tablo

| # | Dosya | Kritik Pattern |
|---|-------|----------------|
| 1 | session_search_tool.py | Lazy store + _parse_limit + dict/tuple kayit guard |
| 2 | execute_code_tool.py | Lazy lab + TimeoutError/MemoryError ayrimi |
| 3 | delegate_task_tool.py | sys.executable + returncode kontrolu + json_cikti flag |
| 4 | vision_tool.py | mkstemp + lazy PIL + ayri exception tipi |
| 5 | discord.py | Interface uyumu + mesaj_akisi generator |
| 6 | test_tools.py | monkeypatch + network mock + her tool icin 3-4 case |
| 7 | context_tool.py | Lazy ctx + method adi fallback chain + TypeError retry |
| 8 | memory_providers/base.py | ABC BellekSaglayici interface — kaydet/oku/ara/sil/durum |
| 9 | memory_providers/file_provider.py | Atomic write (temp+rename) + JSON bozuk dosya recovery |
| 10 | memory_providers/chromadb_provider.py | upsert duplicate-safe + n_results ≤ count() guard |
| 11 | memory_providers/sqlite_provider.py | FTS5 check via compileoption + executescript DDL + LIKE fallback |
| 12 | memory_providers/redis_provider.py | scan_iter lazy iterator + namespace index (sadd) + decode_responses |
| 13 | memory_providers/memory_bridge.py | threading.Lock singleton + frozenset validation + deger=None default |

## Genel Python Kod Standartları (beyin.py / guardrails.py'dan)

Bu kalıplar Reymen'deki TÜM Python dosyaları için geçerlidir. Her yeni dosyada uygulanmalıdır.

### Zorunlu Yapı Taşları

```python
# -*- coding: utf-8 -*-
"""modul_adi.py — Kısa açıklama."""

from __future__ import annotations  # ZORUNLU: deferred evaluation

import logging
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Sabitler
_BIR_SABIT: int = 4096
```

### Dispatch Dict — if/elif Yerine

```python
# YANLIS: uzun if/elif zinciri
if provider == "lmstudio":
    return self._cagir_lmstudio(...)
elif provider == "anthropic":
    return self._cagir_anthropic(...)

# DOGRU: dispatch dict
_DISPATCH: dict[str, str] = {
    "lmstudio":  "_cagir_lmstudio",
    "anthropic": "_cagir_anthropic",
}
metod_adi = _DISPATCH.get(provider, "_cagir_openai_uyumlu")
metod = getattr(self, metod_adi)
return metod(...)
```

### _guvensiz_import() — Opsiyonel Bağımlılıklar

Her modül için ayrı try/except yerine tek yardımcı:

```python
def _guvensiz_import(modul_adi: str) -> Any:
    try:
        import importlib
        return importlib.import_module(modul_adi)
    except ImportError:
        return None

_modul = _guvensiz_import("opsiyonel_modul")
_AKTIF = _modul is not None

# Kullanım:
if _AKTIF:
    _modul.fonksiyon()
```

### Frozen Dataclass — Tip Güvenli Veri

Ham dict/demet yerine:

```python
@dataclass(frozen=True)
class Uyari:
    kod: str
    mesaj: str
    skor: float
    def __str__(self) -> str:
        return f"[{self.kod}] {self.mesaj}"

@dataclass
class SaglayiciAdim:
    provider: str
    model: str
    base_url: str
    api_key: str
    def __repr__(self) -> str:
        return f"<SaglayiciAdim {self.provider} {self.model}>"
```

### frozenset — Immutable Sabit Kümeler

```python
# YANLIS: set({...}) — kazara değiştirilebilir
# DOGRU: frozenset (immutable)
_EK_RISKLI_ARACLAR: frozenset[str] = frozenset({
    "DOSYA_YAZ",
    "WEB_ARA",
})
```

### @property — Getter Metodları Yerine

```python
# YANLIS
def aktif_mi(self) -> bool:
    return self._aktif

# DOGRU
@property
def aktif(self) -> bool:
    return self._aktif

# Geriye uyumluluk için:
def aktif_mi(self) -> bool:
    return self._aktif
```

### Ayrı Kontrol Metodları — Tek Sorumluluk

```python
# YANLIS: tek metotta 6 farklı kontrol
def filtrele(self, yanit):
    uyarilar = []
    if regex1.search(yanit): ...
    if regex2.search(yanit): ...
    return yanit, uyarilar

# DOGRU: her kontrol ayrı metod
def filtrele(self, yanit):
    uyarilar = []
    uyarilar.extend(self._emin_olmayan_kontrol(yanit))
    uyarilar.extend(self._kesin_iddia_kontrol(yanit))
    return yanit, uyarilar

def _emin_olmayan_kontrol(self, yanit) -> list[Uyari]:
    if _EMIN_OLMAYAN_RE.search(yanit):
        return [Uyari(kod="EMIN_OLMAYAN", ...)]
    return []
```

### time.monotonic() — Sistem Saati Değişikliklerinden Etkilenmez

```python
# YANLIS: time.time() — saat değişince negatif süre verir
# DOGRU: time.monotonic() — her zaman ileri gider
t0 = time.monotonic()
# ... işlem ...
sure = time.monotonic() - t0  # güvenli
```

### Logging — print() Yerine

```python
# YANLIS: print("[Beyin] Hata: ...")
# DOGRU:
logger.warning("[Beyin] Beklenmeyen durum: %s", detay)
logger.error("[Beyin] Hata: %s", hata)
logger.info("[Beyin] Başarılı: %s", mesaj)
logger.debug("[Beyin] Detay: %s", detay)  # sadece debug'da görünür
```

### Referans: Bu Kalıpların Uygulandığı Dosyalar

| Dosya | Pattern |
|-------|---------|
| `beyin.py` | Dispatch dict, SaglayiciAdim/LLMYanitMeta dataclass, _guvensiz_import, logging, time.monotonic() |
| `guardrails.py` | Uyari frozen dataclass, frozenset, @property, ayrı kontrol metodları, logging |

## Standart Tool Sablonu

```python
# -*- coding: utf-8 -*-
"""ornek_tool.py — Aciklama."""

from __future__ import annotations
from typing import Any

_VAR: Any = None  # Lazy

def _get_var():
    global _VAR
    if _VAR is None:
        from module import Class  # gec import
        _VAR = Class()
    return _VAR

def run(param: str = "") -> str:
    if not param:
        return "[Hata]: param parametresi gerekli."
    try:
        obj = _get_var()
        return str(obj.islem(param))
    except Exception as e:
        return f"[Hata]: {e}"

def motor_kaydet(motor) -> None:
    motor._plugin_arac_kaydet("ORNEK", run, "Aciklama")
```

## Motor'a Kayit

### Yöntem 1: _plugin_moduller_yukle() (Basit Tool'lar İçin)

Her yeni tool `motor.py`'de `_plugin_moduller_yukle()` listesine eklenir:

```python
"tools.ornek_tool",
```

### Yöntem 2: Erken kontrol ile calistir() (Registry/Plugin Öncesi)

Bazı tool'lar ToolRegistry veya PluginManager tarafından intercept edilir ve `_fallback_calistir()`'e hiç ulaşamaz. Çözüm: `calistir()` metoduna, Registry/Plugin kontrollerinden **önce** erken bir kontrol ekle.

```python
# motor.py — calistir() metodu içinde, RISKLI kontrolünden sonra, Paralel/PARALLEL_CALISTIR'dan önce:

# HATA_COZUCU araçları — Registry/Plugin öncesi erken kontrol
if arac in ("HATA_WATCH_BASLAT", "HATA_WATCH_DURDUR", "HATA_KOD_AL",
             "TERMINAL_HATA_PARSE", "COZUM_UYGULA"):
    try:
        from hata_cozucu import HataWatchdog, HataKoduUretici, TerminalHataParser, CozumUygulayici
        # Singleton pattern: bir kere oluştur, sonra tekrar kullan
        if not hasattr(self, "_hata_watchdog"):
            self._hata_watchdog = HataWatchdog()
            self._hata_kod = HataKoduUretici()
            self._hata_terminal = TerminalHataParser()
            self._hata_cozum = CozumUygulayici(self._hata_kod)
        if arac == "HATA_WATCH_BASLAT":
            self._hata_watchdog.baslat()
            return "[HataWatchdog] Baslatildi."
        if arac == "HATA_KOD_AL":
            kayit = self._hata_kod.kaydet(params[0] if params else "Bilinmeyen hata")
            return f"[HataKod] {kayit.kod}: [{kayit.kategori}] {kayit.ozet}"
        # ... diğer araçlar
    except Exception as e:
        return f"[Hata]: hata_cozucu: {e}"

# sonra normal akış:
# Paralel araç çalıştırma
if arac == "PARALLEL_CALISTIR":
    ...
# 1. ToolRegistry ile dene
# 2. PluginManager ile dene
# 3. Fallback if/else zinciri
```

**Neden:** ToolRegistry `HATA_KOD_AL` gibi yeni araçları tanımasa bile bazen varsayılan bir yanıt döndürür (`startswith("[Bilinmeyen arac]")` kontrolünü geçemez). PluginManager da (`arac.lower()` ile) bazı araçları yakalayıp KeyError fırlatmak yerine hata metni döndürebilir. Erken kontrol bu durumları bypass eder.

**3 adımda tool ekleme:**
1. `TOOLSET_GRUPLARI`'na yeni grup/grup üyesi ekle
2. `_DURUM_MESAJLARI`'na açıklama ekle
3. `calistir()`'a erken kontrol ekle (Registry/Plugin öncesi)

## hata_cozucu.py — 4 Bileşenli Hata Yönetimi

Hata tespit, kodlama ve çözüm modülü. `motor.py`'ye 5 araç olarak entegre edilmiştir.

| Bileşen | Sınıf | Açıklama | Araç Adı |
|---------|-------|----------|----------|
| Watchdog | HataWatchdog | mss + OCR ile ekranı tara, hata dialog'u bul | HATA_WATCH_BASLAT/DURDUR |
| Kod Üretici | HataKoduUretici | HATA-XXXX formatlı kod + .md kayıt | HATA_KOD_AL |
| Terminal Parser | TerminalHataParser | PowerShell/cmd çıktısından hata ayıkla | TERMINAL_HATA_PARSE |
| Çözüm Uygulayıcı | CozumUygulayici | Kullanıcı çözümünü dosyaya patch olarak uygula | COZUM_UYGULA |

Detaylar için: `software-development/reymen-tool-patterns/references/hata-cozucu-arch.md`

## Pitfall'lar

| Hata | Cozum |
|------|-------|
| `liste` eylemi → `store.son_oturumlar()` bulunamadi | `dir(store)` ile gercek method adlarini kontrol et, uymuyorsa fallback mesaj goster |
| SQLite DDL → `incomplete input` | Trigger'lar noktali virgul icerdigi icin `split(";")` bozar. **`executescript()`** ile tek seferde gonder |
| FTS5 kontrolu → `SELECT fts5(?)` hata veriyor | `SELECT sqlite_compileoption_get(0)` ile "FTS5" string'i ara |
| `context_tool.py` → `compress()` missing 1 argument | `AdvancedContextCompressor.compress(mesajlar)` gerektirir — tool disindan cagrilamaz, sadece ReAct dongusu icinde calisir |
| Docker `from_env()` hatasi | `import docker` basarili ama daemon calismiyor. `ping()` ile ek kontrol ekle, fallback local subprocess'e dus |
| Regex `+` karakteri → `re.error: nothing to repeat` | PowerShell ciktisindaki `+` karakteri regex'de escape edilmeli: `r"+"` yerine `r"\+"`. Ham `+` regex'de "1 veya daha fazla" anlamina gelir, ancak satir basindaysa `nothing to repeat` hatasi verir. |
| Regex `(?:Hata|Error)\s*[:：]\s*(.+)` — Turkish colon | Windows hata mesajlarinda hem `:` (ASCII) hem `：` (full-width) kullanilir. Regex'te `[:：]` character class'i ile her ikisini de kapsa. |
| ToolRegistry/PluginManager yeni araclari intercept eder | Erken kontrol ekle (Yontem 2). `calistir()`'da Registry/Plugin oncesi araclari kontrol et. |

```bash
python -m py_compile tools/ornek_tool.py
python -m pytest tests/ -v
```
