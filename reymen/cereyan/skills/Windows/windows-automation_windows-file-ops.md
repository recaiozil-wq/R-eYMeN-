---
name: windows-file-ops
title: "Windows File Ops"
tags: [automation, windows]
description: Windows'ta dosya/klasör oluşturma, açma ve yönetme işlemleri. Uzantı kuralları, Notepad/uygulama seçimi, dosya yolu yönetimi.
version: 1.0.0
author: marko
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [windows, dosya, file, notepad, uzanti]
audience: user
related_skills: [tam-sistem-yetkisi, windows-automation-shortcuts]
---


> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Windows'ta dosya/klasör oluşturma, açma ve yönetme işlemleri. Uzantı kuralları, Notepad/uygulama seçimi, dosya yolu yönetimi. |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Windows Dosya İşlemleri (windows-file-ops)

## Overview

Windows ortamında dosya/klasör oluşturma, açma ve yönetme işlemleri için standart workflow. Bu skill, Windows'un dosya sistemiyle ilgili davranış farklılıklarını ve kullanıcının tercihlerini kapsar.

## Temel Kurallar

### 1. UZANTI ZORUNLUDUR (KRİTİK)

Windows'ta uzantısız dosyalar:
- Dosya Gezgini'nde simge göstermez (boş/bilinmeyen simge)
- Çift tıklayınca "baba dosyasını açmak için bir uygulama seçin" dialog'u açar
- Notepad ile açılsa bile kullanıcı için kafa karıştırıcıdır

**KURAL:** Her dosyayı oluştururken uygun uzantıyı EKLE:
| İçerik türü | Uzantı |
|-------------|--------|
| Boş/düz metin | `.txt` |
| Python kodu | `.py` |
| JSON | `.json` |
| YAML | `.yaml` |
| Shell script | `.sh` |
| Markdown | `.md` |

### 2. Dosya Oluşturma Yöntemleri

Git Bash (terminal) üzerinden:

```bash
# Boş dosya
touch /c/Users/marko/Desktop/dosya.txt

# İçerikli dosya
echo "metin" > /c/Users/marko/Desktop/dosya.txt

# Çok satırlı
cat > /c/Users/marko/Desktop/dosya.txt << 'EOF'
satır1
satır2
EOF
```

PowerShell üzerinden:

```powershell
# Boş dosya
New-Item -Path "C:\Users\marko\Desktop\dosya.txt" -ItemType File

# İçerikli
Set-Content -Path "C:\Users\marko\Desktop\dosya.txt" -Value "metin"
```

### 3. Dosya Açma

Notepad ile aç:

```bash
notepad "C:\Users\marko\Desktop\dosya.txt"
```

Notepad GUI uygulamasıdır — terminal timeout yer, ama dosya açılır. Kullanıcıya "açıldı" bilgisi ver, timeout normaldir.

### 4. Klasör Oluşturma

```bash
mkdir -p /c/Users/marko/Desktop/yeni-klasor
# veya
mkdir "C:\Users\marko\Desktop\yeni-klasor"
```

### 5. Dosya Silme

```bash
rm /c/Users/marko/Desktop/dosya.txt
```

## Windows Yol Formatları

| Ortam | Format | Örnek |
|-------|--------|-------|
| Git Bash | `/c/Users/marko/...` | `touch /c/Users/marko/Desktop/test.txt` |
| PowerShell/cmd | `C:\Users\marko\...` | tırnak içinde: `"C:\Users\marko\Desktop\test.txt"` |
| Python | `C:\\Users\\marko\\...` | çift backslash veya raw string |

## Common Pitfalls

1. **Uzantısız dosya oluşturmak** — Windows'ta her zaman sorun çıkarır. `.txt` ekle.
2. **Notepad timeout** — Normaldir, GUI uygulaması terminalde bloke olur. Kullanıcıya bilgi ver.
3. **Git Bash'te boşluklu yollar** — Tırnak içine al veya MSYS yolunu kullan.
4. **touch ile oluşturulan dosya** — Windows'ta explorer hemen güncellenmeyebilir, F5 gerekebilir.
5. **Kullanıcı ".txt" demese bile ekle** — Kullanıcı "boş bir dosya" dediğinde metin dosyası kastediyordur. Uzantı ekle.

## Verification Checklist

- [ ] Dosya oluşturuldu: `ls -la <yol>` ile kontrol
- [ ] Uzantı doğru (`.txt`, `.py`, vs.)
- [ ] İçerik doğru (gerekirse)
- [ ] Kullanıcıya tam yol söylendi
