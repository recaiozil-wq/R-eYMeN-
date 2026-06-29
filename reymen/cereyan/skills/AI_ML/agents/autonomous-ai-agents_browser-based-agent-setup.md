
> **Kategori:** autonomous-ai-agents

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Autonomous Ai Agents_Browser Based Agent Setup |
| **Nerede?** | autonomous-ai-agents/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: browser-based-agent-setup
title: Browser-Based Agent Setup
description: >
  Configure and deploy autonomous AI agents through web platforms using browser automation.
  Use when setting up Creo AI, similar agent platforms, or any task requiring automated
  web interaction to configure an agent on a website.
triggers:
  - "set up autonomous agent on web platform"
  - "configure AI agent via browser"
  - "automate agent platform setup"
  - "Creo AI setup"
  - "web agent configuration"
  - "autonomous çalışan AI asistan kur"
  - "Creo AI ile kendi kendine çalışan asistan"

audience: user
tags: [agents, ai, automation]
category: autonomous-ai-agents---

# Browser-Based Agent Setup

## When to Use
- Setting up a web-based AI agent platform (Creo AI, similar services)
- Need to automate clicks, form fills, and navigation through a browser
- Need to maintain login state across automation sessions
- Configuring agents, connectors, schedules, and prompts automatically
- User prefers full autonomous execution over step-by-step instructions

## Prerequisites
- Playwright: `pip install playwright && playwright install chromium`
- Google Chrome installed
- Target platform URL and valid login
- Windows: Chrome user data path: `C:\Users\<user>\AppData\Local\Google\Chrome\User Data`

## Workflow

### 1. Launch Browser with Persistent Profile
Use `launch_persistent_context`, NOT `browser_type.launch` with `--user-data-dir`.
**Critical:** Close all Chrome windows first to avoid profile lock.

```python
from playwright.sync_api import sync_playwright
import time

user_data = r"C:\Users\marko\AppData\Local\Google\Chrome\User Data"
with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=user_data,
        headless=False,
        executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        args=["--profile-directory=Default", "--start-maximized"],
        viewport={"width": 1920, "height": 1080}
    )
    page = context.new_page()
```

### 2. Navigate and Assess State
- `page.goto(url, wait_until="domcontentloaded", timeout=120000)`
- `page.screenshot(path=...)` after load
- Analyze screenshot to identify UI state (login, dashboard, etc.)

### 3. Authenticate
- If login page: fill credentials and submit
- If SSO button present: click it
- Wait for dashboard elements to confirm login
- If 2FA/captcha: pause and inform user

### 4. Configure Platform (Generic Pattern)
Most platforms share this flow:
1. Connect services (Connectors / Integrations)
2. Create or select an agent/chat
3. Select model
4. Paste prompt into chat input
5. Submit and wait for agent response
6. Configure schedule/repeat
7. Test with “Run now”

**Prompt formatting:** Use clear numbered bullets. For draft-only tasks, explicitly state “do not send”.

### 5. Set Schedule
- Locate schedule/scheduler control
- Set repeat interval, time, timezone, recipient email
- Confirm submission

### 6. Test and Verify
- Use platform’s “Run now” / manual trigger
- Check outputs: emails sent, files created, social posts

### 7. Report Results
- Screenshot final state
- List completed steps vs. any manual actions still required
- Provide data handles (IDs, URLs, file paths) where applicable

## Pitfalls

### Chrome Profile Lock
- **Symptom:** `TargetClosedError` on launch
- **Cause:** Chrome is open and holding the profile
- **Fix:** Close all Chrome windows, or use a separate profile directory (`--profile-directory=Profile 1`)
- **Rule:** `launch_persistent_context` is required. Never pass `--user-data-dir` via `args` in `browser_type.launch`.

### Dynamic Content Loading
- **Problem:** UI elements appear slowly
- **Fix:** Use `wait_until` with specific selectors, not fixed sleeps
- **Fallback:** Screenshot + coordinate-based click when selectors fail

### Credential Handling
- **Never** hardcode credentials
- Load from user environment, prompt, or secure store
- Mask passwords in logs and screenshots

### Platform Variations
Each platform has different DOM structure. When selectors fail:
1. Use `get_by_role` / `get_by_text` for accessibility-first locating
2. Fall back to CSS selectors
3. Last resort: coordinate-based mouse click (if heredity allows)

## User Preferences
- Autonomous execution is preferred over explanatory instructions
- When a skill is loaded, perform the steps rather than describe them
- Report outcomes after completion; avoid pre-emptive narration
- Do not retry failed steps excessively without user consent

## See Also
- `references/creo-ai-example.md` — platform-specific notes for Creo AI
