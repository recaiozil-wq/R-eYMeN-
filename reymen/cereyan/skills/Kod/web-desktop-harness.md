---
name: web-desktop-harness
description: Build a WebArena/OSWorld-style harness with execution-based evaluation and trajectory-efficiency metrics.
title: "Web Desktop Harness"
version: 1.0.0
phase: 14
lesson: 20
tags: [webarena, osworld, harness, trajectory-efficiency]
category: web-desktop-harness
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Build a WebArena/OSWorld-style harness with execution-based evaluation and trajectory-efficiency metrics. |
| **Nerede** | `software-development\web-desktop-harness.md` |
| **Ne Zaman** | Ilgili gorev gerektiginde |
| **Neden** | Web Desktop Harness islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Build a WebArena/OSWorld-style harness with execution-based evaluation and trajectory-efficiency metrics. |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: Yazilim gelistirici
Ne: Build a WebArena/OSWorld-style harness with execution-based evaluation and trajectory-efficiency metrics.
Nerede: `software-development\web-desktop-harness.md`
Ne Zaman: Ilgili gorev gerektiginde
Neden: Web Desktop Harness islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a target app (web or desktop) and a list of tasks with gold trajectories, build an eval harness.

Produce:

1. Task definitions: `(tid, description, gold_steps, success_predicate, state_reset)`.
2. Runner: runs the agent, captures every action, records step count + elapsed time + success state.
3. Trajectory-efficiency metric: `agent_steps / gold_steps`. Report per-task and aggregate.
4. State reset between tasks — never run one task on state dirtied by another.
5. Failure-mode classifier: for each failure, tag whether it's a grounding miss (wrong element) or a planning miss (wrong action).

Hard rejects:

- No state reset between tasks. Cross-task contamination invalidates all scores.
- Success-rate-only reporting. Trajectory efficiency is the 2026 standard.
- Screenshots-only harness without DOM parity. Some agents use DOM+vision; give both unless specifically constraining the surface.

Refusal rules:

- If the tasks have no gold trajectories, refuse. You cannot measure efficiency without them.
- If the app is not pinned to a specific version, refuse. Drift invalidates cross-run comparisons.
- If the agent has destructive tools (delete, publish), require a sandbox copy of the app.

Output: `tasks.py`, `runner.py`, `failure_classifier.py`, `report.py`, `README.md` explaining reset policy, gold-trajectory sourcing, and the grounding-vs-planning split. End with "what to read next" pointing to Lesson 21 (computer use models) or Lesson 30 (eval-driven development).
