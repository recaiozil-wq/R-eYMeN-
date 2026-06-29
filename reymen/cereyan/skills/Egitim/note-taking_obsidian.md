
> **Kategori:** note-taking

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Note Taking_Obsidian |
| **Nerede?** | note-taking/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: obsidian
description: Read, search, create, and edit notes in the Obsidian vault.
title: "Obsidian"
platforms: [linux, macos, windows]

audience: user
tags: [note-taking, obsidian, productivity]
category: note-taking---

# Obsidian Vault

Use this skill for filesystem-first Obsidian vault work: reading notes, listing notes, searching note files, creating notes, appending content, and adding wikilinks.

## Vault path

Use a known or resolved vault path before calling file tools.

The documented vault-path convention is the `OBSIDIAN_VAULT_PATH` environment variable, for example from `~/.hermes/.env`. If it is unset, use `C:\Users\marko\OneDrive\Belgeler\Obsidian Vault`.

File tools do not expand shell variables. Do not pass paths containing `$OBSIDIAN_VAULT_PATH` to `read_file`, `write_file`, `patch`, or `search_files`; resolve the vault path first and pass a concrete absolute path. Vault paths may contain spaces, which is another reason to prefer file tools over shell commands.

If the vault path is unknown, `terminal` is acceptable for resolving `OBSIDIAN_VAULT_PATH` or checking whether the fallback path exists. Once the path is known, switch back to file tools.

## Sync rules

Prefer direct file-tool sync over shell commands for vault writes. When syncing derived indexes, runlists, or logs from another source of truth into Obsidian, write the full reconciled markdown file rather than incremental terminal appends. Reason: file tools preserve structure and avoid quoting issues.

Use Obsidian wikilinks for references between notes. Keep skill-sync notes idempotent: overwrite the whole note on refresh rather than appending duplicates.

## Read a note

Use `read_file` with the resolved absolute path to the note. Prefer this over `cat` because it provides line numbers and pagination.

## List notes

Use `search_files` with `target: "files"` and the resolved vault path. Prefer this over `find` or `ls`.

- To list all markdown notes, use `pattern: "*.md"` under the vault path.
- To list a subfolder, search under that subfolder's absolute path.

## Search

Use `search_files` for both filename and content searches. Prefer this over `grep`, `find`, or `ls`.

- For filenames, use `search_files` with `target: "files"` and a filename `pattern`.
- For note contents, use `search_files` with `target: "content"`, the content regex as `pattern`, and `file_glob: "*.md"` when you want to restrict matches to markdown notes.

## Create a note

Use `write_file` with the resolved absolute path and the full markdown content. Prefer this over shell heredocs or `echo` because it avoids shell quoting issues and returns structured results.

## Append to a note

Prefer a native file-tool workflow when it is not awkward:

- Read the target note with `read_file`.
- Use `patch` for an anchored append when there is stable context, such as adding a section after an existing heading or appending before a known trailing block.
- Use `write_file` when rewriting the whole note is clearer than constructing a fragile patch.

For a simple append with no stable context, `terminal` is acceptable if it is the clearest safe option.

## Derived index notes

For sync notes such as skill indexes, write the full reconciled markdown file rather than running shell appends. Keep these notes idempotent: on refresh, overwrite the whole note instead of appending duplicate entries.

## Targeted edits

Use `patch` for focused note changes when the current content gives you stable context. Prefer this over shell text rewriting.

## Wikilinks

Obsidian links notes with `[[Note Name]]` syntax. When creating notes, use these to link related content.

### Vault-wide relationship linking

For larger vaults (50+ notes), use a three-tier linking strategy
instead of ad-hoc wikilinks:

1. **MOC (Map of Content)** — one per broad domain, lives at vault root
2. **Category-index cross-references** — `_index.md` header links to MOC
3. **Per-note cross-category links** — `## Cross-category links` section

See `references/vault-relationship-linking.md` for the full strategy
with scan recipe, pitfalls, and relative-path conventions.
