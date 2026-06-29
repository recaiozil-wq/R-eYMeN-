---
name: obsidian-gelistirme-otomasyonu
title: "Obsidian Gelistirme Otomasyonu"
tags: [agents, ai, obsidian]
description: >
  Hermes otomasyon döngüsü: Tor Browser üzerinden sürekli yeni görev
  keşfi ve Obsidian geliştirme. 8 saat boyunca her 3 dakikada bir
  yeni konu araştır ve bilgi ekle.
version: 1.0.0
author: marko
license: MIT
metadata:
  hermes:
    tags: [obsidian, gelistirme, tor, otomasyon, arastirma]
audience: user
related_skills: [tor-browser-arama, obsidian]


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | > |
| **Nerede** | `autonomous-ai-agents\autonomous-ai-agents_obsidian-gelistirme-otomasyonu.md` |
| **Ne Zaman** | Ilgili gorev gerektiginde |
| **Neden** | Autonomous Ai Agents Obsidian Gelistirme Otomasyonu islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | > |
| **Nerede?** | autonomous-ai-agents/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: Otonom ajan gelistiricisi
Ne: >
Nerede: `autonomous-ai-agents\autonomous-ai-agents_obsidian-gelistirme-otomasyonu.md`
Ne Zaman: Ilgili gorev gerektiginde
Neden: Autonomous Ai Agents Obsidian Gelistirme Otomasyonu islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Obsidian Geliştirme Otomasyonu

## Amaç

Obsidian vault'u sürekli geliştirmek için her 3 dakikada bir
Tor Browser üzerinden yeni konular araştırır ve bilgi ekler.

## Adımlar

1. `tor-browser-arama` skill'ini yükle.
2. `obsidian` skill'ini yükle.
3. Hermes otomasyon döngüsünü başlat:
   - Her 3 dakikada bir yeni görev al
   - Tor Browser ile yeni konular araştır
   - Bulunan bilgileri Obsidian vault'a ekle
   - Konular: teknoloji, AI, siber güvenlik, programlama, pentesting
4. 8 saat boyunca sürekli döngüde kal.

## Cron Job

- Schedule: `once in 3m`
- Repeat: forever (8 saat boyunca)
- Skills: `tor-browser-arama`, `obsidian`
- Model: `stepfun/step-3.7-flash:free`
- Provider: `nous`
- Toolsets: `web`, `terminal`, `file`

## Not

Bu cron job varsayılan olarak **devre dışıdır** (disabled).
Aktifleştirmek için `cronjob action='run' job_id='...'` ile manuel
tetiklenebilir veya `cronjob action='update' job_id='...' enabled=true`
ile tekrar aktif edilebilir.
