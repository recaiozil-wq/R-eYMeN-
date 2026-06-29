---
name: gece-3-github-yedek
title: "GitHub Yedekleme"
tags: [automation, devops, git, system, backup, github, memory]
description: >-
  Hermes Agent yedekleme: memory (MEMORY.md + USER.md), skills, config, state.db
  GitHub'a yedeklenir. İki yöntem: (1) gh CLI ile basit memory yedek, (2) full
  backup scripti ile skills+state.db+memory.
version: 3.0.0
author: marko
license: MIT
audience: maintainer
related_skills:
  - github-auth
  - obsidian-vault-kurallari
  - tam-sistem-yetkisi
---


> **Kategori:** devops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | >- |
| **Nerede?** | devops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# GitHub Yedekleme

## Yöntem 1 — Sadece Memory (Basit, Hızlı)

Memory dosyalarını (MEMORY.md + USER.md) GitHub'a yedeklemek için:

```bash
# 1. Token'ları temizle ve geçici dizine kopyala
python3 -c "
import re, shutil, os
src = r'C:\\Users\\marko\\AppData\\Local\\hermes\\memories'
dst = r'C:\\Users\\marko\\AppData\\Local\\Temp\\hermes-memory-temp'
if os.path.exists(dst): shutil.rmtree(dst)
os.makedirs(dst)
for fname in ['MEMORY.md', 'USER.md']:
    with open(os.path.join(src, fname), 'r', encoding='utf-8') as f:
        content = f.read()
    content = re.sub(r'ghp_[A-Za-z0-9]+', '[GIZLI-TOKEN]', content)
    content = re.sub(r'github_pat_[A-Za-z0-9_]+', '[GIZLI-TOKEN]', content)
    content = re.sub(r'sk-[A-Za-z0-9\-]+', '[GIZLI-TOKEN]', content)
    with open(os.path.join(dst, fname), 'w', encoding='utf-8') as f:
        f.write(content)
"

# 2. Repo oluştur ve push et (tek seferde)
cd /c/Users/marko/AppData/Local/Temp/hermes-memory-temp
git init
git add -A
git commit -m "Memory backup $(date +%Y-%m-%d)"
gh repo create hermes-memory-backup --private --push --source .
```

**Not:** `gh` CLI (keyring auth) her zaman HTTPS+PAT'den önce dene. MCP GitHub tool'ları her zaman çalışmayabilir.

## Yöntem 2 — Full Backup (Skills + Memory + state.db)

Script: `scripts/sync_hermes_backup.py`

Kapsam:
- Skills dizini (`.bundled_manifest`, `__pycache__` hariç)
- Memory (MEMORY.md + USER.md)
- state.db (55MB chunk'lara bölünmüş zip)

```bash
python3 scripts/sync_hermes_backup.py
```

Cron için `no_agent=true` modu önerilir (LLM harcamaz).

## Auth Stratejileri (Öncelik Sırası)

1. **gh CLI** (keyring OAuth) — en güvenilir, önce dene
2. **HTTPS + PAT** — `.env`'deki GITHUB_TOKEN ile
3. **MCP GitHub** — sadece basit dosya işlemleri için, repo oluşturmada başarısız olabilir

### gh CLI Kontrol
```bash
gh auth status
# ✓ Logged in to github.com account asdafgf (keyring)
```

## Hedef Repolar

| Repo | Açıklama | Oluşturuldu |
|------|----------|-------------|
| `Watcher-Hermes/hermes-memory-backup` | Memory yedeği (MEMORY.md + USER.md) | ✅ 14 Haz 2026 |
| `Watcher-Hermes/hermes-full-backup` | Skills + memory + state.db | Geçmişte oluşturuldu |

## Obsidian Vault Yedekleme

Obsidian vault zaten GitHub'a bağlıdır (kendi git repo'su). Ayrıca yedeklemeye gerek yoktur. Vault içindeki değişiklikler otomatik git history'de kalır.

## Pitfall'lar

1. **Token sızıntısı** — Memory'de GITHUB_TOKEN/PAT varsa, push öncesi `re.sub` ile temizle
2. **gh CLI yoksa** — `gh` kurulu değilse `GITHUB_TOKEN` ile HTTPS+PAT dene
3. **state.db kilitli** — Hermes açıkken state.db okunamayabilir; WAL modunda retry gerekebilir
4. **Eymen2016 çakışması** — Git credential helper'da eski hesap varsa `git config --unset credential.helper` ile temizle
5. **Large file** — state.db 100MB+ ise GitHub 50MB limitine takılma; chunk'la veya Git LFS kullan
6. **Repo yoksa** — `gh repo create` ile oluştur, `mcp_github_create_repository` her zaman auth vermeyebilir
