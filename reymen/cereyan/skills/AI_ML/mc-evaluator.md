---
name: mc-evaluator
description: Evaluate a policy via Monte Carlo rollouts and produce a convergence report with DP-comparison if available.
title: "Mc Evaluator"
version: 1.0.0
phase: 9
lesson: 3
tags: [rl, monte-carlo, evaluation]
category: mc-evaluator
audience: user


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ML/Veri bilimci |
| **Ne** | Evaluate a policy via Monte Carlo rollouts and produce a convergence report with DP-comparison if available. |
| **Nerede** | `mlops\evaluation\mc-evaluator.md` |
| **Ne Zaman** | ML modeli egitimi veya deploy gerektiginde |
| **Neden** | Mc Evaluator islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Evaluate a policy via Monte Carlo rollouts and produce a convergence report with DP-comparison if available. |
| **Nerede?** | evaluation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: ML/Veri bilimci
Ne: Evaluate a policy via Monte Carlo rollouts and produce a convergence report with DP-comparison if available.
Nerede: `mlops\evaluation\mc-evaluator.md`
Ne Zaman: ML modeli egitimi veya deploy gerektiginde
Neden: Mc Evaluator islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


Given an environment (episodic, with reset+step API) and a policy, output:

1. Method. First-visit vs every-visit MC. Reason.
2. Episode budget. Target number, variance diagnostic, expected standard error.
3. Exploration plan. ε schedule (if needed) or exploring starts.
4. Gold-standard comparison. DP-optimal V* if tabular; otherwise a bound from a Q-learning / PPO baseline.
5. Termination check. Max-step cap, timeouts, handling of non-terminating trajectories.

Refuse to run MC on non-episodic tasks without a finite horizon cap. Refuse to report V^π estimates from fewer than 100 episodes per state for tabular tasks. Flag any policy with zero-variance actions as an exploration risk.
