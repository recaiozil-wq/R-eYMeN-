#!/usr/bin/env python3
"""reymen_skills_to_skillmd.py — Tüm ReYMeN skill'lerini SKILL.md formatına dönüştürür.

Yaptıkları:
  1. Kategori etiketli (> **Kategori:**) dosyalara frontmatter ekler
  2. Frontmatter'ı olan ama eksik alanlı dosyaları tamamlar
  3. Body'deki eski --- ve kategori etiketlerini temizler

Kullanım: python reymen/scripts/reymen_skills_to_skillmd.py
"""

import os
import re
import sys
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

try:
    import yaml
except ImportError:
    print("HATA: PyYAML gerekli. pip install pyyaml")
    sys.exit(1)

SKILLS_DIR = Path("reymen/cereyan/skills")
STATS = {"total": 0, "fm_ok": 0, "fm_fixed": 0, "kategori_to_fm": 0, "error": 0}


def _kategori_adi(path: Path) -> str:
    """Dosyanin ait oldugu kategoriyi dondurur."""
    parent = path.parent.name
    grandparent = path.parent.parent.name
    if grandparent == "skills":
        return parent
    return parent


def _dosya_adindan_title(name: str) -> str:
    """Dosya adindan okunabilir baslik olusturur."""
    name = name.replace(".md", "")
    name = re.sub(r'^reymen[-_]', '', name)
    name = re.sub(r'^autonomous-ai-agents[-_]', '', name)
    name = re.sub(r'^security[-_]', '', name)
    name = name.replace('-', ' ').replace('_', ' ')
    return name.strip().title()


def _body_temizle(body: str) -> str:
    """Body'deki baslangictaki --- ve kategori etiketlerini temizler."""
    # CRLF -> LF (Windows dosyalari icin)
    body = body.replace('\r\n', '\n')
    body = re.sub(r'^>\s*\*\*Kategori:\*\*.*\n?', '', body, flags=re.MULTILINE)
    body = re.sub(r'^\*\*Kategori:\*\*.*\n?', '', body, flags=re.MULTILINE)
    body = body.strip()
    body = re.sub(r'^---\s*\n?', '', body, flags=re.MULTILINE)
    return body.strip()


def _frontmatter_parse(content: str) -> tuple:
    """Varolan frontmatter'i parse et. (fm_dict, body, has_fm) dondur."""
    m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not m:
        return {}, content, False
    try:
        fm = yaml.safe_load(m.group(1))
        if not isinstance(fm, dict):
            fm = {}
    except Exception:
        fm = {}
    body = content[m.end():]
    body = _body_temizle(body)
    return fm, body, True


def _frontmatter_olustur(fm: dict, kategori: str, dosya_adi: str) -> str:
    """Eksik alanlari doldurarak YAML frontmatter stringi olusturur."""
    if not fm.get("name"):
        fm["name"] = dosya_adi.replace(".md", "").lower()
    if not fm.get("title"):
        fm["title"] = _dosya_adindan_title(dosya_adi)
    if not fm.get("description"):
        fm["description"] = ""
    if not fm.get("tags"):
        fm["tags"] = [kategori.lower()]
    elif isinstance(fm["tags"], str):
        fm["tags"] = [fm["tags"]]
    if not fm.get("category"):
        fm["category"] = kategori
    if not fm.get("audience"):
        fm["audience"] = "agent"

    clean = {
        "name": fm["name"],
        "title": fm["title"],
        "description": fm["description"],
        "tags": fm["tags"],
        "category": fm["category"],
        "audience": fm["audience"],
    }
    return yaml.dump(clean, default_flow_style=False, allow_unicode=True, sort_keys=False).strip()


def process_file(path: Path) -> str:
    """Tek bir dosyayi SKILL.md formatina donusturur. 'ok'/'fixed'/'error' dondurur."""
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return f"error: {e}"

    kategori = _kategori_adi(path)
    dosya_adi = path.name

    # Frontmatter var mi?
    fm, body, has_fm = _frontmatter_parse(content)

    if has_fm:
        # Frontmatter var — eksik alanlari doldur
        title_ok = bool(fm.get("title"))
        desc_ok = bool(fm.get("description"))
        tags_ok = bool(fm.get("tags"))
        aud_ok = bool(fm.get("audience"))
        cat_ok = bool(fm.get("category"))
        if title_ok and desc_ok and tags_ok and aud_ok and cat_ok:
            return "ok"  # Zaten tam

        new_fm = _frontmatter_olustur(fm, kategori, dosya_adi)
        output = f"---\n{new_fm}\n---\n{body}"
        path.write_text(output, encoding="utf-8")
        return "fixed"

    # Frontmatter yok — kategori etiketi var mi?
    kat_from_tag = ""
    m = re.search(r'>\s*\*\*Kategori:\*\*\s*(\S+)', content)
    if m:
        kat_from_tag = m.group(1).strip()
    if kat_from_tag:
        kategori = kat_from_tag

    body = _body_temizle(content)

    new_fm = _frontmatter_olustur({}, kategori, dosya_adi)
    output = f"---\n{new_fm}\n---\n{body}"
    path.write_text(output, encoding="utf-8")
    return "kategori_to_fm"


def main():
    print("🔄 ReYMeN skill'leri SKILL.md formatina donusturuluyor...\n")

    md_files = sorted(SKILLS_DIR.rglob("*.md"))
    STATS["total"] = len(md_files)

    for path in md_files:
        result = process_file(path)
        if result == "ok":
            STATS["fm_ok"] += 1
        elif result == "fixed":
            STATS["fm_fixed"] += 1
        elif result == "kategori_to_fm":
            STATS["kategori_to_fm"] += 1
        else:
            STATS["error"] += 1
            print(f"  ❌ {path.relative_to(SKILLS_DIR.parent)}: {result}")

    print(f"\n📊 Sonuc:")
    print(f"  Toplam dosya:     {STATS['total']}")
    print(f"  Zaten tam:        {STATS['fm_ok']}")
    print(f"  Eksik duzeltildi: {STATS['fm_fixed']}")
    print(f"  Kategori->FM:     {STATS['kategori_to_fm']}")
    print(f"  Hata:             {STATS['error']}")
    print("\n✅ Tamamlandi.")


if __name__ == "__main__":
    main()
