---
name: sim2real-planner
description: Plan a sim-to-real transfer pipeline for a given robot + task, covering DR, SI, and safety.
title: "Sim2Real Planner"
version: 1.0.0
phase: 9
lesson: 11
tags: [rl, sim2real, robotics, domain-randomization]
category: sim2real-planner
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | DevOps muhendisi |
| **Ne** | Plan a sim-to-real transfer pipeline for a given robot + task, covering DR, SI, and safety. |
| **Nerede** | `devops\sim2real-planner.md` |
| **Ne Zaman** | CI/CD veya altyapi yonetimi gerektiginde |
| **Neden** | Sim2Real Planner islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Plan a sim-to-real transfer pipeline for a given robot + task, covering DR, SI, and safety. |
| **Nerede?** | devops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: DevOps muhendisi
Ne: Plan a sim-to-real transfer pipeline for a given robot + task, covering DR, SI, and safety.
Nerede: `devops\sim2real-planner.md`
Ne Zaman: CI/CD veya altyapi yonetimi gerektiginde
Neden: Sim2Real Planner islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a robot platform, a task, and access to real hardware time, output:

1. Reality gap inventory. Suspected sources ranked by expected impact (contact, sensing, actuation delay, vision).
2. DR parameters. Exact list, ranges, distribution. Justify each range against real measurements.
3. SI steps. Which parameters to measure; measurement method.
4. Teacher/student split. What privileged info the teacher uses; what obs the student uses.
5. Safety envelope. Low-level limits, emergency stops, backup controller.

Refuse to deploy without (a) a zero-shot sim-variant test, (b) a safety shield, (c) a rollback plan. Flag any DR range wider than 3× measured real variability as likely over-randomized.
