---
name: hermes-approval-policy
title: "Hermes Approval Policy"
tags: [config, hermes]
description: "Configure Hermes Agent approval and auto-approve settings for autonomous operation. Use when user wants to eliminate interactive approval prompts, enable subagent auto-approval, or adjust destructive-command confirmation behavior."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, approvals, autonomous, config, workflow]
audience: user
related_skills: [hermes-agent, windows-automation]


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | "Configure Hermes Agent approval and auto-approve settings for autonomous operation. Use when user wants to eliminate interactive approval prompts, enable subagent auto-approval, or adjust destructive |
| **Nerede** | `autonomous-ai-agents\hermes-agent_hermes-approval-policy.md` |
| **Ne Zaman** | Ilgili gorev gerektiginde |
| **Neden** | Hermes Agent Hermes Approval Policy islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Configure Hermes Agent approval and auto-approve settings for autonomous operation. Use when user wants to eliminate interactive approval prompts, enable subagent auto-approval, or adjust destructive-command confirmation behavior. |
| **Nerede?** | autonomous-ai-agents/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: Otonom ajan gelistiricisi
Ne: "Configure Hermes Agent approval and auto-approve settings for autonomous operation. Use when user wants to eliminate interactive approval prompts, enable subagent auto-approval, or adjust destructive
Nerede: `autonomous-ai-agents\hermes-agent_hermes-approval-policy.md`
Ne Zaman: Ilgili gorev gerektiginde
Neden: Hermes Agent Hermes Approval Policy islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Hermes Approval Policy

Configure how Hermes Agent handles command and tool approvals. Use this skill when the user wants fully autonomous operation (no approval prompts), selective auto-approval, or to restore interactive safeguards.

## Trigger

- User says "tüm onayları otomatik yap", "onay sorma", "otonom mod", "approvals off", "no prompts", or equivalent.
- User asks to enable/disable auto-approval for subagents, cron jobs, MCP reloads, or slash commands.
- User wants to change `approvals.mode`, `delegation.subagent_auto_approve`, or related approval settings.

## Class-Level Settings

| Setting | Values | Meaning |
|---------|--------|---------|
| `approvals.mode` | `manual` / `smart` / `off` | `off` = no prompts |
| `approvals.timeout` | seconds | 0 = no timeout wait |
| `approvals.cron_mode` | `deny` / `auto` | `auto` = cron runs without prompting |
| `approvals.mcp_reload_confirm` | true / false | false = no MCP reload confirm |
| `approvals.destructive_slash_confirm` | true / false | false = no destructive slash confirm |
| `delegation.subagent_auto_approve` | true / false | true = subagents auto-approve |

## Fully Autonomous Preset

The following sequence puts Hermes into fully autonomous mode. Run each `hermes config set` separately or as a chain; all edits are idempotent.

```bash
hermes config set approvals.mode off
hermes config set approvals.timeout 0
hermes config set delegation.subagent_auto_approve true
hermes config set approvals.cron_mode auto
hermes config set approvals.mcp_reload_confirm false
hermes config set approvals.destructive_slash_confirm false
```

## Windows Pitfall

On Windows bash (git-bash), backslash-quoted paths can be stripped or mis-parsed. Use the **full hermes executable path** in that shell:

```bash
/c/Users/marko/AppData/Local/hermes/hermes-agent/venv/Scripts/hermes.exe config set approvals.mode off
```

Do not rely on `python -m hermes_cli`; `hermes_cli` is a package, not a module.

## Verify

After changing settings, confirm with:

```bash
hermes config get approvals.mode
hermes config get delegation.subagent_auto_approve
```

Changes require a fresh session (`/reset` or restart) to take effect.

## Restore Interactive Mode

To re-enable prompts:

```bash
hermes config set approvals.mode manual
hermes config set approvals.timeout 60
hermes config set delegation.subagent_auto_approve false
hermes config set approvals.cron_mode deny
hermes config set approvals.mcp_reload_confirm true
hermes config set approvals.destructive_slash_confirm true
```