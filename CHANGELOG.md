# Changelog

## [1.0.2] — 2026-07-01

### ✨ New Features
- 📦 **Independent Cron System** — `reymen/cron/` runs without Hermes
  - jobs.py — Cron job storage and management
  - scheduler.py — Scheduled task runner
  - cronjob_tool.py — Agent interface (cron management via Motor)
- 🌐 **Independent Gateway** — `reymen/gateway/` Telegram platform adapter
  - Telegram bot infrastructure runs Hermes-free
  - python-telegram-bot support
  - Session management, message delivery
- 🧩 **Hermes Stubs** — `hermes_stubs.py` ReYMeN adaptation of Hermes functions
  - 40+ Hermes functions reimplemented
  - Sufficient for gateway + cron + core system

### 🔧 Improvements
- `model_tools.py` + `motor.py` → Hermes imports protected with try/except
- `pyproject.toml` → cron and gateway packages added
- `.gitignore` → cron_data added
- `README.md` → Comprehensive setup and usage guide
- `requirements.txt` → All dependencies listed

### 🐛 Fixes
- cron `jobs.py` → Data directory doesn't conflict with Python package (cron_data)
- cron `cronjob_tool.py` → Hermes imports properly redirected

## [1.0.1] — 2026-06-30

### ✨ New Features
- 🔌 **Hermes Independence** — 0 Hermes import dependencies
- 🗄️ **Central Database** — 21 DBs in one center (`reymen/merkez_db/`)
  - Session DB merge (14,146 records)
  - WAL mode + busy_timeout
  - Weekly WAL checkpoint cron

### 🔧 Improvements
- `hermes_uyum.py` — Hermes CLI independence layer
- `.env.example` — All bot tokens and API keys
- MIT license file
- GitHub Actions CI (Python 3.12)
- Git LFS binary file management

## [1.0.0] — 2026-06-20

### ✨ Initial Release
- 🤖 3 Telegram Bots (Pasa_38, Kiral38, ReYMeN_ReYMeNbot)
- 🧠 OnceHafiza + vector memory + FTS5 session search
- 🔧 675+ tool support (web, terminal, file, browser)
- 📅 Cron job management
- 🖥️ CLI interface
- 🔒 Security layer
- 📚 Turkish documentation
