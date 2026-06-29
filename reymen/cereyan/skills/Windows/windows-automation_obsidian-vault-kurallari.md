---
name: obsidian-vault-kurallari
title: "Obsidian Vault Kurallari"
tags: [automation, obsidian, windows]
description: Use whenever reading, writing, or syncing anything to Obsidian. Contains the ONLY correct vault path and startup verification routine. ALWAYS check this skill before any Obsidian file operation.
version: 1.0.0
author: marko
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [obsidian, vault, path, startup, sync, kural, yanlis-yol, doğru-yol]
audience: user
related_skills: [obsidian, gorsel-onaylama, tam-sistem-yetkisi]
---


> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Use whenever reading, writing, or syncing anything to Obsidian. Contains the ONLY correct vault path and startup verification routine. ALWAYS check this skill before any Obsidian file operation. |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Obsidian Vault Kuralları — Kesin Yol ve Başlangıç Rutini

## KURAL 1 — Tek Geçerli Vault Yolu

```
DOGRU : C:\Users\marko\OneDrive\Belgeler\Obsidian Vault
YANLIS: C:\Users\marko\Documents\Obsidian Vault       ← ASLA KULLANMA
YANLIS: C:\Users\marko\Documents\ObsidianVault        ← ASLA KULLANMA
YANLIS: ~/Documents/Obsidian Vault                    ← ASLA KULLANMA
```

Hermes .env dosyasındaki kayıt:
```
OBSIDIAN_VAULT_PATH=C:\Users\marko\OneDrive\Belgeler\Obsidian Vault
```

Hermes-ai .env dosyasındaki kayıt:
```
OBSIDIAN_VAULT=C:\Users\marko\OneDrive\Belgeler\Obsidian Vault
```

## KURAL 2 — Her Açılışta İlk İş: Vault Kontrolü

Hermes yeni bir oturum başladığında ILKÖNCE şu kontrolleri yapar:

```python
import os
from pathlib import Path

VAULT = Path(r"C:\Users\marko\OneDrive\Belgeler\Obsidian Vault")

# 1. Vault mevcut mu?
assert VAULT.exists(), f"VAULT BULUNAMADI: {VAULT}"

# 2. Hermes klasörü mevcut mu?
hermes_dir = VAULT / "Hermes"
hermes_dir.mkdir(exist_ok=True)

# 3. Skills klasörü mevcut mu?
skills_dir = hermes_dir / "Skills"
skills_dir.mkdir(exist_ok=True)

# 4. Skill sayısı
skill_count = len(list(skills_dir.rglob("*.md")))
print(f"[OK] Vault: {VAULT}")
print(f"[OK] Skill: {skill_count} dosya")
```

Terminal komutu olarak:
```bash
python C:\Users\marko\hermes-ai\venv\Scripts\python.exe -c "
from pathlib import Path
v = Path(r'C:\Users\marko\OneDrive\Belgeler\Obsidian Vault')
print('[OK]' if v.exists() else '[HATA]', 'Vault:', v)
s = v / 'Hermes' / 'Skills'
print('Skills:', len(list(s.rglob('*.md'))) if s.exists() else 0, 'dosya')
"
```

## KURAL 3 — Skill Sync (Her Kurulumda)

Yeni skill kurulduğunda HEMEN sync çalıştır:

```bash
"C:\Users\marko\hermes-ai\venv\Scripts\python.exe" "C:\Users\marko\AppData\Local\hermes\hooks\sync_skills_to_obsidian.py"
```

Çıktı:
```
Hermes Skills -> Obsidian senkronizasyonu basliyor...
Tamamlandi: X yazildi / Y taranmis
Obsidian: C:\Users\marko\OneDrive\Belgeler\Obsidian Vault\Hermes\Skills
```

## KURAL 4 — Obsidian'a Dosya Yazarken

write_file veya terminal ile Obsidian'a yazarken DAIMA:

```python
VAULT = r"C:\Users\marko\OneDrive\Belgeler\Obsidian Vault"
# Doğru:
path = rf"{VAULT}\Hermes\notum.md"

# YANLIS (asla):
# path = r"C:\Users\marko\Documents\Obsidian Vault\notum.md"
```

## KURAL 5 — Yanlış Yol Tespitinde Düzeltme

Eğer yanlış vault yoluna yazılmış dosya varsa:

```python
import shutil
from pathlib import Path

yanlis = Path(r"C:\Users\marko\Documents\Obsidian Vault")
dogru  = Path(r"C:\Users\marko\OneDrive\Belgeler\Obsidian Vault\Hermes")

for f in yanlis.rglob("*.md"):
    hedef = dogru / f.name
    shutil.copy2(f, hedef)
    print(f"Tasindi: {f.name} -> {hedef}")
```

## Vault Yapısı

```
C:\Users\marko\OneDrive\Belgeler\Obsidian Vault\
└── Hermes\
    ├── Hermes Skills Sync.md
    ├── Telegram Gateway Monitor.md
    ├── GitHub Repo - *.md
    └── Skills\
        ├── windows-automation\   (5 skill)
        ├── autonomous-ai-agents\ (7 skill)
        ├── software-development\ (15 skill)
        ├── productivity\         (12 skill)
        ├── github\               (6 skill)
        ├── research\             (5 skill)
        ├── creative\             (14 skill)
        └── ... (156 not, 142 SKILL.md — son sync: 2026-06-03)
```

## Common Pitfalls

1. **`Documents\Obsidian Vault` kullanmak** — Bu klasör Obsidian tarafından tanınmıyor. Obsidian uygulaması sadece `OneDrive\Belgeler\Obsidian Vault`'u açıyor.
2. **`~/Documents` genişletmek** — Windows'ta `~` = `C:\Users\marko`, bu da `Documents\Obsidian Vault`'a gider. Tam yol kullan.
3. **Vault var ama Obsidian göstermiyor** — Obsidian'da `Ctrl+R` ile yenile.
4. **OneDrive sync gecikmesi** — Dosyalar vault'ta ama Obsidian'da görünmüyor. Sistem tepsinde OneDrive sync'in tamamlanmasını bekle.
5. **Skill index güncellenmiyor** — `skills_list` API'si kaldırılan/deprecate edilen skill'leri otomatik temizlemez. Tam yeniden yükleme (agent restart) gerekir. Skill'leri silmek yerine `__cleanup_deprecated_<ad>` dizinine taşı.
6. **mcp_obsidian_vault_write template hatası** — Vault'ta template yoksa `mcp_obsidian_vault_write()` `"Template not found"` hatası verir. Çözüm: doğrudan `mcp_filesystem_write_file(path="C:\Users\marko\OneDrive\Belgeler\Obsidian Vault\hedef\not.md")` ile yaz, frontmatter'ı manuel ekle. veya `mcp_obsidian_vault_append()` ile mevcut dosyaya ekle (dosya zaten varsa).

## Verification Checklist

- [ ] `OBSIDIAN_VAULT_PATH` .env'de `OneDrive\Belgeler\Obsidian Vault` mi?
- [ ] `OBSIDIAN_VAULT` hermes-ai/.env'de doğru mu?
- [ ] Vault klasörü fiziksel olarak mevcut mu?
- [ ] Hermes/Skills/ altında dosyalar var mı?
- [ ] Obsidian uygulaması bu vault'u açıyor mu (obsidian.json kontrol)?
