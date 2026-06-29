---

name: github-repo-management
title: "GitHub Repo Management"
tags: [development, git, github]
description: "Clone/create/fork repos; manage remotes, releases."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Repositories, Git, Releases, Secrets, Configuration]
audience: contributor
related_skills: [github-auth, github-pr-workflow, github-issues]
---


> **Kategori:** github

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Clone/create/fork repos; manage remotes, releases. |
| **Nerede?** | github/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Github Repo Management

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| GitHub Repository Management | `references/github-repository-management.md` |
| Prerequisites | `references/prerequisites.md` |
| Get your GitHub username (needed for several operations) | `references/get-your-github-username-needed-for-several-operations.md` |
| 1. Cloning Repositories | `references/1-cloning-repositories.md` |
| Clone via HTTPS (works with credential helper or token-embedded URL) | `references/clone-via-https-works-with-credential-helper-or-token-embedd.md` |
| Clone into a specific directory | `references/clone-into-a-specific-directory.md` |
| Shallow clone (faster for large repos) | `references/shallow-clone-faster-for-large-repos.md` |
| Clone a specific branch | `references/clone-a-specific-branch.md` |
| Clone via SSH (if SSH is configured) | `references/clone-via-ssh-if-ssh-is-configured.md` |
| 2. Creating Repositories | `references/2-creating-repositories.md` |
| Create a public repo and clone it | `references/create-a-public-repo-and-clone-it.md` |
| Private, with description and license | `references/private-with-description-and-license.md` |
| Under an organization | `references/under-an-organization.md` |
| From existing local directory | `references/from-existing-local-directory.md` |
| Create the remote repo via API | `references/create-the-remote-repo-via-api.md` |
| Clone it | `references/clone-it.md` |
| -- OR -- push an existing local directory to the new repo | `references/or-push-an-existing-local-directory-to-the-new-repo.md` |
| 3. Forking Repositories | `references/3-forking-repositories.md` |
| Create the fork via API | `references/create-the-fork-via-api.md` |
| Wait a moment for GitHub to create it, then clone | `references/wait-a-moment-for-github-to-create-it-then-clone.md` |
| Add the original repo as "upstream" remote | `references/add-the-original-repo-as-upstream-remote.md` |
| Pure git — works everywhere | `references/pure-git-works-everywhere.md` |
| 4. Repository Information | `references/4-repository-information.md` |
| View repo details | `references/view-repo-details.md` |
| List your repos | `references/list-your-repos.md` |
| Search repos | `references/search-repos.md` |
| 5. Repository Settings | `references/5-repository-settings.md` |
| Update topics | `references/update-topics.md` |
| 6. Branch Protection | `references/6-branch-protection.md` |
| View current protection | `references/view-current-protection.md` |
| Set up branch protection | `references/set-up-branch-protection.md` |
| 7. Secrets Management (GitHub Actions) | `references/7-secrets-management-github-actions.md` |
| Get the repo's public key for encrypting secrets | `references/get-the-repo-s-public-key-for-encrypting-secrets.md` |
| Encrypt and set (requires Python with PyNaCl) | `references/encrypt-and-set-requires-python-with-pynacl.md` |
| Get the public key | `references/get-the-public-key.md` |
| Encrypt | `references/encrypt.md` |
| Then PUT the encrypted secret | `references/then-put-the-encrypted-secret.md` |
| List secrets (names only, values hidden) | `references/list-secrets-names-only-values-hidden.md` |
| 8. Releases | `references/8-releases.md` |
| Create a release | `references/create-a-release.md` |
| List releases | `references/list-releases.md` |
| Upload a release asset (binary file) | `references/upload-a-release-asset-binary-file.md` |
| 9. GitHub Actions Workflows | `references/9-github-actions-workflows.md` |
| List workflows | `references/list-workflows.md` |
| List recent runs | `references/list-recent-runs.md` |
| Download failed run logs | `references/download-failed-run-logs.md` |
| Re-run a failed workflow | `references/re-run-a-failed-workflow.md` |
| Re-run only failed jobs | `references/re-run-only-failed-jobs.md` |
| Trigger a workflow manually (workflow_dispatch) | `references/trigger-a-workflow-manually-workflow_dispatch.md` |
| 10. Gists | `references/10-gists.md` |
| Create a gist | `references/create-a-gist.md` |
| List your gists | `references/list-your-gists.md` |
| 11. Pre-Install Evaluation (Third-Party Repos) | `references/11-pre-install-evaluation-third-party-repos.md` |
| 12. Repo Promotion & SEO | `references/repo-promotion-seo.md` |
| Same SHA = no tampering. Different = review changes. | `references/same-sha-no-tampering-different-review-changes.md` |
| NOT skills scattered in subdirectories | `references/not-skills-scattered-in-subdirectories.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
