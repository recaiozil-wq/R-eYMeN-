---
name: windows-file-operations
description: Windows'ta dosya oluşturma, açma, düzenleme işlemleri için temel kurallar. Uzantı kullanımı, Notepad entegrasyonu ve GUI dosya yönetimi.
title: "Windows File Operations"
version: 1.0.0
author: hermes
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [windows, dosya, file, notepad, txt, uzanti, extension]
category: windows-automation
audience: user
tags: [automation, windows]
---


> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Windows'ta dosya oluşturma, açma, düzenleme işlemleri için temel kurallar. Uzantı kullanımı, Notepad entegrasyonu ve GUI dosya yönetimi. |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Windows Dosya İşlemleri

## Overview

Windows'ta dosya oluştururken ve açarken uyulması gereken kurallar.
Kullanıcı aksini belirtmedikçe tüm dosyalar .txt uzantılı oluşturulur.

## Temel Kural: DOSYALARA UZANTI VER

**KRİTİK:** Windows'ta uzantısız dosya oluşturma.
- Uzantısız dosyalar simge göstermez
- Windows "bunu hangi uygulamayla açayım?" dialog'u gösterir
- Notepad ile direkt açılmaz

**KURAL:** Kullanıcı net bir uzantı belirtmedikçe (ör: .py, .md, .json), tüm dosyalar `.txt` uzantılı oluşturulur.

### Doğru:
```bash
touch /c/Users/marko/Desktop/dosya.txt        # ✓
echo "icirk" > /c/Users/marko/Desktop/dosya.txt # ✓
```

### Yanlış:
```bash
touch /c/Users/marko/Desktop/dosya              # ✗ — uzantısız!
```

## Dosya Oluşturma Yöntemleri

### 1. Boş dosya (touch)
```bash
touch "/c/Users/marko/Desktop/dosya.txt"
```

### 2. İçerikli dosya (write_file)
```python
write_file(path="C:\\Users\\marko\\Desktop\\dosya.txt", content="metin")
```

### 3. echo ile
```bash
echo "metin" > "/c/Users/marko/Desktop/dosya.txt"
```

## Dosya Açma

### Notepad ile aç
```bash
notepad "C:\Users\marko\Desktop\dosya.txt"
```
Notepad.exe GUI uygulamasıdır — terminal timeout yer (normal), arka planda açık kalır.

### Tor Browser / Firefox ile aç (web sayfası)
```bash
start "" "C:\Users\marko\OneDrive\Desktop\Tor Browser\Browser\firefox.exe" "https://..."
```

### Varsayılan programla aç
```bash
start "" "C:\Users\marko\Desktop\dosya.txt"
```

## Dosya Silme

```bash
rm "/c/Users/marko/Desktop/dosya.txt"
```

## Obsidian'da Not Açma

```bash
start "" "obsidian://open?path=C:\Users\marko\OneDrive\Belgeler\Obsidian Vault\not.md"
```

## Common Pitfalls

1. **touch ile uzantısız dosya** — Windows simge göstermez, dialog çıkar
2. **start komutu** — Git Bash'te start çalışır, GUI uygulamaları için kullan
3. **Notepad timeout** — GUI uygulaması, terminal onu beklemez, timeout normal
4. **Yolda Türkçe karakter varsa** — çift tırnak içine al

## Verification Checklist

- [ ] Dosya .txt uzantılı mı? (kullanıcı aksini söylemediyse)
- [ ] Yolda boşluk var mı? → çift tırnak
- [ ] Dosya başarıyla oluştu mu? → ls -la ile kontrol
