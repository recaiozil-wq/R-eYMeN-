1|# ReYMeN
2|
3|> **A Self-Healing, Multi-Bot Agent Framework with Native Reasoning Core**
4|>
5|> Manage 3 bots asynchronously from a single center (`durum.json`), with MCP support,
6|> plugin system, container sandbox, and closed-loop learning. MIT licensed.
7|
8|**694 Python files, 231K lines of code, single developer. MIT license.**
9|
10|---
11|
12|## 🔥 ReYMeN vs The World
13|
14|| Feature | ReYMeN | LangGraph | CrewAI | OpenAI SDK |
15||---------|:------:|:---------:|:------:|:----------:|
16|| Own Reasoning Core | ✅ **Ornith-1.0** | ❌ | ❌ | ❌ |
17|| Multi-Bot Single Center | ✅ **3 shared bots** | ❌ | ❌ | ❌ |
18|| Plugin System (7 hooks) | ✅ | ❌ | ❌ | ❌ |
19|| MCP Server (self-hosted) | ✅ | ❌ | ❌ | ❌ |
20|| Discord + Telegram Gateway | ✅ | ❌ | ❌ | ❌ |
21|| Container Sandbox | ✅ | ❌ | ❌ | ❌ |
22|| Proactive Maintenance (8 checks) | ✅ **UNIQUE** | ❌ | ❌ | ❌ |
23|| Provider Abstraction | ✅ 5+ providers | ✅ | ✅ | ✅ |
24|| Platform Count | 17+ (TG/Discord/WA/Slack/Teams...) | ❌ | ❌ | ❌ |
25|
26|---
27|
28|## 🚀 Quickstart (1 Minute)
29|
30|```bash
31|# 1. Clone
32|git clone https://github.com/recaiozil-wq/reymen-agent.git
33|cd reymen-agent
34|
35|# 2. Virtual environment
36|uv venv
37|source .venv/bin/activate  # Windows: .venv\Scripts\activate
38|uv pip install -e .
39|
40|# 3. Add your API key
41|cp .env.example .env
42|# Set DEEPSEEK_API_KEY or OPENAI_API_KEY in .env
43|
44|# 4. Run
45|python -c "from src.reymen.cereyan.beyin import Beyin; b = Beyin({'model':{'provider':'deepseek','model':'deepseek-v4-flash'}}); print(b.dusun('Merhaba!'))"
46|```
47|
48|Or with Docker:
49|```bash
50|docker compose up
51|```
52|
53|---
54|
55|

---

## 🏆 Hermes→ReYMeN — %100 Özellik Uyumu (2026-07-02)

| # | Özellik | Durum |
|---|---------|:-----:|
| 1 | **Self-update** — `reymen update --check/--auto` | ✅ |
| 2 | **Session Search** — FTS5 tam metin arama + otomatik kayıt | ✅ |
| 3 | **Sub-agent Delegasyonu** — ThreadPoolExecutor ile paralel görev | ✅ |
| 4 | **HyperFrames Video** — HTML→Playwright→FFmpeg pipeline | ✅ |
| 5 | **Memory Compaction** — 50K limit, otomatik arşiv, LRU cache temizleme | ✅ |
| 6 | **Skill Shrink** — 10KB+ skill tespit + references/ yönlendirme | ✅ |
| 7 | **Obsidian Entegrasyonu** — 6 tool (liste/oku/yaz/güncelle/ara/bilgi) | ✅ |
| 8 | **Setup Wizard** — `reymen setup --check/--fix/--auto` (8 aşamalı) | ✅ |
| 9 | **Nightly Self-Improvement** — 6 aşamalı, her gece 03:00 | ✅ |
| 10 | **Auth Sistemi** — JWT token + multi-user + API key doğrulama | ✅ |
| 11 | **Web UI Image Gen** — GET/POST /image-gen, 5 provider | ✅ |
| 12 | **Framework Adaptörleri** — LangGraph/CrewAI/AutoGen (opsiyonel) | ✅ |
| 13 | **A2A/ACP Protokolleri** — Agent Card + Skill Transfer + Task Delegation | ✅ |
| 14 | **Rules Engine** — 5 kategori, 6 built-in kural, her aksiyon kontrolü | ✅ |
| 15 | **Hermes Skills** — 8 yeni Hermes skill'i aktarıldı (531 toplam) | ✅ |


## 📂 Directory Structure
56|
57|```
58|src/
59|├── reymen/          # Framework core
60|│   ├── cereyan/     # Brain, Motor, Conversation Loop
61|│   ├── arac/        # Tools (50+)
62|│   ├── plugin/      # PluginBase + PluginManager
63|│   ├── plugins/     # User plugins
64|│   ├── hafiza/      # Session DB, OnceHafiza, Vector Memory
65|│   ├── guvenlik/    # Container Sandbox, File Safety
66|│   └── sistem/      # Credential Persistence, DB Config
67|├── gateways/        # Platform integrations
68|│   ├── discord_bot.py
69|│   ├── telegram_bot.py
70|│   ├── mcp_server.py
71|│   └── platforms/   # 17+ platform adapters
72|├── core/            # Reasoning Core, Credential Pool
73|│   ├── observability.py
74|│   ├── credential_pool.py
75|│   └── provider_abstraction.py
76|examples/            # 4 usage scenarios
77|tests/               # 112 test files
78|```
79|
80|---
81|
82|## ✨ Key Features
83|
84|| Feature | Description |
85||---------|-------------|
86|| 🧠 **Reasoning Core** | Ornith-1.0: error → DURUM_OKU() → solution → analytics.db. Closed learning loop |
87|| 👥 **3 Bots, One Center** | pasa_38, ReYMeN, kiral38 share config/memory/sessions. `durum.json` SINGLE SOURCE |
88|| 🧩 **Plugin System** | 7 lifecycle hooks: on_load, on_message, pre_llm_call, post_llm_call, on_session_start/end, on_unload |
89|| 🔗 **MCP Server** | Self-hosted MCP: 6 tools (list_sessions, send_message, search_sessions...) |
90|| 🔑 **Provider Abstraction** | 5+ providers: DeepSeek, OpenAI, Anthropic, xAI, OpenRouter. Switch in one line |
91|| ✅ **Pydantic Validation** | Type-safe tool calls, auto JSON fix |
92|| 📊 **OpenTelemetry** | LLM/tool/session spans, token/cost/latency tracking |
93|| 🐳 **Container Sandbox** | Docker isolation (off/partial/full). Secure code execution |
94|| 📎 **@file/@url Reference** | Inline reading via `@file:config.yaml` or `@url:https://...` |
95|| 🔊 **Voice Mode** | Real-time voice conversation (TTS + STT) |
96|| 🩺 **Proactive Maintenance** | 8 checks: config drift, watchdog, SOUL sync, state.db prune, weekly report |
97|| 🔄 **Auto Startup** | 3 bots start headlessly on reboot (VBS) |
98|| 🌐 **17+ Platforms** | Telegram, Discord, WhatsApp, Slack, Teams, Matrix, Signal, Mattermost, DingTalk, Feishu, WeCom, Google Chat, Home Assistant, BlueBubbles, QQ Bot, Yuanbao, and more |
99|
100|---
101|
102|## 🎯 Usage Examples
103|
104|```bash
105|# Example 1: Hello ReYMeN
106|python examples/00_merhaba_reymen.py
107|
108|# Example 2: Write a plugin
109|python examples/01_plugin_kullanimi.py
110|
111|# Example 3: Start MCP Server
112|python -c "from src.gateways.mcp_server import main; main()"
113|
114|# Example 4: Container Sandbox
115|python examples/03_container_sandbox.py
116|```
117|
118|---
119|
120|## 🛠 Developer
121|
122|Single developer: **Marko (Pasa_38)** — [@Pasa_38_bot](https://t.me/Pasa_38_bot)
123|
124|---
125|
126|## 📜 License
127|
128|MIT License — use, modify, distribute freely.
129|