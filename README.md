[![CI](https://github.com/recaiozil-wq/R-eYMeN-/actions/workflows/ci.yml/badge.svg)](https://github.com/recaiozil-wq/R-eYMeN-/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/Version-0.9.0--beta-orange)](https://github.com/recaiozil-wq/R-eYMeN-/releases)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](CONTRIBUTING.md)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

# 🤖 ReYMeN — Türkçe Otonom AI Asistanı

**ReYMeN, çoklu-provider LLM katmanı, araç çağrı motoru ve kapalı öğrenme döngüsü ile çalışan, tamamen Türkçe otonom bir yapay zeka asistanıdır.**

| Özellik | Açıklama |
|:--------|:---------|
| 🧠 **12+ LLM Provider** | DeepSeek, OpenAI, Anthropic, Gemini, Groq, xAI, OpenRouter, Ollama, LM Studio |
| 🛠️ **100+ Araç** | Dosya, terminal, web, tarayıcı, görsel, video, ses, kanban |
| 🔄 **Kapalı Öğrenme** | Hata→çözüm hafızası, self-improvement metrikleri |
| 🧩 **Hook Sistemi** | 8 olay tipi (session/tur/araç/hata/context) |
| 🌐 **Web UI** | FastAPI + HTMX yönetim paneli |
| 📊 **Kanban** | Kart/kolon/öncelik/deadline yönetimi, WIP limit |
| 💰 **Cost Tracking** | SQLite tabanlı API harcama takibi |
| 🔐 **Güvenlik** | Guardrails, sandbox, PII redaction, path doğrulama |
| 🧠 **Hafıza** | OnceHafıza (vektör), FTS5 session search, context compression |
| 🤖 **Telegram Bot** | Çoklu bot desteği (Pasa_38, Kiral38, ReYMeNbot) |

---

## 🚀 Kurulum

### Gereksinimler

- Python **3.10**, **3.11** veya **3.12**
- pip / venv
- (Opsiyonel) ffmpeg — ses/video işleme için
- (Opsiyonel) Playwright — tarayıcı otomasyonu için

### Windows

```powershell
# 1. Projeyi indir
git clone https://github.com/recaiozil-wq/R-eYMeN-.git
cd ReYMeN-Ajan

# 2. Sanal ortam oluştur
python -m venv venv
venv\Scripts\activate

# 3. Bağımlılıkları yükle
pip install -e .

# 4. (Opsiyonel) Tüm özellikler için (chromadb, torch, opencv, vb.)
pip install -e ".[full]"

# 5. (Opsiyonel) Geliştirme araçları
pip install -e ".[dev]"

# 5. API anahtarlarını ayarla
cp .env.example .env
# .env dosyasını düzenle: en az DEEPSEEK_API_KEY gir
```

### Linux / Mac

```bash
# 1. Projeyi indir
git clone https://github.com/recaiozil-wq/R-eYMeN-.git
cd ReYMeN-Ajan

# 2. Sanal ortam oluştur
python3 -m venv venv
source venv/bin/activate

# 3. Bağımlılıkları yükle
pip install -r requirements.txt

# 4. (Opsiyonel) Tüm özellikler
pip install -e ".[full]"

# 5. API anahtarlarını ayarla
cp .env.example .env
chmod 600 .env
nano .env
```

### Tek Komut Kurulum

```bash
# Linux/Mac
curl -fsSL https://raw.githubusercontent.com/recaiozil-wq/R-eYMeN-main/install.sh | bash

# Windows PowerShell
irm https://raw.githubusercontent.com/recaiozil-wq/R-eYMeN-main/install.ps1 | iex
```

---

## ⚙️ Ortam Değişkenleri

`.env.example` dosyasını `.env` olarak kopyala ve düzenle:

| Değişken | Zorunlu | Açıklama |
|:---------|:-------:|:---------|
| `DEEPSEEK_API_KEY` | **Evet** | Ana LLM provider (en uyumlu) |
| `BOT_TOKEN_PASA` | Hayır | Pasa_38 Telegram Bot token |
| `BOT_TOKEN_KRAL` | Hayır | Kiral38 Telegram Bot token |
| `BOT_TOKEN_REYMEN` | Hayır | ReYMeN_ReYMeNbot token |
| `OPENAI_API_KEY` | Hayır | OpenAI yedek provider |
| `ANTHROPIC_API_KEY` | Hayır | Anthropic Claude yedek |
| `GROQ_API_KEY` | Hayır | Groq yedek provider |
| `OPENROUTER_API_KEY` | Hayır | OpenRouter yedek |
| `XAI_API_KEY` | Hayır | xAI/Grok yedek |
| `FAL_KEY` | Hayır | Görsel oluşturma (FAL.ai) |

> 💡 Sadece **DEEPSEEK_API_KEY** zorunlu. Diğerleri boş kalırsa o provider pasif olur.

---

## 🎮 Kullanım

### CLI (REPL)

```bash
# Proje dizininde
python reymen_launcher.py

# Veya PATH varsa
reymen

# Tek soru (one-shot)
python reymen_launcher.py -z "merhaba"

# Versiyon kontrol
python reymen_launcher.py --version
```

### Bileşen Başlatma

```bash
# Telegram Bot (tümü)
python reymen_launcher.py start --mode bot --bot-name all

# Belirli bot
python reymen_launcher.py start --mode bot --bot-name pasa

# Gateway
python reymen_launcher.py start --mode gateway

# Web UI
python reymen_launcher.py start --mode web

# Sistem tepsisi (arkaplan)
python reymen_launcher.py start --mode tray

# Sistem kontrolü
python reymen_launcher.py start --mode doctor
```

### Web UI

```bash
python reymen_launcher.py start --mode web
# http://localhost:8080
```

### Python API

```python
from reymen.cereyan.beyin import Beyin
from reymen.cereyan.motor import Motor
from reymen.cereyan.conversation_loop import ConversationLoop

beyin = Beyin(config={"provider": "deepseek", "model": "deepseek-v4-flash"})
motor = Motor()
cl = ConversationLoop(motor=motor, beyin=beyin)
sonuc = cl.run_conversation("Merhaba, nasılsın?")
print(sonuc["yanit"])
```

---

## 🧪 Test

```bash
# Tüm testler
pytest tests/ -v

# Coverage ile
pytest --cov=reymen tests/

# Belirli modül
pytest tests/test_beyin.py -v
```

---

## 🏗️ Proje Yapısı

```
ReYMeN-Ajan/
├── reymen_launcher.py      # Ana giriş noktası
├── config.yaml             # Merkezi yapılandırma
├── .ReYMeN/                # Çalışma zamanı verileri
│   ├── SOUL.md             # Kişilik tanımı
│   ├── durum.json          # Proje durumu
│   └── session.db          # SQLite FTS5 oturum geçmişi
├── reymen/
│   ├── ag/                 # Gateway katmanı (Telegram/Discord/WhatsApp)
│   ├── arac/               # Araç katmanı (100+ araç)
│   ├── cereyan/            # Ana işlem katmanı
│   │   ├── beyin.py        # LLM bağlantı katmanı
│   │   ├── motor.py        # Eylem motoru
│   │   └── conversation_loop.py  # Konuşma döngüsü
│   ├── core/               # Çekirdek modüller
│   ├── guvenlik/           # Güvenlik katmanı
│   ├── hafiza/             # Hafıza katmanı
│   └── sistem/             # Sistem yönetimi
└── tests/                  # Test dosyaları
```

---

## 🔌 Entegrasyonlar

| Servis | Tür | Durum |
|:-------|:---:|:------|
| **DeepSeek** | LLM | ✅ Varsayılan |
| **OpenAI** | LLM | ✅ |
| **Anthropic** | LLM | ✅ |
| **Google Gemini** | LLM | ✅ |
| **Groq** | LLM | ✅ |
| **xAI (Grok)** | LLM | ✅ |
| **OpenRouter** | LLM | ✅ |
| **Ollama** | LLM (lokal) | ✅ |
| **LM Studio** | LLM (lokal) | ✅ |
| **Telegram** | Mesajlaşma | ✅ |
| **Discord** | Mesajlaşma | ✅ |
| **FAL.ai** | Görsel | ✅ |
| **yt-dlp** | Video | ✅ |
| **Playwright** | Tarayıcı | ✅ |

---

## 🗺️ Yol Haritası

- [x] Çoklu LLM provider
- [x] 100+ araç
- [x] Telegram bot (çoklu)
- [x] Web UI
- [x] Kapalı öğrenme döngüsü
- [x] Kanban board
- [x] Hata→çözüm hafızası
- [ ] Çoklu agent orchestration
- [ ] WhatsApp entegrasyonu
- [ ] Dağıtık A2A
- [ ] Eklenti marketi

---

## 📜 Lisans

MIT License — bakınız [LICENSE](LICENSE)

---

## 🤝 Katkı

Pull request'ler açıktır! [CONTRIBUTING.md](CONTRIBUTING.md) dosyasına bak.

**Öncelikli ihtiyaçlar:**
- Test coverage artırma (%6 → %50+)
- Linux/macOS testleri
- Dokümantasyon
- Hata raporları

---

## 💬 Topluluk

| Kanal | Link |
|:------|:-----|
| GitHub Issues | [Hata bildir / Öneri yap](https://github.com/recaiozil-wq/R-eYMeN-/issues/new/choose) |
| Telegram | @Pasa_38 |
| Discord | (yakında) |
