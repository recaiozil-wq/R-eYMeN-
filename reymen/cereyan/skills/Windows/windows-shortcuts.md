---
name: windows-shortcuts
title: "Windows Kısayolları — Master Skill"
description: "Tüm Windows klavye kısayolları: sistem, dosya gezgini, tarayıcı, geliştirme araçları."
tags: [windows, shortcuts, keyboard, automation, productivity]
category: windows
audience: user
version: 2.0.0
triggers: [kisayol, shortcut, windows, klavye, keyboard, ctrl, alt, win]
related_skills: [windows-automation, windows-system-automation]


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | Windows ajani |
| **Ne** | "Tüm Windows klavye kısayolları: sistem, dosya gezgini, tarayıcı, geliştirme araçları." |
| **Nerede** | `windows\shortcuts\windows-shortcuts.md` |
| **Ne Zaman** | Windows sistem yonetimi gerektiginde |
| **Neden** | Windows Shortcuts islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Tüm Windows klavye kısayolları: sistem, dosya gezgini, tarayıcı, geliştirme araçları. |
| **Nerede?** | shortcuts/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: Windows ajani
Ne: "Tüm Windows klavye kısayolları: sistem, dosya gezgini, tarayıcı, geliştirme araçları."
Nerede: `windows\shortcuts\windows-shortcuts.md`
Ne Zaman: Windows sistem yonetimi gerektiginde
Neden: Windows Shortcuts islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Windows Kısayolları — Master Skill

149 ayrı kısayol skill'i 4 kategoride birleştirildi. İhtiyacın olan kategoriyi seç ve ilgili reference dosyasını yükle.

## 📂 Kategoriler

| Kategori | Açıklama | Referans |
|----------|----------|----------|
| 🖥️ **System Core** | Genel Windows, masaüstü, pencere, görev çubuğu, erişilebilirlik (89 kısayol) | `references/system-core.md` |
| 📁 **File Explorer** | Dosya gezgini işlemleri (13 kısayol) | `references/file-explorer.md` |
| 🌐 **Browsers** | Tarayıcı kısayolları — sekme, geçmiş, adres çubuğu (32 kısayol) | `references/browsers.md` |
| 🛠️ **Dev Tools** | Metin düzenleme, VS Code, terminal (15 kısayol) | `references/dev-tools.md` |

## Kullanım

```markdown
# System Core kısayollarını yükle:
skill_view(name="windows-shortcuts", file_path="references/system-core.md")
```

## İçindekiler

### system-core (89)
Temel Windows: Ctrl+C/V/X/Z/A, Delete, F2, F5, Esc, Win tuşları, pencere yönetimi (Alt+Tab, Win+D), ekran görüntüleri (PrtScn, Win+Shift+S), sanal masaüstü, görev çubuğu, diyalog kutuları, sistem görevleri, erişilebilirlik

### file-explorer (13)
Alt+D (adres çubuğu), Alt+Enter (özellikler), Ctrl+N (yeni pencere), Ctrl+W (kapat), F11 (tam ekran), F4, Num+* (tüm alt klasörler), Ctrl+Shift+E, Ctrl+E, Alt+yukarı/sağ/sol

### browsers (32)
Ctrl+T (yeni sekme), Ctrl+W (kapat), Ctrl+Shift+T (geri aç), Ctrl+Tab, Ctrl+1-9, Ctrl+Shift+N (gizli), Ctrl+H/J/L/R, F11, Ctrl++/-, CTRL+0, geri/ileri, yer imi

### dev-tools (15)
Ctrl+B/I/U (kalın/italik/altı çizili), Home/End, Ctrl+sağ/sol, Ctrl+Backspace/Delete, Ctrl+Shift+yön, Ctrl+yukarı/aşağı
