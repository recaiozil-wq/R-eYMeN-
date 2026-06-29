
> **Kategori:** gaming

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Gaming_Game Trainer Repo Workflow |
| **Nerede?** | gaming/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: game-trainer-repo-workflow
description: Find, evaluate, and apply external game trainer/tool repositories for single-player character enhancement. Use when the user asks about trainers, cheats, character power-ups, repo hunting for game modifications, or any GitHub-based trainer discovery workflow.
title: "Game Trainer Repo Workflow"
trigger: user asks for trainer, cheat, character enhancement, repo search for game tools, "repo" in gaming context, game modification discovery

audience: user
tags: [gaming, training]
category: gaming---

# Game Trainer Repository Workflow

## User Preferences

- **Autonomous action first.** Do NOT ask clarifying questions when the goal is clear. Search, identify, and report directly.
- **Single-player focus.** Only consider trainers/tools that work in single-player or offline modes.
- **Repository-first approach.** Prefer downloading/tweaking external repos over explaining theoretical techniques.
- **Direct results.** User wants actionable GitHub repo links, not tutorials or explanations unless asked.

## Workflow

1. **Detect current game context**
   - Check running processes (`tasklist`) for game executables
   - If game name is unclear, scan recent window titles or ask ONCE only if blocking

2. **Search GitHub for relevant trainer repos**
   - Use queries like: `<game_name> trainer cheat single-player`
   - Also try: `<game_name> character editor save game editor`
   - Filter by language (C#, C++, Python, Lua) depending on game modding ecosystem

3. **Evaluate candidates**
   - Prefer repos with: recent activity, clear README, working binaries or build instructions, single-player focus
   - Avoid: multiplayer-only, anti-cheat flagged, empty/no-activity repos

4. **Report actionable findings**
   - Repo URL
   - Brief description of what it modifies (health, ammo, skills, etc.)
   - Setup steps (build, download, config)
   - Risk note if any (ban risk, detection, save game corruption)

## Pitfalls

- Do NOT suggest online/cloud trainers that require account creation unless user asks
- Do NOT recommend multiplayer cheat tools; user explicitly prefers single-player
- Do NOT search generic terms like "trainer" alone — always include game name
- Do NOT ask "which game" if process list shows a clear candidate

## Integration with Existing Skills

- Uses `mcp_github_search_repositories` for discovery
- Uses `terminal` for process scanning
- Uses `obsidian` to save findings to vault for future reference
