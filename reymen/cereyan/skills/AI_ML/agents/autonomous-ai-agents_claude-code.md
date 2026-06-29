---
name: claude-code
title: "Claude Code"
tags: [agents, ai]
description: "Delegate coding to Claude Code CLI (features, PRs)."
version: 2.3.0
author: Hermes Agent + Teknium
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Coding-Agent, Claude, Anthropic, Code-Review, Refactoring, PTY, Automation]
audience: user
related_skills: [codex, hermes-agent, opencode]


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | "Delegate coding to Claude Code CLI (features, PRs)." |
| **Nerede** | `autonomous-ai-agents\autonomous-ai-agents_claude-code.md` |
| **Ne Zaman** | Ilgili gorev gerektiginde |
| **Neden** | Autonomous Ai Agents Claude Code islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Delegate coding to Claude Code CLI (features, PRs). |
| **Nerede?** | autonomous-ai-agents/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: Otonom ajan gelistiricisi
Ne: "Delegate coding to Claude Code CLI (features, PRs)."
Nerede: `autonomous-ai-agents\autonomous-ai-agents_claude-code.md`
Ne Zaman: Ilgili gorev gerektiginde
Neden: Autonomous Ai Agents Claude Code islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Claude Code

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Claude Code — Hermes Orchestration Guide | `references/claude-code-hermes-orchestration-guide.md` |
| Prerequisites | `references/prerequisites.md` |
| Two Orchestration Modes | `references/two-orchestration-modes.md` |
| Start a tmux session | `references/start-a-tmux-session.md` |
| Launch Claude Code inside it | `references/launch-claude-code-inside-it.md` |
| (after ~3-5 seconds for the welcome screen) | `references/after-3-5-seconds-for-the-welcome-screen.md` |
| Monitor progress by capturing the pane | `references/monitor-progress-by-capturing-the-pane.md` |
| Send follow-up tasks | `references/send-follow-up-tasks.md` |
| Exit when done | `references/exit-when-done.md` |
| PTY Dialog Handling (CRITICAL for Interactive Mode) | `references/pty-dialog-handling-critical-for-interactive-mode.md` |
| Launch with permissions bypass | `references/launch-with-permissions-bypass.md` |
| Handle trust dialog (Enter for default "Yes") | `references/handle-trust-dialog-enter-for-default-yes.md` |
| Handle permissions dialog (Down then Enter for "Yes, I accept") | `references/handle-permissions-dialog-down-then-enter-for-yes-i-accept.md` |
| Now wait for Claude to work | `references/now-wait-for-claude-to-work.md` |
| CLI Subcommands | `references/cli-subcommands.md` |
| Print Mode Deep Dive | `references/print-mode-deep-dive.md` |
| Pipe a file for analysis | `references/pipe-a-file-for-analysis.md` |
| Pipe multiple files | `references/pipe-multiple-files.md` |
| Pipe command output | `references/pipe-command-output.md` |
| Start a task | `references/start-a-task.md` |
| Resume with session ID | `references/resume-with-session-id.md` |
| Or resume the most recent session in the same directory | `references/or-resume-the-most-recent-session-in-the-same-directory.md` |
| Fork a session (new ID, keeps history) | `references/fork-a-session-new-id-keeps-history.md` |
| Complete CLI Flags Reference | `references/complete-cli-flags-reference.md` |
| Settings & Configuration | `references/settings-configuration.md` |
| Interactive Session: Slash Commands | `references/interactive-session-slash-commands.md` |
| .claude/commands/deploy.md | `references/claude-commands-deploy-md.md` |
| .claude/skills/database-migration.md | `references/claude-skills-database-migration-md.md` |
| Interactive Session: Keyboard Shortcuts | `references/interactive-session-keyboard-shortcuts.md` |
| PR Review Pattern | `references/pr-review-pattern.md` |
| Parallel Claude Instances | `references/parallel-claude-instances.md` |
| Task 1: Fix backend | `references/task-1-fix-backend.md` |
| Task 2: Write tests | `references/task-2-write-tests.md` |
| Task 3: Update docs | `references/task-3-update-docs.md` |
| Monitor all | `references/monitor-all.md` |
| CLAUDE.md — Project Context File | `references/claude-md-project-context-file.md` |
| Architecture | `references/architecture.md` |
| Key Commands | `references/key-commands.md` |
| Code Standards | `references/code-standards.md` |
| Custom Subagents | `references/custom-subagents.md` |
| .claude/agents/security-reviewer.md | `references/claude-agents-security-reviewer-md.md` |
| Hooks — Automation on Events | `references/hooks-automation-on-events.md` |
| MCP Integration | `references/mcp-integration.md` |
| GitHub integration | `references/github-integration.md` |
| PostgreSQL queries | `references/postgresql-queries.md` |
| Puppeteer for web testing | `references/puppeteer-for-web-testing.md` |
| Monitoring Interactive Sessions | `references/monitoring-interactive-sessions.md` |
| Periodic capture to check if Claude is still working or waiting for input | `references/periodic-capture-to-check-if-claude-is-still-working-or-wait.md` |
| Environment Variables | `references/environment-variables.md` |
| Cost & Performance Tips | `references/cost-performance-tips.md` |
| Pitfalls & Gotchas | `references/pitfalls-gotchas.md` |
| Rules for Hermes Agents | `references/rules-for-hermes-agents.md` |
| **Import Chain Debugging** | `references/import-chain-debugging.md` |
| **Windows Orchestration Bridge** (VS Code GUI pipeline) | `references/windows-orchestration-bridge.md` |
| **Bash Özel Karakter Workaround** (temp dosya + Python inline) | `references/bash-ozel-karakter-workaround.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
