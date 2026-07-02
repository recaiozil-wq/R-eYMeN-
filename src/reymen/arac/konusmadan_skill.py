# -*- coding: utf-8 -*-
"""
konusmadan_skill.py — Konuşma geçmişinden otomatik skill çıkarma.

Bir görev başarıyla tamamlandığında:
  1. Konuşma mesajlarını analiz et
  2. LLM ile çözüm pattern'ini çıkar
  3. SKILL.md formatında kaydet
  4. FTS5 index'e ekle

Kullanım:
  from reymen.arac.konusmadan_skill import konusmadan_skill_cikar

  # Otomatik (conversation_loop sonunda)
  konusmadan_skill_cikar(messages, basari=True)

  # Manuel (kullanıcı komutu)
  konusmadan_skill_cikar(messages, basari=True, zorla=True)
"""

import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Sabitler ──────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent  # reymen/
SKILLS_DIR = ROOT / "cereyan" / ".ReYMeN" / "skills"
INDEX_DB = ROOT / "cereyan" / ".ReYMeN" / "skills_index.db"
_MAKS_ACIKLAMA = 300
_MAKS_ADIM = 2000
_MIN_MESAJ_SAYISI = 3  # En az 3 mesaj varsa skill çıkar
_BASARI_ESIĞI = 0.4  # Başarı puanı eşiği (0.0-1.0)

# ── LLM Sağlayıcı ─────────────────────────────────────────
try:
    from reymen.cereyan.beyin import Beyin as _Beyin
    _LLM_HAZIR = True
except ImportError:
    _LLM_HAZIR = False

try:
    from reymen.arac.skill_utils import skill_olustur, skill_index_yenile
    _SKILL_UTILS_HAZIR = True
except ImportError:
    _SKILL_UTILS_HAZIR = False


def _mesajlari_ozetle(messages: List[Dict[str, Any]]) -> str:
    """Konuşma mesajlarını LLM'e gönderilebilir metne çevir."""
    parcalar = []
    for m in messages[-20:]:  # Son 20 mesaj
        rol = m.get("role", "bilinmeyen")
        icerik = m.get("content", "")
        if isinstance(icerik, list):
            for p in icerik:
                if isinstance(p, dict):
                    if p.get("type") == "text":
                        icerik = p["text"][:500]
                    elif p.get("type") == "tool_use":
                        icerik = f"[ARAÇ: {p.get('name', '?')}(...)]"
                    elif p.get("type") == "tool_result":
                        icerik = f"[SONUÇ: {str(p.get('content', ''))[:200]}]"
        elif isinstance(icerik, str):
            icerik = icerik[:500]
        parcalar.append(f"[{rol.upper()}] {icerik}")
    return "\n".join(parcalar)


def _skill_adi_ureti(ozet: str, konu: str = "") -> str:
    """Konuşma özetinden skill adı üret."""
    ad = (konu or ozet)[:60].lower()
    ad = re.sub(r'[^a-z0-9\s-]', '', ad)
    ad = re.sub(r'\s+', '-', ad.strip())
    ad = re.sub(r'-+', '-', ad)
    return ad[:50] or f"konusma_skill_{int(time.time())}"


def _beceri_puani_hesapla(messages: List[Dict]) -> float:
    """Konuşmanın skill olmaya değer olup olmadığını hesapla."""
    if len(messages) < _MIN_MESAJ_SAYISI:
        return 0.0

    puan = 0.0

    # Kriter 1: Araç kullanımı var mı?
    arac_sayisi = 0
    for m in messages:
        if m.get("role") == "assistant":
            icerik = m.get("content") or []
            if isinstance(icerik, list):
                for p in icerik:
                    if isinstance(p, dict) and p.get("type") == "tool_use":
                        arac_sayisi += 1
    if arac_sayisi > 0:
        puan += 0.3

    # Kriter 2: Kullanıcı mesajı yeterince uzun mu?
    kullanici_mesajlari = [m for m in messages if m.get("role") == "user"]
    uzun_mesaj = sum(1 for m in kullanici_mesajlari if len(str(m.get("content", ""))) > 100)
    if uzun_mesaj > 0:
        puan += 0.2

    # Kriter 3: Tool sonuçları var mı?
    sonuc_sayisi = sum(1 for m in messages if m.get("role") == "tool")
    if sonuc_sayisi > 0:
        puan += 0.2

    # Kriter 4: Asistan yanıtı uzun mu?
    asistan_mesajlari = [m for m in messages if m.get("role") == "assistant"]
    uzun_yanit = 0
    for m in asistan_mesajlari:
        icerik = m.get("content", "")
        if isinstance(icerik, str) and len(icerik) > 200:
            uzun_yanit += 1
        elif isinstance(icerik, list):
            for p in icerik:
                if isinstance(p, dict) and p.get("type") == "text" and len(p.get("text", "")) > 200:
                    uzun_yanit += 1
    if uzun_yanit > 0:
        puan += 0.3

    return min(puan, 1.0)


def _llm_ile_skill_cikar(mesaj_ozeti: str, konu: str = "") -> Optional[Dict[str, str]]:
    """LLM kullanarak konuşmadan skill çıkar."""
    if not _LLM_HAZIR:
        logger.warning("[KonusmadanSkill] LLM hazir degil, skill cikarilamadi")
        return None

    try:
        beyin = _Beyin()
        prompt = f"""Bir kullanıcı ile AI asistan arasındaki konuşmayı analiz et ve bir SKILL.md olarak kaydetmek için JSON çıktısı ver.

KONUŞMA ÖZETİ:
{mesaj_ozeti[:3000]}

Aşağıdaki JSON formatında çıktı ver (sadece JSON, başka metin yok):
{{
  "ad": "skill_adi (kucuk harf, tire-ile-ayrilmis)",
  "baslik": "Kısa açıklayıcı başlık",
  "aciklama": "Ne işe yarar, ne zaman kullanılır (max 300 karakter)",
  "etiketler": ["etiket1", "etiket2", "etiket3"],
  "kategori": "kategori_adi",
  "adimlar": "Adım adım çözüm talimatları (Markdown, max 2000 karakter)",
  "trigger_kelimeler": ["kelime1", "kelime2"],
  "guven_skoru": 0.85
}}

Kurallar:
- adimlar: somut, adım adım, tekrarlanabilir olmalı
- guven_skoru: 0.0-1.0 arası, konuşmanın skill olmaya ne kadar uygun olduğu
- Eğer konuşma basit bir selamlaşma veya anlamlı bir çözüm içermiyorsa guven_skoru düşük ver
"""

        yanit = beyin.soru(prompt)
        if not yanit:
            return None

        # JSON çıktısını ayıkla
        json_match = re.search(r'\{.*\}', yanit, re.DOTALL)
        if not json_match:
            return None

        data = json.loads(json_match.group())
        return data

    except Exception as e:
        logger.warning("[KonusmadanSkill] LLM hatasi: %s", e)
        return None


def konusmadan_skill_cikar(
    messages: List[Dict[str, Any]],
    basari: bool = True,
    zorla: bool = False,
    konu: str = "",
) -> str:
    """Konuşma mesajlarından skill çıkar ve kaydet.

    Args:
        messages: Konuşma mesaj listesi.
        basari: Görev başarılı mı?
        zorla: Zorla skill çıkar (puan kontrolünü atla).
        konu: İsteğe bağlı konu başlığı.

    Returns:
        Durum mesajı.
    """
    if not _SKILL_UTILS_HAZIR:
        return "[KonusmadanSkill] skill_utils hazir degil"

    if not messages:
        return "[KonusmadanSkill] Mesaj yok"

    if not basari and not zorla:
        return "[KonusmadanSkill] Gorev basarisiz, skill cikarilmadi"

    # Beceri puanı hesapla
    puan = _beceri_puani_hesapla(messages)
    if puan < _BASARI_ESIĞI and not zorla:
        return f"[KonusmadanSkill] Dusuk puan ({puan:.2f} < {_BASARI_ESIĞI}), skill cikarilmadi"

    # Mesajları özetle
    ozet = _mesajlari_ozetle(messages)

    # LLM ile skill çıkar
    skill_data = _llm_ile_skill_cikar(ozet, konu)
    if not skill_data:
        # LLM yoksa basit şablonla skill oluştur
        return _basit_skill_kaydet(ozet, konu)

    guven = skill_data.get("guven_skoru", 0.0)
    if guven < 0.3 and not zorla:
        return f"[KonusmadanSkill] LLM guven skoru dusuk ({guven:.2f}), skill cikarilmadi"

    ad = skill_data.get("ad", _skill_adi_ureti(ozet, konu))
    baslik = skill_data.get("baslik", ad)
    aciklama = skill_data.get("aciklama", "")[:_MAKS_ACIKLAMA]
    etiketler = skill_data.get("etiketler", [])
    kategori = skill_data.get("kategori", "konusma")
    adimlar = skill_data.get("adimlar", "")[:_MAKS_ADIM]
    trigger_kelimeler = skill_data.get("trigger_kelimeler", [])

    if not aciklama:
        return "[KonusmadanSkill] Aciklama bos, skill cikarilmadi"

    # SKILL.md dosyasina yaz
    try:
        etiket_str = ", ".join(f'"{e}"' for e in etiketler)
        trigger_str = ", ".join(f'"{t}"' for t in trigger_kelimeler)

        skill_md = f"""---
name: {ad}
title: "{baslik}"
description: "{aciklama}"
tags: [{etiket_str}]
category: {kategori}
audience: user
triggers: [{trigger_str}]
created_from: conversation
confidence: {guven:.2f}
created_at: {datetime.now().strftime("%Y-%m-%d %H:%M")}

---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI kullanıcısı |
| **Ne** | {baslik} |
| **Nerede** | `{kategori}/{ad}.md` |
| **Ne Zaman** | İlgili görev gerektiğinde |
| **Neden** | {aciklama} |

{adimlar}
"""
        hedef_klasor = SKILLS_DIR / kategori / ad
        hedef_klasor.mkdir(parents=True, exist_ok=True)
        hedef_dosya = hedef_klasor / "SKILL.md"
        hedef_dosya.write_text(skill_md, encoding="utf-8")

        skill_index_yenile(zorla=True)

        logger.info("[KonusmadanSkill] ✅ Skill olusturuldu: %s (guven=%.2f) -> %s", ad, guven, hedef_dosya)
        return f"[KonusmadanSkill] ✅ '{ad}' skill'i olusturuldu (guven: {guven:.0%})"

    except Exception as e:
        logger.error("[KonusmadanSkill] Skill kayit hatasi: %s", e)
        return f"[KonusmadanSkill] Hata: {e}"


def _basit_skill_kaydet(ozet: str, konu: str = "") -> str:
    """LLM yokken basit şablonla skill kaydet."""
    ad = _skill_adi_ureti(ozet, konu)
    baslik = konu or ad.replace("-", " ").title()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    skill_md = f"""---
name: {ad}
title: "{baslik}"
description: "Konusmadan cikarilmis cozum: {baslik}"
tags: ["konusma", "otomatik"]
category: konusma
audience: user
triggers: []
created_from: conversation
created_at: {timestamp}

---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI kullanıcısı |
| **Ne** | {baslik} |
| **Nerede** | `konusma/{ad}.md` |
| **Ne Zaman** | İlgili görev gerektiğinde |
| **Neden** | Konuşmadan çıkarılan çözüm |

## Çözüm Adımları

1. **Problem:** {baslik}
2. **Çözüm:** Konuşma içinde çözülmüştür. Detaylar için skill içeriğine bakın.

## Kullanım

Bu skill otomatik olarak bir konuşmadan çıkarılmıştır.
İlgili bir görev geldiğinde bu skill devreye girecektir.
"""

    try:
        # Direkt SKILLS_DIR'e yaz (skill_olustur yanlis ROOT kullaniyor)
        hedef_klasor = SKILLS_DIR / "konusma" / ad
        hedef_klasor.mkdir(parents=True, exist_ok=True)
        hedef_dosya = hedef_klasor / "SKILL.md"
        hedef_dosya.write_text(skill_md, encoding="utf-8")

        skill_index_yenile(zorla=True)
        logger.info("[KonusmadanSkill] ✅ Basit skill olusturuldu: %s -> %s", ad, hedef_dosya)
        return f"[KonusmadanSkill] ✅ '{ad}' basit skill olusturuldu ({hedef_dosya})"
    except Exception as e:
        logger.error("[KonusmadanSkill] Basit kayit hatasi: %s", e)
        return f"[KonusmadanSkill] Hata: {e}"


# ── Motor'a kayıt ─────────────────────────────────────────
def motor_kaydet(motor: object) -> None:
    """Motor'a konusmadan_skill_cikar aracini kaydet."""
    try:
        motor.kaydet(
            "KONUSMADAN_SKILL",
            konusmadan_skill_cikar,
            "Konusma gecmisinden skill cikar ve kaydet. "
            "Parametre: messages=[...], basari=True/False, zorla=True/False, konu='...'"
        )
        logger.info("[KonusmadanSkill] Motor'a kaydedildi")
    except Exception as e:
        logger.warning("[KonusmadanSkill] Motor kayit hatasi: %s", e)
