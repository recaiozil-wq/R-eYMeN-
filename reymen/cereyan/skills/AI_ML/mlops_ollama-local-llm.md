---
name: ollama-local-llm
description: Ollama local LLM workflows — model pull/run, command execution, generated-code verification, VS Code handoff, and Windows network/device enumeration fallback when model-generated system calls are unreliable on Windows.
title: "Ollama Local LLM"
version: 1.0.0
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [ollama, local-llm, windows, network-enumeration, mac-address, codegen, alpsee]
category: mlops
audience: user
tags: [ai, machine-learning, mlops]
---


> **Kategori:** mlops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ollama local LLM workflows — model pull/run, command execution, generated-code verification, VS Code handoff, and Windows network/device enumeration fallback when model-generated system calls are unreliable on Windows. |
| **Nerede?** | mlops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Ollama Local LLM

Use this skill for running and checking local Ollama models, generating runnable code with them, validating/nullifying model-generated system commands, and recovering Windows networking facts when the model falls back to unreliable cross-platform snippets.

## When to use

- `ollama pull`, `ollama run`, `ollama list` checks
- Ask a local model to write a one-shot Python/PS1 snippet and run it
- Verify generated code before trusting it
- VS Code project scaffold and launch for generated scripts
- Windows local IP / adapter MAC lookup
- ARP table / LAN device lookup when model output is wrong

## Core workflow

### 1) Verify Ollama first

```bash
ollama --version
ollama list
ollama pull <model>
ollama run <model> "prompt"
```

Prefer `ollama list` always before assuming a model name.

### 2) Treat model-generated Windows commands as suspect

Models can emit Linux-style commands that fail silently or with confusing aliases on Windows PowerShell/cmd. Bad patterns:

- `ip link show`
- `iwconfig`
- `cat /sys/class/net/*/address`
- `arp -a` filtering using awk/perl one-liners

Default to `ipconfig /all`, `getmac`, `arp -a`, or Python stdlib.

### 3) Preferred Windows network-fact script pattern

Use stdlib only. Avoid parsing console tables. Known-good targets:

- IP via `socket.gethostbyname` / `socket.getaddrinfo`
- Primary MAC via `uuid.getnode` or Windows shell with `getmac`

Example return contract:

```text
* IP ADDRESSES
192.168.0.xx

* MAC ADDRESSES
AA:BB:CC:DD:EE:FF
```

If the prompt asks for adapters/ wifi / LAN devices:

- primary machine address = `getip` + `getmac`
- LAN peers = parse `arp -a`

This is reusable enough to belong in `references/windows-network.md`.

### 4) Generated-code verification loop

1. Write file with `write_file` / `execute_code`
2. Run with `python "<path>"` from Terminal
3. Read actual output
4. If wrong, rewrite before declaring success

### 5) VS Code handoff

Typical scaffold:

```text
PROJECTS_DIR/<project_name>/
  main.py
  .vscode/launch.json
```

Create `.vscode/launch.json` before opening in VS Code with `code <path>`.

## Pitfalls

- PowerShell expands unquoted backslashes in paths; quote script paths.
- `socket.getaddrinfo(socket.gethostname(), None)` can duplicate sockets; dedupe by value.
- `uuid.getnode()` may return a valid-looking hex when the host is not on a real network; use `ipconfig` / `getmac` to cross-check.
- Avoid `arp` parsing when only local adapter info is needed; ARP is for peer LAN lookup.
- One-shot generation rarely includes correct Windows command syntax on first try.

## Verification / failure rule

Required step when model-generated code or command is questionable:
1. Run `ollama list` first
2. Write or inspect code
3. Execute with explicit Windows-safe form
4. If it fails, switch to this script / template / known-good snippet
