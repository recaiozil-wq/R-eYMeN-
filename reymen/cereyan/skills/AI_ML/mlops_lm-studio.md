---
name: lm-studio
description: "LM Studio local LLM yönetimi — kurulum, GGUF model import, GPU offload, API server, test"
title: "Lm Studio"
tags: [lm-studio, local-llm, gguf, gpu, cuda, model-management]
category: mlops
audience: user
---


> **Kategori:** mlops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | LM Studio local LLM yönetimi — kurulum, GGUF model import, GPU offload, API server, test |
| **Nerede?** | mlops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# LM Studio — Local LLM Yönetimi

LM Studio ile local GGUF modelleri yönetme, GPU offload ayarlama, API serve etme.

Öncelikle `hermes-agent` skill'ini yükle — `lms` ve `hermes` CLI komutları için.

---

## Kurulum (Windows)

```bash
# lmstudio.ai'den indir (en son sürüm)
# veya doğrudan link:
# https://lmstudio.ai/download/latest/win32/x64

# Sessiz kurulum:
Start-Process -FilePath 'C:\path\to\LM-Studio-*.exe' -ArgumentList '/S' -Wait -NoNewWindow
```

Kurulum yolu: `C:\Program Files\LM Studio\LM Studio.exe`
CLI: `C:\Users\<user>\.lmstudio\bin\lms.exe`

---

## Model Yönetimi

### Model İçe Aktarma

```bash
# Elle kopyala (tavsiye edilen):
mkdir -p "/c/Users/<user>/.lmstudio/models/<model-adi>"
cp "/c/Users/<user>/Downloads/<model>.gguf" "/c/Users/<user>/.lmstudio/models/<model-adi>/"

# veya lms import ile:
lms import -y -c "/path/to/model.gguf"
```

### Model Klasörü

```
C:\Users\<user>\.lmstudio\models\
  └── <publisher>-<model>/
       └── <model>.gguf
```

### Modelleri Listele

```bash
lms ls              # Disk'teki tüm modeller
lms ps              # RAM'de yüklü olanlar
lms ps --json       # JSON çıktı (identifier, size, context, status)
```

---

## GPU Offload ile Model Yükleme

```bash
# Otomatik GPU offload:
lms load <model-key> -y --identifier <alias>

# Belirli oran (0.0 - 1.0 arası):
lms load <model-key> --gpu 0.5 -y --identifier <alias>

# Tam GPU offload (VRAM yetersiz kalırsa hata verir):
lms load <model-key> --gpu max -y

# CPU-only (GPU yok):
lms load <model-key> --gpu off -y

# Kaynak tahmini (yüklemeden önce):
lms load <model-key> --gpu max --estimate-only -y
```

### PÜF NOKTALAR

- **--gpu max** ile yüklenemezse **--gpu 0.5** veya **--gpu 0.3** dene
- GPU bellek yetmezse model CPU'da çalışır → çok yavaş olur
- `--gpu off` ile CPU-only dene (hata model dosyasında mı, GPU'da mı ayırt et)
- `--identifier <alias>` ile API'de kolay referans ver

---

## API Server

```bash
# Server başlat (model önceden yüklenmiş olmalı):
lms server start --port 1234

# OpenAI-compatible endpoint:
# POST http://localhost:1234/v1/chat/completions
```

### Test İsteği

```bash
curl -s --max-time 300 http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "<identifier>",
    "messages": [{"role": "user", "content": "Merhaba!"}],
    "temperature": 0.5,
    "max_tokens": 150
  }'
```

### PÜF NOKTALAR

- Reasoning modellerde (Qwen3, DeepSeek-R1) `reasoning_content` ayrı gelir, `content` boş olabilir
- Token limitini (`max_tokens`) reasoning token'ları da tüketir — yeterli ver
- `finish_reason: "length"` = token limitine takıldı, `"stop"` = tam cevap
- Model yavaşsa `--max-time` değerini yüksek tut (300sn+)

---

## Hermes Provider Olarak Kullanma

```bash
# LM Studio'yu Hermes'in ana provider'ı yap:
hermes config set model.provider custom
hermes config set model.base_url "http://localhost:1234/v1"
hermes config set model.default "<model-identifier>"
hermes config set model.api_key ""         # LM Studio key istemez

# Eski provider'a dön:
# hermes config set model.provider deepseek
```

Değişiklikler **yeni session'da** aktif olur (`/reset` veya CLI'ı yeniden başlat).

---

## Model Seçimi — GPU/VRAM Dengesi

| Model | Boyut | VRAM | RAM | Hız | RTX 4070'de? |
|-------|-------|------|-----|-----|------|
| Dolphin 3.0 8B (Q4_K_S) | ~4.7 GB | 4GB yeter | ~5 GB | Hızlı | ✅ Mükemmel |
| Qwen3-32B (Q5_K_M) | ~23.2 GB | 4GB yetmez | ~22 GB | Çok yavaş | ❌ CPU'da kalır |
| Qwen3-8B (Q4_K_M) | ~5 GB | 4GB yeter | ~5 GB | Hızlı | ✅ İyi |

**Kural:** 4GB VRAM için 7B-8B modeller idealdir. 32B modeller CPU'da calisir ve pratik kullanim icin cok yavas kalir.

---

## Sık Hatalar

1. **"Failed to load model"** — model dosyası bozuk olabilir (29 bytes), GGUF sürümü uyumsuz olabilir, veya RAM yetmiyor olabilir. Önce LM Studio'da manuel Load dene, sonra `lms load --gpu off` ile CPU-only dene.
2. **Çok yavaş inference** — model büyük, GPU offload yetersiz. Küçük model dene veya `--gpu` oranını artır.
3. **`content: ""` boş döndü** — reasoning modeli. `max_tokens`'ı yükselt.
4. **Timeout (curl --max-time)** — 32B+ modellerde normal. 300sn+ dene veya küçük model kullan.
5. **İki aynı model görünüyor** — LM Studio Hub indirmesi bozuk 29 bytes dosya + gerçek model. Bozuk olanı `rm -rf ~/.lmstudio/models/lmstudio-community/` ile sil.

## Referanslar
