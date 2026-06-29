---

name: github-code-review
title: "GitHub Code Review"
tags: [development, git, github]
description: "Review PRs: diffs, inline comments via gh or REST."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Code-Review, Pull-Requests, Git, Quality]
audience: contributor
related_skills: [github-auth, github-pr-workflow]
---


> **Kategori:** github

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Review PRs: diffs, inline comments via gh or REST. |
| **Nerede?** | github/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Github Code Review

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| GitHub Code Review | `references/github-code-review.md` |
| Prerequisites | `references/prerequisites.md` |
| 1. Reviewing Local Changes (Pre-Push) | `references/1-reviewing-local-changes-pre-push.md` |
| Staged changes (what would be committed) | `references/staged-changes-what-would-be-committed.md` |
| All changes vs main (what a PR would contain) | `references/all-changes-vs-main-what-a-pr-would-contain.md` |
| File names only | `references/file-names-only.md` |
| Stat summary (insertions/deletions per file) | `references/stat-summary-insertions-deletions-per-file.md` |
| Debug statements, TODOs, console.logs left behind | `references/debug-statements-todos-console-logs-left-behind.md` |
| Large files accidentally staged | `references/large-files-accidentally-staged.md` |
| Secrets or credential patterns | `references/secrets-or-credential-patterns.md` |
| Merge conflict markers | `references/merge-conflict-markers.md` |
| Code Review Summary | `references/code-review-summary.md` |
| 2. Reviewing a Pull Request on GitHub | `references/2-reviewing-a-pull-request-on-github.md` |
| Get PR details | `references/get-pr-details.md` |
| List changed files | `references/list-changed-files.md` |
| Fetch the PR branch and check it out | `references/fetch-the-pr-branch-and-check-it-out.md` |
| View diff against the base branch | `references/view-diff-against-the-base-branch.md` |
| Get the head commit SHA | `references/get-the-head-commit-sha.md` |
| 3. Review Checklist | `references/3-review-checklist.md` |
| 4. Pre-Push Review Workflow | `references/4-pre-push-review-workflow.md` |
| 5. PR Review Workflow (End-to-End) | `references/5-pr-review-workflow-end-to-end.md` |
| Or run the inline setup block from the top of this skill | `references/or-run-the-inline-setup-block-from-the-top-of-this-skill.md` |
| PR details (title, author, description, branch) | `references/pr-details-title-author-description-branch.md` |
| Changed files with line counts | `references/changed-files-with-line-counts.md` |
| Full diff against the base branch | `references/full-diff-against-the-base-branch.md` |
| Then for each file: | `references/then-for-each-file.md` |
| or: eslint, clippy, etc. | `references/or-eslint-clippy-etc.md` |
| If no issues — approve | `references/if-no-issues-approve.md` |
| If issues found — request changes with inline comments | `references/if-issues-found-request-changes-with-inline-comments.md` |
| Build the review JSON — event is APPROVE, REQUEST_CHANGES, or COMMENT | `references/build-the-review-json-event-is-approve-request_changes-or-co.md` |
| Code Review Summary | `references/code-review-summary.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
