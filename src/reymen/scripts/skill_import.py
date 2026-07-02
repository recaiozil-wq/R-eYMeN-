"""ReYMeN skill'lerini ReYMeN formatına dönüştür.
Kullanım: python reymen/scripts/skill_import.py [--kategori AI_ML,DevOps]

Hermes: ~/AppData/Local/hermes/skills/<kategori>/<skill>/SKILL.md
ReYMeN: reymen/cereyan/skills/Skiller/<kategori>/<skill>_SKILL.md (düz dosya)
"""
import os, re, shutil
from pathlib import Path

HERMES_SKILLS = Path.home() / "AppData/Local/hermes/skills"
REYMEN_SKILLS = Path(__file__).parent.parent / "cereyan/skills/Skiller"

# Kategori eşleme: ReYMeN → ReYMeN
KATEGORI_MAP = {
    "devops": "DevOps",
    "data-science": "AI_ML",
    "mlops": "AI_ML",
    "mlops/inference": "AI_ML",
    "mlops/evaluation": "AI_ML",
    "mlops/models": "AI_ML",
    "mlops/research": "AI_ML",
    "software-development": "Yazilim",
    "software": "Yazilim",
    "security": "Guvenlik",
    "kali-pentest": "Guvenlik",
    "windows-automation": "Windows",
    "windows": "Windows",
    "productivity": "Verimlilik",
    "note-taking": "Verimlilik",
    "creative": "Medya",
    "media": "Medya",
    "gaming": "Medya",
    "github": "DevOps",
    "mcp": "MCP",
    "autonomous-ai-agents": "AI_ML",
    "user-preferences": "Kullanici",
    "workflow": "Surec",
    "user-preferences/hersona/skills": "Kullanici",
}

def skill_aktar(hedef_klasor: str = "", limit: int = 0):
    """ReYMeN skill'lerini ReYMeN formatına çevir."""
    hedef = REYMEN_SKILLS
    if hedef_klasor:
        hedef = hedef / hedef_klasor
    hedef.mkdir(parents=True, exist_ok=True)

    aktarilan = 0
    for kategori_dizini in sorted(HERMES_SKILLS.iterdir()):
        if not kategori_dizini.is_dir():
            continue

        # Kategori eşle
        reymen_kat = KATEGORI_MAP.get(kategori_dizini.name, "Diger")
        if hedef_klasor and reymen_kat != hedef_klasor:
            continue

        for skill_dizini in sorted(kategori_dizini.iterdir()):
            skill_md = skill_dizini / "SKILL.md"
            if not skill_md.exists():
                continue

            # ReYMeN formatı: <kategori>/<skill>/SKILL.md
            # ReYMeN formatı: <kategori>/<skill>_SKILL.md (düz dosya)
            icerik = skill_md.read_text("utf-8", errors="replace")

            # Frontmatter'ı temizle (ReYMeN formatına uygun)
            icerik = re.sub(r'^---\n.*?\n---\n', '', icerik, flags=re.DOTALL | re.MULTILINE)
            icerik = icerik.strip()

            # Dosya adı: "skill_adi_SKILL.md"
            dosya_adi = f"{skill_dizini.name}_SKILL.md"
            hedef_klasor_path = hedef / reymen_kat
            hedef_klasor_path.mkdir(parents=True, exist_ok=True)
            (hedef_klasor_path / dosya_adi).write_text(icerik, "utf-8")

            aktarilan += 1
            if limit and aktarilan >= limit:
                return aktarilan

    return aktarilan

def skill_say():
    """ReYMeN ve ReYMeN'deki skill sayılarını göster."""
    ReYMeN = sum(1 for k in HERMES_SKILLS.iterdir() if k.is_dir()
                 for s in k.iterdir() if (s / "SKILL.md").exists())
    reymen = sum(1 for f in REYMEN_SKILLS.rglob("*_SKILL.md"))
    return {"ReYMeN": ReYMeN, "reymen": reymen, "eksik": ReYMeN - reymen}

if __name__ == "__main__":
    import sys
    hedef = sys.argv[1] if len(sys.argv) > 1 else ""
    lim = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    once = skill_say()
    print(f"ReYMeN skill: {once['ReYMeN']} | ReYMeN skill: {once['reymen']}")

    adet = skill_aktar(hedef, lim)
    sonra = skill_say()

    print(f"Aktarilan: {adet} skill")
    print(f"ReYMeN toplam: {sonra['reymen']} (önce: {once['reymen']})")
    print(f"Hala eksik: {sonra['eksik']}")
