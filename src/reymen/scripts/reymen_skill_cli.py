# -*- coding: utf-8 -*-
"""reymen_skill_cli.py — SkillCLI: dosya tabanlı skill yönetim arayüzü.

Export:
    SkillCLI — ana sınıf

Test: tests/test_reymen_skill_cli.py
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional


class SkillCLI:
    """Dosya tabanlı skill deposu.

    Dizin yapısı::

        skill_yolu/
            kategori/
                skill_adi/
                    SKILL.md   (YAML frontmatter + içerik)

    Parametreler:
        skill_yolu: Skill'lerin saklanacağı dizin (str veya Path).
    """

    def __init__(self, skill_yolu: str) -> None:
        self._kok = Path(skill_yolu)
        self._kok.mkdir(parents=True, exist_ok=True)

    # ═══════════════════════════════════════════════════════════════════
    # Yardımcı / internal metodlar
    # ═══════════════════════════════════════════════════════════════════

    def _tum_dosyalar(self) -> List[Path]:
        """Tüm SKILL.md dosyalarını (sıralı) döndürür."""
        if not self._kok.exists():
            return []
        return sorted(self._kok.rglob("SKILL.md"))

    def _meta_oku(self, md_dosyasi: Path) -> Dict[str, Any]:
        """SKILL.md dosyasındaki YAML frontmatter'ı parse eder.

        Dönüş: {"aciklama": str, "tags": list[str]}
        """
        try:
            ham = md_dosyasi.read_text(encoding="utf-8")
        except Exception:
            return {"aciklama": "", "tags": []}

        aciklama = ""
        etiketler: List[str] = []

        if not ham.startswith("---"):
            return {"aciklama": aciklama, "tags": etiketler}

        end = ham.find("---", 3)
        if end == -1:
            return {"aciklama": aciklama, "tags": etiketler}

        frontmatter = ham[3:end].strip()
        for satir in frontmatter.splitlines():
            if ":" not in satir:
                continue
            key, _, val = satir.partition(":")
            key = key.strip()
            val = val.strip()
            if key == "description":
                aciklama = val
            elif key == "tags":
                etiketler = [t.strip() for t in val.split(",") if t.strip()]

        return {"aciklama": aciklama, "tags": etiketler}

    def _skill(self, name: str) -> Optional[Path]:
        """Adı verilen skill'in SKILL.md yolunu bulur (bulamazsa None)."""
        for md in self._tum_dosyalar():
            if md.parent.name == name:
                return md
        return None

    # ═══════════════════════════════════════════════════════════════════
    # Türkçe metodlar (test uyumluluğu)
    # ═══════════════════════════════════════════════════════════════════

    def liste(self, kategori: Optional[str] = None) -> List[Dict[str, Any]]:
        """Tüm skill'leri listeler.

        Parametreler:
            kategori: Sadece bu kategoridekileri getir (None = tümü).

        Dönüş: Sıralı sözlük listesi —
               [{"ad", "kategori", "aciklama", "tags"}, ...]
        """
        sonuc: List[Dict[str, Any]] = []
        for md in self._tum_dosyalar():
            kat = md.parent.parent.name
            if kategori is not None and kat != kategori:
                continue
            meta = self._meta_oku(md)
            sonuc.append({
                "ad": md.parent.name,
                "kategori": kat,
                "aciklama": meta["aciklama"],
                "tags": meta["tags"],
            })
        sonuc.sort(key=lambda s: s["ad"])
        return sonuc

    def goruntule(self, name: str) -> Optional[str]:
        """Bir skill'in SKILL.md dosyasının tüm içeriğini döndürür.

        Bulamazsa None döner.
        """
        md = self._skill(name)
        if md is None:
            return None
        return md.read_text(encoding="utf-8")

    def kategori_liste(self) -> List[str]:
        """Mevcut tüm kategorileri alfabetik sırada döndürür."""
        kategoriler: set[str] = set()
        for md in self._tum_dosyalar():
            kategoriler.add(md.parent.parent.name)
        return sorted(kategoriler)

    def istatistik(self) -> Dict[str, Any]:
        """Skill deposu istatistikleri.

        Dönüş: {"toplam_skill": int, "kategori_sayisi": int, "kategoriler": list[str]}
        """
        skills = self.liste()
        kategoriler = sorted({s["kategori"] for s in skills})
        return {
            "toplam_skill": len(skills),
            "kategori_sayisi": len(kategoriler),
            "kategoriler": kategoriler,
        }

    # ═══════════════════════════════════════════════════════════════════
    # İngilizce alias metodlar (task spesifikasyonu)
    # ═══════════════════════════════════════════════════════════════════

    def list_skills(self) -> List[Dict[str, Any]]:
        """Tüm skill'leri listeler (İngilizce alias)."""
        return self.liste()

    def create_skill(self, name: str, content: str) -> str:
        """Yeni bir skill oluşturur.

        Varsayılan kategori 'genel' altında skil_adi/SKILL.md yazar.

        Parametreler:
            name: Skill adı (dizin adı olarak kullanılır).
            content: SKILL.md içeriği (frontmatter + markdown).

        Dönüş: Kaydedilen içerik metni.
        """
        kategori = "genel"
        skill_dizini = self._kok / kategori / name
        skill_dizini.mkdir(parents=True, exist_ok=True)
        md = skill_dizini / "SKILL.md"
        md.write_text(content, encoding="utf-8")
        return content

    def view_skill(self, name: str) -> Optional[str]:
        """Bir skill'in içeriğini döndürür (İngilizce alias)."""
        return self.goruntule(name)

    def delete_skill(self, name: str) -> bool:
        """Bir skill'i siler.

        Dönüş: Başarılıysa True, skill bulunamazsa False.
        """
        md = self._skill(name)
        if md is None:
            return False
        shutil.rmtree(md.parent)
        return True

    def search_skills(self, query: str) -> List[Dict[str, Any]]:
        """Skill adı ve içeriğinde arama yapar (büyük/küçük harf duyarsız).

        Dönüş: Sıralı sözlük listesi —
               [{"ad", "kategori", "aciklama", "tags"}, ...]
        """
        q = query.lower()
        sonuc: List[Dict[str, Any]] = []
        for md in self._tum_dosyalar():
            try:
                icerik = md.read_text(encoding="utf-8").lower()
            except Exception:
                icerik = ""
            skill_adi = md.parent.name
            if q in skill_adi.lower() or q in icerik:
                meta = self._meta_oku(md)
                sonuc.append({
                    "ad": skill_adi,
                    "kategori": md.parent.parent.name,
                    "aciklama": meta["aciklama"],
                    "tags": meta["tags"],
                })
        sonuc.sort(key=lambda s: s["ad"])
        return sonuc
