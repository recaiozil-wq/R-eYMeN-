#!/usr/bin/env python3
"""Tüm skilleri 27 kategori altında topla - 5N1K sistemine göre"""
import os, shutil, sys

SKILLER = r"C:\Users\marko\Desktop\Reymen Proje\hermes_projesi\reymen\cereyan\skills\Skiller"
ReYMeN = r"C:\Users\marko\.ReYMeN\skills"
PROFIL = r"C:\Users\marko\AppData\Local\hermes\profiles\kiral38\skills"

# Kategori eşleştirme - her skill klasör adı hangi kategoriye gider?
KATEGORI = {
    # AI_ML (varsayılan)
    "default": "AI_ML",
    # Özel eşleşmeler
    "android": "android", "apple": "apple",
    "creative": "Yaratici", "design": "Yaratici", "p5js": "Yaratici",
    "excalidraw": "Yaratici", "manim": "Yaratici", "ascii": "Yaratici",
    "stable-diffusion": "Yaratici", "image-gen": "Yaratici",
    "data-science": "veri-bilimi", "jupyter": "veri-bilimi",
    "devops": "DevOps", "docker": "DevOps", "kubernetes": "DevOps",
    "container": "DevOps", "deploy": "DevOps", "infra": "DevOps",
    "monitoring": "DevOps", "ci-": "DevOps", "cicd": "DevOps",
    "email": "Verimlilik", "productivity": "Verimlilik",
    "notion": "Verimlilik", "workflow": "Verimlilik",
    "ocr": "Verimlilik", "todo": "Verimlilik",
    "github": "Github",
    "media": "Medya", "video": "Medya", "audio": "Medya",
    "youtube": "Medya", "stream": "Medya", "remotion": "Medya",
    "gaming": "Gaming", "game": "Gaming",
    "kali": "Guvenlik", "pentest": "Guvenlik", "security": "Guvenlik",
    "safety": "Guvenlik", "exploit": "Guvenlik", "attack": "Guvenlik",
    "malware": "Guvenlik", "cyber": "Guvenlik",
    "network": "Ag", "vpn": "Ag", "proxy": "Ag", "dns": "Ag",
    "firewall": "Ag", "router": "Ag", "socket": "Ag",
    "powerbi": "powerbi",
    "research": "Research", "paper": "Research", "arxiv": "Research",
    "smart-home": "smart-home", "home": "smart-home",
    "social": "sosyal-medya", "blog": "sosyal-medya",
    "telegram": "sosyal-medya", "discord": "sosyal-medya",
    "test": "Test", "benchmark": "Test", "qa": "Test",
    "pytest": "Test", "unit-": "Test", "e2e": "Test",
    "tor": "tor", "voice": "voice", "speech": "voice",
    "windows": "Windows",
    "cross-platform": "cross-platform",
    "note": "Egitim", "tutorial": "Egitim", "educat": "Egitim",
    "learn": "Egitim", "course": "Egitim",
    # Kod
    "code": "Kod", "python": "Kod", "rust": "Kod", "react": "Kod",
    "node": "Kod", "spring": "Kod", "sql": "Kod", "postgres": "Kod",
    "redis": "Kod", "web": "Kod", "backend": "Kod", "frontend": "Kod",
    "cli": "Kod", "terminal": "Kod", "shell": "Kod",
    "database": "Kod", "api": "Kod", "browser": "Kod",
    "template": "Kod", "tool": "Kod", "system": "Kod",
}

def kategoribul(ad):
    """Skill adına göre kategori bul"""
    ad_lower = ad.lower().replace("-", " ").replace("_", " ")
    for anahtar, kategori in KATEGORI.items():
        if anahtar != "default" and anahtar in ad_lower:
            return kategori
    return KATEGORI["default"]

def main():
    toplam = 0
    hata = 0
    kaynaklar = {"ReYMeN": ReYMeN, "Profil": PROFIL}
    
    for kaynak_ad, kaynak_yol in kaynaklar.items():
        if not os.path.isdir(kaynak_yol):
            print(f"  {kaynak_ad}: YOL YOK ({kaynak_yol})")
            continue
        
        for klasor in sorted(os.listdir(kaynak_yol)):
            klasor_yol = os.path.join(kaynak_yol, klasor)
            if not os.path.isdir(klasor_yol):
                continue
            
            # Kategori belirle
            kategori = kategoribul(klasor)
            hedef_kat = os.path.join(SKILLER, kategori)
            os.makedirs(hedef_kat, exist_ok=True)
            
            # Tüm .md dosyalarını kopyala
            for kok, dirs, files in os.walk(klasor_yol):
                for f in files:
                    if not f.endswith(".md"):
                        continue
                    kaynak_dosya = os.path.join(kok, f)
                    
                    # Hedef isim: skill_adi_dosyaadi.md
                    rel = os.path.relpath(kok, klasor_yol)
                    if rel == ".":
                        hedef_isim = f"{klasor}_{f}"
                    else:
                        alt = rel.replace(os.sep, "_")
                        hedef_isim = f"{klasor}_{alt}_{f}"
                    
                    hedef_dosya = os.path.join(hedef_kat, hedef_isim)
                    
                    # Üzerine yazma
                    if os.path.exists(hedef_dosya):
                        continue
                    
                    try:
                        shutil.copy2(kaynak_dosya, hedef_dosya)
                        toplam += 1
                    except Exception as e:
                        hata += 1
    
    print(f"\n  Kopyalanan: {toplam}")
    print(f"  Hata: {hata}")
    
    # Sayımları göster
    print(f"\n  KATEGORİ DAĞILIMI:")
    for kat in sorted(os.listdir(SKILLER)):
        kat_yol = os.path.join(SKILLER, kat)
        if os.path.isdir(kat_yol):
            say = len([f for f in os.listdir(kat_yol) if f.endswith(".md")])
            print(f"    {kat}: {say}")
    
    toplam_md = sum(1 for f in os.listdir(SKILLER) if f.endswith(".md"))
    print(f"\n  TOPLAM .md: {toplam_md}")

if __name__ == "__main__":
    main()
