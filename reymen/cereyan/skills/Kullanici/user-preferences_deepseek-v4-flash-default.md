---
name: deepseek-v4-flash-default
id: deepseek-v4-flash-default
title: "DeepSeek V4 Flash — Varsayılan Model Profili"
description: "DeepSeek V4 Flash modelini 1M context ile yapılandırır. Hermes başlangıcında bu model aktif olmalıdır."
tags: [model, deepseek, config, default, always-active]
category: user-preferences
audience: user
trigger: "session start, /model komutu çalıştırıldığında"
---


> **Kategori:** preferences

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | DeepSeek V4 Flash modelini 1M context ile yapılandırır. Hermes başlangıcında bu model aktif olmalıdır. |
| **Nerede?** | preferences/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# DeepSeek V4 Flash — Varsayılan Profil

Bu profil Hermes'in varsayılan modelini tanımlar.

## Yapılandırma

- **Model:** `deepseek-v4-flash`
- **Provider:** `deepseek`
- **Base URL:** `https://api.deepseek.com/v1` (config.yaml'da tanımlı)
- **Context:** 1M token (1048576)

## Kalıcı Varsayılan Yapma

Bu komutlar config.yaml'a yazar, oturumlar arası kalıcıdır:

```bash
hermes config set model deepseek-v4-flash
hermes config set provider deepseek
```

Doğrulama:

```bash
hermes config show | grep -A5 "Model"
# Çıktı: Model: {'default': 'deepseek-v4-flash', 'provider': 'deepseek'}
```

## Hızlı Geçiş (Geçici — Sadece Bu Oturum)

```
/model deepseek
```

Bu komut sadece mevcut oturum için geçerlidir, config.yaml değişmez.

## Notlar

- `hermes config set provider deepseek` doğrudan çalışır — custom provider ayarı gerekmez
- API anahtarı `.env` içinde `DEEPSEEK_API_KEY` olarak tanımlıdır
- 1M context penceresi aktif
- Uzun oturumlarda context dolumunu izle
- Provider adı: `deepseek` (büyük harf, "deep seek" gibi farklı format denemeleri çalışmaz)
