---
name: claude-agent
title: "Claude Agent"
tags: [agents, ai]
description: Claude Code CLI agent modunu terminalde baslatma ve kullanma
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [claude, agent, terminal, cli, coding]
audience: user
related_skills: [powershell-claude-agent, codex, opencode]


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Claude Code CLI agent modunu terminalde baslatma ve kullanma |
| **Nerede** | `autonomous-ai-agents\autonomous-ai-agents_claude-agent.md` |
| **Ne Zaman** | Ilgili gorev gerektiginde |
| **Neden** | Autonomous Ai Agents Claude Agent islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Claude Code CLI agent modunu terminalde baslatma ve kullanma |
| **Nerede?** | autonomous-ai-agents/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: Otonom ajan gelistiricisi
Ne: Claude Code CLI agent modunu terminalde baslatma ve kullanma
Nerede: `autonomous-ai-agents\autonomous-ai-agents_claude-agent.md`
Ne Zaman: Ilgili gorev gerektiginde
Neden: Autonomous Ai Agents Claude Agent islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Claude Agent

Claude Code CLI (`claude`) agent modunda çalıştırma.

## Komut

```cmd
echo. | claude
```

- Not: `cmd /k` ile çalışır, PowerShell değil
- Windows'ta cmd.exe üzerinden çalıştırılmalı

## Kullanım

1. `cmd` (Command Prompt) aç
2. `echo. | claude` yaz → agent moduna geçer
3. Claude ile etkileşimli kodlama oturumu başlar

## Alternatif (PowerShell)

```powershell
echo "" | claude
```
