---
name: hermes-muhendislik-analizi
title: Hermes Mühendislik Analizi
description: "Hermes Agent'in tam mimari analizi — 4 paralel ajan + video analizi ile üretilmiş kapsamlı referans dokümanı."
tags: [hermes, architecture, engineering, analysis, reference]
category: devops
audience: maintainer
version: 1.0.0
triggers: [hermes-mimari, mühendislik-analizi, 007-ajan, mimari-harita]
related_skills: [hermes-agent]
---


> **Kategori:** devops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Hermes Agent'in tam mimari analizi — 4 paralel ajan + video analizi ile üretilmiş kapsamlı referans dokümanı. |
| **Nerede?** | devops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Hermes Mühendislik Analizi (Modüler Router)

Bu skill, Hermes Agent'in tam mimari analiz dokümanını 7 bağımsız referans dosyasına bölen modüler bir yönlendiricidir.

## 🎯 Analiz Bölümünü Seç

Kullanıcı hangi konuda soru sorduysa ilgili reference dosyasını yükle:

| Bölüm | Konu | Referans Dosyası |
|-------|------|------------------|
| Bölüm 1 | Genel Mimari & Hermes Nedir | `references/01-genel-mimari.md` |
| Bölüm 2 | Çekirdek Sistem (Akış Tablosu, BrainRouter, Durum Makinesi) | `references/02-cekirdek-sistem.md` |
| Bölüm 3 | Bellek ve RAG Katmanı (ChromaDB, vektör deposu, bilgi grafı) | `references/03-bellek-rag.md` |
| Bölüm 4 | Skill Üretim Sistemi (boru hattı, self-reflection, evrim) | `references/04-skill-uretim.md` |
| Bölüm 5 | Entegrasyon ve Operasyon (Telegram, Obsidian Engine, bütçe, VRAM) | `references/05-entegrasyon.md` |
| Bölüm 6 | Kritik Eksikler ve Güvenlik Açıkları | `references/06-kritik-eksikler.md` |
| Bölüm 7 | 007 Ajan Mimarisi (güven piramidi, GraphRAG, benchmark) | `references/07-007-ajani.md` |
| Bölüm 8 | Yerel Hermes Projeleri Envanteri (4 kod tabanı, konum, durum) | `references/08-yerel-hermes-projeleri.md` |

## Kullanım

Bir analiz sorusu aldığında:
1. Konuyu belirle (genel mimari, çekirdek, bellek, skill üretim, entegrasyon, eksikler, 007 ajan)
2. `skill_view(name="hermes-muhendislik-analizi", file_path="references/XX-bolum.md")` ile ilgili reference dosyasını yükle
3. Oradaki spesifik bilgilerle yanıtla

> **Not:** Analiz dokümanı 420 satırlık kapsamlı bir kaynaktan parçalanmıştır. Sadece aktif bölümün reference dosyasını yükle.
