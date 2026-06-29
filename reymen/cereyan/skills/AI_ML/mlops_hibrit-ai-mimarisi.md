---
name: hibrit-ai-mimarisi
title: "Hibrit AI Mimarisi"
description: "Hermes'in iki katmanlı AI mimarisi — Ollama (yerel) + DeepSeek (uzak) model yönlendirme kuralları ve geçiş mekanizması."
tags: [hibrit, hybrid, ollama, deepseek, AI-mimari, model-routing]
category: mlops
audience: user
related_skills: [dolphin-llama3, hibrit-ai-yonlendirme-kurali]
---


> **Kategori:** mlops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Hermes'in iki katmanlı AI mimarisi — Ollama (yerel) + DeepSeek (uzak) model yönlendirme kuralları ve geçiş mekanizması. |
| **Nerede?** | mlops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Hibrit AI Mimarisi — Ollama + DeepSeek

Hermes iki model katmanıyla çalışır:

## Katman 1: Yerel (Ollama)
- **Ne zaman:** Kısa (<40 kelime) ve basit sorular için
- **Avantaj:** Offline, ücretsiz, hızlı yanıt
- **Model:** `dolphin-llama3` (Ollama üzerinden)
- **Endpoint:** `localhost:11434/v1`
- **Fallback rolü:** Uzak bağlantı koparsa otomatik devralır
- **Ayrıca:** Reddit-benzeri, düşük öncelikli veya alternatif akış gerektiren görevler de bu katmana yönlendirilir

> Detaylı yönlendirme kuralları için `hibrit-ai-yonlendirme-kurali` skill'ine bak.

## Katman 2: Uzak (Değişken Provider)
- **Ne zaman:** Uzun (>40 kelime), karmaşık, analiz/kod/tasarım gerektiren sorular
- **Avantaj:** Yüksek kalite, geniş bilgi, güçlü mantık
- **Model:** Provider'a göre değişir (deepseek-chat, stepfun/step-3.7-flash, claude-sonnet, vb.)
- **Mevcut aktif:** `stepfun/step-3.7-flash:free` (nous provider üzerinden)
- **Geçmiş modeller:** `deepseek-chat` (eski), `dolphin-llama3` (Ollama yedek)
- **Auth:** Provider'a göre `.env` veya `config.yaml` içinde `api_key`

## Yönlendirme Mantığı

```
Sorgu gelir
  ├─ <40 kelime ve basit → Ollama (yerel)
  ├─ ≥40 kelime veya "analiz/kod/tasarla" içeriyor → Uzak provider (aktif model)
  └─ Uzak bağlantı koparsa → otomatik Ollama'ya düş
  └─ Aktif model reddederse/red flag → dolphin-llama3'e düş (dolphin-llama3 skill)

## config.yaml Yapılandırması (Mevcut — custom provider ile)

```yaml
# ÜST DÜZEY (default model)
model:
  default: deepseek-v4-flash
  provider: custom          # "custom" provider, doğrudan model_aliases'den okur
  model: deepseek-v4-flash
  api_key: ''               # API key .env'den okunur
  base_url: https://api.deepseek.com/v1
  context_length: 1048576

# Model alias'ları (provider: custom ile çalışır)
model_aliases:
  deepseek:
    model: deepseek-v4-flash
    provider: custom
    base_url: https://api.deepseek.com/v1
    context_length: 1048576
  dolphin:
    model: dolphin-llama3:latest
    provider: custom
    base_url: http://localhost:11434/v1
    context_length: 65536

# Provider'lar (custom kullanıldığında boş olabilir)
providers: {}

# Fallback — BOŞ OLURSA KREDİ BİTİNCE ÇÖKER
fallback_providers: []
```

**NOT:** `custom` provider, API key'i `.env`'den alır (`DEEPSEEK_API_KEY`). `providers:` listesi sadece isimli provider'lar içindir — `custom` kullanıldığında boş olabilir. Fallback eklemek için `fallback_providers` dizisine yeni bir provider eklenmeli.

## Hatırlatmalar
- API anahtarları `.env` dosyasında saklanır, asla koda yazılmaz
- `env_watcher.py` .env değişikliklerini Obsidian'a yansıtır
- Mevcut aktif profil: `default` (stepfun/step-3.7-flash:free ana, Ollama yedek)
- Provider değiştiğinde (ör: deepseek → nous) skill'deki model referansları güncellenmeli
- `hibrit-ai-yonlendirme-kurali` skill'inde yönlendirme mantığının detaylı kodu var
