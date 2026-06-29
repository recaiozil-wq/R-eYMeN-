
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ecc_Kubernetes Patterns |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: kubernetes-patterns
description: Kubernetes workload patterns, resource management, RBAC, probes, autoscaling, ConfigMap/Secret handling, and kubectl debugging for production-grade deployments.
title: "Kubernetes Patterns"
origin: ECC

audience: contributor
tags: [ai, automation, development, k8s]
category: ecc---

# Kubernetes Patterns

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Kubernetes Patterns | `references/kubernetes-patterns.md` |
| When to Activate | `references/when-to-activate.md` |
| When to Use | `references/when-to-use.md` |
| How It Works | `references/how-it-works.md` |
| Examples | `references/examples.md` |
| Core Workload Patterns | `references/core-workload-patterns.md` |
| Security context at pod level | `references/security-context-at-pod-level.md` |
| Graceful shutdown | `references/graceful-shutdown.md` |
| Resource requests AND limits are both required | `references/resource-requests-and-limits-are-both-required.md` |
| Container security context | `references/container-security-context.md` |
| Probes (see Probes section below) | `references/probes-see-probes-section-below.md` |
| Environment from ConfigMap and Secret | `references/environment-from-configmap-and-secret.md` |
| Writable tmp directory when readOnlyRootFilesystem: true | `references/writable-tmp-directory-when-readonlyrootfilesystem-true.md` |
| Probes — Liveness, Readiness, Startup | `references/probes-liveness-readiness-startup.md` |
| then liveness/readiness take over | `references/then-liveness-readiness-take-over.md` |
| If the app takes 60s to start, set a startupProbe instead | `references/if-the-app-takes-60s-to-start-set-a-startupprobe-instead.md` |
| Services and Ingress | `references/services-and-ingress.md` |
| ClusterIP (default) — internal-only | `references/clusterip-default-internal-only.md` |
| LoadBalancer — external traffic (cloud providers) | `references/loadbalancer-external-traffic-cloud-providers.md` |
| ConfigMaps and Secrets | `references/configmaps-and-secrets.md` |
| Mount as a file for complex config | `references/mount-as-a-file-for-complex-config.md` |
| Mount ConfigMap as a file | `references/mount-configmap-as-a-file.md` |
| Create secret from literal (CLI, then store in Vault/SOPS) | `references/create-secret-from-literal-cli-then-store-in-vault-sops.md` |
| Values are base64-encoded (NOT encrypted — use Sealed Secrets or ESO for real encryption) | `references/values-are-base64-encoded-not-encrypted-use-sealed-secrets-o.md` |
| Resource Requests and Limits | `references/resource-requests-and-limits.md` |
| WRONG: No requests or limits — unpredictable scheduling, OOM evictions | `references/wrong-no-requests-or-limits-unpredictable-scheduling-oom-evi.md` |
| WRONG: Limits without requests — requests default to limits, over-reserves capacity | `references/wrong-limits-without-requests-requests-default-to-limits-ove.md` |
| requests missing — will default to limits values | `references/requests-missing-will-default-to-limits-values.md` |
| RBAC — Roles and ServiceAccounts | `references/rbac-roles-and-serviceaccounts.md` |
| ServiceAccount with token disabled — safest default | `references/serviceaccount-with-token-disabled-safest-default.md` |
| Reference in Deployment — no token, no API access | `references/reference-in-deployment-no-token-no-api-access.md` |
| 1. ServiceAccount — enable token for this SA | `references/1-serviceaccount-enable-token-for-this-sa.md` |
| 2. Role — grant only what the app needs (namespace-scoped) | `references/2-role-grant-only-what-the-app-needs-namespace-scoped.md` |
| 3. Bind Role to ServiceAccount | `references/3-bind-role-to-serviceaccount.md` |
| 4. Reference SA in Deployment | `references/4-reference-sa-in-deployment.md` |
| automountServiceAccountToken defaults to true from SA — token is injected | `references/automountserviceaccounttoken-defaults-to-true-from-sa-token-.md` |
| Horizontal Pod Autoscaler (HPA) | `references/horizontal-pod-autoscaler-hpa.md` |
| PodDisruptionBudget (PDB) | `references/poddisruptionbudget-pdb.md` |
| Namespaces and Multi-Tenancy | `references/namespaces-and-multi-tenancy.md` |
| Create namespace with resource quotas | `references/create-namespace-with-resource-quotas.md` |
| Apply ResourceQuota to limit namespace consumption | `references/apply-resourcequota-to-limit-namespace-consumption.md` |
| Jobs and CronJobs | `references/jobs-and-cronjobs.md` |
| One-off Job (DB migration, data processing) | `references/one-off-job-db-migration-data-processing.md` |
| CronJob | `references/cronjob.md` |
| kubectl Debugging Cheatsheet | `references/kubectl-debugging-cheatsheet.md` |
| --- Pod status and logs --- | `references/pod-status-and-logs.md` |
| --- Execute into a running container --- | `references/execute-into-a-running-container.md` |
| --- Check resource usage --- | `references/check-resource-usage.md` |
| --- Deployment operations --- | `references/deployment-operations.md` |
| --- Scale manually --- | `references/scale-manually.md` |
| --- Inspect events (cluster-wide issues) --- | `references/inspect-events-cluster-wide-issues.md` |
| --- Port-forward for local debugging --- | `references/port-forward-for-local-debugging.md` |
| --- Dry-run to validate YAML --- | `references/dry-run-to-validate-yaml.md` |
| CrashLoopBackOff: container keeps crashing | `references/crashloopbackoff-container-keeps-crashing.md` |
| Increase memory limits, check for memory leaks | `references/increase-memory-limits-check-for-memory-leaks.md` |
| Anti-Patterns | `references/anti-patterns.md` |
| BAD: Using :latest tag — non-deterministic deployments | `references/bad-using-latest-tag-non-deterministic-deployments.md` |
| or | `references/or.md` |
| BAD: Running as root | `references/bad-running-as-root.md` |
| GOOD: Non-root with explicit UID | `references/good-non-root-with-explicit-uid.md` |
| BAD: No resource limits — one pod can starve the entire node | `references/bad-no-resource-limits-one-pod-can-starve-the-entire-node.md` |
| GOOD: Always set requests and limits | `references/good-always-set-requests-and-limits.md` |
| BAD: Storing plaintext secrets in ConfigMaps | `references/bad-storing-plaintext-secrets-in-configmaps.md` |
| BAD: ClusterAdmin for application service accounts | `references/bad-clusteradmin-for-application-service-accounts.md` |
| BAD: minAvailable: 0 in PDB — defeats the purpose | `references/bad-minavailable-0-in-pdb-defeats-the-purpose.md` |
| BAD: restartPolicy: Always in a Job (causes infinite restart loop) | `references/bad-restartpolicy-always-in-a-job-causes-infinite-restart-lo.md` |
| Best Practices Checklist | `references/best-practices-checklist.md` |
| Related Skills | `references/related-skills.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
