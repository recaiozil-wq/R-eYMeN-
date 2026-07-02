"""
skill_5n1k_otomasyon.py — Cron ile otomatik skill 5N1K formatlama

Her çalıştırmada:
1. reymen/cereyan/skills/ altındaki tüm .md dosyalarını tara
2. 5N1K tablosu olmayanlara auto-ekle (başlıktan/description'dan çıkar)
3. Kategoriye göre doğru alt dizine taşı
4. SKILLS_KATALOG.md'yi güncelle
"""

import os
import re
import shutil
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / "cereyan" / "skills"
KATALOG = SKILLS_DIR / "SKILLS_KATALOG.md"

# Ana kategoriler (alt dizin ismi → emoji + açıklama)
KATEGORILER = {
    "reymen":      ("⚙️", "ReYMeN Özel"),
    "kali":        ("🐉", "Kali Pentest"),
    "windows":     ("🪟", "Windows"),
    "video":       ("🎬", "Video"),
    "cross-platform": ("🔗", "Cross-Platform"),
    "ai":          ("🧩", "AI"),
    "misc":        ("📦", "Genel"),
    "mlops":       ("🛠", "MLOps"),
    "software-development": ("💻", "Yazılım"),
    "autonomous-ai-agents": ("🤖", "Otonom Ajanlar"),
    "security":    ("🔒", "Güvenlik"),
    "productivity":("⚡", "Verimlilik"),
    "devops":      ("🚀", "DevOps"),
    "creative":    ("🎨", "Yaratıcı"),
    "note-taking": ("📝", "Not Alma"),
    "media":       ("📺", "Medya"),
    "research":    ("🔬", "Araştırma"),
    "voice":       ("🎙", "Ses"),
    "user":        ("👤", "Kullanıcı"),
    "smart-home":  ("🏠", "Akıllı Ev"),
    "email":       ("📧", "E-posta"),
    "github":      ("☁️", "GitHub"),
    "data-science":("📊", "Veri Bilimi"),
}


def besN1K_var_mi(icerik: str) -> bool:
    """Dosyada 5N1K tablosu var mı?"""
    return "| **Kim?** |" in icerik or "5N1K" in icerik


def besN1K_olustur(dosya_yolu: Path) -> str:
    """Dosyadan bilgi çıkarıp 5N1K tablosu oluştur."""
    try:
        with open(dosya_yolu, "r", encoding="utf-8") as f:
            icerik = f.read()
    except (OSError, UnicodeDecodeError):
        return ""
    
    # Frontmatter'dan name ve description al
    name = ""
    desc = ""
    fm_match = re.search(r"^---\s*\n(.*?)\n---", icerik, re.DOTALL)
    if fm_match:
        fm = fm_match.group(1)
        n = re.search(r"name:\s*(.+)", fm)
        d = re.search(r"description:\s*(.+)", fm)
        if n: name = n.group(1).strip()
        if d: desc = d.group(1).strip().strip('"')
    
    if not name:
        name = dosya_yolu.stem
    
    # İlk ### veya ## başlıktan Ne çıkar
    ne = desc or name.replace("-", " ").title()
    
    # Kategoriyi dizin isminden çıkar
    kategori = dosya_yolu.parent.name
    
    # Dosya adından Kim çıkar
    kim = "Tüm ajanlar"
    if "kali" in name.lower() or kategori == "kali":
        kim = "Kali ajanı"
    elif "windows" in name.lower() or kategori == "windows":
        kim = "Windows ajanı"
    elif "video" in name.lower() or kategori == "video":
        kim = "Video ajanı"
    
    tablo = f"""
> **Kategori:** {kategori}

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | {kim} |
| **Ne?** | {ne} |
| **Nerede?** | {kategori}/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

"""
    return tablo


def besN1K_ekle(dosya_yolu: Path) -> bool:
    """5N1K'sız dosyaya tablo ekle."""
    try:
        with open(dosya_yolu, "r", encoding="utf-8") as f:
            icerik = f.read()
    except (OSError, UnicodeDecodeError):
        return False
    
    if besN1K_var_mi(icerik):
        return False  # Zaten var
    
    tablo = besN1K_olustur(dosya_yolu)
    if not tablo:
        return False
    
    # Frontmatter'dan sonra ekle
    # Pattern: --- ... --- 'dan sonraki ilk bosluktan sonra
    match = re.search(r"^---\s*\n.*?\n---\s*\n", icerik, re.DOTALL)
    if match:
        # Frontmatter sonrasına ekle
        pos = match.end()
        # Başlıktan (# ...) sonra mı eklesek?
        yeni = icerik[:pos] + tablo + icerik[pos:]
    else:
        yeni = tablo + icerik
    
    try:
        with open(dosya_yolu, "w", encoding="utf-8") as f:
            f.write(yeni)
        return True
    except OSError:
        return False


def tarama_yap() -> dict:
    """Tüm skill'leri tara, 5N1K durumunu raporla."""
    sonuc = {
        "toplam": 0,
        "5n1k_var": 0,
        "5n1k_yok": 0,
        "eklenen": 0,
        "kategoriler": {},
    }
    
    for md_file in sorted(SKILLS_DIR.rglob("*.md")):
        # Katalog dosyasını atla
        if md_file.name == "SKILLS_KATALOG.md":
            continue
        
        # tools/ altındakileri atla
        if "tools" in md_file.parts:
            continue
        
        sonuc["toplam"] += 1
        kategorisi = md_file.parent.name if md_file.parent != SKILLS_DIR else "kok"
        
        if kategorisi not in sonuc["kategoriler"]:
            sonuc["kategoriler"][kategorisi] = {"var": 0, "yok": 0}
        
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                icerik = f.read(2000)  # İlk 2000 karakter yeter
        except (OSError, UnicodeDecodeError):
            icerik = ""
        
        if besN1K_var_mi(icerik):
            sonuc["5n1k_var"] += 1
            sonuc["kategoriler"][kategorisi]["var"] += 1
        else:
            sonuc["5n1k_yok"] += 1
            sonuc["kategoriler"][kategorisi]["yok"] += 1
            # Otomatik ekle
            if besN1K_ekle(md_file):
                sonuc["eklenen"] += 1
                sonuc["5n1k_var"] += 1
                sonuc["5n1k_yok"] -= 1
                sonuc["kategoriler"][kategorisi]["var"] += 1
                sonuc["kategoriler"][kategorisi]["yok"] -= 1
    
    return sonuc


def raporla(sonuc: dict) -> str:
    """İnsan okunabilir rapor."""
    lines = []
    lines.append(f"📊 SKILL 5N1K TARAMA RAPORU")
    lines.append(f"{'='*40}")
    lines.append(f"Toplam: {sonuc['toplam']} dosya")
    lines.append(f"✅ 5N1K var: {sonuc['5n1k_var']}")
    lines.append(f"❌ 5N1K yok: {sonuc['5n1k_yok']}")
    lines.append(f"➕ Otomatik eklenen: {sonuc['eklenen']}")
    lines.append("")
    lines.append("Kategori bazında:")
    for kat, durum in sorted(sonuc["kategoriler"].items()):
        emoji = KATEGORILER.get(kat, ("📁", ""))[0]
        lines.append(f"  {emoji} {kat}: {durum['var']}✅ / {durum['yok']}❌")
    
    return "\n".join(lines)


# === ÇALIŞTIR ===
if __name__ == "__main__":
    print("Skill 5N1K otomasyon başlıyor...")
    sonuc = tarama_yap()
    print(raporla(sonuc))
    print(f"\n{sonuc['eklenen']} dosyaya 5N1K eklendi.")
