---
name: model-startup-choice
id: model-startup-choice
title: "Açılışta Model Seçimi"
description: "Her oturum başında kullanıcıya model seçimi sorar: A) DeepSeek B) Dolphin (LM Studio)"
tags: [startup, model, choice, always-active]
category: user-preferences
audience: user
trigger: "Her oturum başlangıcında — kullanıcının ilk mesajından ÖNCE"
---


> **Kategori:** preferences

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Her oturum başında kullanıcıya model seçimi sorar: A) DeepSeek B) Dolphin (LM Studio) |
| **Nerede?** | preferences/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Açılışta Model Seçimi

**ZORUNLU:** Her yeni oturum başladığında, kullanıcının ilk mesajına cevap vermeden önce aşağıdaki seçimi sun.

## STARTUP SEQUENCE

Kullanıcıya şunu söyle (başka hiçbir şey ekleme, sadece bu):

---

Model seçin:

**A)** DeepSeek V4 Flash *(aktif)*
**B)** Dolphin3.0-Llama3.1-8B — LM Studio

---

## SONRASINDA

- Kullanıcı **A** yazarsa → mevcut modeli koru (DeepSeek zaten aktif), devam et
- Kullanıcı **B** yazarsa → `hermes config set model dolphin-lmstudio` çalıştır, ardından "Config güncellendi. Yeni oturumda LM Studio (Dolphin) aktif olacak." de. NOT: `/model` slash komutu **CLI agent'tan çalıştırılamaz** — gateway seviyesinde işlenir. Doğru yol `hermes config set` ile config'i güncellemek ve kullanıcıya yeni oturum açmasını söylemektir.
- Kullanıcı başka bir şey yazarsa → A seçilmiş gibi devam et (DeepSeek varsayılan)

## PITFALLS

- **`/model` komutunu ÇALIŞTIRMA** — bu bir gateway slash komutudur, terminalden çalışmaz. Her zaman `hermes config set model <alias>` kullan.
- **Config değişikliği mevcut oturumda geçerli olmaz** — sadece yeni oturumlar etkilenir. Kullanıcıya bunu bildir.
- Kullanıcı "sen hala eski modeldesin" derse → haklıdır. Config'i güncellemiş olsan bile bu oturum o config ile başlatıldı. Yeni oturum öner.

## KURALLAR

- Bu soruyu HER YENİ OTURUMDA sor (her `/new` veya yeni başlangıçta)
- Soruyu sorduktan sonra bir daha sorma (oturum içinde tekrarlama)
- Soruyu sormadan kullanıcının mesajına cevap verme
