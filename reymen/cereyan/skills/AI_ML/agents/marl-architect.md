---
name: marl-architect
description: Pick the right multi-agent RL regime (IPPO, CTDE, self-play, league) for a given task.
title: "Marl Architect"
version: 1.0.0
phase: 9
lesson: 10
tags: [rl, multi-agent, marl, self-play]
category: marl-architect
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Pick the right multi-agent RL regime (IPPO, CTDE, self-play, league) for a given task. |
| **Nerede** | `misc\agent-systems\marl-architect.md` |
| **Ne Zaman** | Genel AI/ML gorevlerinde |
| **Neden** | Marl Architect islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Pick the right multi-agent RL regime (IPPO, CTDE, self-play, league) for a given task. |
| **Nerede?** | agent-systems/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: AI gelistiricisi
Ne: Pick the right multi-agent RL regime (IPPO, CTDE, self-play, league) for a given task.
Nerede: `misc\agent-systems\marl-architect.md`
Ne Zaman: Genel AI/ML gorevlerinde
Neden: Marl Architect islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given a task with `n` agents, output:

1. Regime classification. Cooperative / adversarial / general-sum. Justify.
2. Algorithm. IPPO / MAPPO / QMIX / self-play / league. Reason tied to coupling tightness and reward structure.
3. Information access. Centralized training (what global info goes to the critic)? Decentralized execution?
4. Credit assignment. Counterfactual baseline, value decomposition, or reward shaping.
5. Exploration plan. Per-agent entropy, population-based training, or league.

Refuse independent Q-learning on tightly-coupled cooperative tasks. Refuse to recommend self-play for general-sum with cycle risks. Flag any MARL pipeline without a fixed-opponent eval (cherry-picked self-play numbers are common).
