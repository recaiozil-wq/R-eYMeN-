
> **Kategori:** gaming

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Gaming_Local Game Trainer Automation |
| **Nerede?** | gaming/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: local-game-trainer-automation
title: Local Game Trainer Automation
description: Author, debug, and operate single-player trainer scripts on Windows using global hotkeys, console command injection, and window focus automation. Use for trainer scripts, console injection, and game hotkey automation.

audience: user
tags: [gaming, training]
category: gaming---

# Local Game Trainer Automation

## Scope
Build and operate local trainers or automation scripts on Windows for single-player games with a developer console. Uses global hotkeys, window focus recovery, and command injection.

## Recommended Stack
- `keyboard` — global hotkeys
- `pyautogui` — key press / type / send
- `pygetwindow` — find and activate the game window
- `threading` — keep the script alive without blocking callbacks

## Pitfalls & Fixes

1. **Hotkeys not firing after script startup**
   - Cause: registration happens after a blocking menu or long init.
   - Fix: register hotkeys first; make menu optional.

2. **`pygetwindow.activate()` raises even when activation succeeds**
   - Cause: Win32 error code 0 is raised by the library.
   - Fix: wrap `activate()` in `try/except`.

3. **Commands arrive before console is open**
   - Cause: no console key, or wrong focus.
   - Fix: activate window, send console key, then send commands.

4. **F1-F9 keys unreliable as global hotkeys**
   - Cause: `suppress=True` or target app interference.
   - Fix: use `suppress=False` and re-register if needed.

5. **Broken path from `.bat` launcher**
   - Cause: relative paths in script.
   - Fix: absolute paths inside `.bat` and script.

## Canonical Pattern
```python
import time, pyautogui, threading
from keyboard import add_hotkey

TITLE = "<game window title>"
CONSOLE_KEY = '`'

def activate():
    import pygetwindow as gw
    wins = gw.getWindowsWithTitle(TITLE)
    if not wins:
        return False
    w = wins[0]
    try:
        if w.isMinimized:
            w.restore()
            time.sleep(0.2)
        w.activate()
    except Exception:
        pass
    time.sleep(0.2)
    return True

def open_console():
    pyautogui.press(CONSOLE_KEY)
    time.sleep(0.15)

def inject(cmds):
    if not activate():
        return
    open_console()
    time.sleep(0.2)
    for cmd in cmds:
        pyautogui.typewrite(cmd, interval=0.02)
        pyautogui.press('enter')
        time.sleep(0.15)
```

## Notes
- Use deterministic timing after focus change.
- If a command needs reload toggle or map change, make it a separate preset with explicit waits/steps.
