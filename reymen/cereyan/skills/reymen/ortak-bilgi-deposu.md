---
name: ortak-bilgi-deposu
title: Ortak Bilgi Deposu
description: Çoklu ajan (Kali/Windows/CAD/Hermes) paylaşımlı bilgi mimarisi.
category: kullanici
---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ReYMeN ajani |
| **Ne** | Çoklu ajan (Kali/Windows/CAD/Hermes) paylaşımlı bilgi mimarisi. |
| **Nerede** | `reymen\ortak-bilgi-deposu.md` |
| **Ne Zaman** | ReYMeN yapilandirmasi gerektiginde |
| **Neden** | Ortak Bilgi Deposu islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |

Kim: ReYMeN ajani
Ne: Çoklu ajan (Kali/Windows/CAD/Hermes) paylaşımlı bilgi mimarisi.
Nerede: `reymen\ortak-bilgi-deposu.md`
Ne Zaman: ReYMeN sistemi yapilandirmasi gerektiginde
Neden: Ortak Bilgi Deposu islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Ortak Bilgi Deposu

> **Kategori:** kullanici/mimari

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar (Kali, Windows, CAD, Hermes) |
| **Ne?** | Çoklu ajan paylaşımlı bilgi mimarisini tanımlar. Memory→DB, skill→.md, karar→.md, log→kazanimlar.md |
| **Nerede?** | `hermes_projesi/` ağacı içinde. DB: `reymen/cereyan/.ReYMeN/ogrenmeler.db` |
| **Ne Zaman?** | Her yeni kayıt/skill/karar oluşturulduğunda |
| **Neden?** | 3 ajanın aynı bilgiyi paylaşması için. Hermes internal (AppData) kullanılmaz |
| **Nasıl?** | Memory→Python sqlite3, Skill→write_file(), Karar→echo append, Log→kazanimlar.md |

## Mimari

```
hermes_projesi/
├── reymen/cereyan/
│   ├── .ReYMeN/ogrenmeler.db    ← 🧠 MEMORY (SQLite)
│   └── skills/{adi}.md          ← 📚 SKILL (Markdown+YAML)
├── .ReYMeN/
│   ├── decisions.md              ← 📋 KARAR (Markdown)
│   ├── kazanimlar.md             ← 🏆 ORTAK LOG
│   └── USER.md / MEMORY.md      ← 👤 Profil
└── AGENTS.md                     ← Proje talimatları
```

## 3 Veri Tipi

| Tip | Dosya | Yazma | Okuma |
|:----|:------|:------|:------|
| 🧠 MEMORY | `.db` | Python sqlite3 | `OnceHafiza.hafizada_ara()` |
| 📚 SKILL | `.md` | `write_file()` | `skill_view()` |
| 📋 KARAR | `.md` | `echo >>` | `read_file()` |
| 🏆 KAZANIM | `.md` | `echo >>` | `read_file()` |

## Yasaklar

1. ❌ Hermes `memory()` tool kullanma — AppData'ya yazar
2. ❌ Skills → AppData yazma — sadece `reymen/cereyan/skills/`
3. ❌ `pytest --collect-only` — HANG yiyor
4. ✅ Tüm ajanlar aynı DB'yi paylaşır, kategori ile ayrışır
5. ✅ Her skill 5N1K formatında
