---
name: lm-studio-local-llm
title: "LM Studio API ile Model Yükleme"
description: "LM Studio v0.4.16.0 REST API ile model yükleme, GPU offload (GUI), context ve flash_attention ayarları. Doğrulanmış curl komutları."
version: 2.0.0
platforms: [windows]
audience: user
tags: [lm-studio, api, model-load, gpu, cuda, gguf, local-llm]
---


> **Kategori:** mlops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | LM Studio v0.4.16.0 REST API ile model yükleme, GPU offload (GUI), context ve flash_attention ayarları. Doğrulanmış curl komutları. |
| **Nerede?** | mlops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# LM Studio API ile Model Yükleme

## API ile Model Yükleme

**LM Studio v0.4.16.0** — API kabul edilen parametreler:

| Parametre | Değer | Durum |
|-----------|-------|--------|
| `model` | Model key (zorunlu) | ✅ |
| `context_length` | 8192, 32768 (max) | ✅ |
| `flash_attention` | true/false | ✅ |
| `echo_load_config` | true (config dönüşü) | ✅ |
| `gpu`, `parallel`, `offload_kv_cache_to_gpu` | — | ❌ Bu derlemede tanınmaz |

```bash
# Dogru komut — context tam kapasite
curl -s -X POST http://localhost:1234/api/v1/models/load \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llava-v1.6-mistral-7b",
    "context_length": 32768,
    "flash_attention": true,
    "echo_load_config": true
  }'
```

## Önemli Notlar

- `context_length: 32768` = modelin tam kapasitesi (LLaVA 7B, n_ctx_train=32768). 8192 verirsen `"n_ctx_seq (8192) < n_ctx_train (32768)"` uyarısı alırsın
- `gpu` parametresi bu derlemede yok. **GPU offload ayarı sadece GUI'den yapılır:** Settings > Model Defaults > GPU Offload slider
- `parallel` ve `offload_kv_cache_to_gpu` API'de yok ama gerek yok — varsayılan olarak `n_parallel=4` ve KV cache otomatik yönetilir
- `echo_load_config: true` eklenirse yanıtta `load_config` altında nihai konfigürasyon görünür

## Bilinen Model Yükleme Sorunları

### Çalışan Modeller
| Model | API Key | Yükleme | Not |
|-------|---------|---------|-----|
| LLaVA 7B | `llava-v1.6-mistral-7b` | ✅ Anında yüklenir, hemen kullanıma hazır | Genel sohbet ve görsel analiz |
| Nomic Embed | `text-embedding-nomic-embed-text-v1.5` | ✅ | Embedding için |

### Çalışmayan / Sorunlu Modeller

| Model | API Key | Durum | Ne Yapmalı |
|-------|---------|-------|-----------|
| Dolphin 8B | `cognitivecomputations.dolphin3.0-llama3.1-8b` | ❌ "Error loading model" | GGUF bozuk olabilir. GUI'den manuel yüklemeyi dene |
| Qwen3 32B | `qwen3-32b-obliterated-i1` | ⏱ API'den yüklenemez (timeout) | 32B model çok büyük, API timeout'a takılır. **GUI'den manuel yükle:** LM Studio aç → modeli seç → Load butonu |

### API'den Yükleme Stratejisi

1. Önce küçük modelleri dene (7B-8B) — bunlar API ile hızlı yüklenir
2. 32B+ modeller için GUI kullan — API timeout riski yüksek
3. Yüklü modeli kontrol et: `curl -s http://localhost:1234/v1/chat/completions` ile test et
4. Model API key'i `/v1/models` endpoint'indeki `id` alanıdır (GGUF dosya adı değil)

## Model Key'leri

```bash
curl -s http://localhost:1234/api/v1/models/ | python3 -c "import sys,json; [print(m['key']) for m in json.load(sys.stdin)['models']]"
```

| Model | Key | Not |
|-------|-----|-----|
| Dolphin 8B | `cognitivecomputations.dolphin3.0-llama3.1-8b` | |
| LLaVA 7B (shadowbeast) | `shadowbeast/llava-v1.6-mistral-7b` | ✅ Çalışan, 4.7 GB |
| LLaVA 7B (lmstudio-community) | `lmstudio-community/llava-v1.6-mistral-7b` | ❌ Bozuk indirme (29 bytes) |
| Qwen3 32B | `qwen3-32b-obliterated-i1` | |
| Nomic Embed | `text-embedding-nomic-embed-text-v1.5` | |

## Runtime Hataları

### "Only user and assistant roles are supported!" (Jinja Template)

**Hata:** LM Studio'dan `400 Bad Request` döner, jinja template hatası:
```
Error rendering prompt with jinja template: "Only user and assistant roles are supported!"
```

**Sebep:** Bazı modeller (özellikle `llava-v1.6-mistral-7b`) prompt template'inde `system` rolünü desteklemez. Sadece `user` ve `assistant` rollerini kabul eder.

**Çözüm:** System mesajını user mesajına çevir, başına `[SISTEM]:` gibi bir prefix ekle:

```python
# Hatalı (system rolü kullanılır):
mesajlar = [
    {"role": "system", "content": "Sen yardımsever bir asistansın."},
    {"role": "user", "content": "2+2 kaç eder?"}
]

# Doğru (system → user çevrilir):
mesajlar = [
    {"role": "user", "content": "[SISTEM]: Sen yardımsever bir asistansın."},
    {"role": "user", "content": "2+2 kaç eder?"}
]
```

**Hangi modellerde görülür:**
| Model | Hata | Çözüm |
|-------|------|-------|
| `llava-v1.6-mistral-7b` | ✅ Sistem rolü kabul etmez | User'a çevir |
| `cognitivecomputations.dolphin3.0-llama3.1-8b` | ❌ Sistem rolü çalışır | Normal kullan |
| `qwen3-32b-obliterated-i1` | ❌ Sistem rolü çalışır | Normal kullan |

## GPU Durumu

```
GPU: NVIDIA RTX 4070 Laptop (8GB VRAM)
Backend: llama.cpp CUDA
VRAM kullanimi: ~5.7GB / 8.2GB (LLaVA 7B ile)
```

Doğrulama: `nvidia-smi` veya `curl -s http://localhost:1234/api/v1/models/`

## Kazanım

Bu öğrenimle elde edilenler:
1. LM Studio REST API'si (v0.4.16.0) sadece `model`, `context_length`, `flash_attention`, `echo_load_config` parametrelerini kabul eder
2. GPU offload API'den yapılamaz, GUI'den yapılır
3. Model key = API'deki `key` alanı, GGUF dosya adı değil
4. `echo_load_config: true` ile yüklenen config görülebilir
5. Varsayılan GPU ayarları: CUDA, flash_attention açık, KV cache GPU'da, parallel=4
