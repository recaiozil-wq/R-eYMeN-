[![CI](https://github.com/recaiozil-wq/reymen-agean/actions/workflows/ci.yml/badge.svg)](https://github.com/recaiozil-wq/reymen-agean/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.0.1-orange)](https://github.com/recaiozil-wq/reymen-agean/releases)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](CONTRIBUTING.md)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

# 🤖 ReYMeN — Türkçe Otonom AI Asistanı

**ReYMeN** (Recaio Yapay Merkezi ENgine), çoklu-provider LLM katmanı, 100+ araçlı eylem motoru ve kapalı öğrenme döngüsü ile çalışan, tamamen Türkçe otonom bir yapay zeka asistanıdır.

Geliştiriciler, DevOps mühendisleri ve güvenlik araştırmacıları için tasarlandı: Telegram üzerinden komut verirsiniz, ReYMeN terminal, dosya sistemi, tarayıcı, görsel işleme ve 100'den fazla araçla sizin adınıza işlem yapar. Hatalarından öğrenir, çözümleri hafızasına kaydeder, tekrarında aynı hatayı yapmaz.

## 🤔 Neden ReYMeN?

ReYMeN, yalnızca bir araç değil; Türkçe konuşan geliştiricilere "AI ajan" (agent) mantığını öğretmek, birlikte geliştirmek ve katkıda bulunanların kendi fikirlerini hayata geçirmesine alan açmak için var. Projenin her satırı, bir geliştiricinin —kendi ihtiyacından yola çıkarak— tek başına başlattığı, sonra toplulukla büyümesini umduğu bir çabanın ürünüdür.

Geliştirilmekte olan vizyon şu: ReYMeN'in kendi hatalarını tespit edip otonom şekilde Python kodu üreterek düzeltmesi. Bugün itibarıyla hata → çözüm hafızası (OnceHafıza) çalışıyor; self-heal ve otonom kod üretimi ise adım adım olgunlaştırılıyor. Bu, henüz "tam çalışan özellik" değil, **üzerinde çalışılan ve katkıya açık bir hedef**. Fikirleriniz, PR'larınız ve deneyimleriniz bu hedefi şekillendirecek.

ReYMeN, Nous Research'in [Hermes Agent](https://hermes-agent.nousresearch.com) mimarisinden ilham alır. Ayrıca Linux ve açık kaynak ekosisteminin yıllardır süren karşılıksız emeği olmasaydı, bu proje bugünkü halinde olmazdı. Hepsine teşekkür ederiz.

Katkı, öneri ve gönüllülüğe açığız. Yol haritamıza göz atın, bir issue açın veya doğrudan PR gönderin: [CONTRIBUTING.md](CONTRIBUTING.md).

Bağış mekanizması (GitHub Sponsors vb.) şu an aktif değil. İleride topluluk ilgisi olursa değerlendirilebilir.

> *For English readers: see below for the English version.*

---

### Why ReYMeN? (English)

ReYMeN exists to help Turkish-speaking developers understand the "AI agent" paradigm, build together, and create space for contributors to grow their own ideas. Every line of this project started as a single developer's need — built alone, then opened up for the community to shape.

The longer-term vision: ReYMeN detecting its own errors and autonomously fixing them by generating Python code. Today, the error → solution memory (OnceHafıza) is working; self-heal and autonomous code generation are being iterated on. This is **not a finished feature — it's a work-in-progress goal, open to contribution**. Your ideas, PRs, and experience will shape it.

ReYMeN is inspired by Nous Research's [Hermes Agent](https://hermes-agent.nousresearch.com) architecture. Separately, the Linux and open-source ecosystem's years of unpaid labor made this project possible. Thank you to all.

Contributions, suggestions, and volunteering are welcome. Check the roadmap, open an issue, or send a PR: [CONTRIBUTING.md](CONTRIBUTING.md).

Donations (GitHub Sponsors, etc.) are not active yet. Will be considered if there's community interest.

---

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

> 📸 *Ekran görüntüsü önerisi: CLI oturumu, Telegram bot sohbeti ve Web UI panosunu yan yana gösteren bir collaj — okunabilirliği artırır.*

---

## 🚀 Kurulum

### Gereksinimler

- Python **3.11**, **3.12** veya **3.13**
- pip / venv
- (Opsiyonel) ffmpeg — ses/video işleme için
- (Opsiyonel) Playwright — tarayıcı otomasyonu için

### Windows

```powershell
# 1. Projeyi indir
git clone https://github.com/recaiozil-wq/reymen-agean.git
cd R-eYMeN-          # clone klasör adı: R-eYMeN-

# 2. Sanal ortam oluştur
python -m venv venv
venv\Scripts\activate

# 3. Bağımlılıkları yükle
pip install -e .

# 4. (Opsiyonel) Tüm özellikler için (chromadb, torch, opencv, vb.)
pip install -e ".[full]"

# 5. (Opsiyonel) Geliştirme araçları
pip install -e ".[dev]"

# 6. API anahtarlarını ayarla
cp .env.example .env
notepad .env          # en az DEEPSEEK_API_KEY gir
```

### Linux / Mac

```bash
# 1. Projeyi indir
git clone https://github.com/recaiozil-wq/reymen-agean.git
cd R-eYMeN-

# 2. Sanal ortam oluştur
python3 -m venv venv
source venv/bin/activate

# 3. Bağımlılıkları yükle
pip install -e .

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
curl -fsSL https://raw.githubusercontent.com/recaiozil-wq/reymen-agean/main/install.sh | bash

# Windows PowerShell
irm https://raw.githubusercontent.com/recaiozil-wq/reymen-agean/main/install.ps1 | iex
```

### Pre-commit Hook (Çoklu Kopya Uyarısı)

Bu repo birden fazla local kopyada çalışılabiliyor. Commit öncesi `git fetch` ile remote'un gerisinde kalıp kalmadığınızı kontrol eden bir hook için:

```bash
bash scripts/install-hooks.sh
```

---

## ⚙️ Ortam Değişkenleri

`.env.example` dosyasını `.env` olarak kopyala ve düzenle (en az `DEEPSEEK_API_KEY` zorunlu):

| Değişken | Zorunlu | Açıklama |
|:---------|:-------:|:---------|
| `DEEPSEEK_API_KEY` | **Evet** | Ana LLM provider (en uyumlu) |
| `OPENAI_API_KEY` | Hayır | OpenAI yedek provider |
| `ANTHROPIC_API_KEY` | Hayır | Anthropic Claude yedek |
| `GROQ_API_KEY` | Hayır | Groq yedek provider |
| `OPENROUTER_API_KEY` | Hayır | OpenRouter yedek |
| `XAI_API_KEY` | Hayır | xAI/Grok yedek |
| `FAL_KEY` | Hayır | Görsel oluşturma (FAL.ai) |

> 💡 Sadece **DEEPSEEK_API_KEY** zorunlu. Diğerleri boş kalırsa o provider pasif olur.
> 🤖 Telegram bot token'ları (`BOT_TOKEN_PASA`, `BOT_TOKEN_KRAL`, `BOT_TOKEN_REYMEN`) gerektiğinde `.env`'ye elle eklenir — kurulum için zorunlu değil.

> **📦 Git LFS:** Repo binary dosyaları (.db, .bin, .sqlite3) Git LFS ile saklar. Clone sonrası `git lfs pull` ile çekmeyi unutma.

---

## 🎮 Kullanım

### CLI (REPL)

```bash
# Proje dizininde
python reymen_launcher.py

# Veya PATH varsa (pip install -e . sonrası)
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
R-eYMeN-/
├── reymen_launcher.py      # Ana giriş noktası
├── config.yaml             # Merkezi yapılandırma
├── .ReYMeN/                # Çalışma zamanı verileri
│   ├── SOUL.md             # Kişilik tanımı
│   ├── durum.json          # Proje durumu
│   └── session.db          # SQLite FTS5 oturum geçmişi
├── reymen/
│   ├── ag/                 # Gateway katmanı (Telegram/Discord)
│   ├── arac/               # Araç katmanı (37 dosya, 100+ araç)
│   ├── cereyan/            # Ana işlem katmanı
│   │   ├── beyin.py        # LLM bağlantı katmanı
│   │   ├── motor.py        # Eylem motoru
│   │   └── conversation_loop.py  # Konuşma döngüsü
│   ├── core/               # Çekirdek modüller
│   ├── guvenlik/           # Güvenlik katmanı (20 dosya)
│   ├── hafiza/             # Hafıza katmanı (21 dosya)
│   └── sistem/             # Sistem yönetimi
└── tests/                  # Test dosyaları
```

### Modül Detayları

| Dosya | Ne İşe Yarar | Bağlantıları (import eden/edilen) | Bozulursa |
|:------|:-------------|:----------------------------------|:----------|
| `reymen_launcher.py` | **Giriş noktası.** REPL, one-shot (-z), bot/gateway/web başlatma, CLI argüman yönetimi. | → `beyin.py`, `motor.py`, `conversation_loop.py`, `cli_commands.py`, `telegram_bot.py` | Hiçbir şey çalışmaz — CLI, bot, web UI tamamen ölür |
| `beyin.py` | **LLM bağlantı katmanı.** 12+ provider'a API çağrısı, model rotasyonu, failover, token sayma, streaming. | **Import eder:** `hata_siniflandirici.py`, `gemini_cloudcode_adapter.py`, `budget_config.py`<br>**Import eden:** `motor.py`, `conversation_loop.py`, `telegram_bot.py`, `alt_ajan.py`, `launcher.py` (5+ modül) | Hiçbir LLM çağrısı çalışmaz — tüm AI yanıtları ölür |
| `motor.py` | **Eylem motoru.** Araç çağırma, terminal çalıştırma, plugin yönetimi, hata cozucu, self-heal, sandbox. | **Import eder:** `guvenlik/`, `hafiza/`, `core/`, `cereyan/`, `arac/` (20+ modül)<br>**Import eden:** `conversation_loop.py`, `launcher.py` | Araç çağırma, terminal, web, dosya işlemleri durur |
| `conversation_loop.py` | **Konuşma döngüsü.** Kullanıcı mesajı → beyin → motor → sonuç döngüsü, skill aktivasyonu, delegasyon, MCP. | **Import eder:** `skill_activator.py`, `session_db.py`, `once_hafiza.py`, `delegasyon.py`, `mcp_tool.py`, `hata_cozucu.py` (25+ modül)<br>**Import eden:** `launcher.py` | Tüm sohbet oturumları, skill kullanımı, MCP bağlantıları ölür |
| `reymen/ag/` (21 dosya) | **Gateway katmanı.** Telegram bot (3 bot), Discord, provider routing, gateway yönetimi, delegasyon. | `telegram_bot.py` → `beyin.py`, `ortak_komutlar.py`<br>`model_provider_router.py` → `config.yaml`<br>`delegasyon.py` → async görev dağıtımı | Botlar çalışmaz, gateway bağlantıları kopar, provider routing bozulur |
| `reymen/arac/` (37 dosya) | **Araç katmanı.** Web arama, dosya analiz, tarayıcı, görsel/video/ses işleme, kanban, MCP, skill utils. | `tool_registry.py` → tüm araçları kaydeder<br>`tool_executor.py` → araçları çalıştırır<br>Her araç dosyası bağımsızdır | Araç çağırma durur — terminal, web, dosya işlemleri çalışmaz |
| `reymen/guvenlik/` (20 dosya) | **Güvenlik katmanı.** File safety, path security, PII redaction, guardrails, sandbox, OAuth. | `motor.py` → `file_safety.py`, `path_security.py`, `redact.py`, `guvenli_sandbox.py` | Zararlı kod çalışabilir, PII sızabilir, dosya erişim kontrolleri atlanabilir |
| `reymen/hafiza/` (21 dosya) | **Hafıza katmanı.** Vektör bellek, FTS5 session DB, context compression, once_hafiza, semantic cache. | `conversation_loop.py` → `session_db.py`, `context_compressor.py`<br>`motor.py` → `vektor_bellek.py`, `vektorel_hafiza.py` | Hafıza çalışmaz, her konuşma sıfırdan başlar, öğrenme döngüsü durur |
| `config.yaml` | **Merkezi yapılandırma.** Provider listesi, model haritası, plugin ayarları, MCP sunucuları. | `model_provider_router.py` okur<br>`cli_commands.py` okur<br>`beyin.py` dolaylı okur | Provider/MCP ayarları okunamaz, yanlış provider seçilir |
| `.env` | **API anahtarları.** DeepSeek, OpenAI, Anthropic, bot token'ları. | `telegram_bot.py`, `beyin.py`, `ai_bot_launcher.py` okur | API çağrıları yetkilendirme hatası alır, botlar bağlanamaz |
| `kurulum.bat` | **Windows kurulum scripti.** 7 adım: Windows/Python/Git/Node.js/FFmpeg kontrolü → repo klon → venv → paket kurulumu → .env oluşturma. | `pip install -e .`, `pyproject.toml`, `.env.example` | Elle kurulum yapmak gerekir |
| `install.sh` | **Linux/macOS kurulum scripti.** Python/Git kontrolü → venv → paket kurulumu → .env oluşturma. | `pip install -e .`, `pyproject.toml` | Elle kurulum yapmak gerekir |

### Kısa Özet — Diğer Klasörler

| Klasör | Açıklama |
|:-------|:---------|
| `alembic/` | Veritabanı migrasyon versiyonlaması |
| `telegram_bot/` | Bağımsız bot modülleri (ai_bot.py, bot.py, memory_agent.py) |
| `plugins/` | Harici plugin'ler (browser, image_gen, memory, model-providers, web, vs.) |
| `scripts/` | Yardımcı scriptler (install-hooks, durum_guncelle, vs.) |
| `skills/` | Skill aktivasyon ve yönetim altyapısı |
| `skins/` | Web UI tema dosyaları |
| `vektor_hafizasi/` | Çalışma zamanı vektör indeksleri (git'te yok) |
| `tests/` | pytest test dosyaları |
| `.github/` | CI/CD workflow'ları, GitHub issue template'leri |

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

- [x] Çoklu LLM provider (12+)
- [x] 100+ araç
- [x] Telegram bot (çoklu: Pasa_38, Kiral38, ReYMeNbot)
- [x] Web UI (FastAPI + HTMX)
- [x] Kapalı öğrenme döngüsü
- [x] Kanban board (WIP limit, deadline)
- [x] Hata→çözüm hafızası (OnceHafıza)
- [x] Cost tracking (SQLite)
- [x] Hook sistemi (8 olay tipi)
- [x] Pre-commit pull uyarısı
- [ ] Çoklu agent orchestration
- [ ] WhatsApp entegrasyonu
- [ ] Dağıtık A2A (Agent-to-Agent)
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

## 💬 İletişim

Telegram: [@ReymenSohbetbot](https://t.me/ReymenSohbetbot) — bot üzerinden mesaj gönderin.

> Proje tek geliştirici tarafından yürütülüyor. Yanıt süresi birkaç saat ile bir gün arasında değişebilir. Sabrınız için teşekkürler 🙏
