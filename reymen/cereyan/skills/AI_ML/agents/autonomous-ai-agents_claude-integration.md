---
name: claude-integration
title: "Claude Code - Hermes Integration"
description: "Expose Claude Code integration and MCP server to Hermes and Obsidian"
tags: [integration, claude, mcp]
version: 1.0.0
author: hermes-agent


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | "Expose Claude Code integration and MCP server to Hermes and Obsidian" |
| **Nerede** | `autonomous-ai-agents\autonomous-ai-agents_claude-integration.md` |
| **Ne Zaman** | Ilgili gorev gerektiginde |
| **Neden** | Autonomous Ai Agents Claude Integration islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Expose Claude Code integration and MCP server to Hermes and Obsidian |
| **Nerede?** | autonomous-ai-agents/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: Otonom ajan gelistiricisi
Ne: "Expose Claude Code integration and MCP server to Hermes and Obsidian"
Nerede: `autonomous-ai-agents\autonomous-ai-agents_claude-integration.md`
Ne Zaman: Ilgili gorev gerektiginde
Neden: Autonomous Ai Agents Claude Integration islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Claude Code - Hermes Integration

## Amaç

Claude Code'in Hermes skill kütüphanesine ve Obsidian vault'a erişmesini sağlayan entegrasyon.

## Adımlar

### 1. Workspace Junctions

```bash
# Hermes skills'e junction oluştur
mklink /J docs/hermes-skills "C:\Users\marko\AppData\Local\hermes\skills"

# Obsidian vault'a junction oluştur
mklink /J docs/obsidian-vault "C:\Users\marko\OneDrive\Belgeler\Obsidian Vault"
```

### 2. VS Code Yapılandırması

`.vscode/.instructions.md` ve `.vscode/pre_prompt.md` dosyalarını workspace'e yerleştir.

### 3. MCP Server

```bash
python -m venv mcp_server/.venv
.\.venv\Scripts\Activate.ps1
pip install -r mcp_server/requirements.txt
python mcp_server/app.py
```

Server `http://127.0.0.1:7070` adresinde çalışır.

### 4. Kullanım

- `/search` endpoint: skill/not araması
- `/note` endpoint: belirli notu getir

## Referanslar

- Obsidian: `Hermes Memories/2026-06-11 Claude integration.md`
- Bu skill otomatik dönüştürülmüştür (standalone .md → SKILL.md)

## Pitfall'lar

- Junction'lar VS Code'un "Add Folder to Workspace" ile aynı değildir — her workspace açılışında otomatik bağlanmaz
- MCP server Windows'ta çalıştırılmalıdır (WSL'den farklı port)
