
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ecc_Django Celery |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: django-celery
description: Django + Celery async task patterns — configuration, task design, beat scheduling, retries, canvas workflows, monitoring, and testing. Use when adding background jobs, scheduled tasks, or async processing to a Django app.
title: "Django Celery"
origin: ECC

audience: contributor
tags: [ai, automation, development]
category: ecc---

# Django Celery

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Django + Celery Async Task Patterns | `references/django-celery-async-task-patterns.md` |
| When to Activate | `references/when-to-activate.md` |
| Project Setup | `references/project-setup.md` |
| config/celery.py | `references/config-celery-py.md` |
| config/__init__.py | `references/config-__init__-py.md` |
| Broker (Redis recommended for production) | `references/broker-redis-recommended-for-production.md` |
| Serialization | `references/serialization.md` |
| Task behavior | `references/task-behavior.md` |
| Result persistence | `references/result-persistence.md` |
| Beat scheduler (for periodic tasks) | `references/beat-scheduler-for-periodic-tasks.md` |
| Installed apps | `references/installed-apps.md` |
| Start worker (development) | `references/start-worker-development.md` |
| Start beat scheduler (periodic tasks) | `references/start-beat-scheduler-periodic-tasks.md` |
| Combined worker + beat (dev only, never production) | `references/combined-worker-beat-dev-only-never-production.md` |
| Production: multiple workers with concurrency | `references/production-multiple-workers-with-concurrency.md` |
| Task Design Patterns | `references/task-design-patterns.md` |
| apps/notifications/tasks.py | `references/apps-notifications-tasks-py.md` |
| Specific retry delay from response header | `references/specific-retry-delay-from-response-header.md` |
| Clean up partial files before hard kill | `references/clean-up-partial-files-before-hard-kill.md` |
| Calling Tasks | `references/calling-tasks.md` |
| Fire and forget (async) | `references/fire-and-forget-async.md` |
| Schedule in the future | `references/schedule-in-the-future.md` |
| Apply with queue routing | `references/apply-with-queue-routing.md` |
| Run synchronously (tests / debugging only) | `references/run-synchronously-tests-debugging-only.md` |
| Beat Scheduling (Periodic Tasks) | `references/beat-scheduling-periodic-tasks.md` |
| config/settings/base.py | `references/config-settings-base-py.md` |
| Manage periodic tasks from Django admin or code | `references/manage-periodic-tasks-from-django-admin-or-code.md` |
| Canvas: Chaining and Grouping Tasks | `references/canvas-chaining-and-grouping-tasks.md` |
| Chain: run tasks sequentially, passing results | `references/chain-run-tasks-sequentially-passing-results.md` |
| Group: run tasks in parallel | `references/group-run-tasks-in-parallel.md` |
| Chord: parallel tasks + callback when all complete | `references/chord-parallel-tasks-callback-when-all-complete.md` |
| Error Handling and Dead Letter Queue | `references/error-handling-and-dead-letter-queue.md` |
| apps/core/tasks.py | `references/apps-core-tasks-py.md` |
| Route failed tasks to dead-letter queue after max retries | `references/route-failed-tasks-to-dead-letter-queue-after-max-retries.md` |
| Persist to dead-letter table for manual review | `references/persist-to-dead-letter-table-for-manual-review.md` |
| Testing Celery Tasks | `references/testing-celery-tasks.md` |
| tests/test_tasks.py | `references/tests-test_tasks-py.md` |
| config/settings/test.py | `references/config-settings-test-py.md` |
| tests/test_integration.py | `references/tests-test_integration-py.md` |
| Monitoring | `references/monitoring.md` |
| Inspect active workers and queues | `references/inspect-active-workers-and-queues.md` |
| Check queue lengths (Redis) | `references/check-queue-lengths-redis.md` |
| Flower: web-based real-time monitor | `references/flower-web-based-real-time-monitor.md` |
| Anti-Patterns | `references/anti-patterns.md` |
| BAD: Passing model instances — they may be stale by execution time | `references/bad-passing-model-instances-they-may-be-stale-by-execution-t.md` |
| BAD: Calling tasks synchronously in production views | `references/bad-calling-tasks-synchronously-in-production-views.md` |
| BAD: Non-idempotent task without guards | `references/bad-non-idempotent-task-without-guards.md` |
| GOOD: Idempotent with status guard | `references/good-idempotent-with-status-guard.md` |
| Production Checklist | `references/production-checklist.md` |
| Related Skills | `references/related-skills.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
