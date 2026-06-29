---
name: skill-cataloging
description: Export and maintain a browsable catalog of all Hermes skills in an Obsidian vault. Enumerates skill definitions, copies their documentation, and generates a refreshed index.
title: "Skill Cataloging"
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [obsidian, skills, sync, export, documentation]
category: productivity
audience: user
tags: [productivity, tools]
---


> **Kategori:** productivity

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Export and maintain a browsable catalog of all Hermes skills in an Obsidian vault. Enumerates skill definitions, copies their documentation, and generates a refreshed index. |
| **Nerede?** | productivity/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Skill Cataloging

Export every Hermes skill to an Obsidian vault for offline browsing and reference.

## When to Use

- User asks to "export all skills to Obsidian", "sync skills to vault", or "build skill library"
- User wants a regenerated `Hermes Skills Sync.md` README
- User references a target directory like `obsidian_skill_all_tree_0`
- Companion to `obsidian` skill for bulk vault writes

## Prerequisites

- Obsidian vault path known
  - Resolved from `OBSIDIAN_VAULT_PATH` env var if set, else `C:\Users\marko\OneDrive\Belgeler\Obsidian Vault`
  - **Must be a concrete absolute path** — expand `~` before passing to tools
- Target directory inside vault (commonly `obsidian_skill_all_tree_0`)
- Write access to that vault path

## Workflow

### 1. Verify vault exists and check app.json

```bash
ls -la "$OBSIDIAN_VAULT_PATH/.obsidian/app.json"
ls -la "$OBSIDIAN_VAULT_PATH/<target_dir>"
```

If the target directory does not exist, create it with the file tool or `mkdir -p`.

### 2. Enumerate ALL skills

**Critical:** Do **not** use `skills_list`. It returns a small subset. Enumerate the filesystem directly:

```bash
# Linux/macOS (git-bash)
find "$HOME/.hermes/skills" -name SKILL.md

# Windows PowerShell
Get-ChildItem -Path "$env:APPDATA\hermes\skills" -Recurse -Filter SKILL.md | Select-Object -ExpandProperty FullName
```

This returns full paths like:
```
C:\Users\marko\AppData\Local\hermes\skills\github\github-pr-workflow\SKILL.md
```

### 3. Copy SKILL.md files to the vault target directory

Use **direct file copy**, not `skill_view`. `skill_view` is for on-demand viewing and may truncate long content, add wrapper metadata, or fail for nested skill names. For bulk copy, read/write markdown through file tools or shell copy.

```bash
# git-bash / MSYS
mkdir -p "$OBSIDIAN_VAULT_PATH/<target_dir>"
find "$HOME/.hermes/skills" -name SKILL.md | while read src; do
  # Build vault-relative path under target_dir, preserving subdirs
  rel="${src#$HOME/.hermes/skills/}"
  dest="$OBSIDIAN_VAULT_PATH/<target_dir>/$rel"
  mkdir -p "$(dirname "$dest")"
  cp -n "$src" "$dest"   # -n = no-clobber
done
```

Windows PowerShell equivalent:
```powershell
$skillsRoot = Join-Path $env:APPDATA 'hermes\skills'
$targetRoot = Join-Path $OBSIDIAN_VAULT_PATH '<target_dir>'
Get-ChildItem -Path $skillsRoot -Recurse -Filter SKILL.md | ForEach-Object {
    $rel = $_.FullName.Substring($skillsRoot.Length + 1)
    $dest = Join-Path $targetRoot $rel
    New-Item -ItemType Directory -Path (Split-Path $dest) -Force | Out-Null
    Copy-Item $_.FullName $dest
}
```

#### If using file tools instead of shell:
```bash
read_file src_path -> markdown content
write_file "$OBSIDIAN_VAULT_PATH/<target_dir>/<subpath>/SKILL.md" markdown content
```

Do this for every enumerated `SKILL.md`. Do **not** skip files just because `skills_list` did not surface them.

### 4. Generate the index (`Hermes Skills Sync.md`)

Write a **fresh**, full README-style index file at the vault root. Overwrite, do not append.

Structure:
```markdown
# Hermes Skills Sync

> Auto-generated catalog. Regenerate with `skill-cataloging`.

## Summary
- Total skills: N
- Last updated: YYYY-MM-DD

## By Category

### Category Name

| Skill | Path |
|-------|------|
| [Name](obsidian_skill_all_tree_0/category/name/SKILL.md) | category/name/SKILL.md |

...
```

#### Index fields to capture per skill
- Display name (from SKILL.md frontmatter `name` or directory name)
- Obsidian wikilink → `obsidian_skill_all_tree_0/<relative path to SKILL.md>`
- One-line description if available

### 5. Verify

```bash
echo "Copied: $(find "$OBSIDIAN_VAULT_PATH/<target_dir>" -name SKILL.md | wc -l)"
ls -la "$OBSIDIAN_VAULT_PATH/Hermes Skills Sync.md"
```

Open the sync file in Obsidian to confirm links resolve.

## Pitfalls

1. **`skills_list` is not exhaustive.** It returns only the subset that the agent runtime loads. The true count lives on disk under `~/.hermes/skills`. Always enumerate the directory tree.
2. **`skill_view` truncates long files.** It is optimized for on-demand reading, not bulk export. Use direct file read/write for complete fidelity.
3. **Spaces in paths.** Vault paths commonly contain spaces (e.g., `Obsidian Vault`). Always quote shell paths or use absolute paths with proper escaping.
4. **Overwriting manual edits.** If the target directory already contains hand-touched notes, use no-clobber copy (`cp -n`) or prompt before overwriting.
5. **Skill name vs path mismatch.** Some skills have frontmatter `name` fields that differ from their directory names. Use the directory structure for the Obsidian file tree; use the frontmatter or first header for the display name in the index.
6. **OneDrive / sync delays.** Obsidian + OneDrive may briefly lock files after writes. If copy fails with a sharing violation, retry once after a short pause.

## Minimal Invocation Example

```bash
# 1. Resolve
vault="/c/Users/marko/OneDrive/Belgeler/Obsidian Vault"
target="obsidian_skill_all_tree_0"

# 2. Ensure dirs
mkdir -p "$vault/$target"

# 3. Copy all SKILL.md files
find "$HOME/.hermes/skills" -name SKILL.md | while read src; do
  rel="${src#$HOME/.hermes/skills/}"
  dest="$vault/$target/$rel"
  mkdir -p "$(dirname "$dest")"
  cp -n "$src" "$dest"
done

# 4. Write index (replace N and table rows after enumerating)
cat > "$vault/Hermes Skills Sync.md" <<'INDEX'
# Hermes Skills Sync
...
INDEX
```

## Quality Benchmark

Tüm skill'lerin yapısal kalite analizi, frontmatter doğrulama, parse hatası düzeltme ve toplu düzeltme prosedürü:

→ `references/skill-quality-benchmark.md`

**Benchmark metrikleri:** title, tags, category, audience, parse geçerliliği, yinelenen isimler.
**Puan hesaplama:** 100 üzerinden (title=%25, tags=%25, category=%20, audience=%20, parse=%10)

**Derinlemesine içerik benchmark'ı (v2):** İçerik Kalitesi %40, Çalışabilirlik %25, Kapsam %20, Token Verimliliği %15.
→ `scripts/skill_benchmark.py` — tüm skill'leri tarar, CSV rapor + özet çıkarır.

```bash
python skills/productivity/skill-cataloging/scripts/skill_benchmark.py --csv ~/Desktop/rapor.csv
```

## Related

- `obsidian` — vault write/sync conventions, wikilink format, idempotent index refreshes
- `references/nemoclaw-repo-analysis.md` — NVIDIA NemoClaw repo incelemesi: skill pattern'i, AGENTS.md formatı, Hermes manifest
- `references/github-repo-layout.md` — GitHub'daki skills/ altında repo yapısı, hermes-full-backup organizasyonu

## Audience Classification

NemoClaw (NVIDIA/NemoClaw) pattern'iyle skill'ler **user / maintainer / contributor** olarak 3 audience'a ayrılır.

Detaylı prosedür, Python scripti, sınıflandırma listeleri ve güvenlik yedekleme talimatı:
→ `references/audience-classification.md`

**Dağılım (14 Haziran 2026):** user=848 / contributor=287 / maintainer=49 (toplam 1.184)

Kısaca:
- **contributor** — kod geliştirme (software-development/, github/, ecc pattern'leri)
- **maintainer** — sistem bakımı (devops/, *-audit/*-auditor, cron/backup)
- **user** — günlük kullanım (geri kalan ~%72)

Her SKILL.md frontmatter'ına `audience` alanı eklenir.
Toplu güncelleme öncesi `.audience-backup/` dizinine SHA256 yedek alınması ZORUNLUDUR.

## Otomatik Sync

Hermes'te `hooks/sync_skills_to_obsidian.py` script'i SKILL.md → Obsidian notu senkronizasyonunu otomatik yapar:

```bash
# Normal sync (sadece yeni skill'leri yazar, eskiyi overwrite etmez)
python3 /c/Users/marko/AppData/Local/hermes/hooks/sync_skills_to_obsidian.py

# Force sync (tüm skill'leri yeniden yazar)
python3 /c/Users/marko/AppData/Local/hermes/hooks/sync_skills_to_obsidian.py --force
```

Bu sync script'i:
- `skills/` altındaki tüm `SKILL.md` dosyalarını okur
- Obsidian vault'ta `Hermes/Skills/<kategori>/<skill-adi>.md` şeklinde yazar
- Var olan notları overwrite ETMEZ (--force ile overwrite eder)
- 145 SKILL.md → 145 Obsidian notu yazar (sayı sync script çalıştıkça güncellenir)

**Ne zaman kullanılır:** Yeni bir skill oluşturduktan sonra, veya `gece-3-github-yedek` cron job'undan önce Obsidian vault'un güncel olduğundan emin olmak için.

**Cron job önerisi:**
```bash
# Her gece 02:30'da sync çalıştır (03:00 yedekten önce)
hermes cron create --schedule "30 2 * * *" --command "python3 /c/Users/marko/AppData/Local/hermes/hooks/sync_skills_to_obsidian.py"
```