
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ecc_Docker Patterns |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: docker-patterns
description: Docker and Docker Compose patterns for local development, container security, networking, volume strategies, and multi-service orchestration.
title: "Docker Patterns"
origin: ECC

audience: contributor
tags: [ai, automation, development, docker]
category: ecc---

# Docker Patterns

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Docker Patterns | `references/docker-patterns.md` |
| When to Activate | `references/when-to-activate.md` |
| Docker Compose for Local Development | `references/docker-compose-for-local-development.md` |
| docker-compose.yml | `references/docker-compose-yml.md` |
| Stage: dependencies | `references/stage-dependencies.md` |
| Stage: dev (hot reload, debug tools) | `references/stage-dev-hot-reload-debug-tools.md` |
| Stage: build | `references/stage-build.md` |
| Stage: production (minimal image) | `references/stage-production-minimal-image.md` |
| docker-compose.override.yml (auto-loaded, dev-only settings) | `references/docker-compose-override-yml-auto-loaded-dev-only-settings.md` |
| docker-compose.prod.yml (explicit for production) | `references/docker-compose-prod-yml-explicit-for-production.md` |
| Development (auto-loads override) | `references/development-auto-loads-override.md` |
| Production | `references/production.md` |
| Networking | `references/networking.md` |
| From "app" container: | `references/from-app-container.md` |
| Omit ports entirely in production -- accessible only within Docker network | `references/omit-ports-entirely-in-production-accessible-only-within-doc.md` |
| Volume Strategies | `references/volume-strategies.md` |
| Named volume: persists across container restarts, managed by Docker | `references/named-volume-persists-across-container-restarts-managed-by-d.md` |
| - /app/node_modules | `references/app-node_modules.md` |
| Container Security | `references/container-security.md` |
| 1. Use specific tags (never :latest) | `references/1-use-specific-tags-never-latest.md` |
| 2. Run as non-root | `references/2-run-as-non-root.md` |
| 5. No secrets in image layers | `references/5-no-secrets-in-image-layers.md` |
| GOOD: Use environment variables (injected at runtime) | `references/good-use-environment-variables-injected-at-runtime.md` |
| GOOD: Docker secrets (Swarm mode) | `references/good-docker-secrets-swarm-mode.md` |
| ENV API_KEY=sk-proj-xxxxx      NEVER DO THIS | `references/env-api_key-sk-proj-xxxxx-never-do-this.md` |
| .dockerignore | `references/dockerignore.md` |
| Debugging | `references/debugging.md` |
| View logs | `references/view-logs.md` |
| Execute commands in running container | `references/execute-commands-in-running-container.md` |
| Inspect | `references/inspect.md` |
| Rebuild | `references/rebuild.md` |
| Clean up | `references/clean-up.md` |
| Check DNS resolution inside container | `references/check-dns-resolution-inside-container.md` |
| Check connectivity | `references/check-connectivity.md` |
| Inspect network | `references/inspect-network.md` |
| Anti-Patterns | `references/anti-patterns.md` |
| Use .env files (gitignored) or Docker secrets | `references/use-env-files-gitignored-or-docker-secrets.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
