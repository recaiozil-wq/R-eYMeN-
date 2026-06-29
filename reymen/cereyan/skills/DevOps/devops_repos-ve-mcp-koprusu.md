
> **Kategori:** devops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Devops_Repos Ve Mcp Koprusu |
| **Nerede?** | devops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: repos-ve-mcp-koprusu
description: Hermes-Obsidian MCP bridge kurulumu ve 6 yeni GitHub reposu. obsidian-pkm MCP server config, repo klonlama ve yapılandırma adımları.
title: "Repos Ve MCP Koprusu"
version: 1.0.0
author: hermes
platforms: [windows]

audience: maintainer
tags: [automation, devops, system]
category: devops---

# Repolar ve Obsidian MCP Köprüsü

## 6 Repo Kurulumu

```bash
cd /c/Users/marko/repos
git clone https://github.com/sigoden/llm-functions.git
git clone https://github.com/techgniouss/pdagent.git
git clone https://github.com/hoangsonww/AI-News-Briefing.git
git clone https://github.com/benmaster82/writher.git
```

Obsidian pluginleri:
```bash
cd "/c/Users/marko/OneDrive/Belgeler/Obsidian Vault/.obsidian/plugins"
git clone https://github.com/takeshy/obsidian-llm-hub.git
git clone https://github.com/AdrianV101/obsidian-pkm-plugin.git
```

## Obsidian MCP Server (Hermes <-> Obsidian)

**Paket:** `obsidian-pkm` (npm) - 20 MCP tool
**Config yolu:** `C:\Users\marko\AppData\Local\hermes\config.yaml`

### Config ekle

```python
import yaml
with open(r'C:\Users\marko\AppData\Local\hermes\config.yaml', 'r') as f:
    config = yaml.safe_load(f)

config['mcp_servers']['obsidian'] = {
    'command': 'npx',
    'args': ['-y', 'obsidian-pkm'],
    'env': {
        'VAULT_PATH': r'C:\Users\marko\OneDrive\Belgeler\Obsidian Vault',
        'VAULT_PKM_VAULT_NAME': 'Obsidian Vault'
    }
}

with open(r'C:\Users\marko\AppData\Local\hermes\config.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
```

### Doğrulama
```bash
npx -y obsidian-pkm --version
# → obsidian-pkm v3.10.1
Sonuc: `obsidian-pkm v3.10.1`

### MCP Dogrulama
```bash
VAULT_PATH="C:/Users/marko/OneDrive/Belgeler/Obsidian Vault" npx -y obsidian-pkm doctor
# Beklenen:
#   ✓ Node.js v24.16.0 (required: >= 20)
#   ✓ VAULT_PATH dogru
#   ✓ Vault is a directory
#   ✓ better-sqlite3 loaded
#   ✓ sqlite-vec loaded
#   ⚠ templates yok (opsiyonel)
#   ⚠ OpenAI key yok (semantic search kapali)
```

### 20 MCP Tool (obsidian-pkm)
MCP baslayinca `mcp_obsidian_*` onekiyle 20 tool kullanima hazir:
- `vault_write`, `vault_search`, `vault_read`, `vault_list`
- `vault_edit`, `vault_move`, `vault_links`, `vault_tags`
- `vault_semantic_search` (OpenAI key gerektirir)
- `vault_activity` (session memory)
