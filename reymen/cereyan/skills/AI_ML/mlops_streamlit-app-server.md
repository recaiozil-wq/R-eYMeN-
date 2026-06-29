
> **Kategori:** mlops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Mlops_Streamlit App Server |
| **Nerede?** | mlops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: "streamlit-app-server"
description: "Run, configure, and serve Streamlit data apps on Windows. Covers installation, first-run bypass, port/IP settings, and background process management."
title: "Streamlit App Server"

audience: user
tags: [ai, machine-learning, mlops]
category: mlops---

# Streamlit App Server

Run Streamlit apps (`streamlit run`) on this Windows setup. Covers the full pipeline: install → first-run email bypass → serve with correct Python path → manage as background process.

## Prerequisites

- Streamlit installed in the **hermes-ai** venv (`C:\Users\marko\hermes-ai\venv\Lib\site-packages`)
- Correct Python: use full venv path, not `python` or `python3`

## Workflow

### 1. Install / verify

```bash
C:/Users/marko/hermes-ai/venv/Scripts/python.exe -m pip install streamlit
```

Verify:
```bash
C:/Users/marko/hermes-ai/venv/Scripts/python.exe -m pip show streamlit
```

### 2. Run the app

**Required flags:**
```bash
C:/Users/marko/hermes-ai/venv/Scripts/python.exe -m streamlit run app.py \
  --server.port=8501 \
  --server.headless=true
```

| Flag | Why |
|------|-----|
| `--server.headless=true` | Skips the interactive email prompt on first run. Without this, streamlit blocks waiting for stdin input. |
| `--server.port=8501` | Explicit port (default is 8501). |

**Default behaviour (secure):** Streamlit binds only to `127.0.0.1` (localhost). No external access possible unless `--server.address=0.0.0.0` is explicitly set.

### 3. Run as background process

Since streamlit runs as a long-lived server, always use `background=true` and `notify_on_complete=true`:

```bash
# Start (from hermes terminal)
cd /c/Users/marko/hermes-ai && \
  C:/Users/marko/hermes-ai/venv/Scripts/python.exe -m streamlit run app.py \
    --server.port=8501 --server.headless=true

# Verify
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501
# Expect: 200
```

### 4. Stop

```bash
# List background processes
process action=list

# Kill
process action=kill session_id=<id>
```

### 5. Access

- **Local browser:** `http://localhost:8501`
- **Same network:** `http://<your-ip>:8501` (only if `--server.address=0.0.0.0` was set)

## Pitfalls

### `--server.allowIps` does NOT exist in Streamlit 1.58.0+
Removed. Trying to use it gives: `Error: No such option '--server.allowIps'`.
If you need IP whitelisting, use a reverse proxy (nginx) or Windows Firewall rule instead.
Default localhost-only binding is sufficient for single-user apps.

### First run blocks on email prompt
Streamlit asks for an email address on first launch and waits for stdin input.
**Fix:** Always pass `--server.headless=true`. This bypasses the prompt entirely.

### Wrong Python version
Running `python -m streamlit run ...` calls the *system* python (3.11.15 or 3.14.5), NOT the venv python where streamlit is installed.
**Fix:** Always use the full venv path:
```
C:/Users/marko/hermes-ai/venv/Scripts/python.exe -m streamlit run ...
```

### Git-bash venv activation fails
`source venv/Scripts/activate` often fails silently in git-bash (exit code 127 = streamlit not found).
Even after `source`, `which streamlit` may show a broken path with literal backslash escapes.
**Fix:** Skip activation entirely — use the full venv Python path above.

### Port already in use — conflicting process detection
If port 8501 is taken, streamlit exits with address-in-use error. But the port might be occupied by a **different Streamlit app** (or any other service), not necessarily the one you just tried to start.

**Diagnose what's on the port:**
```bash
netstat -ano | grep "8501"
# Look for LISTENING line, note the PID
```

**Identify the process:**
```bash
tasklist //FI "PID eq <PID>" //FO LIST
# or for the full command line:
powershell -Command "Get-CimInstance Win32_Process -Filter 'ProcessId=<PID>' | Select-Object CommandLine"
```

If it's a leftover/stale Streamlit instance from a previous `test_app.py` or another app, kill it:
```bash
taskkill //PID <PID> //F
```

**Fix:** After clearing the port, restart your app. Or pick a different port with `--server.port=<port>`.

### Common trap: wrong port number
New users often try `localhost:8080` (the classic dev-server port) but Streamlit defaults to **8501**. If the app doesn't open at 8080, check whether it's actually running on 8501 first.

### Repos with their own venv + launcher scripts
Some GitHub repos (e.g. MoneyPrinterTurbo) ship with their own `.venv/` and a `webui.bat` / `webui.sh` wrapper instead of requiring direct `streamlit run`. These wrappers handle:
- Finding the repo's own Python/venv (not the hermes-ai venv)
- Port allocation (sometimes auto-selects 8501-8599 if 8501 is busy)
- Setting PYTHONPATH to the repo root

**To start such a repo on Windows:**
```bash
cd /c/Users/marko/path/to/repo && cmd.exe /c "webui.bat"
```
Use `terminal(background=true, notify_on_complete=true)` since streamlit is a long-lived server. Verify with `curl http://localhost:8501`.

### Process exits silently
Streamlit writes its startup log then appears to exit. Always verify with `curl http://localhost:<port>`.

## Reference map

- `references/access-control.md`: IP restriction options (or lack thereof) for Streamlit 1.58.0+
