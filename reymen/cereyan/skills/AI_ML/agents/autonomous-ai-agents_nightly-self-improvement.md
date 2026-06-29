---
name: nightly-self-improvement
title: "Nightly Self Improvement"
tags: [agents, ai]
description: >
  Gece otomatik geliştirme cron job'u. Obsidian vault ve Hermes skill
  kütüphanesini tarar, eksik/eksik parçaları tamamlar, skill'leri
  günceller ve sonucu Telegram'a bildirir. Her gece 02:00'de çalışır.
version: 1.0.0
author: hermes-agent
license: MIT
metadata:
  hermes:
    tags: [nightly, self-improvement, cron, obsidian, skill-maintenance]
audience: user
related_skills: [obsidian-vault-kurallari, hermes-agent, telegram-gateway-monitor]


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | > |
| **Nerede** | `autonomous-ai-agents\autonomous-ai-agents_nightly-self-improvement.md` |
| **Ne Zaman** | Ilgili gorev gerektiginde |
| **Neden** | Autonomous Ai Agents Nightly Self Improvement islemini standartlastirmak icin |
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
Nerede: `autonomous-ai-agents\autonomous-ai-agents_nightly-self-improvement.md`
Ne Zaman: Ilgili gorev gerektiginde
Neden: Autonomous Ai Agents Nightly Self Improvement islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Nightly Self-Improvement

## Amaç

Bu cron job, her gece 02:00'de otomatik olarak çalışır. Hermes'in skill kütüphanesini
ve Obsidian vault'u tarar, geliştirme fırsatlarını belirler ve uygular.

## Zorunlu Adımlar (sıralı)

### 1. Ortam Kontrolü

```
# Vault yolunu doğrula
ls "/c/Users/marko/OneDrive/Belgeler/Obsidian Vault" 2>&1 || echo "VAULT_YOK"

# Skill listesini al
hermes skills list 2>&1

# Cron job listesini al
hermes cron list 2>&1
```

### 2. Skill + Obsidian Taraması

1. `skills_list()` ile tüm skill'leri tara
2. `search_files()` ile Obsidian vault'ta güncellenmesi gereken notları bul:
   - `Hermes/Skills/` altındaki skill notları
   - `Hermes/` altındaki yapılandırma notları
3. Her skill için `skill_view()` ile oku
4. Eksik veya güncellenmesi gereken kısımları belirle:
   - Skill adı çakışması var mı? (duplicate kontrol)
   - Skill'de hatalı/eskimiş yol var mı? (örn. `C:\Users\marko\Documents\...` yerine `C:\Users\marko\OneDrive\...`)
   - Eksik linked file var mı? (`references/`, `templates/`, `scripts/`)

### 3. Skill Güncelleme

- **Duplicate skill tespit edilirse**: eski/beklenmedik konumdakini `skill_manage(action='delete', absorbed_into='<hedef-skill>')` ile kaldır
- **Eksik linked file varsa**: `skill_manage(action='write_file', file_path='references/...')` ile ekle
- **Yanlış yol varsa**: `skill_manage(action='patch')` ile düzelt
- **Yeni bir teknik/çözüm bulunduysa**: skill oluştur veya mevcut skill'e ekle

### 4. Telegram Bildirimi

Sonuçları şu formatta Telegram'a bildir:

```
[gece-gelistirme] Tamamlandı:
- ✓ <ne yapıldığının kısa özeti>
- ✓ <ikinci değişiklik>
...
Süre: ~N dk
```

⚠️ Telegram token'ı `.env`'de maskelenmiş olabilir. Eğer `send_message` başarısız olursa:
- Önce `.env`'yi kontrol et: `grep TELEGRAM_BOT_TOKEN /c/Users/marko/AppData/Local/hermes/.env`
- `***` içeriyorsa token maskelenmiş demektir. Bildirimi log'a yaz ve cron (local) delivery'ye bırak.
- Token düzeltmesi YAPMA — bu skill'in görevi değil. Kullanıcıya bırak.

### 5. Obsidian Kaydı

Değişiklikleri Obsidian vault'a şu formatta kaydet:

```
C:\Users\marko\OneDrive\Belgeler\Obsidian Vault\Hermes\Cron\gece-gelistirme.md
```

İçerik:
- Çalışma tarihi/saati
- Yapılan değişiklikler (maddeler halinde)
- Karşılaşılan sorunlar
- Bir sonraki çalışma için notlar

## Pitfall'lar

- **Telegram token maskelenmesi**: `.env`'de `TELEGRAM_BOT_TOKEN=...***...` varsa gateway çalışmaz.
  Bu skill telegram token'ını düzeltmez — sadece tespit eder ve bildirir.
- **Duplicate skill adları**: Aynı isimde iki skill varsa `skill_view()` hata verir.
  Tam kategorili yol kullan: `kategori/skill-adi`
- **shell hook hataları**: `skill_created_hook.py` bulunamazsa hata alınır — bu normaldir, cron devam eder.
- **Cron delivery**: cron job delivery'si `local` veya `telegram:6328823909` olabilir.
  Telegram token sorunluysa delivery başarısız olur — job yine de çalışır.

## Başarı Kriterleri

✓ Skill listesi tarandı
✓ Obsidian vault notları kontrol edildi
✓ En az bir geliştirme/güncelleme yapıldı (veya "yapılacak bir şey yok" raporlandı)
✓ Sonuç Telegram'a bildirildi (veya bildirim denenip başarısız olduğu log'a yazıldı)
✓ Obsidian vault'a çalışma kaydı eklendi
