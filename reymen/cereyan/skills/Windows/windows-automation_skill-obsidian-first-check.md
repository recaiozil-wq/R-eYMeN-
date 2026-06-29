
> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Windows Automation_Skill Obsidian First Check |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: skill-obsidian-first-check
description: Her görevde ilk olarak Hermes skill listesi ve Obsidian vault taraması yap. Eğer konu zaten kayıtlıysa yeni dokümantasyon oluşturma, mevcut kayda devam et. Bu, tekrar kaydetme zaman kaybını önler.
title: "Skill Obsidian First Check"

audience: user
tags: [automation, obsidian, windows]
category: windows-automation---

# Skill + Obsidian Ön Kontrol Kuralı

## Amaç
Herhangi bir görevi başlatmadan önce aşağıdaki sırayı takip et:
1. `skills_list` ile ilgili Hermes becerilerini kontrol et.
2. `search_files` ile Obsidian vault taraması yap.
3. Eğer konu zaten kayıtlıysa, mevcut kayda devam et veya yeniden kullan. Yeni dokümantasyon oluşturma.

## Neden Önemli
- Tekrar kaydetme zaman kaybını önler.
- Kullanıcı kurallarına uygun ilerlemeyi sağlar.
- Bellek ve beceri havuzunu verimli kullanır.

## Adım Adım

1. **skills_list()** — önce Hermes skill'lerini tara, konuyla ilgili skill varsa `skill_view()` ile yükle
2. **search_files()** — Obsidian vault'ta konuyla ilgili not ara:
   - `path: "C:\\Users\\marko\\OneDrive\\Belgeler\\Obsidian Vault\\Hermes"`
   - Kategori klasörleri: Skills/, Knowledge/, Cron/
3. **Bulunan kaydı kullan** — varsa yeniden oluşturma, mevcut kayda devam et
4. **Yoksa oluştur** — hem skill (gerekirse) hem Obsidian notu olarak kaydet

## Notlar
- Bu kural **her görevde**, her oturumda uygulanmalı.
- Doğru Obsidian vault yolu: `C:\Users\marko\OneDrive\Belgeler\Obsidian Vault`
- Yanlış yola (`Documents\Obsidian Vault`) asla yazma
- Önce `skills_list()`, sonra `search_files()` sırası — ikisi de boşsa yeni kayıt oluştur
