# ReYMeN — AGENTS.md

> ReYMeN = ReYMeN AI Agent, **fully independent**.
> Requires **zero** Hermes Agent dependencies.
> Project root: `C:\Users\marko\Desktop\Reymen Proje\ReYMeN-Ajan`

---

## Entry Points

| # | File | Type | Purpose |
|---|------|------|---------|
| 1 | `reymen\bin\reymen.cmd` | `.cmd` (batch) | Main launcher. Runs `python reymen_launcher.py`. |
| 2 | `venv\Scripts\reymen.cmd` | `.cmd` (batch) | Launches via project venv. |
| 3 | `venv\Scripts\reymen.exe` | `.exe` (PyInstaller) | Direct executable. |
| 4 | `~/.local/bin/reymen.exe` | `.exe` (pip zipapp) | pip console_scripts entry point. |

All entry points run `reymen_launcher.py` directly. **No Hermes binary routing.**

---

## Independence Declaration

ReYMeN Agent **runs with zero (0) Hermes dependencies**. All infrastructure is in its own modules:

| Component | ReYMeN Module | Hermes Dependency? |
|-----------|---------------|:------------------:|
| LLM Provider / Brain | `reymen/cereyan/beyin.py` | NO |
| Conversation Loop | `reymen/cereyan/conversation_loop.py` | NO |
| Action Solver (Motor) | `reymen/cereyan/motor.py` | NO |
| Tool Registry / Executor | `reymen/arac/tool_registry.py` + `tool_executor.py` | NO |
| Session DB (SQLite FTS5) | `reymen/hafiza/session_db.py` + `reymen/core/session_db.py` | NO |
| Cron Scheduler | `reymen/core/cron_manager.py` + `reymen/sistem/cron_scheduler.py` | NO |
| Memory / OnceHafiza | `reymen/sistem/once_hafiza.py` + `reymen/hafiza/` | NO |
| Gateway (Telegram etc.) | `reymen/ag/gateway_yonetici.py` + `platform_gateways.py` | NO |
| Skill Manager | `reymen/cereyan/skill_activator.py` | NO |
| CLI / Parser | `reymen/cli/__init__.py` (build_parser) | NO |
| CLI Commands | `reymen/arac/cli_commands.py` | NO |
| Launcher | `reymen_launcher.py` | NO |
| Config | `config.yaml` | NO |

---

## Test & Verification (2026-06-30)

- **13/13 core modules** imported successfully (without Hermes)
- **Hermes import references: 0** (in tools/scripts/helpers)
- **`reymen_launcher.py -z "merhaba"`** works (live API test)
- **`reymen_launcher.py --version`** works
- `reymen/scripts/ReYMeN_tools.py` — Hermes imports cleaned
- `reymen/arac/cli_commands.py` — Hermes binary dependency removed

---

## Running

```bash
# Direct
python reymen_launcher.py

# One-shot question
python reymen_launcher.py -z "merhaba"

# REPL
reymen\bin\reymen.cmd

# Version
python reymen_launcher.py --version
```

---

## Data Locations (Independent)

| Data | Location |
|------|----------|
| Config | `ReYMeN-Ajan\config.yaml` |
| API keys | `ReYMeN-Ajan\.env` |
| Personality/SOUL.md | `ReYMeN-Ajan\SOUL.md` |
| Motor | `reymen\cereyan\conversation_loop.py` |
| Launcher | `reymen_launcher.py` |
| Main entry point | `reymen\bin\reymen.cmd` |
| PATH stub | `~/.local/bin/reymen.exe` |
| **durum.json (SINGLE SOURCE)** | `ReYMeN-Ajan\durum.json` |

---

## HARD RULE: Bot/Token → durum.json

**Mandatory rule — never violated:**

1. **Every new bot** auto-registers in `durum.json > botlar` at startup (`BotProcess._durum_guncelle()`)
2. **New token arrives**: get from BotFather → write to `reymen/.env` → restart bot → auto-registers in durum.json
3. Bots NOT registered in durum.json are **UNKNOWN**, their features cannot be determined
4. **Manual add**: add `"bot_name": { ... }` object under `durum.json > botlar`
5. This rule is confirmed in SOUL.md, telegram_bot.py, and conversation_loop.py
