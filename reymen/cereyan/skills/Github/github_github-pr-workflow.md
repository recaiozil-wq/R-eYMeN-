---

name: github-pr-workflow
title: "GitHub Pr Workflow"
tags: [development, git, github]
description: "GitHub PR lifecycle: branch, commit, open, CI, merge."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Pull-Requests, CI/CD, Git, Automation, Merge]
audience: contributor
related_skills: [github-auth, github-code-review]
---


> **Kategori:** github

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | GitHub PR lifecycle: branch, commit, open, CI, merge. |
| **Nerede?** | github/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Github Pr Workflow

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| GitHub Pull Request Workflow | `references/github-pull-request-workflow.md` |
| Prerequisites | `references/prerequisites.md` |
| Determine which method to use throughout this workflow | `references/determine-which-method-to-use-throughout-this-workflow.md` |
| Ensure we have a token for API calls | `references/ensure-we-have-a-token-for-api-calls.md` |
| Works for both HTTPS and SSH remote URLs | `references/works-for-both-https-and-ssh-remote-urls.md` |
| 1. Branch Creation | `references/1-branch-creation.md` |
| Make sure you're up to date | `references/make-sure-you-re-up-to-date.md` |
| Create and switch to a new branch | `references/create-and-switch-to-a-new-branch.md` |
| 2. Making Commits | `references/2-making-commits.md` |
| Stage specific files | `references/stage-specific-files.md` |
| Commit with a conventional commit message | `references/commit-with-a-conventional-commit-message.md` |
| 3. Pushing and Creating a PR | `references/3-pushing-and-creating-a-pr.md` |
| Test Plan | `references/test-plan.md` |
| 4. Monitoring CI Status | `references/4-monitoring-ci-status.md` |
| One-shot check | `references/one-shot-check.md` |
| Watch until all checks finish (polls every 10s) | `references/watch-until-all-checks-finish-polls-every-10s.md` |
| Get the latest commit SHA on the current branch | `references/get-the-latest-commit-sha-on-the-current-branch.md` |
| Query the combined status | `references/query-the-combined-status.md` |
| Also check GitHub Actions check runs (separate endpoint) | `references/also-check-github-actions-check-runs-separate-endpoint.md` |
| Simple polling loop — check every 30 seconds, up to 10 minutes | `references/simple-polling-loop-check-every-30-seconds-up-to-10-minutes.md` |
| 5. Auto-Fixing CI Failures | `references/5-auto-fixing-ci-failures.md` |
| List recent workflow runs on this branch | `references/list-recent-workflow-runs-on-this-branch.md` |
| View failed logs | `references/view-failed-logs.md` |
| List workflow runs on this branch | `references/list-workflow-runs-on-this-branch.md` |
| Get failed job logs (download as zip, extract, read) | `references/get-failed-job-logs-download-as-zip-extract-read.md` |
| 6. Merging | `references/6-merging.md` |
| Squash merge + delete branch (cleanest for feature branches) | `references/squash-merge-delete-branch-cleanest-for-feature-branches.md` |
| Enable auto-merge (merges when all checks pass) | `references/enable-auto-merge-merges-when-all-checks-pass.md` |
| Merge the PR via API (squash) | `references/merge-the-pr-via-api-squash.md` |
| Delete the remote branch after merge | `references/delete-the-remote-branch-after-merge.md` |
| Switch back to main locally | `references/switch-back-to-main-locally.md` |
| This uses the GraphQL API since REST doesn't support auto-merge. | `references/this-uses-the-graphql-api-since-rest-doesn-t-support-auto-me.md` |
| 7. Complete Workflow Example | `references/7-complete-workflow-example.md` |
| 1. Start from clean main | `references/1-start-from-clean-main.md` |
| 2. Branch | `references/2-branch.md` |
| 4. Commit | `references/4-commit.md` |
| 5. Push | `references/5-push.md` |
| 8. Merge when green (see Section 6) | `references/8-merge-when-green-see-section-6.md` |
| Useful PR Commands Reference | `references/useful-pr-commands-reference.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
