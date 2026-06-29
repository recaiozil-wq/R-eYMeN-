---
name: money-printer-turbo-kurulum
description: MoneyPrinterTurbo kurulumu, yapılandırması ve video oluşturma iş akışı
title: "Money PRinter Turbo Kurulum"
category: software-development
audience: contributor
tags: [coding, development]
---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | MoneyPrinterTurbo kurulumu, yapılandırması ve video oluşturma iş akışı |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# MoneyPrinterTurbo Kullanım Kılavuzu

## Kurulum
- Repo: `C:\Users\marko\MoneyPrinterTurbo`
- Sanal ortam: `.venv` (uv sync ile 125 paket)
- Python 3.11

## Yapılandırma (config.toml)
- `llm_provider = "deepseek"`
- `deepseek_api_key` = `.env`'de
- `pexels_api_keys` = dolu
- `video_source = "pexels"`

## Önemli Düzeltmeler
- Gemini TTS hatası düzeltildi (API key yoksa Edge TTS'e düşer)
- Sessiz video: `--voice-name "no-voice"`
- Config WebUI tarafından sıfırlanabiliyor

## Video Oluşturma
```bash
.venv\Scripts\python.exe cli.py --video-subject "KONU" --video-source pexels --voice-name "no-voice" --no-subtitle-enabled
```

## Özel Scriptler
- `iki_kita.py`, `iki_kita_4k.py`, `simit_ayran.py`, `make_video.py`

## API Key'ler
- DeepSeek: config.toml
- Pexels: config.toml
- Kling AI: .env
- RunwayML: .env

## WebUI
- http://localhost:8501
- Backend: http://localhost:8080/docs

## Manim
- pip install manim ile kurulu
