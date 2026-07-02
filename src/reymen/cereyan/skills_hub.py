# -*- coding: utf-8 -*-
"""skills_hub.py — GitHub'dan Skill Indirme.

Uzak GitHub repolarindan skill paketlerini indirir
ve yerel skills klasorune yukler.
"""

import json
import shutil
import tempfile
import zipfile
from pathlib import Path

SKILLS_KLASOR = Path(__file__).parent / ".ReYMeN" / "skills"
HUB_CACHE = SKILLS_KLASOR / "index-cache" / "hub"

# Varsayilan hub kaynaklari
HUBS = {
    "ReYMeN-skills": {
        "url": "https://github.com/Watcher-ReYMeN/ReYMeN-skills/archive/refs/heads/main.zip",
        "aciklama": "Kullaniciya ait ReYMeN-skills reposu",
    },
    "ReYMeN-agent-skills": {
        "url": "https://github.com/nousresearch/ReYMeN-agent-skills/archive/refs/heads/main.zip",
        "aciklama": "Nous Research ReYMeN Agent skills",
    },
}


def hub_listele() -> str:
    """Kullanilabilir hub'lari listele."""
    satirlar = ["[Skills Hub] Kullanilabilir kaynaklar:\n"]
    for ad, bilgi in HUBS.items():
        satirlar.append(f"  {ad}: {bilgi['aciklama']}")
    return "\n".join(satirlar)


def hub_ekle(ad: str, url: str, aciklama: str = ""):
    """Yeni hub kaynagi ekle.

    Args:
        ad: Hub adi
        url: ZIP URL'si
        aciklama: Aciklama
    """
    HUBS[ad] = {"url": url, "aciklama": aciklama or ad}


def hub_indir(hub_adi: str, kategori: str = "") -> str:
    """Bir hub'dan skill indir.

    Args:
        hub_adi: Hub adi (hub_listele'den)
        kategori: Sadece belirli kategori

    Returns:
    °Yüklenen skill sayisi
    """
    hub = HUBS.get(hub_adi)
    if not hub:
        return f"[Hub] Bilinmeyen hub: {hub_adi}"

    HUB_CACHE.mkdir(parents=True, exist_ok=True)

    try:
        import requests
        print(f"[Hub] Indiriliyor: {hub_adi}...")
        r = requests.get(hub["url"], timeout=60)
        if r.status_code != 200:
            return f"[Hub] Indirme hatasi: HTTP {r.status_code}"

        # ZIP'i cache'e kaydet
        zip_yolu = HUB_CACHE / f"{hub_adi}.zip"
        zip_yolu.write_bytes(r.content)

        # Cikar
        once = len(list(SKILLS_KLASOR.rglob("SKILL.md")))
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(zip_yolu, "r") as zf:
                zf.extractall(tmpdir)

            # Kok klasoru bul (repo adiyla)
            tmp_path = Path(tmpdir)
            kok = None
            for d in tmp_path.iterdir():
                if d.is_dir():
                    kok = d
                    break

            if not kok:
                return "[Hub] ZIP icinde klasor bulunamadi."

            # Skill'leri kopyala
            skills_kaynak = kok / "skills"
            if not skills_kaynak.exists():
                return "[Hub] ZIP'te skills/ klasoru yok."

            hedef = SKILLS_KLASOR
            if kategori:
                hedef = hedef / kategori
                hedef.mkdir(parents=True, exist_ok=True)

            for skill_dizini in skills_kaynak.iterdir():
                if skill_dizini.is_dir():
                    skill_hedef = hedef / skill_dizini.name
                    if not skill_hedef.exists():
                        shutil.copytree(skill_dizini, skill_hedef)

        sonra = len(list(SKILLS_KLASOR.rglob("SKILL.md")))
        yeni = sonra - once
        return f"[Hub] Indirme tamam: {yeni} yeni skill (toplam {sonra})"

    except ImportError:
        return "[Hub] requests kutuphanesi gerekli."
    except Exception as e:
        return f"[Hub] Hata: {e}"


if __name__ == "__main__":
    print(hub_listele())
    print("\n[Hub] Indirme testi icin: pip install requests")
