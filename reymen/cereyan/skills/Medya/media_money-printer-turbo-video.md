
> **Kategori:** media

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Video ajanı |
| **Ne?** | Media_Money Printer Turbo Video |
| **Nerede?** | media/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: money-printer-turbo-video
description: MoneyPrinterTurbo ile otomatik video oluşturma — kurulum, yapılandırma, CLI ve WebUI kullanımı.
title: "Money PRinter Turbo Video"
triggers:
  - moneyprinter
  - video oluştur
  - otomatik video
  - MoneyPrinterTurbo
  - deepseek video

audience: user
tags: [audio, media, video]
category: media---

# MoneyPrinterTurbo Video Oluşturma

MoneyPrinterTurbo — konu/konsept ver, AI senaryo yazsın, seslendirsin, altyazı eklesin, videoyla birleştirsin.

## Kurulum

```bash
cd /c/Users/marko
git clone https://github.com/harry0703/MoneyPrinterTurbo.git
cd MoneyPrinterTurbo
uv sync --frozen        # bağımlılıkları yükle (önerilen)
# Alternatif: .venv/Scripts/python.exe -m pip install -r requirements.txt
```

Proje dizini: `C:\Users\marko\MoneyPrinterTurbo`

## Yapılandırma (config.toml)

Dosya: `C:\Users\marko\MoneyPrinterTurbo\config.toml`

### LLM Sağlayıcı — DeepSeek

```toml
[app]
llm_provider = "deepseek"
deepseek_api_key = "sk-..."
deepseek_base_url = "https://api.deepseek.com"
deepseek_model_name = "deepseek-chat"
```

### Video Kaynağı — Local (API Key Gerekmez)

```toml
[app]
video_source = "local"
```

API key gerektiren kaynaklar: `pexels`, `pixabay`, `coverr`. Local kaynak için video dosyaları `storage/local_videos/` altına konur.

### Ses (TTS)

Edge TTS ücretsiz, API key gerekmez. Türkçe sesler:

| Ses | Cinsiyet |
|-----|----------|
| `tr-TR-EmelNeural` | Kadın |
| `tr-TR-AhmetNeural` | Erkek |

Ses config.toml'a eklenebilir (`voice_name = "tr-TR-EmelNeural"`) veya CLI/WebUI'de parametre olarak verilir.

Tüm sesler: `docs/voice-list.txt`

## Çalıştırma

### CLI ile Video Oluşturma

```bash
cd /c/Users/marko/MoneyPrinterTurbo
.venv/Scripts/python.exe cli.py \
  --video-subject "KONU" \
  --video-source local \
  --video-materials "C:/Users/marko/MoneyPrinterTurbo/storage/local_videos/video.mp4" \
  --voice-name "tr-TR-EmelNeural"
```

**ÖNEMLİ:** Local video yolu **tam Windows yolu** olmalı (örn. `C:/Users/.../storage/local_videos/dosya.mp4`).
Göreceli yol hata verir ("file does not exist").

### Sadece Senaryo Üretme (Video Yok)

```bash
.venv/Scripts/python.exe cli.py --video-subject "KONU" --video-source local --stop-at script
```

`--stop-at` değerleri: `script`, `terms`, `audio`, `subtitle`, `materials`, `video`

### Backend + WebUI Başlatma

**Backend (API):**
```bash
cd /c/Users/marko/MoneyPrinterTurbo
.venv/Scripts/python.exe main.py
```
Adres: http://localhost:8080/docs

**WebUI (Streamlit):**
```bash
cd /c/Users/marko/MoneyPrinterTurbo
.venv/Scripts/python.exe -m streamlit run webui/Main.py --server.port=8501 --server.headless=true
```
Adres: http://localhost:8501

Veya `webui.bat`'a çift tıkla.

## Püf Noktalar

- **Config değişikliğinden sonra** WebUI/backend yeniden başlatılmalı
- Local video için dosya mutlaka `storage/local_videos/` altında olmalı
- Port 8501 doluysa `--server.port=8510` gibi farklı bir port dene
- Video çıktısı `storage/tasks/<task_id>/final-1.mp4` yolunda oluşur
- Video kısa (5sn) ise audio süresine yetişmek için otomatik loop yapar
- DeepSeek API rate-limit'e takılırsa bekle ve tekrar dene
