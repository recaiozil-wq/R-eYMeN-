---
name: obsidian-daily-setup
title: Obsidian Daily Notes Kurulum
description: "Obsidian Daily Notes & Planner onboarding checklist — günlük not ve ajanda sistemi kurulum kılavuzu."
tags: [obsidian, daily-notes, planner, productivity, onboarding]
category: productivity
audience: user
version: 1.0.0
triggers: [obsidian, daily-notes, planner, onboarding, gunluk-not]
related_skills: [obsidian, obsidian-vault-maintenance]
---


> **Kategori:** productivity

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Obsidian Daily Notes & Planner onboarding checklist — günlük not ve ajanda sistemi kurulum kılavuzu. |
| **Nerede?** | productivity/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Obsidian Daily Notes & Planner — Onboarding

## 🔗 Onboarding Checklist

- [ ] 1) Daily Notes & Planner eklentilerini YÖNET ekranından ekle
  - Hızlı kur: **Periodic Notes** kur
  - Varsayılan **Daily Notes** hattı yeterli

- [ ] 2) Şablon klasörünü işaret et
  - `Obsidian Vault/Daily/templates/` yoksa oluştur

- [ ] 3) Şablon dosyasını yükle
  - `Daily/templates/Daily-Planner.md` şablonu

- [ ] 4) Periodic Notes ayarlarını kaydet
  - Daily: `Daily/{{date}}`
  - Weekly: `Weekly/Weekly-{{date:GGGG-[W]ww}}`
  - Monthly: `Monthly/Monthly-{{date:YYYY-MM}}`
  - Template: `Daily/templates/Daily-Planner.md`

- [ ] 5) Her gün açılışta **Daily Planner** üret
  - Eklenti: **Periodic Notes + Daily Notes** senkronize
  - `Ctrl/Cmd + N` veya Calendar'den oluştur

- [ ] 6) Vault aramasında "Günlük Not" ve "Ajanda" görünmesini sağla
  - Dosya isimleri: `YYYY-MM-DD.md`, `Weekly-YYYY-Www.md`, `Monthly-YYYY-MM.md`
  - Search tagleri: `daily`, `weekly`, `monthly`, `productivity`

## 📝 Örnek Günlük Not Şablonu

```markdown
---
date: <% tp.date.now("YYYY-MM-DD") %>
type: daily
tags: [daily, productivity]
---

# 📆 <% tp.date.now("DD.MM.YYYY") %> — Gün

## 🎯 Günün Odakları
- [ ] Öncelik 1

## ✅ Alışkanlıklar
- [ ] Su: 8 bardak
- [ ] Egzersiz: 30 dk
- [ ] Kitap: 20 sayfa
- [ ] Meditasyon: 10 dk

## 📊 Gün Değerlendirmesi
- **Ruh Hali:**
- **Verimlilik:**
```
