---
name: agent-web-ui
title: "AI Agent Web UI (FastAPI + HTMX + Tailwind)"
description: "Build a modern, dark-themed, mobile-responsive web interface for an AI agent using FastAPI, HTMX, and Tailwind CSS. Chat interface, skills browser, gateway dashboard, config panel, session history."
audience: contributor
tags: [web-ui, fastapi, htmx, tailwind, agent, dashboard, python]
version: 1.0.0
---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Build a modern, dark-themed, mobile-responsive web interface for an AI agent using FastAPI, HTMX, and Tailwind CSS. Chat interface, skills browser, gateway dashboard, config panel, session history. |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# AI Agent Web UI (FastAPI + HTMX + Tailwind)

## When to Use

Build this when your AI agent needs a **web-based interface** with:
- Chat/messaging UI to interact with the agent
- Skills/tools browser
- Gateway/service status dashboard
- Configuration panel
- Session history viewer
- Mobile-responsive design (works on phone)

## Architecture

Single-file FastAPI app (or modular if large). All HTML rendered server-side via Jinja2. HTMX handles partial page updates (no JS framework needed). Tailwind CSS via CDN for styling.

```
agent/
├── web_ui.py          ← Single FastAPI file with inline templates
├── .env               ← API keys and config (loaded by python-dotenv)
├── skills/            ← Skill .md files (listed by skills browser)
├── session.db         ← SQLite FTS5 session database (auto-created)
└── templates/         ← Optional: external template directory
```

## Key Endpoints

| Endpoint | Method | Purpose | HTMX? |
|----------|--------|---------|-------|
| `GET /` | HTML | Main chat page | — |
| `GET /skills` | HTML | Skills browser | ✅ hx-get |
| `GET /gateway` | HTML | Gateway status | ✅ hx-get |
| `GET /config` | HTML | Config panel | ✅ hx-get |
| `GET /sessions` | HTML | Session history | ✅ hx-get |
| `POST /api/chat` | JSON | Send message, get reply | ✅ |
| `POST /api/agent/run` | JSON | Run agent with goal | ✅ |
| `GET /api/skills` | JSON | Skills list | — |
| `GET /api/gateway/status` | JSON | Gateway JSON status | — |
| `POST /api/config/save` | JSON | Save .env changes | ✅ |

## Dark Theme Setup

```python
# Tailwind dark class on html tag
<html class="bg-[#1a1b2e] text-gray-100">

# Sidebar
<div class="bg-[#16172b] w-64 h-full border-r border-gray-700/50">

# Chat bubbles
user:  class="bg-[#2d3a6e] text-white rounded-2xl rounded-br-sm"
agent: class="bg-[#2a2d4a] text-gray-100 rounded-2xl rounded-bl-sm"

# Input area
class="bg-[#1e1f36] border border-gray-600/30 rounded-xl text-white"

# Accent color
#6366f1 (indigo-500) for buttons, links, active states
```

## HTMX Navigation Pattern

```python
# FastAPI route returns HTML fragment
@app.get("/skills")
async def skills_page():
    skills = read_skills_from_disk()
    return HTMLResponse(render_skills_html(skills))

# Template uses hx-get for SPA-like navigation
<a href="/skills" 
   hx-get="/skills" 
   hx-target="#main-content" 
   hx-push-url="true"
   hx-indicator="#loading-spinner">
  Yetenekler
</a>
```

## Chat Interface Pattern

Use a POST-then-GET pattern for HTMX chat:

```html
<form hx-post="/api/chat" 
      hx-target="#messages" 
      hx-swap="beforeend"
      hx-on::after-request="this.reset(); scrollToBottom()">
  <input type="text" name="message" class="..." required>
  <button type="submit">Gönder</button>
</form>
<div id="messages" hx-get="/api/messages" hx-trigger="load">
  <!-- Messages rendered here -->
</div>
```

## Mobile Responsive Pattern

```html
<!-- Hamburger button - visible only on mobile -->
<button id="sidebar-toggle" class="md:hidden fixed top-4 left-4 z-50">
  ☰
</button>

<!-- Sidebar - hidden on mobile, overlay when toggled -->
<aside id="sidebar" 
       class="fixed md:relative w-64 h-full 
              -translate-x-full md:translate-x-0 
              transition-transform duration-200 z-40">
```

## Skill Browser

Read `.md` files from `skills/` directory and parse frontmatter:

```python
import frontmatter  # or manual YAML parse
skills = []
for f in Path("skills").glob("*.md"):
    with open(f) as fh:
        meta = next(yaml.safe_load_all(fh))  # frontmatter
        skills.append({"name": f.stem, "title": meta.get("title", f.stem), ...})
```

## .env Config Panel

- Mask sensitive values (KEY/TOKEN/SECRET) in display
- Allow inline editing with POST save
- Write back preserving comments and structure

```python
def mask_value(key, value):
    if any(kw in key.upper() for kw in ["KEY", "TOKEN", "SECRET", "PASSWORD"]):
        return value[:4] + "..." if len(value) > 8 else "***"
    return value
```

## Pitfalls

1. **Port conflicts**: Default 8080 may be in use. Support `WEB_UI_PORT` env var override. Use `socket` to test port before binding.
2. **HTMX oob-swaps**: Chat typing indicator should use `hx-swap-oob="true"` so it updates independently of the message list.
3. **Mobile sidebar**: Use CSS `translate-x` + `transition` + JS `toggle` class — not jQuery. Keep it lightweight.
4. **File watching**: If showing live logs/config, use HTMX polling (`hx-trigger="every 5s"`) not WebSocket (overkill for dashboards).
5. **Session DB**: If the session database (SQLite) doesn't exist yet, return a friendly "henüz oturum yok" message instead of crashing.
6. **API key display**: NEVER expose full keys in the config panel. Always mask tokens/keys/secrets.
7. **Template size**: Single-file inline templates work up to ~50KB. Beyond that, split into `templates/` directory.
8. **Windows paths**: Use `Path` from pathlib, not `os.path`. Avoid backslash issues.
