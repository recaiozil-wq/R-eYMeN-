---
name: vault-fix-and-tag
description: Obsidian vault'ta kırık linkleri düzeltme, orphan dosyaları temizleme ve etiket ekleme
title: "Vault Fix And Tag"
version: 1.0.0
author: marko
license: MIT
metadata:
  hermes:
    tags: [obsidian, vault, maintenance, cleanup, tags]
category: productivity
audience: user
tags: [productivity, tools]
---


> **Kategori:** productivity

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Obsidian vault'ta kırık linkleri düzeltme, orphan dosyaları temizleme ve etiket ekleme |
| **Nerede?** | productivity/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Vault Fix and Tag

Obsidian vault'u tarar ve üç ana düzeltmeyi otomatik yapar: kırık link onarımı, orphan dosya taşıma ve etiket ekleme.

## Kullanım

Bu her seferinde manuel değil, bir Python script'i aracılığıyla çalışır:

### 1. Vault analizi
```bash
python "C:\Users\marko\AppData\Local\Python\PythonCore-3.14-64\python.exe" -c "
from pathlib import Path
import re

vault = Path(r'C:\Users\marko\OneDrive\Belgeler\Obsidian Vault')
hermes_root = vault / 'Hermes'

files = list(hermes_root.rglob('*.md'))
print(f'Dosya sayısı: {len(files)}')
"
```

### 2. Kırık link tarama
Python script'i ile tüm `.md` dosyalarını tara, `[[Link]]` desenlerini bul ve dosyanın var olup olmadığını kontrol et. Var olmayanları raporla.

### 3. Düzeltme kuralları
- **Var olmayan skill referansları** → `[[skill-name]]` → `skill-name` (inline code)
- **Eğitim amaçlı wikilink'ler** (kod blokları, örnekler) → `[[wikilinks]]` → `[[wikilinks]]` → `\`[[wikilinks]]\``
- **Hatalı resim yolları** (`.png360`, `.webp` uzantılı) → düzelt veya kaldır
- **Gerçek broken link** → `f/[[existing-note|görünen ad]]` şeklinde düzelt

### 4. Orphan dosya taşıma
Index notlarında bağlantısı olmayan dosyaları (true orphan) tespit et ve:
- Vault dışı ilgisiz notlar → `Hermes/Knowledge/` altına taşı
- Skill notları → uygun `_index.md`'ye ekle

### 5. Etiket ekleme
Etiketsiz Hermes notlarını tespit et ve dosya konumuna göre etiket ata:
- `Hermes/Skills/**/*.md` → `#hermes #skill`
- `Hermes/Skills/<kategori>/**/*.md` → `#hermes #skill #<kategori>`
- `Hermes/Topics/**/*.md` → `#hermes`
- `Hermes/Knowledge/**/*.md` → `#hermes #knowledge`
- Kök `Hermes/*.md` → `#hermes`

### 6. Önemli yollar
```
Vault:      C:\Users\marko\OneDrive\Belgeler\Obsidian Vault
Python:     C:\Users\marko\AppData\Local\Python\PythonCore-3.14-64\python.exe
Güvenli işlem: önce kuru çalıştır (--dry-run), sonra uygula
```

## Pitfall
- `.png360`, `.webp` uzantılı resimler Obsidian'da görünmez — inline code'a çevir veya uzantıyı düzelt
- Eğitim/örnek wikilink'lere dokunma — sadece gerçek broken link'leri düzelt
- Etiket eklerken mevcut ön yüz (frontmatter) etiketlerini koru
- `_index.md` dosyalarına otomatik etiket ekleme
