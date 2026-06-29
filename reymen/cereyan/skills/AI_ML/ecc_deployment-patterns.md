
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ecc_Deployment Patterns |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: deployment-patterns
description: Deployment workflows, CI/CD pipeline patterns, Docker containerization, health checks, rollback strategies, and production readiness checklists for web applications.
title: "Deployment Patterns"
origin: ECC

audience: contributor
tags: [ai, automation, deployment, development]
category: ecc---

# Deployment Patterns

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Deployment Patterns | `references/deployment-patterns.md` |
| When to Activate | `references/when-to-activate.md` |
| Deployment Strategies | `references/deployment-strategies.md` |
| After verification: | `references/after-verification.md` |
| If metrics look good: | `references/if-metrics-look-good.md` |
| Final: | `references/final.md` |
| Docker | `references/docker.md` |
| Stage 1: Install dependencies | `references/stage-1-install-dependencies.md` |
| Stage 2: Build | `references/stage-2-build.md` |
| Stage 3: Production image | `references/stage-3-production-image.md` |
| GOOD practices | `references/good-practices.md` |
| BAD practices | `references/bad-practices.md` |
| CI/CD Pipeline | `references/ci-cd-pipeline.md` |
| K8s: kubectl set image deployment/app app=ghcr.io/${{ github.repository }}:${{ github.sha }} | `references/k8s-kubectl-set-image-deployment-app-app-ghcr-io-github-repo.md` |
| Health Checks | `references/health-checks.md` |
| Environment Configuration | `references/environment-configuration.md` |
| All config via environment variables — never in code | `references/all-config-via-environment-variables-never-in-code.md` |
| Environment-specific behavior | `references/environment-specific-behavior.md` |
| Rollback Strategy | `references/rollback-strategy.md` |
| Docker/Kubernetes: point to previous image | `references/docker-kubernetes-point-to-previous-image.md` |
| Vercel: promote previous deployment | `references/vercel-promote-previous-deployment.md` |
| Railway: redeploy previous commit | `references/railway-redeploy-previous-commit.md` |
| Database: rollback migration (if reversible) | `references/database-rollback-migration-if-reversible.md` |
| Production Readiness Checklist | `references/production-readiness-checklist.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
