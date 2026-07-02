# ReYMeN

> **A Self-Healing, Multi-Bot Agent Framework with Native Reasoning Core**
>
> Manage 3 bots asynchronously from a single center (`durum.json`), with MCP support,
> plugin system, container sandbox, and closed-loop learning. MIT licensed.

**694 Python files, 231K lines of code, single developer. MIT license.**

---

## 🔥 ReYMeN vs The World

| Feature | ReYMeN | LangGraph | CrewAI | OpenAI SDK |
|---------|:------:|:---------:|:------:|:----------:|
| Own Reasoning Core | ✅ **Ornith-1.0** | ❌ | ❌ | ❌ |
| Multi-Bot Single Center | ✅ **3 shared bots** | ❌ | ❌ | ❌ |
| Plugin System (7 hooks) | ✅ | ❌ | ❌ | ❌ |
| MCP Server (self-hosted) | ✅ | ❌ | ❌ | ❌ |
| Discord + Telegram Gateway | ✅ | ❌ | ❌ | ❌ |
| Container Sandbox | ✅ | ❌ | ❌ | ❌ |
| Proactive Maintenance (8 checks) | ✅ **UNIQUE** | ❌ | ❌ | ❌ |
| Provider Abstraction | ✅ 5+ providers | ✅ | ✅ | ✅ |
| Platform Count | 17+ (TG/Discord/WA/Slack/Teams...) | ❌ | ❌ | ❌ |

---

## 🚀 Quickstart (1 Minute)

```bash
# 1. Clone
git clone https://github.com/recaiozil-wq/reymen-agent.git
cd reymen-agent

# 2. Virtual environment
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e .

# 3. Add your API key
cp .env.example .env
# Set DEEPSEEK_API_KEY or OPENAI_API_KEY in .env

# 4. Run
python -c "from src.reymen.cereyan.beyin import Beyin; b = Beyin({'model':{'provider':'deepseek','model':'deepseek-v4-flash'}}); print(b.dusun('Merhaba!'))"
```

Or with Docker:
```bash
docker compose up
```

---

## 📂 Directory Structure

```
src/
├── reymen/          # Framework core
│   ├── cereyan/     # Brain, Motor, Conversation Loop
│   ├── arac/        # Tools (50+)
│   ├── plugin/      # PluginBase + PluginManager
│   ├── plugins/     # User plugins
│   ├── hafiza/      # Session DB, OnceHafiza, Vector Memory
│   ├── guvenlik/    # Container Sandbox, File Safety
│   └── sistem/      # Credential Persistence, DB Config
├── gateways/        # Platform integrations
│   ├── discord_bot.py
│   ├── telegram_bot.py
│   ├── mcp_server.py
│   └── platforms/   # 17+ platform adapters
├── core/            # Reasoning Core, Credential Pool
│   ├── observability.py
│   ├── credential_pool.py
│   └── provider_abstraction.py
examples/            # 4 usage scenarios
tests/               # 112 test files
```

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🧠 **Reasoning Core** | Ornith-1.0: error → DURUM_OKU() → solution → analytics.db. Closed learning loop |
| 👥 **3 Bots, One Center** | pasa_38, ReYMeN, kiral38 share config/memory/sessions. `durum.json` SINGLE SOURCE |
| 🧩 **Plugin System** | 7 lifecycle hooks: on_load, on_message, pre_llm_call, post_llm_call, on_session_start/end, on_unload |
| 🔗 **MCP Server** | Self-hosted MCP: 6 tools (list_sessions, send_message, search_sessions...) |
| 🔑 **Provider Abstraction** | 5+ providers: DeepSeek, OpenAI, Anthropic, xAI, OpenRouter. Switch in one line |
| ✅ **Pydantic Validation** | Type-safe tool calls, auto JSON fix |
| 📊 **OpenTelemetry** | LLM/tool/session spans, token/cost/latency tracking |
| 🐳 **Container Sandbox** | Docker isolation (off/partial/full). Secure code execution |
| 📎 **@file/@url Reference** | Inline reading via `@file:config.yaml` or `@url:https://...` |
| 🔊 **Voice Mode** | Real-time voice conversation (TTS + STT) |
| 🩺 **Proactive Maintenance** | 8 checks: config drift, watchdog, SOUL sync, state.db prune, weekly report |
| 🔄 **Auto Startup** | 3 bots start headlessly on reboot (VBS) |
| 🌐 **17+ Platforms** | Telegram, Discord, WhatsApp, Slack, Teams, Matrix, Signal, Mattermost, DingTalk, Feishu, WeCom, Google Chat, Home Assistant, BlueBubbles, QQ Bot, Yuanbao, and more |

---

## 🎯 Usage Examples

```bash
# Example 1: Hello ReYMeN
python examples/00_merhaba_reymen.py

# Example 2: Write a plugin
python examples/01_plugin_kullanimi.py

# Example 3: Start MCP Server
python -c "from src.gateways.mcp_server import main; main()"

# Example 4: Container Sandbox
python examples/03_container_sandbox.py
```

---

## 🛠 Developer

Single developer: **Marko (Pasa_38)** — [@Pasa_38_bot](https://t.me/Pasa_38_bot)

---

## 📜 License

MIT License — use, modify, distribute freely.
