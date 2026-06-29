---
name: deepseek-1m-context
title: "DeepSeek 1M Context"
tags: [machine-learning, mlops]
description: "DeepSeek 1M token context penceresini aktif eder — context_length=1048576, ollama_num_ctx=1048576"
version: 1.0.0
author: Hermes Agent
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [deepseek, context, 1m, config, setup]
audience: user
related_skills: [hermes-agent, hibrit-ai-mimarisi]
---


> **Kategori:** mlops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | DeepSeek 1M token context penceresini aktif eder — context_length=1048576, ollama_num_ctx=1048576 |
| **Nerede?** | mlops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# DeepSeek 1M Context

Bu skill, DeepSeek'in 1M token context penceresini aktif eder.

## Ne Yapar

config.yaml'de şu değerleri ayarlar:

```yaml
model:
  context_length: 1048576   # 1 milyon token
  ollama_num_ctx: 1048576   # Ollama context boyutu (1M)
```

## Kullanım

### 1. Manuel Kontrol

Config'de değerlerin doğru olduğunu doğrula:

```bash
grep -E "context_length|ollama_num_ctx" ~/AppData/Local/hermes/config.yaml
```

Beklenen çıktı:
```
context_length: 1048576
ollama_num_ctx: 1048576
```

### 2. El İle Ayarla (gerekirse)

```bash
hermes config set model.context_length 1048576
hermes config set model.ollama_num_ctx 1048576
```

### 3. On-Session-Start Hook (Otomatik)

Config her oturumda otomatik kontrol edilir. Eksikse düzeltilir.
Hook script'i: `C:\Users\marko\AppData\Local\hermes\hooks\verify_1m_context.py`

## Önemli

- Bu ayar DeepSeek API üzerinden çalışır (base_url: https://api.deepseek.com/v1)
- `context_length` = model context penceresi (1M token)
- `ollama_num_ctx` = Ollama uyumluluk için aynı değer
- Yeni session açıldığında etkili olur
