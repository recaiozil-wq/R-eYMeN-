
> **Kategori:** note-taking

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | > |
| **Nerede?** | note-taking/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: obsidian-vault-path-fix
description: >
title: "Obsidian Vault Path Fix"
  Varsayılan yanlış yol `C:\Users\marko\Documents\Obsidian Vault` yerine
  bu skill sadece ve sadece kullanıcıdan gelen kesin doğru yolu kullanır:
  `C:\Users\marko\OneDrive\Belgeler\Obsidian Vault`.
version: 1.0.0
author: marko
license: MIT
metadata:
  hermes:
    tags: [obsidian, vault, path, windows, fix]
category: note-taking
audience: user
tags: [note-taking, obsidian, productivity]
---Windows'ta Obsidian vault yolunu düzeltir ve dosya konumunu doğrular.



# Obsidian Vault Path Fix

## Kural

Bu skill kullanıldığında yapılacaklar:

1. Doğru vault yolunu kullan:
   - `C:\Users\marko\OneDrive\Belgeler\Obsidian Vault`
2. Mevcut `OBSIDIAN_VAULT_PATH` değerini oku.
3. Eğer yukarıdaki doğru yola eşit değilse:
   - `.env`'de `OBSIDIAN_VAULT_PATH` olarak yukarıdaki doğru değeri yaz.
4. Vault içindeki ana notları doğrula:
   - `Telegram Gateway Monitor.md`
   - `Hermes Skills Sync.md`
   - `GitHub Repo - asdafgf hermes-gemini-copilot.md`
5. Dosyalar gerekiyorsa doğru vault’a taşı. Dosyalar zaten doğru yerdeyse işlem yapma.
6. Sonuç raporunu üret:
   - Yol düzeltildi.
   - Vault doğrulama başarılı.
   - Gerekli dosya işlemi tamamlandı.

## Uyarı

- Bu skill yalnızca söz konusu doğru yol için çalışır.
- Genel path varsayılanına göre değişiklik yapma.
- Yol değişikliğinde `.env` güncellenmelidir.
